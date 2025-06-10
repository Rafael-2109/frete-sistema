#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Divisor de Planilhas Grandes
============================

Script para dividir planilhas de 50k+ linhas em arquivos menores para importação segura.
"""

import pandas as pd
import os
from pathlib import Path

def dividir_planilha_grande(arquivo_input, registros_por_arquivo=10000):
    """
    Divide uma planilha grande em arquivos menores
    
    Args:
        arquivo_input: Caminho do arquivo Excel grande
        registros_por_arquivo: Número de registros por arquivo menor (otimizado para alta performance)
    """
    
    print(f"📊 === DIVISOR DE PLANILHAS GRANDES (OTIMIZADO) ===\n")
    print(f"📁 Arquivo: {arquivo_input}")
    print(f"🚀 Registros por arquivo: {registros_por_arquivo:,} (OTIMIZADO)")
    
    if not os.path.exists(arquivo_input):
        print(f"❌ Arquivo não encontrado: {arquivo_input}")
        return False
    
    try:
        # Ler arquivo grande
        print("📖 Lendo arquivo grande...")
        df = pd.read_excel(arquivo_input, dtype=str)
        total_registros = len(df)
        
        print(f"✅ Arquivo lido: {total_registros:,} registros")
        print(f"📋 Colunas: {list(df.columns)}")
        
        if total_registros <= registros_por_arquivo:
            print(f"ℹ️ Arquivo já é pequeno o suficiente ({total_registros:,} registros)")
            return True
        
        # Calcular número de arquivos necessários
        num_arquivos = (total_registros + registros_por_arquivo - 1) // registros_por_arquivo
        print(f"🔢 Será dividido em apenas {num_arquivos} arquivos (otimizado!)")
        
        # Estimar tempo baseado na performance real
        tempo_estimado_min = (num_arquivos * 2)  # 2 minutos por arquivo de 10k
        print(f"⏱️ Tempo estimado de importação: ~{tempo_estimado_min} minutos")
        
        # Criar diretório de saída
        nome_base = Path(arquivo_input).stem
        dir_saida = f"{nome_base}_otimizado"
        os.makedirs(dir_saida, exist_ok=True)
        print(f"📁 Diretório de saída: {dir_saida}")
        
        # Dividir em lotes
        arquivos_criados = []
        
        for i in range(num_arquivos):
            inicio = i * registros_por_arquivo
            fim = min((i + 1) * registros_por_arquivo, total_registros)
            
            lote = df.iloc[inicio:fim]
            nome_arquivo = f"{dir_saida}/{nome_base}_parte_{i+1:02d}.xlsx"
            
            # Salvar lote
            lote.to_excel(nome_arquivo, index=False)
            arquivos_criados.append(nome_arquivo)
            
            print(f"💾 Criado: {nome_arquivo} ({len(lote):,} registros)")
        
        # Relatório final
        print(f"\n📊 === DIVISÃO OTIMIZADA CONCLUÍDA ===")
        print(f"✅ Arquivos criados: {len(arquivos_criados)}")
        print(f"📁 Localização: {dir_saida}/")
        print(f"🎯 Total de registros preservados: {total_registros:,}")
        print(f"🚀 Performance: {registros_por_arquivo:,} registros por arquivo")
        
        print(f"\n📋 === ARQUIVOS CRIADOS ===")
        for arquivo in arquivos_criados:
            tamanho = os.path.getsize(arquivo) / 1024  # KB
            print(f"   • {os.path.basename(arquivo)} ({tamanho:,.1f} KB)")
        
        print(f"\n🎯 === PRÓXIMOS PASSOS OTIMIZADOS ===")
        print(f"1. Fazer upload dos arquivos para o GitHub")
        print(f"2. Importar um arquivo por vez no Render")
        print(f"3. Aguardar apenas 30 segundos entre importações")
        print(f"4. Tempo total estimado: {tempo_estimado_min} minutos")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante divisão: {e}")
        return False

def estimar_tempo_importacao(total_registros, registros_por_lote=10, pausa_entre_lotes=2):
    """Estima tempo total de importação"""
    
    num_lotes = (total_registros + registros_por_lote - 1) // registros_por_lote
    tempo_processamento = num_lotes * 1  # 1 segundo por lote
    tempo_pausas = num_lotes * pausa_entre_lotes
    tempo_total_segundos = tempo_processamento + tempo_pausas
    
    horas = tempo_total_segundos // 3600
    minutos = (tempo_total_segundos % 3600) // 60
    
    return {
        'lotes': num_lotes,
        'tempo_total_segundos': tempo_total_segundos,
        'tempo_formatado': f"{horas}h {minutos}m" if horas > 0 else f"{minutos}m"
    }

def gerar_estrategia_importacao(total_registros):
    """Gera estratégia de importação baseada na performance real demonstrada"""
    
    print(f"\n🎯 === ESTRATÉGIA OTIMIZADA PARA {total_registros:,} REGISTROS ===")
    print(f"📊 Baseada na performance real: 5.570 registros em 5 segundos!")
    
    if total_registros <= 5000:
        print(f"✅ Volume PEQUENO - Importação direta ultra-rápida")
        print(f"   • Use script padrão sem divisão")
        print(f"   • Tempo estimado: 5-10 segundos")
        
    elif total_registros <= 15000:
        print(f"🚀 Volume MÉDIO - Performance excelente esperada")
        print(f"   • Divida em arquivos de 10.000 registros")
        print(f"   • Importe 1 arquivo por vez")
        print(f"   • Tempo estimado: 2-5 minutos total")
        
    elif total_registros <= 50000:
        print(f"⚡ Volume GRANDE - Otimização aproveitando alta performance")
        print(f"   • Divida em arquivos de 10.000 registros")
        print(f"   • Aguarde apenas 30 segundos entre importações")
        print(f"   • Performance comprovada do seu ambiente")
        print(f"   • Tempo estimado: 10-20 minutos total")
        
    else:
        print(f"💫 Volume MASSIVO - Estratégia de alta performance")
        print(f"   • Divida em arquivos de 15.000 registros")
        print(f"   • Importe durante qualquer horário (sistema rápido)")
        print(f"   • Monitore apenas por segurança")
        print(f"   • Tempo estimado: 30-60 minutos total")
        
        # Calcular arquivos necessários com 15.000 registros por arquivo
        registros_por_arquivo = 15000
        arquivos_necessarios = (total_registros + registros_por_arquivo - 1) // registros_por_arquivo
        print(f"   • Arquivos de {registros_por_arquivo:,} registros: {arquivos_necessarios}")
        
        # Nova estimativa baseada na performance real
        # 15.000 registros = ~15 segundos de processamento + 30s pausa = ~45s por arquivo
        tempo_por_arquivo_min = 1  # 1 minuto por arquivo (sendo conservador)
        tempo_total_min = arquivos_necessarios * tempo_por_arquivo_min
        
        print(f"   • Tempo por arquivo: ~{tempo_por_arquivo_min} minuto")
        print(f"   • Tempo total otimizado: ~{tempo_total_min} minutos")
        print(f"   • 🎯 MUITO mais rápido que estimativa anterior!")
    
    print(f"\n💡 === INSIGHTS DA PERFORMANCE ===")
    print(f"✅ Seu ambiente processou 5.570 cidades em 5 segundos")
    print(f"📈 Taxa: ~1.114 registros/segundo")
    print(f"🚀 Performance excepcional - configurações otimizadas aplicadas!")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("🔧 Uso: python dividir_planilha_grandes.py <arquivo.xlsx> [registros_por_arquivo]")
        print("\nExemplos:")
        print("  python dividir_planilha_grandes.py vinculos.xlsx")
        print("  python dividir_planilha_grandes.py vinculos.xlsx 15000")
        print("\n🚀 OTIMIZADO: Agora usa 10.000 registros por padrão (alta performance)")
        sys.exit(1)
    
    arquivo = sys.argv[1]
    registros_por_arquivo = int(sys.argv[2]) if len(sys.argv) > 2 else 10000  # Otimizado!
    
    # Gerar estratégia primeiro
    try:
        df_temp = pd.read_excel(arquivo, dtype=str)
        total = len(df_temp)
        gerar_estrategia_importacao(total)
        
        print(f"\n" + "="*50)
        resposta = input(f"\nConfirma divisão OTIMIZADA em arquivos de {registros_por_arquivo:,} registros? (s/N): ")
        
        if resposta.lower() in ['s', 'sim', 'y', 'yes']:
            sucesso = dividir_planilha_grande(arquivo, registros_por_arquivo)
            if sucesso:
                print(f"\n🎉 DIVISÃO OTIMIZADA CONCLUÍDA COM SUCESSO!")
            else:
                print(f"\n💥 ERRO NA DIVISÃO!")
        else:
            print(f"❌ Operação cancelada.")
            
    except Exception as e:
        print(f"❌ Erro ao analisar arquivo: {e}") 