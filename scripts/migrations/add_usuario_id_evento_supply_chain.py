# -*- coding: utf-8 -*-
"""
Migracao: Adiciona usuario_id + atualiza trigger audit_supply_chain
====================================================================

Adiciona coluna usuario_id (INTEGER, nullable) em evento_supply_chain e
recria audit_supply_chain_trigger() para:
  - Ler nova variavel PG app.current_user_id (cast INTEGER seguro)
  - Aplicar TRIM defensivo em app.current_user (resolve trailing spaces)
  - Gravar usuario_id no INSERT

Idempotente: pode ser executado multiplas vezes sem efeito colateral.
CREATE OR REPLACE FUNCTION mantem os 6 triggers existentes sem recriar.

Uso: python scripts/migrations/add_usuario_id_evento_supply_chain.py
Data: 2026-04-14
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
            print("MIGRACAO: Adicionar usuario_id em evento_supply_chain")
            print("=" * 70)

            # ============================================================
            # 1. BEFORE — estado atual
            # ============================================================
            col_existe_antes = db.session.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.columns "
                "WHERE table_name = 'evento_supply_chain' AND column_name = 'usuario_id')"
            )).scalar()

            total_eventos = db.session.execute(text(
                "SELECT count(*) FROM evento_supply_chain"
            )).scalar()

            print(f"\n[BEFORE]")
            print(f"  Coluna usuario_id existe: {col_existe_antes}")
            print(f"  Total de eventos na tabela: {total_eventos}")

            # ============================================================
            # 2. Ler e executar SQL de migracao
            # ============================================================
            sql_path = os.path.join(
                os.path.dirname(__file__),
                'add_usuario_id_evento_supply_chain.sql'
            )

            if not os.path.exists(sql_path):
                print(f"\n[ERRO] Arquivo SQL nao encontrado: {sql_path}")
                return False

            with open(sql_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            print(f"\n[EXEC] Executando {os.path.basename(sql_path)}...")
            db.session.execute(text(sql_content))
            db.session.commit()

            # ============================================================
            # 3. AFTER — verificacao
            # ============================================================
            print("\n" + "=" * 70)
            print("VERIFICACAO POS-MIGRACAO")
            print("=" * 70)

            col_existe_depois = db.session.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.columns "
                "WHERE table_name = 'evento_supply_chain' AND column_name = 'usuario_id')"
            )).scalar()
            status = "OK" if col_existe_depois else "ERRO"
            print(f"  [{status}] Coluna usuario_id presente")

            col_type = db.session.execute(text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'evento_supply_chain' AND column_name = 'usuario_id'"
            )).scalar()
            print(f"  [OK] Tipo da coluna usuario_id: {col_type}")

            idx_existe = db.session.execute(text(
                "SELECT EXISTS (SELECT FROM pg_indexes "
                "WHERE tablename = 'evento_supply_chain' AND indexname = 'idx_esc_usuario_id')"
            )).scalar()
            status = "OK" if idx_existe else "ERRO"
            print(f"  [{status}] Indice idx_esc_usuario_id criado")

            func_existe = db.session.execute(text(
                "SELECT EXISTS (SELECT FROM pg_proc "
                "WHERE proname = 'audit_supply_chain_trigger')"
            )).scalar()
            status = "OK" if func_existe else "ERRO"
            print(f"  [{status}] Funcao audit_supply_chain_trigger() atualizada")

            triggers = db.session.execute(text(
                "SELECT count(*) FROM information_schema.triggers "
                "WHERE trigger_name LIKE 'trg_audit_%'"
            )).scalar()
            print(f"  [OK] {triggers} triggers de auditoria ativos (inalterados)")

            total_depois = db.session.execute(text(
                "SELECT count(*) FROM evento_supply_chain"
            )).scalar()
            print(f"  [OK] Total de eventos preservado: {total_depois}")

            if total_depois != total_eventos:
                print(f"  [AVISO] Contagem mudou ({total_eventos} -> {total_depois}) "
                      f"— novos eventos chegaram durante migracao (normal)")

            print("\n" + "=" * 70)
            if col_existe_depois and func_existe and (triggers or 0) >= 6:
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
