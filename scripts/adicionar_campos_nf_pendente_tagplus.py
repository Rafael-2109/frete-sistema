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
        """ALTER TABLE usuarios
        ADD COLUMN IF NOT EXISTS sistema_logistica BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS sistema_motochefe BOOLEAN NOT NULL DEFAULT FALSE;

        -- Criar índices para performance
        CREATE INDEX IF NOT EXISTS idx_usuarios_sistema_logistica ON usuarios(sistema_logistica) WHERE sistema_logistica = TRUE;
        CREATE INDEX IF NOT EXISTS idx_usuarios_sistema_motochefe ON usuarios(sistema_motochefe) WHERE sistema_motochefe = TRUE;

        -- Comentários
        COMMENT ON COLUMN usuarios.sistema_logistica IS 'Usuário tem acesso ao sistema de logística';
        COMMENT ON COLUMN usuarios.sistema_motochefe IS 'Usuário tem acesso ao sistema motochefe';

        -- Atualizar usuários existentes para terem acesso à logística (manter compatibilidade)
        UPDATE usuarios
        SET sistema_logistica = TRUE
        WHERE sistema_logistica = FALSE;
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
