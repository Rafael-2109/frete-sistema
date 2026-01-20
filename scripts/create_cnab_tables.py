"""
Script para criar tabelas CNAB400 no banco de dados.

Uso:
    python scripts/create_cnab_tables.py

Ou via Render Shell:
    Copiar e colar o SQL gerado no console do banco
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


# SQL para criar as tabelas (para uso no Render Shell)
SQL_CREATE_TABLES = """
-- =============================================================================
-- CNAB400 - Tabelas de Retorno Bancário
-- Executar no Render Shell ou psql
-- =============================================================================

-- Tabela de Lotes (arquivos importados)
CREATE TABLE IF NOT EXISTS cnab_retorno_lote (
    id SERIAL PRIMARY KEY,
    arquivo_nome VARCHAR(255) NOT NULL,
    banco_codigo VARCHAR(3) NOT NULL,
    banco_nome VARCHAR(100),
    data_arquivo DATE,
    data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Estatísticas
    total_registros INTEGER DEFAULT 0,
    registros_liquidados INTEGER DEFAULT 0,
    registros_confirmados INTEGER DEFAULT 0,
    registros_baixados INTEGER DEFAULT 0,
    registros_com_match INTEGER DEFAULT 0,
    registros_sem_match INTEGER DEFAULT 0,
    registros_ja_pagos INTEGER DEFAULT 0,
    valor_total_liquidado NUMERIC(15, 2) DEFAULT 0,

    -- Status
    status VARCHAR(30) DEFAULT 'IMPORTADO',
    processado_por VARCHAR(100),
    erro_mensagem TEXT,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice para status do lote
CREATE INDEX IF NOT EXISTS idx_cnab_lote_status ON cnab_retorno_lote(status);


-- Tabela de Itens (registros do arquivo)
CREATE TABLE IF NOT EXISTS cnab_retorno_item (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER NOT NULL REFERENCES cnab_retorno_lote(id) ON DELETE CASCADE,

    -- Dados do CNAB
    tipo_registro VARCHAR(1),
    nosso_numero VARCHAR(20),
    seu_numero VARCHAR(25),
    cnpj_pagador VARCHAR(20),

    -- Ocorrência
    codigo_ocorrencia VARCHAR(2),
    descricao_ocorrencia VARCHAR(100),
    data_ocorrencia DATE,

    -- Valores
    valor_titulo NUMERIC(15, 2),
    valor_pago NUMERIC(15, 2),
    valor_juros NUMERIC(15, 2),
    valor_desconto NUMERIC(15, 2),
    valor_abatimento NUMERIC(15, 2),

    -- Datas
    data_vencimento DATE,
    data_credito DATE,

    -- Dados extraídos
    nf_extraida VARCHAR(20),
    parcela_extraida VARCHAR(10),

    -- Vinculação
    conta_a_receber_id INTEGER REFERENCES contas_a_receber(id),

    -- Matching
    status_match VARCHAR(30) DEFAULT 'PENDENTE',
    match_score INTEGER,
    match_criterio VARCHAR(100),

    -- Processamento
    processado BOOLEAN DEFAULT FALSE,
    data_processamento TIMESTAMP,
    erro_mensagem TEXT,

    -- Debug
    linha_original TEXT,
    numero_linha INTEGER,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para buscas comuns
CREATE INDEX IF NOT EXISTS idx_cnab_item_lote ON cnab_retorno_item(lote_id);
CREATE INDEX IF NOT EXISTS idx_cnab_item_nosso_numero ON cnab_retorno_item(nosso_numero);
CREATE INDEX IF NOT EXISTS idx_cnab_item_seu_numero ON cnab_retorno_item(seu_numero);
CREATE INDEX IF NOT EXISTS idx_cnab_item_cnpj ON cnab_retorno_item(cnpj_pagador);
CREATE INDEX IF NOT EXISTS idx_cnab_item_status ON cnab_retorno_item(status_match);
CREATE INDEX IF NOT EXISTS idx_cnab_item_ocorrencia ON cnab_retorno_item(codigo_ocorrencia);
CREATE INDEX IF NOT EXISTS idx_cnab_item_processado ON cnab_retorno_item(processado);
CREATE INDEX IF NOT EXISTS idx_cnab_item_lote_status ON cnab_retorno_item(lote_id, status_match);
CREATE INDEX IF NOT EXISTS idx_cnab_item_conta_receber ON cnab_retorno_item(conta_a_receber_id);

-- Comentários nas tabelas
COMMENT ON TABLE cnab_retorno_lote IS 'Lotes de arquivos CNAB400 importados';
COMMENT ON TABLE cnab_retorno_item IS 'Itens/registros individuais do arquivo CNAB400';

COMMENT ON COLUMN cnab_retorno_lote.status IS 'IMPORTADO, AGUARDANDO_REVISAO, APROVADO, PROCESSANDO, CONCLUIDO, PARCIAL, ERRO';
COMMENT ON COLUMN cnab_retorno_item.status_match IS 'PENDENTE, MATCH_ENCONTRADO, SEM_MATCH, JA_PAGO, FORMATO_INVALIDO, NAO_APLICAVEL, PROCESSADO, ERRO';
COMMENT ON COLUMN cnab_retorno_item.codigo_ocorrencia IS '02=Entrada Confirmada, 06=Liquidação, 10=Baixado, etc.';

SELECT 'Tabelas CNAB400 criadas com sucesso!' as resultado;
"""


def criar_tabelas_via_orm():
    """Cria tabelas usando SQLAlchemy ORM (preferido)"""
    app = create_app()
    with app.app_context():
        try:
            # Importa os modelos para registrar
            from app.financeiro.models import CnabRetornoLote, CnabRetornoItem

            # Cria apenas as tabelas que não existem
            db.create_all()

            print("✅ Tabelas CNAB400 criadas via ORM!")
            return True
        except Exception as e:
            print(f"❌ Erro ao criar tabelas via ORM: {e}")
            return False


def criar_tabelas_via_sql():
    """Cria tabelas usando SQL direto"""
    app = create_app()
    with app.app_context():
        try:
            # Executa cada statement separadamente
            for statement in SQL_CREATE_TABLES.split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    db.session.execute(text(statement))

            db.session.commit()
            print("✅ Tabelas CNAB400 criadas via SQL!")
            return True
        except Exception as e:
            print(f"❌ Erro ao criar tabelas via SQL: {e}")
            db.session.rollback()
            return False


def verificar_tabelas():
    """Verifica se as tabelas existem"""
    app = create_app()
    with app.app_context():
        try:
            result = db.session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('cnab_retorno_lote', 'cnab_retorno_item')
                ORDER BY table_name;
            """))
            tabelas = [row[0] for row in result]

            if len(tabelas) == 2:
                print(f"✅ Tabelas encontradas: {', '.join(tabelas)}")
                return True
            else:
                print(f"⚠️ Tabelas encontradas: {tabelas} (esperado 2)")
                return False
        except Exception as e:
            print(f"❌ Erro ao verificar tabelas: {e}")
            return False


def main():
    print("=" * 60)
    print("CRIAÇÃO DE TABELAS CNAB400")
    print("=" * 60)

    # Tenta via ORM primeiro
    print("\n1. Tentando criar via SQLAlchemy ORM...")
    if criar_tabelas_via_orm():
        print("\n2. Verificando tabelas...")
        verificar_tabelas()
        return

    # Se falhar, tenta via SQL
    print("\n1. ORM falhou, tentando via SQL direto...")
    if criar_tabelas_via_sql():
        print("\n2. Verificando tabelas...")
        verificar_tabelas()
        return

    # Se ambos falharem, exibe SQL para execução manual
    print("\n" + "=" * 60)
    print("⚠️ Falha na criação automática. Execute o SQL abaixo manualmente:")
    print("=" * 60)
    print(SQL_CREATE_TABLES)


if __name__ == '__main__':
    main()
