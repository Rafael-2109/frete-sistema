"""
Migration: Criar tabelas da Fase 2 - Vinculacao NF x PO
Data: 15/01/2026
Descricao: Cria tabelas para validacao e match de NF com PO

Tabelas:
- produto_fornecedor_depara: De-Para de produtos (codigo fornecedor -> interno)
- match_nf_po_item: Resultado do match por item
- divergencia_nf_po: Divergencias para resolucao manual
- validacao_nf_po_dfe: Controle de status por DFE

Uso:
    source .venv/bin/activate && python scripts/migrations/criar_tabelas_fase2_nf_po.py
"""

import sys
import os

# Adiciona o diretorio raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabelas():
    """Cria as tabelas da Fase 2 do recebimento"""

    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("FASE 2: Criando tabelas de Vinculacao NF x PO")
            print("=" * 60)

            # 1. Tabela De-Para
            print("\n[1/4] Criando tabela produto_fornecedor_depara...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS produto_fornecedor_depara (
                    id SERIAL PRIMARY KEY,
                    cnpj_fornecedor VARCHAR(20) NOT NULL,
                    razao_fornecedor VARCHAR(255),
                    cod_produto_fornecedor VARCHAR(50) NOT NULL,
                    descricao_produto_fornecedor VARCHAR(255),
                    cod_produto_interno VARCHAR(50) NOT NULL,
                    nome_produto_interno VARCHAR(255),
                    odoo_product_id INTEGER,
                    um_fornecedor VARCHAR(20),
                    um_interna VARCHAR(20) DEFAULT 'UNITS',
                    fator_conversao NUMERIC(10,4) DEFAULT 1.0000,
                    ativo BOOLEAN DEFAULT TRUE,
                    sincronizado_odoo BOOLEAN DEFAULT FALSE,
                    odoo_supplierinfo_id INTEGER,
                    criado_por VARCHAR(100),
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_por VARCHAR(100),
                    atualizado_em TIMESTAMP,
                    UNIQUE(cnpj_fornecedor, cod_produto_fornecedor)
                )
            """))
            print("   ✓ produto_fornecedor_depara criada")

            # 2. Tabela Validacao DFE (precisa existir antes das outras por FK)
            print("\n[2/4] Criando tabela validacao_nf_po_dfe...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS validacao_nf_po_dfe (
                    id SERIAL PRIMARY KEY,
                    odoo_dfe_id INTEGER NOT NULL UNIQUE,
                    numero_nf VARCHAR(20),
                    serie_nf VARCHAR(10),
                    chave_nfe VARCHAR(44),
                    cnpj_fornecedor VARCHAR(20),
                    razao_fornecedor VARCHAR(255),
                    data_nf DATE,
                    valor_total_nf NUMERIC(15,2),
                    status VARCHAR(20) DEFAULT 'pendente',
                    total_itens INTEGER DEFAULT 0,
                    itens_match INTEGER DEFAULT 0,
                    itens_sem_depara INTEGER DEFAULT 0,
                    itens_sem_po INTEGER DEFAULT 0,
                    itens_preco_diverge INTEGER DEFAULT 0,
                    itens_data_diverge INTEGER DEFAULT 0,
                    itens_qtd_diverge INTEGER DEFAULT 0,
                    po_consolidado_id INTEGER,
                    po_consolidado_name VARCHAR(50),
                    pos_saldo_ids TEXT,
                    pos_cancelados_ids TEXT,
                    acao_executada JSONB,
                    erro_mensagem TEXT,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    validado_em TIMESTAMP,
                    consolidado_em TIMESTAMP,
                    atualizado_em TIMESTAMP
                )
            """))
            print("   ✓ validacao_nf_po_dfe criada")

            # 3. Tabela Match Item
            print("\n[3/4] Criando tabela match_nf_po_item...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS match_nf_po_item (
                    id SERIAL PRIMARY KEY,
                    validacao_id INTEGER NOT NULL,
                    odoo_dfe_line_id INTEGER NOT NULL,
                    cod_produto_fornecedor VARCHAR(50),
                    cod_produto_interno VARCHAR(50),
                    nome_produto VARCHAR(255),
                    qtd_nf NUMERIC(15,3),
                    preco_nf NUMERIC(15,4),
                    data_nf DATE,
                    um_nf VARCHAR(20),
                    fator_conversao NUMERIC(10,4),
                    odoo_po_id INTEGER,
                    odoo_po_name VARCHAR(50),
                    odoo_po_line_id INTEGER,
                    qtd_po NUMERIC(15,3),
                    preco_po NUMERIC(15,4),
                    data_po DATE,
                    status_match VARCHAR(20) NOT NULL,
                    motivo_bloqueio TEXT,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_match_validacao FOREIGN KEY (validacao_id)
                        REFERENCES validacao_nf_po_dfe(id) ON DELETE CASCADE
                )
            """))
            print("   ✓ match_nf_po_item criada")

            # 4. Tabela Divergencia
            print("\n[4/4] Criando tabela divergencia_nf_po...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS divergencia_nf_po (
                    id SERIAL PRIMARY KEY,
                    validacao_id INTEGER NOT NULL,
                    odoo_dfe_id INTEGER NOT NULL,
                    odoo_dfe_line_id INTEGER,
                    cnpj_fornecedor VARCHAR(20),
                    razao_fornecedor VARCHAR(255),
                    cod_produto_fornecedor VARCHAR(50),
                    cod_produto_interno VARCHAR(50),
                    nome_produto VARCHAR(255),
                    tipo_divergencia VARCHAR(50) NOT NULL,
                    campo_label VARCHAR(100),
                    valor_nf VARCHAR(100),
                    valor_po VARCHAR(100),
                    diferenca_percentual NUMERIC(10,2),
                    odoo_po_id INTEGER,
                    odoo_po_name VARCHAR(50),
                    odoo_po_line_id INTEGER,
                    status VARCHAR(20) DEFAULT 'pendente',
                    resolucao VARCHAR(50),
                    justificativa TEXT,
                    resolvido_por VARCHAR(100),
                    resolvido_em TIMESTAMP,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_div_validacao FOREIGN KEY (validacao_id)
                        REFERENCES validacao_nf_po_dfe(id) ON DELETE CASCADE
                )
            """))
            print("   ✓ divergencia_nf_po criada")

            # Criar indices
            print("\n[+] Criando indices...")

            indices = [
                "CREATE INDEX IF NOT EXISTS idx_depara_cnpj ON produto_fornecedor_depara(cnpj_fornecedor)",
                "CREATE INDEX IF NOT EXISTS idx_depara_cod_forn ON produto_fornecedor_depara(cod_produto_fornecedor)",
                "CREATE INDEX IF NOT EXISTS idx_depara_cod_interno ON produto_fornecedor_depara(cod_produto_interno)",
                "CREATE INDEX IF NOT EXISTS idx_depara_ativo ON produto_fornecedor_depara(ativo)",
                "CREATE INDEX IF NOT EXISTS idx_match_validacao ON match_nf_po_item(validacao_id)",
                "CREATE INDEX IF NOT EXISTS idx_match_status ON match_nf_po_item(status_match)",
                "CREATE INDEX IF NOT EXISTS idx_match_dfe_line ON match_nf_po_item(odoo_dfe_line_id)",
                "CREATE INDEX IF NOT EXISTS idx_div_nf_po_validacao ON divergencia_nf_po(validacao_id)",
                "CREATE INDEX IF NOT EXISTS idx_div_nf_po_status ON divergencia_nf_po(status)",
                "CREATE INDEX IF NOT EXISTS idx_div_nf_po_tipo ON divergencia_nf_po(tipo_divergencia)",
                "CREATE INDEX IF NOT EXISTS idx_val_nf_po_status ON validacao_nf_po_dfe(status)",
                "CREATE INDEX IF NOT EXISTS idx_val_nf_po_dfe ON validacao_nf_po_dfe(odoo_dfe_id)",
                "CREATE INDEX IF NOT EXISTS idx_val_nf_po_cnpj ON validacao_nf_po_dfe(cnpj_fornecedor)",
            ]

            for idx in indices:
                db.session.execute(text(idx))

            print(f"   ✓ {len(indices)} indices criados")

            db.session.commit()

            print("\n" + "=" * 60)
            print("✅ SUCESSO: Todas as tabelas da Fase 2 foram criadas!")
            print("=" * 60)

            # Verificar tabelas
            result = db.session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN (
                    'produto_fornecedor_depara',
                    'match_nf_po_item',
                    'divergencia_nf_po',
                    'validacao_nf_po_dfe'
                )
                ORDER BY table_name
            """))

            tabelas = [row[0] for row in result]
            print(f"\nTabelas criadas: {', '.join(tabelas)}")

            return True

        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            db.session.rollback()
            return False


def verificar_tabelas():
    """Verifica se as tabelas existem e mostra contagem"""

    app = create_app()
    with app.app_context():
        try:
            print("\n[INFO] Verificando tabelas...")

            tabelas = [
                'produto_fornecedor_depara',
                'match_nf_po_item',
                'divergencia_nf_po',
                'validacao_nf_po_dfe'
            ]

            for tabela in tabelas:
                try:
                    result = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela}"))
                    count = result.scalar()
                    print(f"   ✓ {tabela}: {count} registros")
                except Exception as e:
                    print(f"   ✗ {tabela}: NAO EXISTE")

        except Exception as e:
            print(f"Erro: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Migration Fase 2 - Vinculacao NF x PO')
    parser.add_argument('--verificar', action='store_true', help='Apenas verificar tabelas')

    args = parser.parse_args()

    if args.verificar:
        verificar_tabelas()
    else:
        criar_tabelas()
        verificar_tabelas()
