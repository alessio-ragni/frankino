# Il protocollo fra tablet e server

Un websocket: `ws://<server>:4390/ws?token=<FRANKINO_TOKEN>&device=<nome>`.
Gettone sbagliato → il server chiude con codice 4401.

I messaggi di testo sono JSON con un campo `type`. L'audio viaggia in frame binari:
**PCM 16 bit, mono, little-endian**. Dal tablet a **16 kHz**; dal server al `rate` dichiarato
nel `say` che lo precede (24 kHz con OpenAI ed ElevenLabs).

## Dal tablet al server

| type | campi | cosa vuol dire |
|---|---|---|
| `start` | `rate` (default 16000) | sto per mandare la voce. Se Frankino stava parlando, tace |
| *(binario)* | PCM | pezzi di voce, fra `start` ed `end` |
| `end` | `rate` | ho finito di parlare: trascrivi e rispondi |
| `text` | `text` | una frase scritta, al posto della voce |
| `action` | `name`, `surfaceId`, `sourceComponentId`, `context` | un tocco su un componente A2UI (il messaggio `action` di A2UI) |
| `stop` | — | zitto: interrompe voce e pensiero |

Le azioni `confirm_yes`, `confirm_always` e `confirm_no` rispondono alla scheda di conferma. Le
altre arrivano a Claude come frase.

## Dal server al tablet

| type | campi | cosa vuol dire |
|---|---|---|
| `ready` | `voice`, `ears`, `rate`, `a2ui` | collegato. `voice`/`ears` falsi = server senza voce o trascrizione |
| `heard` | `text`, `recording` | quello che ha capito |
| `thinking` | — | sta pensando (mostra qualcosa) |
| `say` | `text`, `rate` | sta per dire questa frase; seguono i frame binari dell'audio |
| `say_end` | — | fine dell'audio di quella frase |
| `a2ui` | `messages` | messaggi A2UI da passare al renderer, nell'ordine |
| `done` | `ms` | fine del turno, dopo l'ultima frase: si può tornare ad ascoltare |
| `error` | `text` | qualcosa non va lato server |

## Conferme

Quando Claude vuole usare uno strumento che non è di sola lettura, il server manda una superficie
A2UI con `surfaceId: "conferma"` e dice «Lo faccio?». La risposta può arrivare a voce («sì», «no»,
«non chiedermelo più») o con i pulsanti (`confirm_*`). Dopo la risposta la superficie viene
cancellata con `deleteSurface`. Senza risposta per `FRANKINO_CONFIRM_TIMEOUT_S` vale come no.
