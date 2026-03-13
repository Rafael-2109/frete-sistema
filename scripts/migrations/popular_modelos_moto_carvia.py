"""
Migration: Popular modelos de moto na tabela carvia_modelos_moto
Data: 2026-03-13
Descricao: Insere 18 modelos de moto com dimensoes (cm) e regex auto-gerado.
           Idempotente via ON CONFLICT.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db

MODELOS = [
    # (nome, comprimento, largura, altura, regex_pattern)
    ('PATINETE',    118, 25, 48, r'(?i)patinete'),
    ('MCQ3',        130, 37, 64, r'(?i)mcq3'),
    ('JOY SUPER',   131, 34, 71, r'(?i)joy[\s\-]*super'),
    ('X12-10',      147, 37, 63, r'(?i)x12[\s\-]*10'),
    ('X11 MINI',    141, 39, 65, r'(?i)x11[\s\-]*mini'),
    ('BOB',         144, 33, 76, r'(?i)bob'),
    ('RET',         170, 32, 87, r'(?i)ret'),
    ('SOMA',        154, 42, 78, r'(?i)soma'),
    ('DOT',         158, 45, 80, r'(?i)dot'),
    ('GIGA',        158, 45, 80, r'(?i)giga'),
    ('SOFIA',       158, 45, 80, r'(?i)sofia'),
    ('JET',         168, 42, 84, r'(?i)jet'),
    ('X15',         167, 56, 64, r'(?i)x15'),
    ('S8',          180, 43, 78, r'(?i)s8'),
    ('BIG TRI',     137, 76, 61, r'(?i)big[\s\-]*tri'),
    ('VED',         142, 72, 83, r'(?i)ved'),
    ('MIA TRI',     154, 71, 83, r'(?i)mia[\s\-]*tri'),
    ('POP',         141, 26, 85, r'(?i)pop'),
]


def run():
    app = create_app()
    with app.app_context():
        # Before: contar registros existentes
        result = db.session.execute(
            db.text("SELECT COUNT(*) FROM carvia_modelos_moto")
        )
        count_before = result.scalar()
        print(f"[BEFORE] carvia_modelos_moto: {count_before} registros")

        sql = db.text("""
            INSERT INTO carvia_modelos_moto
                (nome, comprimento, largura, altura, regex_pattern,
                 cubagem_minima, ativo, criado_em, criado_por)
            VALUES
                (:nome, :comprimento, :largura, :altura, :regex_pattern,
                 300, true, NOW(), 'sistema')
            ON CONFLICT (nome) DO UPDATE SET
                comprimento = EXCLUDED.comprimento,
                largura = EXCLUDED.largura,
                altura = EXCLUDED.altura,
                regex_pattern = EXCLUDED.regex_pattern
        """)

        for nome, comp, larg, alt, regex in MODELOS:
            db.session.execute(sql, {
                'nome': nome,
                'comprimento': comp,
                'largura': larg,
                'altura': alt,
                'regex_pattern': regex,
            })

        db.session.commit()

        # After: contar registros
        result = db.session.execute(
            db.text("SELECT COUNT(*) FROM carvia_modelos_moto")
        )
        count_after = result.scalar()
        print(f"[AFTER]  carvia_modelos_moto: {count_after} registros")
        print(f"         Novos: {count_after - count_before}, "
              f"Atualizados: {min(count_before, len(MODELOS))}")
        print("[OK] Migration concluida com sucesso.")


if __name__ == '__main__':
    run()
