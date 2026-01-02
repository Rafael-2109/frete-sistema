#!/usr/bin/env python3
"""
Script de Teste: Haiku com Liberdade Total

Objetivo: Testar se o problema de resolucao de produtos e "excesso de determinismo"
ao pre-filtrar candidatos antes de enviar ao Haiku.

Abordagem: Enviar TODOS os produtos vendidos ao Haiku e deixar ele decidir.

Caso de teste:
- Descricao: "AZEITONA VDE C CAR CAMPO BELO BD 2kg"
- Codigo Cliente: 964348
- Cliente: Tenda Atacado (prefixo CNPJ 01157555)
"""

import sys
import os

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from anthropic import Anthropic
from app import create_app
from app.producao.models import CadastroPalletizacao


def buscar_todos_produtos_vendidos():
    """Busca TODOS os produtos vendidos sem nenhum filtro adicional"""

    produtos = CadastroPalletizacao.query.filter_by(
        produto_vendido=True,
        ativo=True
    ).all()

    # Formatar para enviar ao Haiku
    lista_produtos = []
    for p in produtos:
        lista_produtos.append({
            'cod_produto': p.cod_produto,
            'nome_produto': p.nome_produto,
            'categoria_produto': p.categoria_produto or '',
            'tipo_materia_prima': p.tipo_materia_prima or '',
            'tipo_embalagem': p.tipo_embalagem or '',
            'subcategoria': p.subcategoria or ''
        })

    return lista_produtos


def chamar_haiku_liberdade_total(descricao_cliente: str, codigo_cliente: str,
                                  nome_cliente: str, produtos: list) -> dict:
    """
    Envia TODOS os produtos ao Haiku e deixa ele decidir livremente.

    O Haiku pode pesquisar em qualquer campo que quiser.
    """

    client = Anthropic()

    # Construir lista de produtos para o prompt
    produtos_texto = ""
    for p in produtos:
        produtos_texto += f"""
COD: {p['cod_produto']}
NOME: {p['nome_produto']}
CATEGORIA: {p['categoria_produto']}
MATERIA_PRIMA: {p['tipo_materia_prima']}
EMBALAGEM: {p['tipo_embalagem']}
---"""

    prompt = f"""Voce e um especialista em resolucao de produtos alimenticios.

TAREFA: Encontrar o produto interno que corresponde a descricao do cliente.

INFORMACOES DO CLIENTE:
- Descricao: {descricao_cliente}
- Codigo do Cliente: {codigo_cliente}
- Nome do Cliente: {nome_cliente}

GLOSSARIO DE ABREVIACOES (para sua referencia):
- VDE = Verde
- PTA = Preta
- S/CAR ou S CAR = Sem Caroco
- C/CAR ou C CAR = Com Caroco = INTEIRA
- BD = Balde
- FD = Fardo
- SC = Saco
- CX = Caixa
- DP = Doy Pack
- PT = Pote
- CAMPO BELO = Marca

IMPORTANTE SOBRE AZEITONAS:
- "INTEIRA" significa COM CAROCO (C CAR)
- "SEM CAROCO" ou "S CAR" significa que o caroco foi removido
- Quando o cliente pede "C CAR" ele quer azeitona INTEIRA (com caroco)

LISTA COMPLETA DE PRODUTOS DISPONIVEIS:
{produtos_texto}

INSTRUCOES:
1. Analise a descricao do cliente
2. Identifique: tipo de produto, variedade, presenca/ausencia de caroco, marca, embalagem, peso
3. Procure na lista o produto que melhor corresponde
4. Voce tem LIBERDADE TOTAL para pesquisar em qualquer campo

RESPONDA EXATAMENTE NESTE FORMATO:
CODIGO_ENCONTRADO: [codigo do produto ou NENHUM]
NOME_PRODUTO: [nome completo do produto]
CONFIANCA: [ALTA/MEDIA/BAIXA]
JUSTIFICATIVA: [explicacao da correspondencia]

ANALISE:"""

    print("\n" + "="*80)
    print("ENVIANDO PARA HAIKU...")
    print(f"Total de produtos enviados: {len(produtos)}")
    print("="*80)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    resposta_texto = response.content[0].text

    return {
        'resposta_completa': resposta_texto,
        'tokens_input': response.usage.input_tokens,
        'tokens_output': response.usage.output_tokens
    }


def main():
    """Executa o teste"""

    # Caso de teste
    descricao = "AZEITONA VDE C CAR CAMPO BELO BD 2kg"
    codigo_cliente = "964348"
    nome_cliente = "Tenda Atacado (01157555)"

    print("\n" + "="*80)
    print("TESTE: HAIKU COM LIBERDADE TOTAL")
    print("="*80)
    print(f"\nDescricao Cliente: {descricao}")
    print(f"Codigo Cliente: {codigo_cliente}")
    print(f"Cliente: {nome_cliente}")
    print("="*80)

    app = create_app()
    with app.app_context():
        # Buscar todos produtos vendidos
        print("\nBuscando TODOS os produtos vendidos...")
        produtos = buscar_todos_produtos_vendidos()
        print(f"Total de produtos encontrados: {len(produtos)}")

        # Mostrar alguns exemplos de azeitonas para contexto
        print("\n--- Exemplos de produtos de AZEITONA no catalogo ---")
        azeitonas = [p for p in produtos if 'AZEITONA' in p['nome_produto'].upper()]
        for i, az in enumerate(azeitonas[:20]):  # Primeiros 20
            print(f"  {az['cod_produto']}: {az['nome_produto']}")
        print(f"  ... (total: {len(azeitonas)} azeitonas)")

        # Chamar Haiku
        resultado = chamar_haiku_liberdade_total(
            descricao,
            codigo_cliente,
            nome_cliente,
            produtos
        )

        print("\n" + "="*80)
        print("RESPOSTA DO HAIKU:")
        print("="*80)
        print(resultado['resposta_completa'])
        print("\n" + "="*80)
        print(f"Tokens usados - Input: {resultado['tokens_input']}, Output: {resultado['tokens_output']}")
        print("="*80)

        # Verificar se encontrou INTEIRA
        if 'INTEIRA' in resultado['resposta_completa'].upper():
            print("\n[OK] Haiku identificou corretamente como INTEIRA (com caroco)")
        elif 'SEM CARO' in resultado['resposta_completa'].upper() or 'S/CAR' in resultado['resposta_completa'].upper():
            print("\n[ERRO] Haiku identificou incorretamente como SEM CAROCO")
        else:
            print("\n[?] Verificar resposta manualmente")


if __name__ == "__main__":
    main()
