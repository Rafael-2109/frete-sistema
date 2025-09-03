#!/usr/bin/env python3
"""
Script Python para executar a migração Pedido → VIEW
Data: 2025-01-29

Mais fácil de executar que o script bash, especialmente no Windows
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

# Tentar importar dotenv se disponível
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Arquivo .env carregado")
except ImportError:
    print("ℹ️ python-dotenv não instalado, usando variáveis do ambiente")

def executar_comando(arquivo, descricao):
    """Executa um arquivo SQL ou Python"""
    database_url = os.environ.get('DATABASE_URL')
    
    # Determinar tipo de arquivo
    if arquivo.endswith('.py'):
        return executar_python(arquivo, descricao)
    else:
        return executar_sql(arquivo, descricao)

def executar_python(arquivo_py, descricao):
    """Executa um script Python"""
    print(f"\n🐍 Executando: {descricao}")
    print(f"   Arquivo: {arquivo_py}")
    
    try:
        result = subprocess.run(
            [sys.executable, arquivo_py],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {descricao} - Sucesso!")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ Erro ao executar {arquivo_py}")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def executar_sql(arquivo_sql, descricao):
    """Executa um arquivo SQL no banco"""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL não encontrada!")
        print("\nOpções:")
        print("1. Se está no Render: DATABASE_URL já deveria estar configurada")
        print("2. Se está local: Verifique o arquivo .env")
        return False
    
    # Ocultar senha no log
    db_display = database_url.split('@')[1] if '@' in database_url else 'banco'
    print(f"\n📊 Executando: {descricao}")
    print(f"   Arquivo: {arquivo_sql}")
    print(f"   Banco: ...@{db_display}")
    
    try:
        # Executar SQL usando psql
        result = subprocess.run(
            ['psql', database_url, '-f', arquivo_sql],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {descricao} - Sucesso!")
            return True
        else:
            print(f"❌ Erro ao executar {arquivo_sql}")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print("❌ psql não encontrado. Instale o PostgreSQL client.")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def criar_backup():
    """Cria backup do banco de dados"""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        return None
    
    backup_file = f"backup_migracao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    
    print(f"\n💾 Criando backup: {backup_file}")
    
    try:
        result = subprocess.run(
            ['pg_dump', database_url, '-f', backup_file],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Backup criado: {backup_file}")
            return backup_file
        else:
            print(f"⚠️ Não foi possível criar backup")
            print(result.stderr)
            return None
            
    except FileNotFoundError:
        print("⚠️ pg_dump não encontrado. Continuando sem backup...")
        return None

def main():
    """Executa a migração completa"""
    
    print("=" * 50)
    print("MIGRAÇÃO: PEDIDO → VIEW")
    print("=" * 50)
    
    # Verificar se já foi migrado (para deploy automático)
    if os.path.exists('verificar_view_pedidos.py'):
        import subprocess
        result = subprocess.run([sys.executable, 'verificar_view_pedidos.py'], capture_output=True)
        if result.returncode == 0:
            print("✅ Migração já foi aplicada anteriormente. Pulando...")
            return 0
    
    # Verificar arquivos necessários
    arquivos_necessarios = [
        'executar_migration_movimentacao.py',  # Adicionar colunas em MovimentacaoEstoque
        'recompor_separacoes_perdidas.py',
        'sql_render_modular.sql',
        'sql_criar_view_pedidos_final.sql',
        'sql_adicionar_cotacao_id_separacao.sql',
        'migrar_dados_pedido_para_separacao.py',
        'sql_otimizacao_indices_separacao.sql',  # Índices gerais de Separacao
        'sql_indices_ruptura.sql'  # Índices específicos para ruptura
    ]
    
    print("\n📁 Verificando arquivos...")
    for arquivo in arquivos_necessarios:
        if os.path.exists(arquivo):
            print(f"   ✅ {arquivo}")
        else:
            print(f"   ❌ {arquivo} não encontrado!")
            return 1
    
    # Criar backup (opcional mas recomendado)
    backup_file = criar_backup()
    
    # Se estiver rodando no Render (detectado por variável de ambiente), não pedir confirmação
    is_render = os.environ.get('RENDER') == 'true' or os.environ.get('IS_PULL_REQUEST') == 'false'
    
    if not is_render:
        # Confirmar execução apenas se não for deploy automático
        print("\n⚠️ ATENÇÃO: Esta migração irá:")
        print("   1. Adicionar campos em Separacao")
        print("   2. Migrar dados de Pedido → Separacao")
        print("   3. Renomear pedidos → pedidos_backup")
        print("   4. Criar VIEW pedidos")
        
        resposta = input("\n▶️ Deseja continuar? (s/N): ")
        if resposta.lower() != 's':
            print("❌ Migração cancelada")
            return 0
    else:
        print("\n🚀 Deploy automático detectado. Executando migração...")
        print("   1. Adicionar campos em Separacao")
        print("   2. Migrar dados de Pedido → Separacao")
        print("   3. Renomear pedidos → pedidos_backup")
        print("   4. Criar VIEW pedidos")
    
    # Executar migração
    etapas = [
        ('executar_migration_movimentacao.py', 'Adicionar campos estruturados em MovimentacaoEstoque'),
        ('recompor_separacoes_perdidas.py', 'Recompor separações perdidas usando FaturamentoProduto'),
        ('sql_render_modular.sql', 'Adicionar campos básicos em Separacao'),
        ('sql_adicionar_cotacao_id_separacao.sql', 'Adicionar cotacao_id em Separacao'),
        ('migrar_dados_pedido_para_separacao.py', 'Migrar dados de Pedido para Separacao'),
        ('sql_criar_view_pedidos_final.sql', 'Criar VIEW pedidos'),
        ('sql_otimizacao_indices_separacao.sql', 'Criar índices otimizados para Separacao'),
        ('sql_indices_ruptura.sql', 'Criar índices otimizados para análise de ruptura'),
        ('sql_indices_estoque_otimizado.sql', 'Criar índices otimizados para sistema de estoque simplificado'),
    ]
    
    for arquivo, descricao in etapas:
        if not executar_comando(arquivo, descricao):
            print(f"\n❌ Migração falhou na etapa: {descricao}")
            if backup_file:
                print(f"💡 Para reverter, execute: psql $DATABASE_URL < {backup_file}")
            return 1
    
    # Sucesso!
    print("\n" + "=" * 50)
    print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 50)
    
    # Atualizar modelo Python
    print("\n🐍 Atualizando modelo Python...")
    if os.path.exists('app/pedidos/models_adapter.py'):
        try:
            # Fazer backup
            from datetime import datetime
            
            if os.path.exists('app/pedidos/models.py'):
                backup_name = f"app/pedidos/models_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
                shutil.copy('app/pedidos/models.py', backup_name)
                print(f"   ✅ Backup criado: {backup_name}")
            
            # Substituir pelo adapter
            shutil.copy('app/pedidos/models_adapter.py', 'app/pedidos/models.py')
            print("   ✅ Modelo Pedido atualizado para usar VIEW")
        except Exception as e:
            print(f"   ⚠️ Não foi possível atualizar modelo: {e}")
    else:
        print("   ⚠️ models_adapter.py não encontrado - atualize manualmente")
    
    print("\n📋 Próximos passos:")
    print("1. Testar a aplicação")
    print("2. Verificar que Pedido.query.get(id) funciona")
    print("3. Após validação, executar:")
    print("   - DROP TABLE pedidos_backup;")
    print("   - DROP TABLE pre_separacao_item;")
    
    if backup_file:
        print(f"\n💾 Backup salvo em: {backup_file}")
        print(f"   Para reverter: psql $DATABASE_URL < {backup_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())