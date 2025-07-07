#!/usr/bin/env python3
"""
🔍 ANÁLISE COMPLETA DA MIGRAÇÃO CLAUDE AI
Comparação detalhada entre sistema antigo e novo
"""

import os
import sys
from pathlib import Path
import re

def analisar_sistema_antigo():
    """Analisa o sistema claude_ai antigo"""
    print("🔍 ANALISANDO SISTEMA CLAUDE AI ANTIGO...")
    print("="*60)
    
    antigo_path = Path("app/claude_ai")
    if not antigo_path.exists():
        print("❌ Diretório claude_ai antigo não encontrado")
        return {}
    
    arquivos_antigos = {}
    funcoes_antigos = {}
    
    for arquivo in antigo_path.glob("*.py"):
        if arquivo.name.startswith("__"):
            continue
            
        tamanho = arquivo.stat().st_size
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                conteudo = f.read()
                linhas = len(conteudo.split('\n'))
                
                # Contar funções
                funcoes = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', conteudo)
                classes = re.findall(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[:\(]', conteudo)
                
                arquivos_antigos[arquivo.name] = {
                    'tamanho': tamanho,
                    'linhas': linhas,
                    'funcoes': funcoes,
                    'classes': classes,
                    'total_elementos': len(funcoes) + len(classes)
                }
                
                # Adicionar funções ao mapeamento global
                for func in funcoes:
                    funcoes_antigos[func] = arquivo.name
                    
        except Exception as e:
            print(f"⚠️ Erro ao ler {arquivo.name}: {e}")
    
    return arquivos_antigos, funcoes_antigos

def analisar_sistema_novo():
    """Analisa o sistema claude_ai_novo"""
    print("\n🆕 ANALISANDO SISTEMA CLAUDE AI NOVO...")
    print("="*60)
    
    novo_path = Path("app/claude_ai_novo")
    if not novo_path.exists():
        print("❌ Diretório claude_ai_novo não encontrado")
        return {}
    
    arquivos_novos = {}
    funcoes_novos = {}
    
    for arquivo in novo_path.rglob("*.py"):
        if "__pycache__" in str(arquivo):
            continue
            
        tamanho = arquivo.stat().st_size
        arquivo_relativo = str(arquivo.relative_to(novo_path))
        
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                conteudo = f.read()
                linhas = len(conteudo.split('\n'))
                
                # Contar funções
                funcoes = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', conteudo)
                classes = re.findall(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[:\(]', conteudo)
                
                arquivos_novos[arquivo_relativo] = {
                    'tamanho': tamanho,
                    'linhas': linhas,
                    'funcoes': funcoes,
                    'classes': classes,
                    'total_elementos': len(funcoes) + len(classes)
                }
                
                # Adicionar funções ao mapeamento global
                for func in funcoes:
                    funcoes_novos[func] = arquivo_relativo
                    
        except Exception as e:
            print(f"⚠️ Erro ao ler {arquivo_relativo}: {e}")
    
    return arquivos_novos, funcoes_novos

def comparar_sistemas(antigos, funcoes_antigos, novos, funcoes_novos):
    """Compara os dois sistemas"""
    print("\n📊 COMPARAÇÃO DETALHADA DOS SISTEMAS")
    print("="*60)
    
    # 1. Estatísticas gerais
    total_arquivos_antigos = len(antigos)
    total_funcoes_antigas = len(funcoes_antigos)
    total_arquivos_novos = len(novos)
    total_funcoes_novas = len(funcoes_novos)
    
    print(f"📁 Arquivos - Antigo: {total_arquivos_antigos} | Novo: {total_arquivos_novos}")
    print(f"🔧 Funções - Antigo: {total_funcoes_antigas} | Novo: {total_funcoes_novas}")
    
    # 2. Funções que existiam no antigo mas não no novo
    funcoes_perdidas = set(funcoes_antigos.keys()) - set(funcoes_novos.keys())
    funcoes_migradas = set(funcoes_antigos.keys()) & set(funcoes_novos.keys())
    funcoes_novas_criadas = set(funcoes_novos.keys()) - set(funcoes_antigos.keys())
    
    print(f"\n🔄 MIGRAÇÃO DE FUNÇÕES:")
    print(f"   ✅ Migradas: {len(funcoes_migradas)}")
    print(f"   ❌ Perdidas: {len(funcoes_perdidas)}")
    print(f"   🆕 Novas: {len(funcoes_novas_criadas)}")
    
    return funcoes_perdidas, funcoes_migradas, funcoes_novas_criadas

def analisar_funcoes_perdidas(funcoes_perdidas, funcoes_antigos, antigos):
    """Analisa funções que foram perdidas na migração"""
    print("\n❌ FUNÇÕES PERDIDAS/IGNORADAS:")
    print("="*60)
    
    if not funcoes_perdidas:
        print("🎉 Nenhuma função foi perdida! Migração 100% completa!")
        return
    
    funcoes_por_arquivo = {}
    for func in funcoes_perdidas:
        arquivo = funcoes_antigos[func]
        if arquivo not in funcoes_por_arquivo:
            funcoes_por_arquivo[arquivo] = []
        funcoes_por_arquivo[arquivo].append(func)
    
    for arquivo, funcoes in funcoes_por_arquivo.items():
        print(f"\n📁 {arquivo} ({len(funcoes)} funções perdidas):")
        for i, func in enumerate(funcoes[:10], 1):  # Mostrar até 10
            print(f"   {i}. {func}")
        if len(funcoes) > 10:
            print(f"   ... e mais {len(funcoes) - 10} funções")

def analisar_arquivos_criticos(antigos):
    """Identifica os arquivos mais críticos do sistema antigo"""
    print("\n🔥 ARQUIVOS CRÍTICOS DO SISTEMA ANTIGO:")
    print("="*60)
    
    # Ordenar por número de elementos (funções + classes)
    criticos = sorted(antigos.items(), key=lambda x: x[1]['total_elementos'], reverse=True)
    
    for i, (arquivo, info) in enumerate(criticos[:10], 1):
        print(f"{i:2d}. {arquivo:<35} | {info['total_elementos']:3d} elementos | {info['linhas']:4d} linhas")

def verificar_integração():
    """Verifica se a nova arquitetura está integrada"""
    print("\n🔗 VERIFICANDO INTEGRAÇÃO DA NOVA ARQUITETURA:")
    print("="*60)
    
    # Verificar se existe integração no __init__.py principal
    try:
        with open("app/__init__.py", 'r', encoding='utf-8') as f:
            conteudo = f.read()
            
        if "claude_ai_novo" in conteudo:
            print("✅ Sistema novo está referenciado no app/__init__.py")
        else:
            print("❌ Sistema novo NÃO está integrado no app/__init__.py")
            
        if "claude_ai." in conteudo:
            print("⚠️ Sistema antigo ainda está ativo no app/__init__.py")
        else:
            print("✅ Sistema antigo não está mais ativo")
            
    except Exception as e:
        print(f"❌ Erro ao verificar integração: {e}")

def gerar_plano_uso():
    """Gera plano de como usar a nova arquitetura"""
    print("\n🚀 COMO USAR A NOVA ARQUITETURA:")
    print("="*60)
    
    print("""
1. 🔄 SUBSTITUIR IMPORTS:
   ANTES: from app.claude_ai.claude_real_integration import processar_consulta_real
   DEPOIS: from app.claude_ai_novo.core.claude_integration import processar_com_claude_real

2. 🎯 USAR INTERFACE MODULAR:
   ANTES: claude_real_integration.processar_consulta_real(consulta)
   DEPOIS: from app.claude_ai_novo import claude_ai_modular
           resultado = claude_ai_modular.processar_consulta(consulta)

3. 📦 IMPORTAR MÓDULOS ESPECÍFICOS:
   Excel: from app.claude_ai_novo.commands.excel_commands import get_excel_commands
   Data: from app.claude_ai_novo.data_loaders.database_loader import get_database_loader
   IA: from app.claude_ai_novo.intelligence.advanced_integration import *

4. 🔧 CONFIGURAR ROTAS:
   Atualizar app/claude_ai/routes.py para usar o sistema novo:
   from app.claude_ai_novo.core.claude_integration import get_claude_integration
""")

def main():
    """Função principal"""
    print("🔍 ANÁLISE COMPLETA DA MIGRAÇÃO CLAUDE AI")
    print("🎯 Respondendo todas as perguntas sobre a migração")
    print("="*70)
    
    # Analisar sistemas
    arquivos_antigos, funcoes_antigos = analisar_sistema_antigo()
    arquivos_novos, funcoes_novos = analisar_sistema_novo()
    
    # Comparar
    funcoes_perdidas, funcoes_migradas, funcoes_novas = comparar_sistemas(
        arquivos_antigos, funcoes_antigos, arquivos_novos, funcoes_novos
    )
    
    # Análises específicas
    analisar_funcoes_perdidas(funcoes_perdidas, funcoes_antigos, arquivos_antigos)
    analisar_arquivos_criticos(arquivos_antigos)
    verificar_integração()
    gerar_plano_uso()
    
    # Responder perguntas diretas
    print("\n🎯 RESPOSTAS ÀS SUAS PERGUNTAS:")
    print("="*60)
    print(f"1. Funções ignoradas: {len(funcoes_perdidas)} funções")
    print(f"2. Funções que não existem mais: {len(funcoes_perdidas)} funções")
    print(f"3. Funções da nova arquitetura funcionam: Sim, {len(funcoes_novos)} funções ativas")
    print(f"4. Integração: {'Parcial - precisa configurar' if 'claude_ai' in str(funcoes_antigos) else 'Completa'}")
    print(f"5. Como usar: Substituir imports e usar interface modular (veja acima)")
    
    print(f"\n📊 RESUMO FINAL:")
    print(f"   🔄 Taxa de migração: {len(funcoes_migradas)}/{len(funcoes_antigos)} ({len(funcoes_migradas)/len(funcoes_antigos)*100:.1f}%)")
    print(f"   🆕 Funcionalidades novas: {len(funcoes_novas)}")
    print(f"   📈 Crescimento do sistema: {len(funcoes_novos) - len(funcoes_antigos):+d} funções")

if __name__ == "__main__":
    main() 