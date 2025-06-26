#!/usr/bin/env python3
"""
Script para verificar e preparar a Pasta4.xlsx para importação
"""
import pandas as pd
import os

def verificar_pasta4():
    """Verifica o formato da Pasta4.xlsx"""
    arquivo = "Pasta4.xlsx"
    
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo {arquivo} não encontrado!")
        return
    
    print(f"\n📄 Analisando {arquivo}...")
    
    try:
        # Ler o arquivo
        df = pd.read_excel(arquivo)
        
        print(f"\n📊 Informações do arquivo:")
        print(f"- Total de linhas: {len(df)}")
        print(f"- Total de colunas: {len(df.columns)}")
        
        print(f"\n📋 Colunas encontradas:")
        for i, col in enumerate(df.columns):
            print(f"  {i+1}. {col}")
        
        print(f"\n🔍 Primeiras 5 linhas:")
        print(df.head())
        
        # Verificar se tem as colunas necessárias
        print("\n✅ Verificando colunas necessárias:")
        
        # Procurar coluna de NF
        colunas_nf = [col for col in df.columns if 'NF' in str(col).upper() or 'NOTA' in str(col).upper()]
        if colunas_nf:
            print(f"  - Possível coluna NF: {colunas_nf}")
        else:
            print(f"  - ❌ Nenhuma coluna de NF encontrada")
        
        # Procurar coluna de data
        colunas_data = [col for col in df.columns if 'DATA' in str(col).upper() or 'ENTREGA' in str(col).upper()]
        if colunas_data:
            print(f"  - Possível coluna Data: {colunas_data}")
        else:
            print(f"  - ❌ Nenhuma coluna de data encontrada")
        
        # Verificar tipos de dados
        print("\n📊 Tipos de dados:")
        print(df.dtypes)
        
        # Sugerir mapeamento
        print("\n💡 SUGESTÃO DE PREPARAÇÃO:")
        print("Se as colunas não estiverem no formato esperado, você pode:")
        print("1. Renomear as colunas no Excel para 'NF' e 'Data Entrega'")
        print("2. Ou usar o script abaixo para preparar automaticamente")
        
        return df
        
    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")
        return None

def preparar_arquivo(df, coluna_nf, coluna_data):
    """Prepara o arquivo no formato correto"""
    try:
        # Criar novo DataFrame com as colunas corretas
        df_preparado = pd.DataFrame()
        
        # Copiar coluna NF
        df_preparado['NF'] = df[coluna_nf].astype(str).str.strip()
        
        # Copiar coluna Data
        df_preparado['Data Entrega'] = pd.to_datetime(df[coluna_data])
        
        # Remover linhas vazias
        df_preparado = df_preparado[df_preparado['NF'].notna() & (df_preparado['NF'] != '')]
        
        # Salvar arquivo preparado
        arquivo_saida = 'Pasta4_preparada.xlsx'
        df_preparado.to_excel(arquivo_saida, index=False)
        
        print(f"\n✅ Arquivo preparado salvo em: {arquivo_saida}")
        print(f"Total de registros: {len(df_preparado)}")
        
        print("\n🎯 Agora você pode importar com:")
        print(f"python importar_entregas_realizadas.py {arquivo_saida}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao preparar arquivo: {e}")
        return False

if __name__ == "__main__":
    print("🔍 VERIFICADOR DE PASTA4.XLSX")
    print("="*50)
    
    df = verificar_pasta4()
    
    if df is not None:
        print("\n" + "="*50)
        print("📝 PREPARAR ARQUIVO?")
        print("="*50)
        
        print("\nSe você quiser preparar o arquivo automaticamente,")
        print("informe os nomes das colunas corretas:")
        
        coluna_nf = input("\nNome da coluna com número da NF: ").strip()
        coluna_data = input("Nome da coluna com data de entrega: ").strip()
        
        if coluna_nf and coluna_data:
            if coluna_nf in df.columns and coluna_data in df.columns:
                preparar_arquivo(df, coluna_nf, coluna_data)
            else:
                print(f"\n❌ Colunas '{coluna_nf}' ou '{coluna_data}' não encontradas!")
        else:
            print("\n⚠️ Preparação cancelada.") 