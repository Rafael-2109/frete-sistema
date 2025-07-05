#!/usr/bin/env python3
"""Remove migração fantasma do PostgreSQL no Render"""

import os
import psycopg2
from urllib.parse import urlparse

database_url = os.environ.get('DATABASE_URL')
if database_url:
    url = urlparse(database_url)
    try:
        conn = psycopg2.connect(
            host=url.hostname,
            port=url.port,
            database=url.path[1:],
            user=url.username,
            password=url.password,
            sslmode='require'
        )
        cursor = conn.cursor()
        
        # Remover migração fantasma
        cursor.execute("DELETE FROM alembic_version WHERE version_num = '1d81b88a3038'")
        rows_deleted = cursor.rowcount
        
        if rows_deleted > 0:
            conn.commit()
            print(f"✅ Migração fantasma removida ({rows_deleted} registro)")
        else:
            print("ℹ️ Migração fantasma não encontrada")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ Erro ao remover migração: {e}")
else:
    print("⚠️ DATABASE_URL não encontrada")
