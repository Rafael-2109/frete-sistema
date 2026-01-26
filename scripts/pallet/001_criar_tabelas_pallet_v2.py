#!/usr/bin/env python
"""
Script de criação das tabelas do módulo de Pallets v2

Este script cria as 5 novas tabelas para o módulo de pallets reestruturado:
- pallet_nf_remessa: NFs de remessa de pallet
- pallet_creditos: Créditos de pallet a receber
- pallet_documentos: Documentos de enriquecimento (canhotos, vales)
- pallet_solucoes: Soluções de créditos (baixa, venda, recebimento, substituição)
- pallet_nf_solucoes: Soluções documentais de NF (devolução, retorno, cancelamento)

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
IMPLEMENTATION_PLAN.md: Fase 1.2.1

Uso:
    cd /home/rafaelnascimento/projetos/frete_sistema
    source .venv/bin/activate
    python scripts/pallet/001_criar_tabelas_pallet_v2.py
"""
import sys
import os

# Adicionar o diretório raiz ao path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabela_pallet_nf_remessa():
    """Cria a tabela pallet_nf_remessa"""
    sql = """
    CREATE TABLE IF NOT EXISTS pallet_nf_remessa (
        id SERIAL PRIMARY KEY,

        -- Identificação da NF
        numero_nf VARCHAR(20) NOT NULL,
        serie VARCHAR(5),
        chave_nfe VARCHAR(44) UNIQUE,
        data_emissao TIMESTAMP NOT NULL,

        -- Dados Odoo
        odoo_account_move_id INTEGER,
        odoo_picking_id INTEGER,

        -- Empresa emissora (CD, FB, SC)
        empresa VARCHAR(10) NOT NULL,

        -- Destinatário
        tipo_destinatario VARCHAR(20) NOT NULL,
        cnpj_destinatario VARCHAR(20) NOT NULL,
        nome_destinatario VARCHAR(255),

        -- Transportadora (quando destinatário é CLIENTE)
        cnpj_transportadora VARCHAR(20),
        nome_transportadora VARCHAR(255),

        -- Quantidade e valores
        quantidade INTEGER NOT NULL,
        valor_unitario NUMERIC(15, 2) DEFAULT 35.00,
        valor_total NUMERIC(15, 2),

        -- Vínculo com Embarque
        embarque_id INTEGER REFERENCES embarques(id) ON DELETE SET NULL,
        embarque_item_id INTEGER REFERENCES embarque_itens(id) ON DELETE SET NULL,

        -- Status
        status VARCHAR(20) DEFAULT 'ATIVA' NOT NULL,
        qtd_resolvida INTEGER DEFAULT 0 NOT NULL,

        -- Cancelamento
        cancelada BOOLEAN DEFAULT FALSE NOT NULL,
        cancelada_em TIMESTAMP,
        cancelada_por VARCHAR(100),
        motivo_cancelamento VARCHAR(255),

        -- Referência migração
        movimentacao_estoque_id INTEGER,

        -- Observações
        observacao TEXT,

        -- Auditoria
        criado_em TIMESTAMP DEFAULT NOW(),
        criado_por VARCHAR(100),
        atualizado_em TIMESTAMP DEFAULT NOW(),
        atualizado_por VARCHAR(100),

        -- Soft delete
        ativo BOOLEAN DEFAULT TRUE NOT NULL
    );

    -- Índices
    CREATE INDEX IF NOT EXISTS idx_nf_remessa_numero_nf ON pallet_nf_remessa(numero_nf);
    CREATE INDEX IF NOT EXISTS idx_nf_remessa_status ON pallet_nf_remessa(status);
    CREATE INDEX IF NOT EXISTS idx_nf_remessa_cnpj_destinatario ON pallet_nf_remessa(cnpj_destinatario);
    CREATE INDEX IF NOT EXISTS idx_nf_remessa_odoo_account_move_id ON pallet_nf_remessa(odoo_account_move_id);
    CREATE INDEX IF NOT EXISTS idx_nf_remessa_empresa_status ON pallet_nf_remessa(empresa, status);
    CREATE INDEX IF NOT EXISTS idx_nf_remessa_destinatario_tipo ON pallet_nf_remessa(cnpj_destinatario, tipo_destinatario);
    CREATE INDEX IF NOT EXISTS idx_nf_remessa_data_status ON pallet_nf_remessa(data_emissao, status);
    """
    return sql


def criar_tabela_pallet_creditos():
    """Cria a tabela pallet_creditos"""
    sql = """
    CREATE TABLE IF NOT EXISTS pallet_creditos (
        id SERIAL PRIMARY KEY,

        -- Vínculo com NF de remessa
        nf_remessa_id INTEGER NOT NULL REFERENCES pallet_nf_remessa(id) ON DELETE RESTRICT,

        -- Quantidade
        qtd_original INTEGER NOT NULL,
        qtd_saldo INTEGER NOT NULL,

        -- Responsável
        tipo_responsavel VARCHAR(20) NOT NULL,
        cnpj_responsavel VARCHAR(20) NOT NULL,
        nome_responsavel VARCHAR(255),
        uf_responsavel VARCHAR(2),
        cidade_responsavel VARCHAR(100),

        -- Prazo
        prazo_dias INTEGER,
        data_vencimento DATE,

        -- Status
        status VARCHAR(20) DEFAULT 'PENDENTE' NOT NULL,

        -- Referência migração
        movimentacao_estoque_id INTEGER,

        -- Observações
        observacao TEXT,

        -- Auditoria
        criado_em TIMESTAMP DEFAULT NOW(),
        criado_por VARCHAR(100),
        atualizado_em TIMESTAMP DEFAULT NOW(),
        atualizado_por VARCHAR(100),

        -- Soft delete
        ativo BOOLEAN DEFAULT TRUE NOT NULL
    );

    -- Índices
    CREATE INDEX IF NOT EXISTS idx_credito_nf_remessa_id ON pallet_creditos(nf_remessa_id);
    CREATE INDEX IF NOT EXISTS idx_credito_status ON pallet_creditos(status);
    CREATE INDEX IF NOT EXISTS idx_credito_cnpj_responsavel ON pallet_creditos(cnpj_responsavel);
    CREATE INDEX IF NOT EXISTS idx_credito_responsavel_status ON pallet_creditos(cnpj_responsavel, status);
    CREATE INDEX IF NOT EXISTS idx_credito_tipo_status ON pallet_creditos(tipo_responsavel, status);
    CREATE INDEX IF NOT EXISTS idx_credito_vencimento ON pallet_creditos(data_vencimento, status);
    """
    return sql


def criar_tabela_pallet_documentos():
    """Cria a tabela pallet_documentos"""
    sql = """
    CREATE TABLE IF NOT EXISTS pallet_documentos (
        id SERIAL PRIMARY KEY,

        -- Vínculo com crédito
        credito_id INTEGER NOT NULL REFERENCES pallet_creditos(id) ON DELETE RESTRICT,

        -- Tipo do documento (CANHOTO, VALE_PALLET)
        tipo VARCHAR(20) NOT NULL,

        -- Dados do documento
        numero_documento VARCHAR(50),
        data_emissao DATE,
        data_validade DATE,
        quantidade INTEGER NOT NULL,

        -- Arquivo anexo
        arquivo_path VARCHAR(500),
        arquivo_nome VARCHAR(255),
        arquivo_tipo VARCHAR(50),

        -- Emissor
        cnpj_emissor VARCHAR(20),
        nome_emissor VARCHAR(255),

        -- Recebimento
        recebido BOOLEAN DEFAULT FALSE NOT NULL,
        recebido_em TIMESTAMP,
        recebido_por VARCHAR(100),

        -- Arquivamento físico
        pasta_arquivo VARCHAR(100),
        aba_arquivo VARCHAR(50),

        -- Referência migração
        vale_pallet_id INTEGER,

        -- Observações
        observacao TEXT,

        -- Auditoria
        criado_em TIMESTAMP DEFAULT NOW(),
        criado_por VARCHAR(100),
        atualizado_em TIMESTAMP DEFAULT NOW(),
        atualizado_por VARCHAR(100),

        -- Soft delete
        ativo BOOLEAN DEFAULT TRUE NOT NULL
    );

    -- Índices
    CREATE INDEX IF NOT EXISTS idx_documento_credito_id ON pallet_documentos(credito_id);
    CREATE INDEX IF NOT EXISTS idx_documento_tipo_recebido ON pallet_documentos(tipo, recebido);
    CREATE INDEX IF NOT EXISTS idx_documento_validade ON pallet_documentos(data_validade);
    CREATE INDEX IF NOT EXISTS idx_documento_emissor ON pallet_documentos(cnpj_emissor, tipo);
    """
    return sql


def criar_tabela_pallet_solucoes():
    """Cria a tabela pallet_solucoes"""
    sql = """
    CREATE TABLE IF NOT EXISTS pallet_solucoes (
        id SERIAL PRIMARY KEY,

        -- Vínculo com crédito de origem
        credito_id INTEGER NOT NULL REFERENCES pallet_creditos(id) ON DELETE RESTRICT,

        -- Tipo (BAIXA, VENDA, RECEBIMENTO, SUBSTITUICAO)
        tipo VARCHAR(20) NOT NULL,

        -- Quantidade resolvida
        quantidade INTEGER NOT NULL,

        -- Campos para BAIXA
        motivo_baixa VARCHAR(100),
        confirmado_cliente BOOLEAN,
        data_confirmacao DATE,

        -- Campos para VENDA
        nf_venda VARCHAR(20),
        chave_nfe_venda VARCHAR(44),
        data_venda DATE,
        valor_unitario NUMERIC(15, 2),
        valor_total NUMERIC(15, 2),
        cnpj_comprador VARCHAR(20),
        nome_comprador VARCHAR(255),

        -- Campos para RECEBIMENTO
        data_recebimento DATE,
        local_recebimento VARCHAR(100),
        recebido_de VARCHAR(255),
        cnpj_entregador VARCHAR(20),

        -- Campos para SUBSTITUICAO
        credito_destino_id INTEGER REFERENCES pallet_creditos(id) ON DELETE SET NULL,
        nf_destino VARCHAR(20),
        motivo_substituicao VARCHAR(255),

        -- Responsável genérico
        cnpj_responsavel VARCHAR(20),
        nome_responsavel VARCHAR(255),

        -- Referência migração
        vale_pallet_id INTEGER,

        -- Observações
        observacao TEXT,

        -- Auditoria
        criado_em TIMESTAMP DEFAULT NOW(),
        criado_por VARCHAR(100),
        atualizado_em TIMESTAMP DEFAULT NOW(),
        atualizado_por VARCHAR(100),

        -- Soft delete
        ativo BOOLEAN DEFAULT TRUE NOT NULL
    );

    -- Índices
    CREATE INDEX IF NOT EXISTS idx_solucao_credito_id ON pallet_solucoes(credito_id);
    CREATE INDEX IF NOT EXISTS idx_solucao_tipo ON pallet_solucoes(tipo);
    CREATE INDEX IF NOT EXISTS idx_solucao_credito_destino_id ON pallet_solucoes(credito_destino_id);
    CREATE INDEX IF NOT EXISTS idx_solucao_tipo_data ON pallet_solucoes(tipo, criado_em);
    CREATE INDEX IF NOT EXISTS idx_solucao_nf_venda ON pallet_solucoes(nf_venda);
    CREATE INDEX IF NOT EXISTS idx_solucao_credito_tipo ON pallet_solucoes(credito_id, tipo);
    """
    return sql


def criar_tabela_pallet_nf_solucoes():
    """Cria a tabela pallet_nf_solucoes"""
    sql = """
    CREATE TABLE IF NOT EXISTS pallet_nf_solucoes (
        id SERIAL PRIMARY KEY,

        -- Vínculo com NF de remessa
        nf_remessa_id INTEGER NOT NULL REFERENCES pallet_nf_remessa(id) ON DELETE RESTRICT,

        -- Tipo (DEVOLUCAO, RETORNO, CANCELAMENTO)
        tipo VARCHAR(20) NOT NULL,

        -- Quantidade resolvida
        quantidade INTEGER NOT NULL,

        -- Dados da NF de solução
        numero_nf_solucao VARCHAR(20),
        serie_nf_solucao VARCHAR(5),
        chave_nfe_solucao VARCHAR(44) UNIQUE,
        data_nf_solucao TIMESTAMP,

        -- Odoo
        odoo_account_move_id INTEGER,
        odoo_dfe_id INTEGER,

        -- Emitente
        cnpj_emitente VARCHAR(20),
        nome_emitente VARCHAR(255),

        -- Vinculação
        vinculacao VARCHAR(20) DEFAULT 'MANUAL' NOT NULL,

        -- Confirmação
        confirmado BOOLEAN DEFAULT TRUE NOT NULL,
        confirmado_em TIMESTAMP,
        confirmado_por VARCHAR(100),

        -- Rejeição
        rejeitado BOOLEAN DEFAULT FALSE NOT NULL,
        rejeitado_em TIMESTAMP,
        rejeitado_por VARCHAR(100),
        motivo_rejeicao VARCHAR(255),

        -- Info complementar (para match automático)
        info_complementar TEXT,

        -- Observações
        observacao TEXT,

        -- Auditoria
        criado_em TIMESTAMP DEFAULT NOW(),
        criado_por VARCHAR(100),
        atualizado_em TIMESTAMP DEFAULT NOW(),
        atualizado_por VARCHAR(100),

        -- Soft delete
        ativo BOOLEAN DEFAULT TRUE NOT NULL
    );

    -- Índices
    CREATE INDEX IF NOT EXISTS idx_nf_solucao_nf_remessa_id ON pallet_nf_solucoes(nf_remessa_id);
    CREATE INDEX IF NOT EXISTS idx_nf_solucao_tipo ON pallet_nf_solucoes(tipo);
    CREATE INDEX IF NOT EXISTS idx_nf_solucao_numero_nf ON pallet_nf_solucoes(numero_nf_solucao);
    CREATE INDEX IF NOT EXISTS idx_nf_solucao_tipo_vinculacao ON pallet_nf_solucoes(tipo, vinculacao);
    CREATE INDEX IF NOT EXISTS idx_nf_solucao_confirmado ON pallet_nf_solucoes(confirmado, vinculacao);
    CREATE INDEX IF NOT EXISTS idx_nf_solucao_emitente ON pallet_nf_solucoes(cnpj_emitente, tipo);
    """
    return sql


def executar_sql(sql: str, descricao: str):
    """Executa um bloco SQL com tratamento de erro"""
    try:
        print(f"  - {descricao}...", end=" ")
        db.session.execute(text(sql))
        db.session.commit()
        print("OK")
        return True
    except Exception as e:
        print(f"ERRO: {e}")
        db.session.rollback()
        return False


def verificar_tabela_existe(nome_tabela: str) -> bool:
    """Verifica se uma tabela já existe"""
    sql = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = :nome
        );
    """
    result = db.session.execute(text(sql), {'nome': nome_tabela}).scalar()
    return bool(result)


def main():
    """Função principal"""
    print("=" * 60)
    print("CRIAÇÃO DAS TABELAS DO MÓDULO DE PALLETS v2")
    print("=" * 60)
    print()

    app = create_app()
    with app.app_context():
        # Verificar tabelas existentes
        print("Verificando tabelas existentes...")
        tabelas = [
            'pallet_nf_remessa',
            'pallet_creditos',
            'pallet_documentos',
            'pallet_solucoes',
            'pallet_nf_solucoes'
        ]

        for tabela in tabelas:
            existe = verificar_tabela_existe(tabela)
            status = "JÁ EXISTE" if existe else "NÃO EXISTE"
            print(f"  - {tabela}: {status}")

        print()

        # Confirmar execução
        resposta = input("Deseja criar as tabelas que não existem? (s/n): ").strip().lower()
        if resposta != 's':
            print("Operação cancelada.")
            return

        print()
        print("Criando tabelas...")

        # Ordem de criação respeitando FKs
        # 1. pallet_nf_remessa (sem FK para outras tabelas de pallet)
        # 2. pallet_creditos (FK para pallet_nf_remessa)
        # 3. pallet_documentos (FK para pallet_creditos)
        # 4. pallet_solucoes (FK para pallet_creditos)
        # 5. pallet_nf_solucoes (FK para pallet_nf_remessa)

        resultados = []

        if not verificar_tabela_existe('pallet_nf_remessa'):
            resultado = executar_sql(criar_tabela_pallet_nf_remessa(), "Criando pallet_nf_remessa")
            resultados.append(('pallet_nf_remessa', resultado))
        else:
            print("  - pallet_nf_remessa: PULADO (já existe)")
            resultados.append(('pallet_nf_remessa', True))

        if not verificar_tabela_existe('pallet_creditos'):
            resultado = executar_sql(criar_tabela_pallet_creditos(), "Criando pallet_creditos")
            resultados.append(('pallet_creditos', resultado))
        else:
            print("  - pallet_creditos: PULADO (já existe)")
            resultados.append(('pallet_creditos', True))

        if not verificar_tabela_existe('pallet_documentos'):
            resultado = executar_sql(criar_tabela_pallet_documentos(), "Criando pallet_documentos")
            resultados.append(('pallet_documentos', resultado))
        else:
            print("  - pallet_documentos: PULADO (já existe)")
            resultados.append(('pallet_documentos', True))

        if not verificar_tabela_existe('pallet_solucoes'):
            resultado = executar_sql(criar_tabela_pallet_solucoes(), "Criando pallet_solucoes")
            resultados.append(('pallet_solucoes', resultado))
        else:
            print("  - pallet_solucoes: PULADO (já existe)")
            resultados.append(('pallet_solucoes', True))

        if not verificar_tabela_existe('pallet_nf_solucoes'):
            resultado = executar_sql(criar_tabela_pallet_nf_solucoes(), "Criando pallet_nf_solucoes")
            resultados.append(('pallet_nf_solucoes', resultado))
        else:
            print("  - pallet_nf_solucoes: PULADO (já existe)")
            resultados.append(('pallet_nf_solucoes', True))

        print()
        print("=" * 60)
        print("RESUMO:")
        print("=" * 60)
        sucesso = 0
        falha = 0
        for tabela, ok in resultados:
            status = "OK" if ok else "FALHOU"
            print(f"  {tabela}: {status}")
            if ok:
                sucesso += 1
            else:
                falha += 1

        print()
        print(f"Total: {sucesso} sucesso, {falha} falha(s)")

        if falha == 0:
            print()
            print("Todas as tabelas foram criadas com sucesso!")
            print()
            print("PRÓXIMO PASSO:")
            print("  Execute o script de migração de dados:")
            print("  python scripts/pallet/002_migrar_movimentacao_para_nf_remessa.py")
        else:
            print()
            print("ATENÇÃO: Algumas tabelas falharam. Verifique os erros acima.")


if __name__ == '__main__':
    main()
