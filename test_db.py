#!/usr/bin/env python3
import os
from dotenv import load_dotenv
load_dotenv()

print(f"DATABASE_URL: {os.environ.get('DATABASE_URL')}")

from app import create_app, db
app = create_app()

with app.app_context():
    print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

    try:
        result = db.session.execute(db.text("SELECT 1"))
        print("✅ Conexão PostgreSQL OK!")

        db.create_all()
        print("✅ Tabelas criadas com sucesso!")
    except Exception as e:
        print(f"❌ Erro: {e}")
