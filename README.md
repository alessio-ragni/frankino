# Frankino

A voice companion with a screen. You call it by name («Frankino», «Franco», «Franchino»), talk to
it while you cook or drive, and it gets things done with **Claude Code** and all the connectors you
already have (messages, mail, calendar, documents). Things that are easier to understand by looking
at them (a recipe, a list, a message before it is sent) it shows on the screen with **A2UI**,
Google's protocol for agent-generated interfaces.

```
Android tablet  ── voice (PCM) ──►  server  ── text ──►  Claude Code (Agent SDK)
  listens,      ◄── voice + A2UI ──  transcribes, speaks,  claude.ai connectors + MCP
  speaks, shows                      asks for confirmation «mostra» tool (A2UI)
```

## What you need

- **Your own Claude subscription.** The server runs Claude Code with *your* login: on the server
  you run `claude`, do `/login` once, and that's it. Frankino offers no login of its own, does not
  ask for your credentials and never touches them. It is meant for personal use.
- **An OpenAI key** (or ElevenLabs) to transcribe and speak: Claude does not take audio.
- **An Android tablet** and a private network between tablet and server (Tailscale recommended).
  The server must not be exposed to the internet.

## Starting the server

```bash
cd server
uv venv -p 3.11 .venv && uv pip install -p .venv/bin/python -e ".[dev,mac]"
cp ../.env.example .env        # fill in FRANKINO_TOKEN and OPENAI_API_KEY
.venv/bin/python -m frankino   # listens on :4390
.venv/bin/pytest               # tests
```

To try it without a tablet, from the Mac: `.venv/bin/python ../tools/prova_mac.py --token <gettone>`
(by voice) or with `--scrivi` (by text). `<gettone>` is the token, the value of `FRANKINO_TOKEN`.

## The Android app

It lives in `android/`. You need Java 17 and the Android SDK (platform 37.1); on a Mac with
Homebrew: `brew install openjdk@17 android-commandlinetools`, then
`sdkmanager "platform-tools" "platforms;android-37.1" "build-tools;36.0.0"`.

```bash
cd android
echo "sdk.dir=/opt/homebrew/share/android-commandlinetools" > local.properties
JAVA_HOME=/opt/homebrew/opt/openjdk@17 ./gradlew assembleDebug testDebugUnitTest
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

On first launch it asks for the microphone and notifications, then for the server address (its
Tailscale name, for example `mio-mac:4390`) and the token. It downloads the small Italian
[Vosk](https://alphacephei.com/vosk/models) model once (about 50 MB) for the wake word.

How it listens:
- **It waits for its name** («Franco», «Franchino», «Frankino»). It recognizes it on the tablet with
  a closed grammar: until it hears the name, nothing goes to the server.
- **Right after an answer** it listens for a few seconds even without the name, and while a
  confirmation is open it waits for your «sì» or «no» (yes or no).
- **If you call it while it is speaking** it goes quiet and listens to you. The talk
  button does the same by hand.
- The screen draws A2UI with the official Compose renderer (`androidx.a2ui`, alpha).

## How it works

The path of a question, what is kept and where, model and costs, connectors, the microphone switch
and how it differs from Claude, explained without code: [`docs/how-it-works.md`](docs/how-it-works.md).

## Deployment

Server on AWS inside a Tailscale network, tablet set up over adb, side key instead of Gemini: every
step is in [`docs/deployment.md`](docs/deployment.md), scripts in `deploy/aws/`.

## Outward actions

Every tool that is not clearly read-only asks for confirmation: the screen shows what it is about
to do, and you say «sì», «no» or «non chiedermelo più» (yes, no, don't ask me again), or use the
buttons. «Don't ask me again» applies to that one tool and can be withdrawn
(`POST /permessi/ritira?tool=…`).

## What stays on the server

The audio of what you say, for 30 days (then it is deleted, the text stays), the transcripts, the
exchanges and the permissions. All of it in `FRANKINO_DATA`, never in the repo. Recordings that
were not meant for Frankino (it woke up without anyone calling it) are deleted at once, audio and
text.

## Layout

- `server/` — FastAPI + Claude Agent SDK. Protocol with the tablet: [`docs/protocol.md`](docs/protocol.md).
- `android/` — the tablet app (Kotlin + Compose).
- `deploy/aws/` — the AWS machine: creation, first boot, remote commands.
- `tools/` — tools for testing (the Mac acting as a tablet, the wake word).

Changes are listed in [`CHANGELOG.md`](CHANGELOG.md).
