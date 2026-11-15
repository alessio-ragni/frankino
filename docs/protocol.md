# Il protocollo fra tablet e server

Un websocket: `ws://<server>:4390/ws?token=<FRANKINO_TOKEN>&device=<nome>`.
Gettone sbagliato → il server chiude con codice 4401.

I messaggi di testo sono JSON con un campo `type`. L'audio viaggia in frame binari:
**PCM 16 bit, mono, little-endian**. Dal tablet a **16 kHz**; dal server al `rate` dichiarato
nel `say` che lo precede (24 kHz con OpenAI ed ElevenLabs).

## Dal tablet al server

| type | campi | cosa vuol dire |
|---|---|---|
| `start` | `rate` (default 16000), `why` | sto per mandare la voce. Se Frankino stava parlando, tace. `why` dice perché il tablet ascolta: `name` (ha sentito il nome; è anche il valore se manca), `follow` (subito dopo una risposta, senza nome), `button` (pulsante «Parla»), `key` (tasto laterale) |
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
| `ignored` | `reason` | non era per Frankino: nessuna risposta, audio e testo già cancellati. Si torna ad aspettare il nome, senza seguito |
| `error` | `text` | qualcosa non va lato server |

## Conferme

Quando Claude vuole usare uno strumento che non è di sola lettura, il server manda una superficie
A2UI con `surfaceId: "conferma"` e dice «Lo faccio?». La risposta può arrivare a voce («sì», «no»,
«non chiedermelo più») o con i pulsanti (`confirm_*`). Dopo la risposta la superficie viene
cancellata con `deleteSurface`. Senza risposta per `FRANKINO_CONFIRM_TIMEOUT_S` vale come no.

## Non era per Frankino

Il tablet si sveglia col suo riconoscitore, che può sbagliare. Il server ricontrolla sulla
trascrizione vera:

- `why: name` e la frase non comincia col nome (al più dopo due saluti come «ehi», «ciao», «senti»):
  `ignored` con `reason: "non chiamato"`;
- `why: follow` e la frase è l'eco di quello che Frankino ha appena detto: `ignored`, `"eco"`;
- `why: follow` e Claude giudica che parlassero fra loro (risponde solo «…»): `ignored`, `"non per me"`.

In tutti e tre i casi Claude non risponde a voce e della registrazione resta solo la riga con data,
durata e motivo: audio e testo vengono cancellati subito. Con `button` e `key` non si controlla
niente: l'intenzione è esplicita.
