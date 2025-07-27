"""
Script de migração para o novo sistema de permissões
====================================================

Este script atualiza o banco de dados para a nova estrutura de permissões,
mantendo compatibilidade com os dados existentes.

Executar com: python migrations/upgrade_permissions_system.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.permissions.models import (
    PerfilUsuario, ModuloSistema, 
    FuncaoModulo, PermissaoUsuario
)
from app.auth.models import Usuario
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def criar_tabelas_novas():
    """Cria as novas tabelas do sistema"""
    logger.info("Criando novas tabelas...")
    
    with db.engine.connect() as conn:
        # Criar tabela permission_category
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS permission_category (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(50) UNIQUE NOT NULL,
                nome_exibicao VARCHAR(100) NOT NULL,
                descricao VARCHAR(255),
                icone VARCHAR(50) DEFAULT '📁',
                cor VARCHAR(7) DEFAULT '#6c757d',
                ordem INTEGER DEFAULT 0 NOT NULL,
                ativo BOOLEAN DEFAULT true NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """))
        
        # Criar tabela sub_module
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sub_module (
                id SERIAL PRIMARY KEY,
                modulo_id INTEGER NOT NULL,
                nome VARCHAR(50) NOT NULL,
                nome_exibicao VARCHAR(100) NOT NULL,
                descricao VARCHAR(255),
                icone VARCHAR(50),
                ativo BOOLEAN DEFAULT true NOT NULL,
                ordem INTEGER DEFAULT 0 NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY (modulo_id) REFERENCES modulo_sistema(id),
                UNIQUE (modulo_id, nome)
            );
        """))
        
        # Criar índice para sub_module
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_submodule_ativo 
            ON sub_module(modulo_id, ativo);
        """))
        
        # Criar tabela permission_template
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS permission_template (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) UNIQUE NOT NULL,
                descricao VARCHAR(255),
                perfil_id INTEGER,
                permissions_json TEXT NOT NULL,
                ativo BOOLEAN DEFAULT true NOT NULL,
                criado_por INTEGER,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY (perfil_id) REFERENCES perfil_usuario(id),
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            );
        """))
        
        # Criar tabela batch_permission_operation
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS batch_permission_operation (
                id SERIAL PRIMARY KEY,
                tipo_operacao VARCHAR(50) NOT NULL,
                descricao VARCHAR(255),
                usuarios_afetados INTEGER DEFAULT 0 NOT NULL,
                permissoes_alteradas INTEGER DEFAULT 0 NOT NULL,
                detalhes_json TEXT,
                executado_por INTEGER NOT NULL,
                executado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                status VARCHAR(20) DEFAULT 'CONCLUIDO',
                erro_detalhes TEXT,
                FOREIGN KEY (executado_por) REFERENCES usuarios(id)
            );
        """))
        
        conn.commit()
    
    logger.info("✅ Novas tabelas criadas com sucesso!")

def atualizar_tabelas_existentes():
    """Atualiza as tabelas existentes com novos campos"""
    logger.info("Atualizando tabelas existentes...")
    
    with db.engine.connect() as conn:
        # Adicionar campos à tabela modulo_sistema
        try:
            conn.execute(text("""
                ALTER TABLE modulo_sistema 
                ADD COLUMN category_id INTEGER REFERENCES permission_category(id);
            """))
            logger.info("✅ Campo category_id adicionado a modulo_sistema")
        except Exception as e:
            logger.warning(f"Campo category_id já existe ou erro: {e}")
        
        try:
            conn.execute(text("""
                ALTER TABLE modulo_sistema 
                ADD COLUMN parent_id INTEGER REFERENCES modulo_sistema(id);
            """))
            logger.info("✅ Campo parent_id adicionado a modulo_sistema")
        except Exception as e:
            logger.warning(f"Campo parent_id já existe ou erro: {e}")
        
        try:
            conn.execute(text("""
                ALTER TABLE modulo_sistema 
                ADD COLUMN nivel_hierarquico INTEGER DEFAULT 0 NOT NULL;
            """))
            logger.info("✅ Campo nivel_hierarquico adicionado a modulo_sistema")
        except Exception as e:
            logger.warning(f"Campo nivel_hierarquico já existe ou erro: {e}")
        
        # Adicionar campo submodulo_id à tabela funcao_modulo
        try:
            conn.execute(text("""
                ALTER TABLE funcao_modulo 
                ADD COLUMN submodulo_id INTEGER REFERENCES sub_module(id);
            """))
            logger.info("✅ Campo submodulo_id adicionado a funcao_modulo")
        except Exception as e:
            logger.warning(f"Campo submodulo_id já existe ou erro: {e}")
        
        conn.commit()

def migrar_dados_existentes():
    """Migra dados existentes para a nova estrutura"""
    logger.info("Migrando dados existentes...")
    
    # Criar categorias padrão
    with db.engine.connect() as conn:
        # Inserir categorias padrão
        categorias = [
            ('vendas', 'Vendas', 'Módulos de vendas e faturamento', '💰', '#28a745'),
            ('operacional', 'Operacional', 'Módulos operacionais', '🚚', '#17a2b8'),
            ('financeiro', 'Financeiro', 'Módulos financeiros', '💵', '#ffc107'),
            ('administrativo', 'Administrativo', 'Módulos administrativos', '⚙️', '#dc3545')
        ]
        
        for nome, nome_exibicao, descricao, icone, cor in categorias:
            try:
                conn.execute(text("""
                    INSERT INTO permission_category (nome, nome_exibicao, descricao, icone, cor, ordem, ativo)
                    VALUES (:nome, :nome_exibicao, :descricao, :icone, :cor, 0, true)
                    ON CONFLICT (nome) DO NOTHING
                """), {
                    "nome": nome,
                    "nome_exibicao": nome_exibicao,
                    "descricao": descricao,
                    "icone": icone,
                    "cor": cor
                })
            except Exception as e:
                logger.warning(f"Categoria {nome} já existe ou erro: {e}")
        
        conn.commit()
        
        # Mapear módulos para categorias
        mapeamento = {
            'faturamento': 'vendas',
            'carteira': 'vendas',
            'monitoramento': 'operacional',
            'embarques': 'operacional',
            'portaria': 'operacional',
            'financeiro': 'financeiro',
            'usuarios': 'administrativo',
            'admin': 'administrativo'
        }
        
        for modulo_nome, categoria_nome in mapeamento.items():
            # Buscar ID da categoria
            result = conn.execute(text(
                "SELECT id FROM permission_category WHERE nome = :cat_nome"
            ), {"cat_nome": categoria_nome}).fetchone()
            
            if result:
                categoria_id = result[0]
                # Atualizar módulo
                try:
                    conn.execute(text("""
                        UPDATE modulo_sistema 
                        SET category_id = :cat_id 
                        WHERE nome = :mod_nome
                    """), {"cat_id": categoria_id, "mod_nome": modulo_nome})
                except Exception as e:
                    logger.warning(f"Erro ao atualizar módulo {modulo_nome}: {e}")
        
        conn.commit()
    
    logger.info("✅ Dados migrados com sucesso!")

def criar_dados_exemplo():
    """Cria alguns dados de exemplo para teste"""
    logger.info("Criando dados de exemplo...")
    
    # Criar um submodulo de exemplo
    with db.engine.connect() as conn:
        # Buscar ID do módulo carteira
        result = conn.execute(text(
            "SELECT id FROM modulo_sistema WHERE nome = 'carteira'"
        )).fetchone()
        
        if result:
            modulo_id = result[0]
            try:
                conn.execute(text("""
                    INSERT INTO sub_module (modulo_id, nome, nome_exibicao, descricao, icone, ordem, ativo)
                    VALUES (:modulo_id, 'separacao', 'Separação', 'Gestão de separações de pedidos', '📦', 1, true)
                    ON CONFLICT (modulo_id, nome) DO NOTHING
                """), {"modulo_id": modulo_id})
                conn.commit()
                logger.info("✅ Submódulo de exemplo criado")
            except Exception as e:
                logger.warning(f"Submódulo já existe ou erro: {e}")

def main():
    """Executa a migração completa"""
    app = create_app()
    
    with app.app_context():
        try:
            logger.info("🚀 Iniciando migração do sistema de permissões...")
            
            # 1. Criar novas tabelas
            criar_tabelas_novas()
            
            # 2. Atualizar tabelas existentes
            atualizar_tabelas_existentes()
            
            # 3. Migrar dados existentes
            migrar_dados_existentes()
            
            # 4. Criar dados de exemplo
            criar_dados_exemplo()
            
            logger.info("🎉 Migração concluída com sucesso!")
            logger.info("⚠️  IMPORTANTE: Revise os logs acima para verificar se houve algum aviso.")
            
        except Exception as e:
            logger.error(f"❌ Erro durante a migração: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    main()