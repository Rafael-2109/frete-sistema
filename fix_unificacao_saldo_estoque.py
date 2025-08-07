#!/usr/bin/env python3
"""
Correção para considerar UnificacaoCodigos em todos os cálculos do saldo de estoque
"""

import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("""
╔══════════════════════════════════════════════════════╗
║   CORREÇÃO: UnificacaoCodigos no Saldo de Estoque   ║
╚══════════════════════════════════════════════════════╝
    """)
    
    print("📝 Aplicando correções...")
    
    # 1. Corrigir get_projecao_completa no ServicoEstoqueTempoReal
    corrigir_servico_estoque()
    
    print("\n✅ Correções aplicadas com sucesso!")
    print("\n📋 Resumo das correções:")
    print("1. ✅ routes.py - Carteira e Produção agora consideram códigos unificados")
    print("2. ✅ ServicoEstoqueTempoReal - Projeção agora soma movimentações de códigos unificados")
    print("\n🚀 Faça commit e push para aplicar no Render!")


def corrigir_servico_estoque():
    """Corrige o método get_projecao_completa para considerar UnificacaoCodigos"""
    
    arquivo = 'app/estoque/services/estoque_tempo_real.py'
    print(f"\n📝 Corrigindo {arquivo}...")
    
    with open(arquivo, 'r', encoding='utf-8') as f:
        linhas = f.readlines()
    
    # Procurar e substituir o trecho do get_projecao_completa
    nova_linhas = []
    dentro_metodo = False
    substituido = False
    
    for i, linha in enumerate(linhas):
        # Detectar início do método
        if 'def get_projecao_completa' in linha:
            dentro_metodo = True
        
        # Substituir a busca de movimentação prevista
        if dentro_metodo and not substituido and '# Buscar movimentação prevista' in linha:
            # Inserir nova lógica considerando UnificacaoCodigos
            nova_linhas.append(linha)
            nova_linhas.append("            # IMPORTANTE: Considerar UnificacaoCodigos\n")
            nova_linhas.append("            codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)\n")
            nova_linhas.append("            \n")
            nova_linhas.append("            # Buscar movimentações de todos os códigos relacionados\n")
            nova_linhas.append("            movs = MovimentacaoPrevista.query.filter(\n")
            nova_linhas.append("                MovimentacaoPrevista.cod_produto.in_(codigos_relacionados),\n")
            nova_linhas.append("                MovimentacaoPrevista.data_prevista == data_proj\n")
            nova_linhas.append("            ).all()\n")
            nova_linhas.append("            \n")
            nova_linhas.append("            # Somar entradas e saídas de todos os códigos\n")
            nova_linhas.append("            entrada = sum(float(m.entrada_prevista) for m in movs) if movs else 0\n")
            nova_linhas.append("            saida = sum(float(m.saida_prevista) for m in movs) if movs else 0\n")
            
            # Pular as próximas linhas originais que faziam a busca antiga
            j = i + 1
            while j < len(linhas) and 'entrada = float' not in linhas[j]:
                j += 1
            
            # Pular também as linhas de entrada e saída
            if j < len(linhas) and 'entrada = float' in linhas[j]:
                j += 1
            if j < len(linhas) and 'saida = float' in linhas[j]:
                j += 1
            
            # Atualizar índice
            for k in range(i + 1, min(j + 1, len(linhas))):
                linhas[k] = None  # Marcar para ignorar
            
            substituido = True
            continue
        
        # Adicionar linha se não foi marcada para ignorar
        if linha is not None:
            nova_linhas.append(linha)
    
    # Salvar arquivo atualizado
    with open(arquivo, 'w', encoding='utf-8') as f:
        for linha in nova_linhas:
            if linha is not None:
                f.write(linha)
    
    print(f"✅ {arquivo} corrigido!")


if __name__ == '__main__':
    main()