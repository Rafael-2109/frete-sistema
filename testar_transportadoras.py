from app import create_app, db
from app.transportadoras.models import Transportadora

app = create_app()

with app.app_context():
    print("=== TESTE TRANSPORTADORAS ===")
    
    # Verifica as colunas da tabela
    print("Colunas da tabela transportadoras:")
    for col in Transportadora.__table__.columns:
        print(f"  - {col.name}: {col.type}")
    
    print("\n=== AMOSTRAS DE TRANSPORTADORAS ===")
    
    # Busca algumas transportadoras para teste
    transportadoras = Transportadora.query.limit(5).all()
    
    for t in transportadoras:
        print(f"\nID: {t.id}")
        print(f"Razão Social: {t.razao_social}")
        print(f"CNPJ: {t.cnpj}")
        print(f"Optante: {t.optante} (tipo: {type(t.optante)})")
        print(f"Freteiro: {t.freteiro} (tipo: {type(t.freteiro)})")
        print(f"Cidade: {t.cidade}")
        print(f"UF: {t.uf}")
        print(f"Condição Pgto: {t.condicao_pgto}")
        print("-" * 50) 