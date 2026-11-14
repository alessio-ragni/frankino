# Come funziona Frankino

Per chi vuole capire cosa succede quando parli a Frankino, senza leggere il codice. Come si installa
da zero sta in [`messa-in-opera.md`](messa-in-opera.md); i messaggi fra tablet e server in
[`protocollo.md`](protocollo.md).

## Il giro di una domanda

1. **Il tablet aspetta il nome.** Un riconoscitore piccolo, sul tablet, sente solo una manciata di
   parole: i nomi (Franco, Franchino, Frankino, Franko) e i saluti che ci vanno davanti. Finché non
   sente il nome non manda niente a nessuno.
2. **Sentito il nome, registra** la tua frase, compresi i tre secondi prima, così il nome non si
   perde. Smette quando smetti di parlare.
3. **Il server trascrive** la registrazione con OpenAI (`gpt-4o-transcribe`). Riconosce da solo
   italiano e inglese.
4. **Secondo controllo.** Se la frase trascritta non comincia col nome, il tablet si era sbagliato.
   La registrazione si butta subito, audio e testo, e Frankino non dice niente.
5. **Claude pensa.** Il testo va a Claude Code, che gira sul server col tuo abbonamento. Può
   cercare sul web, usare i tuoi connettori di claude.ai e disegnare sullo schermo.
6. **Risponde a voce mentre ancora pensa.** Ogni frase pronta viene letta da OpenAI
   (`gpt-4o-mini-tts`, voce «ash») e arriva al tablet a pezzetti.
7. **Per qualche secondo ascolta senza nome**, così puoi continuare il discorso. Se in quei secondi
   sente la sua stessa voce, o gente che parla fra sé, la butta e non risponde.

## L'interruttore del microfono

Come il tasto di Alexa: quando è spento il microfono è chiuso davvero, e il pallino verde di Android
in alto sparisce. Si comanda da tre posti:

- il pulsante grande in alto nell'app;
- la notifica fissa di Frankino, con «Spegni microfono» o «Riaccendi microfono»;
- il riquadro «Frankino» nel pannello rapido, la tendina che scende dall'alto.

Resta com'è anche dopo un riavvio. A microfono spento, il pulsante «Parla» o il tasto laterale lo
aprono per una domanda sola, poi si richiude.

## Cosa resta e dove

| Cosa | Dove | Per quanto |
|---|---|---|
| Audio delle domande | sul server, cartella dei dati | 30 giorni, poi si cancella da solo |
| Testo delle domande e delle risposte | database sul server, copia notturna in un archivio privato su AWS | finché non si cancella |
| Registrazioni che non erano per Frankino | solo data, durata e motivo | l'audio e il testo spariscono subito |
| Conversazioni di Claude | da nessuna parte: Claude Code non le salva su disco | finché il server non si riavvia |

Su GitHub c'è solo il codice: niente audio, niente trascrizioni, niente segreti.

## Il cervello e quanto costa

- **Modello:** Claude Haiku 5.5 con poco ragionamento, scelto per rispondere in fretta, che a voce
  conta più di tutto. Per domande difficili si cambia con una riga nella configurazione del server
  (`FRANKINO_MODEL=claude-sonnet-5-5`, oppure `claude-opus-5-5`, e `FRANKINO_EFFORT`).
- **Claude è dentro l'abbonamento** di chi ospita il server: nessuna chiave a consumo, nessun costo
  in più per domanda. Il modello cambia solo quanto si consuma dei limiti dell'abbonamento: Haiku
  molto meno di Sonnet.
- **OpenAI** (capire e parlare) si paga a consumo: circa due decimi di centesimo per domanda.
- **Il server** su AWS costa circa 15 $ al mese, sempre acceso.

## I connettori

Frankino vede gli stessi connettori che hai su claude.ai: WhatsApp, Gmail, Google Calendar, Google
Drive e gli altri collegati al tuo account. Se un connettore chiede di essere ricollegato, lo si fa
su claude.ai e Frankino lo vede al riavvio successivo.

Prima di qualunque azione verso fuori (mandare un messaggio, creare un evento, cancellare un file)
mostra cosa sta per fare e chiede «Lo faccio?». Rispondi «sì», «no» o «non chiedermelo più», a
voce o coi pulsanti. Leggere invece non chiede niente.

## Cosa cambia rispetto a Claude

- Gli parli e ti risponde a voce, a mani libere.
- Mostra sullo schermo ricette, liste e confronti invece di scriverli in chat.
- Chiede sempre conferma prima di fare qualcosa verso fuori.
- Non tocca file e non lancia comandi: può solo cercare, leggere pagine, usare i connettori e
  disegnare sullo schermo.
- Non ricorda le conversazioni passate e non compare nella cronologia di claude.ai.

## Lo schermo (A2UI)

Claude ha uno strumento, «mostra», con cui descrive una scheda nel formato aperto A2UI. Il tablet la
disegna col componente ufficiale di Google per Android. Per provarlo:

- «Franco, fammi vedere la carbonara per due»;
- «Franco, mostrami la lista della spesa per una pizza»;
- «Franco, confrontami tre robot aspirapolvere».

## Cosa ci si può costruire sopra

Tutto quello che Claude sa fare con i tuoi connettori diventa una cosa da chiedere a voce: leggere
la posta del giorno, mettere un evento, mandare un WhatsApp dopo averlo visto sullo schermo. Le
aggiunte naturali sono quattro:

- nuovi connettori su claude.ai, che Frankino vede subito;
- schede nuove sullo schermo (timer, liste che si spuntano, foto);
- una memoria sua, che oggi non c'è;
- voci diverse, perché il servizio della voce si cambia senza toccare il resto.

## Trovare l'app sul tablet

L'app installata dal computer non finisce sulla schermata Home ma nell'elenco delle app: scorri
dal basso verso l'alto e cerca «Frankino». Per averla sulla Home tienila premuta e trascinala. Il
servizio gira comunque da solo, anche senza aprirla, con la notifica fissa.
