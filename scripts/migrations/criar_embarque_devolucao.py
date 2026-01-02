"""
Migração: Criar Embarque fictício para devoluções órfãs
Depende de: criar_transportadora_devolucao.py (executar primeiro)
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text
from datetime import datetime


def criar_embarque_devolucao():
    """Cria embarque fictício para devoluções órfãs"""
    app = create_app()
    with app.app_context():
        try:
            # Buscar ID da transportadora 'Devolução'
            resultado = db.session.execute(text("""
                SELECT id FROM transportadoras
                WHERE cnpj = '00000000000000'
            """))
            transp = resultado.fetchone()

            if not transp:
                print("ERRO: Transportadora 'Devolução' não encontrada!")
                print("Execute primeiro: python criar_transportadora_devolucao.py")
                return None

            transportadora_id = transp[0]

            # Verificar se embarque já existe (numero=0)
            resultado = db.session.execute(text("""
                SELECT id FROM embarques
                WHERE numero = 0
            """))
            existente = resultado.fetchone()

            if existente:
                print(f"Embarque de devolução já existe (ID: {existente[0]})")
                return existente[0]

            # Criar embarque fictício
            db.session.execute(text("""
                INSERT INTO embarques (
                    numero,
                    transportadora_id,
                    status,
                    tipo_carga,
                    observacoes,
                    criado_em,
                    criado_por
                ) VALUES (
                    0,
                    :transportadora_id,
                    'ativo',
                    'FRACIONADA',
                    'Embarque fictício para devoluções órfãs - NÃO USAR MANUALMENTE',
                    :criado_em,
                    'Sistema'
                )
            """), {
                'transportadora_id': transportadora_id,
                'criado_em': datetime.utcnow()
            })
            db.session.commit()

            # Obter ID criado
            resultado = db.session.execute(text("""
                SELECT id FROM embarques
                WHERE numero = 0
            """))
            novo_id = resultado.fetchone()[0]

            print(f"Embarque de devolução criado com sucesso (ID: {novo_id})")
            return novo_id

        except Exception as e:
            print(f"Erro ao criar embarque: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    criar_embarque_devolucao()
