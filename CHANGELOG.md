# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the version numbers follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-11-14

Frankino no longer wakes up by itself when people talk around the house, and it can be switched
off like Alexa. It answers sooner, understands English too, and there is a plain explanation of
how it works.

### Added

- **A microphone switch, like the one on Alexa.** A big button in the app, an action in the
  notification and a «Frankino» tile in quick settings. Off means the microphone is really closed;
  it stays off even after a restart.
- **Italian and English.** Transcription recognizes the language by itself, and Frankino answers in
  the language you speak to it.
- **How it works, explained without code**: [`docs/how-it-works.md`](docs/how-it-works.md).

### Changed

- **The follow-up without the name is more careful.** After an answer it listens for less time and
  only to a real voice. It throws away its own voice, and if it understands that you are talking to
  each other it does not answer.
- **It thinks with Claude Haiku**, with little reasoning: it answers sooner and uses much less of
  the subscription. Going back to Sonnet or Opus takes one line.
- **Conversations with Claude are not saved to disk** on the server.

### Fixed

- **Never without the name.** Every now and then the tablet thought it heard «Franco» in the middle
  of a conversation. Now the server checks again on the transcribed sentence: if it does not start
  with the name, it is thrown away at once, audio and text, and Frankino stays quiet.
- **Silence no longer sounds like a call.** The names are no longer suggested to the transcription:
  when it heard nothing, the transcriber repeated them and it looked as if someone had called
  Frankino.

## [0.2.0] - 2026-11-14

The tablet has arrived and Frankino answers aloud from it. The brain is no longer on the Mac: it
lives on a server of its own, always on, inside a private network.

### Added

- **The server is on AWS, always on.** A small machine (about $15 a month) that can only be reached
  from your private Tailscale network: no port open to the internet. Every night it copies the
  database to a separate archive.
- **You can also call it with a greeting.** «Ehi Franko», «ciao Franchino», «hey Franco», «hi
  Franco», as well as the name on its own.
- **The side key opens Frankino, not Gemini.** Holding it down opens Frankino already listening;
  «Hey Google» is no longer the assistant either.
- **A step-by-step guide** to redo everything from scratch: [`docs/deployment.md`](docs/deployment.md).

### Changed

- **Secrets are not stored anywhere on disk.** The voice key and the tablet token are read at every
  start from a protected AWS store.
- **It hears you better from a distance.** A faraway voice is boosted before it is transcribed, and
  the app recognizes it as speech even when it arrives faint.

### Fixed

- **The name said in the middle of a sentence no longer wakes it** («ho visto Franco», I saw Franco).
- **It no longer answers itself.** Right after speaking, the tablet still heard its own voice and
  sent it back: that audio is now thrown away.
- **The token no longer ends up in the server logs.**

## [0.1.0] - 2026-11-13

A new project, from scratch, for a voice companion with a screen that you can carry around. On
12 November came the server: it understands, thinks with Claude Code and all the connectors,
answers aloud and draws on the screen. On 13 November Frankino went on GitHub as an open source
project, with the first version of the Android app, ready to install on the tablet as soon as it
arrives.

### Added

- **It thinks with Claude Code and your connectors.** It uses your subscription login, so it sees
  the same services you have already linked (messages, mail, calendar, documents) without setting
  them up a second time.
- **It shows things on the screen.** When an answer is easier to understand by looking at it (a
  recipe, a list) it draws it with A2UI, and says only the gist aloud.
- **It starts speaking at the first sentence.** It does not wait for the end of the answer: each
  complete sentence goes out right away.
- **Voice and transcription can be changed with a setting.** It starts with OpenAI; ElevenLabs is
  already there.
- **It asks before doing anything outward.** It shows what it is about to do and waits for a «sì»,
  a «no» or a «non chiedermelo più» (yes, no, don't ask me again), by voice or with a button. When
  in doubt it asks: only what just reads goes through without questions.
- **Audio is kept for 30 days, text forever.** Long dictations are not lost, and after a month the
  audio deletes itself.
- **A test from the Mac.** While waiting for the tablet, a script acts as the tablet: you speak into
  the Mac's microphone and hear the answer.
- **It keeps listening even with another app on the screen.** A persistent notification shows it
  is there; the microphone stays open as long as the app is running.
- **It wakes up with its name.** It recognizes «Franco», «Franchino», «Frankino» right on the
  tablet, without sending anything to anyone until it hears it.
- **No need to call it again after an answer.** For a few seconds it listens even without the name,
  and when it asks «Lo faccio?» (shall I do it?) it waits for your «sì» or «no».
- **If you talk over it, it goes quiet.** Just call it by name while it is speaking, or tap the
  stop button.
- **The screen shows what Claude sends**: recipes, lists and the confirmation card with its buttons,
  drawn with Google's official A2UI component.
- **It is set up from the tablet.** The server address and the token are entered in the app's
  settings, not written in the code.

[1.0.0]: https://github.com/alessio-ragni/frankino/releases/tag/v1.0.0
