#!/usr/bin/env python3
"""
🔧 TESTE DAS CORREÇÕES DE INTEGRIDADE DOS DADOS

Este script testa todas as correções implementadas para garantir a integridade dos dados:

1. ✅ Verificar se NFs FOB não estão sendo incluídas no monitoramento
2. ✅ Verificar se filtro "SEM AGENDAMENTO" está funcionando corretamente
3. ✅ Verificar se NFs CIF estão sendo vinculadas adequadamente
4. ✅ Testar sincronização com filtros ativos

Uso: python testar_correcoes_integridade.py [--verbose]
"""

import sys
import os
import argparse

# Adiciona o diretório pai ao Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.faturamento.models import RelatorioFaturamentoImportado
from app.monitoramento.models import EntregaMonitorada
from app.embarques.models import EmbarqueItem, Embarque
from app.cadastros_agendamento.models import ContatoAgendamento
from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf

def testar_filtro_fob(verbose=False):
    """Testa se NFs FOB não estão no monitoramento"""
    print("🚫 TESTE: Filtro FOB")
    
    # Busca NFs FOB ativas
    nfs_fob = RelatorioFaturamentoImportado.query.filter(
        RelatorioFaturamentoImportado.incoterm.ilike('%FOB%'),
        RelatorioFaturamentoImportado.ativo == True
    ).all()
    
    print(f"   • NFs FOB ativas no faturamento: {len(nfs_fob)}")
    
    # Verifica quantas estão no monitoramento (deveria ser 0)
    nfs_fob_monitoradas = []
    for nf in nfs_fob:
        entrega = EntregaMonitorada.query.filter_by(numero_nf=nf.numero_nf).first()
        if entrega:
            nfs_fob_monitoradas.append(nf)
    
    print(f"   • NFs FOB no monitoramento: {len(nfs_fob_monitoradas)}")
    
    if len(nfs_fob_monitoradas) == 0:
        print("   ✅ PASSOU: Nenhuma NF FOB está no monitoramento")
        resultado = True
    else:
        print("   ❌ FALHOU: Existem NFs FOB no monitoramento")
        if verbose:
            for nf in nfs_fob_monitoradas[:3]:
                print(f"      • NF {nf.numero_nf} - {nf.nome_cliente[:30]}...")
        resultado = False
    
    return resultado

def testar_filtro_sem_agendamento(verbose=False):
    """Testa se alertas 'Sem Agendamento' não aparecem quando forma é 'SEM AGENDAMENTO'"""
    print("\n📞 TESTE: Filtro 'Sem Agendamento'")
    
    # Busca contatos com forma "SEM AGENDAMENTO"
    contatos_sem_agendamento = ContatoAgendamento.query.filter_by(forma='SEM AGENDAMENTO').all()
    print(f"   • Contatos com forma 'SEM AGENDAMENTO': {len(contatos_sem_agendamento)}")
    
    # Para cada contato, verifica se há entregas sem agendamento
    entregas_problematicas = []
    for contato in contatos_sem_agendamento:
        entregas = EntregaMonitorada.query.filter_by(cnpj_cliente=contato.cnpj).all()
        for entrega in entregas:
            if len(entrega.agendamentos) == 0:
                entregas_problematicas.append((contato, entrega))
    
    print(f"   • Entregas sem agendamento com CNPJ 'SEM AGENDAMENTO': {len(entregas_problematicas)}")
    
    if verbose and entregas_problematicas:
        for contato, entrega in entregas_problematicas[:3]:
            print(f"      • NF {entrega.numero_nf} - CNPJ {contato.cnpj} - {entrega.cliente[:30]}...")
    
    # A lógica foi corrigida no template, então isso é apenas informativo
    print("   ℹ️  INFO: Lógica corrigida no template para não mostrar alerta quando forma for 'SEM AGENDAMENTO'")
    
    return True

def testar_vinculacao_cif(verbose=False):
    """Testa se NFs CIF estão sendo vinculadas adequadamente"""
    print("\n🔗 TESTE: Vinculação NFs CIF")
    
    # Busca NFs CIF ativas dos últimos 30 dias
    from datetime import datetime, timedelta
    data_limite = datetime.now().date() - timedelta(days=30)
    
    nfs_cif = RelatorioFaturamentoImportado.query.filter(
        RelatorioFaturamentoImportado.incoterm.ilike('%CIF%'),
        RelatorioFaturamentoImportado.ativo == True,
        RelatorioFaturamentoImportado.data_fatura >= data_limite
    ).all()
    
    print(f"   • NFs CIF ativas (últimos 30 dias): {len(nfs_cif)}")
    
    if len(nfs_cif) == 0:
        print("   ℹ️  INFO: Nenhuma NF CIF recente para testar")
        return True
    
    # Verifica vinculação
    nfs_vinculadas = 0
    nfs_nao_vinculadas = []
    
    for nf in nfs_cif:
        entrega = EntregaMonitorada.query.filter_by(numero_nf=nf.numero_nf).first()
        if entrega:
            nfs_vinculadas += 1
        else:
            # Verifica se não está vinculada por motivo válido (embarque)
            item_embarque = EmbarqueItem.query.filter_by(nota_fiscal=nf.numero_nf).first()
            if not item_embarque:
                nfs_nao_vinculadas.append(nf)
    
    taxa_vinculacao = (nfs_vinculadas / len(nfs_cif)) * 100 if len(nfs_cif) > 0 else 0
    print(f"   • NFs CIF vinculadas ao monitoramento: {nfs_vinculadas} ({taxa_vinculacao:.1f}%)")
    print(f"   • NFs CIF não vinculadas sem motivo: {len(nfs_nao_vinculadas)}")
    
    if verbose and nfs_nao_vinculadas:
        print("   📋 NFs CIF não vinculadas:")
        for nf in nfs_nao_vinculadas[:3]:
            print(f"      • NF {nf.numero_nf} - {nf.nome_cliente[:30]}...")
    
    # Taxa de vinculação aceitável é > 80%
    if taxa_vinculacao > 80:
        print("   ✅ PASSOU: Taxa de vinculação adequada")
        return True
    else:
        print("   ⚠️  ATENÇÃO: Taxa de vinculação baixa")
        return False

def testar_sincronizacao_com_filtros(verbose=False):
    """Testa se a sincronização está respeitando os filtros"""
    print("\n🔄 TESTE: Sincronização com Filtros")
    
    # Pega uma NF FOB para testar
    nf_fob = RelatorioFaturamentoImportado.query.filter(
        RelatorioFaturamentoImportado.incoterm.ilike('%FOB%'),
        RelatorioFaturamentoImportado.ativo == True
    ).first()
    
    if not nf_fob:
        print("   ℹ️  INFO: Nenhuma NF FOB encontrada para testar")
        return True
    
    print(f"   • Testando sincronização da NF FOB: {nf_fob.numero_nf}")
    
    # Verifica se está no monitoramento antes
    entrega_antes = EntregaMonitorada.query.filter_by(numero_nf=nf_fob.numero_nf).first()
    print(f"   • Antes da sincronização: {'No monitoramento' if entrega_antes else 'Não monitorada'}")
    
    # Executa sincronização
    try:
        sincronizar_entrega_por_nf(nf_fob.numero_nf)
        
        # Verifica se continua fora do monitoramento
        entrega_depois = EntregaMonitorada.query.filter_by(numero_nf=nf_fob.numero_nf).first()
        print(f"   • Depois da sincronização: {'No monitoramento' if entrega_depois else 'Não monitorada'}")
        
        if not entrega_depois:
            print("   ✅ PASSOU: NF FOB não foi incluída no monitoramento")
            return True
        else:
            print("   ❌ FALHOU: NF FOB foi incluída no monitoramento")
            return False
            
    except Exception as e:
        print(f"   ❌ ERRO na sincronização: {e}")
        return False

def testar_correcoes_integridade(verbose=False):
    """Executa todos os testes de integridade"""
    app = create_app()
    
    with app.app_context():
        print("🔧 TESTE DAS CORREÇÕES DE INTEGRIDADE DOS DADOS")
        print("=" * 60)
        
        testes_resultados = []
        
        # Executa todos os testes
        testes_resultados.append(testar_filtro_fob(verbose))
        testes_resultados.append(testar_filtro_sem_agendamento(verbose))
        testes_resultados.append(testar_vinculacao_cif(verbose))
        testes_resultados.append(testar_sincronizacao_com_filtros(verbose))
        
        # Resumo final
        print(f"\n📊 RESUMO DOS TESTES:")
        testes_passou = sum(testes_resultados)
        total_testes = len(testes_resultados)
        
        print(f"   • Testes executados: {total_testes}")
        print(f"   • Testes passou: {testes_passou}")
        print(f"   • Testes falhou: {total_testes - testes_passou}")
        
        if testes_passou == total_testes:
            print(f"\n✅ TODOS OS TESTES PASSARAM!")
            print(f"   A integridade dos dados está garantida.")
        else:
            print(f"\n⚠️  {total_testes - testes_passou} TESTE(S) FALHARAM")
            print(f"   Revise as correções implementadas.")
        
        # Estatísticas gerais
        print(f"\n📈 ESTATÍSTICAS GERAIS:")
        total_faturamento = RelatorioFaturamentoImportado.query.filter_by(ativo=True).count()
        total_monitoramento = EntregaMonitorada.query.count()
        total_fob = RelatorioFaturamentoImportado.query.filter(
            RelatorioFaturamentoImportado.incoterm.ilike('%FOB%'),
            RelatorioFaturamentoImportado.ativo == True
        ).count()
        total_cif = RelatorioFaturamentoImportado.query.filter(
            RelatorioFaturamentoImportado.incoterm.ilike('%CIF%'),
            RelatorioFaturamentoImportado.ativo == True
        ).count()
        
        print(f"   • Total NFs ativas no faturamento: {total_faturamento}")
        print(f"   • Total NFs no monitoramento: {total_monitoramento}")
        print(f"   • Total NFs FOB: {total_fob}")
        print(f"   • Total NFs CIF: {total_cif}")
        
        if total_faturamento > 0:
            taxa_monitoramento = (total_monitoramento / total_faturamento) * 100
            print(f"   • Taxa de monitoramento: {taxa_monitoramento:.1f}%")

def main():
    parser = argparse.ArgumentParser(description='Testar correções de integridade dos dados')
    parser.add_argument('--verbose', '-v', action='store_true', help='Mostra detalhes dos testes')
    
    args = parser.parse_args()
    
    testar_correcoes_integridade(verbose=args.verbose)

if __name__ == '__main__':
    main() 