#!/bin/bash
# Loop de resume resiliente a SSL drop (G016). Re-roda B->D ate todas transmitidas.
# Idempotente: B pula feitos, C acha invoices, D transmite SEFAZ; crash -> proxima iter retoma.
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
LOG=/tmp/fat_resume.log
contar() {
  python3 -c "
import sys,warnings; warnings.simplefilter('ignore'); sys.path.insert(0,'.')
from app import create_app
from app.odoo.models.ajuste_estoque_inventario import AjusteEstoqueInventario as A
app=create_app()
with app.app_context():
    print(A.query.filter_by(ciclo='FATURAMENTO_LF_2026_05_20').filter(A.fase_pipeline.in_(['F5c_LIBERADO','F5d_INVOICE_GERADA'])).count())
" 2>/dev/null | grep -E '^[0-9]+$' | tail -1
}

prev=99999
for i in $(seq 1 18); do
  echo "===== ITER $i $(date +%H:%M:%S) =====" >> "$LOG"
  timeout 900 python scripts/inventario_2026_05/fat_lf_05_executar_clean.py \
    --confirmar --confirmar-sefaz --apenas-etapa D >> "$LOG" 2>&1
  # ETAPA C separada (achar invoices p/ F5c) so se precisar
  rem=$(contar)
  echo "ITER $i: remaining(F5c+F5d)=$rem (prev=$prev)"
  [ "$rem" = "0" ] && { echo "TUDO TRANSMITIDO"; break; }
  if [ "$rem" = "$prev" ]; then
    # sem progresso em D -> rodar C p/ achar invoices das F5c, depois continua
    echo "sem progresso em D; rodando ETAPA C p/ resolver F5c..."
    timeout 900 python scripts/inventario_2026_05/fat_lf_05_executar_clean.py \
      --confirmar --apenas-etapa C >> "$LOG" 2>&1
    rem2=$(contar)
    echo "ITER $i pos-C: remaining=$rem2"
    [ "$rem2" = "$prev" ] && { echo "sem progresso apos C; parando"; break; }
    prev=$rem2
  else
    prev=$rem
  fi
done
echo "RESUME LOOP FIM remaining=$(contar)"
