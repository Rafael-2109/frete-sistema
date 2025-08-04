#!/usr/bin/env python3
"""
Script rápido para configurar o cache de estoque
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

def criar_tabelas_cache():
    """Cria as tabelas de cache diretamente via SQL"""
    app = create_app()
    
    with app.app_context():
        try:
            print("=" * 60)
            print("CONFIGURAÇÃO RÁPIDA DO CACHE DE ESTOQUE")
            print("=" * 60)
            
            # SQL para criar as tabelas
            sql_saldo_cache = """
            CREATE TABLE IF NOT EXISTS saldo_estoque_cache (
                id SERIAL PRIMARY KEY,
                cod_produto VARCHAR(50) NOT NULL UNIQUE,
                nome_produto VARCHAR(200) NOT NULL,
                saldo_atual NUMERIC(15,3) NOT NULL DEFAULT 0,
                qtd_carteira NUMERIC(15,3) NOT NULL DEFAULT 0,
                qtd_pre_separacao NUMERIC(15,3) NOT NULL DEFAULT 0,
                qtd_separacao NUMERIC(15,3) NOT NULL DEFAULT 0,
                previsao_ruptura_7d NUMERIC(15,3),
                status_ruptura VARCHAR(20),
                ultima_atualizacao_saldo TIMESTAMP,
                ultima_atualizacao_carteira TIMESTAMP,
                ultima_atualizacao_projecao TIMESTAMP,
                criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            sql_projecao_cache = """
            CREATE TABLE IF NOT EXISTS projecao_estoque_cache (
                id SERIAL PRIMARY KEY,
                cod_produto VARCHAR(50) NOT NULL,
                data_projecao DATE NOT NULL,
                dia_offset INTEGER NOT NULL,
                estoque_inicial NUMERIC(15,3) NOT NULL DEFAULT 0,
                saida_prevista NUMERIC(15,3) NOT NULL DEFAULT 0,
                producao_programada NUMERIC(15,3) NOT NULL DEFAULT 0,
                estoque_final NUMERIC(15,3) NOT NULL DEFAULT 0,
                atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cod_produto, data_projecao)
            );
            """
            
            sql_cache_log = """
            CREATE TABLE IF NOT EXISTS cache_update_log (
                id SERIAL PRIMARY KEY,
                tabela_origem VARCHAR(50) NOT NULL,
                operacao VARCHAR(20) NOT NULL,
                cod_produto VARCHAR(50),
                processado BOOLEAN DEFAULT FALSE,
                criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                processado_em TIMESTAMP
            );
            """
            
            # Criar índices
            sql_indices = """
            CREATE INDEX IF NOT EXISTS idx_saldo_cache_status ON saldo_estoque_cache(status_ruptura);
            CREATE INDEX IF NOT EXISTS idx_saldo_cache_ruptura ON saldo_estoque_cache(previsao_ruptura_7d);
            CREATE INDEX IF NOT EXISTS idx_projecao_produto_dia ON projecao_estoque_cache(cod_produto, dia_offset);
            CREATE INDEX IF NOT EXISTS idx_cache_log_processado ON cache_update_log(processado);
            CREATE INDEX IF NOT EXISTS idx_cache_log_produto ON cache_update_log(cod_produto);
            """
            
            print("\n1. Criando tabelas de cache...")
            db.session.execute(text(sql_saldo_cache))
            db.session.execute(text(sql_projecao_cache))
            db.session.execute(text(sql_cache_log))
            db.session.commit()
            print("✅ Tabelas criadas")
            
            print("\n2. Criando índices...")
            for sql in sql_indices.strip().split(';'):
                if sql.strip():
                    db.session.execute(text(sql))
            db.session.commit()
            print("✅ Índices criados")
            
            # Importar e inicializar cache
            print("\n3. Inicializando cache com dados existentes...")
            from app.estoque.models_cache import SaldoEstoqueCache
            
            # Popular cache apenas com produtos mais usados (top 100)
            sql_top_produtos = """
            INSERT INTO saldo_estoque_cache (cod_produto, nome_produto, saldo_atual, status_ruptura, ultima_atualizacao_saldo)
            SELECT 
                cod_produto,
                MAX(nome_produto) as nome_produto,
                SUM(qtd_movimentacao) as saldo_atual,
                CASE 
                    WHEN SUM(qtd_movimentacao) <= 0 THEN 'CRÍTICO'
                    WHEN SUM(qtd_movimentacao) < 10 THEN 'ATENÇÃO'
                    ELSE 'OK'
                END as status_ruptura,
                NOW() as ultima_atualizacao_saldo
            FROM movimentacao_estoque
            WHERE ativo = true
            GROUP BY cod_produto
            LIMIT 200
            ON CONFLICT (cod_produto) DO UPDATE
            SET 
                saldo_atual = EXCLUDED.saldo_atual,
                status_ruptura = EXCLUDED.status_ruptura,
                ultima_atualizacao_saldo = EXCLUDED.ultima_atualizacao_saldo;
            """
            
            db.session.execute(text(sql_top_produtos))
            db.session.commit()
            
            # Contar registros
            result = db.session.execute(text("SELECT COUNT(*) FROM saldo_estoque_cache")).scalar()
            print(f"✅ Cache inicializado com {result} produtos")
            
            # Estatísticas
            stats = db.session.execute(text("""
                SELECT 
                    COUNT(*) FILTER (WHERE status_ruptura = 'CRÍTICO') as criticos,
                    COUNT(*) FILTER (WHERE status_ruptura = 'ATENÇÃO') as atencao,
                    COUNT(*) FILTER (WHERE status_ruptura = 'OK') as ok
                FROM saldo_estoque_cache
            """)).first()
            
            print(f"\n4. Estatísticas do cache:")
            print(f"   - CRÍTICOS: {stats.criticos}")
            print(f"   - ATENÇÃO: {stats.atencao}")
            print(f"   - OK: {stats.ok}")
            
            print("\n" + "=" * 60)
            print("✅ CACHE CONFIGURADO COM SUCESSO!")
            print("Acesse: /estoque/saldo-estoque")
            print("Performance esperada: < 1 segundo")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    sucesso = criar_tabelas_cache()
    sys.exit(0 if sucesso else 1)