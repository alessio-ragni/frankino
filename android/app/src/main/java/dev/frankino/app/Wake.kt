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

    /** Saluti ammessi davanti al nome: «ehi Franco», «ciao Franchino», «hey Franko». */
    val GREETINGS = listOf("ehi", "hey", "hei", "ei", "ciao", "hi")

    const val UNKNOWN = "[unk]"

    /** Sotto questa sicurezza, nel risultato finale, non è un richiamo. Tarata con `tools/prova_parola.py`. */
    const val MIN_CONFIDENCE = 0.5

    /** Al massimo due saluti davanti al nome. */
    const val MAX_GREETINGS = 2

    enum class Verdict { YES, NO, MAYBE }

    fun grammar(): String = JsonArray(
        (NAMES + GREETINGS + DECOYS.filter { it !in NAMES } + UNKNOWN).map { JsonPrimitive(it) },
    ).toString()

    /**
     * Dal JSON di vosk (parziale o finale) a «mi hanno chiamato»: SÌ, NO, o FORSE quando il nome è
     * l'ultima cosa sentita e non si sa ancora se dopo arriva un'esca («il franco… svizzero»).
     *
     * Regola: saltati i saluti, la prima parola dev'essere un nome, e quella dopo non un'esca.
     * «Ho visto Franco» non sveglia: il nome non è in testa. Il resto non si conserva.
     */
    fun verdict(voskJson: String): Verdict {
        val obj = try {
            Json.parseToJsonElement(voskJson).jsonObject
        } catch (_: Exception) {
            return Verdict.NO
        }
        val result = obj["result"] as? JsonArray
        if (result != null) {
            val words = result.mapNotNull { it as? JsonObject }.map {
                ((it["word"] as? JsonPrimitive)?.contentOrNull ?: "") to
                    ((it["conf"] as? JsonPrimitive)?.doubleOrNull ?: 0.0)
            }
            return decide(words, final = true)
        }
        val text = (obj["partial"] as? JsonPrimitive)?.contentOrNull
            ?: (obj["text"] as? JsonPrimitive)?.contentOrNull
            ?: return Verdict.NO
        return decide(text.split(' ').filter { it.isNotBlank() }.map { it to 1.0 }, final = false)
    }

    private fun decide(words: List<Pair<String, Double>>, final: Boolean): Verdict {
        var i = 0
        while (i < words.size && words[i].first in GREETINGS) i++
        if (i >= words.size || i > MAX_GREETINGS) return Verdict.NO
        val (word, conf) = words[i]
        if (word !in NAMES || (final && conf < MIN_CONFIDENCE)) return Verdict.NO
        val next = words.getOrNull(i + 1)?.first
        return when {
            next != null -> if (next in DECOYS) Verdict.NO else Verdict.YES
            final -> Verdict.YES
            else -> Verdict.MAYBE
        }
    }

    fun heard(voskJson: String): Boolean = verdict(voskJson) == Verdict.YES
}
