#!/usr/bin/env python3
"""
Script para analisar o impacto de itens cancelados na criação de novos embarques
- Analisa o fluxo: criar embarque → preencher NF → cancelar item
- Identifica dados que podem estar "sobrando" e causando conflitos
- Foca em campos essenciais para criação de embarques
"""

import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido
from app.embarques.models import Embarque, EmbarqueItem

def analisar_fluxo_completo():
    """Analisa o fluxo completo de criação, preenchimento e cancelamento"""
    app = create_app()
    
    with app.app_context():
        print(f"🔍 ANÁLISE DE IMPACTO - ITENS CANCELADOS")
        print("=" * 60)
        print(f"Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print()
        
        print("📋 FLUXO ANALISADO:")
        print("1. Criar embarque (pedido fica COTADO)")
        print("2. Preencher NF (pedido fica FATURADO)")
        print("3. Cancelar item do embarque")
        print("4. Tentar criar novo embarque com mesmo pedido")
        print()
        
        # 1. Busca itens cancelados que têm dados "sobrando"
        print("🔍 ANALISANDO ITENS CANCELADOS...")
        
        itens_cancelados = EmbarqueItem.query.filter_by(status='cancelado').all()
        
        if not itens_cancelados:
            print("✅ Nenhum item cancelado encontrado")
            return
        
        print(f"📦 Encontrados {len(itens_cancelados)} itens cancelados")
        print()
        
        problemas_encontrados = []
        
        for item in itens_cancelados:
            problema = {
                'item_id': item.id,
                'embarque_id': item.embarque_id,
                'pedido': item.pedido,
                'separacao_lote_id': item.separacao_lote_id,
                'dados_sobrando': []
            }
            
            # Verifica dados que podem estar "sobrando"
            
            # 1. NF preenchida em item cancelado
            if item.nota_fiscal and item.nota_fiscal.strip():
                problema['dados_sobrando'].append(f"NF: {item.nota_fiscal}")
            
            # 2. Cotação vinculada em item cancelado
            if item.cotacao_id:
                problema['dados_sobrando'].append(f"cotacao_id: {item.cotacao_id}")
            
            # 3. Dados de tabela preenchidos em item cancelado
            if item.tabela_nome_tabela:
                problema['dados_sobrando'].append(f"tabela: {item.tabela_nome_tabela}")
            
            # 4. Modalidade preenchida em item cancelado
            if item.modalidade:
                problema['dados_sobrando'].append(f"modalidade: {item.modalidade}")
            
            # 5. Verifica se o pedido correspondente tem dados inconsistentes
            if item.separacao_lote_id:
                pedido = Pedido.query.filter_by(separacao_lote_id=item.separacao_lote_id).first()
                if pedido:
                    # Verifica se pedido ainda tem cotacao_id mesmo com item cancelado
                    if pedido.cotacao_id:
                        problema['dados_sobrando'].append(f"pedido.cotacao_id: {pedido.cotacao_id}")
                    
                    # Verifica se pedido ainda tem transportadora mesmo com item cancelado
                    if pedido.transportadora:
                        problema['dados_sobrando'].append(f"pedido.transportadora: {pedido.transportadora}")
                    
                    # Verifica se pedido ainda tem NF mesmo com item cancelado
                    if pedido.nf:
                        problema['dados_sobrando'].append(f"pedido.nf: {pedido.nf}")
                    
                    # Verifica status do pedido
                    status_calculado = pedido.status_calculado
                    if status_calculado != 'ABERTO':
                        problema['dados_sobrando'].append(f"pedido.status: {status_calculado} (deveria ser ABERTO)")
            
            if problema['dados_sobrando']:
                problemas_encontrados.append(problema)
        
        # 2. Analisa problemas encontrados
        if not problemas_encontrados:
            print("✅ Nenhum problema encontrado com itens cancelados!")
            return
        
        print(f"⚠️  PROBLEMAS ENCONTRADOS: {len(problemas_encontrados)}")
        print()
        
        # Categoriza problemas por tipo
        problemas_por_tipo = {
            'nf_sobrando': [],
            'cotacao_sobrando': [],
            'tabela_sobrando': [],
            'pedido_inconsistente': []
        }
        
        for problema in problemas_encontrados:
            for dado in problema['dados_sobrando']:
                if 'NF:' in dado:
                    problemas_por_tipo['nf_sobrando'].append(problema)
                elif 'cotacao_id:' in dado:
                    problemas_por_tipo['cotacao_sobrando'].append(problema)
                elif 'tabela:' in dado or 'modalidade:' in dado:
                    problemas_por_tipo['tabela_sobrando'].append(problema)
                elif 'pedido.' in dado:
                    problemas_por_tipo['pedido_inconsistente'].append(problema)
        
        # 3. Relatório detalhado por categoria
        print("📊 ANÁLISE POR CATEGORIA:")
        print()
        
        # NFs sobrando
        if problemas_por_tipo['nf_sobrando']:
            print(f"🔴 NFs SOBRANDO EM ITENS CANCELADOS: {len(problemas_por_tipo['nf_sobrando'])}")
            print("   IMPACTO: NFs ficam 'presas' em itens cancelados, podem causar conflitos")
            for problema in problemas_por_tipo['nf_sobrando'][:5]:  # Mostra apenas 5 exemplos
                nf_data = [d for d in problema['dados_sobrando'] if 'NF:' in d][0]
                print(f"   • Item {problema['item_id']}: {nf_data}")
            if len(problemas_por_tipo['nf_sobrando']) > 5:
                print(f"   ... e mais {len(problemas_por_tipo['nf_sobrando']) - 5} casos")
            print()
        
        # Cotações sobrando
        if problemas_por_tipo['cotacao_sobrando']:
            print(f"🔴 COTAÇÕES SOBRANDO EM ITENS CANCELADOS: {len(problemas_por_tipo['cotacao_sobrando'])}")
            print("   IMPACTO: Cotações ficam vinculadas a itens cancelados, podem causar conflitos")
            for problema in problemas_por_tipo['cotacao_sobrando'][:5]:
                cotacao_data = [d for d in problema['dados_sobrando'] if 'cotacao_id:' in d][0]
                print(f"   • Item {problema['item_id']}: {cotacao_data}")
            if len(problemas_por_tipo['cotacao_sobrando']) > 5:
                print(f"   ... e mais {len(problemas_por_tipo['cotacao_sobrando']) - 5} casos")
            print()
        
        # Dados de tabela sobrando
        if problemas_por_tipo['tabela_sobrando']:
            print(f"🔴 DADOS DE TABELA SOBRANDO: {len(problemas_por_tipo['tabela_sobrando'])}")
            print("   IMPACTO: Dados de tabela ficam em itens cancelados, podem causar confusão")
            for problema in problemas_por_tipo['tabela_sobrando'][:5]:
                tabela_data = [d for d in problema['dados_sobrando'] if 'tabela:' in d or 'modalidade:' in d]
                print(f"   • Item {problema['item_id']}: {', '.join(tabela_data)}")
            if len(problemas_por_tipo['tabela_sobrando']) > 5:
                print(f"   ... e mais {len(problemas_por_tipo['tabela_sobrando']) - 5} casos")
            print()
        
        # Pedidos inconsistentes
        if problemas_por_tipo['pedido_inconsistente']:
            print(f"🔴 PEDIDOS INCONSISTENTES: {len(problemas_por_tipo['pedido_inconsistente'])}")
            print("   IMPACTO: Pedidos não voltaram para status ABERTO após cancelamento")
            for problema in problemas_por_tipo['pedido_inconsistente'][:5]:
                pedido_data = [d for d in problema['dados_sobrando'] if 'pedido.' in d]
                print(f"   • Pedido {problema['pedido']}: {', '.join(pedido_data)}")
            if len(problemas_por_tipo['pedido_inconsistente']) > 5:
                print(f"   ... e mais {len(problemas_por_tipo['pedido_inconsistente']) - 5} casos")
            print()
        
        return problemas_encontrados

def analisar_impacto_cotacao():
    """Analisa especificamente o impacto na criação de novos embarques"""
    app = create_app()
    
    with app.app_context():
        print("🎯 ANÁLISE DE IMPACTO NA COTAÇÃO")
        print("=" * 40)
        
        # Busca pedidos que podem estar com problemas para cotação
        pedidos_problematicos = []
        
        # 1. Pedidos que têm cotacao_id mas não estão em embarques ativos
        pedidos_com_cotacao = Pedido.query.filter(Pedido.cotacao_id.isnot(None)).all()
        
        for pedido in pedidos_com_cotacao:
            # Verifica se está em algum embarque ativo
            item_ativo = EmbarqueItem.query.join(Embarque).filter(
                EmbarqueItem.separacao_lote_id == pedido.separacao_lote_id,
                EmbarqueItem.status == 'ativo',
                Embarque.status == 'ativo'
            ).first()
            
            if not item_ativo:
                # Pedido tem cotacao_id mas não está em embarque ativo
                # Pode estar em item cancelado
                item_cancelado = EmbarqueItem.query.filter(
                    EmbarqueItem.separacao_lote_id == pedido.separacao_lote_id,
                    EmbarqueItem.status == 'cancelado'
                ).first()
                
                if item_cancelado:
                    pedidos_problematicos.append({
                        'pedido': pedido.num_pedido,
                        'cotacao_id': pedido.cotacao_id,
                        'transportadora': pedido.transportadora,
                        'status': pedido.status_calculado,
                        'problema': 'Tem cotacao_id mas está em item cancelado',
                        'item_cancelado_id': item_cancelado.id,
                        'embarque_id': item_cancelado.embarque_id
                    })
        
        if pedidos_problematicos:
            print(f"⚠️  {len(pedidos_problematicos)} PEDIDOS PROBLEMÁTICOS PARA COTAÇÃO:")
            print()
            
            for problema in pedidos_problematicos[:10]:  # Mostra 10 exemplos
                print(f"📋 Pedido {problema['pedido']}:")
                print(f"   • Status: {problema['status']}")
                print(f"   • Cotação ID: {problema['cotacao_id']}")
                print(f"   • Transportadora: {problema['transportadora'] or 'N/A'}")
                print(f"   • Problema: {problema['problema']}")
                print(f"   • Item cancelado: {problema['item_cancelado_id']} (Embarque: {problema['embarque_id']})")
                print()
            
            if len(pedidos_problematicos) > 10:
                print(f"... e mais {len(pedidos_problematicos) - 10} casos similares")
        else:
            print("✅ Nenhum pedido problemático encontrado para cotação")
        
        return pedidos_problematicos

def gerar_solucoes(problemas_encontrados, pedidos_problematicos):
    """Gera soluções para os problemas encontrados"""
    print("\n💡 SOLUÇÕES RECOMENDADAS:")
    print("=" * 40)
    
    if not problemas_encontrados and not pedidos_problematicos:
        print("✅ Nenhuma solução necessária - sistema está limpo!")
        return
    
    print("🔧 CORREÇÕES NECESSÁRIAS:")
    print()
    
    # 1. Limpeza de itens cancelados
    if problemas_encontrados:
        print("1️⃣ LIMPEZA DE ITENS CANCELADOS:")
        print("   • Remover NFs de itens cancelados")
        print("   • Limpar cotacao_id de itens cancelados")
        print("   • Limpar dados de tabela de itens cancelados")
        print("   • Resetar modalidade de itens cancelados")
        print()
    
    # 2. Correção de pedidos inconsistentes
    if pedidos_problematicos:
        print("2️⃣ CORREÇÃO DE PEDIDOS INCONSISTENTES:")
        print("   • Remover cotacao_id de pedidos órfãos")
        print("   • Remover transportadora de pedidos órfãos")
        print("   • Remover NF de pedidos órfãos")
        print("   • Garantir que status volte para ABERTO")
        print()
    
    # 3. Melhorias no processo
    print("3️⃣ MELHORIAS NO PROCESSO DE CANCELAMENTO:")
    print("   • Melhorar função sincronizar_nf_embarque_pedido_completa")
    print("   • Adicionar limpeza automática de dados órfãos")
    print("   • Implementar validação antes de criar novos embarques")
    print("   • Adicionar logs detalhados do processo de cancelamento")
    print()
    
    print("📝 SCRIPT DE CORREÇÃO:")
    print("   Execute: python corrigir_itens_cancelados.py")

def main():
    """Função principal"""
    print("🚀 ANÁLISE DE IMPACTO - ITENS CANCELADOS EM EMBARQUES")
    print()
    
    # 1. Analisa o fluxo completo
    problemas_encontrados = analisar_fluxo_completo()
    
    # 2. Analisa impacto específico na cotação
    pedidos_problematicos = analisar_impacto_cotacao()
    
    # 3. Gera soluções
    gerar_solucoes(problemas_encontrados or [], pedidos_problematicos or [])
    
    print("\n🎉 Análise concluída!")
    print("\n💡 RESUMO:")
    print(f"   • Itens cancelados com dados sobrando: {len(problemas_encontrados) if problemas_encontrados else 0}")
    print(f"   • Pedidos problemáticos para cotação: {len(pedidos_problematicos) if pedidos_problematicos else 0}")

if __name__ == "__main__":
    main() 