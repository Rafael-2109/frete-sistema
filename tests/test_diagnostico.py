from app import create_app
from flask import json

def test_diagnostico():
    app = create_app()
    with app.test_client() as client:
        response = client.get('/cotacao/diagnostico_tabelas')
        result = json.loads(response.data)
        print("\nDiagnóstico das Tabelas:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    test_diagnostico() 