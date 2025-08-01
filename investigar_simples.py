# Script simplificado para colar no console do Render
# Execute linha por linha ou cole tudo de uma vez

# 1. Importe os modelos
from app.embarques.models import Embarque
from app.tabelas.models import TabelaFrete
from app.transportadoras.models import Transportadora
from app import db

# 2. Substitua XXXXX pelo número do embarque problemático
embarque_numero = XXXXX  # <-- COLOQUE O NÚMERO AQUI

# 3. Busque o embarque
e = Embarque.query.filter_by(numero=embarque_numero).first()

# 4. Veja os dados básicos
print(f"Embarque #{e.numero}")
print(f"Transportadora ID: {e.transportadora_id}")
print(f"Tabela: {e.tabela_nome_tabela}")
print(f"Tipo: {e.tipo_carga}")

# 5. Veja o nome da transportadora
t = Transportadora.query.get(e.transportadora_id)
print(f"Transportadora: {t.razao_social}")

# 6. Verifique se a tabela pertence à transportadora
tabela_existe = TabelaFrete.query.filter_by(
    transportadora_id=e.transportadora_id,
    nome_tabela=e.tabela_nome_tabela,
    tipo_carga=e.tipo_carga
).first()

if tabela_existe:
    print("✅ OK - Tabela pertence à transportadora")
else:
    print("❌ PROBLEMA - Tabela NÃO pertence à transportadora!")
    
    # 7. Descubra de quem é a tabela
    tabela_real = TabelaFrete.query.filter_by(
        nome_tabela=e.tabela_nome_tabela,
        tipo_carga=e.tipo_carga
    ).first()
    
    if tabela_real:
        t2 = Transportadora.query.get(tabela_real.transportadora_id)
        print(f"A tabela pertence a: {t2.razao_social} (ID: {t2.id})")

# 8. Verifique quando foi criado
print(f"\nCriado em: {e.criado_em}")
print(f"Criado por: {e.criado_por}")

# 9. Verifique se tem cotação
if e.cotacao_id:
    from app.cotacao.models import Cotacao
    c = Cotacao.query.get(e.cotacao_id)
    print(f"\nCotação ID: {c.id}")
    print(f"Transportadora na cotação: {c.transportadora_id}")
    print(f"Tabela na cotação: {c.nome_tabela}")

# 10. Conte quantos embarques têm esse problema
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

print(f"\nTotal de embarques com esse problema: {len(todos_problemas)}")