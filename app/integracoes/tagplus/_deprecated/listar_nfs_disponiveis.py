"""
Script para verificar conexão e listar NFs disponíveis
"""
from app import create_app
from app.integracoes.tagplus.importador_v2 import ImportadorTagPlusV2

app = create_app()
with app.app_context():
    importador = ImportadorTagPlusV2()
    
    # Testar conexão
    resultado = importador.testar_conexoes()
    print("\n=== STATUS DA CONEXÃO ===")
    print(f"API Notas: {resultado.get('notas', {})}")
    
    if not resultado.get('notas', {}).get('sucesso'):
        print("\n❌ NÃO CONECTADO!")
        print("➡️ Acesse: http://localhost:5000/tagplus/oauth/")
        print("➡️ Faça login e autorize o acesso")
    else:
        print("\n✅ CONECTADO! Você pode importar NFs.")
