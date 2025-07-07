#!/usr/bin/env python3
"""
Script para atualizar as rotas do Claude AI para usar a interface de transição
"""

import re

def atualizar_arquivo():
    arquivo_path = "app/claude_ai/routes.py"
    
    try:
        # Ler arquivo
        with open(arquivo_path, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Fazer substituições
        # 1. Substituir todas as chamadas restantes
        conteudo = conteudo.replace(
            'resposta = processar_com_claude_real(consulta, user_context)',
            'resposta = processar_consulta_transicao(consulta, user_context)'
        )
        
        # 2. Substituir a linha do relatório
        conteudo = conteudo.replace(
            'relatorio = processar_com_claude_real(consulta_relatorio)',
            'relatorio = processar_consulta_transicao(consulta_relatorio)'
        )
        
        # 3. Substituir qualquer resultado restante
        conteudo = conteudo.replace(
            'resultado = processar_com_claude_real(consulta, user_context)',
            'resultado = processar_consulta_transicao(consulta, user_context)'
        )
        
        # 4. Remover imports desnecessários do sistema antigo
        conteudo = re.sub(
            r'from \.claude_real_integration import processar_com_claude_real\n?',
            '',
            conteudo
        )
        
        # Salvar arquivo atualizado
        with open(arquivo_path, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        print("✅ Arquivo atualizado com sucesso!")
        print("✅ Todas as chamadas agora usam a interface de transição")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    atualizar_arquivo() 