package dev.frankino.app

import android.content.Context

/** Indirizzo del server e gettone: li scrivi tu sul tablet, non stanno nel codice. */
class Prefs(context: Context) {
    private val sp = context.getSharedPreferences("frankino", Context.MODE_PRIVATE)

    var server: String
        get() = sp.getString("server", "").orEmpty()
        set(value) = sp.edit().putString("server", value.trim()).apply()

    var token: String
        get() = sp.getString("token", "").orEmpty()
        set(value) = sp.edit().putString("token", value.trim()).apply()

    /** L'interruttore del microfono: resta com'è anche dopo un riavvio. */
    var micOn: Boolean
        get() = sp.getBoolean("mic", true)
        set(value) = sp.edit().putBoolean("mic", value).apply()

    val ready: Boolean get() = server.isNotBlank() && token.isNotBlank()
}
