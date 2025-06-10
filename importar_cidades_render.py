#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para Importar Cidades no Render
======================================

Este script é específico para executar no Render e importar as cidades no PostgreSQL.
"""

import os
import sys
import requests
import pandas as pd
from io import BytesIO

def baixar_arquivo_cidades():
    """Baixa o arquivo de cidades do GitHub"""
    
    # URL do arquivo cidades.xlsx no repositório
    github_url = "https://github.com/Rafael-2109/frete-sistema/raw/main/cidades.xlsx"
    
    print("📥 Baixando arquivo de cidades do GitHub...")
    
    try:
        response = requests.get(github_url)
        response.raise_for_status()
        
        # Salva temporariamente
        with open('/tmp/cidades.xlsx', 'wb') as f:
            f.write(response.content)
            
        print("✅ Arquivo baixado com sucesso!")
        return '/tmp/cidades.xlsx'
        
    except Exception as e:
        print(f"❌ Erro ao baixar arquivo: {e}")
        return None

def importar_cidades_render():
    """Importa cidades no ambiente do Render"""
    
    # Configurar o app Flask
    sys.path.append('/opt/render/project/src')
    
    from app import create_app, db
    from app.localidades.models import Cidade
    
    app = create_app()
    
    with app.app_context():
        # Verificar se já existem cidades
        total_existentes = Cidade.query.count()
        print(f"🔍 Cidades já cadastradas: {total_existentes}")
        
        if total_existentes > 0:
            print("⚠️ Já existem cidades cadastradas. Pulando importação.")
            return True
        
        # Baixar arquivo
        arquivo_path = baixar_arquivo_cidades()
        if not arquivo_path:
            return False
        
        try:
            print("📖 Lendo arquivo Excel...")
            df = pd.read_excel(arquivo_path, dtype=str)
            df.columns = df.columns.str.strip().str.upper()
            
            print(f"✅ Arquivo lido: {len(df)} linhas encontradas")
            
            contador_importados = 0
            contador_erros = 0
            
            for index, row in df.iterrows():
                try:
                    cidade_nome = row.get('CIDADE', '').strip()
                    uf = row.get('UF', '').strip().upper()
                    codigo_ibge = row.get('IBGE', '').strip()
                    
                    if not cidade_nome or not uf or not codigo_ibge:
                        contador_erros += 1
                        continue
                    
                    # Processar ICMS
                    icms_str = str(row.get('ICMS', '0')).replace('%', '').replace(',', '.').strip()
                    try:
                        icms = float(icms_str)
                        if icms > 1:
                            icms = icms / 100
                    except:
                        icms = 0.0
                    
                    # Processar ISS
                    iss_str = str(row.get('SUBSTITUI ICMS POR ISS', row.get('ISS', ''))).upper()
                    substitui_iss = iss_str in ['SIM', 'S', 'TRUE', '1', 'YES']
                    
                    # Verificar se cidade já existe
                    cidade_existente = Cidade.query.filter_by(
                        nome=cidade_nome,
                        uf=uf
                    ).first()
                    
                    if cidade_existente:
                        contador_erros += 1
                        continue
                    
                    # Criar cidade
                    cidade = Cidade(
                        nome=cidade_nome,
                        uf=uf,
                        codigo_ibge=codigo_ibge,
                        icms=icms,
                        substitui_icms_por_iss=substitui_iss,
                        microrregiao=row.get('MICRORREGIAO', '').strip() if pd.notna(row.get('MICRORREGIAO')) else None,
                        mesorregiao=row.get('MESORREGIAO', '').strip() if pd.notna(row.get('MESORREGIAO')) else None
                    )
                    
                    db.session.add(cidade)
                    contador_importados += 1
                    
                    # Commit a cada 100 registros
                    if contador_importados % 100 == 0:
                        db.session.commit()
                        print(f"💾 {contador_importados} cidades processadas...")
                        
                except Exception as e:
                    print(f"❌ Erro na linha {index + 1}: {e}")
                    contador_erros += 1
                    continue
            
            # Commit final
            db.session.commit()
            
            # Limpar arquivo temporário
            if os.path.exists(arquivo_path):
                os.remove(arquivo_path)
            
            print("✅ === IMPORTAÇÃO CONCLUÍDA ===")
            print(f"🎯 Cidades importadas: {contador_importados}")
            print(f"⚠️ Linhas com erro: {contador_erros}")
            print(f"📊 Total no banco: {Cidade.query.count()}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro na importação: {e}")
            return False

if __name__ == "__main__":
    print("🏙️ === IMPORTAÇÃO DE CIDADES NO RENDER ===")
    
    sucesso = importar_cidades_render()
    
    if sucesso:
        print("🎉 Importação realizada com sucesso!")
        sys.exit(0)
    else:
        print("💥 Importação falhou!")
        sys.exit(1) 