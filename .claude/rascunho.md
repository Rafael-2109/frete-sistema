# 1. Backfill dos campos nos registros existentes
# (via Render Shell ou script)
python -c "
from app import create_app
app = create_app()
with app.app_context():
    from app.financeiro.services.sincronizacao_contas_pagar_service import SincronizacaoContasAPagarService
    service = SincronizacaoContasAPagarService()
    resultado = service._sincronizar_por_write_date('2020-01-01 00:00:00')
    print(resultado)
"

python scripts/reconciliar_titulos_odoo.py --importar 