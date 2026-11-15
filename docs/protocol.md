# The protocol between tablet and server

One websocket: `ws://<server>:4390/ws?token=<FRANKINO_TOKEN>&device=<nome>`.
Wrong token → the server closes with code 4401.

Text messages are JSON with a `type` field. Audio travels in binary frames:
**16-bit PCM, mono, little-endian**. From the tablet at **16 kHz**; from the server at the `rate`
declared in the `say` that comes before it (24 kHz with OpenAI and ElevenLabs).

How the whole thing behaves, without code, is in [`how-it-works.md`](how-it-works.md).

## From the tablet to the server

| type | fields | what it means |
|---|---|---|
| `start` | `rate` (default 16000), `why` | I am about to send voice. If Frankino was speaking, it goes quiet. `why` says why the tablet is listening: `name` (it heard the name; also the value when missing), `follow` (right after an answer, without the name), `button` (the talk button), `key` (side key) |
| *(binary)* | PCM | pieces of voice, between `start` and `end` |
| `end` | `rate` | I have finished speaking: transcribe and answer |
| `text` | `text` | a written sentence, instead of voice |
| `action` | `name`, `surfaceId`, `sourceComponentId`, `context` | a tap on an A2UI component (the A2UI `action` message) |
| `stop` | — | quiet: stops both voice and thinking |

The actions `confirm_yes`, `confirm_always` and `confirm_no` answer the confirmation card. The
others reach Claude as a sentence.

## From the server to the tablet

| type | fields | what it means |
|---|---|---|
| `ready` | `voice`, `ears`, `rate`, `a2ui` | connected. `voice`/`ears` false = server without voice or transcription |
| `heard` | `text`, `recording` | what it understood |
| `thinking` | — | it is thinking (show something) |
| `say` | `text`, `rate` | it is about to say this sentence; the binary audio frames follow |
| `say_end` | — | end of the audio for that sentence |
| `a2ui` | `messages` | A2UI messages to pass to the renderer, in order |
| `done` | `ms` | end of the turn, after the last sentence: listening can start again |
| `ignored` | `reason` | it was not for Frankino: no answer, audio and text already deleted. Go back to waiting for the name, with no follow-up |
| `error` | `text` | something is wrong on the server side |

## Confirmations

When Claude wants to use a tool that is not read-only, the server sends an A2UI surface with
`surfaceId: "conferma"` and says «Lo faccio?» (shall I do it?). The answer can come by voice («sì»,
«no», «non chiedermelo più»: yes, no, don't ask me again) or with the buttons (`confirm_*`). After
the answer the surface is removed with `deleteSurface`. No answer within
`FRANKINO_CONFIRM_TIMEOUT_S` counts as no.

## Not meant for Frankino

The tablet wakes up with its own recognizer, which can be wrong. The server checks again on the
real transcript:

- `why: name` and the sentence does not start with the name (at most after two greetings such as
  «ehi», «ciao», «senti»): `ignored` with `reason: "non chiamato"` (not called);
- `why: follow` and the sentence is the echo of what Frankino has just said: `ignored`, `"eco"`
  (echo);
- `why: follow` and Claude judges that people were talking to each other (it answers only «…»):
  `ignored`, `"non per me"` (not for me).

In all three cases Claude does not answer aloud and all that is left of the recording is the row
with date, length and reason: audio and text are deleted at once. With `button` and `key` nothing
is checked: the intent is explicit.
