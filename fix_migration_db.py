#!/usr/bin/env python3
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Remover migração inexistente
        result = db.session.execute(
            text("DELETE FROM alembic_version WHERE version_num = '1d81b88a3038'")
        )
        db.session.commit()
        print("Removidas " + str(result.rowcount) + " referencias a migracao 1d81b88a3038")
        
        # Verificar migrações atuais
        current = db.session.execute(
            text("SELECT version_num FROM alembic_version")
        ).fetchall()
        
        print("Migracoes atuais no banco:")
        for row in current:
            print("   - " + str(row[0]))
            
    except Exception as e:
        print("Erro: " + str(e))
        db.session.rollback()
