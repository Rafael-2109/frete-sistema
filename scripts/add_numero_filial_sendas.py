"""
Script para adicionar coluna 'numero' na tabela portal_sendas_filial_depara
e popular os dados extraindo o número do campo 'filial'

Uso local:
    source .venv/bin/activate && python scripts/add_numero_filial_sendas.py

SQL para Render:
    -- Ver seção SQL PARA RENDER abaixo
"""

import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def adicionar_coluna_numero():
    """Adiciona coluna 'numero' se não existir"""
    app = create_app()
    with app.app_context():
        try:
            # Verifica se a coluna já existe
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'portal_sendas_filial_depara'
                AND column_name = 'numero'
            """))

            if result.fetchone():
                print("Coluna 'numero' já existe na tabela")
                return True

            # Adiciona a coluna
            db.session.execute(text("""
                ALTER TABLE portal_sendas_filial_depara
                ADD COLUMN numero VARCHAR(10)
            """))

            # Cria índice
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sendas_filial_numero
                ON portal_sendas_filial_depara (numero)
            """))

            db.session.commit()
            print("Coluna 'numero' adicionada com sucesso")
            return True

        except Exception as e:
            print(f"Erro ao adicionar coluna: {e}")
            db.session.rollback()
            return False


def popular_numeros():
    """Popula o campo 'numero' extraindo do campo 'filial'"""
    app = create_app()
    with app.app_context():
        try:
            from app.portal.sendas.models import FilialDeParaSendas
            filiais = FilialDeParaSendas.query.all()
            atualizados = 0
            for filial in filiais:
                if filial.filial:
                    # Extrai números do início do campo filial
                    # Ex: "010 SAO BERNARDO PIRAPORI" -> "010"
                    match = re.match(r'^(\d+)', filial.filial)
                    if match:
                        numero = match.group(1).zfill(3)
                        filial.numero = numero
                        atualizados += 1
                        print(f"  {filial.filial} -> numero: {numero}")

            db.session.commit()
            print(f"\nTotal de registros atualizados: {atualizados}")
            return True

        except Exception as e:
            print(f"Erro ao popular números: {e}")
            db.session.rollback()
            return False


if __name__ == '__main__':
    print("=" * 60)
    print("Adicionando coluna 'numero' na tabela portal_sendas_filial_depara")
    print("=" * 60)

    # Passo 1: Adicionar coluna
    print("\n1. Adicionando coluna...")
    if adicionar_coluna_numero():
        # Passo 2: Popular dados
        print("\n2. Populando números...")
        popular_numeros()

    print("\n" + "=" * 60)
    print("Script finalizado!")
    print("=" * 60)

    # SQL PARA RENDER
    print("""
=== SQL PARA RENDER (copiar e colar no Shell) ===

-- 1. Adicionar coluna 'numero' na tabela de filiais
ALTER TABLE portal_sendas_filial_depara
ADD COLUMN IF NOT EXISTS numero VARCHAR(10);

-- 2. Criar índice
CREATE INDEX IF NOT EXISTS idx_sendas_filial_numero
ON portal_sendas_filial_depara (numero);

-- 3. Popular campo 'numero' extraindo do campo 'filial'
UPDATE portal_sendas_filial_depara
SET numero = LPAD(
    COALESCE(
        (regexp_match(filial, '^(\d+)'))[1],''),3, '0') WHERE numero IS NULL;

-- 5. Padronizar região do ASSAI para 'SAO PAULO' em ambas as tabelas
-- 5a. Atualizar mapeamento de região
UPDATE tabela_rede_regiao
SET regiao = 'SAO PAULO'
WHERE rede = 'ASSAI' AND uf = 'SP';

-- 5b. Atualizar TabelaRede (caso tenha SP em vez de SAO PAULO)
UPDATE tabela_rede
SET regiao = 'SAO PAULO'
WHERE rede = 'ASSAI' AND regiao = 'SP';

-- 6. Verificar resultado das filiais
SELECT id, filial, numero, nome_filial, uf
FROM portal_sendas_filial_depara
ORDER BY numero
LIMIT 20;

-- 7. Verificar mapeamento de região ASSAI
SELECT * FROM tabela_rede_regiao WHERE rede = 'ASSAI';
""")
