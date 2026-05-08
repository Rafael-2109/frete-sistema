"""
Migration: Seed do CD único 'Operação VOE'
==========================================
Executar: python scripts/migrations/motos_assai_03_seed_cd.py

Cria 1 CD com nome 'Operação VOE'. Endereço/CNPJ ficam vazios e
podem ser preenchidos via tela admin (`/motos-assai/cd/editar`).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.motos_assai.models import AssaiCd


CD_DADOS = {
    'nome': 'Operação VOE',
    'cnpj': None,
    'endereco': None,
    'bairro': None,
    'cep': None,
    'cidade': None,
    'uf': None,
    'ativo': True,
}


def seed_cd():
    app = create_app()
    with app.app_context():
        existente = AssaiCd.query.filter_by(nome=CD_DADOS['nome']).first()
        if existente:
            print(f"CD '{CD_DADOS['nome']}' já existe (id={existente.id}). Nada a fazer.")
            return

        cd = AssaiCd(**CD_DADOS)
        db.session.add(cd)
        db.session.commit()
        print(f"CD criado: id={cd.id} nome={cd.nome}")


if __name__ == '__main__':
    seed_cd()
