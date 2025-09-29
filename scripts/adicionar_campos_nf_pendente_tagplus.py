"""Garante campos extras em ``nf_pendente_tagplus``.

Pode ser executado diretamente pela linha de comando:

    python scripts/adicionar_campos_nf_pendente_tagplus.py
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
        """
        ALTER TABLE nf_pendente_tagplus
        ADD COLUMN IF NOT EXISTS nome_cidade VARCHAR(120)
        """
    ),
    text(
        """
        ALTER TABLE nf_pendente_tagplus
        ADD COLUMN IF NOT EXISTS cod_uf VARCHAR(5)
        """
    ),
    text(
        """
        ALTER TABLE nf_pendente_tagplus
        ADD COLUMN IF NOT EXISTS pedido_preenchido_em TIMESTAMP WITHOUT TIME ZONE
        """
    ),
    text(
        """
        ALTER TABLE nf_pendente_tagplus
        ADD COLUMN IF NOT EXISTS pedido_preenchido_por VARCHAR(100)
        """
    ),
]


def main() -> None:
    app = create_app()

    with app.app_context():
        for statement in DDL_STATEMENTS:
            db.session.execute(statement)
        db.session.commit()
        print("✅ Campos adicionados/garantidos em nf_pendente_tagplus")


if __name__ == "__main__":
    main()
