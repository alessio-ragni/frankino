#!/bin/bash
# Primo avvio della macchina Frankino su AWS (Ubuntu 24.04, ARM). Lo lancia AWS una volta sola.
# Qui dentro non c'è nessun segreto: chiave OpenAI e gettone si leggono da SSM a ogni avvio.
# crea.sh sostituisce __REPO__, __BUCKET__ e __PARAMS__ prima di passarlo ad AWS.
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

REPO="__REPO__"
BUCKET="__BUCKET__"
PARAMS="__PARAMS__"

apt-get update
apt-get install -y python3 python3-venv python3-pip git sqlite3 curl unzip

# AWS CLI v2 (serve per leggere i segreti e copiare il backup)
curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o /tmp/awscli.zip
unzip -q /tmp/awscli.zip -d /tmp && /tmp/aws/install && rm -rf /tmp/aws /tmp/awscli.zip

# Tailscale: l'unica strada per arrivare qui. Il login lo fa chi possiede la rete.
curl -fsSL https://tailscale.com/install.sh | sh

# Utente di servizio e cartelle
id frankino >/dev/null 2>&1 || useradd --create-home --shell /bin/bash frankino
install -d -o frankino -g frankino /var/lib/frankino /opt/frankino
install -d -m 750 -o root -g frankino /etc/frankino

# Codice
sudo -u frankino git clone "$REPO" /opt/frankino
sudo -u frankino python3 -m venv /opt/frankino/server/.venv
sudo -u frankino /opt/frankino/server/.venv/bin/pip install --quiet --upgrade pip
sudo -u frankino /opt/frankino/server/.venv/bin/pip install --quiet -e /opt/frankino/server

# Claude Code per l'utente di servizio: il /login lo fa il proprietario dell'abbonamento.
sudo -u frankino bash -c 'curl -fsSL https://claude.ai/install.sh | bash'

# Impostazioni non segrete
cat >/etc/frankino/config <<EOF
FRANKINO_DATA=/var/lib/frankino
FRANKINO_HOST=0.0.0.0
FRANKINO_PORT=4390
FRANKINO_TZ=Europe/Rome
FRANKINO_MODEL=claude-haiku-5-5
FRANKINO_EFFORT=low
FRANKINO_STT=openai
FRANKINO_TTS=openai
FRANKINO_OPENAI_VOICE=ash
EOF
echo "$BUCKET" >/etc/frankino/backup-bucket
echo "$PARAMS" >/etc/frankino/params

# Segreti da SSM a ogni avvio, solo in memoria (/run sparisce allo spegnimento)
cat >/usr/local/bin/frankino-secrets <<'EOF'
#!/bin/bash
set -euo pipefail
PARAMS=$(cat /etc/frankino/params)
TOKEN=$(curl -s -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 60')
REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)
install -d -m 750 -o root -g frankino /run/frankino
umask 027
aws ssm get-parameters-by-path --region "$REGION" --path "$PARAMS" --with-decryption \
  --query 'Parameters[].[Name,Value]' --output text \
  | awk -F'\t' '{n=$1; sub(".*/","",n); print n"="$2}' >/run/frankino/secrets
chgrp frankino /run/frankino/secrets
EOF
chmod 755 /usr/local/bin/frankino-secrets

cat >/etc/systemd/system/frankino-secrets.service <<'EOF'
[Unit]
Description=Frankino: segreti da SSM
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/frankino-secrets
EOF

cat >/etc/systemd/system/frankino.service <<'EOF'
[Unit]
Description=Frankino
Requires=frankino-secrets.service
After=frankino-secrets.service tailscaled.service

[Service]
User=frankino
WorkingDirectory=/opt/frankino/server
EnvironmentFile=/etc/frankino/config
EnvironmentFile=/run/frankino/secrets
Environment=PATH=/home/frankino/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/opt/frankino/server/.venv/bin/python -m frankino
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Copia notturna del database su S3: una per giorno della settimana, si sovrascrive.
cat >/usr/local/bin/frankino-backup <<'EOF'
#!/bin/bash
set -euo pipefail
DB=/var/lib/frankino/frankino.db
[ -f "$DB" ] || exit 0
OUT=$(mktemp --suffix=.db)
sqlite3 "$DB" ".backup '$OUT'"
aws s3 cp --quiet "$OUT" "s3://$(cat /etc/frankino/backup-bucket)/frankino-$(date +%u).db"
rm -f "$OUT"
EOF
chmod 755 /usr/local/bin/frankino-backup

cat >/etc/systemd/system/frankino-backup.service <<'EOF'
[Unit]
Description=Frankino: copia del database su S3

[Service]
Type=oneshot
ExecStart=/usr/local/bin/frankino-backup
EOF

cat >/etc/systemd/system/frankino-backup.timer <<'EOF'
[Unit]
Description=Frankino: copia notturna del database

[Timer]
OnCalendar=*-*-* 03:30:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable frankino.service frankino-backup.timer
systemctl start frankino-backup.timer
# Frankino parte, ma risponde davvero solo dopo il /login a Claude e con i segreti in SSM.
systemctl start frankino.service || true
touch /var/lib/frankino/.pronto
