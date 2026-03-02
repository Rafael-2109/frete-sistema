"""
Migration: Backfill de NFs referenciadas em itens de fatura CarVia
===================================================================

Problema: 13 das 31 NFs referenciadas em carvia_fatura_cliente_itens nunca
foram importadas para carvia_nfs, resultando em nf_id = NULL.

Solucao:
1. Buscar itens com nf_id IS NULL e nf_numero IS NOT NULL
2. Tentar resolver via resolver_nf_por_numero (caso NF importada depois)
3. Tentar resolver via junction carvia_operacao_nfs
4. Ultimo recurso: criar CarviaNf com tipo_fonte='FATURA_REFERENCIA'
5. Criar junction carvia_operacao_nfs (se item tem operacao_id)
6. Atualizar nf_id no item

Idempotencia:
- Cada operacao verifica estado ANTES de agir
- NF criada com check por numero + cnpj normalizado
- Junction com verificacao de existencia
- nf_id so atualizado se ainda NULL
- Script pode rodar N vezes com resultado identico

Execucao:
    source .venv/bin/activate
    python scripts/migrations/backfill_carvia_nf_linking.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def run_backfill():
    app = create_app()
    with app.app_context():

        print("=" * 60)
        print("Backfill: CarVia NF Linking — NFs referencia")
        print("=" * 60)

        # Estado ANTES
        conn = db.session.connection()
        result = conn.execute(text("""
            SELECT
                count(*) AS total,
                count(nf_id) AS com_nf,
                count(*) - count(nf_id) AS sem_nf
            FROM carvia_fatura_cliente_itens
            WHERE nf_numero IS NOT NULL
        """))
        row = result.fetchone()
        print(f"\n--- Estado ANTES ---")
        print(f"  Total itens com nf_numero: {row[0]}")
        print(f"  Com nf_id: {row[1]}")
        print(f"  Sem nf_id (a resolver): {row[2]}")

        if row[2] == 0:
            print("\n[OK] Nenhum item pendente. Nada a fazer.")
            return

        # Importar service
        from app.carvia.services.linking_service import LinkingService
        from app.carvia.models import CarviaFaturaClienteItem

        linker = LinkingService()

        # Buscar itens pendentes
        itens_pendentes = CarviaFaturaClienteItem.query.filter(
            CarviaFaturaClienteItem.nf_id.is_(None),
            CarviaFaturaClienteItem.nf_numero.isnot(None),
        ).all()

        stats = {
            'total_pendentes': len(itens_pendentes),
            'nfs_match_direto': 0,
            'nfs_via_junction': 0,
            'nfs_criadas_referencia': 0,
            'junctions_criadas': 0,
            'falhas': 0,
        }

        print(f"\n--- Processando {len(itens_pendentes)} itens ---\n")

        for item in itens_pendentes:
            nf = None
            metodo = None

            # Nivel 1: Match direto
            nf = linker.resolver_nf_por_numero(
                item.nf_numero, item.contraparte_cnpj
            )
            if nf:
                metodo = 'match_direto'
                stats['nfs_match_direto'] += 1

            # Nivel 2: Fallback via junction
            if nf is None and item.operacao_id:
                nf = linker._resolver_nf_via_junction(
                    item.nf_numero, item.operacao_id
                )
                if nf:
                    metodo = 'junction'
                    stats['nfs_via_junction'] += 1

            # Nivel 3: Criar NF referencia
            if nf is None:
                nf = linker._criar_nf_referencia(
                    nf_numero=item.nf_numero,
                    contraparte_cnpj=item.contraparte_cnpj,
                    contraparte_nome=item.contraparte_nome,
                    valor_mercadoria=item.valor_mercadoria,
                    peso_kg=item.peso_kg,
                    criado_por='backfill',
                )
                if nf:
                    metodo = 'referencia_criada'
                    stats['nfs_criadas_referencia'] += 1

            if nf:
                item.nf_id = nf.id
                print(
                    f"  [OK] item={item.id} nf_numero={item.nf_numero} "
                    f"-> nf_id={nf.id} ({metodo})"
                )

                # Criar junction se item tem operacao_id
                if item.operacao_id:
                    if linker._criar_junction_se_necessario(item.operacao_id, nf.id):
                        stats['junctions_criadas'] += 1
                        print(
                            f"       + junction: operacao={item.operacao_id} nf={nf.id}"
                        )
            else:
                stats['falhas'] += 1
                print(
                    f"  [FALHA] item={item.id} nf_numero={item.nf_numero} "
                    f"cnpj={item.contraparte_cnpj} -> sem dados para criar NF"
                )

        db.session.commit()

        # Estado DEPOIS
        print(f"\n--- Estatisticas ---")
        print(f"  Total pendentes processados: {stats['total_pendentes']}")
        print(f"  Match direto (NF ja importada): {stats['nfs_match_direto']}")
        print(f"  Via junction (NF vinculada): {stats['nfs_via_junction']}")
        print(f"  NFs referencia criadas: {stats['nfs_criadas_referencia']}")
        print(f"  Junctions criadas: {stats['junctions_criadas']}")
        print(f"  Falhas: {stats['falhas']}")

        # Verificacao final
        result = conn.execute(text("""
            SELECT
                count(*) AS total,
                count(nf_id) AS com_nf,
                count(*) - count(nf_id) AS sem_nf
            FROM carvia_fatura_cliente_itens
            WHERE nf_numero IS NOT NULL
        """))
        row = result.fetchone()
        print(f"\n--- Estado DEPOIS ---")
        print(f"  Total itens com nf_numero: {row[0]}")
        print(f"  Com nf_id: {row[1]}")
        print(f"  Sem nf_id: {row[2]}")

        # Verificar NFs referencia
        result = conn.execute(text("""
            SELECT count(*) FROM carvia_nfs WHERE tipo_fonte = 'FATURA_REFERENCIA'
        """))
        count = result.scalar()
        print(f"  NFs tipo FATURA_REFERENCIA no banco: {count}")

        # Verificar junctions
        result = conn.execute(text("""
            SELECT count(*) FROM carvia_operacao_nfs
        """))
        count = result.scalar()
        print(f"  Total junctions carvia_operacao_nfs: {count}")

        if row[2] == 0:
            print("\n[SUCESSO] Todos os itens com nf_numero tem nf_id vinculado!")
        else:
            print(f"\n[ATENCAO] {row[2]} itens ainda sem nf_id (dados insuficientes)")


if __name__ == '__main__':
    run_backfill()
