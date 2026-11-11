#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if docker compose version >/dev/null 2>&1; then
  compose=(docker compose)
elif [[ -x tools/docker-compose ]]; then
  compose=(tools/docker-compose)
else
  echo 'Instala Docker Compose desde https://docs.docker.com/compose/install/'
  exit 1
fi
python3 init_env.py
mkdir -p evidence trivy tmp-terraform tmp-trivy cache-trivy zap-home tmp-zap
chmod 777 zap-home tmp-zap
"${compose[@]}" up -d localstack
"${compose[@]}" run --rm terraform init -no-color > evidence/terraform-init.log 2>&1
"${compose[@]}" run --rm terraform fmt -check -no-color > evidence/terraform-fmt.log 2>&1
"${compose[@]}" run --rm terraform validate -no-color > evidence/terraform-validate.log 2>&1
"${compose[@]}" run --rm terraform apply -auto-approve -no-color > evidence/terraform-apply.log 2>&1
python3 verify_s3.py > evidence/s3-validation.log 2>&1
python3 verify_iam.py > evidence/iam-validation.log 2>&1
"${compose[@]}" build api > evidence/docker-build-hardened.log 2>&1
docker build -f api/Dockerfile.node18 -t actividad3-api:node18 api > evidence/docker-build-node18.log 2>&1
docker save actividad3-api:node18 -o trivy/api-node18.tar
"${compose[@]}" run --rm --no-deps trivy image --scanners vuln --format json --output /reports/api-node18.json --input /reports/api-node18.tar
"${compose[@]}" up -d api zap
for version in 14 18; do
  "${compose[@]}" run --rm --no-deps trivy image --scanners vuln --platform linux/arm64 --format json --output "/reports/node${version}.json" "node:${version}"
done
"${compose[@]}" run --rm --no-deps trivy image --scanners vuln --platform linux/arm64 --format json --output /reports/node24-alpine.json node:24-alpine
docker save actividad3-api:secure -o trivy/api-secure.tar
"${compose[@]}" run --rm --no-deps trivy image --scanners vuln --format json --output /reports/api-secure.json --input /reports/api-secure.tar
python3 run_api_tests.py > evidence/api-tests.log 2>&1
python3 run_zap_scan.py > evidence/zap-scan.log 2>&1
# Repeat the negative tests after the authenticated scan removes its header rule.
python3 run_api_tests.py > evidence/api-tests.log 2>&1
"${compose[@]}" run --rm terraform plan -detailed-exitcode -no-color > evidence/terraform-plan-final.log 2>&1
echo 'Ejecución finalizada. Revisa los hallazgos en evidence/. S3 no valida el bloqueo efectivo en la edición Community.'
