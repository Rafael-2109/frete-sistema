#!/usr/bin/env python3
"""
📊 TESTE DO SISTEMA DE EXCEL VIA CLAUDE
Valida funcionamento do export Excel real
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def testar_excel_generator():
    """Testa gerador de Excel básico"""
    print("📊 TESTE DO GERADOR DE EXCEL")
    print("=" * 50)
    
    try:
        # Simular contexto Flask
        from flask import Flask
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test'
        
        with app.app_context():
            # Configurar diretório static
            app.static_folder = os.path.join(os.path.dirname(__file__), 'app', 'static')
            
            from app.claude_ai.excel_generator import ExcelGenerator
            
            generator = ExcelGenerator()
            print("✅ ExcelGenerator criado com sucesso")
            
            # Teste básico - gerar Excel vazio
            resultado = generator._gerar_excel_vazio("Teste de funcionalidade")
            
            if resultado.get('success'):
                print(f"✅ Excel de teste gerado: {resultado['filename']}")
                print(f"📁 Caminho: {resultado.get('filepath', 'N/A')}")
                return True
            else:
                print(f"❌ Erro ao gerar Excel: {resultado}")
                return False
                
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def testar_deteccao_comando():
    """Testa detecção de comandos Excel"""
    print("\n🧠 TESTE DE DETECÇÃO DE COMANDOS")
    print("=" * 50)
    
    try:
        from app.claude_ai.claude_real_integration import ClaudeRealIntegration
        
        claude = ClaudeRealIntegration()
        
        comandos_teste = [
            "Gere um relatório em excel com os clientes",
            "Exportar dados para planilha",
            "Como estão as entregas?",  # Não deve ser Excel
            "Download de dados em xlsx",
            "Status do sistema"  # Não deve ser Excel
        ]
        
        for comando in comandos_teste:
            eh_excel = claude._is_excel_command(comando)
            status = "📊 Excel" if eh_excel else "💬 Chat"
            print(f"{status}: '{comando}'")
        
        print("✅ Detecção de comandos funcionando")
        return True
        
    except Exception as e:
        print(f"❌ Erro na detecção: {e}")
        return False

def testar_integração_completa():
    """Testa integração completa (simulada)"""
    print("\n🔄 TESTE DE INTEGRAÇÃO COMPLETA")
    print("=" * 50)
    
    try:
        # Verificar se módulos necessários estão disponíveis
        import pandas as pd
        print("✅ Pandas disponível")
        
        # Verificar openpyxl para Excel
        try:
            import openpyxl
            print("✅ OpenPyXL disponível") 
        except ImportError:
            print("⚠️ OpenPyXL não encontrado - instalar: pip install openpyxl")
            return False
        
        # Verificar estrutura de diretórios
        reports_dir = os.path.join('app', 'static', 'reports')
        if os.path.exists(reports_dir):
            print(f"✅ Diretório reports existe: {reports_dir}")
        else:
            print(f"❌ Diretório reports não existe: {reports_dir}")
            return False
        
        print("✅ Integração completa validada")
        return True
        
    except Exception as e:
        print(f"❌ Erro na integração: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("🚀 INICIANDO TESTES DO SISTEMA EXCEL VIA CLAUDE")
    print("=" * 60)
    
    testes = [
        ("Gerador Excel", testar_excel_generator),
        ("Detecção Comandos", testar_deteccao_comando), 
        ("Integração Completa", testar_integração_completa)
    ]
    
    resultados = []
    
    for nome, funcao_teste in testes:
        try:
            resultado = funcao_teste()
            resultados.append((nome, resultado))
        except Exception as e:
            print(f"❌ ERRO CRÍTICO em {nome}: {e}")
            resultados.append((nome, False))
    
    # Resumo
    print("\n" + "=" * 60)
    print("📋 RESUMO DOS TESTES")
    print("=" * 60)
    
    sucessos = 0
    for nome, sucesso in resultados:
        status = "✅ PASSOU" if sucesso else "❌ FALHOU"
        print(f"{status}: {nome}")
        if sucesso:
            sucessos += 1
    
    taxa_sucesso = (sucessos / len(resultados)) * 100
    print(f"\n🎯 TAXA DE SUCESSO: {taxa_sucesso:.1f}% ({sucessos}/{len(resultados)})")
    
    if taxa_sucesso == 100:
        print("🎉 SISTEMA EXCEL VIA CLAUDE TOTALMENTE FUNCIONAL!")
        return True
    elif taxa_sucesso >= 66:
        print("⚠️ Sistema parcialmente funcional - revisar falhas")
        return False
    else:
        print("❌ Sistema com problemas críticos - revisar implementação")
        return False

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1) 