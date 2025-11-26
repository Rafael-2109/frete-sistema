"""
Teste direto do LoaderExecutor para verificar o bug do filtro ilike.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def testar_loader_executor():
    from app import create_app
    app = create_app()

    with app.app_context():
        from app.claude_ai_lite.ia_trainer.services.loader_executor import executar_loader

        # Definição EXATA que foi gerada pelo Claude
        definicao = {
            "modelo_base": "Separacao",
            "filtros": [
                {
                    "campo": "raz_social_red",
                    "operador": "ilike",
                    "valor": "%TOTAL ATACADO LJ 2%"
                },
                {
                    "campo": "qtd_saldo",
                    "operador": ">",
                    "valor": 0
                },
                {
                    "campo": "sincronizado_nf",
                    "operador": "==",
                    "valor": False
                }
            ],
            "campos_retorno": [
                "num_pedido",
                "raz_social_red",
                "cod_produto",
                "nome_produto",
                "qtd_saldo",
                "agendamento",
                "expedicao",
                "status"
            ],
            "limite": 100
        }

        print("=" * 60)
        print("TESTE DIRETO DO LOADER EXECUTOR")
        print("=" * 60)
        print(f"\nDefinição:")
        import json
        print(json.dumps(definicao, indent=2, ensure_ascii=False))

        print("\n--- Executando ---")
        resultado = executar_loader(definicao, {})

        print(f"\nSucesso: {resultado.get('sucesso')}")
        print(f"Total: {resultado.get('total')}")
        print(f"Erro: {resultado.get('erro')}")

        dados = resultado.get('dados', [])
        print(f"\nPrimeiros 5 resultados:")
        for i, item in enumerate(dados[:5]):
            print(f"  {i+1}. {item.get('raz_social_red', '?')} | {item.get('num_pedido', '?')} | qtd={item.get('qtd_saldo', '?')}")

        # Verifica se tem resultado de outro cliente
        clientes_encontrados = set()
        for item in dados:
            cliente = item.get('raz_social_red')
            if cliente:
                clientes_encontrados.add(cliente)

        print(f"\nClientes encontrados: {clientes_encontrados}")

        if clientes_encontrados and 'TOTAL ATACADO LJ 2' not in clientes_encontrados:
            print("\n⚠️  PROBLEMA: Nenhum resultado do 'TOTAL ATACADO LJ 2'!")
            print("   O filtro ilike NÃO está funcionando como esperado.")

            # Teste direto no banco
            print("\n--- Teste direto no banco ---")
            from app.separacao.models import Separacao

            # Query manual
            query_manual = Separacao.query.filter(
                Separacao.raz_social_red.ilike('%TOTAL ATACADO LJ 2%'),
                Separacao.qtd_saldo > 0,
                Separacao.sincronizado_nf == False
            )

            print(f"SQL gerado: {str(query_manual)}")

            resultados_manual = query_manual.limit(10).all()
            print(f"\nResultados da query manual: {len(resultados_manual)}")
            for r in resultados_manual[:5]:
                print(f"  - {r.raz_social_red} | {r.num_pedido} | qtd={r.qtd_saldo}")


if __name__ == "__main__":
    testar_loader_executor()
