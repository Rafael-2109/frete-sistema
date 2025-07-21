#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANÁLISE BÁSICA DE PRÉ-SEPARAÇÕES
Script simples para verificar estrutura atual
"""

import os
import sys

def main():
    print("ANALISE DE PRE-SEPARACOES EXISTENTES")
    print("=" * 50)
    
    # Verificar se o arquivo de models existe
    models_path = os.path.join(os.path.dirname(__file__), 'app', 'carteira', 'models.py')
    if os.path.exists(models_path):
        print("OK - Arquivo models.py encontrado")
    else:
        print("ERRO - Arquivo models.py nao encontrado")
        return
    
    # Análise do arquivo models.py
    print("\nAnalise do arquivo models.py:")
    try:
        with open(models_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'class PreSeparacaoItem' in content:
            print("OK - Classe PreSeparacaoItem encontrada")
            
            # Verificar campos importantes
            campos_importantes = [
                'data_expedicao_editada',
                'data_agendamento_editada', 
                'protocolo_editado',
                'num_pedido',
                'cod_produto',
                'status'
            ]
            
            print("\nCampos verificados:")
            for campo in campos_importantes:
                if campo in content:
                    print(f"OK - {campo}")
                else:
                    print(f"FALTANDO - {campo}")
                    
            # Verificar se há constraint única atual
            if '__table_args__' in content and 'unique' in content.lower():
                print("\nOK - Constraint unica detectada no modelo")
            else:
                print("\nINFO - Nenhuma constraint unica detectada")
                
        else:
            print("ERRO - Classe PreSeparacaoItem nao encontrada")
            
    except Exception as e:
        print(f"Erro ao ler arquivo: {e}")
    
    print("\nCONCLUSAO:")
    print("- Para analise completa da base de dados, e necessario:")
    print("  1. Ambiente Python configurado com Flask")
    print("  2. Acesso ao banco de dados")
    print("  3. Variaveis de ambiente configuradas")
    
    print("\n- Estrutura do modelo PreSeparacaoItem parece estar presente")
    print("- Proximos passos: configurar ambiente e executar analise completa")

if __name__ == "__main__":
    main()