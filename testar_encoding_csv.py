#!/usr/bin/env python3
"""
Script para testar leitura de CSV com diferentes encodings
Simula o comportamento do portal Atacadão
"""

import pandas as pd
import tempfile
import os

def testar_leitura_csv(arquivo_path):
    """Testa leitura de CSV com diferentes encodings"""
    
    print(f"Testando arquivo: {arquivo_path}")
    print("="*60)
    
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-16']
    df = None
    
    for encoding in encodings:
        try:
            df = pd.read_csv(arquivo_path, encoding=encoding)
            print(f"✅ Sucesso com encoding: {encoding}")
            print(f"   Linhas: {len(df)}")
            print(f"   Colunas: {list(df.columns)[:5]}")
            break
        except UnicodeDecodeError as e:
            print(f"❌ Falha com {encoding}: {str(e)[:50]}...")
        except Exception as e:
            print(f"⚠️ Erro com {encoding}: {str(e)[:50]}...")
    
    if df is None:
        print("\n🔧 Tentando com latin-1 e errors='ignore'...")
        try:
            df = pd.read_csv(arquivo_path, encoding='latin-1', errors='ignore')
            print("✅ Leitura bem-sucedida com latin-1 + ignore")
            print(f"   Linhas: {len(df)}")
            print(f"   Colunas: {list(df.columns)[:5]}")
        except Exception as e:
            print(f"❌ Falha total: {e}")
            return None
    
    return df

def criar_csv_teste_latin1():
    """Cria um CSV de teste com caracteres Latin-1"""
    
    # Criar conteúdo com caracteres problemáticos (Latin-1)
    conteudo = """cod atacadao,descricao atacadao,nosso cod
12345,AÇÚCAR CRISTAL 1KG,001
67890,FEIJÃO CARIOCA 1KG,002
11111,PÃO FRANCÊS,003
22222,MAÇÃ ARGENTINA,004
33333,JOSÉ MARIA CÔRTES,005"""
    
    # Salvar em arquivo temporário com encoding Latin-1
    with tempfile.NamedTemporaryFile(mode='w', encoding='latin-1', 
                                     suffix='.csv', delete=False) as f:
        f.write(conteudo)
        temp_path = f.name
    
    print(f"CSV teste criado: {temp_path}")
    return temp_path

def criar_csv_teste_windows():
    """Cria um CSV de teste com caracteres Windows-1252"""
    
    # Conteúdo com caracteres Windows-1252
    conteudo = """cod atacadao,descricao atacadao,nosso cod
54321,CAFÉ SOLÚVEL 200G,006
98765,AÇÚCAR — REFINADO,007
44444,CURAÇAO BLUE,008
55555,JOSÉ'S SPECIAL,009"""
    
    # Salvar com encoding Windows-1252
    with tempfile.NamedTemporaryFile(mode='w', encoding='cp1252', 
                                     suffix='.csv', delete=False) as f:
        f.write(conteudo)
        temp_path = f.name
    
    print(f"CSV teste Windows-1252 criado: {temp_path}")
    return temp_path

if __name__ == "__main__":
    print("="*60)
    print("TESTE DE LEITURA DE CSV COM DIFERENTES ENCODINGS")
    print("="*60)
    
    # Teste 1: Latin-1
    print("\n📄 TESTE 1: CSV com Latin-1")
    print("-"*40)
    csv_latin1 = criar_csv_teste_latin1()
    df1 = testar_leitura_csv(csv_latin1)
    
    if df1 is not None:
        print("\n📊 Primeiras linhas do DataFrame:")
        print(df1.head())
    
    # Teste 2: Windows-1252
    print("\n📄 TESTE 2: CSV com Windows-1252")
    print("-"*40)
    csv_windows = criar_csv_teste_windows()
    df2 = testar_leitura_csv(csv_windows)
    
    if df2 is not None:
        print("\n📊 Primeiras linhas do DataFrame:")
        print(df2.head())
    
    # Limpar arquivos temporários
    os.remove(csv_latin1)
    os.remove(csv_windows)
    
    print("\n" + "="*60)
    print("✅ TESTES CONCLUÍDOS")
    print("="*60)
    print("\nA correção implementada deve funcionar para:")
    print("- UTF-8 (padrão)")
    print("- Latin-1 (ISO-8859-1)")
    print("- Windows-1252 (CP1252)")
    print("- UTF-16")
    print("\nSe todos falharem, usa Latin-1 com errors='ignore'")