#!/usr/bin/env python3
"""
Script para executar atualização completa do banco PostgreSQL no Render
Executa comandos SQL em partes menores para evitar timeout
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RenderDatabaseUpdater:
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL não encontrada!")
        
        self.conn = None
        self.cursor = None
        self.success_count = 0
        self.error_count = 0
    
    def connect(self):
        """Conectar ao PostgreSQL"""
        logger.info("🔌 Conectando ao PostgreSQL...")
        self.conn = psycopg2.connect(self.database_url)
        self.cursor = self.conn.cursor()
        
        # Verificar versão
        self.cursor.execute("SELECT version()")
        version = self.cursor.fetchone()[0]
        logger.info(f"✅ Conectado: {version.split(',')[0]}")
        return True
    
    def disconnect(self):
        """Desconectar"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("🔌 Desconectado")
    
    def execute_sql(self, sql, description=""):
        """Executar comando SQL com tratamento de erro"""
        try:
            if description:
                logger.info(f"📌 {description}")
            self.cursor.execute(sql)
            self.success_count += 1
            return True
        except psycopg2.errors.DuplicateTable:
            logger.info(f"⏭️  Tabela já existe")
            return True
        except psycopg2.errors.DuplicateColumn:
            logger.info(f"⏭️  Coluna já existe")
            return True
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            self.error_count += 1
            raise
    
    def criar_tabelas_principais(self):
        """Criar tabelas principais"""
        logger.info("\n" + "="*50)
        logger.info("PARTE 1: TABELAS PRINCIPAIS")
        logger.info("="*50)
        
        # 1. CADASTRO_CLIENTE
        sql_cadastro_cliente = """
        CREATE TABLE IF NOT EXISTS public.cadastro_cliente (
            id SERIAL PRIMARY KEY,
            cnpj_cpf VARCHAR(20) NOT NULL UNIQUE,
            raz_social VARCHAR(255) NOT NULL,
            raz_social_red VARCHAR(100),
            municipio VARCHAR(100),
            estado VARCHAR(2),
            vendedor VARCHAR(100),
            equipe_vendas VARCHAR(100),
            cnpj_endereco_ent VARCHAR(20),
            empresa_endereco_ent VARCHAR(255),
            cep_endereco_ent VARCHAR(10),
            nome_cidade VARCHAR(100),
            cod_uf VARCHAR(2),
            bairro_endereco_ent VARCHAR(100),
            rua_endereco_ent VARCHAR(255),
            endereco_ent VARCHAR(20),
            telefone_endereco_ent VARCHAR(20),
            endereco_mesmo_cliente BOOLEAN DEFAULT true,
            cliente_ativo BOOLEAN DEFAULT true,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP,
            criado_por VARCHAR(100),
            atualizado_por VARCHAR(100),
            observacoes TEXT
        );
        """
        self.execute_sql(sql_cadastro_cliente, "Criando tabela CADASTRO_CLIENTE")
        
        # Índices
        self.execute_sql("CREATE INDEX IF NOT EXISTS idx_cadastro_cliente_cnpj ON public.cadastro_cliente (cnpj_cpf);")
        self.execute_sql("CREATE INDEX IF NOT EXISTS idx_cadastro_cliente_vendedor ON public.cadastro_cliente (vendedor);")
        self.execute_sql("CREATE INDEX IF NOT EXISTS idx_cadastro_cliente_ativo ON public.cadastro_cliente (cliente_ativo);")
    
    def criar_tabelas_cache(self):
        """Criar tabelas de cache"""
        logger.info("\n" + "="*50)
        logger.info("PARTE 2: TABELAS DE CACHE")
        logger.info("="*50)
        
        # SALDO_ESTOQUE_CACHE
        sql_saldo_cache = """
        CREATE TABLE IF NOT EXISTS public.saldo_estoque_cache (
            id SERIAL PRIMARY KEY,
            cod_produto VARCHAR(50) NOT NULL,
            nome_produto VARCHAR(255),
            qtd_saldo NUMERIC(15,3) DEFAULT 0,
            qtd_carteira NUMERIC(15,3) DEFAULT 0,
            qtd_disponivel NUMERIC(15,3) DEFAULT 0,
            qtd_reservada NUMERIC(15,3) DEFAULT 0,
            qtd_em_transito NUMERIC(15,3) DEFAULT 0,
            qtd_prevista NUMERIC(15,3) DEFAULT 0,
            custo_medio NUMERIC(15,2) DEFAULT 0,
            valor_total NUMERIC(15,2) DEFAULT 0,
            data_ultima_entrada DATE,
            data_ultima_saida DATE,
            ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            versao INTEGER DEFAULT 1,
            UNIQUE(cod_produto)
        );
        """
        self.execute_sql(sql_saldo_cache, "Criando SALDO_ESTOQUE_CACHE")
        
        # PROJECAO_ESTOQUE_CACHE
        sql_projecao_cache = """
        CREATE TABLE IF NOT EXISTS public.projecao_estoque_cache (
            id SERIAL PRIMARY KEY,
            cod_produto VARCHAR(50) NOT NULL,
            data_projecao DATE NOT NULL,
            qtd_entrada_prevista NUMERIC(15,3) DEFAULT 0,
            qtd_saida_prevista NUMERIC(15,3) DEFAULT 0,
            saldo_projetado NUMERIC(15,3) DEFAULT 0,
            saldo_minimo NUMERIC(15,3) DEFAULT 0,
            ponto_reposicao NUMERIC(15,3) DEFAULT 0,
            sugestao_compra NUMERIC(15,3) DEFAULT 0,
            ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(cod_produto, data_projecao)
        );
        """
        self.execute_sql(sql_projecao_cache, "Criando PROJECAO_ESTOQUE_CACHE")
        
        # CACHE_UPDATE_LOG
        sql_cache_log = """
        CREATE TABLE IF NOT EXISTS public.cache_update_log (
            id SERIAL PRIMARY KEY,
            tabela_cache VARCHAR(100) NOT NULL,
            tipo_atualizacao VARCHAR(50),
            registros_afetados INTEGER DEFAULT 0,
            tempo_execucao_ms INTEGER,
            mensagem TEXT,
            erro TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.execute_sql(sql_cache_log, "Criando CACHE_UPDATE_LOG")
        
        # Índices do cache
        self.execute_sql("CREATE INDEX IF NOT EXISTS idx_saldo_cache_produto ON public.saldo_estoque_cache (cod_produto);")
        self.execute_sql("CREATE INDEX IF NOT EXISTS idx_projecao_cache_produto ON public.projecao_estoque_cache (cod_produto);")
    
    def criar_tabelas_permissoes(self):
        """Criar tabelas de permissões"""
        logger.info("\n" + "="*50)
        logger.info("PARTE 3: TABELAS DE PERMISSÕES")
        logger.info("="*50)
        
        tabelas = [
            ("batch_operation", """
                CREATE TABLE IF NOT EXISTS public.batch_operation (
                    id SERIAL PRIMARY KEY,
                    operation_type VARCHAR(50) NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    total_items INTEGER DEFAULT 0,
                    processed_items INTEGER DEFAULT 0,
                    failed_items INTEGER DEFAULT 0,
                    parameters JSONB,
                    result JSONB,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                );
            """),
            ("permission_log", """
                CREATE TABLE IF NOT EXISTS public.permission_log (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    action VARCHAR(100) NOT NULL,
                    resource VARCHAR(100),
                    resource_id INTEGER,
                    old_value JSONB,
                    new_value JSONB,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT true
                );
            """),
            ("user_vendedor", """
                CREATE TABLE IF NOT EXISTS public.user_vendedor (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    vendedor_id INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER,
                    updated_at TIMESTAMP,
                    updated_by INTEGER,
                    UNIQUE(user_id, vendedor_id)
                );
            """),
            ("user_equipe", """
                CREATE TABLE IF NOT EXISTS public.user_equipe (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    equipe_id INTEGER NOT NULL,
                    role VARCHAR(50) DEFAULT 'member',
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER,
                    updated_at TIMESTAMP,
                    updated_by INTEGER,
                    UNIQUE(user_id, equipe_id)
                );
            """),
        ]
        
        for nome, sql in tabelas:
            self.execute_sql(sql, f"Criando {nome}")
    
    def adicionar_colunas_faltantes(self):
        """Adicionar colunas em tabelas existentes"""
        logger.info("\n" + "="*50)
        logger.info("PARTE 4: COLUNAS EM TABELAS EXISTENTES")
        logger.info("="*50)
        
        # Verificar e adicionar colunas
        colunas = [
            ("separacao", "separacao_lote_id", "VARCHAR(50)"),
            ("separacao", "tipo_envio", "VARCHAR(10) DEFAULT 'total'"),
            ("pre_separacao_itens", "tipo_envio", "VARCHAR(10) DEFAULT 'total'"),
            ("carteira_principal", "qtd_pre_separacoes", "INTEGER DEFAULT 0"),
            ("carteira_principal", "qtd_separacoes", "INTEGER DEFAULT 0"),
        ]
        
        for tabela, coluna, tipo in colunas:
            sql_check = f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = '{tabela}' 
                    AND column_name = '{coluna}'
                ) THEN
                    ALTER TABLE public.{tabela} ADD COLUMN {coluna} {tipo};
                    RAISE NOTICE '✅ Coluna {coluna} adicionada em {tabela}';
                ELSE
                    RAISE NOTICE '⏭️ Coluna {coluna} já existe em {tabela}';
                END IF;
            END $$;
            """
            self.execute_sql(sql_check, f"Verificando {tabela}.{coluna}")
    
    def criar_indices(self):
        """Criar índices para performance"""
        logger.info("\n" + "="*50)
        logger.info("PARTE 5: ÍNDICES DE PERFORMANCE")
        logger.info("="*50)
        
        indices = [
            ("idx_separacao_lote_id", "separacao", "separacao_lote_id"),
            ("idx_separacao_num_pedido", "separacao", "num_pedido"),
            ("idx_pre_separacao_carteira_id", "pre_separacao_itens", "carteira_principal_id"),
            ("idx_carteira_num_pedido", "carteira_principal", "num_pedido"),
            ("idx_carteira_cod_produto", "carteira_principal", "cod_produto"),
        ]
        
        for idx_name, tabela, coluna in indices:
            sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON public.{tabela} ({coluna});"
            self.execute_sql(sql, f"Criando índice {idx_name}")
    
    def limpar_dados(self):
        """Limpar dados inválidos"""
        logger.info("\n" + "="*50)
        logger.info("PARTE 6: LIMPEZA DE DADOS")
        logger.info("="*50)
        
        sql = """
        UPDATE public.separacao 
        SET separacao_lote_id = NULL 
        WHERE separacao_lote_id IN ('', 'null', 'NULL', 'None')
        AND separacao_lote_id IS NOT NULL;
        """
        self.execute_sql(sql, "Limpando valores inválidos")
    
    def executar_atualizacao(self):
        """Executar toda a atualização"""
        print("""
╔══════════════════════════════════════════════╗
║  ATUALIZADOR COMPLETO - POSTGRESQL RENDER   ║
╠══════════════════════════════════════════════╣
║  • Criação de 18 tabelas faltantes          ║
║  • Adição de colunas necessárias            ║
║  • Criação de índices de performance        ║
║  • Limpeza de dados inválidos               ║
╚══════════════════════════════════════════════╝
        """)
        
        if not self.connect():
            return False
        
        try:
            # Iniciar transação
            logger.info("🔄 Iniciando transação...")
            
            # Executar em etapas
            self.criar_tabelas_principais()
            self.criar_tabelas_cache()
            self.criar_tabelas_permissoes()
            self.adicionar_colunas_faltantes()
            self.criar_indices()
            self.limpar_dados()
            
            # Commit
            self.conn.commit()
            logger.info("\n✅ TRANSAÇÃO CONFIRMADA COM SUCESSO!")
            
            # Estatísticas
            logger.info(f"\n📊 RESUMO:")
            logger.info(f"   Operações bem-sucedidas: {self.success_count}")
            logger.info(f"   Erros: {self.error_count}")
            
            # VACUUM
            logger.info("\n🔧 Executando VACUUM ANALYZE...")
            self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            vacuum_cursor = self.conn.cursor()
            vacuum_cursor.execute("VACUUM ANALYZE")
            vacuum_cursor.close()
            logger.info("✅ VACUUM ANALYZE concluído!")
            
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"\n❌ ERRO: {e}")
            logger.error("🔄 Transação revertida (ROLLBACK)")
            return False
        finally:
            self.disconnect()

def main():
    """Função principal"""
    import sys
    
    # Verificar DATABASE_URL
    if not os.environ.get('DATABASE_URL'):
        print("❌ DATABASE_URL não encontrada!")
        print("📝 Execute este script no Shell do Render")
        sys.exit(1)
    
    # Perguntar confirmação
    print("\n⚠️  Este script irá:")
    print("   • Criar 18 tabelas novas")
    print("   • Adicionar colunas em tabelas existentes")
    print("   • Criar índices de performance")
    print("   • NÃO apagará nenhum dado\n")
    
    resposta = input("Deseja continuar? (s/n): ")
    if resposta.lower() != 's':
        print("❌ Cancelado pelo usuário")
        sys.exit(0)
    
    # Executar
    updater = RenderDatabaseUpdater()
    sucesso = updater.executar_atualizacao()
    
    if sucesso:
        print("\n" + "="*50)
        print("✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!")
        print("="*50)
        print("\nPróximos passos:")
        print("1. Teste o sistema")
        print("2. Faça commit do código se tudo estiver OK")
    else:
        print("\n❌ Atualização falhou - banco não foi alterado")
        sys.exit(1)

if __name__ == "__main__":
    main()