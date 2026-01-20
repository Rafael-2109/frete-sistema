#!/usr/bin/env python3
"""
Script de Diagnóstico: De-Para vs Divergências NF-PO
====================================================

Verifica se há divergências do tipo 'sem_depara' que na verdade JÁ TÊM
um De-Para ativo, indicando falha no reprocessamento.

Uso:
    python scripts/diagnostico_depara_divergencias.py

Para rodar em produção (Render):
    python scripts/diagnostico_depara_divergencias.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def diagnosticar():
    """Executa diagnóstico completo."""
    app = create_app()
    with app.app_context():
        print("=" * 80)
        print("DIAGNÓSTICO: DE-PARA vs DIVERGÊNCIAS SEM_DEPARA")
        print("=" * 80)
        print()

        # 1. Buscar divergências sem_depara pendentes que TÊM De-Para ativo
        query_problema = text("""
            SELECT
                d.id as divergencia_id,
                d.cnpj_fornecedor,
                d.cod_produto_fornecedor,
                d.nome_produto,
                d.odoo_dfe_id,
                v.numero_nf,
                v.status as validacao_status,
                dp.id as depara_id,
                dp.cod_produto_interno,
                dp.ativo as depara_ativo,
                dp.atualizado_em as depara_atualizado
            FROM divergencia_nf_po d
            JOIN validacao_nf_po_dfe v ON d.validacao_id = v.id
            LEFT JOIN produto_fornecedor_depara dp ON
                dp.cnpj_fornecedor = d.cnpj_fornecedor AND
                dp.cod_produto_fornecedor = d.cod_produto_fornecedor AND
                dp.ativo = true
            WHERE d.tipo_divergencia = 'sem_depara'
              AND d.status = 'pendente'
              AND dp.id IS NOT NULL
            ORDER BY d.criado_em DESC
        """)

        result = db.session.execute(query_problema)
        problemas = list(result)

        print(f"🔴 PROBLEMAS ENCONTRADOS: {len(problemas)}")
        print("-" * 80)

        if problemas:
            print("\nDivergências 'sem_depara' que JÁ TÊM De-Para ativo:\n")
            for row in problemas:
                print(f"  Divergência ID: {row[0]}")
                print(f"    NF: {row[5]} | DFE ID: {row[4]}")
                print(f"    CNPJ: {row[1]}")
                print(f"    Código Fornecedor: {row[2]}")
                print(f"    Produto: {row[3][:50]}..." if row[3] and len(row[3]) > 50 else f"    Produto: {row[3]}")
                print(f"    Status Validação: {row[6]}")
                print(f"    De-Para ID: {row[7]} | Código Interno: {row[8]}")
                print(f"    De-Para Atualizado: {row[10]}")
                print()

            # Gerar comandos para reprocessar
            print("\n" + "=" * 80)
            print("COMANDOS PARA REPROCESSAR:")
            print("=" * 80)

            dfe_ids = set([row[4] for row in problemas])
            print(f"\n# Revalidar {len(dfe_ids)} DFE(s) afetados:")
            print("from app import create_app")
            print("from app.recebimento.services.validacao_nf_po_service import ValidacaoNfPoService")
            print()
            print("app = create_app()")
            print("with app.app_context():")
            print("    service = ValidacaoNfPoService()")
            for dfe_id in dfe_ids:
                print(f"    print(service.validar_dfe({dfe_id}))")

        else:
            print("\n✅ Nenhum problema encontrado!")
            print("   Todas as divergências 'sem_depara' realmente não têm De-Para.")

        # 2. Estatísticas gerais
        print("\n" + "=" * 80)
        print("ESTATÍSTICAS GERAIS")
        print("=" * 80)

        stats = db.session.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM divergencia_nf_po WHERE tipo_divergencia = 'sem_depara' AND status = 'pendente') as div_pendentes,
                (SELECT COUNT(*) FROM produto_fornecedor_depara WHERE ativo = true) as deparas_ativos,
                (SELECT COUNT(*) FROM validacao_nf_po_dfe WHERE status = 'bloqueado') as validacoes_bloqueadas,
                (SELECT COUNT(*) FROM validacao_nf_po_dfe WHERE status = 'finalizado_odoo') as validacoes_finalizadas
        """)).fetchone()

        print(f"\n  Divergências 'sem_depara' pendentes: {stats[0]}")
        print(f"  De-Para ativos: {stats[1]}")
        print(f"  Validações bloqueadas: {stats[2]}")
        print(f"  Validações finalizadas (já no Odoo): {stats[3]}")

        # 3. Verificar se há NFs com PO vinculado que ainda têm divergências
        query_finalizadas_com_div = text("""
            SELECT
                v.numero_nf,
                v.odoo_dfe_id,
                v.status,
                v.odoo_po_vinculado_name,
                COUNT(d.id) as qtd_divergencias
            FROM validacao_nf_po_dfe v
            JOIN divergencia_nf_po d ON d.validacao_id = v.id AND d.status = 'pendente'
            WHERE v.status = 'finalizado_odoo'
            GROUP BY v.id, v.numero_nf, v.odoo_dfe_id, v.status, v.odoo_po_vinculado_name
        """)

        result_final = db.session.execute(query_finalizadas_com_div)
        finalizadas_com_div = list(result_final)

        if finalizadas_com_div:
            print("\n" + "-" * 80)
            print(f"⚠️  NFs finalizadas no Odoo mas com divergências pendentes: {len(finalizadas_com_div)}")
            for row in finalizadas_com_div:
                print(f"    NF {row[0]} (DFE {row[1]}) - PO: {row[3]} - {row[4]} div. pendentes")

        print("\n" + "=" * 80)
        print("FIM DO DIAGNÓSTICO")
        print("=" * 80)


def reprocessar_divergencias_com_depara():
    """
    Reprocessa automaticamente todas as divergências que têm De-Para.
    USE COM CUIDADO - isso vai revalidar todos os DFEs afetados.
    """
    app = create_app()
    with app.app_context():
        from app.recebimento.services.validacao_nf_po_service import ValidacaoNfPoService

        # Buscar DFEs que precisam ser revalidados
        query = text("""
            SELECT DISTINCT d.odoo_dfe_id, v.numero_nf
            FROM divergencia_nf_po d
            JOIN validacao_nf_po_dfe v ON d.validacao_id = v.id
            JOIN produto_fornecedor_depara dp ON
                dp.cnpj_fornecedor = d.cnpj_fornecedor AND
                dp.cod_produto_fornecedor = d.cod_produto_fornecedor AND
                dp.ativo = true
            WHERE d.tipo_divergencia = 'sem_depara'
              AND d.status = 'pendente'
              AND v.status != 'finalizado_odoo'
        """)

        result = db.session.execute(query)
        dfes = list(result)

        if not dfes:
            print("Nenhum DFE precisa ser reprocessado.")
            return

        print(f"Reprocessando {len(dfes)} DFE(s)...")

        service = ValidacaoNfPoService()

        for dfe_id, numero_nf in dfes:
            try:
                print(f"\n  Revalidando DFE {dfe_id} (NF {numero_nf})...", end=" ")
                resultado = service.validar_dfe(dfe_id)
                print(f"Status: {resultado.get('status')}")
            except Exception as e:
                print(f"ERRO: {e}")

        print("\nReprocessamento concluído!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--reprocessar":
        print("⚠️  MODO REPROCESSAMENTO ATIVADO")
        confirma = input("Tem certeza que deseja reprocessar? (sim/nao): ")
        if confirma.lower() == "sim":
            reprocessar_divergencias_com_depara()
        else:
            print("Cancelado.")
    else:
        diagnosticar()
