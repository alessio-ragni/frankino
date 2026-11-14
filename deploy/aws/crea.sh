#!/bin/bash
# Crea su AWS tutto quello che serve a Frankino: una macchina piccola senza porte aperte,
# il ruolo per leggere i segreti, il bucket del backup. Si lancia una volta, dal proprio computer:
#
#   AWS_PROFILE=<profilo> deploy/aws/crea.sh
#
# Prima mettere i segreti in SSM (vedi docs/messa-in-opera.md). Rilanciarlo non duplica niente:
# se la macchina esiste già si ferma.
set -euo pipefail

: "${AWS_PROFILE:?imposta AWS_PROFILE}"
export AWS_REGION="${AWS_REGION:-eu-west-1}"
NAME="${FRANKINO_NAME:-frankino}"
TYPE="${FRANKINO_INSTANCE_TYPE:-t4g.small}"
REPO="${FRANKINO_REPO:-https://github.com/alessio-ragni/frankino.git}"
PARAMS="/$NAME/"
HERE="$(cd "$(dirname "$0")" && pwd)"

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
BUCKET="$NAME-backup-$ACCOUNT-$AWS_REGION"

existing=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=$NAME" "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query 'Reservations[].Instances[].InstanceId' --output text)
if [ -n "$existing" ]; then
  echo "La macchina $NAME esiste già: $existing"
  exit 0
fi

echo "› bucket per il backup: $BUCKET"
if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  aws s3api create-bucket --bucket "$BUCKET" \
    --create-bucket-configuration LocationConstraint="$AWS_REGION" >/dev/null
  aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
fi

echo "› ruolo della macchina"
ROLE="$NAME-server"
if ! aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE" --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]
  }' >/dev/null
  aws iam attach-role-policy --role-name "$ROLE" \
    --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
  aws iam create-instance-profile --instance-profile-name "$ROLE" >/dev/null
  aws iam add-role-to-instance-profile --instance-profile-name "$ROLE" --role-name "$ROLE"
fi
aws iam put-role-policy --role-name "$ROLE" --policy-name "$NAME-segreti-e-backup" --policy-document "{
  \"Version\":\"2012-10-17\",
  \"Statement\":[
    {\"Effect\":\"Allow\",\"Action\":[\"ssm:GetParametersByPath\",\"ssm:GetParameters\",\"ssm:GetParameter\"],
     \"Resource\":\"arn:aws:ssm:$AWS_REGION:$ACCOUNT:parameter/$NAME/*\"},
    {\"Effect\":\"Allow\",\"Action\":\"ssm:GetParametersByPath\",
     \"Resource\":\"arn:aws:ssm:$AWS_REGION:$ACCOUNT:parameter/$NAME\"},
    {\"Effect\":\"Allow\",\"Action\":\"s3:PutObject\",\"Resource\":\"arn:aws:s3:::$BUCKET/*\"}
  ]
}"

echo "› gruppo di sicurezza senza porte aperte"
VPC=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
SG=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$NAME" "Name=vpc-id,Values=$VPC" \
  --query 'SecurityGroups[0].GroupId' --output text)
if [ "$SG" = "None" ]; then
  SG=$(aws ec2 create-security-group --group-name "$NAME" --vpc-id "$VPC" \
    --description "Frankino: nessun ingresso, si arriva solo via Tailscale" --query GroupId --output text)
fi

AMI=$(aws ssm get-parameter \
  --name /aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id \
  --query Parameter.Value --output text)

USERDATA=$(mktemp)
sed -e "s|__REPO__|$REPO|" -e "s|__BUCKET__|$BUCKET|" -e "s|__PARAMS__|$PARAMS|" \
  "$HERE/user-data.sh" >"$USERDATA"

echo "› macchina $TYPE ($AMI)"
# Il profilo appena creato impiega qualche secondo a essere visibile a EC2.
for i in 1 2 3 4 5 6; do
  if ID=$(aws ec2 run-instances --image-id "$AMI" --instance-type "$TYPE" \
    --iam-instance-profile Name="$ROLE" --security-group-ids "$SG" \
    --metadata-options HttpTokens=required,HttpEndpoint=enabled \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":20,"VolumeType":"gp3","Encrypted":true}}]' \
    --user-data "file://$USERDATA" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NAME}]" \
    --query 'Instances[0].InstanceId' --output text 2>/dev/null); then
    break
  fi
  sleep 10
done
rm -f "$USERDATA"
[ -n "${ID:-}" ] || { echo "non sono riuscito a creare la macchina"; exit 1; }
echo "Creata: $ID. Fra 5 minuti circa è pronta: poi deploy/aws/tailscale.sh"
