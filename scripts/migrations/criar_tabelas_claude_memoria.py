"""
Migração: Criar tabelas de memória do Claude AI Lite.

Tabelas criadas:
- claude_historico_conversa: Histórico de mensagens por usuário
- claude_aprendizado: Conhecimento permanente (por usuário ou global)

Executar: python scripts/migrations/criar_tabelas_claude_memoria.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabelas_claude_memoria():
    app = create_app()

    with app.app_context():
        try:
            # ============================================
            # TABELA: claude_historico_conversa
            # ============================================
            print("\n[1/2] Criando tabela claude_historico_conversa...")

            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS claude_historico_conversa (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
                    tipo VARCHAR(20) NOT NULL,
                    conteudo TEXT NOT NULL,
                    metadados JSONB,
                    criado_em TIMESTAMP DEFAULT NOW() NOT NULL
                );
            """))

            # Índices
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_claude_hist_usuario
                ON claude_historico_conversa(usuario_id);
            """))

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_claude_hist_tipo
                ON claude_historico_conversa(tipo);
            """))

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_claude_hist_criado
                ON claude_historico_conversa(criado_em);
            """))

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_claude_hist_usuario_data
                ON claude_historico_conversa(usuario_id, criado_em);
            """))

            print("   ✅ Tabela claude_historico_conversa criada!")

            # ============================================
            # TABELA: claude_aprendizado
            # ============================================
            print("\n[2/2] Criando tabela claude_aprendizado...")

            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS claude_aprendizado (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER REFERENCES usuarios(id),
                    categoria VARCHAR(50) NOT NULL,
                    chave VARCHAR(100) NOT NULL,
                    valor TEXT NOT NULL,
                    contexto JSONB,
                    ativo BOOLEAN DEFAULT TRUE NOT NULL,
                    prioridade INTEGER DEFAULT 5 NOT NULL,
                    criado_em TIMESTAMP DEFAULT NOW() NOT NULL,
                    criado_por VARCHAR(100),
                    atualizado_em TIMESTAMP DEFAULT NOW(),
                    atualizado_por VARCHAR(100)
                );
            """))

            # Índices
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_claude_aprend_usuario
                ON claude_aprendizado(usuario_id);
            """))

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_claude_aprend_categoria
                ON claude_aprendizado(categoria);
            """))

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_claude_aprend_chave
                ON claude_aprendizado(chave);
            """))

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_claude_aprend_ativo
                ON claude_aprendizado(ativo);
            """))

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_claude_aprend_usuario_cat
                ON claude_aprendizado(usuario_id, categoria);
            """))

            # Constraint de unicidade (usuario_id + chave)
            db.session.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'uk_claude_aprend_usuario_chave'
                    ) THEN
                        ALTER TABLE claude_aprendizado
                        ADD CONSTRAINT uk_claude_aprend_usuario_chave
                        UNIQUE (usuario_id, chave);
                    END IF;
                END $$;
            """))

            print("   ✅ Tabela claude_aprendizado criada!")

            db.session.commit()

            # ============================================
            # VERIFICAÇÃO
            # ============================================
            print("\n" + "=" * 50)
            print("VERIFICANDO TABELAS CRIADAS:")
            print("=" * 50)

            resultado = db.session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name LIKE 'claude_%'
                ORDER BY table_name;
            """)).fetchall()

            for row in resultado:
                print(f"   ✅ {row[0]}")

            print("\n✅ Migração concluída com sucesso!")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro na migração: {e}")
            raise


if __name__ == '__main__':
    criar_tabelas_claude_memoria()
