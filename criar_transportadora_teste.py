from app import create_app, db
from app.transportadoras.models import Transportadora

app = create_app()

with app.app_context():
    print("=== CRIANDO TRANSPORTADORAS DE TESTE ===")
    
    # Verifica se já existem transportadoras
    count = Transportadora.query.count()
    print(f"Transportadoras existentes: {count}")
    
    if count == 0:
        # Cria algumas transportadoras de teste
        transportadoras_teste = [
            {
                'cnpj': '12345678000123',
                'razao_social': 'Transportadora Teste 1 Ltda',
                'cidade': 'São Paulo',
                'uf': 'SP',
                'optante': True,
                'freteiro': False,
                'condicao_pgto': '30 dias'
            },
            {
                'cnpj': '98765432000198',
                'razao_social': 'Freteiro Autônomo Silva',
                'cidade': 'Rio de Janeiro',
                'uf': 'RJ',
                'optante': False,
                'freteiro': True,
                'condicao_pgto': 'À vista'
            },
            {
                'cnpj': '11111111000111',
                'razao_social': 'Transportes Express',
                'cidade': 'Belo Horizonte',
                'uf': 'MG',
                'optante': None,  # Teste com valor NULL
                'freteiro': None,  # Teste com valor NULL
                'condicao_pgto': '15 dias'
            }
        ]
        
        for dados in transportadoras_teste:
            transportadora = Transportadora(**dados)
            db.session.add(transportadora)
            print(f"Adicionando: {dados['razao_social']}")
        
        try:
            db.session.commit()
            print("✅ Transportadoras de teste criadas com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao criar transportadoras: {e}")
    
    else:
        print("Transportadoras já existem no banco local.")
    
    # Lista as transportadoras existentes
    print("\n=== TRANSPORTADORAS NO BANCO ===")
    transportadoras = Transportadora.query.all()
    
    for t in transportadoras:
        print(f"ID {t.id}: {t.razao_social}")
        print(f"  CNPJ: {t.cnpj}")
        print(f"  Optante: {t.optante} (tipo: {type(t.optante)})")
        print(f"  Freteiro: {t.freteiro} (tipo: {type(t.freteiro)})")
        print(f"  Cidade/UF: {t.cidade}/{t.uf}")
        print("-" * 50) 