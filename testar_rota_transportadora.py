from app import create_app
import requests

app = create_app()

# Vamos simular uma requisição à rota de dados
with app.test_client() as client:
    print("=== TESTE DA ROTA DE DADOS TRANSPORTADORA ===")
    
    # Primeiro, vamos buscar uma transportadora para pegar um ID válido
    from app.transportadoras.models import Transportadora
    
    with app.app_context():
        transportadora = Transportadora.query.first()
        
        if transportadora:
            print(f"Testando com transportadora ID: {transportadora.id}")
            print(f"Razão Social: {transportadora.razao_social}")
            print(f"Optante (direto do modelo): {transportadora.optante}")
            print(f"Freteiro (direto do modelo): {transportadora.freteiro}")
            
            # Simula a mesma lógica da rota dados_transportadora
            try:
                optante_valor = transportadora.optante if transportadora.optante is not None else False
                freteiro_valor = transportadora.freteiro if transportadora.freteiro is not None else False
                
                dados = {
                    'success': True,
                    'transportadora': {
                        'id': transportadora.id,
                        'cnpj': transportadora.cnpj or '',
                        'razao_social': transportadora.razao_social or '',
                        'cidade': transportadora.cidade or '',
                        'uf': transportadora.uf or '',
                        'optante': optante_valor,
                        'freteiro': freteiro_valor,
                        'condicao_pgto': transportadora.condicao_pgto or ''
                    }
                }
                
                print("\n=== DADOS QUE SERIAM RETORNADOS ===")
                for key, value in dados['transportadora'].items():
                    print(f"{key}: {value} (tipo: {type(value)})")
                    
            except Exception as e:
                print(f"Erro ao processar dados: {e}")
                
        else:
            print("Nenhuma transportadora encontrada no banco!") 