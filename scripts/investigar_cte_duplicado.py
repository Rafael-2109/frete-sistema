"""
Script para investigar CTe duplicado no banco de dados

Chave investigada: 35240647543687000175570010000059641031340579
DFe ID do erro: 31785
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.fretes.models import ConhecimentoTransporte
from sqlalchemy import text

def investigar_cte_duplicado():
    """Investiga CTe duplicado"""
    app = create_app()

    with app.app_context():
        chave_acesso = '35240647543687000175570010000059641031340579'
        dfe_id_erro = '31785'

        print("=" * 80)
        print("🔍 INVESTIGAÇÃO DE CTE DUPLICADO")
        print("=" * 80)
        print(f"Chave de Acesso: {chave_acesso}")
        print(f"DFe ID do erro: {dfe_id_erro}")
        print()

        # 1. Buscar TODOS os registros com essa chave de acesso
        print("📊 1. BUSCANDO TODOS OS REGISTROS COM ESSA CHAVE DE ACESSO:")
        print("-" * 80)

        ctes_mesma_chave = ConhecimentoTransporte.query.filter_by(
            chave_acesso=chave_acesso
        ).all()

        if ctes_mesma_chave:
            print(f"✅ Encontrados {len(ctes_mesma_chave)} registro(s) com essa chave:")
            print()

            for idx, cte in enumerate(ctes_mesma_chave, 1):
                print(f"   REGISTRO {idx}:")
                print(f"   - ID: {cte.id}")
                print(f"   - DFe ID: {cte.dfe_id}")
                print(f"   - Odoo Name: {cte.odoo_name}")
                print(f"   - Número CTe: {cte.numero_cte}/{cte.serie_cte}")
                print(f"   - Tipo CTe: {cte.tipo_cte} ({cte.tipo_cte_descricao})")
                print(f"   - Chave Acesso: {cte.chave_acesso}")
                print(f"   - Data Emissão: {cte.data_emissao}")
                print(f"   - Data Entrada: {cte.data_entrada}")
                print(f"   - Valor Total: {cte.valor_total}")
                print(f"   - CNPJ Emitente: {cte.cnpj_emitente}")
                print(f"   - Nome Emitente: {cte.nome_emitente}")
                print(f"   - Status Odoo: {cte.odoo_status_codigo} - {cte.odoo_status_descricao}")
                print(f"   - Ativo: {cte.ativo}")
                print(f"   - Importado em: {cte.importado_em}")
                print(f"   - Atualizado em: {cte.atualizado_em}")

                # Se for complementar
                if cte.tipo_cte == '1':
                    print(f"   - 🔗 CTe Complementa Chave: {cte.cte_complementa_chave}")
                    print(f"   - 🔗 CTe Complementa ID: {cte.cte_complementa_id}")
                    print(f"   - 📝 Motivo Complemento: {cte.motivo_complemento[:100] if cte.motivo_complemento else None}...")

                print()
        else:
            print(f"❌ NENHUM registro encontrado com essa chave!")
            print()

        # 2. Buscar pelo DFe ID do erro
        print()
        print("📊 2. BUSCANDO PELO DFe ID DO ERRO:")
        print("-" * 80)

        cte_por_dfe = ConhecimentoTransporte.query.filter_by(
            dfe_id=dfe_id_erro
        ).first()

        if cte_por_dfe:
            print(f"✅ Encontrado registro com DFe ID {dfe_id_erro}:")
            print(f"   - ID: {cte_por_dfe.id}")
            print(f"   - Chave Acesso: {cte_por_dfe.chave_acesso}")
            print(f"   - Número CTe: {cte_por_dfe.numero_cte}/{cte_por_dfe.serie_cte}")
            print(f"   - Odoo Name: {cte_por_dfe.odoo_name}")
            print()

            if cte_por_dfe.chave_acesso == chave_acesso:
                print(f"   ⚠️  MESMA CHAVE DE ACESSO do erro!")
            else:
                print(f"   ℹ️  Chave de acesso DIFERENTE do erro")
        else:
            print(f"❌ NENHUM registro encontrado com DFe ID {dfe_id_erro}")
            print(f"   → Isso significa que o INSERT falhou antes de criar o registro")
        print()

        # 3. Verificar se há múltiplos DFe IDs para a mesma chave
        print()
        print("📊 3. VERIFICANDO MÚLTIPLOS DFe IDs PARA A MESMA CHAVE:")
        print("-" * 80)

        if ctes_mesma_chave:
            dfe_ids_distintos = set(cte.dfe_id for cte in ctes_mesma_chave)
            print(f"DFe IDs distintos: {dfe_ids_distintos}")
            print(f"Total: {len(dfe_ids_distintos)}")
            print()

            if len(dfe_ids_distintos) > 1:
                print("⚠️  ATENÇÃO: Mesma chave de acesso com MÚLTIPLOS DFe IDs!")
                print("   Isso pode indicar que:")
                print("   - Odoo criou múltiplos DFes para o mesmo CTe")
                print("   - Houve reprocessamento/reimportação no Odoo")
                print("   - CTe foi cancelado e reemitido com mesma chave")
            else:
                print("✅ Apenas 1 DFe ID para essa chave (OK)")
        print()

        # 4. Buscar CTes com mesmo número mas chaves diferentes
        print()
        print("📊 4. BUSCANDO CTes COM MESMO NÚMERO MAS CHAVES DIFERENTES:")
        print("-" * 80)

        if ctes_mesma_chave:
            numero_cte = ctes_mesma_chave[0].numero_cte
            serie_cte = ctes_mesma_chave[0].serie_cte
            cnpj_emitente = ctes_mesma_chave[0].cnpj_emitente

            ctes_mesmo_numero = ConhecimentoTransporte.query.filter_by(
                numero_cte=numero_cte,
                serie_cte=serie_cte,
                cnpj_emitente=cnpj_emitente
            ).all()

            print(f"CTe: {numero_cte}/{serie_cte}")
            print(f"CNPJ Emitente: {cnpj_emitente}")
            print(f"Total encontrados: {len(ctes_mesmo_numero)}")
            print()

            if len(ctes_mesmo_numero) > 1:
                print("⚠️  MÚLTIPLOS CTes com mesmo número/série/emitente:")
                for idx, cte in enumerate(ctes_mesmo_numero, 1):
                    print(f"   {idx}. DFe ID: {cte.dfe_id}, Tipo: {cte.tipo_cte_descricao}, Chave: {cte.chave_acesso}")
                print()
                print("   Possíveis causas:")
                print("   - CTe original (tipo 0) + CTe complementar (tipo 1)")
                print("   - CTe cancelado + CTe substituto")
            else:
                print("✅ Apenas 1 CTe com esse número/série/emitente (OK)")
        print()

        # 5. Query SQL direta para verificar constraints
        print()
        print("📊 5. VERIFICANDO CONSTRAINTS DA TABELA:")
        print("-" * 80)

        result = db.session.execute(text("""
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_name = 'conhecimento_transporte'
            AND constraint_type IN ('UNIQUE', 'PRIMARY KEY')
            ORDER BY constraint_type, constraint_name
        """))

        print("Constraints UNIQUE e PRIMARY KEY:")
        for row in result:
            print(f"   - {row[0]} ({row[1]})")
        print()

        # 6. Resumo e recomendação
        print()
        print("=" * 80)
        print("📝 RESUMO DA INVESTIGAÇÃO:")
        print("=" * 80)

        if ctes_mesma_chave:
            print(f"✅ Chave de acesso JÁ EXISTE no banco: {len(ctes_mesma_chave)} registro(s)")
            print(f"   DFe ID(s): {[cte.dfe_id for cte in ctes_mesma_chave]}")
            print()
            print("🔴 CAUSA DO ERRO:")
            print("   O sistema tentou INSERIR um novo registro com DFe ID 31785")
            print("   mas a chave de acesso já existe no banco de dados.")
            print()
            print("💡 SOLUÇÃO NECESSÁRIA:")
            print("   Alterar cte_service.py linha 414 para verificar por CHAVE_ACESSO")
            print("   ao invés de apenas DFe ID:")
            print()
            print("   # ANTES:")
            print("   cte_existente = ConhecimentoTransporte.query.filter_by(dfe_id=dfe_id).first()")
            print()
            print("   # DEPOIS:")
            print("   cte_existente = ConhecimentoTransporte.query.filter_by(chave_acesso=chave_acesso).first()")
            print("   if not cte_existente:")
            print("       cte_existente = ConhecimentoTransporte.query.filter_by(dfe_id=dfe_id).first()")
        else:
            print(f"❌ Chave de acesso NÃO EXISTE no banco")
            print(f"   Isso é estranho, pois o erro indica duplicata...")
            print()
            print("🔍 INVESTIGAÇÃO ADICIONAL NECESSÁRIA:")
            print("   - Verificar se o erro ocorreu em transação que sofreu rollback")
            print("   - Verificar se há race condition na sincronização")

        print()
        print("=" * 80)

if __name__ == '__main__':
    investigar_cte_duplicado()
