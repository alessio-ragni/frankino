package dev.frankino.app

import android.content.Context
import androidx.a2ui.compose.runtime.A2uiMessageParser
import androidx.a2ui.compose.ui.catalog.A2uiBasicCatalogV1
import androidx.a2ui.model.processor.processInput
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.material3.a2ui.catalog.A2uiAudioPlayerRenderer
import androidx.compose.material3.a2ui.catalog.A2uiImageRenderer
import androidx.compose.material3.a2ui.catalog.A2uiVideoRenderer
import androidx.compose.material3.a2ui.catalog.MaterialA2uiBasicCatalogV1Defaults
import androidx.compose.material3.a2ui.catalog.materialA2uiBasicCatalogV1
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch
import androidx.a2ui.compose.ui.A2uiMessageProcessor as newA2uiMessageProcessor
import androidx.a2ui.model.processor.A2uiMessageProcessor

/** A che punto è Frankino: è quello che si vede in alto sullo schermo. */
enum class Phase(val label: String) {
    SETUP("Da configurare"),
    CONNECTING("Mi collego…"),
    OFFLINE("Non raggiungo il server"),
    LOADING_EARS("Preparo le orecchie…"),
    LISTENING("Ti ascolto: chiamami per nome"),
    FOLLOW_UP("Dimmi pure"),
    RECORDING("Sto ascoltando…"),
    THINKING("Ci penso…"),
    SPEAKING("Parlo"),
}

sealed interface Command {
    data object Talk : Command
    data object Hush : Command
    /** Dal tasto laterale (assistente): ascolta subito, senza nome. */
    data object Listen : Command
    data object Reconnect : Command
}

/** Lo stato condiviso fra il servizio che ascolta e lo schermo che mostra. */
object Hub {
    val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    val phase = MutableStateFlow(Phase.CONNECTING)
    val heard = MutableStateFlow("")
    val said = MutableStateFlow("")
    val error = MutableStateFlow<String?>(null)
    val earsProgress = MutableStateFlow<Int?>(null)
    val commands = MutableSharedFlow<Command>(extraBufferCapacity = 8)

    /** Chiesto di ascoltare prima che il filo col server fosse pronto: si ascolta appena lo è. */
    @Volatile var listenWhenReady = false
        set(value) {
            field = value
            listenAskedAt = if (value) System.currentTimeMillis() else 0L
        }

    @Volatile var listenAskedAt = 0L

    /** Una richiesta d'ascolto vecchia (il server era giù) non deve aprire il microfono dopo. */
    val listenStillWanted: Boolean
        get() = listenWhenReady && System.currentTimeMillis() - listenAskedAt < 15_000

    /** Quello che si manda al server quando tocchi un componente A2UI. */
    var onAction: (String) -> Unit = {}

    @Volatile private var processor: A2uiMessageProcessor? = null
    private val parser = A2uiMessageParser()

    fun screen(context: Context): A2uiMessageProcessor = processor ?: synchronized(this) {
        processor ?: build(context.applicationContext).also { processor = it }
    }

    fun show(context: Context, message: ScreenMessage) {
        screen(context).processInput(parser, message.raw)
    }

    private fun build(context: Context): A2uiMessageProcessor {
        val catalog = materialA2uiBasicCatalogV1(
            image = MaterialA2uiBasicCatalogV1Defaults.image(imageRenderer),
            video = MaterialA2uiBasicCatalogV1Defaults.video(videoRenderer),
            audioPlayer = MaterialA2uiBasicCatalogV1Defaults.audioPlayer(audioRenderer),
            functions = A2uiBasicCatalogV1.Functions(context),
        )
        val p = newA2uiMessageProcessor(listOf(catalog))
        scope.launch { p.collectMessages() }
        scope.launch {
            p.outboundEvents.collect { event ->
                if (event is androidx.a2ui.model.protocol.A2uiClientEventMessage) {
                    onAction(Outgoing.action(event.type, event.surfaceId, event.componentId, event.context))
                }
            }
        }
        return p
    }

    private val imageRenderer = A2uiImageRenderer { url, description, scale, modifier, onError ->
        AsyncImage(
            model = url,
            contentDescription = description,
            contentScale = scale,
            modifier = modifier,
            onError = { onError(it.result.throwable) },
        )
    }

    // Video e audio dentro lo schermo non servono ancora: si mostra il link.
    private val videoRenderer = A2uiVideoRenderer { url, modifier, _ ->
        Text("Video: $url", modifier = modifier.padding(8.dp))
    }

    private val audioRenderer = A2uiAudioPlayerRenderer { url, _, modifier, _ ->
        Text("Audio: $url", modifier = modifier.padding(8.dp))
    }
}
