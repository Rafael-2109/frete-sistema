#!/usr/bin/env python3
"""
🛡️ PREPARAÇÃO PARA IMPORTAÇÃO DE HISTÓRICO

Script para:
1. Fazer backup da base atual
2. Analisar dados existentes
3. Validar arquivo de importação
4. Fornecer estatísticas antes da importação
"""

import pandas as pd
from datetime import datetime
import sys
import os
import shutil

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.monitoramento.models import EntregaMonitorada

def fazer_backup_base():
    """Faz backup do banco de dados atual"""
    
    print("🛡️ FAZENDO BACKUP DA BASE ATUAL")
    print("=" * 50)
    
    # Localiza o arquivo do banco
    arquivos_db = []
    for arquivo in os.listdir('.'):
        if arquivo.endswith('.db'):
            arquivos_db.append(arquivo)
    
    if not arquivos_db:
        print("❌ Nenhum arquivo .db encontrado no diretório atual")
        return False
    
    # Usa o primeiro encontrado ou pede para escolher
    if len(arquivos_db) == 1:
        arquivo_db = arquivos_db[0]
    else:
        print("📁 Múltiplos arquivos .db encontrados:")
        for i, arquivo in enumerate(arquivos_db):
            print(f"   {i+1}. {arquivo}")
        
        try:
            escolha = int(input("Escolha o número do arquivo: ")) - 1
            arquivo_db = arquivos_db[escolha]
        except (ValueError, IndexError):
            print("❌ Escolha inválida")
            return False
    
    # Gera nome do backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    arquivo_backup = f"backup_pre_importacao_{timestamp}.db"
    
    try:
        shutil.copy2(arquivo_db, arquivo_backup)
        print(f"✅ Backup criado: {arquivo_backup}")
        print(f"   Tamanho: {os.path.getsize(arquivo_backup) / 1024 / 1024:.1f} MB")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar backup: {e}")
        return False

def analisar_base_atual():
    """Analisa a base atual de monitoramento"""
    
    print("\n📊 ANÁLISE DA BASE ATUAL")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        
        # Estatísticas gerais
        total_entregas = EntregaMonitorada.query.count()
        print(f"   Total de entregas:     {total_entregas}")
        
        if total_entregas == 0:
            print("   Base vazia - todas as importações serão novas")
            return
        
        # Por status
        entregues = EntregaMonitorada.query.filter_by(entregue=True).count()
        pendentes = total_entregas - entregues
        print(f"   Entregues:             {entregues}")
        print(f"   Pendentes:             {pendentes}")
        
        # Com dados específicos
        com_embarque = EntregaMonitorada.query.filter(EntregaMonitorada.data_embarque.isnot(None)).count()
        com_previsao = EntregaMonitorada.query.filter(EntregaMonitorada.data_entrega_prevista.isnot(None)).count()
        com_agenda = EntregaMonitorada.query.filter(EntregaMonitorada.data_agenda.isnot(None)).count()
        
        print(f"   Com data embarque:     {com_embarque}")
        print(f"   Com previsão entrega:  {com_previsao}")
        print(f"   Com agendamento:       {com_agenda}")
        
        # Transportadoras mais usadas
        transportadoras = db.session.query(
            EntregaMonitorada.transportadora, 
            db.func.count(EntregaMonitorada.id).label('count')
        ).filter(
            EntregaMonitorada.transportadora != '-',
            EntregaMonitorada.transportadora.isnot(None)
        ).group_by(EntregaMonitorada.transportadora).order_by(db.desc('count')).limit(5).all()
        
        if transportadoras:
            print(f"\n   Top 5 Transportadoras:")
            for transp, count in transportadoras:
                print(f"     {transp}: {count} entregas")

def validar_arquivo_importacao(arquivo_excel):
    """Valida arquivo de importação e mostra preview"""
    
    print(f"\n🔍 VALIDAÇÃO DO ARQUIVO: {arquivo_excel}")
    print("=" * 50)
    
    if not os.path.exists(arquivo_excel):
        print(f"❌ Arquivo não encontrado: {arquivo_excel}")
        return False
    
    try:
        # Carrega arquivo
        df = pd.read_excel(arquivo_excel)
        print(f"✅ Arquivo carregado com sucesso")
        print(f"   Linhas: {len(df)}")
        print(f"   Colunas: {len(df.columns)}")
        
        # Mostra colunas
        print(f"\n📋 Colunas encontradas:")
        for i, col in enumerate(df.columns):
            print(f"   {i+1:2d}. {col}")
        
        # Detecta possíveis mapeamentos
        colunas_importantes = {
            'numero_nf': ['numero_nf', 'nf', 'nota_fiscal', 'nf_numero'],
            'cliente': ['cliente', 'nome_cliente', 'razao_social'],
            'data_faturamento': ['data_faturamento', 'data_fatura', 'data_emissao'],
            'transportadora': ['transportadora', 'transportador']
        }
        
        print(f"\n🎯 Mapeamentos sugeridos:")
        mapeamentos_encontrados = 0
        for campo, opcoes in colunas_importantes.items():
            encontrado = False
            for opcao in opcoes:
                if opcao in df.columns:
                    print(f"   {campo:20} → {opcao}")
                    mapeamentos_encontrados += 1
                    encontrado = True
                    break
            if not encontrado:
                print(f"   {campo:20} → ❌ NÃO ENCONTRADO")
        
        # Verifica duplicatas por NF
        col_nf = None
        for opcao in colunas_importantes['numero_nf']:
            if opcao in df.columns:
                col_nf = opcao
                break
        
        if col_nf:
            duplicatas = df[col_nf].duplicated().sum()
            if duplicatas > 0:
                print(f"\n⚠️ ATENÇÃO: {duplicatas} NFs duplicadas encontradas!")
                print("   Apenas a primeira ocorrência será processada")
            else:
                print(f"\n✅ Nenhuma NF duplicada encontrada")
        
        # Preview dos dados
        print(f"\n👀 PREVIEW (primeiras 3 linhas):")
        print("-" * 80)
        for idx, row in df.head(3).iterrows():
            if col_nf:
                nf = str(row[col_nf])[:15]
                print(f"   Linha {idx+1}: NF {nf}")
            else:
                print(f"   Linha {idx+1}: {dict(row)}")
        
        return mapeamentos_encontrados >= 2  # Pelo menos NF + outro campo
        
    except Exception as e:
        print(f"❌ Erro ao validar arquivo: {e}")
        return False

def analisar_conflitos_potenciais(arquivo_excel):
    """Analisa potenciais conflitos entre dados históricos e atuais"""
    
    print(f"\n⚡ ANÁLISE DE CONFLITOS POTENCIAIS")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        
        # Carrega dados históricos
        df = pd.read_excel(arquivo_excel)
        
        # Detecta coluna de NF
        col_nf = None
        for opcao in ['numero_nf', 'nf', 'nota_fiscal', 'nf_numero']:
            if opcao in df.columns:
                col_nf = opcao
                break
        
        if not col_nf:
            print("❌ Coluna de NF não encontrada, não é possível analisar conflitos")
            return
        
        # Lista de NFs do histórico
        nfs_historico = set(str(nf).strip() for nf in df[col_nf] if pd.notna(nf))
        print(f"   NFs no histórico: {len(nfs_historico)}")
        
        # Lista de NFs na base atual
        nfs_atuais = set(nf for (nf,) in db.session.query(EntregaMonitorada.numero_nf).all())
        print(f"   NFs na base atual: {len(nfs_atuais)}")
        
        # Intersecção (conflitos)
        conflitos = nfs_historico.intersection(nfs_atuais)
        novas = nfs_historico - nfs_atuais
        
        print(f"   📊 RESULTADO:")
        print(f"     Novas (serão criadas):        {len(novas)}")
        print(f"     Conflitos (serão atualizadas): {len(conflitos)}")
        
        if conflitos:
            print(f"\n   🔄 Primeiros 10 conflitos:")
            for nf in list(conflitos)[:10]:
                entrega = EntregaMonitorada.query.filter_by(numero_nf=nf).first()
                status = "ENTREGUE" if entrega.entregue else "PENDENTE"
                embarque = "SIM" if entrega.data_embarque else "NÃO"
                print(f"     {nf:15} | Status: {status:8} | Embarque: {embarque}")
            
            if len(conflitos) > 10:
                print(f"     ... e mais {len(conflitos) - 10} conflitos")

def main():
    """Função principal"""
    
    if len(sys.argv) < 2:
        print("🛡️ PREPARAÇÃO PARA IMPORTAÇÃO DE HISTÓRICO")
        print()
        print("USO:")
        print("python preparar_importacao_historico.py <arquivo.xlsx>")
        print()
        print("O script irá:")
        print("1. Fazer backup da base atual")
        print("2. Analisar dados existentes") 
        print("3. Validar arquivo de importação")
        print("4. Mostrar potenciais conflitos")
        return
    
    arquivo = sys.argv[1]
    
    print("🛡️ PREPARAÇÃO PARA IMPORTAÇÃO DE HISTÓRICO")
    print("=" * 60)
    print(f"Arquivo: {arquivo}")
    print("=" * 60)
    
    # 1. Backup
    if not fazer_backup_base():
        print("\n❌ Falha no backup. Abortando preparação.")
        return
    
    # 2. Análise da base atual
    analisar_base_atual()
    
    # 3. Validação do arquivo
    if not validar_arquivo_importacao(arquivo):
        print("\n❌ Arquivo inválido ou com problemas. Verifique e tente novamente.")
        return
    
    # 4. Análise de conflitos
    analisar_conflitos_potenciais(arquivo)
    
    print("\n" + "=" * 60)
    print("✅ PREPARAÇÃO CONCLUÍDA!")
    print("=" * 60)
    print("📋 Próximos passos:")
    print("1. Revisar as informações acima")
    print("2. Se tudo estiver correto, execute:")
    print(f"   python importar_historico_monitoramento.py {arquivo} visualizar")
    print("3. Depois execute:")
    print(f"   python importar_historico_monitoramento.py {arquivo} importar")
    print()
    print("💡 DICA: Em caso de problemas, restaure o backup criado.")

if __name__ == "__main__":
    main() 