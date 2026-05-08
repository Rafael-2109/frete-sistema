"""
Migration: Seed dos 3 modelos canônicos (X11 MINI, DOT, SOL) + aliases
======================================================================
Executar: python scripts/migrations/motos_assai_05_seed_modelos.py

regex_chassi: PREENCHER após dono enviar máscaras (Claude monta os regex).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.motos_assai.models import (
    AssaiModelo, AssaiModeloAlias,
    ALIAS_TIPO_NOME_LIVRE, ALIAS_TIPO_CODIGO_QPA, ALIAS_TIPO_DESCRICAO_RECIBO,
)


MODELOS = [
    {
        'codigo': 'X11_MINI',
        'nome': 'X11 MINI 1000W',
        'descricao_qpa': 'AUTOPROPELIDO X11 MINI 1000W 60V 20AH',
        'codigo_qpa': '1342056',
        # Aprovado 2026-05-07: cobre X11M-A (MCBRX11M+9 dígitos) e X11M-B (LA+ano/mês+V1000W+4 dígitos).
        # Colisão admitida com DOT no padrão LA*V1000W* — modelo vem do recibo Motochefe.
        'regex_chassi': r'^(MCBRX11M\d{9}|LA\d+V1000W\d{4})$',
        'aliases': [
            ('X11 NAC', ALIAS_TIPO_NOME_LIVRE),
            ('X11 MINI', ALIAS_TIPO_NOME_LIVRE),
            ('X11', ALIAS_TIPO_NOME_LIVRE),
            ('AUTOPROPELIDO X11 MINI 1000W', ALIAS_TIPO_DESCRICAO_RECIBO),
            ('AUTOPROPELIDO X11 MINI 1000W 60V 20AH', ALIAS_TIPO_DESCRICAO_RECIBO),
            ('1342056', ALIAS_TIPO_CODIGO_QPA),
        ],
    },
    {
        'codigo': 'DOT',
        'nome': 'DOT 1000W',
        'descricao_qpa': 'AUTOPROPELIDO DOT 1000W 60V 20AH',
        'codigo_qpa': '1342059',
        # Aprovado 2026-05-07: 4 alternativas — DOT-A (LA*SA*+5dig), DOT-B/C (LA*V1000W*+4dig),
        # DOT-D (HL5TCAH3 VIN-like), DOT-E (MCBRDOT+10dig).
        'regex_chassi': r'^(LA\d+SA\d+\d{5}|LA\d+V1000W\d{4}|HL5TCAH3[0-9X]S9W57\d{3}|MCBRDOT\d{10})$',
        'aliases': [
            ('DOT', ALIAS_TIPO_NOME_LIVRE),
            ('DOT 1000W', ALIAS_TIPO_NOME_LIVRE),
            ('AUTOPROPELIDO DOT 1000W', ALIAS_TIPO_DESCRICAO_RECIBO),
            ('AUTOPROPELIDO DOT 1000W 60V 20AH', ALIAS_TIPO_DESCRICAO_RECIBO),
            ('1342059', ALIAS_TIPO_CODIGO_QPA),
        ],
    },
    {
        'codigo': 'SOL',
        'nome': 'SOL 1000W',
        'descricao_qpa': 'AUTOPROPELIDO SOL 1000W 60V 20AH',
        'codigo_qpa': '1342063',
        # Aprovado 2026-05-07: 15 dígitos numéricos começando com 17292.
        # Cobre lotes diferentes (17292250467*, 17292251217*, etc.) sem manutenção.
        'regex_chassi': r'^17292\d{10}$',
        'aliases': [
            ('SOL', ALIAS_TIPO_NOME_LIVRE),
            ('SOL 1000W', ALIAS_TIPO_NOME_LIVRE),
            ('AUTOPROPELIDO SOL 1000W', ALIAS_TIPO_DESCRICAO_RECIBO),
            ('AUTOPROPELIDO SOL 1000W 60V 20AH', ALIAS_TIPO_DESCRICAO_RECIBO),
            ('1342063', ALIAS_TIPO_CODIGO_QPA),
        ],
    },
]


def seed_modelos():
    app = create_app()
    with app.app_context():
        criados = 0
        for m_data in MODELOS:
            existente = AssaiModelo.query.filter_by(codigo=m_data['codigo']).first()
            if existente:
                print(f"Modelo {m_data['codigo']} já existe (id={existente.id}).")
                continue

            aliases_data = m_data.pop('aliases')
            modelo = AssaiModelo(**m_data)
            for alias, tipo in aliases_data:
                modelo.aliases.append(AssaiModeloAlias(alias=alias, tipo=tipo))

            db.session.add(modelo)
            criados += 1

        db.session.commit()
        print(f"OK: {criados} modelos criados. Total: {AssaiModelo.query.count()}")
        print(f"Aliases criados: {AssaiModeloAlias.query.count()}")


if __name__ == '__main__':
    seed_modelos()
