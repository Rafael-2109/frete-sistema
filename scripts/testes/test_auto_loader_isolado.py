"""
Teste ISOLADO do AutoLoaderService.

Testa apenas o auto_loader sem precisar do Flask completo.
Isso permite debugar onde está falhando.

Roda: .venv/bin/python scripts/testes/test_auto_loader_isolado.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import logging

# Configura logging detalhado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(name)s - %(message)s'
)

# Reduz ruido de outros modulos
for name in ['urllib3', 'httpx', 'httpcore', 'anthropic']:
    logging.getLogger(name).setLevel(logging.WARNING)

print("=" * 70)
print("TESTE ISOLADO DO AUTO-LOADER")
print("=" * 70)
print()

# 1. Teste de import
print("1. TESTANDO IMPORTS")
print("-" * 50)
try:
    from app import db
    print("   db importado OK")

    from app.utils.timezone import agora_brasil
    print("   agora_brasil importado OK")

    from app.claude_ai_lite.models import ClaudePerguntaNaoRespondida
    print("   ClaudePerguntaNaoRespondida importado OK")

    from app.claude_ai_lite.ia_trainer.models import CodigoSistemaGerado
    print("   CodigoSistemaGerado importado OK")

    from app.claude_ai_lite.ia_trainer.services.auto_loader import AutoLoaderService
    print("   AutoLoaderService importado OK")

except ImportError as e:
    print(f"   ERRO DE IMPORT: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"   ERRO: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# 2. Teste de elegibilidade
print("2. TESTANDO ELEGIBILIDADE")
print("-" * 50)
service = AutoLoaderService()

intencao_teste = {
    'dominio': 'carteira',
    'intencao': 'buscar_pedido_sem_agendamento',
    'entidades': {'cliente': 'Assai'},
    'confianca': 0.6
}

elegivel = service._pergunta_elegivel(
    "Há pedidos do cliente Assai sem agendamento?",
    intencao_teste
)
print(f"   Elegivel: {elegivel}")

if not elegivel:
    print("   PROBLEMA: Pergunta deveria ser elegivel!")
    print(f"   Dominio: {intencao_teste.get('dominio')}")
    print(f"   Entidades: {intencao_teste.get('entidades')}")

print()

# 3. Teste de decomposicao
print("3. TESTANDO DECOMPOSIÇÃO AUTOMATICA")
print("-" * 50)
decomposicao = service._gerar_decomposicao_automatica(
    "Há pedidos do cliente Assai sem agendamento?",
    intencao_teste
)
for i, parte in enumerate(decomposicao, 1):
    print(f"   {i}. {parte.get('parte', '')[:50]}")
    print(f"      Tipo: {parte.get('tipo')} | Campo: {parte.get('campo')}")

print()

# 4. Teste de geracao (requer API Claude)
print("4. TESTANDO GERACAO DE LOADER (API CLAUDE)")
print("-" * 50)
print("   AVISO: Este teste faz chamada real a API Claude")
print("   Pressione Ctrl+C para pular...")
print()

try:
    import time
    for i in range(3, 0, -1):
        print(f"   Iniciando em {i}...")
        time.sleep(1)

    codigo_gerado = service._gerar_loader(
        "Há pedidos do cliente Assai sem agendamento?",
        decomposicao
    )

    print(f"   Sucesso: {codigo_gerado.get('sucesso')}")
    print(f"   Nome: {codigo_gerado.get('nome')}")
    print(f"   Dominio: {codigo_gerado.get('dominio')}")
    print(f"   Tem definicao_tecnica: {bool(codigo_gerado.get('definicao_tecnica'))}")

    if codigo_gerado.get('erro'):
        print(f"   ERRO: {codigo_gerado.get('erro')}")

    # 5. Validacao
    print()
    print("5. TESTANDO VALIDACAO DO LOADER")
    print("-" * 50)

    definicao = codigo_gerado.get('definicao_tecnica')
    valido = service._validar_loader_estruturado(definicao)
    print(f"   Loader valido: {valido}")

    if not valido:
        print("   PROBLEMA: Loader deveria ser valido!")
        print(f"   Tipo da definicao: {type(definicao)}")
        if isinstance(definicao, str):
            print(f"   Conteudo (100 chars): {definicao[:100]}...")

    # 6. Execucao
    if valido:
        print()
        print("6. TESTANDO EXECUCAO DO LOADER")
        print("-" * 50)

        resultado = service._executar_loader(definicao, {'cliente': 'Assai'})
        print(f"   Sucesso: {resultado.get('sucesso')}")
        print(f"   Total: {resultado.get('total')}")

        if resultado.get('erro'):
            print(f"   ERRO: {resultado.get('erro')}")

        dados = resultado.get('dados', [])
        if dados:
            print(f"   Primeiros 3 resultados:")
            for item in dados[:3]:
                print(f"      {item}")

except KeyboardInterrupt:
    print("\n   Teste de API pulado pelo usuario")
except Exception as e:
    print(f"   ERRO: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("TESTE CONCLUIDO")
print("=" * 70)
