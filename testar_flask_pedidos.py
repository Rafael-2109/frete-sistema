#!/usr/bin/env python3
"""
Testar o que a aplicação Flask retorna para Pedido
"""

from app import create_app, db
app = create_app()
from app.pedidos.models import Pedido
from sqlalchemy import text

def testar():
    with app.app_context():
        print("=" * 80)
        print("TESTE: O QUE A APLICAÇÃO FLASK VÊ")
        print("=" * 80)
        
        # 1. Teste básico via SQLAlchemy ORM
        print("\n1. TESTE VIA SQLALCHEMY ORM:")
        print("-" * 40)
        
        count = Pedido.query.count()
        print(f"Pedido.query.count() = {count}")
        
        # Listar primeiros 5
        pedidos = Pedido.query.limit(5).all()
        print(f"\nPrimeiros {len(pedidos)} pedidos:")
        for p in pedidos:
            print(f"  - ID: {p.id}, Lote: {p.separacao_lote_id}, Pedido: {p.num_pedido}, Status: {p.status}")
        
        # 2. Verificar se há algo estranho com o primeiro registro
        print("\n2. ANALISANDO O PRIMEIRO PEDIDO:")
        print("-" * 40)
        
        primeiro = Pedido.query.first()
        if primeiro:
            print(f"ID: {primeiro.id}")
            print(f"Lote: {primeiro.separacao_lote_id}")
            print(f"Pedido: {primeiro.num_pedido}")
            print(f"Status: {primeiro.status}")
            print(f"CNPJ: {primeiro.cnpj_cpf}")
            print(f"Cliente: {primeiro.raz_social_red}")
        
        # 3. Verificar se há filtros implícitos
        print("\n3. TESTE DE FILTROS:")
        print("-" * 40)
        
        # Contar por status
        abertos = Pedido.query.filter_by(status='ABERTO').count()
        cotados = Pedido.query.filter_by(status='COTADO').count()
        faturados = Pedido.query.filter_by(status='FATURADO').count()
        nf_cd = Pedido.query.filter(Pedido.nf_cd == True).count()
        
        print(f"ABERTO: {abertos}")
        print(f"COTADO: {cotados}")
        print(f"FATURADO: {faturados}")
        print(f"NF no CD: {nf_cd}")
        
        # 4. Verificar modelo Pedido
        print("\n4. VERIFICANDO MODELO PEDIDO:")
        print("-" * 40)
        
        # Verificar se é VIEW
        print(f"Tabela: {Pedido.__tablename__}")
        if hasattr(Pedido, '__table_args__'):
            table_args = Pedido.__table_args__
            if isinstance(table_args, dict):
                is_view = table_args.get('info', {}).get('is_view', False)
            else:
                # Se for tupla, procurar o dict
                is_view = False
                for arg in table_args:
                    if isinstance(arg, dict):
                        is_view = arg.get('info', {}).get('is_view', False)
                        break
            print(f"É VIEW? {is_view}")
        
        # 5. Query raw para comparar
        print("\n5. QUERY RAW DIRETO NO BANCO:")
        print("-" * 40)
        
        result = db.session.execute(text("SELECT COUNT(*) FROM pedidos"))
        count_raw = result.scalar()
        print(f"SELECT COUNT(*) FROM pedidos = {count_raw}")
        
        # 6. Verificar se há problema com cache ou sessão
        print("\n6. TESTE DE CACHE/SESSÃO:")
        print("-" * 40)
        
        # Limpar cache da sessão
        db.session.expire_all()
        db.session.commit()
        
        # Recontar
        count_depois = Pedido.query.count()
        print(f"Após limpar cache: {count_depois} pedidos")
        
        # 7. Teste simulando a rota
        print("\n7. SIMULANDO A ROTA /pedidos:")
        print("-" * 40)
        
        # Simular query da rota
        query = Pedido.query
        pedidos_simulados = query.all()
        print(f"query.all() retorna: {len(pedidos_simulados)} pedidos")
        
        # Mostrar alguns
        if pedidos_simulados:
            print("\nPrimeiros 3:")
            for p in pedidos_simulados[:3]:
                print(f"  - {p.num_pedido}: {p.status}")
        
        # 8. DIAGNÓSTICO FINAL
        print("\n" + "=" * 80)
        print("DIAGNÓSTICO:")
        print("=" * 80)
        
        if count == 1:
            print("❌ PROBLEMA CONFIRMADO: SQLAlchemy só vê 1 pedido!")
            print("   Possíveis causas:")
            print("   1. Problema na definição do modelo")
            print("   2. Filtro default no modelo")
            print("   3. Problema de permissões")
            print("   4. VIEW com problema")
        elif count != count_raw:
            print(f"⚠️ INCONSISTÊNCIA: ORM vê {count}, SQL vê {count_raw}")
            print("   O modelo pode estar apontando para tabela errada")
        else:
            print(f"✅ Tudo normal: {count} pedidos visíveis")

if __name__ == "__main__":
    testar()