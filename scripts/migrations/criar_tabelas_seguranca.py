"""
Migration: Criar tabelas do modulo de Seguranca
=================================================

4 tabelas:
- seguranca_varreduras
- seguranca_vulnerabilidades
- seguranca_scores
- seguranca_config

Executar: python scripts/migrations/criar_tabelas_seguranca.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text, inspect


def criar_tabelas():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        tabelas_existentes = inspector.get_table_names()

        # ── 1. seguranca_varreduras ──
        if 'seguranca_varreduras' in tabelas_existentes:
            print("[OK] Tabela 'seguranca_varreduras' ja existe.")
        else:
            print("Criando tabela 'seguranca_varreduras'...")
            db.session.execute(text("""
                CREATE TABLE seguranca_varreduras (
                    id SERIAL PRIMARY KEY,
                    tipo VARCHAR(30) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'EM_EXECUCAO',
                    iniciado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    concluido_em TIMESTAMP,
                    total_verificados INTEGER DEFAULT 0,
                    total_vulnerabilidades INTEGER DEFAULT 0,
                    detalhes JSONB,
                    disparado_por VARCHAR(120)
                );
            """))
            print("[CRIADA] seguranca_varreduras")

        # ── 2. seguranca_vulnerabilidades ──
        if 'seguranca_vulnerabilidades' in tabelas_existentes:
            print("[OK] Tabela 'seguranca_vulnerabilidades' ja existe.")
        else:
            print("Criando tabela 'seguranca_vulnerabilidades'...")
            db.session.execute(text("""
                CREATE TABLE seguranca_vulnerabilidades (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES usuarios(id),
                    varredura_id INTEGER REFERENCES seguranca_varreduras(id),
                    categoria VARCHAR(30) NOT NULL,
                    severidade VARCHAR(10) NOT NULL,
                    titulo VARCHAR(200) NOT NULL,
                    descricao TEXT,
                    dados JSONB,
                    status VARCHAR(20) NOT NULL DEFAULT 'ABERTA',
                    notificado BOOLEAN DEFAULT FALSE,
                    notificado_em TIMESTAMP,
                    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_seguranca_vuln_user_cat_titulo
                        UNIQUE (user_id, categoria, titulo)
                );

                CREATE INDEX ix_seguranca_vuln_user_status
                    ON seguranca_vulnerabilidades (user_id, status);
                CREATE INDEX ix_seguranca_vuln_cat_sev
                    ON seguranca_vulnerabilidades (categoria, severidade);
            """))
            print("[CRIADA] seguranca_vulnerabilidades")

        # ── 3. seguranca_scores ──
        if 'seguranca_scores' in tabelas_existentes:
            print("[OK] Tabela 'seguranca_scores' ja existe.")
        else:
            print("Criando tabela 'seguranca_scores'...")
            db.session.execute(text("""
                CREATE TABLE seguranca_scores (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES usuarios(id),
                    score INTEGER NOT NULL,
                    componentes JSONB,
                    vulnerabilidades_abertas INTEGER DEFAULT 0,
                    vulnerabilidades_criticas INTEGER DEFAULT 0,
                    calculado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX ix_seguranca_score_user_calc
                    ON seguranca_scores (user_id, calculado_em);
            """))
            print("[CRIADA] seguranca_scores")

        # ── 4. seguranca_config ──
        if 'seguranca_config' in tabelas_existentes:
            print("[OK] Tabela 'seguranca_config' ja existe.")
        else:
            print("Criando tabela 'seguranca_config'...")
            db.session.execute(text("""
                CREATE TABLE seguranca_config (
                    id SERIAL PRIMARY KEY,
                    chave VARCHAR(100) UNIQUE NOT NULL,
                    valor TEXT,
                    descricao VARCHAR(300),
                    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    atualizado_por VARCHAR(120)
                );
            """))
            print("[CRIADA] seguranca_config")

            # Inserir defaults
            print("Inserindo configuracoes padrao...")
            db.session.execute(text("""
                INSERT INTO seguranca_config (chave, valor, descricao) VALUES
                ('hibp_api_key', '', 'API Key do HaveIBeenPwned (opcional, email breaches)'),
                ('scan_interval_hours', '24', 'Intervalo entre varreduras automaticas (horas)'),
                ('password_min_entropy', '3', 'Score minimo de senha (0-4, zxcvbn)'),
                ('domains_to_monitor', '', 'Dominios adicionais para monitorar (separados por virgula)'),
                ('auto_scan_enabled', 'true', 'Habilitar varredura automatica');
            """))
            print("[OK] Defaults inseridos")

        db.session.commit()

        # ── Verificacao final ──
        inspector = inspect(db.engine)
        tabelas_depois = inspector.get_table_names()
        esperadas = [
            'seguranca_varreduras',
            'seguranca_vulnerabilidades',
            'seguranca_scores',
            'seguranca_config',
        ]
        for t in esperadas:
            status = "OK" if t in tabelas_depois else "FALHOU"
            print(f"  [{status}] {t}")

        print("\nMigration concluida!")


if __name__ == '__main__':
    criar_tabelas()
