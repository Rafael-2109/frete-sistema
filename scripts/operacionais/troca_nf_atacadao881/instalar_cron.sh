#!/usr/bin/env bash
# Instala (idempotente, preservando o crontab atual) a linha de cron da Troca NF Atacadao 881.
#
# USO:
#   sudo bash scripts/operacionais/troca_nf_atacadao881/instalar_cron.sh
#
# Roda diariamente 11:30 BRT: verifica se as NFs 146390/146608 foram revertidas e,
# quando estiverem 100% revertidas, devolve o saldo para CD/Indisponivel (lote MIGRACAO).
set -euo pipefail

USER_CRON=rafaelnascimento
MARK=troca_nf_atacadao881
LINE_COMMENT='# Troca NF Atacadao 881 — verifica reversao das NFs 146390/146608 e devolve ao CD/Indisponivel (diario 11:30 BRT)'
LINE_CRON='30 11 * * * cd /home/rafaelnascimento/projetos/frete_sistema && .venv/bin/python scripts/operacionais/troca_nf_atacadao881/verificar_reversao_e_devolver.py --confirmar >> /tmp/troca_nf_881.log 2>&1'

TMP=$(mktemp)
crontab -u "$USER_CRON" -l 2>/dev/null > "$TMP" || true

if grep -q "$MARK" "$TMP"; then
  echo "Linha ja existe no crontab de $USER_CRON — nada a fazer (idempotente)."
else
  printf '%s\n%s\n' "$LINE_COMMENT" "$LINE_CRON" >> "$TMP"
  crontab -u "$USER_CRON" "$TMP"
  echo "Linha instalada no crontab de $USER_CRON."
fi
rm -f "$TMP"

echo "--- crontab atual de $USER_CRON ---"
crontab -u "$USER_CRON" -l
