#!/usr/bin/env python3
"""
Script de teste para leitura de PDFs de pedidos
Testa especificamente o formato Atacadão
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.pedidos.leitura import AtacadaoExtractor, PedidoProcessor
import json
from decimal import Decimal


def decimal_to_float(obj):
    """Converte Decimal para float para serialização JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def test_atacadao_pdf():
    """Testa extração de PDF do Atacadão"""
    
    # Caminho do arquivo de teste
    pdf_path = '/mnt/c/Users/rafael.nascimento/Downloads/PROPOSTA NACOM (2).pdf'
    
    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        return
    
    print("=" * 60)
    print("TESTE DE LEITURA DE PDF - FORMATO ATACADÃO")
    print("=" * 60)
    
    # Teste 1: Extração direta com AtacadaoExtractor
    print("\n📋 Teste 1: Extração direta com AtacadaoExtractor")
    print("-" * 40)
    
    extractor = AtacadaoExtractor()
    data = extractor.extract(pdf_path)
    
    print(f"✅ Itens extraídos: {len(data)}")
    
    if data:
        # Mostra primeiro item como exemplo
        print("\n📦 Exemplo do primeiro item:")
        first_item = data[0]
        for key, value in first_item.items():
            print(f"  {key}: {value}")
    
    # Teste 2: Processamento completo com PedidoProcessor
    print("\n📋 Teste 2: Processamento com PedidoProcessor")
    print("-" * 40)
    
    processor = PedidoProcessor()
    result = processor.process_file(
        pdf_path,
        formato='atacadao',
        validate=True,
        save_to_db=False
    )
    
    if result['success']:
        print("✅ Processamento bem-sucedido!")
        
        summary = result['summary']
        print(f"\n📊 Resumo:")
        print(f"  Total de itens: {summary.get('total_itens', 0)}")
        print(f"  Total de filiais: {summary.get('total_filiais', 0)}")
        print(f"  Total de produtos: {summary.get('total_produtos', 0)}")
        print(f"  Quantidade total: {summary.get('quantidade_total', 0):,} caixas")
        print(f"  Valor total: R$ {summary.get('valor_total', 0):,.2f}")
        
        # Mostra resumo por filial
        if 'por_filial' in summary:
            print(f"\n📍 Por Filial:")
            for filial in summary['por_filial']:
                print(f"  {filial['local']}:")
                print(f"    CNPJ: {filial['cnpj']}")
                print(f"    Itens: {filial['itens']}")
                print(f"    Quantidade: {filial['quantidade']:,} caixas")
                print(f"    Valor: R$ {filial['valor']:,.2f}")
    else:
        print("❌ Erro no processamento:")
        for error in result.get('errors', []):
            print(f"  - {error}")
    
    # Teste 3: Exportar para Excel
    print("\n📋 Teste 3: Exportação para Excel")
    print("-" * 40)
    
    if result['success'] and result['data']:
        try:
            output_path = '/tmp/pedido_atacadao_teste.xlsx'
            processor.export_to_excel(result['data'], output_path)
            print(f"✅ Excel exportado para: {output_path}")
            
            # Verifica se arquivo foi criado
            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                print(f"  Tamanho do arquivo: {size:,} bytes")
        except Exception as e:
            print(f"❌ Erro ao exportar: {e}")
    
    # Teste 4: Validação de dados específicos
    print("\n📋 Teste 4: Validação de Dados Específicos")
    print("-" * 40)
    
    if result['success'] and result['data']:
        # Verifica CNPJs únicos
        cnpjs = set(item.get('cnpj_filial', '') for item in result['data'])
        print(f"CNPJs encontrados: {len(cnpjs)}")
        for cnpj in sorted(cnpjs):
            if cnpj:
                print(f"  - {cnpj}")
        
        # Verifica produtos únicos
        produtos = {}
        for item in result['data']:
            codigo = item.get('codigo', '')
            if codigo and codigo not in produtos:
                produtos[codigo] = item.get('descricao', '')
        
        print(f"\nProdutos únicos: {len(produtos)}")
        # Mostra primeiros 5 produtos
        for i, (codigo, descricao) in enumerate(list(produtos.items())[:5]):
            print(f"  {codigo}: {descricao}")
        
        if len(produtos) > 5:
            print(f"  ... e mais {len(produtos) - 5} produtos")
    
    # Mostra avisos se houver
    if result.get('warnings'):
        print(f"\n⚠️ Avisos:")
        for warning in result['warnings']:
            print(f"  - {warning}")
    
    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO")
    print("=" * 60)


if __name__ == "__main__":
    test_atacadao_pdf()