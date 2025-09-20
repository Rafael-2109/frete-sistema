#!/usr/bin/env python3
"""
Script para criar as tabelas de permissões comerciais no banco de dados.

Este script cria as tabelas:
- permissao_comercial: Armazena as permissões de cada usuário
- log_permissao_comercial: Armazena o histórico de alterações

Autor: Sistema de Fretes
Data: 2025-01-21
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

def criar_tabelas_permissao():
    """Cria as tabelas de permissão comercial no banco de dados"""

    app = create_app()

    with app.app_context():
        print("\n" + "="*80)
        print("CRIAÇÃO DAS TABELAS DE PERMISSÃO COMERCIAL")
        print("="*80 + "\n")

        try:
            # Importar os modelos para registrá-los
            from app.comercial.models import PermissaoComercial, LogPermissaoComercial

            print("📋 Criando tabelas...")

            # SQL para criar tabela de permissões
            sql_permissao = """
            CREATE TABLE IF NOT EXISTS permissao_comercial (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
                tipo VARCHAR(20) NOT NULL,
                valor VARCHAR(100) NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                criado_por VARCHAR(100) NOT NULL,
                UNIQUE(usuario_id, tipo, valor)
            );

            CREATE INDEX IF NOT EXISTS idx_permissao_usuario_tipo
            ON permissao_comercial(usuario_id, tipo);
            """

            # SQL para criar tabela de logs
            sql_log = """
            CREATE TABLE IF NOT EXISTS log_permissao_comercial (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
                admin_id INTEGER NOT NULL REFERENCES usuarios(id),
                acao VARCHAR(20) NOT NULL,
                tipo VARCHAR(20),
                valor VARCHAR(100),
                data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(45),
                user_agent VARCHAR(500),
                observacao TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_log_usuario_data
            ON log_permissao_comercial(usuario_id, data_hora);

            CREATE INDEX IF NOT EXISTS idx_log_admin_data
            ON log_permissao_comercial(admin_id, data_hora);

            CREATE INDEX IF NOT EXISTS idx_log_data
            ON log_permissao_comercial(data_hora);
            """

            # Executar SQLs
            db.session.execute(text(sql_permissao))
            db.session.commit()
            print("✅ Tabela 'permissao_comercial' criada com sucesso!")

            db.session.execute(text(sql_log))
            db.session.commit()
            print("✅ Tabela 'log_permissao_comercial' criada com sucesso!")

            # Verificar se as tabelas foram criadas
            result = db.session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name IN ('permissao_comercial', 'log_permissao_comercial')
                AND table_schema = 'public'
            """)).fetchall()

            print(f"\n📊 Tabelas encontradas: {len(result)}")
            for row in result:
                print(f"   - {row[0]}")

            # Contar registros existentes (se houver)
            count_perm = db.session.execute(text("SELECT COUNT(*) FROM permissao_comercial")).scalar()
            count_log = db.session.execute(text("SELECT COUNT(*) FROM log_permissao_comercial")).scalar()

            print(f"\n📈 Status:")
            print(f"   - Permissões cadastradas: {count_perm}")
            print(f"   - Logs registrados: {count_log}")

            print("\n" + "="*80)
            print("✅ TABELAS CRIADAS COM SUCESSO!")
            print("="*80 + "\n")

            print("📝 PRÓXIMOS PASSOS:")
            print("1. Acesse o módulo comercial como administrador ou gerente comercial")
            print("2. No menu Comercial, clique em 'Gerenciar Permissões'")
            print("3. Configure as permissões para cada vendedor")
            print("4. As alterações são salvas automaticamente")

        except Exception as e:
            print(f"\n❌ ERRO ao criar tabelas: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == '__main__':
    criar_tabelas_permissao()