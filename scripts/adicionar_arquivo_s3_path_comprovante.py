# -*- coding: utf-8 -*-
"""
Migracao: Adicionar campo arquivo_s3_path em comprovante_pagamento_boleto
=========================================================================

Armazena o path do PDF original no S3 para acesso posterior.
1 PDF pode gerar N comprovantes — todos compartilham o mesmo arquivo_s3_path.

Executar localmente:
    source .venv/bin/activate && python scripts/adicionar_arquivo_s3_path_comprovante.py

SQL para Render Shell:
    ALTER TABLE comprovante_pagamento_boleto
    ADD COLUMN IF NOT EXISTS arquivo_s3_path VARCHAR(500);
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_arquivo_s3_path():
    """Adiciona coluna arquivo_s3_path na tabela comprovante_pagamento_boleto."""
    app = create_app()
    with app.app_context():
        try:
            # Adicionar coluna
            db.session.execute(text("""
                ALTER TABLE comprovante_pagamento_boleto
                ADD COLUMN IF NOT EXISTS arquivo_s3_path VARCHAR(500);
            """))
            print("[OK] Coluna arquivo_s3_path adicionada")

            db.session.commit()
            print("\n[SUCESSO] Migracao concluida!")

            # Verificar
            resultado = db.session.execute(text("""
                SELECT column_name, data_type, character_maximum_length, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'comprovante_pagamento_boleto'
                  AND column_name = 'arquivo_s3_path';
            """))
            for row in resultado:
                print(f"  - {row[0]}: {row[1]}({row[2]}) nullable={row[3]}")

        except Exception as e:
            print(f"[ERRO] {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    adicionar_arquivo_s3_path()
