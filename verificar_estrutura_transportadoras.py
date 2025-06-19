from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("=== ESTRUTURA DA TABELA TRANSPORTADORAS ===")
    
    # Consulta SQL direta para ver a estrutura da tabela
    try:
        result = db.session.execute(text("PRAGMA table_info(transportadoras)"))
        columns = result.fetchall()
        
        print("Colunas na tabela transportadoras (SQL direto):")
        for col in columns:
            print(f"  - {col[1]} ({col[2]}) - nullable: {not col[3]} - default: {col[4]}")
        
        print("\n=== TESTE DE ALGUMAS TRANSPORTADORAS ===")
        
        # Consulta SQL direta para pegar dados
        result = db.session.execute(text("SELECT id, razao_social, optante, freteiro FROM transportadoras LIMIT 3"))
        transportadoras = result.fetchall()
        
        for t in transportadoras:
            print(f"ID: {t[0]} | Razão: {t[1]} | Optante: {t[2]} | Freteiro: {t[3]}")
            
    except Exception as e:
        print(f"Erro ao consultar: {e}")
        
        # Fallback: tentar via modelo SQLAlchemy
        from app.transportadoras.models import Transportadora
        transportadoras = Transportadora.query.limit(3).all()
        
        for t in transportadoras:
            print(f"ID: {t.id} | Razão: {t.razao_social}")
            print(f"  Optante: {getattr(t, 'optante', 'CAMPO NÃO EXISTE')}")
            print(f"  Freteiro: {getattr(t, 'freteiro', 'CAMPO NÃO EXISTE')}") 