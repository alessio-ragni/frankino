# How Frankino works

For anyone who wants to understand what happens when you talk to Frankino, without reading the
code. How to install it from scratch is in [`deployment.md`](deployment.md); the messages between
tablet and server are in [`protocol.md`](protocol.md).

## The path of a question

1. **The tablet waits for the name.** A small recognizer, on the tablet, hears only a handful of
   words: the names (Franco, Franchino, Frankino, Franko) and the greetings that go before them.
   Until it hears the name, it sends nothing to anyone.
2. **Once it hears the name, it records** your sentence, including the three seconds before, so the
   name is not lost. It stops when you stop talking.
3. **The server transcribes** the recording with OpenAI (`gpt-4o-transcribe`). It recognizes
   Italian and English by itself.
4. **Second check.** If the transcribed sentence does not start with the name, the tablet got it
   wrong. The recording is thrown away at once, audio and text, and Frankino says nothing.
5. **Claude thinks.** The text goes to Claude Code, which runs on the server with your
   subscription. It can search the web, use your claude.ai connectors and draw on the screen.
6. **It answers aloud while it is still thinking.** Each sentence, once ready, is read out by
   OpenAI (`gpt-4o-mini-tts`, voice «ash») and reaches the tablet in small pieces.
7. **For a few seconds it listens without the name**, so you can carry on the conversation. If in
   those seconds it hears its own voice, or people talking to each other, it throws that away and
   does not answer.

## The microphone switch

Like the button on Alexa: when it is off, the microphone is really closed, and Android's green dot
at the top goes away. You control it from three places:

- the big button at the top of the app;
- Frankino's persistent notification, with an action to turn the microphone off or back on;
- the «Frankino» tile in quick settings, the panel that slides down from the top.

It stays as it is even after a restart. With the microphone off, the talk button or the side key
open it for a single question, then it closes again.

## What is kept and where

| What | Where | For how long |
|---|---|---|
| Audio of the questions | on the server, in the data folder | 30 days, then it deletes itself |
| Text of the questions and answers | database on the server, nightly copy to a private archive on AWS | until it is deleted |
| Recordings that were not meant for Frankino | only date, length and reason | audio and text disappear at once |
| Claude conversations | nowhere: Claude Code does not save them to disk | until the server restarts |

GitHub holds only the code: no audio, no transcripts, no secrets.

## The brain and what it costs

- **Model:** Claude Haiku 5.5 with little reasoning, chosen to answer quickly, which matters more
  than anything when you talk. For hard questions you change one line in the server configuration
  (`FRANKINO_MODEL=claude-sonnet-5-5`, or `claude-opus-5-5`, and `FRANKINO_EFFORT`).
- **Claude is part of the subscription** of whoever hosts the server: no pay-per-use key, no extra
  cost per question. The model only changes how much of the subscription's limits you use: Haiku
  much less than Sonnet.
- **OpenAI** (understanding and speaking) is paid per use: about two tenths of a cent per question.
- **The server** on AWS costs about $15 a month, always on.

## The connectors

Frankino sees the same connectors you have on claude.ai: WhatsApp, Gmail, Google Calendar, Google
Drive and the others linked to your account. If a connector asks to be reconnected, you do it on
claude.ai and Frankino sees it at the next restart.

Before any outward action (sending a message, creating an event, deleting a file) it shows what it
is about to do and asks «Lo faccio?» (shall I do it?). You answer «sì», «no» or «non chiedermelo
più» (yes, no, don't ask me again), by voice or with the buttons. Reading, on the other hand, asks
nothing.

## How it differs from Claude

- You talk to it and it answers aloud, hands free.
- It shows recipes, lists and comparisons on the screen instead of writing them in a chat.
- It always asks for confirmation before doing anything outward.
- It does not touch files or run commands: it can only search, read pages, use the connectors and
  draw on the screen.
- It does not remember past conversations and does not show up in your claude.ai history.

## The screen (A2UI)

Claude has a tool, «mostra» (show), with which it describes a card in the open A2UI format. The
tablet draws it with Google's official Android component. To try it:

- «Franco, fammi vedere la carbonara per due» (show me carbonara for two);
- «Franco, mostrami la lista della spesa per una pizza» (show me the shopping list for a pizza);
- «Franco, confrontami tre robot aspirapolvere» (compare three robot vacuums for me).

## What you can build on top

Anything Claude can do with your connectors becomes something you can ask for by voice: reading
the day's mail, adding an event, sending a WhatsApp after seeing it on the screen. There are four
natural additions:

- new connectors on claude.ai, which Frankino sees right away;
- new cards on the screen (timers, lists you can tick off, photos);
- a memory of its own, which it does not have today;
- different voices, because the voice service can be changed without touching the rest.

## Finding the app on the tablet

An app installed from the computer does not land on the Home screen but in the app list: swipe up
from the bottom and look for «Frankino». To have it on the Home screen, press and hold it and drag
it there. The service runs by itself anyway, even without opening it, with the persistent
notification.
