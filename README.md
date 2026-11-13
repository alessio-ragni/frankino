# Frankino

Un compagno vocale con schermo. Lo chiami per nome («Frankino», «Franco», «Franchino»), gli parli
mentre cucini o guidi, e lui fa le cose con **Claude Code** e tutti i connettori che hai già
(messaggi, posta, calendario, documenti). Quello che si capisce meglio guardandolo (una ricetta, una
lista, un messaggio prima di mandarlo) te lo mostra sullo schermo con **A2UI**, il protocollo di
Google per le interfacce generate dagli agenti.

```
tablet Android  ── voce (PCM) ──►  server  ── testo ──►  Claude Code (Agent SDK)
  ascolta,      ◄── voce + A2UI ──  trascrive, parla,    connettori claude.ai + MCP
  parla, mostra                     chiede conferma       strumento «mostra» (A2UI)
```

## Cosa serve

- **Un abbonamento Claude tuo.** Il server usa Claude Code col *tuo* login: sul server lanci
  `claude`, fai `/login` una volta, e basta. Frankino non offre nessun login suo, non chiede le tue
  credenziali e non le tocca. È pensato per uso personale.
- **Una chiave OpenAI** (o ElevenLabs) per trascrivere e parlare: Claude non accetta audio.
- **Un tablet Android** e una rete privata fra tablet e server (consigliata Tailscale). Il server
  non va esposto su internet.

## Avvio del server

```bash
cd server
uv venv -p 3.11 .venv && uv pip install -p .venv/bin/python -e ".[dev,mac]"
cp ../.env.example .env        # riempi FRANKINO_TOKEN e OPENAI_API_KEY
.venv/bin/python -m frankino   # ascolta su :4390
.venv/bin/pytest               # test
```

Per provarlo senza tablet, dal Mac: `.venv/bin/python ../tools/prova_mac.py --token <gettone>`
(a voce) o con `--scrivi` (a testo).

## L'app Android

Sta in `android/`. Serve Java 17 e l'Android SDK (platform 37.1); sul Mac con Homebrew:
`brew install openjdk@17 android-commandlinetools`, poi
`sdkmanager "platform-tools" "platforms;android-37.1" "build-tools;36.0.0"`.

```bash
cd android
echo "sdk.dir=/opt/homebrew/share/android-commandlinetools" > local.properties
JAVA_HOME=/opt/homebrew/opt/openjdk@17 ./gradlew assembleDebug testDebugUnitTest
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Al primo avvio chiede il microfono e le notifiche, poi l'indirizzo del server (il nome su
Tailscale, per esempio `mio-mac:4390`) e il gettone. Scarica una volta il modello italiano piccolo
di [Vosk](https://alphacephei.com/vosk/models) (circa 50 MB) per la parola d'avvio.

Come ascolta:
- **Aspetta il nome** («Franco», «Franchino», «Frankino»). Lo riconosce sul tablet con una
  grammatica chiusa: finché non lo sente, al server non parte niente.
- **Subito dopo una risposta** ascolta qualche secondo anche senza nome, e mentre c'è una conferma
  aperta aspetta il tuo «sì» o «no».
- **Se lo richiami mentre parla** si zittisce e ti ascolta. Il pulsante «Parla» fa lo stesso a mano.
- Lo schermo disegna l'A2UI con il renderer ufficiale per Compose (`androidx.a2ui`, alpha).

## Le azioni verso fuori

Ogni strumento che non è chiaramente di sola lettura chiede conferma: lo schermo mostra cosa sta
per fare, e tu dici «sì», «no» o «non chiedermelo più» (anche coi pulsanti). Il «non chiedermelo
più» vale per quello strumento e si ritira (`POST /permessi/ritira?tool=…`).

## Cosa resta sul server

Gli audio di quello che dici, per 30 giorni (poi si cancellano, il testo resta), le trascrizioni, gli
scambi e i permessi. Tutto in `FRANKINO_DATA`, mai nella repo.

## Struttura

- `server/` — FastAPI + Claude Agent SDK. Protocollo col tablet: [`docs/protocollo.md`](docs/protocollo.md).
- `android/` — l'app per il tablet (Kotlin + Compose).
- `tools/` — attrezzi per provare.
