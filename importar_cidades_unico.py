#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de Importação Única de Cidades
=====================================

Este script deve ser executado APENAS UMA VEZ para importar a base completa de cidades.

Uso:
    python importar_cidades_unico.py arquivo_cidades.xlsx

Formato esperado do Excel:
    CIDADE | UF | IBGE | ICMS | ISS | MICRORREGIAO | MESORREGIAO
    
Exemplo:
    Goiânia | GO | 5208707 | 7,00% | NÃO | Goiânia | Centro Goiano
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Adiciona o diretório raiz ao path para importações
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.localidades.models import Cidade

def verificar_arquivo(caminho):
    """Verifica se o arquivo existe e tem formato válido"""
    if not os.path.exists(caminho):
        print(f"❌ Arquivo não encontrado: {caminho}")
        return False
    
    if not caminho.endswith('.xlsx'):
        print("❌ Arquivo deve ser .xlsx")
        return False
    
    return True

def verificar_colunas_obrigatorias(df):
    """Verifica se o DataFrame tem as colunas obrigatórias"""
    colunas_obrigatorias = ['CIDADE', 'UF', 'IBGE', 'ICMS']
    colunas_faltando = [col for col in colunas_obrigatorias if col not in df.columns]
    
    if colunas_faltando:
        print(f"❌ Colunas obrigatórias faltando: {', '.join(colunas_faltando)}")
        print(f"📋 Colunas encontradas: {', '.join(df.columns)}")
        return False
    
    return True

def processar_icms(valor_icms):
    """Converte valor ICMS de string para float"""
    if pd.isna(valor_icms):
        return 0.0
    
    try:
        # Remove %, espaços e converte vírgula para ponto
        icms_str = str(valor_icms).replace('%', '').replace(',', '.').strip()
        icms = float(icms_str)
        
        # Se o valor for maior que 1, assume que está em percentual (ex: 7.00 = 7%)
        if icms > 1:
            icms = icms / 100
            
        return icms
    except (ValueError, TypeError):
        print(f"⚠️ Valor ICMS inválido: {valor_icms}, usando 0.0")
        return 0.0

def processar_iss(valor_iss):
    """Converte valor ISS para boolean"""
    if pd.isna(valor_iss):
        return False
    
    valor_str = str(valor_iss).strip().upper()
    return valor_str in ['SIM', 'S', 'TRUE', '1', 'YES']

def limpar_campo(valor):
    """Limpa e formata campos de texto"""
    if pd.isna(valor):
        return None
    return str(valor).strip()

def importar_cidades_unico(caminho_arquivo):
    """Função principal de importação única"""
    
    print("🏙️ === IMPORTAÇÃO ÚNICA DE CIDADES ===")
    print(f"📁 Arquivo: {caminho_arquivo}")
    print(f"⏰ Início: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # 1. Verificações iniciais
    if not verificar_arquivo(caminho_arquivo):
        return False
    
    app = create_app()
    
    with app.app_context():
        # 2. Verificar se já existem cidades
        total_existentes = Cidade.query.count()
        print(f"🔍 Cidades já cadastradas: {total_existentes}")
        
        if total_existentes > 0:
            resposta = input("⚠️ Já existem cidades cadastradas. Continuar? (s/N): ")
            if resposta.lower() not in ['s', 'sim', 'y', 'yes']:
                print("❌ Importação cancelada pelo usuário.")
                return False
        
        # 3. Ler arquivo Excel
        try:
            print("📖 Lendo arquivo Excel...")
            df = pd.read_excel(caminho_arquivo, dtype=str)
            df.columns = df.columns.str.strip().str.upper()
            print(f"✅ Arquivo lido: {len(df)} linhas encontradas")
        except Exception as e:
            print(f"❌ Erro ao ler arquivo: {e}")
            return False
        
        # 4. Verificar colunas
        if not verificar_colunas_obrigatorias(df):
            return False
        
        # 5. Processar dados
        print("⚙️ Processando dados...")
        cidades_importadas = 0
        cidades_com_erro = 0
        
        for index, row in df.iterrows():
            try:
                # Campos obrigatórios
                nome = limpar_campo(row['CIDADE'])
                uf = limpar_campo(row['UF'])
                codigo_ibge = limpar_campo(row['IBGE'])
                
                if not nome or not uf or not codigo_ibge:
                    print(f"⚠️ Linha {index + 2}: Campos obrigatórios vazios - pulando")
                    cidades_com_erro += 1
                    continue
                
                # Verificar se cidade já existe
                cidade_existente = Cidade.query.filter_by(
                    nome=nome, 
                    uf=uf.upper()
                ).first()
                
                if cidade_existente:
                    print(f"⚠️ Linha {index + 2}: {nome}/{uf} já existe - pulando")
                    cidades_com_erro += 1
                    continue
                
                # Processar campos opcionais
                icms = processar_icms(row['ICMS'])
                iss = processar_iss(row.get('ISS', ''))
                microrregiao = limpar_campo(row.get('MICRORREGIAO', ''))
                mesorregiao = limpar_campo(row.get('MESORREGIAO', ''))
                
                # Criar cidade
                cidade = Cidade(
                    nome=nome,
                    uf=uf.upper(),
                    codigo_ibge=codigo_ibge,
                    icms=icms,
                    substitui_icms_por_iss=iss,
                    microrregiao=microrregiao,
                    mesorregiao=mesorregiao
                )
                
                db.session.add(cidade)
                cidades_importadas += 1
                
                # Commit a cada 100 registros para evitar problemas de memória
                if cidades_importadas % 100 == 0:
                    db.session.commit()
                    print(f"💾 {cidades_importadas} cidades processadas...")
                
            except Exception as e:
                print(f"❌ Erro na linha {index + 2}: {e}")
                cidades_com_erro += 1
                continue
        
        # 6. Commit final
        try:
            db.session.commit()
            print()
            print("✅ === IMPORTAÇÃO CONCLUÍDA ===")
            print(f"🎯 Cidades importadas: {cidades_importadas}")
            print(f"⚠️ Linhas com erro: {cidades_com_erro}")
            print(f"📊 Total no banco: {Cidade.query.count()}")
            print(f"⏰ Fim: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao salvar no banco: {e}")
            return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("❌ Uso: python importar_cidades_unico.py arquivo_cidades.xlsx")
        print()
        print("📋 Formato esperado do Excel:")
        print("   CIDADE | UF | IBGE | ICMS | ISS | MICRORREGIAO | MESORREGIAO")
        print()
        print("💡 Colunas obrigatórias: CIDADE, UF, IBGE, ICMS")
        print("💡 Colunas opcionais: ISS, MICRORREGIAO, MESORREGIAO")
        sys.exit(1)
    
    caminho_arquivo = sys.argv[1]
    sucesso = importar_cidades_unico(caminho_arquivo)
    
    if sucesso:
        print("🎉 Importação realizada com sucesso!")
        sys.exit(0)
    else:
        print("💥 Importação falhou!")
        sys.exit(1) 