"""
Migration: Adicionar coluna separacao.equipe_vendas + backfill

Data: 2026-06-07
Descricao:
    Desnormaliza equipe_vendas em `separacao` (hoje obtido via LEFT JOIN caro
    com carteira_principal na VIEW pedidos). Permite recriar a VIEW v8 SEM o
    JOIN (medido: 710ms -> ~26-70ms por scan; o JOIN respondia por 97% dos
    buffers). equipe_vendas e constante por num_pedido (validado em producao:
    0/8654 pedidos com divergencia entre produtos).

    Mesmo padrao ja usado por `tags_pedido` (desnormalizado de CarteiraPrincipal
    via AtualizarDadosService).

ORDEM DE DEPLOY (critico): rodar ESTA migration (coluna + backfill) e o deploy
    do codigo que propaga equipe_vendas ANTES de recriar a VIEW v8. Caso
    contrario a VIEW v8 leria equipe_vendas ainda vazia.

Executar: python scripts/migrations/add_equipe_vendas_separacao.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def migrar():
    app = create_app()
    with app.app_context():
        try:
            # ---- BEFORE ----
            coluna_existe = db.session.execute(text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'separacao' AND column_name = 'equipe_vendas'
            """)).scalar() is not None
            print(f"🔎 BEFORE: coluna separacao.equipe_vendas existe? {coluna_existe}")

            # ---- 1. ADD COLUMN (idempotente) ----
            print("🔄 Adicionando coluna separacao.equipe_vendas (VARCHAR(100))...")
            db.session.execute(text(
                "ALTER TABLE separacao ADD COLUMN IF NOT EXISTS equipe_vendas VARCHAR(100)"
            ))
            db.session.commit()

            # ---- 2. BACKFILL (replica o LEFT JOIN da VIEW v7) ----
            print("🔄 Backfill a partir de carteira_principal (num_pedido, cod_produto)...")
            res = db.session.execute(text("""
                UPDATE separacao s
                SET equipe_vendas = cp.equipe_vendas
                FROM carteira_principal cp
                WHERE s.num_pedido = cp.num_pedido
                  AND s.cod_produto = cp.cod_produto
                  AND s.equipe_vendas IS DISTINCT FROM cp.equipe_vendas
            """))
            db.session.commit()
            print(f"   → {res.rowcount} linhas de separacao atualizadas")

            # ---- AFTER ----
            total = db.session.execute(text("SELECT count(*) FROM separacao")).scalar()
            com_equipe = db.session.execute(text(
                "SELECT count(*) FROM separacao WHERE equipe_vendas IS NOT NULL"
            )).scalar()
            print(f"✅ AFTER: {com_equipe}/{total} linhas de separacao com equipe_vendas preenchida")

            # Sanity: lotes nao-PREVISAO sem nenhuma linha com equipe (esperado baixo)
            lotes_sem_equipe = db.session.execute(text("""
                SELECT count(*) FROM (
                    SELECT separacao_lote_id
                    FROM separacao
                    WHERE separacao_lote_id IS NOT NULL AND status <> 'PREVISAO'
                    GROUP BY separacao_lote_id
                    HAVING bool_and(equipe_vendas IS NULL)
                ) x
            """)).scalar()
            print(f"ℹ️  Lotes (nao-PREVISAO) sem nenhuma equipe_vendas: {lotes_sem_equipe}")

            return True

        except Exception as e:
            print(f"❌ Erro na migration: {e}")
            db.session.rollback()
            return False


if __name__ == '__main__':
    sys.exit(0 if migrar() else 1)
