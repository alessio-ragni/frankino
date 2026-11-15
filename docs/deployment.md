# Messa in opera — dal tablet nuovo a Frankino che risponde

Questa è la strada fatta la prima volta, passo per passo, con un Galaxy Tab A11 (Android 16, One UI
8.5, menu in inglese) e il server su AWS. Vale per qualunque tablet Android 11+ e qualunque macchina
Linux: cambiano solo i nomi dei menu.

## Com'è fatto

```
Tablet ──Tailscale (rete privata)──► macchina «frankino» su AWS (Ubuntu, ARM, t4g.small)
  app Android                           server Python + Claude Code (login dell'abbonamento)
  - parola d'avvio sul tablet           - SQLite e audio su disco, copia notturna su S3
  - voce in streaming                   - segreti in SSM Parameter Store
  - schede A2UI                                 │
                                                ▼
                         OpenAI (capire e parlare) · Claude (pensare) · connettori claude.ai
```

- **Nessuna porta aperta su internet.** Il tablet arriva al server solo dentro la rete Tailscale;
  i comandi alla macchina passano da AWS Systems Manager, senza chiavi SSH.
- **I segreti non stanno né nella repo né sul disco:** chiave OpenAI e gettone del tablet vivono in
  SSM Parameter Store e vengono letti a ogni avvio in una cartella che sparisce allo spegnimento.
- **Il database è un file SQLite.** Tutto passa da `server/frankino/store.py`: per passare a
  Postgres (Supabase o altro) si riscrive quel file e basta.
- **Costo:** la macchina `t4g.small` con 20 GB di disco costa circa 15 $ al mese; OpenAI pochi
  centesimi al giorno; Claude è dentro l'abbonamento.

## Cosa sa fare la v0

- Lo chiami per nome: «Frankino», «Franco», «Franchino», «Franko», anche con un saluto davanti
  («ehi», «hey», «hei», «ciao», «hi»). Il nome lo riconosce il tablet da solo: finché non lo sente,
  al server non parte niente. Il nome detto a metà frase («ho visto Franco») non lo sveglia, e se il
  tablet si sbaglia il server lo ricontrolla sulla trascrizione e butta tutto.
- Ha un interruttore del microfono (app, notifica, pannello rapido), come quello di Alexa.
- Capisce e risponde in italiano e in inglese.
- Tenendo premuto il tasto laterale si apre Frankino già in ascolto, al posto di Gemini.
- Ti risponde a voce mentre ancora pensa, e mostra sullo schermo ricette, liste e confronti (A2UI,
  renderer ufficiale di Android).
- Dopo una risposta ascolta ancora qualche secondo senza bisogno del nome.
- Prima di qualunque azione verso fuori (messaggi, mail, eventi) mostra cosa sta per fare e aspetta
  un «sì», un «no» o un «non chiedermelo più».
- Se lo chiami mentre parla, si zittisce e ti ascolta; c'è anche il pulsante «Zitto».

## 1. Il server su AWS

Serve la CLI di AWS con un profilo che possa creare EC2, IAM, S3 e parametri SSM.

```bash
export AWS_PROFILE=<profilo> AWS_REGION=eu-west-1

# segreti (il gettone lo inventi: il tablet lo userà per farsi riconoscere)
aws ssm put-parameter --name /frankino/OPENAI_API_KEY --type SecureString --value '<chiave OpenAI>'
aws ssm put-parameter --name /frankino/FRANKINO_TOKEN --type SecureString --value "$(openssl rand -hex 24)"

deploy/aws/crea.sh          # macchina, ruolo, gruppo di sicurezza senza ingressi, bucket del backup
```

In circa cinque minuti la macchina ha installato tutto da sola (`deploy/aws/user-data.sh`):
Python, il codice della repo in `/opt/frankino`, Claude Code, Tailscale, il servizio `frankino`
che riparte da solo, e la copia notturna del database su S3.

Poi due passi che fa **chi possiede gli account**, non uno script:

```bash
# Tailscale: stampa un link, lo apri e entri col tuo account
deploy/aws/remoto.sh '(nohup tailscale up --ssh --hostname=frankino >/tmp/ts.log 2>&1 &); sleep 8; cat /tmp/ts.log'

# Claude: login col proprio abbonamento (mai ANTHROPIC_API_KEY)
ssh -t frankino@frankino .local/bin/claude      # dentro: /login, poi /exit
```

Comandi di tutti i giorni:

```bash
deploy/aws/remoto.sh aggiorna                                      # git pull + riavvio
deploy/aws/remoto.sh segreti                                       # dopo aver cambiato un parametro SSM
deploy/aws/remoto.sh 'journalctl -u frankino -n 50 --no-pager'     # registro
```

Prova senza tablet, dal Mac nella stessa rete Tailscale:

```bash
cd server && .venv/bin/python ../tools/prova_mac.py --url ws://frankino:4390/ws --token <gettone> --scrivi
```

## 2. Il tablet (da fare a mano, una volta)

Android non lascia comandare un tablet da fuori finché non lo si permette dal tablet stesso.

1. **Settings → Security and privacy → Auto Blocker**: Off (blocca i comandi via USB).
2. **Settings → About tablet → Software information**: tocca 7 volte **Build number**.
3. **Settings → Developer options → USB debugging**: On.
4. Collega il cavo (un cavo dati: con uno solo-ricarica il computer non vede niente). Su «Use USB
   for» va bene **Transferring files**. Al messaggio **Allow USB debugging?** spunta **Always allow
   from this computer** e tocca **Allow**.

Da qui in poi il resto si fa dal computer.

## 3. Il tablet (dal computer, con adb)

```bash
cd android
JAVA_HOME=/opt/homebrew/opt/openjdk@17 ./gradlew assembleDebug
adb install -r -g app/build/outputs/apk/debug/app-debug.apk

P=dev.frankino.app
adb shell pm grant $P android.permission.RECORD_AUDIO
adb shell pm grant $P android.permission.POST_NOTIFICATIONS
adb shell dumpsys deviceidle whitelist +$P                 # niente risparmio batteria
adb shell cmd appops set $P RUN_ANY_IN_BACKGROUND allow
adb shell settings put global stay_on_while_plugged_in 7   # schermo acceso in carica

# Frankino assistente predefinito: tasto laterale tenuto premuto → Frankino, e Gemini esce di scena
adb shell cmd role add-role-holder android.app.role.ASSISTANT $P

# Il riquadro «Frankino» (interruttore del microfono) nel pannello rapido
adb shell cmd statusbar add-tile $P/.MicTile

# Tailscale sempre acceso, anche dopo un riavvio
adb shell settings put secure always_on_vpn_app com.tailscale.ipn
```

Tailscale si installa dal Play Store
(`adb shell am start -a android.intent.action.VIEW -p com.android.vending -d market://details?id=com.tailscale.ipn`);
il login lo fa il proprietario, sul tablet, con lo stesso account del server.

Indirizzo del server e gettone si scrivono in **Impostazioni** dentro l'app (`frankino:4390` e il
gettone). In alternativa, su un'app di debug, si possono mettere da adb nel file delle preferenze
con `run-as dev.frankino.app` (`shared_prefs/frankino.xml`, chiavi `server` e `token`).

Al primo avvio l'app scarica una volta il modello per la parola d'avvio (circa 50 MB).

Per vedere e comandare lo schermo del tablet dal computer: `brew install scrcpy && scrcpy`.

## 4. La prova

- «Ciao Franco, che ore sono?» con lo schermo su un'altra app: risponde a voce.
- «Franco, fammi vedere la carbonara per due»: la ricetta compare sullo schermo.
- Tasto laterale tenuto premuto: Frankino si apre già in ascolto.
- «Franco, metti un evento di prova domani alle dieci»: compare la scheda di conferma; un «no» non
  crea niente.

## Cosa si è imparato la prima volta

- **La parola d'avvio** è tarata con `tools/prova_parola.py` su frasi generate con le voci italiane
  del Mac: tutte le chiamate di prova lo svegliano, il nome detto a metà frase quasi mai.
  «Frankino» non è nel vocabolario del modello: lo si riconosce come «Franchino».
- **Eco:** subito dopo che Frankino ha parlato, il microfono sente ancora la sua voce. L'app scarta
  l'audio di prima e il primo istante, altrimenti al server torna indietro la sua stessa frase.
- **Da lontano** la voce arriva piano: il server la alza (fino a 8 volte) prima di trascriverla, e
  l'app considera parlato anche un livello più basso.
- **Il gettone** viaggia nell'indirizzo del websocket: il server lo toglie dai registri.
- **Falsi risvegli:** il primo giorno il riconoscitore del tablet si svegliava con i discorsi di
  casa, e dopo ogni risposta il seguito senza nome si portava dietro altre frasi. Da allora il
  server ricontrolla il nome sulla trascrizione vera, e il seguito è più corto e più esigente.
