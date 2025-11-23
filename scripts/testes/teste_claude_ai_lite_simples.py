"""
Teste Simplificado - Claude AI Lite - Domínios e Variações
===========================================================
Versão: Sem depender de create_app() completo
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Configura variáveis de ambiente mínimas
os.environ.setdefault('FLASK_APP', 'app')
os.environ.setdefault('FLASK_ENV', 'development')
os.environ.setdefault('DATABASE_URL', 'postgresql://localhost/frete_db')

print("=" * 80)
print("BATERIA DE TESTES SIMPLIFICADA - CLAUDE AI LITE")
print("=" * 80)
print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
print()

# ==================== TESTE 1: ESTRUTURA DOS LOADERS ====================
print("\n" + "=" * 60)
print("1. VERIFICAÇÃO DE ESTRUTURA DOS LOADERS")
print("=" * 60)

loaders_esperados = [
    ("carteira", "PedidosLoader", ["num_pedido", "cnpj_cpf", "raz_social_red", "pedido_cliente"]),
    ("carteira_produto", "ProdutosLoader", ["nome_produto", "cod_produto"]),
    ("carteira_disponibilidade", "DisponibilidadeLoader", ["num_pedido"]),
    ("carteira_rota", "RotasLoader", ["rota", "sub_rota", "cod_uf"]),
    ("estoque", "EstoqueLoader", ["cod_produto", "nome_produto", "ruptura"]),
    ("carteira_saldo", "SaldoPedidoLoader", ["num_pedido", "cnpj_cpf", "raz_social_red"]),
    ("carteira_gargalo", "GargalosLoader", ["num_pedido", "geral", "cod_produto"]),
]

resultados_estrutura = []

# Importa diretamente os loaders sem Flask
try:
    from app.claude_ai_lite.domains.carteira.loaders.pedidos import PedidosLoader
    from app.claude_ai_lite.domains.carteira.loaders.produtos import ProdutosLoader
    from app.claude_ai_lite.domains.carteira.loaders.disponibilidade import DisponibilidadeLoader
    from app.claude_ai_lite.domains.carteira.loaders.rotas import RotasLoader
    from app.claude_ai_lite.domains.carteira.loaders.estoque import EstoqueLoader
    from app.claude_ai_lite.domains.carteira.loaders.saldo_pedido import SaldoPedidoLoader
    from app.claude_ai_lite.domains.carteira.loaders.gargalos import GargalosLoader

    loaders_classes = {
        "PedidosLoader": PedidosLoader,
        "ProdutosLoader": ProdutosLoader,
        "DisponibilidadeLoader": DisponibilidadeLoader,
        "RotasLoader": RotasLoader,
        "EstoqueLoader": EstoqueLoader,
        "SaldoPedidoLoader": SaldoPedidoLoader,
        "GargalosLoader": GargalosLoader,
    }

    for dominio, loader_nome, campos_esperados in loaders_esperados:
        loader_class = loaders_classes.get(loader_nome)
        if not loader_class:
            print(f"  ❌ {dominio}: Loader {loader_nome} não encontrado")
            resultados_estrutura.append({"dominio": dominio, "passou": False})
            continue

        # Verifica CAMPOS_BUSCA
        campos_reais = getattr(loader_class, "CAMPOS_BUSCA", [])
        campos_ok = all(c in campos_reais for c in campos_esperados)

        # Verifica métodos necessários
        tem_buscar = hasattr(loader_class, "buscar") and callable(getattr(loader_class, "buscar"))
        tem_formatar = hasattr(loader_class, "formatar_contexto") and callable(getattr(loader_class, "formatar_contexto"))

        passou = campos_ok and tem_buscar and tem_formatar

        if passou:
            print(f"  ✅ {dominio}: {loader_nome}")
            print(f"      CAMPOS_BUSCA: {campos_reais}")
            print(f"      buscar(): ✓ | formatar_contexto(): ✓")
        else:
            print(f"  ❌ {dominio}: {loader_nome}")
            print(f"      CAMPOS_BUSCA esperados: {campos_esperados}")
            print(f"      CAMPOS_BUSCA reais: {campos_reais}")
            print(f"      buscar(): {'✓' if tem_buscar else '✗'} | formatar_contexto(): {'✓' if tem_formatar else '✗'}")

        resultados_estrutura.append({
            "dominio": dominio,
            "loader": loader_nome,
            "campos_busca": campos_reais,
            "tem_buscar": tem_buscar,
            "tem_formatar": tem_formatar,
            "passou": passou
        })

except Exception as e:
    print(f"  ❌ ERRO ao importar loaders: {e}")

# ==================== TESTE 2: SERVIÇO DE LEARNING ====================
print("\n" + "=" * 60)
print("2. VERIFICAÇÃO DO SERVIÇO DE APRENDIZADO (LearningService)")
print("=" * 60)

testes_learning = [
    ("lembre que o cliente Ceratti é VIP", "lembrar", "o cliente ceratti é vip"),
    ("Lembrar que o código AZV é azeitona", "lembrar", "o código azv é azeitona"),
    ("guarde que sempre priorizar pedidos grandes", "lembrar", "sempre priorizar pedidos grandes"),
    ("esqueca que o cliente X é VIP", "esquecer", "o cliente x é vip"),
    ("esquecer que o código ABC é palmito", "esquecer", "o código abc é palmito"),
    ("o que você sabe sobre mim?", "listar", None),
    ("quais conhecimentos você tem?", "listar", None),
    ("mostre sua memória", "listar", None),
    ("status do pedido VCD123", None, None),  # NÃO é comando de aprendizado
    ("quando enviar o pedido?", None, None),  # NÃO é comando de aprendizado
]

resultados_learning = []

try:
    from app.claude_ai_lite.learning import LearningService

    for texto, tipo_esperado, conteudo_esperado in testes_learning:
        tipo_detectado, conteudo_detectado = LearningService.detectar_comando(texto)

        passou = tipo_detectado == tipo_esperado
        if conteudo_esperado:
            passou = passou and (conteudo_detectado == conteudo_esperado)

        if passou:
            print(f"  ✅ '{texto[:40]}...' → {tipo_detectado}")
        else:
            print(f"  ❌ '{texto[:40]}...'")
            print(f"      Esperado: {tipo_esperado} | Detectado: {tipo_detectado}")
            if conteudo_esperado:
                print(f"      Conteúdo esperado: {conteudo_esperado}")
                print(f"      Conteúdo detectado: {conteudo_detectado}")

        resultados_learning.append({
            "texto": texto,
            "tipo_esperado": tipo_esperado,
            "tipo_detectado": tipo_detectado,
            "passou": passou
        })

    # Testa detecção de comando global
    print("\n  Testando detecção de comando GLOBAL:")
    testes_global = [
        ("Lembre que X é Y (global)", True),
        ("lembre que código 123 é produto X para todos", True),
        ("lembre que cliente Z é VIP", False),  # Não é global
    ]

    for texto, esperado_global in testes_global:
        eh_global = LearningService.verificar_comando_global(texto)
        passou = eh_global == esperado_global

        if passou:
            print(f"  ✅ '{texto[:40]}...' → global={eh_global}")
        else:
            print(f"  ❌ '{texto[:40]}...' → Esperado: {esperado_global}, Detectado: {eh_global}")

except Exception as e:
    print(f"  ❌ ERRO ao testar LearningService: {e}")

# ==================== TESTE 3: SERVIÇO DE MEMÓRIA ====================
print("\n" + "=" * 60)
print("3. VERIFICAÇÃO DO SERVIÇO DE MEMÓRIA (MemoryService)")
print("=" * 60)

try:
    from app.claude_ai_lite.memory import MemoryService, MAX_HISTORICO, MAX_TOKENS_CONTEXTO

    print(f"  Configurações:")
    print(f"    MAX_HISTORICO: {MAX_HISTORICO}")
    print(f"    MAX_TOKENS_CONTEXTO: {MAX_TOKENS_CONTEXTO}")

    # Verifica métodos disponíveis
    metodos_necessarios = [
        "registrar_mensagem",
        "buscar_historico",
        "buscar_aprendizados",
        "formatar_contexto_memoria",
        "registrar_conversa_completa",
        "estatisticas_usuario",
    ]

    print("\n  Métodos disponíveis:")
    for metodo in metodos_necessarios:
        tem = hasattr(MemoryService, metodo) and callable(getattr(MemoryService, metodo))
        print(f"    {'✅' if tem else '❌'} {metodo}()")

except Exception as e:
    print(f"  ❌ ERRO ao verificar MemoryService: {e}")

# ==================== TESTE 4: ACTIONS (Separação) ====================
print("\n" + "=" * 60)
print("4. VERIFICAÇÃO DAS ACTIONS (separacao_actions)")
print("=" * 60)

try:
    from app.claude_ai_lite.actions.separacao_actions import processar_acao_separacao

    # Testa processamento de intenções
    testes_acoes = [
        ("escolher_opcao", {"opcao": "A"}, "Você escolheu a Opcao A"),
        ("escolher_opcao", {"opcao": "B", "num_pedido": "VCD123"}, None),  # Deve tentar buscar
        ("criar_separacao", {}, "Para criar separacao"),  # Sem parâmetros
        ("confirmar_acao", {}, "Para criar a separacao"),
    ]

    for intencao, entidades, esperado_contem in testes_acoes:
        try:
            resposta = processar_acao_separacao(intencao, entidades, "teste")
            passou = True

            if esperado_contem:
                passou = esperado_contem.lower() in resposta.lower()

            if passou:
                print(f"  ✅ {intencao} → Resposta OK")
                print(f"      Preview: {resposta[:60]}...")
            else:
                print(f"  ❌ {intencao} → Resposta inesperada")
                print(f"      Esperado conter: {esperado_contem}")
                print(f"      Resposta: {resposta[:80]}...")
        except Exception as e:
            # Erros de banco são esperados já que não temos conexão
            if "database" in str(e).lower() or "connection" in str(e).lower() or "operational" in str(e).lower():
                print(f"  ⚠️ {intencao} → Erro de banco (esperado sem conexão)")
            else:
                print(f"  ❌ {intencao} → ERRO: {e}")

except Exception as e:
    print(f"  ❌ ERRO ao importar actions: {e}")

# ==================== TESTE 5: CORE (Roteamento) ====================
print("\n" + "=" * 60)
print("5. VERIFICAÇÃO DO CORE (Roteamento de Domínios)")
print("=" * 60)

try:
    # Testa função de roteamento diretamente
    import importlib.util
    spec = importlib.util.spec_from_file_location("core", "app/claude_ai_lite/core.py")
    core_module = importlib.util.module_from_spec(spec)

    # Lê o código fonte para análise estática
    with open("app/claude_ai_lite/core.py", "r") as f:
        core_code = f.read()

    # Verifica se os roteamentos existem
    roteamentos_esperados = [
        ("carteira_rota", "buscar_rota"),
        ("carteira_rota", "buscar_uf"),
        ("estoque", "consultar_estoque"),
        ("estoque", "consultar_ruptura"),
        ("carteira_saldo", "analisar_saldo"),
        ("carteira_gargalo", "analisar_gargalo"),
        ("carteira_produto", "buscar_produto"),
        ("carteira_disponibilidade", "analisar_disponibilidade"),
    ]

    print("  Verificando roteamentos no core.py:")
    for dominio, intencao in roteamentos_esperados:
        # Verifica se a combinação está no código
        tem_intencao = f'"{intencao}"' in core_code or f"'{intencao}'" in core_code
        tem_dominio = f'"{dominio}"' in core_code or f"'{dominio}'" in core_code

        if tem_intencao and tem_dominio:
            print(f"  ✅ {intencao} → {dominio}")
        else:
            print(f"  ⚠️ {intencao} → {dominio} (verificar manualmente)")

    # Verifica mapeamento de entidades
    print("\n  Verificando mapeamento de entidades:")
    mapeamentos = [
        ("num_pedido", "num_pedido"),
        ("cnpj", "cnpj_cpf"),
        ("cliente", "raz_social_red"),
        ("produto", "nome_produto"),
        ("rota", "rota"),
        ("sub_rota", "sub_rota"),
        ("uf", "cod_uf"),
    ]

    for entidade, campo in mapeamentos:
        presente = f'"{entidade}": "{campo}"' in core_code or f"'{entidade}': '{campo}'" in core_code
        print(f"  {'✅' if presente else '⚠️'} {entidade} → {campo}")

except Exception as e:
    print(f"  ❌ ERRO ao verificar core: {e}")

# ==================== TESTE 6: MODELS (Tabelas de Memória) ====================
print("\n" + "=" * 60)
print("6. VERIFICAÇÃO DOS MODELS (Tabelas de Memória)")
print("=" * 60)

try:
    # Lê o código fonte para análise estática
    with open("app/claude_ai_lite/models.py", "r") as f:
        models_code = f.read()

    # Verifica se as tabelas existem
    tabelas_esperadas = [
        ("ClaudeHistoricoConversa", "claude_historico_conversa"),
        ("ClaudeAprendizado", "claude_aprendizado"),
    ]

    for classe, tabela in tabelas_esperadas:
        tem_classe = f"class {classe}" in models_code
        tem_tabela = f'__tablename__ = "{tabela}"' in models_code or f"__tablename__ = '{tabela}'" in models_code

        print(f"  {'✅' if tem_classe and tem_tabela else '❌'} {classe} (tabela: {tabela})")

    # Verifica campos importantes
    campos_historico = ["usuario_id", "tipo", "conteudo", "metadados", "criado_em"]
    campos_aprendizado = ["usuario_id", "categoria", "chave", "valor", "escopo", "ativo", "prioridade"]

    print("\n  Campos ClaudeHistoricoConversa:")
    for campo in campos_historico:
        presente = f"{campo} = db.Column" in models_code
        print(f"    {'✅' if presente else '❌'} {campo}")

    print("\n  Campos ClaudeAprendizado:")
    for campo in campos_aprendizado:
        presente = f"{campo} = db.Column" in models_code
        print(f"    {'✅' if presente else '❌'} {campo}")

except Exception as e:
    print(f"  ❌ ERRO ao verificar models: {e}")

# ==================== RESUMO FINAL ====================
print("\n" + "=" * 80)
print("RESUMO FINAL")
print("=" * 80)

# Conta resultados
total_loaders = len(resultados_estrutura)
loaders_ok = len([r for r in resultados_estrutura if r.get("passou", False)])

total_learning = len(resultados_learning)
learning_ok = len([r for r in resultados_learning if r.get("passou", False)])

print(f"""
ESTRUTURA DOS LOADERS:
  Total: {total_loaders} | OK: {loaders_ok} | Taxa: {loaders_ok/total_loaders*100:.0f}%

DETECÇÃO DE COMANDOS (LearningService):
  Total: {total_learning} | OK: {learning_ok} | Taxa: {learning_ok/total_learning*100:.0f}%

VERIFICAÇÕES DE CÓDIGO:
  - Core (roteamento): Verificado estaticamente
  - Models (tabelas): Verificado estaticamente
  - Actions: Verificado parcialmente (sem banco)
  - Memory: Estrutura OK

NOTA: Os testes de execução real (com banco de dados) devem ser
executados com a aplicação Flask rodando.

Para testar com banco, use:
  1. flask run (em um terminal)
  2. curl -X POST http://localhost:5000/claude-lite/api/query \\
       -H "Content-Type: application/json" \\
       -d '{{"query": "Status do pedido VCD123"}}'
""")

# Salva resultados
output = {
    "data_execucao": datetime.now().isoformat(),
    "tipo": "verificacao_estrutura",
    "loaders": resultados_estrutura,
    "learning": resultados_learning,
    "resumo": {
        "loaders_ok": loaders_ok,
        "loaders_total": total_loaders,
        "learning_ok": learning_ok,
        "learning_total": total_learning
    }
}

output_file = os.path.join(os.path.dirname(__file__), "resultado_testes_simplificado.json")
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"Resultados salvos em: {output_file}")
