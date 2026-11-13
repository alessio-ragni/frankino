package dev.frankino.app

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ProtocolTest {
    @Test
    fun readsReady() {
        val m = parseIncoming("""{"type":"ready","voice":true,"ears":false,"rate":24000,"a2ui":"v0.9.1"}""")
        assertEquals(Incoming.Ready(voice = true, ears = false, rate = 24000, a2ui = "v0.9.1"), m)
    }

    @Test
    fun readsSayAndDone() {
        assertEquals(Incoming.Say("Ecco la carbonara.", 24000), parseIncoming("""{"type":"say","text":"Ecco la carbonara.","rate":24000}"""))
        assertEquals(Incoming.Done(9100), parseIncoming("""{"type":"done","ms":9100}"""))
        assertEquals(Incoming.SayEnd, parseIncoming("""{"type":"say_end"}"""))
    }

    @Test
    fun readsScreenMessagesKeepingThemWhole() {
        val m = parseIncoming(
            """{"type":"a2ui","messages":[
              {"version":"v0.9.1","createSurface":{"surfaceId":"conferma","catalogId":"x"}},
              {"version":"v0.9.1","deleteSurface":{"surfaceId":"ricetta"}}
            ]}""",
        ) as Incoming.Screen
        assertEquals(listOf("createSurface", "deleteSurface"), m.messages.map { it.kind })
        assertEquals(listOf("conferma", "ricetta"), m.messages.map { it.surfaceId })
        val first = Json.parseToJsonElement(m.messages[0].raw).jsonObject
        assertEquals("v0.9.1", first["version"]!!.jsonPrimitive.content)
    }

    @Test
    fun garbageIsUnknown() {
        assertEquals(Incoming.Unknown(null), parseIncoming("non è json"))
        assertEquals(Incoming.Unknown("boh"), parseIncoming("""{"type":"boh"}"""))
    }

    @Test
    fun writesAction() {
        val raw = Outgoing.action("confirm_yes", "conferma", "yes", mapOf("n" to 2, "list" to listOf("a", null)))
        val obj = Json.parseToJsonElement(raw).jsonObject
        assertEquals("action", obj["type"]!!.jsonPrimitive.content)
        assertEquals("confirm_yes", obj["name"]!!.jsonPrimitive.content)
        assertEquals("yes", obj["sourceComponentId"]!!.jsonPrimitive.content)
        assertEquals("""{"n":2,"list":["a",null]}""", obj["context"].toString())
    }

    @Test
    fun buildsSocketUrl() {
        assertEquals("ws://mio-mac:4390/ws?token=abc&device=tablet", socketUrl("mio-mac", "abc"))
        assertEquals("ws://mio-mac:4390/ws?token=abc&device=tablet", socketUrl("mio-mac:4390", "abc"))
        assertEquals("wss://x.example:443/ws?token=a+b&device=tablet", socketUrl("https://x.example:443/", "a b"))
        assertTrue(socketUrl("ws://10.0.0.2:4390/ws", "t").startsWith("ws://10.0.0.2:4390/ws?"))
    }
}
