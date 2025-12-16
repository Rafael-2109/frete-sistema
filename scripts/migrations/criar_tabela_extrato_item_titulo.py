"""
Script para criar a tabela extrato_item_titulo (associação M:N).
=============================================================================

Esta tabela permite vincular múltiplos títulos a uma única linha de extrato,
suportando cenários como:
- Pagamento agrupado (cliente paga N NFs de uma vez)
- Alocação parcial (pagar apenas parte de um título)

Data: 2025-12-15
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabela():
    """Cria a tabela extrato_item_titulo."""
    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("CRIAÇÃO DA TABELA extrato_item_titulo")
        print("=" * 70)

        try:
            # Verificar se tabela já existe
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'extrato_item_titulo'
                )
            """))
            existe = result.scalar()

            if existe:
                print("⚠️  Tabela extrato_item_titulo já existe!")
                return

            # Criar tabela
            db.session.execute(text("""
                CREATE TABLE extrato_item_titulo (
                    id SERIAL PRIMARY KEY,

                    -- Relacionamentos
                    extrato_item_id INTEGER NOT NULL REFERENCES extrato_item(id) ON DELETE CASCADE,
                    titulo_receber_id INTEGER REFERENCES contas_a_receber(id),
                    titulo_pagar_id INTEGER REFERENCES contas_a_pagar(id),

                    -- Dados da alocação
                    valor_alocado NUMERIC(15, 2) NOT NULL,
                    valor_titulo_original NUMERIC(15, 2),
                    percentual_alocado NUMERIC(5, 2),

                    -- Cache
                    titulo_nf VARCHAR(50),
                    titulo_parcela INTEGER,
                    titulo_vencimento DATE,
                    titulo_cliente VARCHAR(255),
                    titulo_cnpj VARCHAR(20),
                    match_score INTEGER,
                    match_criterio VARCHAR(100),

                    -- Controle
                    status VARCHAR(30) DEFAULT 'PENDENTE' NOT NULL,
                    aprovado BOOLEAN DEFAULT FALSE NOT NULL,
                    aprovado_em TIMESTAMP,
                    aprovado_por VARCHAR(100),

                    -- Resultado conciliação
                    partial_reconcile_id INTEGER,
                    full_reconcile_id INTEGER,
                    payment_id INTEGER,
                    titulo_saldo_antes NUMERIC(15, 2),
                    titulo_saldo_depois NUMERIC(15, 2),
                    mensagem TEXT,

                    -- Auditoria
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processado_em TIMESTAMP,

                    -- Constraint: título receber OU pagar, não ambos
                    CONSTRAINT chk_titulo_receber_ou_pagar CHECK (
                        (titulo_receber_id IS NOT NULL AND titulo_pagar_id IS NULL) OR
                        (titulo_receber_id IS NULL AND titulo_pagar_id IS NOT NULL)
                    )
                )
            """))

            # Criar índices
            db.session.execute(text("""
                CREATE INDEX idx_extrato_titulo_item ON extrato_item_titulo(extrato_item_id)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_extrato_titulo_receber ON extrato_item_titulo(titulo_receber_id)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_extrato_titulo_pagar ON extrato_item_titulo(titulo_pagar_id)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_extrato_titulo_status ON extrato_item_titulo(status)
            """))

            db.session.commit()
            print("✅ Tabela extrato_item_titulo criada com sucesso!")
            print("✅ Índices criados!")

        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    criar_tabela()
