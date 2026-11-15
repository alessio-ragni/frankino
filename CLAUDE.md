# Frankino — guide for Claude

A voice companion with a screen: an Android tablet in front, a Python server behind, Claude Code
(Agent SDK, logged in with the subscription of whoever hosts it) as the brain, A2UI for the screen.
Start simple and add things as they are needed: no architecture ahead of time.

## Rules

- **Public repo.** Never secrets, audio, transcripts, real names or real numbers: not in the code,
  not in the tests, not in the examples. `.env` and `FRANKINO_DATA` stay outside the repo.
- **Never `ANTHROPIC_API_KEY`.** The server uses the subscription login; if the key is set, the CLI
  prefers it and bills per use.
- **Frankino offers no Claude.ai login and never touches credentials.** Everyone does `/login`
  themselves.
- **Outward actions go through the gate** (`server/frankino/confirm.py`, PreToolUse hook). Cautious
  by design: it asks about everything except what is clearly read-only. Do not replace it with
  `can_use_tool`: with user settings in «auto» mode, it is never called.
- **Voice and transcription are interchangeable** (`server/frankino/speech/`): a new service is one
  file and one line in the dictionaries, never a scattered `if`.
- **The screen speaks A2UI** (`server/frankino/a2ui.py`), version from `FRANKINO_A2UI_VERSION`.
- The protocol with the tablet is in `docs/protocol.md`: if you change it, change the document.
- How Frankino works, for people who do not read code, is in `docs/how-it-works.md`; the setup
  steps are in `docs/deployment.md`. Keep them in line with what the code does.

## Language

- **Everything in the repo is written in English**: names in the code, comments, docstrings, docs,
  changelog, commit messages.
- **The Android app's on-screen strings** have English defaults in `res/values/strings.xml` and an
  Italian translation in `res/values-it/strings.xml`. A new string goes in both.
- **What Frankino says aloud follows the language the person speaks.**

## Commands

```bash
cd server
.venv/bin/pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/python -m frankino
.venv/bin/python ../tools/prova_mac.py --token <gettone> [--scrivi]
```

Server on AWS (the owner's account, profile and region from the environment; steps in
`docs/deployment.md`):

```bash
AWS_PROFILE=<profilo> deploy/aws/remoto.sh aggiorna          # after the push: git pull + restart
AWS_PROFILE=<profilo> deploy/aws/remoto.sh 'journalctl -u frankino -n 50 --no-pager'
```

Android app (Java 17 from Homebrew, SDK in `/opt/homebrew/share/android-commandlinetools`):

```bash
cd android
JAVA_HOME=/opt/homebrew/opt/openjdk@17 ./gradlew assembleDebug testDebugUnitTest lintDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

## Changelog

`CHANGELOG.md` at the repo root, updated at every commit. Format:
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) with
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). New entries go under `## [Unreleased]`
until a version is cut. Written in English for a reader who does not read code: say what changes
for the person using Frankino, not which functions changed.
