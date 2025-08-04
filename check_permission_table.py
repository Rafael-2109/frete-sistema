#!/usr/bin/env python
"""Script para verificar estrutura da tabela permission_module"""

import os
import sys
from sqlalchemy import create_engine, text

# Obter URL do banco
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("DATABASE_URL não definida!")
    sys.exit(1)

# Conectar ao banco
engine = create_engine(DATABASE_URL)

# Query para verificar colunas da tabela
query = """
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'permission_module'
ORDER BY ordinal_position;
"""

print("Colunas na tabela permission_module:")
print("-" * 40)

try:
    with engine.connect() as conn:
        result = conn.execute(text(query))
        for row in result:
            print(f"{row[0]}: {row[1]}")
except Exception as e:
    print(f"Erro ao conectar ao banco: {e}")
    sys.exit(1)