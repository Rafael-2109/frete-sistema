#!/usr/bin/env python3
"""
Script para atualizar formatação JavaScript nos templates MotoChefe
Adiciona função formatarValorBR() e substitui toFixed() por ela
Data: 2025-01-10
"""

import os
import re
from pathlib import Path

# Diretório base dos templates motochefe
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / 'app' / 'templates' / 'motochefe'

# Função helper JavaScript para adicionar nos arquivos
HELPER_FUNCTION = """
// Função helper para formatar valores monetários no padrão brasileiro
function formatarValorBR(valor, decimais = 2) {
    if (valor === null || valor === undefined) return '0,00';
    const numero = parseFloat(valor);
    if (isNaN(numero)) return '0,00';

    // Formatar com decimais e substituir separadores
    return numero.toFixed(decimais)
        .replace(/\\d(?=(\\d{3})+\\.)/g, '$&.')  // Adiciona ponto a cada 3 dígitos
        .replace('.', ',');  // Troca ponto por vírgula no decimal
}
"""

def processar_arquivo(caminho):
    """Processa um arquivo HTML adicionando helper e substituindo toFixed"""
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            conteudo = f.read()

        modificado = False

        # Verificar se já tem a função helper
        if 'function formatarValorBR' not in conteudo:
            # Encontrar o primeiro <script> e adicionar antes dele
            # OU adicionar antes do </script> se houver script inline
            if '<script>' in conteudo:
                conteudo = conteudo.replace(
                    '<script>',
                    '<script>' + HELPER_FUNCTION,
                    1
                )
                modificado = True

        # Substituir padrões de toFixed() por formatarValorBR()
        # Padrão 1: .toFixed(2).replace('.', ',')  →  formatarValorBR(valor)
        conteudo_novo = re.sub(
            r'([a-zA-Z_][\w.]*?)\.toFixed\(2\)\.replace\([\'"]\.[\'"]\s*,\s*[\'"],[\'"]\)',
            r'formatarValorBR(\1)',
            conteudo
        )

        # Padrão 2: toFixed(2) em contextos de exibição de valores monetários
        # ATENÇÃO: Só substituir quando há "R$" próximo ou contexto de valor
        # Mantém toFixed em cálculos (valor.toFixed(2) em value=)

        # Substituir em template strings com R$
        conteudo_novo = re.sub(
            r'R\$\s*\$\{([^}]+?)\.toFixed\(2\)\}',
            r'R$ ${formatarValorBR(\1)}',
            conteudo_novo
        )

        if conteudo_novo != conteudo:
            modificado = True
            conteudo = conteudo_novo

        if modificado:
            with open(caminho, 'w', encoding='utf-8') as f:
                f.write(conteudo)
            return True

        return False

    except Exception as e:
        print(f"❌ Erro ao processar {caminho}: {e}")
        return False

def main():
    """Função principal"""
    print("🔧 Iniciando atualização de JavaScript...\n")

    arquivos_processados = 0

    # Arquivos que têm toFixed() segundo o grep
    arquivos_alvo = [
        'titulos_a_pagar/listar.html',
        'financeiro/contas_a_receber.html',
        'financeiro/contas_a_pagar.html',
        'vendas/pedidos/detalhes.html',
        'vendas/pedidos/form.html',
    ]

    for arquivo_relativo in arquivos_alvo:
        arquivo = TEMPLATES_DIR / arquivo_relativo
        if arquivo.exists():
            if processar_arquivo(arquivo):
                arquivos_processados += 1
                print(f"✅ {arquivo_relativo}")
        else:
            print(f"⚠️  Arquivo não encontrado: {arquivo_relativo}")

    print(f"\n📊 RESUMO:")
    print(f"   Arquivos modificados: {arquivos_processados}")
    print(f"\n✅ Processo concluído!")

if __name__ == '__main__':
    main()
