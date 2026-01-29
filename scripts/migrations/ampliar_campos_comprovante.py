# -*- coding: utf-8 -*-
"""
Migration: Ampliar campos do comprovante_pagamento_boleto
=========================================================

Altera campos que podem receber dados de OCR maiores que o esperado.
Remove constraint UNIQUE de 'autenticacao' (OCR não é confiável como chave).

A chave real é 'numero_agendamento' (já tem UNIQUE).

SQL equivalente para Render:
    ALTER TABLE comprovante_pagamento_boleto
        ALTER COLUMN beneficiario_cnpj_cpf TYPE VARCHAR(50),
        ALTER COLUMN pagador_cnpj_cpf TYPE VARCHAR(50),
        ALTER COLUMN nosso_numero TYPE VARCHAR(100),
        ALTER COLUMN instituicao_emissora TYPE VARCHAR(100),
        ALTER COLUMN tipo_documento TYPE VARCHAR(100),
        ALTER COLUMN situacao TYPE VARCHAR(50),
        ALTER COLUMN autenticacao TYPE VARCHAR(255);

    ALTER TABLE comprovante_pagamento_boleto
        DROP CONSTRAINT IF EXISTS comprovante_pagamento_boleto_autenticacao_key;

Data: 2026-01-29
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def ampliar_campos():
    app = create_app()
    with app.app_context():
        try:
            # 1. Ampliar campos VARCHAR
            print("Ampliando campos VARCHAR...")
            db.session.execute(text("""
                ALTER TABLE comprovante_pagamento_boleto
                    ALTER COLUMN beneficiario_cnpj_cpf TYPE VARCHAR(50),
                    ALTER COLUMN pagador_cnpj_cpf TYPE VARCHAR(50),
                    ALTER COLUMN nosso_numero TYPE VARCHAR(100),
                    ALTER COLUMN instituicao_emissora TYPE VARCHAR(100),
                    ALTER COLUMN tipo_documento TYPE VARCHAR(100),
                    ALTER COLUMN situacao TYPE VARCHAR(50),
                    ALTER COLUMN autenticacao TYPE VARCHAR(255);
            """))
            print("  ✅ Campos ampliados")

            # 2. Remover UNIQUE de autenticacao (OCR não é confiável como chave)
            print("Removendo UNIQUE de autenticacao...")
            db.session.execute(text("""
                ALTER TABLE comprovante_pagamento_boleto
                    DROP CONSTRAINT IF EXISTS comprovante_pagamento_boleto_autenticacao_key;
            """))
            print("  ✅ Constraint UNIQUE removida de autenticacao")

            db.session.commit()
            print("\n✅ Migration concluída com sucesso!")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro na migration: {e}")
            raise


if __name__ == '__main__':
    ampliar_campos()
