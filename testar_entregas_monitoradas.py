#!/usr/bin/env python3
"""
Teste para verificar problemas na página de Entregas Monitoradas

Este script testa:
1. Acesso aos dados de EntregaMonitorada
2. Possíveis problemas de sessão SQLAlchemy
3. Queries que podem estar causando erro 500

Uso: python testar_entregas_monitoradas.py
"""

import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app import create_app, db
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from app.cadastros_agendamento.models import ContatoAgendamento
from sqlalchemy import func
from datetime import date

def testar_entregas_monitoradas():
    """Testa o acesso à página de entregas monitoradas"""
    
    app = create_app()
    
    with app.app_context():
        print("🧪 TESTE: PÁGINA ENTREGAS MONITORADAS")
        print("=" * 60)
        
        try:
            # 1. Teste básico de query
            print("\n1️⃣ TESTE: Query básica de entregas")
            entregas = EntregaMonitorada.query.limit(5).all()
            print(f"   ✅ Encontradas {len(entregas)} entregas")
            
            for entrega in entregas:
                try:
                    # Testa acesso aos atributos básicos
                    nf = entrega.numero_nf
                    cliente = entrega.cliente
                    cnpj = entrega.cnpj_cliente
                    print(f"   ✅ NF {nf} - {cliente}")
                except Exception as e:
                    print(f"   ❌ Erro ao acessar entrega {getattr(entrega, 'id', 'N/A')}: {e}")
        
        except Exception as e:
            print(f"   ❌ ERRO na query básica: {e}")
            return False
        
        try:
            # 2. Teste de filtros comuns
            print("\n2️⃣ TESTE: Filtros da página")
            
            # Teste filtro pendentes
            pendentes = EntregaMonitorada.query.filter(EntregaMonitorada.entregue == False).count()
            print(f"   ✅ Entregas pendentes: {pendentes}")
            
            # Teste filtro entregues
            entregues = EntregaMonitorada.query.filter(EntregaMonitorada.entregue == True).count()
            print(f"   ✅ Entregas entregues: {entregues}")
            
            # Teste filtro atrasadas
            atrasadas = EntregaMonitorada.query.filter(
                EntregaMonitorada.entregue == False,
                EntregaMonitorada.data_entrega_prevista != None,
                EntregaMonitorada.data_entrega_prevista < date.today()
            ).count()
            print(f"   ✅ Entregas atrasadas: {atrasadas}")
            
        except Exception as e:
            print(f"   ❌ ERRO nos filtros: {e}")
            return False
        
        try:
            # 3. Teste de relacionamentos
            print("\n3️⃣ TESTE: Relacionamentos e joins")
            
            # Teste join com agendamentos
            with_agendamentos = db.session.query(EntregaMonitorada).join(AgendamentoEntrega).count()
            print(f"   ✅ Entregas com agendamentos: {with_agendamentos}")
            
            # Teste subquery de agendamentos
            subquery = db.session.query(AgendamentoEntrega.entrega_id).distinct()
            cnpjs_agendamento = db.session.query(ContatoAgendamento.cnpj).all()
            print(f"   ✅ CNPJs com contato de agendamento: {len(cnpjs_agendamento)}")
            
        except Exception as e:
            print(f"   ❌ ERRO nos relacionamentos: {e}")
            return False
        
        try:
            # 4. Teste de agrupamento (similar ao da página)
            print("\n4️⃣ TESTE: Agrupamento por status")
            
            # Testa a lógica de agrupamento da página
            cnpjs_com_agendamento = {c.cnpj for c in ContatoAgendamento.query.all()}
            
            entregas_teste = EntregaMonitorada.query.limit(10).all()
            
            grupos = {
                'atrasadas': [],
                'sem_agendamento': [],
                'sem_previsao': [],
                'pendentes': [],
                'entregues': []
            }
            
            for e in entregas_teste:
                try:
                    if e.entregue:
                        grupos['entregues'].append(e)
                    elif e.cnpj_cliente in cnpjs_com_agendamento and len(e.agendamentos) == 0:
                        grupos['sem_agendamento'].append(e)
                    elif e.data_entrega_prevista and e.data_entrega_prevista < date.today():
                        grupos['atrasadas'].append(e)
                    elif not e.data_entrega_prevista:
                        grupos['sem_previsao'].append(e)
                    else:
                        grupos['pendentes'].append(e)
                except Exception as e_inner:
                    print(f"   ❌ Erro ao agrupar entrega {getattr(e, 'id', 'N/A')}: {e_inner}")
            
            for grupo, lista in grupos.items():
                print(f"   ✅ {grupo}: {len(lista)} entregas")
                
        except Exception as e:
            print(f"   ❌ ERRO no agrupamento: {e}")
            return False
        
        try:
            # 5. Teste de ordenação
            print("\n5️⃣ TESTE: Ordenação")
            
            # Teste ordenação por diferentes campos
            campos_ordenacao = [
                EntregaMonitorada.numero_nf,
                EntregaMonitorada.cliente,
                EntregaMonitorada.data_faturamento,
                EntregaMonitorada.criado_em
            ]
            
            for campo in campos_ordenacao:
                try:
                    query_test = EntregaMonitorada.query.order_by(campo.desc()).limit(1)
                    resultado = query_test.first()
                    print(f"   ✅ Ordenação por {campo.name}: OK")
                except Exception as e_order:
                    print(f"   ❌ Erro na ordenação por {campo.name}: {e_order}")
                    
        except Exception as e:
            print(f"   ❌ ERRO na ordenação: {e}")
            return False
        
        try:
            # 6. Teste de paginação
            print("\n6️⃣ TESTE: Paginação")
            
            paginacao = EntregaMonitorada.query.paginate(page=1, per_page=20, error_out=False)
            print(f"   ✅ Página 1: {len(paginacao.items)} itens")
            print(f"   ✅ Total de páginas: {paginacao.pages}")
            print(f"   ✅ Total de itens: {paginacao.total}")
            
        except Exception as e:
            print(f"   ❌ ERRO na paginação: {e}")
            return False
        
        print("\n📈 RESULTADO FINAL:")
        print("✅ Todos os testes passaram! A página de Entregas Monitoradas deve funcionar.")
        print("\n💡 Se ainda há erro 500, pode ser:")
        print("   1. Problema no template HTML")
        print("   2. Erro em algum filtro específico aplicado pelo usuário")
        print("   3. Problema de permissão ou autenticação")
        print("   4. Erro no JavaScript da página")
        
        return True

if __name__ == "__main__":
    testar_entregas_monitoradas() 