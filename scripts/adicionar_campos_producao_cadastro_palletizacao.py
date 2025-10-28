"""Adiciona campos de produção à tabela cadastro_palletizacao.

Campos adicionados:
- produto_comprado (BOOLEAN)
- produto_produzido (BOOLEAN)
- produto_vendido (BOOLEAN)
- lead_time_mto (INTEGER)
- disparo_producao (VARCHAR(3))
- custo_produto (NUMERIC(15, 4))

Pode ser executado diretamente pela linha de comando:

    python scripts/adicionar_campos_producao_cadastro_palletizacao.py
"""

import sys
from pathlib import Path

from sqlalchemy import text


# Ajusta ``sys.path`` para permitir ``import app`` mesmo quando o script
# for executado a partir da raiz do projeto ou de diretórios externos.
PROJETO_ROOT = Path(__file__).resolve().parents[1]
if str(PROJETO_ROOT) not in map(str, sys.path):
    sys.path.insert(0, str(PROJETO_ROOT))

from app import create_app, db


DDL_STATEMENTS = [
    text(
        """ALTER TABLE cadastro_palletizacao
        ADD COLUMN IF NOT EXISTS produto_comprado BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS produto_produzido BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS produto_vendido BOOLEAN NOT NULL DEFAULT TRUE,
        ADD COLUMN IF NOT EXISTS lead_time_mto INTEGER,
        ADD COLUMN IF NOT EXISTS disparo_producao VARCHAR(3),
        ADD COLUMN IF NOT EXISTS custo_produto NUMERIC(15, 4);

        -- Criar índices para performance em campos usados para filtros
        CREATE INDEX IF NOT EXISTS idx_cadastro_palletizacao_produto_comprado ON cadastro_palletizacao(produto_comprado) WHERE produto_comprado = TRUE;
        CREATE INDEX IF NOT EXISTS idx_cadastro_palletizacao_produto_produzido ON cadastro_palletizacao(produto_produzido) WHERE produto_produzido = TRUE;
        CREATE INDEX IF NOT EXISTS idx_cadastro_palletizacao_produto_vendido ON cadastro_palletizacao(produto_vendido) WHERE produto_vendido = TRUE;

        -- Comentários explicativos
        COMMENT ON COLUMN cadastro_palletizacao.produto_comprado IS 'Indica se o produto é comprado de terceiros';
        COMMENT ON COLUMN cadastro_palletizacao.produto_produzido IS 'Indica se o produto é fabricado internamente';
        COMMENT ON COLUMN cadastro_palletizacao.produto_vendido IS 'Indica se o produto está disponível para venda';
        COMMENT ON COLUMN cadastro_palletizacao.lead_time_mto IS 'Lead time MTO (Make to Order) em dias';
        COMMENT ON COLUMN cadastro_palletizacao.disparo_producao IS 'Código de disparo de produção';
        COMMENT ON COLUMN cadastro_palletizacao.custo_produto IS 'Custo unitário do produto';
        """
    ),
]


def main() -> None:
    app = create_app()

    with app.app_context():
        print("🔄 Iniciando adição de campos de produção em cadastro_palletizacao...")

        for statement in DDL_STATEMENTS:
            db.session.execute(statement)

        db.session.commit()
        print("✅ Campos de produção adicionados com sucesso em cadastro_palletizacao!")
        print("\nCampos adicionados:")
        print("  • produto_comprado (BOOLEAN, default: FALSE)")
        print("  • produto_produzido (BOOLEAN, default: FALSE)")
        print("  • produto_vendido (BOOLEAN, default: TRUE)")
        print("  • lead_time_mto (INTEGER, nullable)")
        print("  • disparo_producao (VARCHAR(3), nullable)")
        print("  • custo_produto (NUMERIC(15, 4), nullable)")


if __name__ == "__main__":
    main()
