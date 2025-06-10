#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script Otimizado para Importar Vínculos no Render
=================================================

Este script importa vínculos transportadora-cidade seguindo a estrutura do sistema.

Estrutura da Planilha Excel (vinculos.xlsx):
-------------------------------------------
TRANSPORTADORA | CIDADE | UF | CODIGO IBGE | TABELA | LEAD TIME
Vale Logistics | São Paulo | SP | 3550308 | EXPRESSA | 2
JTL Express | Rio de Janeiro | RJ | 3304557 | ECONOMICA | 3

Performance: Otimizado para 500 registros/lote com 1s de pausa.
"""

import os
import sys
import time
import requests
from pathlib import Path

def aguardar_com_progresso(segundos, mensagem="Aguardando"):
    """Aguarda com indicador de progresso"""
    print(f"{mensagem}...", end="")
    for i in range(segundos):
        print(".", end="", flush=True)
        time.sleep(1)
    print(" ✅")

def importar_vinculos_seguro():
    """Importa vínculos de forma otimizada no Render - Performance Excepcional"""
    
    print("🚀 === IMPORTAÇÃO OTIMIZADA DE VÍNCULOS NO RENDER ===\n")
    print("⚡ Configurado para ALTA PERFORMANCE baseado em 5.570 registros/5s")
    
    # Configurar o app Flask
    sys.path.append('/opt/render/project/src')
    
    try:
        from app import create_app, db
        from app.vinculos.models import CidadeAtendida
        from app.transportadoras.models import Transportadora
        from app.localidades.models import Cidade
        from sqlalchemy import text
        import pandas as pd
        
        print("📦 Módulos importados com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao importar módulos: {e}")
        return False
    
    app = create_app()
    
    with app.app_context():
        try:
            # 1. Verificar conexão com banco
            print("🔍 Testando conexão com banco...")
            total_vinculos = CidadeAtendida.query.count()
            print(f"✅ Conexão OK. Vínculos atuais: {total_vinculos}")
            
            # 2. Baixar arquivo diretamente (sem verificação HEAD que dá redirect)
            github_url = "https://github.com/Rafael-2109/frete-sistema/raw/main/vinculos.xlsx"
            print(f"📥 Baixando arquivo: {github_url}")
            
            try:
                response = requests.get(github_url, timeout=60, allow_redirects=True)
                response.raise_for_status()
                
                # Salvar temporariamente
                temp_file = '/tmp/vinculos.xlsx'
                with open(temp_file, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Arquivo baixado: {len(response.content):,} bytes")
                
            except requests.RequestException as e:
                print(f"❌ Erro ao baixar arquivo: {e}")
                print("💡 Verifique se vinculos.xlsx está no repositório")
                return False
            
            # 4. Ler arquivo Excel
            print("📖 Lendo arquivo Excel...")
            df = pd.read_excel(temp_file, dtype=str)
            
            # Normalizar nomes das colunas (igual sistema web)
            df.columns = df.columns.str.strip().str.upper()
            
            print(f"✅ Arquivo lido: {len(df):,} linhas")
            
            if df.empty:
                print("⚠️ Arquivo está vazio!")
                return False
            
            print(f"📋 Colunas disponíveis: {list(df.columns)}")
            print("🔄 Colunas normalizadas para maiúscula automaticamente")
            
            # Validar estrutura da planilha
            colunas_necessarias = ['TRANSPORTADORA', 'CIDADE', 'UF', 'CODIGO IBGE', 'TABELA', 'LEAD TIME']
            colunas_faltantes = []
            
            for coluna in colunas_necessarias:
                if coluna not in df.columns:
                    colunas_faltantes.append(coluna)
            
            if colunas_faltantes:
                print(f"❌ Colunas faltantes na planilha: {colunas_faltantes}")
                print("💡 Estrutura esperada: TRANSPORTADORA | CIDADE | UF | CODIGO IBGE | TABELA | LEAD TIME")
                return False
            
            print("✅ Estrutura da planilha validada!")
            
            # 5. Processar em lotes OTIMIZADOS (500 registros por vez!)
            print("⚡ Processando vínculos em lotes OTIMIZADOS para alta performance...")
            
            lote_size = 500  # 25x maior que antes!
            total_processados = 0
            total_erros = 0
            
            for i in range(0, len(df), lote_size):
                lote = df.iloc[i:i+lote_size]
                
                print(f"💾 Processando lote {i//lote_size + 1} ({len(lote):,} registros)...")
                
                for index, row in lote.iterrows():
                    try:
                        # Lendo dados da planilha conforme estrutura do sistema
                        transportadora_nome = str(row.get('TRANSPORTADORA', '')).strip()
                        cidade_nome = str(row.get('CIDADE', '')).strip()
                        uf = str(row.get('UF', '')).strip().upper()
                        codigo_ibge = str(row.get('CODIGO IBGE', '')).strip()
                        nome_tabela = str(row.get('TABELA', '')).strip()
                        lead_time = row.get('LEAD TIME', None)
                        
                        # Validação básica
                        if not transportadora_nome or not cidade_nome or not uf or not codigo_ibge or not nome_tabela:
                            print(f"⚠️ Dados incompletos na linha {index + 1}")
                            total_erros += 1
                            continue
                        
                        # Buscar transportadora pelo nome (mesma lógica da função web)
                        transportadora = Transportadora.query.filter(
                            Transportadora.razao_social.ilike(transportadora_nome)
                        ).first()
                        
                        if not transportadora:
                            print(f"⚠️ Transportadora não encontrada: {transportadora_nome}")
                            total_erros += 1
                            continue
                        
                        # Buscar cidade pelo código IBGE (mesma lógica da função web)
                        cidade = Cidade.query.filter_by(
                            codigo_ibge=codigo_ibge
                        ).first()
                        
                        if not cidade:
                            print(f"⚠️ Cidade (IBGE) não encontrada: {codigo_ibge}")
                            total_erros += 1
                            continue
                        
                        # Verificar se vínculo já existe (mesma lógica da função web)
                        vinculo_existente = CidadeAtendida.query.filter_by(
                            cidade_id=cidade.id,
                            transportadora_id=transportadora.id,
                            nome_tabela=nome_tabela
                        ).first()
                        
                        if vinculo_existente:
                            # print(f"ℹ️ Vínculo já existe: {transportadora_nome} → {cidade_nome}/{uf} → {nome_tabela}")
                            total_erros += 1
                            continue
                        
                        # Criar novo vínculo (exatamente como na função web)
                        novo_vinculo = CidadeAtendida(
                            cidade_id=cidade.id,
                            transportadora_id=transportadora.id,
                            codigo_ibge=codigo_ibge,
                            uf=uf,
                            nome_tabela=nome_tabela,
                            lead_time=lead_time
                        )
                        
                        db.session.add(novo_vinculo)
                        total_processados += 1
                        
                    except Exception as e:
                        print(f"❌ Erro no registro {index + 1}: {e}")
                        total_erros += 1
                        continue
                
                # Commit do lote
                try:
                    db.session.commit()
                    print(f"✅ Lote de {len(lote):,} registros salvo em segundos!")
                    
                    # Pausa mínima entre lotes (reduzida drasticamente)
                    if i + lote_size < len(df):
                        aguardar_com_progresso(1, "Pausa mínima")  # Apenas 1 segundo!
                        
                except Exception as e:
                    db.session.rollback()
                    print(f"❌ Erro ao salvar lote: {e}")
                    # Continuar com próximo lote
                    continue
            
            # 6. Limpar arquivo temporário
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            # 7. Relatório final
            print("\n📊 === RELATÓRIO FINAL OTIMIZADO ===")
            print(f"✅ Vínculos processados: {total_processados:,}")
            print(f"❌ Erros encontrados: {total_erros:,}")
            print(f"📊 Total de vínculos no banco: {CidadeAtendida.query.count():,}")
            print(f"🚀 Performance: {lote_size} registros por lote")
            print(f"📈 Taxa de sucesso: {(total_processados / len(df) * 100):.1f}%")
            
            if total_processados > 0:
                print("🎉 Importação OTIMIZADA concluída com sucesso!")
                print("💡 Vínculos criados seguem a estrutura: Transportadora → Cidade → Tabela")
                return True
            else:
                print("⚠️ Nenhum vínculo foi importado!")
                print("💡 Verifique se:")
                print("   • Transportadoras estão cadastradas no sistema")
                print("   • Códigos IBGE das cidades estão corretos")
                print("   • Vínculos não já existem no sistema")
                return False
                
        except Exception as e:
            print(f"❌ Erro durante importação: {e}")
            try:
                db.session.rollback()
            except:
                pass
            return False

def verificar_ambiente():
    """Verifica se está no ambiente Render"""
    render_vars = ['RENDER', 'RENDER_SERVICE_ID', 'RENDER_SERVICE_NAME']
    is_render = any(var in os.environ for var in render_vars)
    
    if not is_render:
        print("⚠️ Este script deve ser executado no ambiente Render!")
        print("💡 Use o Shell do Render para executar este script.")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Iniciando importação de vínculos...")
    
    if not verificar_ambiente():
        sys.exit(1)
    
    sucesso = importar_vinculos_seguro()
    
    if sucesso:
        print("\n🎉 IMPORTAÇÃO REALIZADA COM SUCESSO! 🔗")
        sys.exit(0)
    else:
        print("\n💥 IMPORTAÇÃO FALHOU! ❌")
        sys.exit(1) 