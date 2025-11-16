"""
Script simplificado para investigar CTe duplicado no Render
Conecta diretamente ao banco PostgreSQL sem precisar do Flask

Chave investigada: 35240647543687000175570010000059641031340579
DFe ID do erro: 31785
"""

import psycopg2
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def investigar_cte_duplicado():
    """Investiga CTe duplicado"""

    # Pegar DATABASE_URL do .env
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ DATABASE_URL não encontrada no .env")
        return

    # Converter postgres:// para postgresql:// se necessário
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    chave_acesso = '35240647543687000175570010000059641031340579'
    dfe_id_erro = '31785'

    try:
        # Conectar ao banco
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        print("=" * 80)
        print("🔍 INVESTIGAÇÃO DE CTE DUPLICADO")
        print("=" * 80)
        print(f"Chave de Acesso: {chave_acesso}")
        print(f"DFe ID do erro: {dfe_id_erro}")
        print()

        # 1. Buscar TODOS os registros com essa chave de acesso
        print("📊 1. BUSCANDO TODOS OS REGISTROS COM ESSA CHAVE DE ACESSO:")
        print("-" * 80)

        cur.execute("""
            SELECT
                id, dfe_id, odoo_name, numero_cte, serie_cte, tipo_cte,
                chave_acesso, data_emissao, data_entrada, valor_total,
                cnpj_emitente, nome_emitente, odoo_status_codigo,
                odoo_status_descricao, ativo, importado_em, atualizado_em,
                cte_complementa_chave, cte_complementa_id, motivo_complemento,
                numeros_nfs
            FROM conhecimento_transporte
            WHERE chave_acesso = %s
            ORDER BY importado_em
        """, (chave_acesso,))

        ctes = cur.fetchall()

        if ctes:
            print(f"✅ Encontrados {len(ctes)} registro(s) com essa chave:")
            print()

            tipos = {
                '0': 'Normal',
                '1': 'Complementar',
                '2': 'Anulação',
                '3': 'Substituto'
            }

            for idx, cte in enumerate(ctes, 1):
                print(f"   REGISTRO {idx}:")
                print(f"   - ID: {cte[0]}")
                print(f"   - DFe ID: {cte[1]}")
                print(f"   - Odoo Name: {cte[2]}")
                print(f"   - Número CTe: {cte[3]}/{cte[4]}")
                print(f"   - Tipo CTe: {cte[5]} ({tipos.get(cte[5], 'Desconhecido')})")
                print(f"   - Chave Acesso: {cte[6]}")
                print(f"   - Data Emissão: {cte[7]}")
                print(f"   - Data Entrada: {cte[8]}")
                print(f"   - Valor Total: {cte[9]}")
                print(f"   - CNPJ Emitente: {cte[10]}")
                print(f"   - Nome Emitente: {cte[11]}")
                print(f"   - Status Odoo: {cte[12]} - {cte[13]}")
                print(f"   - Ativo: {cte[14]}")
                print(f"   - Importado em: {cte[15]}")
                print(f"   - Atualizado em: {cte[16]}")
                print(f"   - NFs: {cte[20]}")

                if cte[5] == '1':  # Se for complementar
                    print(f"   - 🔗 CTe Complementa Chave: {cte[17]}")
                    print(f"   - 🔗 CTe Complementa ID: {cte[18]}")
                    if cte[19]:
                        motivo = cte[19][:100] if len(cte[19]) > 100 else cte[19]
                        print(f"   - 📝 Motivo Complemento: {motivo}...")

                print()
        else:
            print(f"❌ NENHUM registro encontrado com essa chave!")
            print()

        # 2. Buscar pelo DFe ID do erro
        print()
        print("📊 2. BUSCANDO PELO DFe ID DO ERRO:")
        print("-" * 80)

        cur.execute("""
            SELECT id, dfe_id, chave_acesso, numero_cte, serie_cte, odoo_name
            FROM conhecimento_transporte
            WHERE dfe_id = %s
        """, (dfe_id_erro,))

        cte_por_dfe = cur.fetchone()

        if cte_por_dfe:
            print(f"✅ Encontrado registro com DFe ID {dfe_id_erro}:")
            print(f"   - ID: {cte_por_dfe[0]}")
            print(f"   - Chave Acesso: {cte_por_dfe[2]}")
            print(f"   - Número CTe: {cte_por_dfe[3]}/{cte_por_dfe[4]}")
            print(f"   - Odoo Name: {cte_por_dfe[5]}")
            print()

            if cte_por_dfe[2] == chave_acesso:
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

        if ctes:
            dfe_ids_distintos = list(set(cte[1] for cte in ctes))
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

        if ctes:
            numero_cte = ctes[0][3]
            serie_cte = ctes[0][4]
            cnpj_emitente = ctes[0][10]

            cur.execute("""
                SELECT id, dfe_id, tipo_cte, chave_acesso
                FROM conhecimento_transporte
                WHERE numero_cte = %s
                AND serie_cte = %s
                AND cnpj_emitente = %s
                ORDER BY importado_em
            """, (numero_cte, serie_cte, cnpj_emitente))

            ctes_mesmo_numero = cur.fetchall()

            print(f"CTe: {numero_cte}/{serie_cte}")
            print(f"CNPJ Emitente: {cnpj_emitente}")
            print(f"Total encontrados: {len(ctes_mesmo_numero)}")
            print()

            if len(ctes_mesmo_numero) > 1:
                print("⚠️  MÚLTIPLOS CTes com mesmo número/série/emitente:")
                for idx, cte in enumerate(ctes_mesmo_numero, 1):
                    tipo_desc = tipos.get(cte[2], 'Desconhecido')
                    print(f"   {idx}. DFe ID: {cte[1]}, Tipo: {tipo_desc}, Chave: {cte[3]}")
                print()
                print("   Possíveis causas:")
                print("   - CTe original (tipo 0) + CTe complementar (tipo 1)")
                print("   - CTe cancelado + CTe substituto")
            else:
                print("✅ Apenas 1 CTe com esse número/série/emitente (OK)")
        print()

        # 5. Verificar constraints
        print()
        print("📊 5. VERIFICANDO CONSTRAINTS DA TABELA:")
        print("-" * 80)

        cur.execute("""
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_name = 'conhecimento_transporte'
            AND constraint_type IN ('UNIQUE', 'PRIMARY KEY')
            ORDER BY constraint_type, constraint_name
        """)

        constraints = cur.fetchall()

        print("Constraints UNIQUE e PRIMARY KEY:")
        for constraint in constraints:
            print(f"   - {constraint[0]} ({constraint[1]})")
        print()

        # 6. Resumo e recomendação
        print()
        print("=" * 80)
        print("📝 RESUMO DA INVESTIGAÇÃO:")
        print("=" * 80)

        if ctes:
            print(f"✅ Chave de acesso JÁ EXISTE no banco: {len(ctes)} registro(s)")
            print(f"   DFe ID(s): {[cte[1] for cte in ctes]}")
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
            print("   # Verificar PRIMEIRO por chave_acesso (UNIQUE constraint)")
            print("   cte_existente = ConhecimentoTransporte.query.filter_by(")
            print("       chave_acesso=chave_acesso")
            print("   ).first()")
            print()
            print("   # Se não encontrou, verificar por dfe_id")
            print("   if not cte_existente:")
            print("       cte_existente = ConhecimentoTransporte.query.filter_by(")
            print("           dfe_id=dfe_id")
            print("       ).first()")
        else:
            print(f"❌ Chave de acesso NÃO EXISTE no banco")
            print(f"   Isso é estranho, pois o erro indica duplicata...")

        print()
        print("=" * 80)

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    investigar_cte_duplicado()
