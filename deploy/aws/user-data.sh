#!/bin/bash
# First boot of the Frankino machine on AWS (Ubuntu 24.04, ARM). AWS runs it only once.
# No secrets in here: the OpenAI key and the token are read from SSM at every boot.
# crea.sh replaces __REPO__, __BUCKET__ and __PARAMS__ before handing it to AWS.
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

REPO="__REPO__"
BUCKET="__BUCKET__"
PARAMS="__PARAMS__"

apt-get update
apt-get install -y python3 python3-venv python3-pip git sqlite3 curl unzip

# AWS CLI v2 (needed to read the secrets and copy the backup)
curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o /tmp/awscli.zip
unzip -q /tmp/awscli.zip -d /tmp && /tmp/aws/install && rm -rf /tmp/aws /tmp/awscli.zip

# Tailscale: the only way in. The network owner does the login.
curl -fsSL https://tailscale.com/install.sh | sh

# Service user and directories
id frankino >/dev/null 2>&1 || useradd --create-home --shell /bin/bash frankino
install -d -o frankino -g frankino /var/lib/frankino /opt/frankino
install -d -m 750 -o root -g frankino /etc/frankino

# Code
sudo -u frankino git clone "$REPO" /opt/frankino
sudo -u frankino python3 -m venv /opt/frankino/server/.venv
sudo -u frankino /opt/frankino/server/.venv/bin/pip install --quiet --upgrade pip
sudo -u frankino /opt/frankino/server/.venv/bin/pip install --quiet -e /opt/frankino/server

# Claude Code for the service user: the subscription owner does the /login.
sudo -u frankino bash -c 'curl -fsSL https://claude.ai/install.sh | bash'

# Non-secret settings
cat >/etc/frankino/config <<EOF
FRANKINO_DATA=/var/lib/frankino
FRANKINO_HOST=0.0.0.0
FRANKINO_PORT=4390
FRANKINO_TZ=Europe/Rome
FRANKINO_MODEL=claude-haiku-5-5
FRANKINO_EFFORT=low
FRANKINO_LANG=it
FRANKINO_CONNECTORS=WhatsApp,Gmail,Google Calendar,Google Drive
FRANKINO_STT=openai
FRANKINO_TTS=openai
FRANKINO_OPENAI_VOICE=ash
EOF
echo "$BUCKET" >/etc/frankino/backup-bucket
echo "$PARAMS" >/etc/frankino/params

# Secrets from SSM at every boot, in memory only (/run is wiped at shutdown)
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
Description=Frankino: secrets from SSM
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

# Nightly copy of the database to S3: one per weekday, overwritten each week.
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
Description=Frankino: database copy to S3

[Service]
Type=oneshot
ExecStart=/usr/local/bin/frankino-backup
EOF

cat >/etc/systemd/system/frankino-backup.timer <<'EOF'
[Unit]
Description=Frankino: nightly database copy

[Timer]
OnCalendar=*-*-* 03:30:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable frankino.service frankino-backup.timer
systemctl start frankino-backup.timer
# Frankino starts, but it really answers only after the Claude /login and with the secrets in SSM.
systemctl start frankino.service || true
touch /var/lib/frankino/.pronto
