from app import create_app, db
from app.transportadoras.models import Transportadora

app = create_app()

with app.app_context():
    print("=== VERIFICANDO TRANSPORTADORAS ===")
    
    # Conta quantas transportadoras existem
    total = Transportadora.query.count()
    print(f"Total de transportadoras no banco: {total}")
    
    if total == 0:
        print("\n=== CRIANDO TRANSPORTADORAS DE TESTE ===")
        
        # Cria algumas transportadoras de teste
        transportadoras_teste = [
            {
                'cnpj': '12345678000195',
                'razao_social': 'Transportadora Teste A Ltda',
                'cidade': 'São Paulo',
                'uf': 'SP',
                'optante': True,
                'freteiro': False,
                'condicao_pgto': '30 dias'
            },
            {
                'cnpj': '98765432000156',
                'razao_social': 'Freteiro Teste B',
                'cidade': 'Rio de Janeiro',
                'uf': 'RJ',
                'optante': False,
                'freteiro': True,
                'condicao_pgto': '15 dias'
            },
            {
                'cnpj': '11223344000187',
                'razao_social': 'Logística Teste C S/A',
                'cidade': 'Belo Horizonte',
                'uf': 'MG',
                'optante': True,
                'freteiro': True,
                'condicao_pgto': '7 dias'
            }
        ]
        
        for dados in transportadoras_teste:
            transportadora = Transportadora(
                cnpj=dados['cnpj'],
                razao_social=dados['razao_social'],
                cidade=dados['cidade'],
                uf=dados['uf'],
                optante=dados['optante'],
                freteiro=dados['freteiro'],
                condicao_pgto=dados['condicao_pgto']
            )
            db.session.add(transportadora)
            print(f"  - Criada: {dados['razao_social']}")
        
        try:
            db.session.commit()
            print("✅ Transportadoras de teste criadas com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao criar transportadoras: {e}")
    
    else:
        print("\n=== TRANSPORTADORAS EXISTENTES ===")
        transportadoras = Transportadora.query.limit(5).all()
        
        for t in transportadoras:
            print(f"ID: {t.id}")
            print(f"  Razão Social: {t.razao_social}")
            print(f"  CNPJ: {t.cnpj}")
            print(f"  Optante: {t.optante}")
            print(f"  Freteiro: {t.freteiro}")
            print(f"  Cidade/UF: {t.cidade}/{t.uf}")
            print(f"  Condição Pgto: {t.condicao_pgto}")
            print("-" * 40) 