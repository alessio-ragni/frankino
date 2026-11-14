# Changelog

## 14 novembre 2026 — Frankino gira davvero: tablet, server su AWS, tasto laterale

**Il tablet è arrivato e Frankino risponde a voce da lì. Il cervello non sta più sul Mac: vive su un server tutto suo, sempre acceso, in una rete privata.**

1. **Il server sta su AWS, sempre acceso.** Una macchina piccola (circa 15 $ al mese) raggiungibile solo dalla tua rete privata Tailscale: nessuna porta aperta su internet. Ogni notte copia il database in un archivio a parte.
2. **I segreti non stanno da nessuna parte su disco.** La chiave per la voce e il gettone del tablet si leggono a ogni avvio da un archivio protetto di AWS.
3. **Lo chiami anche con un saluto.** «Ehi Franko», «ciao Franchino», «hey Franco», «hi Franco», oltre al nome da solo. Il nome detto a metà frase («ho visto Franco») non lo sveglia più.
4. **Il tasto laterale apre Frankino, non Gemini.** Tenendolo premuto Frankino si apre già in ascolto; anche «Hey Google» non è più l'assistente.
5. **Non si risponde più da solo.** Subito dopo aver parlato il tablet sentiva ancora la sua voce e gliela rimandava: adesso quell'audio si scarta.
6. **Ti sente meglio da lontano.** La voce lontana viene alzata prima di essere trascritta, e l'app la riconosce come parlato anche quando arriva bassa.
7. **Il gettone non finisce nei registri del server.**
8. **C'è la guida passo passo** per rifare tutto da zero: `docs/messa-in-opera.md`.

## 13 novembre 2026 — L'app per il tablet, e Frankino è pubblico

**Frankino è su GitHub come progetto open source, e c'è la prima versione dell'app Android: pronta da installare sul tablet appena arriva.**

1. **Sta in ascolto anche con lo schermo su un'altra app.** Una notifica fissa dice che c'è; il microfono resta aperto finché l'app gira.
2. **Si sveglia col suo nome.** Riconosce «Franco», «Franchino», «Frankino» direttamente sul tablet, senza mandare niente a nessuno finché non lo sente.
3. **Dopo una risposta non serve richiamarlo.** Per qualche secondo ascolta anche senza nome, e quando chiede «Lo faccio?» aspetta il tuo «sì» o «no».
4. **Se gli parli sopra si zittisce.** Basta chiamarlo per nome mentre parla, oppure toccare «Zitto».
5. **Lo schermo mostra quello che manda Claude**: ricette, liste e la scheda di conferma con i pulsanti, disegnati col componente ufficiale di Google per A2UI.
6. **Si configura dal tablet.** Indirizzo del server e gettone si scrivono nelle impostazioni dell'app, non stanno nel codice.

## 12 novembre 2026 — Frankino nasce: il cervello, la voce intercambiabile e le conferme

**Un nuovo progetto, da zero, per un compagno vocale con schermo che si porta in giro. Stasera c'è il server: capisce, pensa con Claude Code e tutti i connettori, risponde a voce e disegna sullo schermo. Il tablet arriva domani.**

1. **Pensa con Claude Code e i tuoi connettori.** Usa il login del tuo abbonamento, quindi vede gli stessi servizi che hai già collegati (messaggi, posta, calendario, documenti) senza configurarli una seconda volta.
2. **Mostra le cose sullo schermo.** Quando una risposta si capisce meglio guardandola (una ricetta, una lista) la disegna con A2UI, e a voce dice solo il succo.
3. **Comincia a parlare alla prima frase.** Non aspetta la fine della risposta: ogni frase completa parte subito.
4. **Voce e trascrizione si cambiano con un'impostazione.** Si parte con OpenAI; ElevenLabs è già pronto.
5. **Chiede prima di fare cose verso fuori.** Mostra cosa sta per fare e aspetta un «sì», un «no» o un «non chiedermelo più», a voce o col pulsante. Nel dubbio chiede: passa senza domande solo quello che legge e basta.
6. **Gli audio restano 30 giorni, il testo per sempre.** Le dettature lunghe non si perdono, e dopo un mese l'audio si cancella da solo.
7. **Una prova dal Mac.** In attesa del tablet, uno script fa da tablet: parli al microfono del Mac e senti la risposta.
