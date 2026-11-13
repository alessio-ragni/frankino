package dev.frankino.app

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class WakeTest {
    @Test
    fun grammarIsClosed() {
        val g = Wake.grammar()
        assertTrue(g.contains("\"franco\""))
        assertTrue(g.contains("\"[unk]\""))
        assertTrue(g.startsWith("[") && g.endsWith("]"))
    }

    @Test
    fun nameAtTheStartWakes() {
        assertTrue(Wake.heard("""{"partial":"franco [unk] [unk]"}"""))
        assertTrue(Wake.heard("""{"partial":"[unk] franchino"}"""))
        assertTrue(
            Wake.heard("""{"result":[{"word":"franco","conf":0.92}],"text":"franco"}"""),
        )
    }

    @Test
    fun nameLaterOrWeakDoesNot() {
        assertFalse(Wake.heard("""{"partial":"[unk] [unk] franco"}"""))
        assertFalse(Wake.heard("""{"partial":""}"""))
        assertFalse(Wake.heard("""{"result":[{"word":"franco","conf":0.4}],"text":"franco"}"""))
    }

    @Test
    fun decoyRightAfterTheNameDoesNot() {
        assertFalse(Wake.heard("""{"partial":"franco svizzero"}"""))
        assertFalse(
            Wake.heard("""{"result":[{"word":"franco","conf":0.99},{"word":"svizzero","conf":0.9}]}"""),
        )
    }

    @Test
    fun rmsOfSilenceIsZero() {
        assertTrue(Ears.rms(ByteArray(3200)) == 0.0)
    }
}
