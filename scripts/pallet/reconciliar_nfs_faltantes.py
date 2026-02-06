"""
Reconciliacao: Importar NFs de pallet faltantes do Odoo.

O modulo de pallet v2 foi criado recentemente e so sincroniza 30 dias por padrao.
NFs de agosto/2025 em diante nunca foram importadas.

Este script executa o sync retroativo com data_de='2025-08-01' para importar
todas as NFs pendentes.

Uso:
    source .venv/bin/activate
    python scripts/pallet/reconciliar_nfs_faltantes.py
"""
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app
from app.pallet.services.sync_odoo_service import PalletSyncService


def reconciliar():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("RECONCILIACAO DE NFs DE PALLET FALTANTES")
        print("Periodo: 2025-08-01 ate hoje")
        print("=" * 60)
        print()

        service = PalletSyncService()

        # Autenticar
        print("Autenticando no Odoo...")
        if not service.odoo.authenticate():
            print("ERRO: Falha na autenticacao com Odoo")
            return

        print("Autenticado com sucesso!\n")

        t_inicio = time.time()

        # Executar sync retroativo completo
        resultado = service.sincronizar_tudo(
            data_de='2025-08-01'
        )

        elapsed = time.time() - t_inicio

        # Exibir resultado
        print("\n" + "=" * 60)
        print("RESULTADO DA RECONCILIACAO")
        print("=" * 60)

        for tipo in ['remessas', 'vendas', 'devolucoes', 'recusas']:
            r = resultado.get(tipo, {})
            print(f"\n{tipo.upper()}:")
            print(f"  Processados: {r.get('processados', 0)}")
            print(f"  Novos:       {r.get('novos', 0)}")
            print(f"  Existentes:  {r.get('ja_existentes', 0)}")
            print(f"  Erros:       {r.get('erros', 0)}")

        ncs = resultado.get('ncs', {})
        print(f"\nNCs:")
        print(f"  Vinculadas:     {ncs.get('ncs_vinculadas', 0)}")
        print(f"  Sem remessa:    {ncs.get('ncs_sem_remessa', 0)}")

        canceladas = resultado.get('canceladas', {})
        print(f"\nCANCELADAS:")
        print(f"  Registradas:    {canceladas.get('canceladas_registradas', 0)}")
        print(f"  Ja existentes:  {canceladas.get('ja_existentes', 0)}")

        print(f"\n{'=' * 60}")
        print(f"TOTAL NOVOS:  {resultado.get('total_novos', 0)}")
        print(f"TOTAL BAIXAS: {resultado.get('total_baixas', 0)}")
        print(f"TEMPO TOTAL:  {elapsed:.1f}s ({elapsed/60:.1f} min)")
        print(f"{'=' * 60}")


if __name__ == '__main__':
    reconciliar()
