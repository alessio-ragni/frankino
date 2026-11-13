package dev.frankino.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * Il cuore sul tablet: un servizio in primo piano che tiene aperti microfono e filo col server
 * anche quando lo schermo mostra un'altra app. Una notifica fissa dice che sta ascoltando.
 */
class FrankinoService : Service(), Link.Listener, Ears.Listener {
    private lateinit var prefs: Prefs
    private lateinit var link: Link
    private lateinit var ears: Ears
    private val voice = Voice()
    private var wakeLock: PowerManager.WakeLock? = null
    private val jobs = mutableListOf<Job>()
    private var stopped = false

    // Lo stato del turno.
    @Volatile private var turnOpen = false
    @Volatile private var confirmOpen = false
    @Volatile private var endedAt = 0L

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        prefs = Prefs(this)
        link = Link(this)
        ears = Ears(this)
        try {
            startForeground(NOTIFICATION_ID, notification(), ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
        } catch (bad: Exception) {
            // Android non lascia aprire il microfono a un servizio ripartito da solo in background:
            // si riparte quando apri l'app.
            Log.w(TAG, "non posso ascoltare adesso", bad)
            stopped = true
            stopSelf()
            return
        }
        wakeLock = (getSystemService(Context.POWER_SERVICE) as PowerManager)
            .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "frankino:ascolto")
            .apply { acquire() }

        Hub.onAction = { link.send(it) }
        Hub.screen(this)
        ears.start()
        jobs += Hub.scope.launch { prepareEars() }
        jobs += Hub.scope.launch { Hub.commands.collect { onCommand(it) } }
        jobs += Hub.scope.launch { watchVoice() }
        connect()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int =
        if (stopped) START_NOT_STICKY else START_STICKY

    override fun onDestroy() {
        if (stopped) {
            voice.close()
            super.onDestroy()
            return
        }
        jobs.forEach { it.cancel() }
        link.close()
        ears.stop()
        voice.close()
        wakeLock?.release()
        super.onDestroy()
    }

    private fun connect() {
        if (!prefs.ready) {
            Hub.phase.value = Phase.SETUP
            link.close()
            return
        }
        Hub.phase.value = Phase.CONNECTING
        link.connect(socketUrl(prefs.server, prefs.token))
    }

    private suspend fun prepareEars() {
        try {
            if (!EarsModel.ready(this)) {
                Hub.earsProgress.value = 0
                EarsModel.fetch(this) { Hub.earsProgress.value = it }
            }
            ears.loadModel(EarsModel.dir(this).absolutePath)
            Hub.earsProgress.value = null
            if (link.connected && ears.mode == Ears.Mode.OFF) listen()
        } catch (bad: Exception) {
            Log.e(TAG, "parola d'avvio non disponibile", bad)
            Hub.earsProgress.value = null
            Hub.error.value = "Non riesco a preparare la parola d'avvio: usa il pulsante per parlare."
        }
    }

    private fun onCommand(command: Command) {
        when (command) {
            Command.Talk -> {
                if (ears.mode != Ears.Mode.RECORDING) hushLocally()
                ears.toggle()
            }
            Command.Hush -> {
                hushLocally()
                link.send(Outgoing.stop())
                turnOpen = false
                listen()
            }
            Command.Reconnect -> connect()
        }
    }

    private fun hushLocally() {
        voice.hush()
    }

    /** Torna ad aspettare il nome (o, se non c'è la parola d'avvio, il pulsante). */
    private fun listen() {
        ears.set(Ears.Mode.WAKE)
        Hub.phase.value = if (link.connected) Phase.LISTENING else Phase.OFFLINE
    }

    /**
     * Quando la voce ha finito: se il turno è chiuso si ascolta qualche secondo senza nome; se c'è
     * una conferma aperta si ascolta finché non arriva la risposta.
     */
    private suspend fun watchVoice() {
        val scope = Hub.scope
        while (scope.isActive) {
            delay(150)
            val m = ears.mode
            if (m != Ears.Mode.BUSY || voice.busy) continue
            val stale = System.currentTimeMillis() - endedAt > NO_ANSWER_MS
            when {
                // «Lo faccio?» detto e finito: si aspetta la risposta senza bisogno del nome.
                confirmOpen && Hub.phase.value == Phase.SPEAKING -> {
                    ears.set(Ears.Mode.FOLLOW, followLimit = CONFIRM_LISTEN_MS)
                    Hub.phase.value = Phase.FOLLOW_UP
                }
                !turnOpen && Hub.phase.value == Phase.SPEAKING -> {
                    ears.set(Ears.Mode.FOLLOW)
                    Hub.phase.value = Phase.FOLLOW_UP
                }
                // Il server non ha risposto (audio vuoto o troppo corto): si torna ad ascoltare.
                !turnOpen && Hub.phase.value == Phase.THINKING && stale -> listen()
            }
        }
    }

    // ── il filo ─────────────────────────────────────────────────────────────

    override fun onOpen() {
        Hub.error.value = null
    }

    override fun onText(text: String) {
        when (val m = parseIncoming(text)) {
            is Incoming.Ready -> {
                Hub.error.value = when {
                    !m.ears -> "Il server non ha la trascrizione: scrivi o configura la chiave."
                    !m.voice -> "Il server non ha la voce: risponderà solo sullo schermo."
                    else -> null
                }
                if (ears.mode == Ears.Mode.OFF || ears.mode == Ears.Mode.BUSY) listen()
                else Hub.phase.value = Phase.LISTENING
            }
            is Incoming.Heard -> Hub.heard.value = m.text
            Incoming.Thinking -> {
                turnOpen = true
                Hub.said.value = ""
                Hub.phase.value = Phase.THINKING
                if (ears.mode != Ears.Mode.RECORDING) ears.set(Ears.Mode.BUSY)
            }
            is Incoming.Say -> {
                voice.rate(m.rate)
                Hub.said.value = m.text
                Hub.phase.value = Phase.SPEAKING
                if (ears.mode != Ears.Mode.RECORDING) ears.set(Ears.Mode.BUSY)
            }
            Incoming.SayEnd -> Unit
            is Incoming.Screen -> m.messages.forEach { msg ->
                if (msg.surfaceId == CONFIRM_SURFACE) {
                    if (msg.kind == "createSurface") confirmOpen = true
                    if (msg.kind == "deleteSurface") confirmOpen = false
                }
                Hub.scope.launch(Dispatchers.Main) {
                    runCatching { Hub.show(this@FrankinoService, msg) }
                        .onFailure { Log.w(TAG, "messaggio A2UI scartato", it) }
                }
            }
            is Incoming.Done -> {
                turnOpen = false
                if (Hub.phase.value != Phase.SPEAKING && ears.mode == Ears.Mode.BUSY) {
                    // Nessuna voce (o già finita): si ascolta subito senza nome.
                    ears.set(Ears.Mode.FOLLOW)
                    Hub.phase.value = Phase.FOLLOW_UP
                }
            }
            is Incoming.Failure -> Hub.error.value = m.text
            is Incoming.Unknown -> Unit
        }
    }

    override fun onAudio(pcm: ByteArray) = voice.play(pcm)

    override fun onClosed(reason: String, retry: Boolean) {
        Hub.error.value = reason
        Hub.phase.value = if (retry) Phase.OFFLINE else Phase.SETUP
        voice.hush()
        ears.set(Ears.Mode.OFF)
        turnOpen = false
    }

    // ── le orecchie ─────────────────────────────────────────────────────────

    override fun onBegin(lead: ByteArray) {
        Hub.phase.value = Phase.RECORDING
        Hub.heard.value = ""
        link.send(Outgoing.start())
        if (lead.isNotEmpty()) link.send(lead)
    }

    override fun onMic(pcm: ByteArray) {
        link.send(pcm)
    }

    override fun onEnd() {
        endedAt = System.currentTimeMillis()
        link.send(Outgoing.end())
        Hub.phase.value = Phase.THINKING
    }

    override fun onBargeIn() {
        voice.hush()
        link.send(Outgoing.stop())
    }

    override fun onFollowUpExpired() {
        Hub.phase.value = if (link.connected) Phase.LISTENING else Phase.OFFLINE
    }

    private fun notification(): Notification {
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL, "Ascolto", NotificationManager.IMPORTANCE_LOW).apply {
                description = "Frankino è in ascolto della parola d'avvio"
            },
        )
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE,
        )
        return Notification.Builder(this, CHANNEL)
            .setContentTitle("Frankino")
            .setContentText("Ti ascolto: chiamami per nome")
            .setSmallIcon(R.drawable.ic_frankino)
            .setContentIntent(open)
            .setOngoing(true)
            .build()
    }

    companion object {
        private const val TAG = "frankino"
        private const val CHANNEL = "ascolto"
        private const val NOTIFICATION_ID = 1
        private const val CONFIRM_LISTEN_MS = 60_000
        private const val NO_ANSWER_MS = 20_000L

        fun start(context: Context) {
            ContextCompat.startForegroundService(context, Intent(context, FrankinoService::class.java))
        }
    }
}
