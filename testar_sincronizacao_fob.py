#!/usr/bin/env python3

"""
Script para Testar Sincronização FOB

Este script testa especificamente a sincronização de NFs em embarques FOB:
1. Busca embarques FOB ativos
2. Verifica se têm NFs lançadas
3. Testa a sincronização com pedidos
4. Verifica se cotação FOB é criada automaticamente

Executar: python testar_sincronizacao_fob.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.embarques.models import Embarque, EmbarqueItem
from app.pedidos.models import Pedido
from app.cotacao.models import Cotacao
from app.transportadoras.models import Transportadora
from app.embarques.routes import sincronizar_nf_embarque_pedido_completa

def buscar_embarques_fob():
    """Busca embarques FOB ativos"""
    print("🚛 Buscando embarques FOB ativos...")
    
    # Buscar por tipo_carga = 'FOB'
    embarques_fob_tipo = Embarque.query.filter_by(
        status='ativo',
        tipo_carga='FOB'
    ).all()
    
    # Buscar por transportadora = 'FOB - COLETA'
    transportadora_fob = Transportadora.query.filter_by(razao_social="FOB - COLETA").first()
    embarques_fob_transp = []
    if transportadora_fob:
        embarques_fob_transp = Embarque.query.filter_by(
            status='ativo',
            transportadora_id=transportadora_fob.id
        ).all()
    
    # Combinar e remover duplicatas
    embarques_fob = list(set(embarques_fob_tipo + embarques_fob_transp))
    
    print(f"📊 Encontrados {len(embarques_fob)} embarques FOB ativos:")
    for embarque in embarques_fob:
        transportadora_nome = embarque.transportadora.razao_social if embarque.transportadora else 'N/A'
        print(f"   - Embarque #{embarque.numero}: {embarque.tipo_carga or 'N/A'} | {transportadora_nome}")
    
    return embarques_fob

def verificar_embarque_fob(embarque):
    """Verifica detalhes de um embarque FOB"""
    print(f"\n🔍 ANALISANDO EMBARQUE #{embarque.numero}")
    print("-" * 50)
    
    transportadora_nome = embarque.transportadora.razao_social if embarque.transportadora else 'N/A'
    print(f"📋 Tipo de carga: {embarque.tipo_carga or 'N/A'}")
    print(f"🚚 Transportadora: {transportadora_nome}")
    print(f"📦 Itens: {len(embarque.itens)}")
    
    # Verificar itens com NF
    itens_com_nf = [item for item in embarque.itens if item.nota_fiscal and item.nota_fiscal.strip()]
    itens_sem_nf = [item for item in embarque.itens if not item.nota_fiscal or not item.nota_fiscal.strip()]
    
    print(f"📝 Itens com NF: {len(itens_com_nf)}")
    print(f"📋 Itens sem NF: {len(itens_sem_nf)}")
    
    # Mostrar detalhes dos itens com NF
    for item in itens_com_nf:
        print(f"   • Pedido {item.pedido} | NF: {item.nota_fiscal} | Lote: {item.separacao_lote_id or 'N/A'}")
    
    # Verificar pedidos correspondentes
    print(f"\n🔍 Verificando pedidos correspondentes:")
    pedidos_analisados = []
    
    for item in itens_com_nf:
        pedido = None
        
        # Buscar pedido
        if item.separacao_lote_id:
            pedido = Pedido.query.filter_by(separacao_lote_id=item.separacao_lote_id).first()
        if not pedido and item.pedido:
            pedido = Pedido.query.filter_by(num_pedido=item.pedido).first()
        
        if pedido:
            pedidos_analisados.append(pedido)
            print(f"   ✅ Pedido {pedido.num_pedido}:")
            print(f"      - NF no pedido: {pedido.nf or 'SEM NF'}")
            print(f"      - NF no embarque: {item.nota_fiscal}")
            print(f"      - Status: {pedido.status}")
            print(f"      - Status calculado: {pedido.status_calculado}")
            print(f"      - Transportadora: {pedido.transportadora or 'N/A'}")
            print(f"      - Cotação ID: {pedido.cotacao_id or 'N/A'}")
            
            if pedido.nf != item.nota_fiscal:
                print(f"      ⚠️ NF DESATUALIZADA: Pedido tem '{pedido.nf}', embarque tem '{item.nota_fiscal}'")
            if not pedido.cotacao_id:
                print(f"      ⚠️ SEM COTAÇÃO: Pedido FOB sem cotacao_id")
        else:
            print(f"   ❌ Pedido {item.pedido} não encontrado!")
    
    return itens_com_nf, pedidos_analisados

def testar_sincronizacao_embarque_fob(embarque):
    """Testa a sincronização de um embarque FOB"""
    print(f"\n🔧 TESTANDO SINCRONIZAÇÃO EMBARQUE #{embarque.numero}")
    print("-" * 50)
    
    # Executar sincronização
    sucesso, resultado = sincronizar_nf_embarque_pedido_completa(embarque.id)
    
    if sucesso:
        print(f"✅ Sincronização: {resultado}")
    else:
        print(f"❌ Erro na sincronização: {resultado}")
    
    return sucesso, resultado

def verificar_cotacao_fob_criada():
    """Verifica se há cotação FOB no sistema"""
    print(f"\n🔍 VERIFICANDO COTAÇÃO FOB")
    print("-" * 50)
    
    # Buscar transportadora FOB
    transportadora_fob = Transportadora.query.filter_by(razao_social="FOB - COLETA").first()
    
    if transportadora_fob:
        print(f"✅ Transportadora FOB encontrada: ID {transportadora_fob.id}")
        
        # Buscar cotações FOB
        cotacoes_fob = Cotacao.query.filter_by(
            transportadora_id=transportadora_fob.id,
            tipo_carga='FOB'
        ).all()
        
        print(f"📊 Cotações FOB encontradas: {len(cotacoes_fob)}")
        for cotacao in cotacoes_fob:
            print(f"   • Cotação ID {cotacao.id}: {cotacao.status} | {cotacao.nome_tabela}")
        
        return transportadora_fob, cotacoes_fob
    else:
        print(f"❌ Transportadora 'FOB - COLETA' não encontrada!")
        return None, []

def main():
    """Função principal"""
    
    print("🚛 TESTE DE SINCRONIZAÇÃO FOB")
    print("=" * 60)
    print("Testando sincronização automática de NFs em embarques FOB")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # 1. Buscar embarques FOB
            embarques_fob = buscar_embarques_fob()
            
            if not embarques_fob:
                print("❌ Nenhum embarque FOB ativo encontrado!")
                return
            
            # 2. Verificar cotação FOB
            transportadora_fob, cotacoes_fob = verificar_cotacao_fob_criada()
            
            # 3. Analisar cada embarque FOB
            for embarque in embarques_fob:
                itens_com_nf, pedidos = verificar_embarque_fob(embarque)
                
                if itens_com_nf:
                    # Testar sincronização
                    testar_sincronizacao_embarque_fob(embarque)
                    
                    # Verificar resultado
                    print(f"\n🔍 VERIFICAÇÃO PÓS-SINCRONIZAÇÃO:")
                    print("-" * 40)
                    
                    for item in itens_com_nf:
                        pedido = None
                        if item.separacao_lote_id:
                            pedido = Pedido.query.filter_by(separacao_lote_id=item.separacao_lote_id).first()
                        if not pedido and item.pedido:
                            pedido = Pedido.query.filter_by(num_pedido=item.pedido).first()
                        
                        if pedido:
                            # Recarregar para ver mudanças
                            db.session.refresh(pedido)
                            
                            print(f"   📝 Pedido {pedido.num_pedido}:")
                            print(f"      - NF: {pedido.nf}")
                            print(f"      - Status: {pedido.status}")
                            print(f"      - Cotação ID: {pedido.cotacao_id}")
                            
                            if pedido.nf == item.nota_fiscal and pedido.cotacao_id:
                                print(f"      ✅ SUCESSO: NF sincronizada e cotação associada!")
                            elif pedido.nf == item.nota_fiscal:
                                print(f"      ⚠️ PARCIAL: NF sincronizada mas sem cotação")
                            else:
                                print(f"      ❌ FALHA: NF não sincronizada")
                else:
                    print(f"   📋 Nenhum item com NF para testar")
            
            print(f"\n" + "=" * 60)
            print("🚀 TESTE CONCLUÍDO!")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ ERRO durante o teste: {str(e)}")
            raise

if __name__ == "__main__":
    main() 