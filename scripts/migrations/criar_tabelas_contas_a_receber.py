"""
Script de Migração: Criar tabelas de Contas a Receber
=====================================================

Este script cria as seguintes tabelas:
1. contas_a_receber_tipos - Tabela de domínio para tipos
2. liberacao_antecipacao - Configuração de prazos de liberação
3. contas_a_receber - Tabela principal de contas a receber
4. contas_a_receber_abatimento - Abatimentos vinculados
5. contas_a_receber_snapshot - Histórico de alterações do Odoo

Data: 2025-11-27
Autor: Sistema de Fretes
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabelas_contas_a_receber():
    """Cria todas as tabelas de Contas a Receber"""

    app = create_app()

    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRAÇÃO: Criar Tabelas de Contas a Receber")
            print("=" * 60)

            # =====================================================
            # 1. TABELA: contas_a_receber_tipos
            # =====================================================
            print("\n[1/5] Criando tabela: contas_a_receber_tipos...")

            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS contas_a_receber_tipos (
                    id SERIAL PRIMARY KEY,
                    tipo VARCHAR(100) NOT NULL,
                    considera_a_receber BOOLEAN NOT NULL DEFAULT TRUE,
                    tabela VARCHAR(50) NOT NULL,
                    campo VARCHAR(50) NOT NULL,
                    explicacao TEXT,
                    ativo BOOLEAN NOT NULL DEFAULT TRUE,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    criado_por VARCHAR(100),
                    CONSTRAINT uq_tipo_tabela_campo UNIQUE (tipo, tabela, campo)
                );
            """))

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_tipo_tabela_campo
                ON contas_a_receber_tipos (tabela, campo);
            """))

            print("   ✅ Tabela contas_a_receber_tipos criada com sucesso!")

            # =====================================================
            # 2. TABELA: liberacao_antecipacao
            # =====================================================
            print("\n[2/5] Criando tabela: liberacao_antecipacao...")

            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS liberacao_antecipacao (
                    id SERIAL PRIMARY KEY,
                    criterio_identificacao VARCHAR(20) NOT NULL,
                    identificador VARCHAR(255) NOT NULL,
                    uf VARCHAR(100) NOT NULL DEFAULT 'TODOS',
                    dias_uteis_previsto INTEGER NOT NULL,
                    ativo BOOLEAN NOT NULL DEFAULT TRUE,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    criado_por VARCHAR(100),
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_por VARCHAR(100)
                );
            """))

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_liberacao_criterio
                ON liberacao_antecipacao (criterio_identificacao, identificador);
            """))

            print("   ✅ Tabela liberacao_antecipacao criada com sucesso!")

            # =====================================================
            # 3. TABELA: contas_a_receber
            # =====================================================
            print("\n[3/5] Criando tabela: contas_a_receber...")

            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS contas_a_receber (
                    id SERIAL PRIMARY KEY,

                    -- Identificação única (chave composta)
                    empresa INTEGER NOT NULL,
                    titulo_nf VARCHAR(20) NOT NULL,
                    parcela VARCHAR(10) NOT NULL,

                    -- Cliente
                    cnpj VARCHAR(20),
                    raz_social VARCHAR(255),
                    raz_social_red VARCHAR(100),
                    uf_cliente VARCHAR(2),

                    -- Datas do Odoo
                    emissao DATE,
                    vencimento DATE,

                    -- Valores do Odoo
                    valor_original FLOAT,
                    desconto_percentual FLOAT,
                    desconto FLOAT,

                    -- Tipo do título
                    tipo_titulo VARCHAR(100),

                    -- Status do Odoo
                    parcela_paga BOOLEAN DEFAULT FALSE,
                    status_pagamento_odoo VARCHAR(50),

                    -- Campos calculados
                    valor_titulo FLOAT,
                    liberacao_prevista_antecipacao DATE,

                    -- Campos do sistema (confirmação)
                    confirmacao_tipo_id INTEGER REFERENCES contas_a_receber_tipos(id),
                    forma_confirmacao_tipo_id INTEGER REFERENCES contas_a_receber_tipos(id),
                    data_confirmacao TIMESTAMP,
                    confirmacao_entrega TEXT,

                    -- Observações e alertas
                    observacao TEXT,
                    alerta BOOLEAN NOT NULL DEFAULT FALSE,

                    -- Ação necessária
                    acao_necessaria_tipo_id INTEGER REFERENCES contas_a_receber_tipos(id),
                    obs_acao_necessaria TEXT,
                    data_lembrete DATE,

                    -- Campos enriquecidos (EntregaMonitorada)
                    entrega_monitorada_id INTEGER REFERENCES entregas_monitoradas(id),
                    data_entrega_prevista DATE,
                    data_hora_entrega_realizada TIMESTAMP,
                    status_finalizacao VARCHAR(50),
                    nova_nf VARCHAR(20),
                    reagendar BOOLEAN DEFAULT FALSE,
                    data_embarque DATE,
                    transportadora VARCHAR(255),
                    vendedor VARCHAR(100),
                    canhoto_arquivo VARCHAR(500),

                    -- AgendamentoEntrega (último)
                    ultimo_agendamento_data DATE,
                    ultimo_agendamento_status VARCHAR(20),
                    ultimo_agendamento_protocolo VARCHAR(100),

                    -- FaturamentoProduto
                    nf_cancelada BOOLEAN NOT NULL DEFAULT FALSE,

                    -- NF no CD (EntregaMonitorada)
                    nf_cd BOOLEAN NOT NULL DEFAULT FALSE,

                    -- Auditoria e controle
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    criado_por VARCHAR(100),
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_por VARCHAR(100),

                    -- Controle de sincronização
                    odoo_write_date TIMESTAMP,
                    ultima_sincronizacao TIMESTAMP,

                    -- Constraint de unicidade
                    CONSTRAINT uq_conta_receber_empresa_nf_parcela UNIQUE (empresa, titulo_nf, parcela)
                );
            """))

            # Índices
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conta_receber_empresa ON contas_a_receber (empresa);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conta_receber_titulo_nf ON contas_a_receber (titulo_nf);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conta_receber_parcela ON contas_a_receber (parcela);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conta_receber_vencimento ON contas_a_receber (vencimento);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conta_receber_cnpj ON contas_a_receber (cnpj);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conta_receber_nf ON contas_a_receber (titulo_nf);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conta_receber_uf_cliente ON contas_a_receber (uf_cliente);
            """))

            print("   ✅ Tabela contas_a_receber criada com sucesso!")

            # =====================================================
            # 4. TABELA: contas_a_receber_abatimento
            # =====================================================
            print("\n[4/5] Criando tabela: contas_a_receber_abatimento...")

            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS contas_a_receber_abatimento (
                    id SERIAL PRIMARY KEY,

                    -- FK para ContasAReceber
                    conta_a_receber_id INTEGER NOT NULL REFERENCES contas_a_receber(id) ON DELETE CASCADE,

                    -- Tipo do abatimento
                    tipo_id INTEGER REFERENCES contas_a_receber_tipos(id),

                    -- Dados do abatimento
                    motivo TEXT,
                    doc_motivo VARCHAR(255),
                    valor FLOAT NOT NULL,

                    -- Se é previsto ou já realizado
                    previsto BOOLEAN NOT NULL DEFAULT TRUE,

                    -- Datas
                    data DATE,
                    data_vencimento DATE,

                    -- Auditoria
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    criado_por VARCHAR(100),
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_por VARCHAR(100)
                );
            """))

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_abatimento_conta
                ON contas_a_receber_abatimento (conta_a_receber_id);
            """))

            print("   ✅ Tabela contas_a_receber_abatimento criada com sucesso!")

            # =====================================================
            # 5. TABELA: contas_a_receber_snapshot
            # =====================================================
            print("\n[5/5] Criando tabela: contas_a_receber_snapshot...")

            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS contas_a_receber_snapshot (
                    id SERIAL PRIMARY KEY,

                    -- FK para ContasAReceber
                    conta_a_receber_id INTEGER NOT NULL REFERENCES contas_a_receber(id) ON DELETE CASCADE,

                    -- Campo alterado
                    campo VARCHAR(50) NOT NULL,

                    -- Valores (JSON para suportar diferentes tipos)
                    valor_anterior TEXT,
                    valor_novo TEXT,

                    -- Auditoria
                    alterado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    alterado_por VARCHAR(100),

                    -- Referência do Odoo
                    odoo_write_date TIMESTAMP
                );
            """))

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_snapshot_conta_campo
                ON contas_a_receber_snapshot (conta_a_receber_id, campo);
            """))

            print("   ✅ Tabela contas_a_receber_snapshot criada com sucesso!")

            # Commit das alterações
            db.session.commit()

            print("\n" + "=" * 60)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 60)
            print("\nTabelas criadas:")
            print("  1. contas_a_receber_tipos")
            print("  2. liberacao_antecipacao")
            print("  3. contas_a_receber")
            print("  4. contas_a_receber_abatimento")
            print("  5. contas_a_receber_snapshot")
            print("\n")

            return True

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO na migração: {e}")
            import traceback
            traceback.print_exc()
            return False


def verificar_tabelas():
    """Verifica se as tabelas foram criadas corretamente"""

    app = create_app()

    with app.app_context():
        try:
            print("\n" + "=" * 60)
            print("VERIFICAÇÃO: Tabelas de Contas a Receber")
            print("=" * 60)

            tabelas = [
                'contas_a_receber_tipos',
                'liberacao_antecipacao',
                'contas_a_receber',
                'contas_a_receber_abatimento',
                'contas_a_receber_snapshot'
            ]

            for tabela in tabelas:
                result = db.session.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = '{tabela}'
                    );
                """)).scalar()

                status = "✅" if result else "❌"
                print(f"  {status} {tabela}")

            print("\n")
            return True

        except Exception as e:
            print(f"\n❌ ERRO na verificação: {e}")
            return False


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migração: Criar tabelas de Contas a Receber')
    parser.add_argument('--verificar', action='store_true', help='Apenas verificar se tabelas existem')

    args = parser.parse_args()

    if args.verificar:
        verificar_tabelas()
    else:
        criar_tabelas_contas_a_receber()
        verificar_tabelas()
