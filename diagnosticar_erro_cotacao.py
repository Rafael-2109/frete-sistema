#!/usr/bin/env python3
"""
Script para diagnosticar e corrigir problemas com pedidos que causam erro 500 na cotação
- Identifica pedidos com dados inconsistentes
- Corrige pedidos que foram cancelados de embarques mas ainda têm NF
- Limpa dados órfãos que podem causar conflitos
"""

import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido
from app.embarques.models import Embarque, EmbarqueItem

def diagnosticar_pedidos_problematicos():
    """Diagnostica pedidos que podem estar causando problemas na cotação"""
    app = create_app()
    
    with app.app_context():
        print(f"🔍 DIAGNÓSTICO DE PEDIDOS PROBLEMÁTICOS")
        print("=" * 60)
        print(f"Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print()
        
        problemas_encontrados = []
        
        # 1. Pedidos com NF preenchida mas não estão em embarques ativos
        print("1️⃣ Verificando pedidos com NF mas sem embarque ativo...")
        pedidos_com_nf_sem_embarque = []
        
        pedidos_com_nf = Pedido.query.filter(
            Pedido.nf.isnot(None),
            Pedido.nf != ''
        ).all()
        
        for pedido in pedidos_com_nf:
            # Verifica se está em algum embarque ativo
            item_ativo = EmbarqueItem.query.join(Embarque).filter(
                EmbarqueItem.separacao_lote_id == pedido.separacao_lote_id,
                EmbarqueItem.status == 'ativo',
                Embarque.status == 'ativo'
            ).first()
            
            if not item_ativo:
                pedidos_com_nf_sem_embarque.append(pedido)
                print(f"   ⚠️  Pedido {pedido.num_pedido}: NF={pedido.nf}, Status={pedido.status_calculado}, sem embarque ativo")
        
        if pedidos_com_nf_sem_embarque:
            problemas_encontrados.append({
                'tipo': 'NF sem embarque',
                'pedidos': pedidos_com_nf_sem_embarque,
                'descricao': 'Pedidos com NF preenchida mas não estão em embarques ativos'
            })
        
        print(f"   Encontrados: {len(pedidos_com_nf_sem_embarque)} pedidos")
        print()
        
        # 2. Pedidos com cotacao_id mas sem embarque ativo
        print("2️⃣ Verificando pedidos com cotacao_id mas sem embarque ativo...")
        pedidos_cotados_sem_embarque = []
        
        pedidos_cotados = Pedido.query.filter(
            Pedido.cotacao_id.isnot(None)
        ).all()
        
        for pedido in pedidos_cotados:
            # Verifica se está em algum embarque ativo
            item_ativo = EmbarqueItem.query.join(Embarque).filter(
                EmbarqueItem.separacao_lote_id == pedido.separacao_lote_id,
                EmbarqueItem.status == 'ativo',
                Embarque.status == 'ativo'
            ).first()
            
            if not item_ativo:
                pedidos_cotados_sem_embarque.append(pedido)
                print(f"   ⚠️  Pedido {pedido.num_pedido}: cotacao_id={pedido.cotacao_id}, Status={pedido.status_calculado}, sem embarque ativo")
        
        if pedidos_cotados_sem_embarque:
            problemas_encontrados.append({
                'tipo': 'Cotacao sem embarque',
                'pedidos': pedidos_cotados_sem_embarque,
                'descricao': 'Pedidos com cotacao_id mas não estão em embarques ativos'
            })
        
        print(f"   Encontrados: {len(pedidos_cotados_sem_embarque)} pedidos")
        print()
        
        # 3. Pedidos com status inconsistente
        print("3️⃣ Verificando pedidos com status inconsistente...")
        pedidos_status_inconsistente = []
        
        todos_pedidos = Pedido.query.all()
        
        for pedido in todos_pedidos:
            status_calculado = pedido.status_calculado
            status_banco = pedido.status
            
            if status_calculado != status_banco:
                pedidos_status_inconsistente.append(pedido)
                print(f"   ⚠️  Pedido {pedido.num_pedido}: Calculado={status_calculado}, Banco={status_banco}")
        
        if pedidos_status_inconsistente:
            problemas_encontrados.append({
                'tipo': 'Status inconsistente',
                'pedidos': pedidos_status_inconsistente,
                'descricao': 'Pedidos com status calculado diferente do status no banco'
            })
        
        print(f"   Encontrados: {len(pedidos_status_inconsistente)} pedidos")
        print()
        
        # 4. Pedidos duplicados em embarques ativos
        print("4️⃣ Verificando pedidos duplicados em embarques ativos...")
        pedidos_duplicados = []
        
        # Busca pedidos que aparecem em mais de um embarque ativo
        from sqlalchemy import func
        duplicados_query = db.session.query(
            EmbarqueItem.separacao_lote_id,
            func.count(EmbarqueItem.id).label('count')
        ).join(Embarque).filter(
            EmbarqueItem.status == 'ativo',
            Embarque.status == 'ativo'
        ).group_by(EmbarqueItem.separacao_lote_id).having(
            func.count(EmbarqueItem.id) > 1
        ).all()
        
        for lote_id, count in duplicados_query:
            pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()
            if pedido:
                pedidos_duplicados.append(pedido)
                print(f"   ⚠️  Pedido {pedido.num_pedido}: aparece em {count} embarques ativos")
        
        if pedidos_duplicados:
            problemas_encontrados.append({
                'tipo': 'Duplicados em embarques',
                'pedidos': pedidos_duplicados,
                'descricao': 'Pedidos que aparecem em múltiplos embarques ativos'
            })
        
        print(f"   Encontrados: {len(pedidos_duplicados)} pedidos")
        print()
        
        # Relatório final
        print("📊 RELATÓRIO FINAL:")
        print(f"   • Total de problemas encontrados: {len(problemas_encontrados)}")
        for problema in problemas_encontrados:
            print(f"   • {problema['tipo']}: {len(problema['pedidos'])} pedidos")
        print()
        
        return problemas_encontrados

def corrigir_problemas(problemas_encontrados, executar_correcao=False):
    """Corrige os problemas encontrados"""
    if not problemas_encontrados:
        print("✅ Nenhum problema para corrigir!")
        return
    
    print("🔧 CORREÇÕES DISPONÍVEIS:")
    print()
    
    for problema in problemas_encontrados:
        print(f"📋 {problema['tipo']}: {problema['descricao']}")
        print(f"   Pedidos afetados: {len(problema['pedidos'])}")
        
        if problema['tipo'] == 'NF sem embarque':
            print("   Correção: Limpar campo NF e resetar para status ABERTO")
            if executar_correcao:
                for pedido in problema['pedidos']:
                    print(f"      Corrigindo pedido {pedido.num_pedido}...")
                    pedido.nf = None
                    pedido.data_embarque = None
                    pedido.cotacao_id = None
                    pedido.transportadora = None
                    pedido.nf_cd = False
        
        elif problema['tipo'] == 'Cotacao sem embarque':
            print("   Correção: Limpar cotacao_id e resetar para status ABERTO")
            if executar_correcao:
                for pedido in problema['pedidos']:
                    print(f"      Corrigindo pedido {pedido.num_pedido}...")
                    pedido.cotacao_id = None
                    pedido.transportadora = None
                    pedido.nf_cd = False
        
        elif problema['tipo'] == 'Status inconsistente':
            print("   Correção: Sincronizar status do banco com status calculado")
            if executar_correcao:
                for pedido in problema['pedidos']:
                    print(f"      Corrigindo pedido {pedido.num_pedido}: {pedido.status} → {pedido.status_calculado}")
                    pedido.status = pedido.status_calculado
        
        elif problema['tipo'] == 'Duplicados em embarques':
            print("   Correção: Manter apenas no embarque mais recente")
            if executar_correcao:
                for pedido in problema['pedidos']:
                    # Busca todos os itens deste pedido em embarques ativos
                    itens = EmbarqueItem.query.join(Embarque).filter(
                        EmbarqueItem.separacao_lote_id == pedido.separacao_lote_id,
                        EmbarqueItem.status == 'ativo',
                        Embarque.status == 'ativo'
                    ).order_by(Embarque.id.desc()).all()
                    
                    # Mantém apenas o mais recente
                    for i, item in enumerate(itens):
                        if i > 0:  # Remove todos exceto o primeiro (mais recente)
                            print(f"      Removendo pedido {pedido.num_pedido} do embarque #{item.embarque.numero}")
                            item.status = 'cancelado'
        
        print()
    
    if executar_correcao:
        try:
            db.session.commit()
            print("✅ Correções aplicadas com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao aplicar correções: {str(e)}")
    else:
        print("ℹ️  Para executar as correções, execute o script com --corrigir")

def main():
    """Função principal"""
    print("🚀 DIAGNÓSTICO DE PROBLEMAS NA COTAÇÃO")
    print()
    
    # Verifica se deve executar correções
    executar_correcao = '--corrigir' in sys.argv
    
    if executar_correcao:
        resposta = input("⚠️  Este script irá corrigir problemas encontrados nos pedidos.\n"
                        "   Deseja continuar? (s/N): ").strip().lower()
        
        if resposta not in ['s', 'sim', 'y', 'yes']:
            print("❌ Operação cancelada pelo usuário.")
            return
        print()
    
    # Executa o diagnóstico
    problemas = diagnosticar_pedidos_problematicos()
    
    # Executa as correções se solicitado
    corrigir_problemas(problemas, executar_correcao)
    
    print("\n🎉 Diagnóstico concluído!")
    if not executar_correcao and problemas:
        print("💡 Para corrigir os problemas encontrados, execute:")
        print("   python diagnosticar_erro_cotacao.py --corrigir")

if __name__ == "__main__":
    main() 