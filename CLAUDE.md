# Frankino — guida per Claude

Compagno vocale con schermo: tablet Android davanti, server Python dietro, Claude Code (Agent SDK,
login dell'abbonamento di chi lo ospita) come cervello, A2UI per lo schermo. Si parte semplici e si
aggiunge a mano a mano: niente architettura in anticipo.

## Regole

- **Repo pubblica.** Mai segreti, audio, trascrizioni, nomi o numeri veri: né nel codice, né nei
  test, né negli esempi. `.env` e `FRANKINO_DATA` stanno fuori.
- **Mai `ANTHROPIC_API_KEY`.** Il server usa il login dell'abbonamento; se la chiave c'è, la CLI la
  preferisce e fattura a consumo.
- **Frankino non offre login a Claude.ai e non tocca credenziali.** Ognuno fa `/login` da sé.
- **Le azioni verso fuori passano dal cancello** (`server/frankino/confirm.py`, hook PreToolUse).
  Prudente per costruzione: chiede tutto tranne ciò che è chiaramente di sola lettura. Non
  sostituirlo con il `can_use_tool`: con le impostazioni utente in modalità «auto» non viene chiamato.
- **Voce e trascrizione sono intercambiabili** (`server/frankino/speech/`): un servizio nuovo è un
  file e una riga nei dizionari, mai un `if` sparso.
- **Lo schermo parla A2UI** (`server/frankino/a2ui.py`), versione da `FRANKINO_A2UI_VERSION`.
- Il protocollo col tablet è in `docs/protocollo.md`: se lo cambi, cambi il documento.
- Nomi nel codice in inglese, testi per le persone in italiano.

## Comandi

```bash
cd server
.venv/bin/pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/python -m frankino
.venv/bin/python ../tools/prova_mac.py --token <gettone> [--scrivi]
```

## Changelog

`docs/00_CHANGELOG.md`, in italiano per chi non legge codice, a ogni commit.
