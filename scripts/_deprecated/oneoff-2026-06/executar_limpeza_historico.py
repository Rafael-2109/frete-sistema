#!/usr/bin/env python3
"""
Script para LIMPAR COMPLETAMENTE a tabela HistoricoPedidos
Data: 25/08/2025
"""

from app import create_app, db
from app.manufatura.models import HistoricoPedidos
from sqlalchemy import text
from datetime import datetime

def limpar_historico_completo():
    """Limpa TODOS os registros de HistoricoPedidos"""
    
    print("\n" + "="*80)
    print("🚨 LIMPEZA COMPLETA DA TABELA HISTORICO_PEDIDOS")
    print("="*80)
    
    # Contar registros atuais
    count_antes = HistoricoPedidos.query.count()
    print(f"\n📊 Registros atuais na tabela: {count_antes}")
    
    if count_antes > 0:
        # Mostrar alguns exemplos que serão apagados
        print("\n📋 Exemplos de registros que serão APAGADOS:")
        exemplos = HistoricoPedidos.query.limit(5).all()
        for ex in exemplos:
            print(f"  - Pedido: {ex.num_pedido}, Produto: {ex.cod_produto} ({ex.nome_produto})")
    
    print("\n⚠️  INICIANDO LIMPEZA COMPLETA...")
    
    try:
        # Usar SQL direto para garantir limpeza completa
        db.session.execute(text("DELETE FROM historico_pedidos"))
        
        # Resetar a sequência do ID
        db.session.execute(text("ALTER SEQUENCE historico_pedidos_id_seq RESTART WITH 1"))
        
        # Commit das mudanças
        db.session.commit()
        
        # Verificar que está vazio
        count_depois = HistoricoPedidos.query.count()
        
        print("\n✅ LIMPEZA CONCLUÍDA COM SUCESSO!")
        print(f"   - Registros antes: {count_antes}")
        print(f"   - Registros depois: {count_depois}")
        print(f"   - Registros removidos: {count_antes}")
        print("   - Sequência de ID resetada para 1")
        
        # Verificar sequência
        result = db.session.execute(text("SELECT last_value FROM historico_pedidos_id_seq"))
        seq_value = result.scalar()
        print(f"   - Próximo ID será: {seq_value if seq_value else 1}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO na limpeza: {e}")
        db.session.rollback()
        return False

def main():
    app = create_app()
    
    with app.app_context():
        print("\n🔄 Conectando ao banco de dados...")
        
        # Executar limpeza
        sucesso = limpar_historico_completo()
        
        if sucesso:
            print("\n" + "="*80)
            print("🎯 TABELA HISTORICO_PEDIDOS LIMPA E PRONTA PARA REIMPORTAÇÃO")
            print("="*80)
            print("\n📌 Próximos passos:")
            print("   1. Execute a importação corrigida com o mapeamento usando default_code")
            print("   2. O campo cod_produto agora terá os códigos corretos (ex: 4759699)")
            print("   3. A previsão de demanda funcionará corretamente")
        else:
            print("\n❌ Falha na limpeza. Verifique os erros acima.")

if __name__ == "__main__":
    main()