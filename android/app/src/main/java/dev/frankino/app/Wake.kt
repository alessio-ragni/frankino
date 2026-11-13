package dev.frankino.app

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.jsonObject

/**
 * La parola d'avvio. Il riconoscitore sul tablet ha una grammatica CHIUSA: i nomi, qualche
 * parola-esca e `[unk]`. Il parlato di casa non è rappresentabile lì dentro, quindi non viene
 * trascritto: finché non sente il nome, al server non parte niente.
 *
 * Le esche sono parole con cui «franco» si confonde (franchi, Francia, francese…): danno a quei
 * suoni una casella loro, così il nome smette di raccogliere tutto ciò che gli somiglia. Non
 * escono mai di qui: servono a decidere, poi spariscono come `[unk]`.
 */
object Wake {
    val NAMES = listOf("franco", "franko", "franchino", "frankino")

    val DECOYS = listOf(
        "franchi", "franca", "franche", "franchezza", "franchigia", "francamente", "francia",
        "francese", "francesi", "francesco", "franceschi", "franchini", "francobollo",
        "franchismo", "svizzero", "svizzeri", "svizzera", "porto", "parlo", "parla", "parlava",
        "trieste", "pagato", "lingua", "vinto",
    )

    const val UNKNOWN = "[unk]"

    /** Sotto questa sicurezza, nel risultato finale, non è un richiamo. */
    const val MIN_CONFIDENCE = 0.65

    /** Il nome deve stare in testa: «Franco, …», non «…ho visto Franco». */
    const val MAX_LEADING_TOKENS = 2

    fun grammar(): String = JsonArray(
        (NAMES + DECOYS.filter { it !in NAMES } + UNKNOWN).map { JsonPrimitive(it) },
    ).toString()

    /**
     * Dal JSON di vosk (parziale o finale) a «mi hanno chiamato» sì/no. Si guardano solo i token
     * in testa; il resto non si conserva.
     */
    fun heard(voskJson: String): Boolean {
        val obj = try {
            Json.parseToJsonElement(voskJson).jsonObject
        } catch (_: Exception) {
            return false
        }
        val result = obj["result"] as? JsonArray
        if (result != null) {
            val words = result.mapNotNull { it as? JsonObject }
            return words.take(MAX_LEADING_TOKENS).withIndex().any { (i, w) ->
                val word = (w["word"] as? JsonPrimitive)?.contentOrNull
                val conf = (w["conf"] as? JsonPrimitive)?.doubleOrNull ?: 0.0
                val next = (words.getOrNull(i + 1)?.get("word") as? JsonPrimitive)?.contentOrNull
                word in NAMES && conf >= MIN_CONFIDENCE && next !in DECOYS
            }
        }
        val text = (obj["partial"] as? JsonPrimitive)?.contentOrNull
            ?: (obj["text"] as? JsonPrimitive)?.contentOrNull
            ?: return false
        val tokens = text.split(' ').filter { it.isNotBlank() }
        return tokens.take(MAX_LEADING_TOKENS).withIndex().any { (i, t) ->
            t in NAMES && tokens.getOrNull(i + 1) !in DECOYS
        }
    }
}
