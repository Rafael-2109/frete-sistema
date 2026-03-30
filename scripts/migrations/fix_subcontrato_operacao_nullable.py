"""Tornar operacao_id nullable em carvia_subcontratos (R10)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from app import create_app, db

app = create_app()
with app.app_context():
    with open(os.path.join(os.path.dirname(__file__), 'fix_subcontrato_operacao_nullable.sql')) as f:
        db.session.execute(db.text(f.read()))
    db.session.commit()
    print("operacao_id agora nullable em carvia_subcontratos.")
