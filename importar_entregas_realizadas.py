#!/usr/bin/env python3
"""
📦 IMPORTAR ENTREGAS REALIZADAS VIA EXCEL
Script para atualizar datas de entrega e status das NFs
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.monitoramento.models import EntregaMonitorada
from sqlalchemy import text


def importar_entregas_realizadas(arquivo_excel: str):
    """Importa entregas realizadas do Excel"""
    print("\n" + "="*80)
    print("📦 IMPORTANDO ENTREGAS REALIZADAS")
    print("="*80 + "\n")
    
    # Verificar arquivo
    if not os.path.exists(arquivo_excel):
        print(f"❌ Arquivo não encontrado: {arquivo_excel}")
        return False
    
    app = create_app()
    
    with app.app_context():
        try:
            # Ler Excel
            print(f"📄 Lendo arquivo: {arquivo_excel}")
            df = pd.read_excel(arquivo_excel)
            
            # Verificar colunas necessárias
            colunas_necessarias = ['NF', 'Data Entrega']
            colunas_faltando = [col for col in colunas_necessarias if col not in df.columns]
            
            if colunas_faltando:
                print(f"❌ Colunas faltando no Excel: {colunas_faltando}")
                print(f"📋 Colunas encontradas: {list(df.columns)}")
                return False
            
            # Converter coluna NF para string
            df['NF'] = df['NF'].astype(str).str.strip()
            
            # Remover linhas vazias
            df = df[df['NF'].notna() & (df['NF'] != '')]
            
            print(f"📊 Total de registros no Excel: {len(df)}")
            
            # Estatísticas
            total_processar = len(df)
            atualizadas = 0
            nao_encontradas = 0
            ja_entregues = 0
            erros = 0
            
            # Processar cada NF
            for idx, row in df.iterrows():
                try:
                    numero_nf = str(row['NF']).strip()
                    data_entrega = pd.to_datetime(row['Data Entrega'])
                    
                    # Se só tem data, adicionar hora 12:00
                    if data_entrega.hour == 0 and data_entrega.minute == 0:
                        data_entrega = data_entrega.replace(hour=12, minute=0)
                    
                    # Buscar entrega
                    entrega = db.session.query(EntregaMonitorada).filter(
                        EntregaMonitorada.numero_nf == numero_nf
                    ).first()
                    
                    if not entrega:
                        print(f"❌ NF {numero_nf} não encontrada no sistema")
                        nao_encontradas += 1
                        continue
                    
                    # Verificar se já está entregue
                    if entrega.entregue and entrega.data_hora_entrega_realizada:
                        print(f"ℹ️ NF {numero_nf} já estava entregue em {entrega.data_hora_entrega_realizada}")
                        ja_entregues += 1
                        continue
                    
                    # Atualizar entrega
                    entrega.data_hora_entrega_realizada = data_entrega
                    entrega.entregue = True
                    entrega.status_finalizacao = 'Entregue'
                    entrega.finalizado_em = datetime.now()
                    entrega.finalizado_por = 'Importação Excel'
                    
                    # Se não tem data prevista, usar a data de entrega
                    if not entrega.data_entrega_prevista:
                        entrega.data_entrega_prevista = data_entrega.date()
                    
                    db.session.commit()
                    
                    print(f"✅ NF {numero_nf} - Entregue em {data_entrega.strftime('%d/%m/%Y %H:%M')}")
                    atualizadas += 1
                    
                    # Commit a cada 50 registros
                    if atualizadas % 50 == 0:
                        db.session.commit()
                        print(f"💾 {atualizadas} entregas atualizadas...")
                    
                except Exception as e:
                    print(f"❌ Erro ao processar NF {row.get('NF', 'N/A')}: {e}")
                    erros += 1
                    db.session.rollback()
            
            # Commit final
            db.session.commit()
            
            # Resumo
            print("\n" + "="*80)
            print("📊 RESUMO DA IMPORTAÇÃO")
            print("="*80)
            print(f"📋 Total no Excel: {total_processar}")
            print(f"✅ Atualizadas com sucesso: {atualizadas}")
            print(f"ℹ️ Já estavam entregues: {ja_entregues}")
            print(f"❌ NFs não encontradas: {nao_encontradas}")
            print(f"❌ Erros no processamento: {erros}")
            print(f"📈 Taxa de sucesso: {(atualizadas/total_processar*100):.1f}%")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO GERAL: {e}")
            import traceback
            traceback.print_exc()
            return False


def gerar_template_excel():
    """Gera template Excel de exemplo"""
    print("\n📄 Gerando template de exemplo...")
    
    # Criar DataFrame de exemplo
    exemplo = pd.DataFrame({
        'NF': ['123456', '123457', '123458'],
        'Data Entrega': ['25/06/2025', '25/06/2025 14:30', '24/06/2025']
    })
    
    # Salvar Excel
    arquivo_template = 'template_entregas_realizadas.xlsx'
    exemplo.to_excel(arquivo_template, index=False)
    
    print(f"✅ Template salvo em: {arquivo_template}")
    print("\nColunas necessárias:")
    print("- NF: Número da nota fiscal (6 dígitos)")
    print("- Data Entrega: Data/hora da entrega (formato DD/MM/AAAA ou DD/MM/AAAA HH:MM)")
    print("\nSe não informar hora, será usado 12:00 automaticamente")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Importar entregas realizadas via Excel')
    parser.add_argument('arquivo', nargs='?', help='Arquivo Excel com as entregas')
    parser.add_argument('--template', action='store_true', help='Gerar template de exemplo')
    
    args = parser.parse_args()
    
    print(f"🕐 Início: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    if args.template:
        gerar_template_excel()
    elif args.arquivo:
        sucesso = importar_entregas_realizadas(args.arquivo)
        if sucesso:
            print("\n🎉 IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
        else:
            print("\n❌ Importação falhou. Verifique os erros acima.")
    else:
        print("\n❌ Uso incorreto!")
        print("\nPara importar:")
        print("  python importar_entregas_realizadas.py arquivo.xlsx")
        print("\nPara gerar template:")
        print("  python importar_entregas_realizadas.py --template")
    
    print(f"\n🕐 Fim: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}") 