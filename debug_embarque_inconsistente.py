#!/usr/bin/env python3
"""
Script para investigar inconsistências entre tabela e transportadora em embarques
Execute com: python debug_embarque_inconsistente.py [ID_DO_EMBARQUE]
"""

import sys
from app import create_app, db
from app.embarques.models import Embarque
from app.cotacao.models import Cotacao
from app.tabelas.models import TabelaFrete
from app.transportadoras.models import Transportadora

def investigar_embarque(embarque_id):
    """Investiga inconsistências em um embarque específico"""
    
    print(f"\n=== INVESTIGANDO EMBARQUE ID: {embarque_id} ===\n")
    
    # Buscar embarque
    embarque = Embarque.query.get(embarque_id)
    if not embarque:
        print(f"❌ Embarque {embarque_id} não encontrado")
        return
    
    print(f"📦 Embarque #{embarque.numero}")
    print(f"   Status: {embarque.status}")
    print(f"   Tipo Carga: {embarque.tipo_carga}")
    print(f"   Criado em: {embarque.criado_em}")
    print(f"   Criado por: {embarque.criado_por}")
    
    # Transportadora do embarque
    transportadora = Transportadora.query.get(embarque.transportadora_id)
    print(f"\n🚚 Transportadora do Embarque:")
    print(f"   ID: {embarque.transportadora_id}")
    print(f"   Nome: {transportadora.razao_social if transportadora else 'NÃO ENCONTRADA'}")
    
    # Tabela do embarque
    print(f"\n📋 Tabela do Embarque:")
    print(f"   Nome: {embarque.tabela_nome_tabela}")
    print(f"   Modalidade: {embarque.modalidade}")
    
    # Verificar se a tabela existe para esta transportadora
    if embarque.tabela_nome_tabela:
        tabelas_transportadora = TabelaFrete.query.filter_by(
            transportadora_id=embarque.transportadora_id,
            nome_tabela=embarque.tabela_nome_tabela,
            tipo_carga=embarque.tipo_carga
        ).all()
        
        if tabelas_transportadora:
            print(f"   ✅ Tabela ENCONTRADA para esta transportadora ({len(tabelas_transportadora)} registros)")
        else:
            print(f"   ❌ Tabela NÃO ENCONTRADA para esta transportadora!")
            
            # Buscar em qual transportadora está esta tabela
            tabelas_outras = TabelaFrete.query.filter_by(
                nome_tabela=embarque.tabela_nome_tabela,
                tipo_carga=embarque.tipo_carga
            ).all()
            
            if tabelas_outras:
                print(f"\n   ⚠️  Esta tabela foi encontrada em outras transportadoras:")
                transportadoras_com_tabela = set()
                for t in tabelas_outras:
                    transp = Transportadora.query.get(t.transportadora_id)
                    if transp and transp.id not in transportadoras_com_tabela:
                        transportadoras_com_tabela.add(transp.id)
                        print(f"      - {transp.razao_social} (ID: {transp.id})")
    
    # Verificar cotação
    if embarque.cotacao_id:
        print(f"\n💰 Cotação Associada:")
        cotacao = Cotacao.query.get(embarque.cotacao_id)
        if cotacao:
            print(f"   ID: {cotacao.id}")
            print(f"   Status: {cotacao.status}")
            print(f"   Data: {cotacao.data_criacao}")
            
            # Verificar se transportadora da cotação é diferente
            if cotacao.transportadora_id != embarque.transportadora_id:
                print(f"   ⚠️  INCONSISTÊNCIA: Transportadora da cotação é diferente!")
                transp_cotacao = Transportadora.query.get(cotacao.transportadora_id)
                print(f"   Transportadora Cotação: {transp_cotacao.razao_social if transp_cotacao else 'NÃO ENCONTRADA'}")
            
            # Verificar tabela da cotação
            if cotacao.nome_tabela:
                print(f"   Tabela na Cotação: {cotacao.nome_tabela}")
                if cotacao.nome_tabela != embarque.tabela_nome_tabela:
                    print(f"   ⚠️  INCONSISTÊNCIA: Tabela da cotação é diferente!")
    else:
        print(f"\n💰 Sem cotação associada")
    
    # Listar tabelas disponíveis para a transportadora
    print(f"\n📊 Tabelas disponíveis para {transportadora.razao_social if transportadora else 'transportadora'}:")
    tabelas_disponiveis = TabelaFrete.query.filter_by(
        transportadora_id=embarque.transportadora_id,
        tipo_carga=embarque.tipo_carga
    ).all()
    
    if tabelas_disponiveis:
        for t in tabelas_disponiveis[:5]:  # Mostrar apenas 5 primeiras
            print(f"   - {t.nome_tabela} ({t.modalidade}) - UF: {t.uf_origem}->{t.uf_destino}")
        if len(tabelas_disponiveis) > 5:
            print(f"   ... e mais {len(tabelas_disponiveis) - 5} tabelas")
    else:
        print("   Nenhuma tabela encontrada!")
    
    print("\n" + "="*50 + "\n")


def buscar_todos_inconsistentes():
    """Busca todos os embarques com inconsistências"""
    
    print("\n=== BUSCANDO EMBARQUES INCONSISTENTES ===\n")
    
    # Query para buscar embarques onde a tabela não bate com a transportadora
    query = db.session.query(Embarque).filter(
        Embarque.status == 'ativo',
        Embarque.tabela_nome_tabela.isnot(None)
    )
    
    inconsistentes = []
    
    for embarque in query:
        # Verificar se a tabela existe para esta transportadora
        tabela_existe = TabelaFrete.query.filter_by(
            transportadora_id=embarque.transportadora_id,
            nome_tabela=embarque.tabela_nome_tabela,
            tipo_carga=embarque.tipo_carga
        ).first()
        
        if not tabela_existe:
            inconsistentes.append(embarque)
    
    print(f"Total de embarques ativos com tabela: {query.count()}")
    print(f"Total de embarques inconsistentes: {len(inconsistentes)}")
    
    if inconsistentes:
        print("\nEmbarques com problemas:")
        for e in inconsistentes[:10]:  # Mostrar apenas 10 primeiros
            print(f"   - Embarque #{e.numero} (ID: {e.id}) - Tabela: {e.tabela_nome_tabela}")
        
        if len(inconsistentes) > 10:
            print(f"   ... e mais {len(inconsistentes) - 10} embarques")
    
    return inconsistentes


if __name__ == "__main__":
    app = create_app()
    
    with app.app_context():
        if len(sys.argv) > 1:
            # Investigar embarque específico
            embarque_id = int(sys.argv[1])
            investigar_embarque(embarque_id)
        else:
            # Buscar todos os inconsistentes
            inconsistentes = buscar_todos_inconsistentes()
            
            if inconsistentes and input("\nDeseja investigar o primeiro embarque inconsistente? (s/n): ").lower() == 's':
                investigar_embarque(inconsistentes[0].id)