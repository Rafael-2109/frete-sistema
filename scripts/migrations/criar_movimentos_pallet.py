"""
Migracao: Adicionar campos de pallet em MovimentacaoEstoque e embarques/embarque_itens
Data: 03/01/2026

Campos adicionados em movimentacao_estoque:
- tipo_destinatario: CLIENTE ou TRANSPORTADORA (para pallet em terceiro)
- cnpj_destinatario: CNPJ do cliente/transportadora
- nome_destinatario: Nome do destinatario
- embarque_item_id: FK para embarque_itens (para vincular ao item especifico)
- baixado: Se o movimento de pallet foi baixado
- baixado_em: Data/hora da baixa
- baixado_por: Usuario que baixou
- movimento_baixado_id: FK para o movimento de retorno que quitou esta saida
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def migrar():
    app = create_app()
    with app.app_context():
        try:
            # 1. Campos em embarques
            print("Adicionando campos de NF pallet em embarques...")
            db.session.execute(text("""
                ALTER TABLE embarques
                ADD COLUMN IF NOT EXISTS nf_pallet_transportadora VARCHAR(20),
                ADD COLUMN IF NOT EXISTS qtd_pallet_transportadora FLOAT DEFAULT 0;
            """))
            print("  OK")

            # 2. Campos em embarque_itens
            print("Adicionando campos de NF pallet em embarque_itens...")
            db.session.execute(text("""
                ALTER TABLE embarque_itens
                ADD COLUMN IF NOT EXISTS nf_pallet_cliente VARCHAR(20),
                ADD COLUMN IF NOT EXISTS qtd_pallet_cliente FLOAT DEFAULT 0;
            """))
            print("  OK")

            # 3. Campos de pallet em terceiros na movimentacao_estoque
            print("Adicionando campos de pallet em terceiros em movimentacao_estoque...")
            db.session.execute(text("""
                ALTER TABLE movimentacao_estoque
                ADD COLUMN IF NOT EXISTS tipo_destinatario VARCHAR(20),
                ADD COLUMN IF NOT EXISTS cnpj_destinatario VARCHAR(20),
                ADD COLUMN IF NOT EXISTS nome_destinatario VARCHAR(255),
                ADD COLUMN IF NOT EXISTS embarque_item_id INTEGER REFERENCES embarque_itens(id) ON DELETE SET NULL,
                ADD COLUMN IF NOT EXISTS baixado BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS baixado_em TIMESTAMP,
                ADD COLUMN IF NOT EXISTS baixado_por VARCHAR(100),
                ADD COLUMN IF NOT EXISTS movimento_baixado_id INTEGER REFERENCES movimentacao_estoque(id) ON DELETE SET NULL;
            """))
            print("  OK")

            # 4. Indices para pallet
            print("Criando indices para pallet...")
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_movimentacao_cnpj_destinatario
                ON movimentacao_estoque(cnpj_destinatario);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_movimentacao_tipo_destinatario
                ON movimentacao_estoque(tipo_destinatario);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_movimentacao_baixado
                ON movimentacao_estoque(baixado);
            """))
            print("  OK")

            db.session.commit()
            print("\nMigracao concluida com sucesso!")

        except Exception as e:
            print(f"\nErro na migracao: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    migrar()
