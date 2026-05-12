"""Migration: adicionar peso_kg + peso_cubado_kg em assai_modelo.

peso_kg: peso fisico (kg) — usado em relatorios/portaria.
peso_cubado_kg: peso cubado (kg) — usado no CALCULO DO FRETE.
  Motos vao MONTADAS na carga — ocupam muito mais espaco que peso real.
  Quando ausente, frete usa peso_kg (fallback).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def _coluna_existe(coluna: str) -> bool:
    return bool(db.session.execute(db.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'assai_modelo' AND column_name = :c
    """), {'c': coluna}).scalar())


def verificar_antes():
    for c in ('peso_kg', 'peso_cubado_kg'):
        print(f"[BEFORE] assai_modelo.{c} existe = {_coluna_existe(c)}")


def executar_migration():
    db.session.execute(db.text(
        "ALTER TABLE assai_modelo ADD COLUMN IF NOT EXISTS peso_kg NUMERIC(8, 2)"
    ))
    print("[OK] assai_modelo.peso_kg adicionado")
    db.session.execute(db.text(
        "ALTER TABLE assai_modelo ADD COLUMN IF NOT EXISTS peso_cubado_kg NUMERIC(8, 2)"
    ))
    print("[OK] assai_modelo.peso_cubado_kg adicionado")
    db.session.commit()


def verificar_depois():
    for c in ('peso_kg', 'peso_cubado_kg'):
        existe = _coluna_existe(c)
        print(f"[AFTER] assai_modelo.{c} existe = {existe}")
        assert existe, f"Coluna {c} nao foi criada"

    total = db.session.execute(db.text(
        "SELECT COUNT(*) FROM assai_modelo"
    )).scalar()
    sem_peso = db.session.execute(db.text(
        "SELECT COUNT(*) FROM assai_modelo WHERE peso_cubado_kg IS NULL"
    )).scalar()
    print(f"[DATA] {sem_peso}/{total} modelos sem peso_cubado_kg cadastrado "
          "(operador deve cadastrar via UI antes de cotar frete)")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("[DONE] Migration assai_modelo peso/peso_cubado concluida")
