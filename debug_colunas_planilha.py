#!/usr/bin/env python3
"""
🔍 DEBUG - DETECÇÃO DE COLUNAS PLANILHA
Investiga por que o status_finalizacao não está sendo detectado
"""

import sys
import os
import pandas as pd

def debug_colunas_planilha(arquivo_excel, sheet_name='Sheet1'):
    """Debug das colunas da planilha"""
    
    print("🔍 DEBUG - DETECÇÃO DE COLUNAS")
    print("=" * 50)
    
    try:
        # Carrega planilha
        df = pd.read_excel(arquivo_excel, sheet_name=sheet_name)
        print(f"✅ Planilha carregada: {len(df)} linhas, {len(df.columns)} colunas")
        
        print(f"\n📋 TODAS AS COLUNAS ENCONTRADAS:")
        for i, col in enumerate(df.columns):
            print(f"   {i+1:2}. '{col}' (tipo: {type(col).__name__})")
            
        print(f"\n🔍 ANÁLISE DETALHADA DAS COLUNAS:")
        for col in df.columns:
            col_clean = str(col).strip()
            print(f"   • Original: '{col}'")
            print(f"     Limpa: '{col_clean}'")
            print(f"     Len: {len(str(col))}")
            print(f"     Bytes: {[hex(ord(c)) for c in str(col)]}")
            print()
        
        # Colunas que o script procura
        colunas_esperadas = [
            'numero_nf',
            'data_embarque', 
            'data_entrega_prevista',
            'data_agenda',
            'status_finalizacao',  # ← ESTA É A PROBLEMÁTICA
            'data_entrega_realizada',
            'protocolo_agendamento',
            'data_agendamento',
            'acompanhamento_descricao'
        ]
        
        print(f"🎯 VERIFICAÇÃO DAS COLUNAS ESPERADAS:")
        for col_esperada in colunas_esperadas:
            encontrada = col_esperada in df.columns
            status = "✅ ENCONTRADA" if encontrada else "❌ NÃO ENCONTRADA"
            print(f"   {col_esperada}: {status}")
            
            if not encontrada:
                # Busca similar
                similares = []
                for col_real in df.columns:
                    col_real_lower = str(col_real).lower().strip()
                    col_esperada_lower = col_esperada.lower()
                    
                    if col_esperada_lower in col_real_lower or col_real_lower in col_esperada_lower:
                        similares.append(col_real)
                
                if similares:
                    print(f"     Similares encontradas: {similares}")
        
        # Mostra alguns dados da primeira linha
        print(f"\n📊 PRIMEIRA LINHA DE DADOS:")
        if len(df) > 0:
            primeira_linha = df.iloc[0]
            for col in df.columns:
                valor = primeira_linha[col]
                print(f"   {col}: '{valor}' (tipo: {type(valor).__name__})")
        
        # Verifica se status_finalizacao existe com outro nome
        print(f"\n🔍 BUSCANDO VARIAÇÕES DE 'status_finalizacao':")
        possibilidades = [
            'status_finalizacao', 'status finalizacao', 'statusfinalizacao',
            'status_finalizacao', 'Status_Finalizacao', 'STATUS_FINALIZACAO',
            'status', 'Status', 'STATUS',
            'finalizacao', 'Finalizacao', 'FINALIZACAO',
            'situacao', 'Situacao', 'SITUACAO'
        ]
        
        for poss in possibilidades:
            if poss in df.columns:
                print(f"   ✅ ENCONTRADA: '{poss}'")
                # Mostra alguns valores
                valores_unicos = df[poss].dropna().unique()[:5]
                print(f"     Valores exemplo: {list(valores_unicos)}")
            
    except Exception as e:
        print(f"❌ Erro ao processar planilha: {e}")

def main():
    if len(sys.argv) != 2:
        print("Uso: python debug_colunas_planilha.py arquivo.xlsx")
        return
    
    arquivo = sys.argv[1]
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        return
    
    debug_colunas_planilha(arquivo)

if __name__ == '__main__':
    main() 