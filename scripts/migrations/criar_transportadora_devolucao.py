"""
Migração: Criar Transportadora fictícia "Devolução"
Usada para fretes placeholder de devoluções órfãs
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_transportadora_devolucao():
    """Cria transportadora fictícia para devoluções"""
    app = create_app()
    with app.app_context():
        try:
            # Verificar se já existe
            resultado = db.session.execute(text("""
                SELECT id FROM transportadoras
                WHERE cnpj = '00000000000000'
            """))
            existente = resultado.fetchone()

            if existente:
                print(f"Transportadora 'Devolução' já existe (ID: {existente[0]})")
                return existente[0]

            # Criar transportadora
            db.session.execute(text("""
                INSERT INTO transportadoras (
                    cnpj,
                    razao_social,
                    cidade,
                    uf,
                    optante,
                    freteiro,
                    ativo
                ) VALUES (
                    '00000000000000',
                    'Devolução',
                    'N/A',
                    'SP',
                    false,
                    false,
                    true
                )
            """))
            db.session.commit()

            # Obter ID criado
            resultado = db.session.execute(text("""
                SELECT id FROM transportadoras
                WHERE cnpj = '00000000000000'
            """))
            novo_id = resultado.fetchone()[0]

            print(f"Transportadora 'Devolução' criada com sucesso (ID: {novo_id})")
            return novo_id

        except Exception as e:
            print(f"Erro ao criar transportadora: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    criar_transportadora_devolucao()
