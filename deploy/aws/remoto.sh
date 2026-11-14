#!/bin/bash
# Lancia un comando sulla macchina Frankino via SSM (nessuna porta aperta, nessuna chiave SSH)
# e ne stampa l'uscita. Esempi:
#
#   AWS_PROFILE=<profilo> deploy/aws/remoto.sh 'journalctl -u frankino -n 50 --no-pager'
#   AWS_PROFILE=<profilo> deploy/aws/remoto.sh aggiorna     # git pull + riavvio
#   AWS_PROFILE=<profilo> deploy/aws/remoto.sh segreti      # rilegge i segreti da SSM e riavvia
set -euo pipefail

: "${AWS_PROFILE:?imposta AWS_PROFILE}"
export AWS_REGION="${AWS_REGION:-eu-west-1}"
NAME="${FRANKINO_NAME:-frankino}"
CMD="${1:?quale comando?}"

case "$CMD" in
  aggiorna)
    CMD='cd /opt/frankino && sudo -u frankino git pull --ff-only &&
      sudo -u frankino server/.venv/bin/pip install --quiet -e server &&
      systemctl restart frankino && sleep 3 && systemctl --no-pager status frankino | head -5' ;;
  segreti)
    CMD='systemctl restart frankino-secrets frankino && sleep 3 && systemctl --no-pager status frankino | head -5' ;;
esac

ID=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=$NAME" "Name=instance-state-name,Values=running" \
  --query 'Reservations[0].Instances[0].InstanceId' --output text)
[ "$ID" != "None" ] || { echo "la macchina $NAME non è accesa"; exit 1; }

PARAMS=$(python3 -c 'import json,sys; print(json.dumps({"commands":[sys.argv[1]]}))' "$CMD")
CID=$(aws ssm send-command --instance-ids "$ID" --document-name AWS-RunShellScript \
  --parameters "$PARAMS" --timeout-seconds 600 --query Command.CommandId --output text)
while true; do
  sleep 2
  STATUS=$(aws ssm get-command-invocation --command-id "$CID" --instance-id "$ID" \
    --query Status --output text 2>/dev/null || echo Pending)
  case "$STATUS" in Pending|InProgress|Delayed) continue ;; esac
  break
done
aws ssm get-command-invocation --command-id "$CID" --instance-id "$ID" \
  --query '[StandardOutputContent,StandardErrorContent]' --output text
[ "$STATUS" = "Success" ]
