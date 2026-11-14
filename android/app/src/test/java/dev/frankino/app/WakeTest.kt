package dev.frankino.app

import dev.frankino.app.Wake.Verdict
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class WakeTest {
    private fun partial(text: String) = Wake.verdict("""{"partial":"$text"}""")

    private fun final(vararg words: Pair<String, Double>) = Wake.verdict(
        words.joinToString(",", """{"result":[""", "]}") { (w, c) -> """{"word":"$w","conf":$c}""" },
    )

    @Test
    fun grammarIsClosed() {
        val g = Wake.grammar()
        assertTrue(g.contains("\"franco\""))
        assertTrue(g.contains("\"ciao\""))
        assertTrue(g.contains("\"[unk]\""))
        assertTrue(g.startsWith("[") && g.endsWith("]"))
    }

    @Test
    fun nameFollowedBySomethingWakes() {
        assertEquals(Verdict.YES, partial("franco franko"))
        assertEquals(Verdict.YES, partial("ciao franco hey"))
        assertEquals(Verdict.YES, partial("ehi franko franco"))
    }

    @Test
    fun greetingsInFrontAreAllowed() {
        assertEquals(Verdict.YES, final("hey" to 0.9, "franco" to 0.9))
        assertEquals(Verdict.YES, final("hi" to 0.5, "franchino" to 0.8))
        assertEquals(Verdict.YES, final("ciao" to 1.0, "franko" to 0.7))
        assertEquals(Verdict.YES, final("franchino" to 0.52))
    }

    @Test
    fun nameAloneIsMaybeUntilFinal() {
        assertEquals(Verdict.MAYBE, partial("franco"))
        assertEquals(Verdict.MAYBE, partial("ehi franchino"))
        assertEquals(Verdict.YES, final("franco" to 0.9))
    }

    @Test
    fun nameNotFirstOrWeakDoesNot() {
        assertEquals(Verdict.NO, partial("vinto franco hey"))
        assertEquals(Verdict.NO, partial("trieste franko"))
        assertEquals(Verdict.NO, partial("[unk] franco"))
        assertEquals(Verdict.NO, partial(""))
        assertEquals(Verdict.NO, final("franco" to 0.3))
    }

    @Test
    fun decoyRightAfterTheNameDoesNot() {
        assertEquals(Verdict.NO, partial("franco svizzero"))
        assertEquals(Verdict.NO, partial("hi franco svizzero hei"))
        assertEquals(Verdict.NO, final("franco" to 0.99, "svizzero" to 0.9))
    }

    @Test
    fun rmsOfSilenceIsZero() {
        assertTrue(Ears.rms(ByteArray(3200)) == 0.0)
    }
}
