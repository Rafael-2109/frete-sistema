"""
Script para recalcular impostos de todos os pedidos de uma importação

Uso:
    source .venv/bin/activate
    python scripts/recalcular_impostos_importacao.py <ID_IMPORTACAO>

Exemplo:
    python scripts/recalcular_impostos_importacao.py 18
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.pedidos.integracao_odoo.models import RegistroPedidoOdoo, PedidoImportacaoTemp


def main():
    if len(sys.argv) < 2:
        print("❌ Informe o ID da importação")
        print("\nUso: python scripts/recalcular_impostos_importacao.py <ID>")
        sys.exit(1)

    importacao_id = int(sys.argv[1])

    app = create_app()
    with app.app_context():
        # Busca importação
        importacao = PedidoImportacaoTemp.query.get(importacao_id)
        if not importacao:
            print(f"❌ Importação {importacao_id} não encontrada")
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"RECÁLCULO DE IMPOSTOS - Importação {importacao_id}")
        print(f"{'='*60}")
        print(f"📄 Rede: {importacao.rede}")
        print(f"📄 Documento: {importacao.numero_documento}")

        # Busca pedidos criados dessa importação
        registros = RegistroPedidoOdoo.query.filter_by(
            rede=importacao.rede,
            numero_documento=importacao.numero_documento,
            status_odoo='SUCESSO'
        ).all()

        if not registros:
            print(f"\n❌ Nenhum pedido encontrado para esta importação")
            sys.exit(1)

        print(f"\n📋 Pedidos encontrados: {len(registros)}")
        print("-" * 60)

        # Importa o que precisa para enfileirar
        from app.portal.workers import enqueue_job
        from app.pedidos.workers.impostos_jobs import calcular_impostos_odoo

        jobs_criados = []

        for reg in registros:
            print(f"📦 {reg.odoo_order_name} (ID: {reg.odoo_order_id}) - {reg.nome_cliente[:30] if reg.nome_cliente else 'N/A'}")

            try:
                job = enqueue_job(
                    calcular_impostos_odoo,
                    reg.odoo_order_id,
                    reg.odoo_order_name,
                    queue_name='impostos',
                    timeout='5m'
                )
                jobs_criados.append({
                    'job_id': job.id,
                    'order_name': reg.odoo_order_name
                })
                print(f"   ✅ Job {job.id} enfileirado")
            except Exception as e:
                print(f"   ❌ Erro ao enfileirar: {e}")

        print(f"\n{'='*60}")
        print(f"✅ {len(jobs_criados)} jobs enfileirados na fila 'impostos'")
        print(f"📊 Acompanhe no dashboard RQ: /portal/rq/")
        print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
