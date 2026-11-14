package dev.frankino.app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.a2ui.A2uiSurface
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat

class MainActivity : ComponentActivity() {
    private lateinit var prefs: Prefs

    private val askPermissions = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { startIfAllowed() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        prefs = Prefs(this)
        // In cucina lo schermo resta acceso finché l'app è davanti.
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        setContent {
            MaterialTheme(colorScheme = if (isSystemInDarkTheme()) darkColorScheme() else lightColorScheme()) {
                Surface(modifier = Modifier.fillMaxSize()) {
                    var editing by remember { mutableStateOf(!prefs.ready) }
                    if (editing) {
                        SettingsScreen(prefs) {
                            editing = false
                            startIfAllowed()
                            Hub.commands.tryEmit(Command.Reconnect)
                        }
                    } else {
                        MainScreen(onSettings = { editing = true })
                    }
                }
            }
        }
        askPermissions()
        handle(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handle(intent)
    }

    /** Tasto laterale tenuto premuto (Frankino è l'assistente predefinito): si ascolta subito. */
    private fun handle(intent: Intent?) {
        if (intent?.action != Intent.ACTION_ASSIST && intent?.action != ACTION_LISTEN) return
        Hub.listenWhenReady = true
        Hub.commands.tryEmit(Command.Listen)
    }

    companion object {
        const val ACTION_LISTEN = "dev.frankino.app.ASCOLTA"
    }

    private fun askPermissions() {
        val wanted = buildList {
            add(Manifest.permission.RECORD_AUDIO)
            if (Build.VERSION.SDK_INT >= 33) add(Manifest.permission.POST_NOTIFICATIONS)
        }.filter { ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED }
        if (wanted.isEmpty()) startIfAllowed() else askPermissions.launch(wanted.toTypedArray())
    }

    private fun startIfAllowed() {
        val mic = ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
        if (mic != PackageManager.PERMISSION_GRANTED) {
            Hub.error.value = "Senza il permesso del microfono Frankino non ti sente."
            return
        }
        if (prefs.ready) FrankinoService.start(this)
    }
}

@Composable
private fun MainScreen(onSettings: () -> Unit) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val phase by Hub.phase.collectAsState()
    val heard by Hub.heard.collectAsState()
    val said by Hub.said.collectAsState()
    val error by Hub.error.collectAsState()
    val progress by Hub.earsProgress.collectAsState()
    val surfaces by Hub.screen(context).activeSurfaces.collectAsState()
    val micOn by Hub.micOn.collectAsState()

    Column(modifier = Modifier.fillMaxSize().safeDrawingPadding().padding(16.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
            Text(phase.label, style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f))
            TextButton(onClick = onSettings) { Text("Impostazioni") }
        }
        // L'interruttore del microfono, come il tasto di Alexa: rosso quando è spento.
        Button(
            onClick = { Hub.commands.tryEmit(Command.Mic(!micOn)) },
            colors = if (micOn) ButtonDefaults.filledTonalButtonColors() else ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.error,
                contentColor = MaterialTheme.colorScheme.onError,
            ),
            modifier = Modifier.fillMaxWidth().height(64.dp).padding(top = 8.dp),
        ) {
            Text(
                if (micOn) "Microfono acceso · tocca per spegnere" else "Microfono spento · tocca per riaccendere",
                style = MaterialTheme.typography.titleMedium,
            )
        }
        progress?.let {
            Text("Scarico la parola d'avvio: $it%", style = MaterialTheme.typography.bodySmall)
            LinearProgressIndicator(progress = { it / 100f }, modifier = Modifier.fillMaxWidth())
        }
        error?.let {
            Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium)
        }
        if (heard.isNotBlank()) {
            Text("«$heard»", style = MaterialTheme.typography.bodyLarge, modifier = Modifier.padding(top = 8.dp))
        }
        if (said.isNotBlank()) {
            Text(said, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.primary)
        }
        Spacer(Modifier.height(12.dp))

        // Lo schermo A2UI: la conferma, se c'è, sempre in cima.
        val ordered = surfaces.sortedBy { if (it.id == CONFIRM_SURFACE) 0 else 1 }
        Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
            Column(
                modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                ordered.forEach { surface ->
                    A2uiSurface(surfaceModel = surface, modifier = Modifier.fillMaxWidth())
                }
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.padding(top = 12.dp)) {
            Button(onClick = { Hub.commands.tryEmit(Command.Talk) }, modifier = Modifier.height(56.dp).width(200.dp)) {
                Text(if (phase == Phase.RECORDING) "Ho finito" else "Parla")
            }
            OutlinedButton(onClick = { Hub.commands.tryEmit(Command.Hush) }, modifier = Modifier.height(56.dp)) {
                Text("Zitto")
            }
        }
    }
}

@Composable
private fun SettingsScreen(prefs: Prefs, onDone: () -> Unit) {
    var server by remember { mutableStateOf(prefs.server) }
    var token by remember { mutableStateOf(prefs.token) }
    Column(
        modifier = Modifier.fillMaxSize().safeDrawingPadding().padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("Impostazioni", style = MaterialTheme.typography.headlineMedium)
        Text(
            "L'indirizzo del server è il nome del Mac (o del server) su Tailscale, per esempio " +
                "«mio-mac:4390». Il gettone è il FRANKINO_TOKEN del file .env del server.",
            style = MaterialTheme.typography.bodyMedium,
        )
        OutlinedTextField(
            value = server,
            onValueChange = { server = it },
            label = { Text("Indirizzo del server") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = token,
            onValueChange = { token = it },
            label = { Text("Gettone") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth(),
        )
        Button(
            enabled = server.isNotBlank() && token.isNotBlank(),
            onClick = {
                prefs.server = server
                prefs.token = token
                onDone()
            },
        ) { Text("Salva e collegati") }
    }
}
