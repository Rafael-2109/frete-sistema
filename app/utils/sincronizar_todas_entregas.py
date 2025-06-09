from app.faturamento.models import RelatorioFaturamentoImportado
from .sincronizar_entregas import sincronizar_entrega_por_nf

def sincronizar_todas_entregas(verbose=False):
    total = 0
    for row in RelatorioFaturamentoImportado.query.all():
        sincronizar_entrega_por_nf(row.numero_nf)
        total += 1
        if verbose:
            print(f"✔️ NF {row.numero_nf} sincronizada")
    print(f"✅ Total de entregas sincronizadas: {total}")