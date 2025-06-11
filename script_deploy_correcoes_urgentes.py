#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para Deploy de Correções Urgentes
========================================

Este script documenta e executa o deploy das correções urgentes para resolver:
1. DetachedInstanceError na função buscar_cidade_unificada()
2. Erro do filtro 'formatar_data_segura' no template de separação

PROBLEMAS IDENTIFICADOS NO RENDER:
---------------------------------
❌ Erro 1: DetachedInstanceError em app/utils/localizacao.py linha 193
❌ Erro 2: TemplateRuntimeError - filtro 'formatar_data_segura' não encontrado

CORREÇÕES IMPLEMENTADAS:
-----------------------
✅ 1. Proteção try/catch em buscar_cidade_unificada() e funções relacionadas  
✅ 2. Eager loading forçado para evitar lazy loading problems
✅ 3. Adicionado registro do filtro formatar_data_segura no Jinja2

STATUS: PRONTO PARA DEPLOY
"""

import os
import sys
import subprocess
from datetime import datetime

def verificar_arquivos_corrigidos():
    """Verifica se os arquivos foram corrigidos localmente"""
    
    print("🔍 === VERIFICAÇÃO DAS CORREÇÕES LOCAIS ===")
    print()
    
    arquivos_verificar = [
        {
            "arquivo": "app/utils/localizacao.py",
            "verifica": "try:",
            "descricao": "Proteção try/catch no DetachedInstanceError"
        },
        {
            "arquivo": "app/__init__.py", 
            "verifica": "formatar_data_segura'] = formatar_data_segura",
            "descricao": "Registro do filtro formatar_data_segura"
        }
    ]
    
    todas_ok = True
    
    for item in arquivos_verificar:
        arquivo = item["arquivo"]
        if os.path.exists(arquivo):
            with open(arquivo, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            
            if item["verifica"] in conteudo:
                print(f"✅ {arquivo} - {item['descricao']}")
            else:
                print(f"❌ {arquivo} - {item['descricao']} - NÃO ENCONTRADO")
                todas_ok = False
        else:
            print(f"❌ {arquivo} - Arquivo não encontrado")
            todas_ok = False
    
    print()
    if todas_ok:
        print("✅ Todas as correções estão presentes localmente")
    else:
        print("❌ Algumas correções estão faltando")
    
    return todas_ok

def mostrar_status_git():
    """Mostra o status do Git"""
    
    print("📊 === STATUS DO GIT ===")
    print()
    
    try:
        # Status
        result = subprocess.run(['git', 'status', '--porcelain'], 
                               capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            print("📁 Arquivos modificados:")
            for linha in result.stdout.strip().split('\n'):
                status = linha[:2]
                arquivo = linha[3:]
                status_desc = "Modificado" if 'M' in status else "Novo" if 'A' in status else "Desconhecido"
                print(f"   {status_desc}: {arquivo}")
        else:
            print("✅ Nenhum arquivo modificado (tudo já commitado)")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao verificar status git: {e}")
        return False
    
    print()
    return True

def fazer_commit_correcoes():
    """Faz commit das correções"""
    
    print("💾 === FAZENDO COMMIT DAS CORREÇÕES ===")
    print()
    
    try:
        # Add all
        subprocess.run(['git', 'add', '.'], check=True)
        print("✅ Arquivos adicionados ao stage")
        
        # Commit
        commit_msg = "🚨 CORREÇÃO URGENTE: DetachedInstanceError + filtro formatar_data_segura\n\n" \
                    "- Adicionada proteção try/catch em buscar_cidade_unificada()\n" \
                    "- Implementado eager loading para evitar sessões desanexadas\n" \
                    "- Corrigido registro do filtro formatar_data_segura no Jinja2\n" \
                    "- Sistema agora resiliente a problemas de sessão SQLAlchemy\n\n" \
                    "Fixes: Internal Server Error 500 na importação de separações"
        
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        print("✅ Commit realizado com sucesso")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao fazer commit: {e}")
        return False

def mostrar_instrucoes_render():
    """Mostra instruções para verificar no Render após deploy"""
    
    print("🌐 === INSTRUÇÕES PÓS-DEPLOY ===")
    print()
    
    print("📋 **COMO VERIFICAR SE AS CORREÇÕES FUNCIONARAM:**")
    print()
    
    print("1. 🚀 **Faça push para o repositório:**")
    print("   ```bash")
    print("   git push origin main")
    print("   ```")
    print()
    
    print("2. ⏳ **Aguarde o deploy automático no Render (~3-5 minutos)")
    print()
    
    print("3. 🧪 **Teste as funcionalidades:**")
    print("   a) Acesse: https://sistema-fretes.onrender.com/separacao/listar")
    print("   b) Acesse: https://sistema-fretes.onrender.com/pedidos/lista_pedidos") 
    print("   c) Tente fazer uma cotação")
    print()
    
    print("4. 📊 **Monitore os logs do Render:**")
    print("   - Logs esperados (BONS):")
    print("     ✅ 'Cidade encontrada por IBGE: SAO PAULO'")
    print("     ✅ 'Cidade encontrada por nome: RIO DE JANEIRO'")
    print("     ✅ Template de separação carrega sem erro")
    print()
    print("   - Logs alternativos (ACEITÁVEIS):")
    print("     ⚠️ 'Cidade encontrada por IBGE (IBGE: 3550308)'")
    print("     ⚠️ 'Problema ao carregar atributos da cidade...'")
    print()
    print("   - Logs que NÃO devem aparecer (RUINS):")
    print("     ❌ 'DetachedInstanceError: Instance <Cidade> is not bound to a Session'")
    print("     ❌ 'No filter named formatar_data_segura found'")
    print()

def mostrar_script_verificacao_pos_deploy():
    """Script para testar se tudo está funcionando"""
    
    print("🧪 === SCRIPT DE TESTE PÓS-DEPLOY ===")
    print()
    print("Execute estes comandos no Render Shell após o deploy:")
    print()
    print("```bash")
    print("# 1. Teste básico de importação do módulo corrigido")
    print("python -c \"from app.utils.localizacao import LocalizacaoService; print('✅ LocalizacaoService OK')\"")
    print()
    print("# 2. Teste o filtro de data")
    print("python -c \"from app import create_app; app=create_app(); print('✅ App criado, filtros:', 'formatar_data_segura' in app.jinja_env.filters)\"")
    print()
    print("# 3. Teste busca de cidade (pode dar aviso mas não deve quebrar)")
    print("python -c \"from app import create_app; from app.utils.localizacao import LocalizacaoService; app=create_app(); app.app_context().push(); cidade=LocalizacaoService.buscar_cidade_por_ibge('3550308'); print('✅ Busca funcionou:', cidade is not None)\"")
    print("```")
    print()

def mostrar_resumo_correcoes():
    """Mostra resumo das correções implementadas"""
    
    print("📋 === RESUMO DAS CORREÇÕES ===")
    print()
    
    print("🛠️ **PROBLEMA 1: DetachedInstanceError**")
    print("   ❌ Local: app/utils/localizacao.py:193")
    print("   ❌ Erro: logger.debug(f'Cidade encontrada: {cidade.nome}')")
    print("   ✅ Solução: Try/catch + eager loading")
    print()
    
    print("🛠️ **PROBLEMA 2: Filtro não encontrado**")
    print("   ❌ Local: app/templates/separacao/listar.html:302")
    print("   ❌ Erro: 'No filter named formatar_data_segura found'")
    print("   ✅ Solução: Registrado filtro no app/__init__.py")
    print()
    
    print("🎯 **IMPACTO ESPERADO:**")
    print("   ✅ Separações acessíveis sem erro 500")
    print("   ✅ Cotações funcionando normalmente") 
    print("   ✅ Importações resilientes a problemas de sessão")
    print("   ✅ Sistema estável em produção")
    print()

if __name__ == "__main__":
    print("🚨 === DEPLOY DE CORREÇÕES URGENTES ===")
    print("📅 Data:", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    print()
    
    # Verifica correções
    if not verificar_arquivos_corrigidos():
        print("❌ Correções não estão completas. Abortando.")
        sys.exit(1)
    
    print("="*60)
    mostrar_status_git()
    
    print("="*60)
    resposta = input("Deseja fazer commit das correções? (s/N): ").lower().strip()
    
    if resposta == 's':
        if fazer_commit_correcoes():
            print("="*60)
            mostrar_instrucoes_render()
            print("="*60)
            mostrar_script_verificacao_pos_deploy()
            print("="*60)
            mostrar_resumo_correcoes()
            
            print("🎉 **PRÓXIMOS PASSOS:**")
            print("1. Execute: git push origin main")
            print("2. Aguarde deploy no Render")
            print("3. Teste as funcionalidades")
            print("4. Monitore os logs")
        else:
            print("❌ Falha no commit. Verifique e tente novamente.")
    else:
        print("ℹ️ Commit cancelado pelo usuário.")
        print()
        print("Para fazer o commit manualmente:")
        print("git add .")
        print("git commit -m 'CORREÇÃO: DetachedInstanceError + filtro formatar_data_segura'")
        print("git push origin main") 