#!/usr/bin/env python3
"""
Teste manual do gerador Excel
"""

import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from app import create_app
from app.claude_ai.excel_generator import get_excel_generator

def testar_excel():
    """Testa a geração de Excel diretamente"""
    print("🧪 Iniciando teste do gerador Excel...")
    
    # Criar contexto Flask
    app = create_app()
    
    with app.app_context():
        try:
            print("📊 Obtendo gerador Excel...")
            excel_generator = get_excel_generator()
            
            print("🎯 Testando geração de entregas pendentes...")
            resultado = excel_generator.gerar_relatorio_entregas_pendentes()
            
            print(f"✅ Resultado: {resultado}")
            
            if resultado.get('success'):
                print(f"📄 Arquivo gerado: {resultado['filename']}")
                print(f"📂 Caminho: {resultado.get('filepath', 'N/A')}")
                print(f"🔗 URL: {resultado['file_url']}")
                print(f"📈 Registros: {resultado['total_registros']}")
                
                # Verificar se arquivo existe (apenas se filepath estiver disponível)
                filepath = resultado.get('filepath')
                if filepath and os.path.exists(filepath):
                    tamanho = os.path.getsize(filepath)
                    print(f"✅ Arquivo confirmado no disco: {tamanho} bytes")
                    
                    if resultado['total_registros'] == 0:
                        print("ℹ️ Arquivo vazio (sem dados) - isso é esperado se não há entregas pendentes")
                    else:
                        print(f"📊 Arquivo com dados reais: {resultado['total_registros']} registros")
                        
                elif filepath:
                    print(f"❌ Arquivo NÃO encontrado no disco: {filepath}")
                else:
                    print("⚠️ Caminho do arquivo não fornecido")
                    
                # Mostrar estatísticas se disponíveis
                if 'estatisticas' in resultado:
                    stats = resultado['estatisticas']
                    print(f"📊 Estatísticas: {stats}")
                    
            else:
                print(f"❌ Erro na geração: {resultado.get('error', 'Erro desconhecido')}")
                
            # Testar se há dados no banco
            print("\n🔍 Verificando dados no banco...")
            from app import db
            from app.monitoramento.models import EntregaMonitorada
            from app.pedidos.models import Pedido
            
            entregas_pendentes = db.session.query(EntregaMonitorada).filter(
                EntregaMonitorada.entregue == False
            ).count()
            
            pedidos_agendados = db.session.query(Pedido).filter(
                Pedido.agendamento.isnot(None),
                Pedido.nf.is_(None)
            ).count()
            
            print(f"📊 Entregas monitoradas pendentes: {entregas_pendentes}")
            print(f"📋 Pedidos agendados não faturados: {pedidos_agendados}")
            print(f"🎯 Total de dados disponíveis: {entregas_pendentes + pedidos_agendados}")
            
            if entregas_pendentes == 0 and pedidos_agendados == 0:
                print("ℹ️ Como não há dados, o sistema gerou um arquivo vazio (comportamento correto)")
            else:
                print("✅ Há dados disponíveis - arquivo deveria ter conteúdo")
                
        except Exception as e:
            print(f"❌ Erro crítico: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    testar_excel() 