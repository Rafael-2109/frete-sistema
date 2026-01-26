"""
Script para detectar e marcar NFDs de pallet existentes.

Detecta NFDs existentes que são de pallet/vasilhame baseado nos CFOPs
das linhas de produto (1920, 2920, 5920, 6920, etc.) e atualiza o campo
e_pallet_devolucao para True.

Autor: Sistema de Fretes
Data: 25/01/2026
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

# CFOPs de devolução/remessa de vasilhame (pallet)
CFOPS_PALLET = {'1920', '2920', '5920', '6920', '5917', '6917', '1917', '2917'}

# Código do produto PALLET no sistema
CODIGO_PRODUTO_PALLET = '208000012'


def detectar_nfds_pallet():
    """Detecta e marca NFDs de pallet existentes"""
    app = create_app()
    with app.app_context():
        try:
            print("🔍 Buscando NFDs com linhas de produto que contenham CFOPs de pallet...")

            # Buscar NFDs que têm linhas com CFOPs de pallet
            # Usando SQL direto para performance
            cfops_str = ','.join([f"'{cfop}'" for cfop in CFOPS_PALLET])

            result = db.session.execute(text(f"""
                UPDATE nf_devolucao nfd
                SET e_pallet_devolucao = TRUE
                WHERE nfd.id IN (
                    SELECT DISTINCT nfd_linha.nf_devolucao_id
                    FROM nf_devolucao_linha nfd_linha
                    WHERE nfd_linha.cfop IN ({cfops_str})
                )
                AND nfd.e_pallet_devolucao = FALSE
                RETURNING nfd.id, nfd.numero_nfd
            """))

            nfds_atualizadas_cfop = result.fetchall()
            count_cfop = len(nfds_atualizadas_cfop)

            if count_cfop > 0:
                print(f"✅ {count_cfop} NFDs marcadas como pallet (por CFOP)")
                for nfd_id, numero_nfd in nfds_atualizadas_cfop[:10]:  # Mostrar primeiras 10
                    print(f"   - NFD {numero_nfd} (ID: {nfd_id})")
                if count_cfop > 10:
                    print(f"   ... e mais {count_cfop - 10} NFDs")

            # Buscar NFDs que têm linhas com código de produto pallet
            print("")
            print("🔍 Buscando NFDs com código de produto pallet...")

            result = db.session.execute(text(f"""
                UPDATE nf_devolucao nfd
                SET e_pallet_devolucao = TRUE
                WHERE nfd.id IN (
                    SELECT DISTINCT nfd_linha.nf_devolucao_id
                    FROM nf_devolucao_linha nfd_linha
                    WHERE nfd_linha.codigo_produto_cliente LIKE '%{CODIGO_PRODUTO_PALLET}%'
                )
                AND nfd.e_pallet_devolucao = FALSE
                RETURNING nfd.id, nfd.numero_nfd
            """))

            nfds_atualizadas_codigo = result.fetchall()
            count_codigo = len(nfds_atualizadas_codigo)

            if count_codigo > 0:
                print(f"✅ {count_codigo} NFDs adicionais marcadas como pallet (por código produto)")
                for nfd_id, numero_nfd in nfds_atualizadas_codigo[:10]:
                    print(f"   - NFD {numero_nfd} (ID: {nfd_id})")
                if count_codigo > 10:
                    print(f"   ... e mais {count_codigo - 10} NFDs")

            db.session.commit()

            # Estatísticas finais
            print("")
            print("📊 Estatísticas:")

            result = db.session.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE e_pallet_devolucao = TRUE) as pallets,
                    COUNT(*) FILTER (WHERE e_pallet_devolucao = FALSE) as produtos,
                    COUNT(*) as total
                FROM nf_devolucao
            """))
            row = result.fetchone()
            if row:
                pallets, produtos, total = row
                print(f"   Total de NFDs: {total}")
                print(f"   NFDs de pallet: {pallets}")
                print(f"   NFDs de produto: {produtos}")

            print("")
            print("✅ Processo concluído com sucesso!")
            print("")
            print("💡 As NFDs marcadas como pallet não aparecerão mais na listagem de órfãs")
            print("   do módulo de devolução e devem ser tratadas no módulo de pallet.")

            return True

        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()
            return False


if __name__ == '__main__':
    detectar_nfds_pallet()
