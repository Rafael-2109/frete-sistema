#!/usr/bin/env python3
"""
ANÁLISE SIMPLES DE PRÉ-SEPARAÇÕES EXISTENTES
Script básico para verificar dados atuais
"""

import os
import sys

def main():
    print("ANÁLISE DE PRÉ-SEPARAÇÕES EXISTENTES")
    print("=" * 50)
    
    # Verificar se há um ambiente virtual ativo
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("Ambiente virtual detectado")
    else:
        print("AVISO: Nenhum ambiente virtual detectado")
    
    # Verificar se o arquivo de models existe
    models_path = os.path.join(os.path.dirname(__file__), 'app', 'carteira', 'models.py')
    if os.path.exists(models_path):
        print("✓ Arquivo models.py encontrado")
    else:
        print("✗ Arquivo models.py não encontrado")
        return
    
    # Listar dependências necessárias
    print("\nDependências necessárias para análise completa:")
    dependencies = ['flask', 'flask-sqlalchemy', 'python-dotenv', 'psycopg2']
    
    for dep in dependencies:
        try:
            __import__(dep.replace('-', '_'))
            print(f"✓ {dep}")
        except ImportError:
            print(f"✗ {dep} - FALTANDO")
    
    print("\nPara executar análise completa:")
    print("1. Ativar ambiente virtual (se existir)")
    print("2. Instalar dependências: pip install -r requirements.txt")
    print("3. Executar: python analise_pre_separacoes_existentes.py")
    
    # Análise básica do arquivo models.py
    print("\nAnálise básica do arquivo models.py:")
    try:
        with open(models_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'class PreSeparacaoItem' in content:
            print("✓ Classe PreSeparacaoItem encontrada")
            
            # Verificar campos importantes
            if 'data_expedicao_editada' in content:
                print("✓ Campo data_expedicao_editada encontrado")
            else:
                print("✗ Campo data_expedicao_editada não encontrado")
                
            if 'data_agendamento_editada' in content:
                print("✓ Campo data_agendamento_editada encontrado")
            else:
                print("✗ Campo data_agendamento_editada não encontrado")
                
            if 'protocolo_editado' in content:
                print("✓ Campo protocolo_editado encontrado")
            else:
                print("✗ Campo protocolo_editado não encontrado")
        else:
            print("✗ Classe PreSeparacaoItem não encontrada")
            
    except Exception as e:
        print(f"Erro ao ler arquivo: {e}")

if __name__ == "__main__":
    main()