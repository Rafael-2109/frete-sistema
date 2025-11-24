"""
Script de migracao para criar tabelas do IA Trainer.

Tabelas:
- codigo_sistema_gerado: Codigo gerado pelo Claude
- versao_codigo_gerado: Historico de versoes
- sessao_ensino_ia: Sessoes de ensino

Uso:
    python scripts/migrations/criar_tabelas_ia_trainer.py

Criado em: 23/11/2025
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabelas():
    """Cria as tabelas do IA Trainer."""
    app = create_app()

    with app.app_context():
        try:
            # === TABELA: sessao_ensino_ia ===
            print("Criando tabela sessao_ensino_ia...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS sessao_ensino_ia (
                    id SERIAL PRIMARY KEY,

                    -- Origem
                    pergunta_origem_id INTEGER REFERENCES claude_perguntas_nao_respondidas(id),
                    pergunta_original TEXT NOT NULL,

                    -- Decomposicao
                    decomposicao JSONB,

                    -- Debate com Claude
                    historico_debate JSONB,

                    -- Codigo gerado (referencia circular, adicionar depois)
                    codigo_gerado_id INTEGER,

                    -- Status
                    status VARCHAR(30) DEFAULT 'iniciada' NOT NULL,

                    -- Resultado
                    solucao_criada BOOLEAN DEFAULT FALSE NOT NULL,

                    -- Auditoria
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    criado_por VARCHAR(100) NOT NULL,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finalizado_em TIMESTAMP
                );
            """))

            # Indices sessao_ensino_ia
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sessao_ensino_pergunta
                ON sessao_ensino_ia(pergunta_origem_id);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sessao_ensino_status
                ON sessao_ensino_ia(status);
            """))

            # === TABELA: codigo_sistema_gerado ===
            print("Criando tabela codigo_sistema_gerado...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS codigo_sistema_gerado (
                    id SERIAL PRIMARY KEY,

                    -- Identificacao
                    nome VARCHAR(100) NOT NULL UNIQUE,
                    tipo_codigo VARCHAR(30) NOT NULL,
                    dominio VARCHAR(50),

                    -- Gatilhos
                    gatilhos JSONB NOT NULL,
                    composicao VARCHAR(200),

                    -- Definicao tecnica
                    definicao_tecnica TEXT NOT NULL,
                    models_referenciados JSONB,
                    campos_referenciados JSONB,

                    -- Documentacao
                    descricao_claude TEXT NOT NULL,
                    exemplos_uso JSONB,
                    variacoes TEXT,

                    -- Controle de estado
                    ativo BOOLEAN DEFAULT FALSE NOT NULL,
                    validado BOOLEAN DEFAULT FALSE NOT NULL,
                    data_validacao TIMESTAMP,
                    validado_por VARCHAR(100),

                    -- Resultado de teste
                    ultimo_teste_sucesso BOOLEAN,
                    ultimo_teste_erro TEXT,
                    ultimo_teste_em TIMESTAMP,

                    -- Permissoes
                    permite_acao BOOLEAN DEFAULT FALSE NOT NULL,
                    apenas_admin BOOLEAN DEFAULT FALSE NOT NULL,

                    -- Rastreabilidade
                    versao_atual INTEGER DEFAULT 1 NOT NULL,
                    pergunta_origem_id INTEGER REFERENCES claude_perguntas_nao_respondidas(id),
                    sessao_ensino_id INTEGER REFERENCES sessao_ensino_ia(id),

                    -- Auditoria
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    criado_por VARCHAR(100) NOT NULL,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_por VARCHAR(100)
                );
            """))

            # Indices codigo_sistema_gerado
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_codigo_nome
                ON codigo_sistema_gerado(nome);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_codigo_tipo_ativo
                ON codigo_sistema_gerado(tipo_codigo, ativo);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_codigo_dominio
                ON codigo_sistema_gerado(dominio, ativo);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_codigo_pergunta
                ON codigo_sistema_gerado(pergunta_origem_id);
            """))

            # Adiciona FK circular em sessao_ensino_ia
            db.session.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints
                        WHERE constraint_name = 'fk_sessao_codigo_gerado'
                    ) THEN
                        ALTER TABLE sessao_ensino_ia
                        ADD CONSTRAINT fk_sessao_codigo_gerado
                        FOREIGN KEY (codigo_gerado_id) REFERENCES codigo_sistema_gerado(id);
                    END IF;
                END $$;
            """))

            # === TABELA: versao_codigo_gerado ===
            print("Criando tabela versao_codigo_gerado...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS versao_codigo_gerado (
                    id SERIAL PRIMARY KEY,

                    -- Referencia ao codigo
                    codigo_id INTEGER NOT NULL REFERENCES codigo_sistema_gerado(id),
                    versao INTEGER NOT NULL,

                    -- Snapshot
                    tipo_codigo VARCHAR(30) NOT NULL,
                    gatilhos JSONB NOT NULL,
                    definicao_tecnica TEXT NOT NULL,
                    descricao_claude TEXT NOT NULL,

                    -- Motivo da alteracao
                    motivo_alteracao TEXT,

                    -- Resultado de teste
                    teste_sucesso BOOLEAN,
                    teste_erro TEXT,

                    -- Auditoria
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    criado_por VARCHAR(100) NOT NULL,

                    -- Constraint unica
                    CONSTRAINT uk_codigo_versao UNIQUE (codigo_id, versao)
                );
            """))

            # Indices versao_codigo_gerado
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_versao_codigo
                ON versao_codigo_gerado(codigo_id);
            """))

            db.session.commit()
            print("\n✓ Todas as tabelas do IA Trainer criadas com sucesso!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Erro ao criar tabelas: {e}")
            return False


def verificar_estrutura():
    """Verifica a estrutura das tabelas criadas."""
    app = create_app()

    with app.app_context():
        tabelas = ['sessao_ensino_ia', 'codigo_sistema_gerado', 'versao_codigo_gerado']

        for tabela in tabelas:
            print(f"\n--- Tabela: {tabela} ---")
            try:
                resultado = db.session.execute(text(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = '{tabela}'
                    ORDER BY ordinal_position
                    LIMIT 15;
                """))

                colunas = resultado.fetchall()
                for col in colunas:
                    nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
                    print(f"  {col[0]}: {col[1]} {nullable}")

                if len(colunas) >= 15:
                    print("  ... (mais colunas)")

            except Exception as e:
                print(f"  Erro: {e}")


def adicionar_campo_solucao_criada():
    """Adiciona campo solucao_criada na tabela claude_perguntas_nao_respondidas."""
    app = create_app()

    with app.app_context():
        try:
            # Verifica se coluna ja existe
            resultado = db.session.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'claude_perguntas_nao_respondidas'
                AND column_name = 'solucao_criada';
            """))

            if resultado.fetchone():
                print("✓ Campo solucao_criada ja existe.")
                return True

            # Adiciona coluna
            db.session.execute(text("""
                ALTER TABLE claude_perguntas_nao_respondidas
                ADD COLUMN solucao_criada BOOLEAN DEFAULT FALSE;
            """))

            db.session.commit()
            print("✓ Campo solucao_criada adicionado com sucesso!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"✗ Erro ao adicionar campo: {e}")
            return False


if __name__ == "__main__":
    print("=" * 60)
    print("Migracao: Criar tabelas do IA Trainer")
    print("=" * 60)

    # Adiciona campo na tabela de perguntas nao respondidas
    print("\n1. Atualizando tabela claude_perguntas_nao_respondidas...")
    adicionar_campo_solucao_criada()

    # Cria tabelas do IA Trainer
    print("\n2. Criando tabelas do IA Trainer...")
    sucesso = criar_tabelas()

    if sucesso:
        print("\n3. Verificando estrutura...")
        verificar_estrutura()

    print("\n" + "=" * 60)
    print("Migracao finalizada.")
