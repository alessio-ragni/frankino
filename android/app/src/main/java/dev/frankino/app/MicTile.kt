package dev.frankino.app

import android.content.ComponentName
import android.content.Context
import android.service.quicksettings.Tile
import android.service.quicksettings.TileService
import android.util.Log

/**
 * Il riquadro «Frankino» nel pannello rapido (la tendina dall'alto): il tasto del microfono, come
 * quello di Alexa. Acceso ascolta il nome, spento chiude il microfono.
 */
class MicTile : TileService() {
    override fun onStartListening() {
        super.onStartListening()
        show(Prefs(this).micOn)
    }

    override fun onClick() {
        super.onClick()
        val on = !Prefs(this).micOn
        Prefs(this).micOn = on
        show(on)
        try {
            startService(FrankinoService.micIntent(this, on))
        } catch (bad: Exception) {
            // Il servizio non gira e Android non lo lascia partire da qui: lo farà l'app, aprendola.
            Log.w("frankino", "servizio non raggiungibile dal riquadro", bad)
        }
    }

    private fun show(on: Boolean) {
        val tile = qsTile ?: return
        tile.state = if (on) Tile.STATE_ACTIVE else Tile.STATE_INACTIVE
        tile.label = "Frankino"
        tile.subtitle = if (on) "In ascolto" else "Microfono spento"
        tile.updateTile()
    }

    companion object {
        /** Chiede al pannello rapido di ridisegnare il riquadro dopo un cambio fatto altrove. */
        fun refresh(context: Context) {
            runCatching { requestListeningState(context, ComponentName(context, MicTile::class.java)) }
        }
    }
}
