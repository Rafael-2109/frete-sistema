"""
Diagnóstico completo do fluxo Claude AI Lite.

Testa passo a passo com "TOTAL ATACADO LJ 2" para identificar
onde o contexto se perde e onde as suposições estão corretas.

Execução:
    python scripts/testes/diagnostico_fluxo_completo.py
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Cores para output
class Cores:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_etapa(num, titulo):
    print(f"\n{Cores.HEADER}{'='*60}{Cores.END}")
    print(f"{Cores.BOLD}ETAPA {num}: {titulo}{Cores.END}")
    print(f"{Cores.HEADER}{'='*60}{Cores.END}")


def print_dados(label, dados, max_len=500):
    """Imprime dados formatados."""
    if isinstance(dados, dict):
        texto = json.dumps(dados, ensure_ascii=False, indent=2, default=str)
    elif isinstance(dados, str):
        texto = dados
    else:
        texto = str(dados)

    if len(texto) > max_len:
        texto = texto[:max_len] + f"\n... [truncado, total: {len(texto)} chars]"

    print(f"{Cores.BLUE}{label}:{Cores.END}")
    print(texto)


def print_ok(msg):
    print(f"{Cores.GREEN}✓ {msg}{Cores.END}")


def print_erro(msg):
    print(f"{Cores.RED}✗ {msg}{Cores.END}")


def print_aviso(msg):
    print(f"{Cores.YELLOW}⚠ {msg}{Cores.END}")


def testar_fluxo_completo():
    """Testa fluxo completo com múltiplas mensagens."""

    print(f"\n{Cores.BOLD}{'#'*60}{Cores.END}")
    print(f"{Cores.BOLD}# DIAGNÓSTICO COMPLETO DO FLUXO CLAUDE AI LITE{Cores.END}")
    print(f"{Cores.BOLD}# Cliente de teste: TOTAL ATACADO LJ 2{Cores.END}")
    print(f"{Cores.BOLD}{'#'*60}{Cores.END}")

    from app import create_app
    app = create_app()

    with app.app_context():
        # Usuário de teste
        USUARIO_ID = 9999
        USUARIO_NOME = "Teste Diagnóstico"

        # Limpa estado anterior
        from app.claude_ai_lite.core.structured_state import EstadoManager
        EstadoManager.limpar_tudo(USUARIO_ID)

        # ============================================================
        # MENSAGEM 1: "Tem pedido do Total Atacado?"
        # ============================================================
        print_etapa(1, "MENSAGEM 1: 'Tem pedido do Total Atacado?'")

        consulta1 = "Tem pedido do Total Atacado?"
        resultado1 = executar_com_rastreamento(consulta1, USUARIO_ID, USUARIO_NOME)

        # Verifica se encontrou
        if resultado1.get('total_encontrado', 0) > 0:
            print_ok(f"Encontrou {resultado1['total_encontrado']} resultados")
        else:
            print_erro("Não encontrou resultados - PROBLEMA AQUI!")

        # ============================================================
        # MENSAGEM 2: "Veja TOTAL ATACADO LJ 2" (case diferente)
        # ============================================================
        print_etapa(2, "MENSAGEM 2: 'Veja TOTAL ATACADO LJ 2'")

        consulta2 = "Veja TOTAL ATACADO LJ 2"
        resultado2 = executar_com_rastreamento(consulta2, USUARIO_ID, USUARIO_NOME)

        # ============================================================
        # MENSAGEM 3: "Preciso saber se há saldo que ainda não separou"
        # ============================================================
        print_etapa(3, "MENSAGEM 3: 'Preciso saber se há saldo que ainda não separou'")

        consulta3 = "Preciso saber se há saldo que ainda não separou"
        resultado3 = executar_com_rastreamento(consulta3, USUARIO_ID, USUARIO_NOME)

        # Verifica se manteve contexto
        print(f"\n{Cores.YELLOW}--- VERIFICAÇÃO DE CONTEXTO ---{Cores.END}")
        estado = EstadoManager.obter(USUARIO_ID)

        # Verifica se tem cliente no contexto
        cliente_no_estado = estado.entidades.get('raz_social_red') or estado.entidades.get('cliente')
        if cliente_no_estado:
            valor_cliente = cliente_no_estado.get('valor') if isinstance(cliente_no_estado, dict) else cliente_no_estado
            print_ok(f"Cliente no estado: {valor_cliente}")
        else:
            print_erro("Cliente NÃO está no estado - CONTEXTO PERDIDO!")

        # Verifica referência
        if estado.referencia.get('cliente'):
            print_ok(f"Referência cliente: {estado.referencia['cliente']}")
        else:
            print_aviso("Sem referência de cliente")

        # ============================================================
        # MENSAGEM 4: "Eu preciso saber do TOTAL ATACADO LJ 2"
        # ============================================================
        print_etapa(4, "MENSAGEM 4: 'Eu preciso saber do TOTAL ATACADO LJ 2'")

        consulta4 = "Eu preciso saber do TOTAL ATACADO LJ 2"
        resultado4 = executar_com_rastreamento(consulta4, USUARIO_ID, USUARIO_NOME)

        # ============================================================
        # MENSAGEM 5: "O que tem pendente de separação?"
        # ============================================================
        print_etapa(5, "MENSAGEM 5: 'O que tem pendente de separação?'")

        consulta5 = "O que tem pendente de separação?"
        resultado5 = executar_com_rastreamento(consulta5, USUARIO_ID, USUARIO_NOME)

        # ============================================================
        # RESUMO FINAL
        # ============================================================
        print(f"\n{Cores.HEADER}{'='*60}{Cores.END}")
        print(f"{Cores.BOLD}RESUMO DO DIAGNÓSTICO{Cores.END}")
        print(f"{Cores.HEADER}{'='*60}{Cores.END}")

        print(f"\nEstado final do contexto:")
        print_dados("ENTIDADES", dict(estado.entidades))
        print_dados("REFERENCIA", dict(estado.referencia))
        print_dados("ESTADO_DIALOGO", estado.estado_dialogo)


def executar_com_rastreamento(consulta: str, usuario_id: int, usuario: str) -> dict:
    """
    Executa uma consulta rastreando TODAS as etapas internas.
    """
    print(f"\n{Cores.BLUE}Consulta: {Cores.END}{consulta}")

    from app.claude_ai_lite.core.structured_state import obter_estado_json, EstadoManager
    from app.claude_ai_lite.core.intelligent_extractor import extrair_inteligente
    from app.claude_ai_lite.core.entity_mapper import mapear_extracao
    from app.claude_ai_lite.core.agent_planner import plan_and_execute

    resultado = {'total_encontrado': 0}

    try:
        # --- PASSO 1: Estado Estruturado ---
        print(f"\n{Cores.YELLOW}[1] ESTADO ESTRUTURADO{Cores.END}")
        contexto_estruturado = obter_estado_json(usuario_id)

        if contexto_estruturado:
            estado_json = json.loads(contexto_estruturado)
            print_dados("Estado atual", estado_json, max_len=800)

            # Destaca entidades
            if 'ENTIDADES' in estado_json:
                print(f"\n{Cores.GREEN}  → Entidades no estado:{Cores.END}")
                for k, v in estado_json['ENTIDADES'].items():
                    print(f"     {k}: {v}")
        else:
            print("  (estado vazio)")

        # --- PASSO 2: Conhecimento do Negócio ---
        print(f"\n{Cores.YELLOW}[2] CONHECIMENTO DO NEGÓCIO{Cores.END}")
        try:
            from app.claude_ai_lite.prompts.intent_prompt import _carregar_aprendizados_usuario
            conhecimento = _carregar_aprendizados_usuario(usuario_id)
            if conhecimento:
                print(f"  {len(conhecimento)} chars de conhecimento")
            else:
                print("  (sem conhecimento)")
        except Exception as e:
            conhecimento = ""
            print(f"  Erro: {e}")

        # --- PASSO 3: Extração Inteligente (CLAUDE) ---
        print(f"\n{Cores.YELLOW}[3] EXTRAÇÃO INTELIGENTE (Claude){Cores.END}")
        extracao = extrair_inteligente(consulta, contexto_estruturado, conhecimento)
        print_dados("Resposta do Claude", extracao)

        # --- PASSO 4: Mapeamento de Entidades ---
        print(f"\n{Cores.YELLOW}[4] MAPEAMENTO DE ENTIDADES{Cores.END}")
        intencao = mapear_extracao(extracao)
        print_dados("Após mapeamento", {
            'dominio': intencao.get('dominio'),
            'intencao': intencao.get('intencao'),
            'entidades': intencao.get('entidades')
        })

        dominio = intencao.get('dominio', 'geral')
        intencao_tipo = intencao.get('intencao', '')
        entidades = intencao.get('entidades', {})

        # Verifica normalização de case
        for campo, valor in entidades.items():
            if isinstance(valor, str) and valor != valor.upper() and campo in ['raz_social_red', 'cliente']:
                print_aviso(f"  Campo '{campo}' não está em UPPERCASE: '{valor}'")

        # --- PASSO 5: Atualização do Estado ---
        print(f"\n{Cores.YELLOW}[5] ATUALIZAÇÃO DO ESTADO{Cores.END}")
        if entidades:
            EstadoManager.atualizar_do_extrator(usuario_id, entidades)
            print_ok(f"Estado atualizado com {len(entidades)} entidades")
        else:
            print_aviso("Nenhuma entidade para atualizar")

        # --- PASSO 6: AgentPlanner ---
        print(f"\n{Cores.YELLOW}[6] AGENT PLANNER{Cores.END}")

        # Verifica se entidades do estado estão sendo passadas
        estado_atual = EstadoManager.obter(usuario_id)
        entidades_no_estado = {}
        for campo, dados in estado_atual.entidades.items():
            valor = dados.get('valor') if isinstance(dados, dict) else dados
            if valor:
                entidades_no_estado[campo] = valor

        print(f"  Entidades extraídas da consulta: {list(entidades.keys())}")
        print(f"  Entidades no estado: {list(entidades_no_estado.keys())}")

        # Verifica se há entidades no estado que NÃO estão na consulta
        entidades_perdidas = set(entidades_no_estado.keys()) - set(entidades.keys())
        if entidades_perdidas:
            print_aviso(f"  Entidades no estado que NÃO foram passadas: {entidades_perdidas}")

        # Executa o planner COM LOG DO PLANO
        from app.claude_ai_lite.core.agent_planner import get_agent_planner
        planner = get_agent_planner()

        # Monkey patch temporário para capturar o plano
        original_planejar = planner._planejar
        plano_capturado = {}

        def _planejar_com_log(*args, **kwargs):
            plano = original_planejar(*args, **kwargs)
            plano_capturado['plano'] = plano
            return plano

        planner._planejar = _planejar_com_log

        resultado_planner = planner.plan_and_execute(
            consulta=consulta,
            dominio=dominio,
            entidades=entidades,  # <-- AQUI: só passa entidades da consulta, não do estado!
            intencao_original=intencao_tipo,
            usuario_id=usuario_id,
            usuario=usuario,
            contexto_estruturado=contexto_estruturado,
            conhecimento_negocio=conhecimento
        )

        # Restaura original
        planner._planejar = original_planejar

        # Mostra o plano gerado
        if plano_capturado.get('plano'):
            print(f"\n{Cores.GREEN}  PLANO GERADO PELO CLAUDE:{Cores.END}")
            print_dados("  Plano", plano_capturado['plano'], max_len=1500)

        print_dados("Resultado do AgentPlanner", {
            'sucesso': resultado_planner.get('sucesso'),
            'total_encontrado': resultado_planner.get('total_encontrado'),
            'etapas_executadas': resultado_planner.get('etapas_executadas'),
            'experimental': resultado_planner.get('experimental'),
            'erro': resultado_planner.get('erro')
        })

        # Mostra primeiros dados
        dados = resultado_planner.get('dados', [])
        if dados:
            print(f"\n  Primeiros 3 resultados:")
            if dados and isinstance(dados[0], dict):
                print(f"    [DEBUG] Keys do primeiro item: {list(dados[0].keys())}")
            for i, item in enumerate(dados[:3]):
                if isinstance(item, dict):
                    cliente = item.get('raz_social_red') or item.get('cliente', '?')
                    pedido = item.get('num_pedido', '?')
                    print(f"    {i+1}. {cliente} - {pedido}")

        resultado = resultado_planner

        # --- PASSO 7: Verificação Final ---
        print(f"\n{Cores.YELLOW}[7] VERIFICAÇÃO FINAL{Cores.END}")

        # O resultado corresponde ao cliente em contexto?
        cliente_esperado = entidades_no_estado.get('raz_social_red') or entidades_no_estado.get('cliente')
        if cliente_esperado and dados:
            clientes_retornados = set()
            for item in dados[:10]:
                if isinstance(item, dict):
                    c = item.get('raz_social_red') or item.get('cliente')
                    if c:
                        clientes_retornados.add(c.upper() if isinstance(c, str) else c)

            if cliente_esperado.upper() in clientes_retornados:
                print_ok(f"Resultado corresponde ao cliente esperado: {cliente_esperado}")
            else:
                print_erro(f"RESULTADO NÃO CORRESPONDE!")
                print_erro(f"  Esperado: {cliente_esperado}")
                print_erro(f"  Retornados: {clientes_retornados}")

    except Exception as e:
        import traceback
        print_erro(f"ERRO: {e}")
        traceback.print_exc()

    return resultado


if __name__ == "__main__":
    testar_fluxo_completo()
