#!/usr/bin/env python3
"""
Debug: Simular exatamente o que acontece na rota /pedidos/lista_pedidos
"""

from app import create_app, db
app = create_app()
from app.pedidos.models import Pedido
from sqlalchemy import text, distinct
from datetime import datetime, timedelta

def debug_rota():
    with app.app_context():
        print("=" * 80)
        print("DEBUG: SIMULANDO ROTA /pedidos/lista_pedidos SEM FILTROS")
        print("=" * 80)
        
        # Simular início da rota
        query = Pedido.query
        print(f"\n1. Query inicial: Pedido.query")
        print(f"   Total sem filtros: {query.count()} pedidos")
        
        # Verificar se há filtros GET (simulando sem parâmetros)
        filtro_status = None  # request.args.get('status')
        filtro_data = None    # request.args.get('data')
        
        print(f"\n2. Parâmetros GET:")
        print(f"   filtro_status: {filtro_status}")
        print(f"   filtro_data: {filtro_data}")
        
        # Contadores (para comparação)
        hoje = datetime.now().date()
        print(f"\n3. Contadores (para comparação):")
        
        todos = Pedido.query.count()
        abertos = Pedido.query.filter(
            Pedido.cotacao_id.is_(None),
            Pedido.nf_cd == False,
            (Pedido.nf.is_(None)) | (Pedido.nf == ""),
            Pedido.data_embarque.is_(None)
        ).count()
        
        cotados = Pedido.query.filter(
            Pedido.cotacao_id.isnot(None),
            Pedido.data_embarque.is_(None),
            (Pedido.nf.is_(None)) | (Pedido.nf == ""),
            Pedido.nf_cd == False
        ).count()
        
        print(f"   Todos: {todos}")
        print(f"   Abertos: {abertos}")
        print(f"   Cotados: {cotados}")
        
        # Verificar se há filtro padrão sendo aplicado
        print(f"\n4. Query SEM FILTROS aplicados:")
        print(f"   Total: {query.count()} pedidos")
        
        # Listar alguns pedidos
        pedidos = query.limit(10).all()
        print(f"\n5. Primeiros 10 pedidos da query:")
        for p in pedidos:
            print(f"   - {p.num_pedido}: Status={p.status}, Cotacao={p.cotacao_id}, NF={p.nf}, NF_CD={p.nf_cd}")
        
        # Verificar se há algum filtro no formulário sendo aplicado
        print(f"\n6. Simulando POST sem dados de formulário:")
        # Em GET/POST sem dados, nenhum filtro adicional seria aplicado
        
        # Verificar ordenação padrão
        print(f"\n7. Aplicando ordenação padrão:")
        query_ordenada = query.order_by(
            Pedido.rota.asc().nullslast(),
            Pedido.sub_rota.asc().nullslast(),
            Pedido.cnpj_cpf.asc().nullslast(),
            Pedido.expedicao.asc().nullslast(),
        )
        
        pedidos_final = query_ordenada.all()
        print(f"   Total após ordenação: {len(pedidos_final)} pedidos")
        
        # Mostrar primeiros pedidos finais
        print(f"\n8. Primeiros 5 pedidos FINAIS (como apareceriam na tabela):")
        for p in pedidos_final[:5]:
            print(f"   - {p.num_pedido}: {p.status} | CNPJ: {p.cnpj_cpf} | Cliente: {p.raz_social_red}")
        
        # Verificar se há algo específico com pedidos recentes
        print(f"\n9. Verificando pedidos mais recentes:")
        
        # Pedidos criados hoje
        pedidos_hoje = Pedido.query.filter(
            db.func.date(Pedido.criado_em) == hoje
        ).count()
        print(f"   Pedidos criados hoje: {pedidos_hoje}")
        
        # Último pedido criado
        ultimo = Pedido.query.order_by(Pedido.criado_em.desc()).first()
        if ultimo:
            print(f"\n   Último pedido criado:")
            print(f"   - Pedido: {ultimo.num_pedido}")
            print(f"   - Status: {ultimo.status}")
            print(f"   - Criado em: {ultimo.criado_em}")
            print(f"   - Lote: {ultimo.separacao_lote_id}")
        
        # DIAGNÓSTICO
        print("\n" + "=" * 80)
        print("DIAGNÓSTICO:")
        print("=" * 80)
        
        if len(pedidos_final) == 1:
            print("❌ PROBLEMA CONFIRMADO: Apenas 1 pedido na query final!")
            print("   Investigando o pedido único...")
            p = pedidos_final[0]
            print(f"   - Pedido: {p.num_pedido}")
            print(f"   - Status: {p.status}")
            print(f"   - Lote: {p.separacao_lote_id}")
            print(f"   - Criado: {p.criado_em}")
            print("\n   POSSÍVEL CAUSA: Filtro oculto ou problema na VIEW")
        elif len(pedidos_final) < todos:
            print(f"⚠️ Query retorna {len(pedidos_final)} de {todos} pedidos")
            print("   Algum filtro está sendo aplicado")
        else:
            print(f"✅ Query retorna todos os {len(pedidos_final)} pedidos corretamente")

if __name__ == "__main__":
    debug_rota()