#!/bin/bash
# Loop de resume da ENTRADA (E + F), resiliente a hang do robo CIEL IT (post invoice entrada).
# ETAPA E (PERDA/DEV LF->FB) e ETAPA F (INDUSTR FB->LF) das NFs F5e_SEFAZ_OK.
# Timeout/iteracao mata hang; idempotencia (RecebimentoLf/origin) retoma por resume.
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
LOG=/tmp/fat_entrada.log

contar_e() {  # ajustes SEFAZ_OK de PERDA/DEV ainda SEM RecebimentoLf (precisam ETAPA E)
  python3 -c "
import sys,warnings; warnings.simplefilter('ignore'); sys.path.insert(0,'.')
from app import create_app
from app.odoo.models.ajuste_estoque_inventario import AjusteEstoqueInventario as A
from app.recebimento.models import RecebimentoLf
app=create_app()
with app.app_context():
    aj=A.query.filter_by(ciclo='FATURAMENTO_LF_2026_05_20',fase_pipeline='F5e_SEFAZ_OK').filter(A.acao_decidida.in_(['PERDA_LF_FB','DEV_LF_FB'])).all()
    invs=set(a.invoice_id_odoo for a in aj if a.invoice_id_odoo)
    feitos=set(r.odoo_lf_invoice_id for r in RecebimentoLf.query.filter(RecebimentoLf.odoo_lf_invoice_id.in_(list(invs) or [0])).all()) if invs else set()
    print(len(invs-feitos))
" 2>/dev/null | grep -E '^[0-9]+$' | tail -1
}

# FASE E (entrada FB para PERDA/DEV)
prev=99999
for i in $(seq 1 30); do
  echo "===== E ITER $i $(date +%H:%M:%S) =====" >> "$LOG"
  timeout 600 python scripts/inventario_2026_05/fat_lf_05_executar_clean.py \
    --confirmar --apenas-etapa E >> "$LOG" 2>&1
  rem=$(contar_e)
  echo "E ITER $i: entradas PERDA/DEV pendentes=$rem (prev=$prev)"
  [ "$rem" = "0" ] && { echo "ENTRADA E COMPLETA"; break; }
  [ "$rem" = "$prev" ] && { echo "E sem progresso (blocker robo?) — parando E"; break; }
  prev=$rem
done

# FASE F (entrada destino LF para INDUSTRIALIZACAO_FB_LF) — marca F5f_ENTRADA_OK
for i in $(seq 1 12); do
  echo "===== F ITER $i $(date +%H:%M:%S) =====" >> "$LOG"
  timeout 600 python scripts/inventario_2026_05/fat_lf_05_executar_clean.py \
    --confirmar --apenas-etapa F >> "$LOG" 2>&1
  f5f=$(python3 -c "
import sys,warnings; warnings.simplefilter('ignore'); sys.path.insert(0,'.')
from app import create_app
from app.odoo.models.ajuste_estoque_inventario import AjusteEstoqueInventario as A
app=create_app()
with app.app_context():
    pend=A.query.filter_by(ciclo='FATURAMENTO_LF_2026_05_20',fase_pipeline='F5e_SEFAZ_OK').filter(A.acao_decidida=='INDUSTRIALIZACAO_FB_LF').count()
    print(pend)
" 2>/dev/null | grep -E '^[0-9]+$' | tail -1)
  echo "F ITER $i: INDUSTR sem entrada destino=$f5f"
  [ "$f5f" = "0" ] && { echo "ENTRADA F COMPLETA"; break; }
done
echo "ENTRADA LOOP FIM"
