"""
Adiciona campos de endereco de entrega (entrega_*) na tabela carvia_cotacoes.

Permite que cada cotacao tenha seu proprio endereco de entrega, independente
do destino cadastrado (CarviaClienteEndereco). Usado quando o usuario edita
o endereco inline na tela de detalhe da cotacao.

Campos: entrega_uf, entrega_cidade, entrega_logradouro, entrega_numero,
        entrega_bairro, entrega_cep, entrega_complemento (todos nullable).
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_coluna_existe(coluna: str) -> bool:
    result = db.session.execute(db.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_cotacoes' AND column_name = :col
    """), {'col': coluna})
    return result.fetchone() is not None


def run():
    app = create_app()
    with app.app_context():
        colunas = [
            ('entrega_uf', 'VARCHAR(2)'),
            ('entrega_cidade', 'VARCHAR(100)'),
            ('entrega_logradouro', 'VARCHAR(255)'),
            ('entrega_numero', 'VARCHAR(20)'),
            ('entrega_bairro', 'VARCHAR(100)'),
            ('entrega_cep', 'VARCHAR(10)'),
            ('entrega_complemento', 'VARCHAR(255)'),
        ]

        adicionadas = 0
        for nome, tipo in colunas:
            if verificar_coluna_existe(nome):
                print(f"  [SKIP] {nome} ja existe.")
                continue
            db.session.execute(db.text(
                f"ALTER TABLE carvia_cotacoes ADD COLUMN {nome} {tipo}"
            ))
            print(f"  [ADD] {nome} {tipo}")
            adicionadas += 1

        if adicionadas > 0:
            db.session.commit()
            print(f"\n{adicionadas} coluna(s) adicionada(s) com sucesso.")
        else:
            print("\nNenhuma coluna adicionada (todas ja existiam).")


if __name__ == '__main__':
    run()
