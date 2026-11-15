#!/bin/bash
# Runs a command on the Frankino machine through SSM (no open port, no SSH key) and prints its
# output. Examples:
#
#   AWS_PROFILE=<profile> deploy/aws/remoto.sh 'journalctl -u frankino -n 50 --no-pager'
#   AWS_PROFILE=<profile> deploy/aws/remoto.sh aggiorna     # git pull + restart
#   AWS_PROFILE=<profile> deploy/aws/remoto.sh segreti      # re-reads the secrets from SSM and restarts
#   AWS_PROFILE=<profile> deploy/aws/remoto.sh registro 6   # the journal: last 6 hours of questions, timings, tools
set -euo pipefail

: "${AWS_PROFILE:?imposta AWS_PROFILE}"
export AWS_REGION="${AWS_REGION:-eu-west-1}"
NAME="${FRANKINO_NAME:-frankino}"
CMD="${1:?which command?}"
HOURS="${2:-24}"

case "$CMD" in
  aggiorna)
    CMD='cd /opt/frankino && sudo -u frankino git pull --ff-only &&
      sudo -u frankino server/.venv/bin/pip install --quiet -e server &&
      systemctl restart frankino && sleep 3 && systemctl --no-pager status frankino | head -5' ;;
  registro)
    CMD="DATA=\$(grep ^FRANKINO_DATA= /etc/frankino/config | cut -d= -f2); cd /opt/frankino/server &&
      sudo -u frankino .venv/bin/python -m frankino.journal --db \$DATA/frankino.db --hours $HOURS" ;;
  segreti)
    CMD='systemctl restart frankino-secrets frankino && sleep 3 && systemctl --no-pager status frankino | head -5' ;;
esac

ID=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=$NAME" "Name=instance-state-name,Values=running" \
  --query 'Reservations[0].Instances[0].InstanceId' --output text)
[ "$ID" != "None" ] || { echo "the machine $NAME is not running"; exit 1; }

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
