#!/usr/bin/env python3
"""
Script de Debug: Por que pedidos não aparecem no Render?
Execute no shell do Render para diagnóstico
"""

from app import create_app, db
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from sqlalchemy import text

def debug_pedidos():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("DIAGNÓSTICO: PEDIDOS NO RENDER")
        print("=" * 60)
        
        # 1. Verificar se VIEW existe
        print("\n1. VERIFICANDO SE VIEW PEDIDOS EXISTE:")
        result = db.session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.views 
                WHERE table_name = 'pedidos'
            ) as exists
        """)).fetchone()
        print(f"   VIEW pedidos existe: {result[0]}")
        
        # 2. Contar registros em Separacao
        print("\n2. DADOS NA TABELA SEPARACAO:")
        total_sep = Separacao.query.count()
        print(f"   Total registros: {total_sep}")
        
        # Registros com lote_id NOT NULL
        com_lote = Separacao.query.filter(
            Separacao.separacao_lote_id.isnot(None)
        ).count()
        print(f"   Com separacao_lote_id NOT NULL: {com_lote}")
        
        # Registros com status != PREVISAO
        nao_previsao = Separacao.query.filter(
            Separacao.status != 'PREVISAO'
        ).count()
        print(f"   Com status != 'PREVISAO': {nao_previsao}")
        
        # Elegíveis para VIEW
        elegiveis = Separacao.query.filter(
            Separacao.separacao_lote_id.isnot(None),
            Separacao.status != 'PREVISAO'
        ).count()
        print(f"   Elegíveis (ambas condições): {elegiveis}")
        
        # 3. Status únicos
        print("\n3. VALORES ÚNICOS DE STATUS:")
        status_list = db.session.execute(text("""
            SELECT DISTINCT status, COUNT(*) as qtd
            FROM separacao
            GROUP BY status
            ORDER BY qtd DESC
            LIMIT 10
        """)).fetchall()
        for status, qtd in status_list:
            print(f"   '{status}': {qtd}")
        
        # 4. Tentar query Pedido direto
        print("\n4. QUERY PEDIDO (VIEW):")
        try:
            total_pedidos = Pedido.query.count()
            print(f"   Total pedidos na VIEW: {total_pedidos}")
            
            if total_pedidos > 0:
                # Pegar primeiro pedido
                primeiro = Pedido.query.first()
                print(f"   Exemplo: {primeiro.separacao_lote_id} - {primeiro.num_pedido}")
        except Exception as e:
            print(f"   ERRO ao consultar Pedido: {e}")
        
        # 5. Query SQL direto na VIEW
        print("\n5. QUERY SQL DIRETO NA VIEW:")
        try:
            result = db.session.execute(text("SELECT COUNT(*) FROM pedidos")).fetchone()
            print(f"   COUNT(*) FROM pedidos: {result[0]}")
            
            if result[0] > 0:
                exemplos = db.session.execute(text("""
                    SELECT separacao_lote_id, num_pedido, status 
                    FROM pedidos 
                    LIMIT 3
                """)).fetchall()
                for ex in exemplos:
                    print(f"   - {ex[0]} | {ex[1]} | {ex[2]}")
        except Exception as e:
            print(f"   ERRO SQL: {e}")
        
        # 6. Testar query da rota lista_pedidos
        print("\n6. SIMULANDO QUERY DE lista_pedidos:")
        try:
            # Query básica como em lista_pedidos
            query = Pedido.query
            
            # Filtro básico de ABERTOS
            query_abertos = query.filter(
                Pedido.cotacao_id.is_(None),
                Pedido.nf_cd == False,
                (Pedido.nf.is_(None)) | (Pedido.nf == ""),
                Pedido.data_embarque.is_(None)
            )
            
            total_abertos = query_abertos.count()
            print(f"   Pedidos ABERTOS: {total_abertos}")
            
            # Todos os pedidos
            todos = query.count()
            print(f"   Todos os pedidos: {todos}")
            
        except Exception as e:
            print(f"   ERRO na query: {e}")
            import traceback
            traceback.print_exc()
        
        # 7. Verificar problema de case/espaços em STATUS
        print("\n7. VERIFICANDO PROBLEMAS NO CAMPO STATUS:")
        problemas = db.session.execute(text("""
            SELECT 
                '|' || status || '|' as status_delim,
                LENGTH(status) as tamanho,
                COUNT(*) as qtd
            FROM separacao
            WHERE status LIKE '%PREVISAO%'
               OR status LIKE '% %'
               OR LENGTH(status) != LENGTH(TRIM(status))
            GROUP BY status
            LIMIT 5
        """)).fetchall()
        
        if problemas:
            print("   Encontrados status com possíveis problemas:")
            for status, tamanho, qtd in problemas:
                print(f"   - {status} (tamanho: {tamanho}, qtd: {qtd})")
        else:
            print("   Nenhum problema detectado em STATUS")
        
        # 8. Diagnóstico final
        print("\n" + "=" * 60)
        print("DIAGNÓSTICO FINAL:")
        print("=" * 60)
        
        if total_pedidos > 0:
            print("✅ VIEW tem dados - Problema pode ser:")
            print("   1. Filtros na aplicação muito restritivos")
            print("   2. Problema de permissões")
            print("   3. Erro no template ou JavaScript")
        elif elegiveis > 0:
            print("⚠️ Há dados elegíveis mas VIEW está vazia!")
            print("   AÇÃO: Recriar a VIEW com o script SQL")
        else:
            print("❌ Não há dados elegíveis em Separacao!")
            print("   - Verificar se sincronizado_nf está correto")
            print("   - Verificar se status está sendo preenchido")
            print("   - Verificar se separacao_lote_id está sendo gerado")
        
        # 9. Query de teste final
        print("\n9. TESTE FINAL - Query exata da VIEW:")
        teste_sql = """
            SELECT COUNT(*) as total
            FROM (
                SELECT 
                    ROW_NUMBER() OVER (ORDER BY s.separacao_lote_id) as id,
                    s.separacao_lote_id
                FROM separacao s
                WHERE s.separacao_lote_id IS NOT NULL
                  AND s.status != 'PREVISAO'
                GROUP BY s.separacao_lote_id
            ) as teste
        """
        try:
            result = db.session.execute(text(teste_sql)).fetchone()
            print(f"   Query direta (simulando VIEW): {result[0]} registros")
        except Exception as e:
            print(f"   ERRO na query de teste: {e}")

if __name__ == "__main__":
    debug_pedidos()