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

## Le azioni verso fuori

Ogni strumento che non è chiaramente di sola lettura chiede conferma: lo schermo mostra cosa sta
per fare, e tu dici «sì», «no» o «non chiedermelo più» (anche coi pulsanti). Il «non chiedermelo
più» vale per quello strumento e si ritira (`POST /permessi/ritira?tool=…`).

## Cosa resta sul server

Gli audio di quello che dici, per 30 giorni (poi si cancellano, il testo resta), le trascrizioni, gli
scambi e i permessi. Tutto in `FRANKINO_DATA`, mai nella repo.

## Struttura

- `server/` — FastAPI + Claude Agent SDK. Protocollo col tablet: [`docs/protocollo.md`](docs/protocollo.md).
- `android/` — l'app (in arrivo).
- `tools/` — attrezzi per provare.
