#!/usr/bin/env python3
"""
CORREÇÃO ESPECÍFICA DAS CAUSAS RAIZ
Script focado nos 3 problemas exatos identificados
"""

import os
import shutil
from datetime import datetime

def corrigir_multi_agent_concatenacao():
    """Corrige o erro NoneType + str no multi_agent_system.py"""
    print("1. Corrigindo Multi-Agent System - erro de concatenação...")
    
    arquivo = "app/claude_ai/multi_agent_system.py"
    
    # Backup
    shutil.copy2(arquivo, f"{arquivo}.backup_concatenacao")
    
    # Ler arquivo
    with open(arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Localizar e corrigir a linha problemática (591-594)
    linha_problema = """        # Proteção absoluta contra None
        main_response = main_response or "Resposta não disponível"
        convergence_note = convergence_note or ""
        validation_note = validation_note or ""
        
        final_response = str(main_response) + str(convergence_note) + str(validation_note)"""
    
    linha_corrigida = """        # Proteção ABSOLUTA contra None - verificação tripla
        if main_response is None:
            main_response = "Resposta não disponível"
        if convergence_note is None:
            convergence_note = ""
        if validation_note is None:
            validation_note = ""
        
        # Conversão explícita para string com fallback
        try:
            final_response = str(main_response) + str(convergence_note) + str(validation_note)
        except (TypeError, AttributeError) as e:
            final_response = "Erro na concatenação de resposta: " + str(e)"""
    
    # Aplicar correção
    if linha_problema in conteudo:
        conteudo = conteudo.replace(linha_problema, linha_corrigida)
        
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        print("   ✅ Multi-Agent System corrigido")
        return True
    else:
        print("   ⚠️ Linha problema não encontrada no Multi-Agent System")
        return False

def corrigir_sqlalchemy_imports():
    """Corrige os imports SQLAlchemy nos arquivos de IA"""
    print("2. Corrigindo imports SQLAlchemy...")
    
    arquivos_ia = [
        "app/claude_ai/lifelong_learning.py",
        "app/claude_ai/advanced_integration.py"
    ]
    
    corrigidos = 0
    
    for arquivo in arquivos_ia:
        if not os.path.exists(arquivo):
            continue
            
        # Backup
        shutil.copy2(arquivo, f"{arquivo}.backup_sqlalchemy")
        
        # Ler arquivo
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Substituir imports problemáticos
        mudancas = [
            # Trocar import direto do db por import com contexto
            ("from app import db", "from flask import current_app"),
            
            # Adicionar função helper para SQLAlchemy
            ("from sqlalchemy import text, func", 
             "from sqlalchemy import text, func\nfrom flask_sqlalchemy import SQLAlchemy"),
            
            # Substituir uso direto do db por função segura
            ("db.session.execute(", "_get_db_session().execute("),
            ("db.session.commit()", "_get_db_session().commit()"),
            ("db.session.rollback()", "_get_db_session().rollback()"),
        ]
        
        conteudo_original = conteudo
        
        for antigo, novo in mudancas:
            if antigo in conteudo:
                conteudo = conteudo.replace(antigo, novo)
        
        # Adicionar função helper no início do arquivo (após imports)
        if "_get_db_session" not in conteudo and conteudo != conteudo_original:
            helper_function = '''
def _get_db_session():
    """Função helper para obter sessão SQLAlchemy com contexto Flask"""
    try:
        from app import db
        return db.session
    except RuntimeError:
        # Se não há contexto Flask, criar um
        from app import create_app
        app = create_app()
        with app.app_context():
            from app import db
            return db.session
'''
            
            # Inserir após os imports
            linhas = conteudo.split('\n')
            linha_insert = 0
            for i, linha in enumerate(linhas):
                if linha.startswith('logger = ') or linha.startswith('class '):
                    linha_insert = i
                    break
            
            linhas.insert(linha_insert, helper_function)
            conteudo = '\n'.join(linhas)
        
        # Salvar se houve mudanças
        if conteudo != conteudo_original:
            with open(arquivo, 'w', encoding='utf-8') as f:
                f.write(conteudo)
            corrigidos += 1
            print(f"   ✅ {arquivo} corrigido")
    
    print(f"   ✅ {corrigidos} arquivos SQLAlchemy corrigidos")
    return corrigidos > 0

def corrigir_encoding_utf8():
    """Corrige configurações de encoding UTF-8"""
    print("3. Corrigindo configurações UTF-8...")
    
    arquivo_config = "config.py"
    
    # Backup
    shutil.copy2(arquivo_config, f"{arquivo_config}.backup_utf8")
    
    # Ler arquivo
    with open(arquivo_config, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Localizar e substituir configurações de encoding
    config_antiga = '''                'client_encoding': 'utf8',  # Encoding UTF-8 explícito
                'options': '-c client_encoding=UTF8'  # Força UTF-8 no PostgreSQL'''
    
    config_nova = '''                'client_encoding': 'utf8',  # Encoding UTF-8 explícito
                'options': '-c client_encoding=UTF8 -c timezone=UTC'  # Força UTF-8 + UTC no PostgreSQL'''
    
    if config_antiga in conteudo:
        conteudo = conteudo.replace(config_antiga, config_nova)
        
        with open(arquivo_config, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        print("   ✅ Configurações UTF-8 corrigidas")
        return True
    else:
        print("   ⚠️ Configurações UTF-8 não encontradas")
        return False

def main():
    """Executa todas as correções específicas"""
    print("🎯 CORREÇÃO ESPECÍFICA DAS CAUSAS RAIZ")
    print("=" * 50)
    
    resultados = []
    
    # Executar correções
    resultados.append(corrigir_multi_agent_concatenacao())
    resultados.append(corrigir_sqlalchemy_imports()) 
    resultados.append(corrigir_encoding_utf8())
    
    # Relatório final
    print("\n" + "=" * 50)
    print("📊 RELATÓRIO DE CORREÇÕES:")
    
    sucessos = sum(resultados)
    total = len(resultados)
    
    if sucessos == total:
        print(f"✅ TODAS as {total} correções aplicadas com sucesso!")
        print("\n🚀 PRÓXIMOS PASSOS:")
        print("1. Fazer commit: git add . && git commit -m 'fix: Causa raiz corrigida'")
        print("2. Fazer push: git push")
        print("3. Aguardar deploy no Render")
    else:
        print(f"⚠️ {sucessos}/{total} correções aplicadas")
        print("Verificar logs acima para detalhes")

if __name__ == "__main__":
    main() 