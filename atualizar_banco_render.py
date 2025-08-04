#!/usr/bin/env python3
"""
Script Python para atualizar o banco de dados PostgreSQL no Render
Compatível com PostgreSQL 12+ 
Executa todas as alterações necessárias de forma segura
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseUpdater:
    def __init__(self, database_url=None):
        """Inicializar o atualizador do banco"""
        self.database_url = database_url or os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL não encontrada. Configure a variável de ambiente.")
        
        self.conn = None
        self.cursor = None
        self.changes_made = []
        self.errors = []
        
    def connect(self):
        """Conectar ao banco de dados PostgreSQL"""
        try:
            logger.info("🔌 Conectando ao banco de dados PostgreSQL...")
            self.conn = psycopg2.connect(self.database_url)
            self.cursor = self.conn.cursor()
            
            # Verificar versão do PostgreSQL
            self.cursor.execute("SELECT version()")
            version = self.cursor.fetchone()[0]
            logger.info(f"📊 Versão do PostgreSQL: {version.split(',')[0]}")
            
            # Verificar se é realmente PostgreSQL
            if 'PostgreSQL' not in version:
                raise ValueError("Este script é apenas para bancos PostgreSQL!")
            
            logger.info("✅ Conectado com sucesso ao PostgreSQL!")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao conectar: {e}")
            return False
    
    def disconnect(self):
        """Desconectar do banco"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("🔌 Desconectado do banco")
    
    def check_column_exists(self, table_name, column_name):
        """Verificar se uma coluna existe"""
        query = """
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = %s 
            AND column_name = %s
        );
        """
        self.cursor.execute(query, (table_name, column_name))
        return self.cursor.fetchone()[0]
    
    def check_index_exists(self, table_name, index_name):
        """Verificar se um índice existe"""
        query = """
        SELECT EXISTS (
            SELECT 1 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND tablename = %s 
            AND indexname = %s
        );
        """
        self.cursor.execute(query, (table_name, index_name))
        return self.cursor.fetchone()[0]
    
    def add_column(self, table_name, column_name, column_type, default_value=None):
        """Adicionar coluna se não existir"""
        try:
            if not self.check_column_exists(table_name, column_name):
                query = f"ALTER TABLE public.{table_name} ADD COLUMN {column_name} {column_type}"
                if default_value:
                    query += f" DEFAULT {default_value}"
                
                self.cursor.execute(query)
                self.changes_made.append(f"✅ Coluna {column_name} adicionada na tabela {table_name}")
                logger.info(f"✅ Coluna {column_name} adicionada na tabela {table_name}")
                return True
            else:
                logger.info(f"⚠️  Coluna {column_name} já existe na tabela {table_name}")
                return False
        except Exception as e:
            error_msg = f"❌ Erro ao adicionar coluna {column_name} em {table_name}: {e}"
            self.errors.append(error_msg)
            logger.error(error_msg)
            raise
    
    def create_index(self, table_name, index_name, column_name):
        """Criar índice se não existir"""
        try:
            if not self.check_index_exists(table_name, index_name):
                query = f"CREATE INDEX {index_name} ON public.{table_name} ({column_name})"
                self.cursor.execute(query)
                self.changes_made.append(f"✅ Índice {index_name} criado na tabela {table_name}")
                logger.info(f"✅ Índice {index_name} criado na tabela {table_name}")
                return True
            else:
                logger.info(f"⚠️  Índice {index_name} já existe na tabela {table_name}")
                return False
        except Exception as e:
            error_msg = f"❌ Erro ao criar índice {index_name}: {e}"
            self.errors.append(error_msg)
            logger.error(error_msg)
            raise
    
    def clean_invalid_data(self):
        """Limpar dados inválidos"""
        try:
            # Limpar valores inválidos em separacao_lote_id
            query = """
            UPDATE public.separacao 
            SET separacao_lote_id = NULL 
            WHERE separacao_lote_id IN ('', 'null', 'NULL', 'None')
            AND separacao_lote_id IS NOT NULL;
            """
            self.cursor.execute(query)
            rows_affected = self.cursor.rowcount
            if rows_affected > 0:
                self.changes_made.append(f"✅ {rows_affected} valores inválidos limpos em separacao_lote_id")
                logger.info(f"✅ {rows_affected} valores inválidos limpos")
        except Exception as e:
            logger.warning(f"⚠️  Erro ao limpar dados: {e}")
    
    def initialize_cache_tables(self):
        """Criar e inicializar tabelas de cache se não existirem"""
        try:
            # 1. Criar tabela saldo_estoque_cache se não existir
            query_saldo_cache = """
            CREATE TABLE IF NOT EXISTS public.saldo_estoque_cache (
                id SERIAL PRIMARY KEY,
                cod_produto VARCHAR(50) NOT NULL,
                nome_produto VARCHAR(255),
                qtd_saldo NUMERIC(15,3) DEFAULT 0,
                qtd_carteira NUMERIC(15,3) DEFAULT 0,
                qtd_disponivel NUMERIC(15,3) DEFAULT 0,
                ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cod_produto)
            );
            """
            self.cursor.execute(query_saldo_cache)
            
            # 2. Criar tabela projecao_estoque_cache se não existir
            query_projecao_cache = """
            CREATE TABLE IF NOT EXISTS public.projecao_estoque_cache (
                id SERIAL PRIMARY KEY,
                cod_produto VARCHAR(50) NOT NULL,
                data_projecao DATE NOT NULL,
                qtd_entrada_prevista NUMERIC(15,3) DEFAULT 0,
                qtd_saida_prevista NUMERIC(15,3) DEFAULT 0,
                saldo_projetado NUMERIC(15,3) DEFAULT 0,
                ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cod_produto, data_projecao)
            );
            """
            self.cursor.execute(query_projecao_cache)
            
            # 3. Criar tabela cache_update_log se não existir
            query_update_log = """
            CREATE TABLE IF NOT EXISTS public.cache_update_log (
                id SERIAL PRIMARY KEY,
                tabela_cache VARCHAR(100) NOT NULL,
                tipo_atualizacao VARCHAR(50),
                registros_afetados INTEGER DEFAULT 0,
                tempo_execucao_ms INTEGER,
                mensagem TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            self.cursor.execute(query_update_log)
            
            # 4. Criar índices para as tabelas de cache
            indices_cache = [
                ("idx_saldo_cache_produto", "saldo_estoque_cache", "cod_produto"),
                ("idx_saldo_cache_atualizacao", "saldo_estoque_cache", "ultima_atualizacao"),
                ("idx_projecao_cache_produto", "projecao_estoque_cache", "cod_produto"),
                ("idx_projecao_cache_data", "projecao_estoque_cache", "data_projecao"),
                ("idx_cache_log_tabela", "cache_update_log", "tabela_cache"),
                ("idx_cache_log_criado", "cache_update_log", "criado_em")
            ]
            
            for index_name, table_name, column_name in indices_cache:
                if not self.check_index_exists(table_name, index_name):
                    self.cursor.execute(f"CREATE INDEX {index_name} ON public.{table_name} ({column_name})")
                    logger.info(f"✅ Índice {index_name} criado para cache")
            
            # 5. Inicializar cache com dados básicos se estiver vazio
            self.cursor.execute("SELECT COUNT(*) FROM public.saldo_estoque_cache")
            count = self.cursor.fetchone()[0]
            
            if count == 0:
                logger.info("📦 Inicializando cache de saldo de estoque...")
                query_init_cache = """
                INSERT INTO public.saldo_estoque_cache (cod_produto, nome_produto, qtd_saldo, qtd_carteira, qtd_disponivel)
                SELECT DISTINCT 
                    cp.cod_produto,
                    cp.nome_produto,
                    COALESCE(SUM(cp.qtd_saldo), 0) as qtd_saldo,
                    COALESCE(SUM(cp.qtd_saldo_produto_pedido), 0) as qtd_carteira,
                    COALESCE(SUM(cp.qtd_saldo), 0) - COALESCE(SUM(cp.qtd_saldo_produto_pedido), 0) as qtd_disponivel
                FROM public.carteira_principal cp
                WHERE cp.cod_produto IS NOT NULL
                GROUP BY cp.cod_produto, cp.nome_produto
                ON CONFLICT (cod_produto) DO UPDATE SET
                    qtd_saldo = EXCLUDED.qtd_saldo,
                    qtd_carteira = EXCLUDED.qtd_carteira,
                    qtd_disponivel = EXCLUDED.qtd_disponivel,
                    ultima_atualizacao = CURRENT_TIMESTAMP;
                """
                self.cursor.execute(query_init_cache)
                rows_affected = self.cursor.rowcount
                if rows_affected > 0:
                    self.changes_made.append(f"✅ Cache inicializado com {rows_affected} produtos")
                    logger.info(f"✅ Cache inicializado com {rows_affected} produtos")
                
                # Registrar no log
                self.cursor.execute("""
                    INSERT INTO public.cache_update_log (tabela_cache, tipo_atualizacao, registros_afetados, mensagem)
                    VALUES ('saldo_estoque_cache', 'INICIALIZACAO', %s, 'Cache inicializado com dados da carteira_principal')
                """, (rows_affected,))
            
            self.changes_made.append("✅ Tabelas de cache verificadas/criadas")
            logger.info("✅ Tabelas de cache prontas")
            
        except Exception as e:
            logger.warning(f"⚠️  Erro ao inicializar cache: {e}")
    
    def get_table_stats(self):
        """Obter estatísticas das tabelas"""
        stats = {}
        tables = ['carteira_principal', 'separacao', 'pre_separacao_itens', 
                  'vinculacao_carteira_separacao', 'embarques', 'embarque_itens',
                  'saldo_estoque_cache', 'projecao_estoque_cache', 'cache_update_log']
        
        for table in tables:
            try:
                self.cursor.execute(f"SELECT COUNT(*) FROM public.{table}")
                count = self.cursor.fetchone()[0]
                stats[table] = count
                logger.info(f"📊 {table}: {count} registros")
            except:
                stats[table] = "N/A"
        
        return stats
    
    def run_updates(self):
        """Executar todas as atualizações"""
        print("\n" + "="*60)
        print("🚀 INICIANDO ATUALIZAÇÃO DO BANCO DE DADOS RENDER")
        print("="*60 + "\n")
        
        if not self.connect():
            return False
        
        try:
            # Iniciar transação
            logger.info("🔄 Iniciando transação...")
            
            # 1. ADICIONAR COLUNAS NA TABELA SEPARACAO
            print("\n📋 Atualizando tabela SEPARACAO...")
            self.add_column('separacao', 'separacao_lote_id', 'VARCHAR(50)')
            self.add_column('separacao', 'tipo_envio', 'VARCHAR(10)', "'total'")
            
            # 2. ADICIONAR COLUNAS NA TABELA PRE_SEPARACAO_ITENS
            print("\n📋 Atualizando tabela PRE_SEPARACAO_ITENS...")
            self.add_column('pre_separacao_itens', 'tipo_envio', 'VARCHAR(10)', "'total'")
            
            # 3. ADICIONAR COLUNAS NA TABELA CARTEIRA_PRINCIPAL
            print("\n📋 Atualizando tabela CARTEIRA_PRINCIPAL...")
            self.add_column('carteira_principal', 'qtd_pre_separacoes', 'INTEGER', '0')
            self.add_column('carteira_principal', 'qtd_separacoes', 'INTEGER', '0')
            
            # 4. CRIAR ÍNDICES PARA PERFORMANCE
            print("\n🔍 Criando índices para melhor performance...")
            self.create_index('separacao', 'idx_separacao_lote_id', 'separacao_lote_id')
            self.create_index('separacao', 'idx_separacao_num_pedido', 'num_pedido')
            self.create_index('pre_separacao_itens', 'idx_pre_separacao_carteira_id', 'carteira_principal_id')
            self.create_index('carteira_principal', 'idx_carteira_num_pedido', 'num_pedido')
            self.create_index('carteira_principal', 'idx_carteira_cod_produto', 'cod_produto')
            
            # 5. LIMPAR DADOS INVÁLIDOS
            print("\n🧹 Limpando dados inválidos...")
            self.clean_invalid_data()
            
            # 6. INICIALIZAR TABELAS DE CACHE (se não existirem)
            print("\n💾 Verificando/criando tabelas de cache...")
            self.initialize_cache_tables()
            
            # 7. OBTER ESTATÍSTICAS
            print("\n📊 Estatísticas das tabelas:")
            stats = self.get_table_stats()
            
            # Confirmar transação
            if not self.errors:
                self.conn.commit()
                logger.info("✅ Transação confirmada com sucesso!")
                
                # Executar VACUUM ANALYZE (PostgreSQL específico)
                print("\n🔧 Executando VACUUM ANALYZE (PostgreSQL)...")
                self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)  # Necessário para VACUUM no PostgreSQL
                vacuum_cursor = self.conn.cursor()
                vacuum_cursor.execute("VACUUM ANALYZE")
                vacuum_cursor.close()
                logger.info("✅ VACUUM ANALYZE executado no PostgreSQL")
                
                # Relatório final
                print("\n" + "="*60)
                print("✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!")
                print("="*60)
                
                if self.changes_made:
                    print("\n📝 Alterações realizadas:")
                    for change in self.changes_made:
                        print(f"   {change}")
                else:
                    print("\n⚠️  Nenhuma alteração foi necessária (banco já atualizado)")
                
                print("\n📊 Total de registros nas tabelas principais:")
                for table, count in stats.items():
                    print(f"   - {table}: {count}")
                
                return True
            else:
                self.conn.rollback()
                logger.error("❌ Transação revertida devido a erros")
                print("\n❌ ERROS ENCONTRADOS:")
                for error in self.errors:
                    print(f"   {error}")
                return False
                
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ Erro durante atualização: {e}")
            print(f"\n❌ Erro durante atualização: {e}")
            return False
        finally:
            self.disconnect()
    
    def verify_updates(self):
        """Verificar se as atualizações foram aplicadas"""
        print("\n🔍 Verificando atualizações...")
        
        if not self.connect():
            return False
        
        try:
            checks = {
                'separacao.separacao_lote_id': self.check_column_exists('separacao', 'separacao_lote_id'),
                'separacao.tipo_envio': self.check_column_exists('separacao', 'tipo_envio'),
                'pre_separacao_itens.tipo_envio': self.check_column_exists('pre_separacao_itens', 'tipo_envio'),
                'carteira_principal.qtd_pre_separacoes': self.check_column_exists('carteira_principal', 'qtd_pre_separacoes'),
                'carteira_principal.qtd_separacoes': self.check_column_exists('carteira_principal', 'qtd_separacoes'),
                'idx_separacao_lote_id': self.check_index_exists('separacao', 'idx_separacao_lote_id'),
                'idx_separacao_num_pedido': self.check_index_exists('separacao', 'idx_separacao_num_pedido'),
            }
            
            all_ok = True
            for item, exists in checks.items():
                status = "✅" if exists else "❌"
                print(f"   {status} {item}")
                if not exists:
                    all_ok = False
            
            if all_ok:
                print("\n✅ Todas as atualizações foram aplicadas com sucesso!")
            else:
                print("\n⚠️  Algumas atualizações estão pendentes")
            
            return all_ok
            
        finally:
            self.disconnect()


def main():
    """Função principal"""
    print("""
    ╔════════════════════════════════════════════╗
    ║  ATUALIZADOR DE BANCO PostgreSQL - RENDER ║
    ╠════════════════════════════════════════════╣
    ║  Este script irá:                          ║
    ║  • Adicionar colunas necessárias          ║
    ║  • Criar índices para performance         ║
    ║  • Limpar dados inválidos                 ║
    ║  • Inicializar tabelas de cache           ║
    ║  • NÃO apagará nenhum dado importante     ║
    ╚════════════════════════════════════════════╝
    
    📌 Compatível com PostgreSQL 12+
    """)
    
    # Verificar se está no Render
    if not os.environ.get('DATABASE_URL'):
        print("⚠️  DATABASE_URL não encontrada!")
        print("📝 Se estiver rodando localmente para teste, configure:")
        print("   export DATABASE_URL='sua_url_aqui'")
        return
    
    # Perguntar confirmação
    response = input("\n❓ Deseja continuar com a atualização? (s/n): ")
    if response.lower() != 's':
        print("❌ Atualização cancelada")
        return
    
    # Criar atualizador e executar
    updater = DatabaseUpdater()
    
    # Executar atualizações
    success = updater.run_updates()
    
    if success:
        # Verificar se tudo foi aplicado
        updater.verify_updates()
        print("\n✅ Processo concluído com sucesso!")
        print("🎉 O banco de dados está atualizado e pronto para uso!")
    else:
        print("\n❌ Processo falhou. Verifique os logs acima.")
        print("💡 Dica: O banco não foi alterado devido ao rollback automático")
    
    print("\n" + "="*60)
    print("Log salvo em: database_update.log")
    print("="*60)


if __name__ == "__main__":
    # Configurar log em arquivo também
    file_handler = logging.FileHandler('database_update.log')
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Processo interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        logging.exception("Erro inesperado")