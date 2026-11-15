# How Frankino works

For anyone who wants to understand what happens when you talk to Frankino, without reading the
code. How to install it from scratch is in [`deployment.md`](deployment.md); the messages between
tablet and server are in [`protocol.md`](protocol.md).

## The states, and the one button

The circle in the middle of the screen shows what Frankino is doing, and it is the only button.

| What you see | State | Tapping the circle |
|---|---|---|
| Grey circle, red ring, crossed-out microphone | **Off**: the microphone is really closed | listens to one question, then closes again |
| Quiet circle that slowly breathes, with a play sign | **Waiting for its name** | listens right away, without the name |
| Blue, pulsing with your voice | **Listening** | you are done, it answers |
| Four coloured dots turning, with a soft two-note sound | **Thinking** | stops everything |
| Green, with moving bars | **Speaking** | stops everything |
| Amber | **Ringing** (a timer or a reminder) | stops the bell |

After an answer it keeps listening a few seconds without the name, so you can carry on; then it
goes back to waiting for its name. Saying «stop», «basta» or «grazie» ends the conversation at once.

The microphone switch is the small chip at the top left, the action in Frankino's notification, and
the «Frankino» tile in quick settings (the panel that slides down from the top). It stays as it is
even after a restart. With the microphone off, Android's green dot at the top goes away.

## The path of a question

1. **The tablet waits for the name.** A small recognizer, on the tablet, hears only a handful of
   words: the names (Franco, Franchino, Frankino, Franko) and the greetings that go before them.
   Until it hears the name, it sends nothing to anyone. When it does, it plays a short note.
2. **It records your sentence**, including the three seconds before, so the name is not lost. A
   pause of less than a second means you are done.
3. **The thinking sound starts at once**, so you know it heard you.
4. **The server transcribes** the recording with OpenAI (`gpt-4o-transcribe`), Italian or English.
5. **Second check.** If the transcribed sentence does not start with the name, the tablet got it
   wrong: the recording is thrown away at once, audio and text, and Frankino says nothing.
6. **Claude thinks.** The text goes to Claude Code, which runs on the server with your subscription,
   together with the date and time and the cards on the screen.
7. **It answers aloud while it is still thinking**, in one or two short sentences. The details go on
   a card. If nothing has been said after three seconds, it says «un attimo».

## Cards

The screen is a row of cards, one per topic: a recipe, tomorrow's events, the shopping list, the
alarms. Swipe left and right to move between them; scroll a card up and down to see all of it; close
it with its ✕ (or by saying so). A card is a topic that evolves: while you cook, «prossimo passo» or
«quanto pecorino?» stay on the recipe card, which updates in place. Under each card there are the
last answers on that topic, with your question small above each one. What has nothing to show goes
to the «Conversazione» card.

Cards are drawn with **A2UI**, Google's open format for interfaces written by an agent, by the
official Android renderer. For the common cases (events, recipes, lists, tables) Claude passes plain
data and the server writes the A2UI, which is faster and never breaks; for anything else Claude
writes the A2UI itself, and the server checks it before it reaches the tablet. Cards are kept on the
server and come back after a restart.

To try: «Franco, fammi vedere la carbonara per due» (carbonara for two), then «prossimo passo»
(next step); «Franco, cosa ho in calendario domani?» (what's on tomorrow).

## Alarms, timers, reminders, lists

- **Alarms** go on the tablet's Clock app, so they ring even if Frankino is down. The Clock app only
  takes an hour and a minute, so an alarm further ahead than the next time that hour comes round is
  rung by Frankino. Android lets no app delete another app's alarm: to cancel one, Frankino opens
  the Clock app and you remove it there.
- **Timers and reminders** ring from Frankino, with a bell and his voice, never over a conversation.
- **Lists**: «metti il latte nella spesa» (put milk on the shopping list), «ho preso il pane»
  (I bought the bread), «cosa c'è nella lista?».
- «Sveglie e promemoria» is a card that lists everything that is set.

When you ask for something it has no tool for (turning on lights, music), it says so and writes it
down, so the missing tools can be added.

## What is kept and where

| What | Where | For how long |
|---|---|---|
| Audio of the questions | on the server, in the data folder | 30 days, then it deletes itself |
| Every question: text, answer, timings, tools used, errors | the journal in the server database | until it is deleted |
| Recordings that were not meant for Frankino | only date, length and reason | audio and text disappear at once |
| Cards, alarms, timers, reminders, lists | the server database | cards until closed; the rest is never deleted, only marked as ended |
| Claude conversations | nowhere: Claude Code does not save them to disk | they start afresh after 10 quiet minutes |

The database has a nightly copy in a private archive on AWS. GitHub holds only the code: no audio,
no transcripts, no secrets.

## The journal

Every question leaves a row with why it started, how long each step took (transcription, first
word, first sound, total), which tools it called and with what, how long they took, whether they
failed, and whether it asked for confirmation. Discarded recordings, «stop», cards that failed to
draw and missing tools are written down too. To read it:

```bash
AWS_PROFILE=<profile> deploy/aws/remoto.sh registro 6     # the last 6 hours
```

or ask Claude in this repository «what did Frankino do this morning?».

## The brain, speed and cost

- **Model:** Claude Haiku 5.5, low effort, no extended thinking. For hard questions one line in the
  server configuration changes it (`FRANKINO_MODEL=claude-sonnet-5-5`).
- **Only the household connectors**: WhatsApp, Gmail, Google Calendar, Google Drive (and web
  search). Every connector adds its tool descriptions to every question, so the others are switched
  off for Frankino, and so are the tools of these four that a voice never needs. That took the
  request from about 290k tokens to about 40k. To add one: `FRANKINO_CONNECTORS` in the server
  configuration.
- **How long it takes**, measured on the server: a simple question gets its first word from Claude
  in about 1.2 s and the first sound in about 2 s; showing a card or using a tool, 3 to 4 s to the
  first sound; the calendar, which has to be read first, about 3.5 s with the «un attimo» covering
  the wait. The first question after a long pause is slower (about 3.5 s), because Claude has to
  read its instructions again. Anthropic has no real-time voice service today: the chain is
  transcription → Claude → voice, and each link has been trimmed.
- **Claude is part of the subscription** of whoever hosts the server: no extra cost per question.
  **OpenAI** (understanding and speaking) is paid per use, about two tenths of a cent per question.
  **The server** on AWS costs about $15 a month.

## Confirmations

Before any outward action (sending a message, creating an event, deleting a file) it shows what it
is about to do and asks «Lo faccio?» (shall I do it?). You answer «sì», «no» or «non chiedermelo
più» (yes, no, don't ask me again), by voice or with the buttons. Reading asks nothing, and neither
do Frankino's own tools (cards, alarms, lists).

## How it differs from Claude

- You talk to it and it answers aloud, hands free, with the details on cards.
- It always asks for confirmation before doing anything outward.
- It does not touch files or run commands.
- It does not remember past conversations and does not show up in your claude.ai history; the cards
  and lists are its memory of what is going on.

## Finding the app on the tablet

An app installed from the computer lands in the app list, not on the Home screen: swipe up from
the bottom and look for «Frankino», then press and hold it and drag it to the Home screen. The
service runs by itself anyway, with the persistent notification.
