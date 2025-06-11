#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para Sincronizar NFs Órfãs
=================================

Este script identifica NFs que estão no faturamento mas não estão
no monitoramento e faz a sincronização correta.
"""

import sys
import os
from datetime import datetime

# Adiciona o diretório do app ao path
sys.path.append(os.path.dirname(__file__))

# Configura Flask
from app import create_app, db
from app.faturamento.models import RelatorioFaturamentoImportado
from app.monitoramento.models import EntregaMonitorada
from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf

def verificar_nfs_orphas():
    """Identifica NFs que estão no faturamento mas não no monitoramento"""
    print("🔍 === VERIFICANDO NFS ÓRFÃS ===")
    print(f"⏰ Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # Busca todas as NFs do faturamento
    nfs_faturamento = RelatorioFaturamentoImportado.query.all()
    print(f"📊 Total de NFs no faturamento: {len(nfs_faturamento)}")
    
    # Busca todas as NFs no monitoramento
    nfs_monitoramento = EntregaMonitorada.query.all()
    print(f"📊 Total de NFs no monitoramento: {len(nfs_monitoramento)}")
    
    # Identifica NFs órfãs
    nfs_fat_set = {nf.numero_nf for nf in nfs_faturamento}
    nfs_mon_set = {nf.numero_nf for nf in nfs_monitoramento}
    
    nfs_orphas = nfs_fat_set - nfs_mon_set
    
    print(f"🔍 NFs órfãs (no faturamento, mas não no monitoramento): {len(nfs_orphas)}")
    print()
    
    if nfs_orphas:
        print("📋 **LISTA DE NFs ÓRFÃS:**")
        for nf in sorted(nfs_orphas):
            nf_fat = RelatorioFaturamentoImportado.query.filter_by(numero_nf=nf).first()
            data_fat = nf_fat.data_fatura.strftime('%d/%m/%Y') if nf_fat.data_fatura else 'N/A'
            print(f"   📄 NF: {nf} - Cliente: {nf_fat.nome_cliente} - Data: {data_fat}")
        print()
    
    return list(nfs_orphas)

def sincronizar_nfs_orphas(nfs_orphas, confirmar=True):
    """Sincroniza as NFs órfãs com o monitoramento"""
    if not nfs_orphas:
        print("✅ **NENHUMA NF ÓRFÃ ENCONTRADA!**")
        return
    
    if confirmar:
        print(f"🔧 === INICIANDO SINCRONIZAÇÃO DE {len(nfs_orphas)} NFs ===")
        resposta = input(f"Deseja sincronizar {len(nfs_orphas)} NFs órfãs? (s/n): ")
        if resposta.lower() != 's':
            print("❌ Sincronização cancelada pelo usuário")
            return
    
    sucesso = 0
    erros = 0
    
    print("🔄 **PROCESSANDO SINCRONIZAÇÃO:**")
    
    for i, numero_nf in enumerate(nfs_orphas, 1):
        try:
            print(f"   📄 {i}/{len(nfs_orphas)}: NF {numero_nf}...", end=" ")
            
            # Faz a sincronização
            sincronizar_entrega_por_nf(numero_nf)
            
            print("✅ Sincronizada")
            sucesso += 1
            
        except Exception as e:
            print(f"❌ Erro: {str(e)}")
            erros += 1
    
    print()
    print(f"📊 **RESULTADO DA SINCRONIZAÇÃO:**")
    print(f"   ✅ Sucesso: {sucesso}")
    print(f"   ❌ Erros: {erros}")
    print(f"   📊 Total: {len(nfs_orphas)}")
    
    if sucesso > 0:
        db.session.commit()
        print(f"💾 Alterações salvas no banco de dados")

def verificar_pos_sincronizacao():
    """Verifica o status após a sincronização"""
    print("\n🔍 === VERIFICAÇÃO PÓS-SINCRONIZAÇÃO ===")
    
    # Busca novamente as contagens
    nfs_faturamento = RelatorioFaturamentoImportado.query.count()
    nfs_monitoramento = EntregaMonitorada.query.count()
    
    print(f"📊 NFs no faturamento: {nfs_faturamento}")
    print(f"📊 NFs no monitoramento: {nfs_monitoramento}")
    
    # Verifica se ainda há órfãs
    nfs_fat_set = {nf.numero_nf for nf in RelatorioFaturamentoImportado.query.all()}
    nfs_mon_set = {nf.numero_nf for nf in EntregaMonitorada.query.all()}
    nfs_orphas_restantes = nfs_fat_set - nfs_mon_set
    
    if nfs_orphas_restantes:
        print(f"⚠️ Ainda há {len(nfs_orphas_restantes)} NFs órfãs:")
        for nf in sorted(list(nfs_orphas_restantes)[:5]):  # Mostra só as primeiras 5
            print(f"   📄 {nf}")
        if len(nfs_orphas_restantes) > 5:
            print(f"   ... e mais {len(nfs_orphas_restantes)-5}")
    else:
        print("✅ **TODAS AS NFs ESTÃO SINCRONIZADAS!**")

def listar_nfs_recentes(limite=10):
    """Lista as NFs mais recentemente importadas"""
    print(f"\n📋 === {limite} NFs MAIS RECENTES DO FATURAMENTO ===")
    
    nfs_recentes = RelatorioFaturamentoImportado.query.order_by(
        RelatorioFaturamentoImportado.id.desc()
    ).limit(limite).all()
    
    for nf in nfs_recentes:
        data_fat = nf.data_fatura.strftime('%d/%m/%Y') if nf.data_fatura else 'N/A'
        
        # Verifica se está no monitoramento
        no_monitoramento = EntregaMonitorada.query.filter_by(numero_nf=nf.numero_nf).first()
        status = "✅ Sync" if no_monitoramento else "❌ Órfã"
        
        print(f"   📄 NF: {nf.numero_nf} - {nf.nome_cliente} - {data_fat} - {status}")

if __name__ == "__main__":
    # Cria o contexto da aplicação
    app = create_app()
    with app.app_context():
        print("🔄 === SINCRONIZAÇÃO DE NFs ÓRFÃS ===")
        print("📅 Data:", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        print()
        
        try:
            # 1. Lista NFs recentes para contexto
            listar_nfs_recentes(10)
            
            # 2. Identifica NFs órfãs
            nfs_orphas = verificar_nfs_orphas()
            
            # 3. Sincroniza se houver órfãs
            if nfs_orphas:
                sincronizar_nfs_orphas(nfs_orphas, confirmar=False)  # Auto-confirma
                
                # 4. Verifica resultado
                verificar_pos_sincronizacao()
            
            print("\n🎉 **PROCESSO CONCLUÍDO!**")
            
        except Exception as e:
            print(f"❌ Erro durante execução: {e}")
            import traceback
            traceback.print_exc() 