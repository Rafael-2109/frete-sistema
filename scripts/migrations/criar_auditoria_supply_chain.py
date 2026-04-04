# -*- coding: utf-8 -*-
"""
Migracao: Criar tabela evento_supply_chain + trigger function + triggers
=========================================================================

Implementa auditoria completa de supply chain via PostgreSQL triggers.
Captura 100% dos writes em 6 tabelas: carteira_principal, separacao,
faturamento_produto, movimentacao_estoque, programacao_producao, pedido_compras.

Uso: python scripts/migrations/criar_auditoria_supply_chain.py
Data: 2026-04-04
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migracao():
    app = create_app()
    with app.app_context():
        try:
            print("=" * 70)
            print("MIGRACAO: Auditoria Supply Chain (Event Sourcing para ML)")
            print("=" * 70)

            # ============================================================
            # 1. Verificar se tabela ja existe
            # ============================================================
            existe = db.session.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_name = 'evento_supply_chain')"
            )).scalar()

            if existe:
                count = db.session.execute(text(
                    "SELECT count(*) FROM evento_supply_chain"
                )).scalar()
                print(f"\n[AVISO] Tabela evento_supply_chain ja existe ({count} registros).")
                print("A function e os triggers serao recriados (CREATE OR REPLACE / DROP + CREATE).")
                print("Os dados existentes NAO serao apagados.\n")
            else:
                print("\n[INFO] Criando tabela evento_supply_chain...\n")

            # ============================================================
            # 2. Ler e executar SQL de migracao
            # ============================================================
            sql_path = os.path.join(os.path.dirname(__file__), 'criar_auditoria_supply_chain.sql')

            if not os.path.exists(sql_path):
                print(f"[ERRO] Arquivo SQL nao encontrado: {sql_path}")
                return False

            with open(sql_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # Executar SQL completo
            # Separar statements por ';' nao e seguro (functions tem ';' interno)
            # Usar execute direto — PostgreSQL aceita multiple statements
            db.session.execute(text(sql_content))
            db.session.commit()

            # ============================================================
            # 3. Verificacao pos-migracao
            # ============================================================
            print("\n" + "=" * 70)
            print("VERIFICACAO POS-MIGRACAO")
            print("=" * 70)

            # 3.1 Tabela existe?
            existe = db.session.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_name = 'evento_supply_chain')"
            )).scalar()
            status = "OK" if existe else "ERRO"
            print(f"  [{status}] Tabela evento_supply_chain")

            # 3.2 Colunas corretas?
            colunas = db.session.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'evento_supply_chain' "
                "ORDER BY ordinal_position"
            )).fetchall()
            colunas_nomes = [c[0] for c in colunas]
            print(f"  [OK] {len(colunas_nomes)} colunas: {', '.join(colunas_nomes)}")

            # 3.3 Indices?
            indices = db.session.execute(text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'evento_supply_chain'"
            )).fetchall()
            print(f"  [OK] {len(indices)} indices")
            for idx in indices:
                print(f"       - {idx[0]}")

            # 3.4 Triggers?
            triggers = db.session.execute(text(
                "SELECT trigger_name, event_object_table, event_manipulation "
                "FROM information_schema.triggers "
                "WHERE trigger_name LIKE 'trg_audit_%' "
                "ORDER BY event_object_table"
            )).fetchall()
            print(f"  [OK] {len(triggers)} triggers")
            for trg in triggers:
                print(f"       - {trg[0]} ON {trg[1]} ({trg[2]})")

            # 3.5 Trigger function?
            func_exists = db.session.execute(text(
                "SELECT EXISTS (SELECT FROM pg_proc "
                "WHERE proname = 'audit_supply_chain_trigger')"
            )).scalar()
            status = "OK" if func_exists else "ERRO"
            print(f"  [{status}] Funcao audit_supply_chain_trigger()")

            print("\n" + "=" * 70)
            if existe and func_exists and len(triggers) >= 6:
                print("MIGRACAO CONCLUIDA COM SUCESSO")
            else:
                print("MIGRACAO CONCLUIDA COM AVISOS — verificar itens acima")
            print("=" * 70)

            return True

        except Exception as e:
            db.session.rollback()
            print(f"\n[ERRO FATAL] Migracao falhou: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    sucesso = executar_migracao()
    sys.exit(0 if sucesso else 1)
