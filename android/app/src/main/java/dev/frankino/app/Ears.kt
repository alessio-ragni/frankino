package dev.frankino.app

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import org.vosk.Model
import org.vosk.Recognizer
import kotlin.math.max
import kotlin.math.sqrt

/**
 * Le orecchie: un solo microfono aperto, sempre, e quattro modi di usarlo.
 *
 * - WAKE: aspetta il nome. Il parlato passa solo dal riconoscitore sul tablet, a grammatica chiusa.
 * - FOLLOW: subito dopo una risposta (o mentre c'è una conferma aperta) basta parlare, senza nome.
 * - RECORDING: manda la voce al server finché non smetti di parlare.
 * - BUSY: Frankino pensa o parla; se lo richiami per nome si zittisce e ti ascolta.
 */
class Ears(private val listener: Listener) {
    interface Listener {
        /** Comincia a mandare: `lead` è l'audio appena prima, così il nome non si perde. */
        fun onBegin(lead: ByteArray)
        fun onMic(pcm: ByteArray)
        fun onEnd()
        /** Il nome detto mentre Frankino parla o pensa. */
        fun onBargeIn()
        fun onFollowUpExpired()
    }

    enum class Mode { OFF, WAKE, FOLLOW, RECORDING, BUSY }

    @Volatile var mode = Mode.OFF
        private set

    @Volatile private var model: Model? = null
    @Volatile private var recognizer: Recognizer? = null
    @Volatile private var running = false
    private var thread: Thread? = null

    // Per capire quando parli e quando hai smesso.
    private var noise = 300.0
    private var speechMs = 0
    private var silenceMs = 0
    private var heardSpeech = false
    private var modeMs = 0
    private var followLimitMs = FOLLOW_MS
    private val lead = ArrayDeque<ByteArray>()

    val hasWakeWord: Boolean get() = recognizer != null

    fun loadModel(path: String) {
        val m = Model(path)
        val r = Recognizer(m, INPUT_RATE.toFloat(), Wake.grammar())
        r.setWords(true)
        model = m
        recognizer = r
    }

    @Synchronized
    fun set(next: Mode, followLimit: Int = FOLLOW_MS) {
        if (next == mode && next != Mode.FOLLOW) return
        mode = next
        modeMs = 0
        speechMs = 0
        silenceMs = 0
        heardSpeech = false
        followLimitMs = followLimit
        if (next == Mode.WAKE || next == Mode.BUSY) runCatching { recognizer?.reset() }
    }

    @SuppressLint("MissingPermission")
    fun start() {
        if (running) return
        running = true
        thread = Thread({ loop() }, "frankino-ears").apply { start() }
    }

    fun stop() {
        running = false
        thread?.join(1000)
        thread = null
        recognizer?.close()
        model?.close()
        recognizer = null
        model = null
    }

    @SuppressLint("MissingPermission")
    private fun loop() {
        val min = AudioRecord.getMinBufferSize(INPUT_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        val rec = AudioRecord(
            MediaRecorder.AudioSource.VOICE_RECOGNITION,
            INPUT_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            max(min, CHUNK_BYTES * 4),
        )
        if (rec.state != AudioRecord.STATE_INITIALIZED) {
            Log.e(TAG, "microfono non disponibile")
            Hub.error.value = "Il microfono non si apre: controlla il permesso."
            running = false
            return
        }
        rec.startRecording()
        val buf = ByteArray(CHUNK_BYTES)
        try {
            while (running) {
                val n = rec.read(buf, 0, buf.size)
                if (n <= 0) continue
                val chunk = buf.copyOf(n)
                step(chunk)
            }
        } finally {
            rec.stop()
            rec.release()
        }
    }

    @Synchronized
    private fun step(chunk: ByteArray) {
        val ms = chunk.size / 2 * 1000 / INPUT_RATE
        modeMs += ms
        val level = rms(chunk)
        val loud = level > max(noise * SPEECH_OVER_NOISE, MIN_SPEECH_RMS)
        if (!loud && mode != Mode.RECORDING) noise = noise * 0.95 + level * 0.05

        when (mode) {
            Mode.OFF -> remember(chunk)
            Mode.WAKE -> {
                remember(chunk)
                if (wake(chunk)) begin()
            }
            Mode.BUSY -> {
                remember(chunk)
                if (wake(chunk)) {
                    listener.onBargeIn()
                    begin()
                }
            }
            Mode.FOLLOW -> {
                remember(chunk)
                speechMs = if (loud) speechMs + ms else 0
                if (speechMs >= FOLLOW_TRIGGER_MS) {
                    begin()
                } else if (modeMs >= followLimitMs) {
                    set(Mode.WAKE)
                    listener.onFollowUpExpired()
                }
            }
            Mode.RECORDING -> {
                listener.onMic(chunk)
                if (loud) {
                    heardSpeech = true
                    silenceMs = 0
                } else {
                    silenceMs += ms
                }
                val done = (heardSpeech && silenceMs >= END_SILENCE_MS) ||
                    (!heardSpeech && modeMs >= NOTHING_SAID_MS) ||
                    modeMs >= MAX_RECORDING_MS
                if (done) finish()
            }
        }
    }

    /** Dal pulsante: comincia ad ascoltare subito, o smetti se stava già ascoltando. */
    @Synchronized
    fun toggle() {
        if (mode == Mode.RECORDING) finish() else begin()
    }

    private fun begin() {
        val before = lead.fold(ByteArray(0)) { acc, b -> acc + b }
        lead.clear()
        set(Mode.RECORDING)
        heardSpeech = before.isNotEmpty() && rms(before) > max(noise * SPEECH_OVER_NOISE, MIN_SPEECH_RMS)
        listener.onBegin(before)
    }

    private fun finish() {
        set(Mode.BUSY)
        listener.onEnd()
    }

    private fun wake(chunk: ByteArray): Boolean {
        val r = recognizer ?: return false
        val final = r.acceptWaveForm(chunk, chunk.size)
        val heard = if (final) Wake.heard(r.result) else Wake.heard(r.partialResult)
        if (heard) r.reset()
        return heard
    }

    private fun remember(chunk: ByteArray) {
        lead.addLast(chunk)
        while (lead.size * CHUNK_MS > LEAD_MS) lead.removeFirst()
    }

    companion object {
        private const val TAG = "frankino.ears"
        const val CHUNK_MS = 100
        const val CHUNK_BYTES = INPUT_RATE / 1000 * CHUNK_MS * 2
        const val LEAD_MS = 1500
        const val FOLLOW_MS = 7000
        const val FOLLOW_TRIGGER_MS = 200
        const val END_SILENCE_MS = 1300
        const val NOTHING_SAID_MS = 5000
        const val MAX_RECORDING_MS = 5 * 60 * 1000
        const val SPEECH_OVER_NOISE = 3.0
        const val MIN_SPEECH_RMS = 500.0

        fun rms(pcm: ByteArray): Double {
            if (pcm.size < 2) return 0.0
            var sum = 0.0
            var i = 0
            while (i + 1 < pcm.size) {
                val s = ((pcm[i + 1].toInt() shl 8) or (pcm[i].toInt() and 0xff)).toShort().toDouble()
                sum += s * s
                i += 2
            }
            return sqrt(sum / (pcm.size / 2))
        }
    }
}
