#!/usr/bin/env python
"""
Script para limpar pré-separações órfãs (sem separacao_lote_id)
Essas pré-separações foram criadas antes do campo existir
"""
import os
import sys
import psycopg2
from urllib.parse import urlparse
from datetime import datetime

def get_db_connection():
    """Obter conexão com o banco de dados"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL não encontrada!")
        sys.exit(1)
    
    result = urlparse(database_url)
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )
    return conn

def limpar_pre_separacoes_orfas():
    """Limpar pré-separações sem separacao_lote_id"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        print("🔍 Analisando pré-separações órfãs...")
        
        # 1. Contar quantas existem
        cur.execute("""
            SELECT COUNT(*) 
            FROM pre_separacao_item 
            WHERE separacao_lote_id IS NULL
        """)
        total_orfas = cur.fetchone()[0]
        
        if total_orfas == 0:
            print("✅ Nenhuma pré-separação órfã encontrada!")
            return
        
        print(f"\n⚠️  Encontradas {total_orfas} pré-separações sem separacao_lote_id")
        
        # 2. Mostrar alguns exemplos
        cur.execute("""
            SELECT id, num_pedido, cod_produto, data_criacao, criado_por
            FROM pre_separacao_item 
            WHERE separacao_lote_id IS NULL
            ORDER BY data_criacao DESC
            LIMIT 10
        """)
        
        print("\n📋 Exemplos (máximo 10):")
        print("-" * 80)
        print(f"{'ID':>6} | {'Pedido':^15} | {'Produto':^10} | {'Data Criação':^20} | {'Criado Por':^20}")
        print("-" * 80)
        
        for row in cur.fetchall():
            id_item, pedido, produto, data, usuario = row
            data_str = data.strftime('%d/%m/%Y %H:%M') if data else 'N/A'
            print(f"{id_item:>6} | {pedido:^15} | {produto:^10} | {data_str:^20} | {usuario or 'N/A':^20}")
        
        # 3. Confirmar antes de deletar
        print("\n" + "="*80)
        print(f"🗑️  ATENÇÃO: Isso irá DELETAR {total_orfas} pré-separações órfãs!")
        print("="*80)
        
        if os.environ.get('FORCE_DELETE') != '1':
            resposta = input("\n❓ Confirma a exclusão? (digite 'SIM' para confirmar): ")
            if resposta.upper() != 'SIM':
                print("❌ Operação cancelada!")
                return
        
        # 4. Fazer backup dos IDs antes de deletar
        print("\n📝 Salvando backup dos IDs deletados...")
        cur.execute("""
            SELECT id, num_pedido, cod_produto, data_criacao
            FROM pre_separacao_item 
            WHERE separacao_lote_id IS NULL
        """)
        
        backup_file = f"pre_separacoes_deletadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(backup_file, 'w') as f:
            f.write("IDs das pré-separações deletadas:\n")
            f.write("="*50 + "\n")
            for row in cur.fetchall():
                f.write(f"ID: {row[0]}, Pedido: {row[1]}, Produto: {row[2]}, Data: {row[3]}\n")
        
        print(f"✅ Backup salvo em: {backup_file}")
        
        # 5. Deletar as órfãs
        print("\n🗑️  Deletando pré-separações órfãs...")
        cur.execute("""
            DELETE FROM pre_separacao_item 
            WHERE separacao_lote_id IS NULL
        """)
        
        registros_deletados = cur.rowcount
        
        # 6. Confirmar a operação
        conn.commit()
        
        print(f"\n✅ SUCESSO! {registros_deletados} pré-separações órfãs foram deletadas!")
        
        # 7. Mostrar estatísticas finais
        cur.execute("SELECT COUNT(*) FROM pre_separacao_item")
        total_restante = cur.fetchone()[0]
        
        print(f"\n📊 Estatísticas finais:")
        print(f"   - Total antes: {total_orfas + total_restante}")
        print(f"   - Deletadas: {registros_deletados}")
        print(f"   - Total atual: {total_restante}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erro ao limpar pré-separações: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    print("🧹 LIMPEZA DE PRÉ-SEPARAÇÕES ÓRFÃS")
    print("=" * 50)
    print("Este script irá deletar pré-separações sem separacao_lote_id")
    print("=" * 50)
    
    try:
        limpar_pre_separacoes_orfas()
    except Exception as e:
        print(f"\n❌ Falha na limpeza: {e}")
        sys.exit(1) 