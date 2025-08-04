"""
Script para investigar inconsistências no console do Render
Execute no Render Console:
1. Abra o shell do Render
2. Execute: python
3. Cole este código
"""

# Primeiro, importe os modelos necessários
from app.embarques.models import Embarque
from app.cotacao.models import Cotacao
from app.tabelas.models import TabelaFrete
from app.transportadoras.models import Transportadora
from app import db

# Função para investigar um embarque específico
def investigar(embarque_numero):
    """Investiga embarque por número"""
    e = Embarque.query.filter_by(numero=embarque_numero).first()
    if not e:
        print(f"Embarque {embarque_numero} não encontrado")
        return
    
    print(f"\n=== EMBARQUE #{e.numero} (ID: {e.id}) ===")
    print(f"Transportadora ID: {e.transportadora_id}")
    t = Transportadora.query.get(e.transportadora_id)
    print(f"Transportadora: {t.razao_social if t else 'NÃO ENCONTRADA'}")
    print(f"Tabela: {e.tabela_nome_tabela}")
    print(f"Tipo: {e.tipo_carga}")
    print(f"Criado: {e.criado_em} por {e.criado_por}")
    
    # Verifica se a tabela pertence à transportadora
    if e.tabela_nome_tabela:
        tabela_ok = TabelaFrete.query.filter_by(
            transportadora_id=e.transportadora_id,
            nome_tabela=e.tabela_nome_tabela,
            tipo_carga=e.tipo_carga
        ).first()
        
        if tabela_ok:
            print("✅ Tabela pertence à transportadora")
        else:
            print("❌ PROBLEMA: Tabela NÃO pertence à transportadora!")
            
            # Busca de quem é a tabela
            tabela_real = TabelaFrete.query.filter_by(
                nome_tabela=e.tabela_nome_tabela,
                tipo_carga=e.tipo_carga
            ).first()
            
            if tabela_real:
                t2 = Transportadora.query.get(tabela_real.transportadora_id)
                print(f"⚠️  Tabela pertence a: {t2.razao_social if t2 else 'ID ' + str(tabela_real.transportadora_id)}")
    
    # Verifica cotação
    if e.cotacao_id:
        c = Cotacao.query.get(e.cotacao_id)
        if c:
            print(f"\nCotação ID: {c.id}")
            if c.transportadora_id != e.transportadora_id:
                print(f"⚠️  Transportadora cotação diferente! ID: {c.transportadora_id}")
            if c.nome_tabela and c.nome_tabela != e.tabela_nome_tabela:
                print(f"⚠️  Tabela cotação diferente: {c.nome_tabela}")

# Função para listar inconsistências
def listar_problemas():
    """Lista todos os embarques com problemas"""
    print("\nBuscando inconsistências...")
    
    # Query todos embarques ativos com tabela
    embarques = Embarque.query.filter(
        Embarque.status == 'ativo',
        Embarque.tabela_nome_tabela.isnot(None)
    ).all()
    
    problemas = []
    for e in embarques:
        # Verifica se tabela existe para transportadora
        tabela_ok = TabelaFrete.query.filter_by(
            transportadora_id=e.transportadora_id,
            nome_tabela=e.tabela_nome_tabela,
            tipo_carga=e.tipo_carga
        ).first()
        
        if not tabela_ok:
            problemas.append(e)
    
    print(f"Total embarques com tabela: {len(embarques)}")
    print(f"Total com problemas: {len(problemas)}")
    
    if problemas:
        print("\nPrimeiros 10 problemas:")
        for p in problemas[:10]:
            print(f"  Embarque #{p.numero} - Tabela: {p.tabela_nome_tabela}")
    
    return problemas

# Função para analisar padrões
def analisar_padroes():
    """Analisa padrões nos problemas"""
    from sqlalchemy import func
    
    # Conta por transportadora
    result = db.session.query(
        Embarque.transportadora_id,
        func.count(Embarque.id).label('total')
    ).filter(
        Embarque.status == 'ativo',
        Embarque.tabela_nome_tabela.isnot(None)
    ).group_by(Embarque.transportadora_id).all()
    
    print("\nEmbarques por transportadora:")
    for r in result[:5]:
        t = Transportadora.query.get(r.transportadora_id)
        print(f"  {t.razao_social if t else 'ID ' + str(r.transportadora_id)}: {r.total}")

# INSTRUÇÕES DE USO:
print("""
=== COMANDOS DISPONÍVEIS ===

1. Para investigar um embarque específico:
   investigar(NUMERO_DO_EMBARQUE)
   
2. Para listar todos os problemas:
   problemas = listar_problemas()
   
3. Para analisar padrões:
   analisar_padroes()

4. Para ver detalhes de um embarque da lista:
   investigar(problemas[0].numero)
""")