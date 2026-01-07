"""
Script para adicionar campo qtd_abatida na tabela movimentacao_estoque.

Este campo rastreia quanto de uma NF de remessa de pallet ja foi devolvido/abatido.
Saldo pendente = qtd_movimentacao - qtd_abatida

Execucao local: python scripts/migrations/add_qtd_abatida_pallet.py
Execucao Render: Executar SQL diretamente no Shell
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def verificar_campo_existe():
    """Verifica se o campo ja existe"""
    app = create_app()
    with app.app_context():
        resultado = db.session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'movimentacao_estoque'
              AND column_name = 'qtd_abatida'
        """))
        return resultado.fetchone() is not None


def adicionar_campo():
    """Adiciona o campo qtd_abatida"""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se ja existe
            if verificar_campo_existe():
                print("Campo qtd_abatida ja existe. Pulando criacao.")
                return True

            print("Adicionando campo qtd_abatida...")
            db.session.execute(text("""
                ALTER TABLE movimentacao_estoque
                ADD COLUMN qtd_abatida NUMERIC(15, 3) DEFAULT 0
            """))
            db.session.commit()
            print("Campo qtd_abatida adicionado com sucesso!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"Erro ao adicionar campo: {e}")
            return False


def popular_qtd_abatida():
    """
    Popula qtd_abatida com base em devolucoes ja existentes.

    Logica: Para cada DEVOLUCAO/RECUSA de pallet, encontrar a REMESSA
    correspondente (pela NF) e somar na qtd_abatida.
    """
    app = create_app()
    with app.app_context():
        try:
            print("\nPopulando qtd_abatida com base em devolucoes existentes...")

            # Buscar todas as devolucoes/recusas de pallet
            resultado = db.session.execute(text("""
                SELECT numero_nf, SUM(qtd_movimentacao) as total_devolvido
                FROM movimentacao_estoque
                WHERE local_movimentacao = 'PALLET'
                  AND tipo_movimentacao IN ('DEVOLUCAO', 'RECUSA')
                  AND ativo = TRUE
                  AND numero_nf IS NOT NULL
                  AND numero_nf != ''
                GROUP BY numero_nf
            """))

            devolucoes = resultado.fetchall()

            if not devolucoes:
                print("Nenhuma devolucao encontrada para processar.")
                return True

            print(f"Encontradas {len(devolucoes)} NFs com devolucoes.")

            # Atualizar qtd_abatida nas remessas correspondentes
            for devol in devolucoes:
                nf = devol.numero_nf
                total = devol.total_devolvido

                # Atualizar remessas com essa NF
                result = db.session.execute(text("""
                    UPDATE movimentacao_estoque
                    SET qtd_abatida = :total
                    WHERE numero_nf = :nf
                      AND local_movimentacao = 'PALLET'
                      AND tipo_movimentacao = 'REMESSA'
                      AND ativo = TRUE
                """), {'nf': nf, 'total': total})

                if result.rowcount > 0:
                    print(f"  NF {nf}: {total} pallets abatidos ({result.rowcount} registro(s) atualizado(s))")

            db.session.commit()
            print("\nPopulacao concluida!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"Erro ao popular qtd_abatida: {e}")
            return False


def mostrar_resumo():
    """Mostra resumo do saldo fiscal"""
    app = create_app()
    with app.app_context():
        resultado = db.session.execute(text("""
            SELECT
                COUNT(*) as total_remessas,
                SUM(CASE WHEN COALESCE(qtd_abatida, 0) > 0 THEN 1 ELSE 0 END) as com_abatimento,
                SUM(qtd_movimentacao) as total_enviado,
                SUM(COALESCE(qtd_abatida, 0)) as total_abatido,
                SUM(qtd_movimentacao - COALESCE(qtd_abatida, 0)) as saldo_pendente
            FROM movimentacao_estoque
            WHERE local_movimentacao = 'PALLET'
              AND tipo_movimentacao = 'REMESSA'
              AND ativo = TRUE
              AND baixado = FALSE
        """))

        r = resultado.fetchone()

        print("\n" + "=" * 60)
        print("RESUMO SALDO FISCAL - REMESSAS DE PALLET PENDENTES")
        print("=" * 60)
        print(f"Total de remessas pendentes: {r.total_remessas}")
        print(f"Remessas com abatimento:     {r.com_abatimento}")
        print(f"Total enviado:               {int(r.total_enviado or 0)} pallets")
        print(f"Total abatido:               {int(r.total_abatido or 0)} pallets")
        print(f"Saldo fiscal pendente:       {int(r.saldo_pendente or 0)} pallets")
        print("=" * 60)


if __name__ == '__main__':
    print("=" * 60)
    print("MIGRACAO: Adicionar campo qtd_abatida")
    print("=" * 60)

    # 1. Adicionar campo
    if not adicionar_campo():
        print("\nFalha na migracao!")
        sys.exit(1)

    # 2. Popular com dados existentes
    if '--popular' in sys.argv or '--execute' in sys.argv:
        popular_qtd_abatida()
    else:
        print("\nPara popular com devolucoes existentes, rode com --popular")

    # 3. Mostrar resumo
    mostrar_resumo()

    print("\n SQL para executar no Render Shell:")
    print("-" * 60)
    print("""
-- 1. Adicionar campo
ALTER TABLE movimentacao_estoque
ADD COLUMN IF NOT EXISTS qtd_abatida NUMERIC(15, 3) DEFAULT 0;

-- 2. Popular com devolucoes existentes
UPDATE movimentacao_estoque rem
SET qtd_abatida = COALESCE((
    SELECT SUM(qtd_movimentacao)
    FROM movimentacao_estoque dev
    WHERE dev.numero_nf = rem.numero_nf
      AND dev.local_movimentacao = 'PALLET'
      AND dev.tipo_movimentacao IN ('DEVOLUCAO', 'RECUSA')
      AND dev.ativo = TRUE
), 0)
WHERE rem.local_movimentacao = 'PALLET'
  AND rem.tipo_movimentacao = 'REMESSA'
  AND rem.ativo = TRUE;

-- 3. Verificar resultado
SELECT
    COUNT(*) as total_remessas,
    SUM(CASE WHEN COALESCE(qtd_abatida, 0) > 0 THEN 1 ELSE 0 END) as com_abatimento,
    SUM(qtd_movimentacao) as total_enviado,
    SUM(COALESCE(qtd_abatida, 0)) as total_abatido
FROM movimentacao_estoque
WHERE local_movimentacao = 'PALLET'
  AND tipo_movimentacao = 'REMESSA'
  AND ativo = TRUE
  AND baixado = FALSE;
""")
