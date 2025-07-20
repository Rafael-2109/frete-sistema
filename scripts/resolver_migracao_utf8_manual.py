#!/usr/bin/env python3
"""
SCRIPT DEFINITIVO: Resolver Migração UTF-8 Manual
Aplica criação da tabela pre_separacao_itens via SQL direto
"""

import os
import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def aplicar_migracao_manual():
    """Aplica migração via SQL manual para resolver UTF-8"""
    
    try:
        logger.info("🔧 ETAPA 1 CRÍTICA: Resolvendo Migração UTF-8 Manual")
        
        # Tentar importar psycopg2 para conexão direta
        try:
            import psycopg2
            from urllib.parse import urlparse
        except ImportError:
            logger.error("❌ psycopg2 não instalado. Execute: pip install psycopg2-binary")
            return False
        
        # Obter DATABASE_URL
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("❌ DATABASE_URL não encontrada")
            return False
        
        # Parse da URL de forma segura
        try:
            parsed = urlparse(database_url)
            logger.info(f"📍 Conectando ao banco: {parsed.hostname}")
        except Exception as e:
            logger.error(f"❌ Erro ao fazer parse da URL: {e}")
            return False
        
        # SQL para criar tabela pre_separacao_itens
        sql_create_table = """
        CREATE TABLE IF NOT EXISTS pre_separacao_itens (
            id SERIAL PRIMARY KEY,
            num_pedido VARCHAR(50) NOT NULL,
            cod_produto VARCHAR(50) NOT NULL,
            cnpj_cliente VARCHAR(20),
            qtd_original_carteira NUMERIC(15,3) NOT NULL,
            qtd_selecionada_usuario NUMERIC(15,3) NOT NULL,
            qtd_restante_calculada NUMERIC(15,3) NOT NULL,
            valor_original_item NUMERIC(15,2),
            peso_original_item NUMERIC(15,3),
            hash_item_original VARCHAR(128),
            data_expedicao_editada DATE,
            data_agendamento_editada DATE,
            protocolo_editado VARCHAR(50),
            observacoes_usuario TEXT,
            recomposto BOOLEAN DEFAULT FALSE,
            data_recomposicao TIMESTAMP,
            recomposto_por VARCHAR(100),
            versao_carteira_original VARCHAR(50),
            versao_carteira_recomposta VARCHAR(50),
            status VARCHAR(20) DEFAULT 'CRIADO',
            tipo_envio VARCHAR(10) DEFAULT 'total',
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            criado_por VARCHAR(100),
            
            -- Índices para performance
            CONSTRAINT pre_separacao_itens_pedido_produto_unique 
                UNIQUE (num_pedido, cod_produto, cnpj_cliente, data_criacao)
        );
        
        -- Criar índices
        CREATE INDEX IF NOT EXISTS idx_pre_separacao_num_pedido 
            ON pre_separacao_itens(num_pedido);
        CREATE INDEX IF NOT EXISTS idx_pre_separacao_cnpj_cliente 
            ON pre_separacao_itens(cnpj_cliente);
        CREATE INDEX IF NOT EXISTS idx_pre_separacao_status 
            ON pre_separacao_itens(status);
        CREATE INDEX IF NOT EXISTS idx_pre_separacao_recomposto 
            ON pre_separacao_itens(recomposto);
        """
        
        # Conectar com psycopg2 diretamente
        logger.info("🔄 Tentando conexão direta com psycopg2...")
        
        # Extrair nome do banco de forma segura
        database_name = 'postgres'  # Fallback padrão
        if parsed.path is not None and len(parsed.path) > 1:
            database_name = parsed.path[1:]  # Remove '/' do início
        
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=database_name,
            user=parsed.username,
            password=parsed.password,
            # Configurações específicas para UTF-8
            client_encoding='utf8',
            connect_timeout=30
        )
        
        logger.info("✅ Conexão estabelecida!")
        
        # Executar SQL
        cursor = conn.cursor()
        
        # Verificar se tabela já existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'pre_separacao_itens'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            logger.info("✅ Tabela pre_separacao_itens já existe")
        else:
            logger.info("🔄 Criando tabela pre_separacao_itens...")
            cursor.execute(sql_create_table)
            logger.info("✅ Tabela pre_separacao_itens criada com sucesso!")
        
        # Verificar estrutura da tabela
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'pre_separacao_itens'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        logger.info(f"✅ Tabela tem {len(columns)} colunas:")
        for col, dtype in columns:
            logger.info(f"  - {col}: {dtype}")
        
        # Commit e fechar
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("🎯 ETAPA 1 CONCLUÍDA: Migração UTF-8 resolvida via SQL manual")
        
        # Verificar se precisa atualizar versão da migração
        atualizar_versao_migracao()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na migração manual: {e}")
        return False

def atualizar_versao_migracao():
    """Atualiza versão do Alembic para refletir a tabela criada"""
    
    try:
        logger.info("🔄 Verificando versão do Alembic...")
        
        # Verificar se precisa executar comando Alembic
        import subprocess
        
        # Tentar marcar como aplicada a migração mais recente
        result = subprocess.run(
            ['flask', 'db', 'stamp', 'head'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.info("✅ Versão do Alembic atualizada")
        else:
            logger.warning(f"⚠️ Não foi possível atualizar Alembic: {result.stderr}")
            
    except Exception as e:
        logger.warning(f"⚠️ Erro ao atualizar Alembic: {e}")

def validar_sistema():
    """Valida se o sistema está funcionando após correção"""
    
    try:
        logger.info("🔍 Validando sistema pós-correção...")
        
        # Tentar importar modelo
        sys.path.insert(0, str(Path.cwd()))
        
        from app.carteira.models import PreSeparacaoItem
        
        logger.info("✅ Modelo PreSeparacaoItem importado com sucesso")
        
        # TODO: Testar criação de instância quando Flask context estiver disponível
        
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ Validação parcial: {e}")
        return False

def main():
    """Função principal"""
    
    logger.info("🚀 INICIANDO RESOLUÇÃO DEFINITIVA UTF-8")
    logger.info("=" * 60)
    
    # Verificar ambiente
    if not os.getenv('DATABASE_URL'):
        logger.error("❌ DATABASE_URL não configurada")
        return False
    
    # Aplicar correção
    sucesso = aplicar_migracao_manual()
    
    if sucesso:
        logger.info("=" * 60)
        logger.info("🎉 ETAPA 1 CRÍTICA CONCLUÍDA COM SUCESSO!")
        logger.info("📋 Próximos passos:")
        logger.info("  1. ✅ Migração UTF-8 resolvida")
        logger.info("  2. 🔄 Continuar com Etapa 2 (Dropdown Separações)")
        logger.info("  3. 🔄 Validações de performance")
        logger.info("=" * 60)
        
        # Validar sistema
        validar_sistema()
        
    else:
        logger.error("❌ FALHA NA ETAPA 1")
        logger.error("🔄 Considerar Plano C: Workaround permanente")
    
    return sucesso

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 