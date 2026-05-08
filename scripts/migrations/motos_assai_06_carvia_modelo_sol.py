"""Adiciona modelo SOL ao reconhecedor CarVia (CarviaModeloMoto).

Idempotente: cria apenas se nome 'SOL' ainda não existe.

Dimensões: mesma classe do DOT (moto elétrica similar, ~158x45x80 cm).
regex_pattern: ilike SOL — compatível com DanfePDFParser text search.
criado_por: 'motos_assai_migration' — rastreabilidade.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def run():
    app = create_app()
    with app.app_context():
        try:
            from app.carvia.models import CarviaModeloMoto
        except ImportError:
            print('CarviaModeloMoto não disponível neste ambiente. Pulando.')
            return

        existente = CarviaModeloMoto.query.filter(
            db.func.upper(CarviaModeloMoto.nome) == 'SOL'
        ).first()
        if existente:
            print(f'Modelo SOL já existe (id={existente.id}, nome={existente.nome!r}).')
            return

        novo = CarviaModeloMoto(
            nome='SOL',
            regex_pattern=r'(?i)\bSOL\b',
            comprimento=158,
            largura=45,
            altura=80,
            peso_medio=None,
            cubagem_minima=300,
            ativo=True,
            criado_por='motos_assai_migration',
        )
        db.session.add(novo)
        db.session.commit()
        print(f'OK: modelo SOL adicionado (id={novo.id}, {novo.comprimento}x{novo.largura}x{novo.altura} cm).')


if __name__ == '__main__':
    run()
