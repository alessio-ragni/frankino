package dev.frankino.app

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.longOrNull
import kotlinx.serialization.json.put

/** I messaggi fra tablet e server, come descritti in docs/protocollo.md. */

const val INPUT_RATE = 16_000
const val CONFIRM_SURFACE = "conferma"

/** Un messaggio A2UI da passare al renderer, con quel poco che serve sapere senza aprirlo. */
data class ScreenMessage(val raw: String, val kind: String?, val surfaceId: String?)

sealed interface Incoming {
    data class Ready(val voice: Boolean, val ears: Boolean, val rate: Int?, val a2ui: String?) : Incoming
    data class Heard(val text: String) : Incoming
    data object Thinking : Incoming
    data class Say(val text: String, val rate: Int?) : Incoming
    data object SayEnd : Incoming
    data class Screen(val messages: List<ScreenMessage>) : Incoming
    data class Done(val ms: Long?) : Incoming
    data class Failure(val text: String) : Incoming
    data class Unknown(val type: String?) : Incoming
}

private val SCREEN_KINDS = listOf("createSurface", "updateComponents", "updateDataModel", "deleteSurface")

private fun JsonObject.str(key: String): String? = (this[key] as? JsonPrimitive)?.contentOrNull

private fun JsonObject.int(key: String): Int? = (this[key] as? JsonPrimitive)?.intOrNull

private fun JsonObject.bool(key: String): Boolean = (this[key] as? JsonPrimitive)?.booleanOrNull ?: false

fun parseIncoming(text: String): Incoming {
    val obj =
        try {
            Json.parseToJsonElement(text).jsonObject
        } catch (_: Exception) {
            return Incoming.Unknown(null)
        }
    return when (val type = obj.str("type")) {
        "ready" -> Incoming.Ready(obj.bool("voice"), obj.bool("ears"), obj.int("rate"), obj.str("a2ui"))
        "heard" -> Incoming.Heard(obj.str("text").orEmpty())
        "thinking" -> Incoming.Thinking
        "say" -> Incoming.Say(obj.str("text").orEmpty(), obj.int("rate"))
        "say_end" -> Incoming.SayEnd
        "a2ui" -> Incoming.Screen(screenMessages(obj["messages"]))
        "done" -> Incoming.Done((obj["ms"] as? JsonPrimitive)?.longOrNull)
        "error" -> Incoming.Failure(obj.str("text").orEmpty())
        else -> Incoming.Unknown(type)
    }
}

private fun screenMessages(element: JsonElement?): List<ScreenMessage> {
    val list = element as? JsonArray ?: return emptyList()
    return list.mapNotNull { item ->
        val msg = item as? JsonObject ?: return@mapNotNull null
        val kind = SCREEN_KINDS.firstOrNull { it in msg }
        val surfaceId = kind?.let { (msg[it] as? JsonObject)?.str("surfaceId") }
        ScreenMessage(msg.toString(), kind, surfaceId)
    }
}

object Outgoing {
    fun start(rate: Int = INPUT_RATE): String = buildJsonObject {
        put("type", "start")
        put("rate", rate)
    }.toString()

    fun end(rate: Int = INPUT_RATE): String = buildJsonObject {
        put("type", "end")
        put("rate", rate)
    }.toString()

    fun text(text: String): String = buildJsonObject {
        put("type", "text")
        put("text", text)
    }.toString()

    fun stop(): String = buildJsonObject { put("type", "stop") }.toString()

    /** Un tocco su un componente A2UI: il messaggio `action` del protocollo. */
    fun action(name: String, surfaceId: String, componentId: String, context: Map<String, Any?>): String =
        buildJsonObject {
            put("type", "action")
            put("name", name)
            put("surfaceId", surfaceId)
            put("sourceComponentId", componentId)
            put("context", toJson(context))
        }.toString()
}

/** Da un valore Kotlin qualsiasi (mappe, liste, numeri, testo) a JSON. */
fun toJson(value: Any?): JsonElement = when (value) {
    null -> JsonNull
    is JsonElement -> value
    is String -> JsonPrimitive(value)
    is Boolean -> JsonPrimitive(value)
    is Number -> JsonPrimitive(value)
    is Map<*, *> -> JsonObject(value.entries.associate { (k, v) -> k.toString() to toJson(v) })
    is Iterable<*> -> JsonArray(value.map { toJson(it) })
    is Array<*> -> JsonArray(value.map { toJson(it) })
    else -> JsonPrimitive(value.toString())
}

/** L'indirizzo del websocket a partire da quello che si scrive nelle impostazioni. */
fun socketUrl(server: String, token: String, device: String = "tablet"): String {
    var base = server.trim().trimEnd('/')
    base = when {
        base.startsWith("ws://") || base.startsWith("wss://") -> base
        base.startsWith("http://") -> "ws://" + base.removePrefix("http://")
        base.startsWith("https://") -> "wss://" + base.removePrefix("https://")
        else -> "ws://$base"
    }
    val hostPart = base.substringAfter("://")
    if (!hostPart.substringBefore('/').contains(':')) {
        val scheme = base.substringBefore("://")
        base = "$scheme://${hostPart.substringBefore('/')}:4390" +
            hostPart.removePrefix(hostPart.substringBefore('/'))
    }
    if (!base.endsWith("/ws")) base += "/ws"
    val enc = { s: String -> java.net.URLEncoder.encode(s, "UTF-8") }
    return "$base?token=${enc(token)}&device=${enc(device)}"
}
