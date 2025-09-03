#!/usr/bin/env python3
"""
Script para aplicar índices otimizados do sistema de estoque simplificado
Aplica localmente e pode ser executado no Render
"""

import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

# Importar aplicação Flask
from sqlalchemy import text
from app import db, create_app

def criar_indices():
    """Cria todos os índices otimizados para o sistema de estoque"""
    
    indices = [
        # MovimentacaoEstoque
        {
            'nome': 'idx_mov_estoque_produto_ativo_not_cancelado',
            'sql': """
                CREATE INDEX IF NOT EXISTS idx_mov_estoque_produto_ativo_not_cancelado 
                ON movimentacao_estoque(cod_produto, ativo)
                WHERE ativo = true AND (status_nf != 'CANCELADO' OR status_nf IS NULL)
            """
        },
        {
            'nome': 'idx_mov_estoque_cobertura',
            'sql': """
                CREATE INDEX IF NOT EXISTS idx_mov_estoque_cobertura 
                ON movimentacao_estoque(cod_produto, qtd_movimentacao)
                WHERE ativo = true AND (status_nf != 'CANCELADO' OR status_nf IS NULL)
            """
        },
        
        # Separacao
        {
            'nome': 'idx_separacao_produto_expedicao_sync',
            'sql': """
                CREATE INDEX IF NOT EXISTS idx_separacao_produto_expedicao_sync 
                ON separacao(cod_produto, expedicao, sincronizado_nf)
                WHERE sincronizado_nf = false
            """
        },
        {
            'nome': 'idx_separacao_cobertura',
            'sql': """
                CREATE INDEX IF NOT EXISTS idx_separacao_cobertura 
                ON separacao(cod_produto, expedicao, qtd_saldo)
                WHERE sincronizado_nf = false
            """
        },
        
        # ProgramacaoProducao
        {
            'nome': 'idx_programacao_produto_data',
            'sql': """
                CREATE INDEX IF NOT EXISTS idx_programacao_produto_data 
                ON programacao_producao(cod_produto, data_programacao)
            """
        },
        {
            'nome': 'idx_programacao_cobertura',
            'sql': """
                CREATE INDEX IF NOT EXISTS idx_programacao_cobertura
                ON programacao_producao(cod_produto, data_programacao, qtd_programada)
            """
        },
        
        # UnificacaoCodigos
        {
            'nome': 'idx_unificacao_origem',
            'sql': """
                CREATE INDEX IF NOT EXISTS idx_unificacao_origem 
                ON unificacao_codigos(codigo_origem)
                WHERE ativo = true
            """
        },
        {
            'nome': 'idx_unificacao_destino',
            'sql': """
                CREATE INDEX IF NOT EXISTS idx_unificacao_destino 
                ON unificacao_codigos(codigo_destino)
                WHERE ativo = true
            """
        }
    ]
    
    print("=" * 50)
    print("CRIANDO ÍNDICES OTIMIZADOS PARA SISTEMA DE ESTOQUE")
    print("=" * 50)
    
    sucesso = 0
    erro = 0
    
    for indice in indices:
        try:
            print(f"\n📊 Criando índice: {indice['nome']}")
            db.session.execute(text(indice['sql']))
            db.session.commit()
            print(f"   ✅ {indice['nome']} criado com sucesso")
            sucesso += 1
        except Exception as e:
            print(f"   ❌ Erro ao criar {indice['nome']}: {e}")
            erro += 1
            db.session.rollback()
    
    # Atualizar estatísticas
    print("\n🔄 Atualizando estatísticas das tabelas...")
    tabelas = ['movimentacao_estoque', 'separacao', 'programacao_producao', 'unificacao_codigos']
    
    for tabela in tabelas:
        try:
            db.session.execute(text(f"ANALYZE {tabela}"))
            db.session.commit()
            print(f"   ✅ Estatísticas de {tabela} atualizadas")
        except Exception as e:
            print(f"   ⚠️ Erro ao analisar {tabela}: {e}")
            db.session.rollback()
    
    print("\n" + "=" * 50)
    print(f"✅ Sucesso: {sucesso} índices criados")
    if erro > 0:
        print(f"❌ Erros: {erro} índices falharam")
    print("=" * 50)
    
    return sucesso, erro

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        sucesso, erro = criar_indices()
        sys.exit(0 if erro == 0 else 1)