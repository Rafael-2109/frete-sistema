#!/usr/bin/env python
"""
Script para investigar inconsistências entre tabela e transportadora em embarques
USO: python investigar_simples.py [NUMERO_EMBARQUE]
"""
import sys

def investigar_embarque(numero_embarque):
    from app.embarques.models import Embarque
    from app.tabelas.models import TabelaFrete
    from app.transportadoras.models import Transportadora
    from app import db
    
    # Busque o embarque
    e = Embarque.query.filter_by(numero=numero_embarque).first()
    
    if not e:
        print(f"❌ Embarque #{numero_embarque} não encontrado!")
        return
    
    # Veja os dados básicos
    print(f"\n=== EMBARQUE #{e.numero} ===")
    print(f"Transportadora ID: {e.transportadora_id}")
    print(f"Tabela: {e.tabela_nome_tabela}")
    print(f"Tipo: {e.tipo_carga}")
    
    # Veja o nome da transportadora
    t = Transportadora.query.get(e.transportadora_id)
    print(f"Transportadora: {t.razao_social if t else 'NÃO ENCONTRADA'}")
    
    # Verifique se a tabela pertence à transportadora
    if e.tabela_nome_tabela:
        tabela_existe = TabelaFrete.query.filter_by(
            transportadora_id=e.transportadora_id,
            nome_tabela=e.tabela_nome_tabela,
            tipo_carga=e.tipo_carga
        ).first()
        
        if tabela_existe:
            print("\n✅ OK - Tabela pertence à transportadora")
        else:
            print("\n❌ PROBLEMA - Tabela NÃO pertence à transportadora!")
            
            # Descubra de quem é a tabela
            tabela_real = TabelaFrete.query.filter_by(
                nome_tabela=e.tabela_nome_tabela,
                tipo_carga=e.tipo_carga
            ).first()
            
            if tabela_real:
                t2 = Transportadora.query.get(tabela_real.transportadora_id)
                print(f"⚠️  A tabela pertence a: {t2.razao_social if t2 else 'ID ' + str(tabela_real.transportadora_id)} (ID: {tabela_real.transportadora_id})")
    else:
        print("\n⚠️  Embarque sem tabela definida")
    
    # Verifique quando foi criado
    print(f"\nCriado em: {e.criado_em}")
    print(f"Criado por: {e.criado_por}")
    
    # Verifique se tem cotação
    if e.cotacao_id:
        from app.cotacao.models import Cotacao
        c = Cotacao.query.get(e.cotacao_id)
        if c:
            print(f"\nCotação ID: {c.id}")
            print(f"Transportadora na cotação: {c.transportadora_id}")
            print(f"Tabela na cotação: {c.nome_tabela}")
            
            if c.transportadora_id != e.transportadora_id:
                print("⚠️  Transportadora da cotação é diferente do embarque!")
    
    # Conte quantos embarques têm esse problema
    print("\nVerificando outros embarques com problemas similares...")
    todos_problemas = []
    embarques = Embarque.query.filter(
        Embarque.status == 'ativo',
        Embarque.tabela_nome_tabela.isnot(None)
    ).all()
    
    for emb in embarques:
        tab = TabelaFrete.query.filter_by(
            transportadora_id=emb.transportadora_id,
            nome_tabela=emb.tabela_nome_tabela,
            tipo_carga=emb.tipo_carga
        ).first()
        if not tab:
            todos_problemas.append(emb)
    
    print(f"\nTotal de embarques com problemas similares: {len(todos_problemas)}")
    
    if todos_problemas and len(todos_problemas) <= 10:
        print("\nOutros embarques com problemas:")
        for p in todos_problemas:
            if p.numero != numero_embarque:
                print(f"  - Embarque #{p.numero}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("USO: python investigar_simples.py NUMERO_EMBARQUE")
        print("Exemplo: python investigar_simples.py 12345")
        sys.exit(1)
    
    try:
        numero = int(sys.argv[1])
        investigar_embarque(numero)
    except ValueError:
        print("❌ Erro: O número do embarque deve ser um número inteiro")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro ao executar: {str(e)}")
        sys.exit(1)