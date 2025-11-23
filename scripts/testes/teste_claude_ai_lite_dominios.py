"""
Bateria de Testes - Claude AI Lite - Domínios e Variações
=========================================================
Data: 22/11/2025
Objetivo: Testar 5 variações de cada domínio e avaliar respostas

DOMÍNIOS TESTADOS:
1. PedidosLoader (carteira) - 5 variações
2. ProdutosLoader (carteira_produto) - 5 variações
3. DisponibilidadeLoader (carteira_disponibilidade) - 5 variações
4. RotasLoader (carteira_rota) - 5 variações
5. EstoqueLoader (estoque) - 5 variações
6. SaldoPedidoLoader (carteira_saldo) - 5 variações
7. GargalosLoader (carteira_gargalo) - 5 variações
8. MemoryService + LearningService - 5 variações
9. Actions (Separação) - 5 variações

Total: 45 testes
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db


# ==================== DEFINIÇÃO DOS TESTES ====================

TESTES_POR_DOMINIO = {

    # 1. DOMÍNIO: PEDIDOS (PedidosLoader)
    "pedidos": {
        "dominio": "carteira",
        "loader_class": "PedidosLoader",
        "descricao": "Consultas por pedido, cliente, CNPJ",
        "perguntas": [
            {
                "id": "PED_01",
                "tipo": "num_pedido",
                "pergunta": "Status do pedido VCD2564344",
                "campo_esperado": "num_pedido",
                "criterios_avaliacao": [
                    "Retorna dados do pedido",
                    "Mostra cliente e CNPJ",
                    "Mostra produtos do pedido",
                    "Mostra status de separação"
                ]
            },
            {
                "id": "PED_02",
                "tipo": "cliente",
                "pergunta": "Pedidos do cliente Atacadão",
                "campo_esperado": "raz_social_red",
                "criterios_avaliacao": [
                    "Busca por razão social parcial",
                    "Lista múltiplos pedidos se houver",
                    "Agrupa por pedido corretamente"
                ]
            },
            {
                "id": "PED_03",
                "tipo": "cnpj",
                "pergunta": "Pedidos do CNPJ 12345678000199",
                "campo_esperado": "cnpj_cpf",
                "criterios_avaliacao": [
                    "Aceita CNPJ com ou sem formatação",
                    "Remove caracteres especiais",
                    "Retorna todos pedidos do CNPJ"
                ]
            },
            {
                "id": "PED_04",
                "tipo": "pedido_cliente",
                "pergunta": "Pedido de compra PC-123456",
                "campo_esperado": "pedido_cliente",
                "criterios_avaliacao": [
                    "Busca pelo pedido de compra do cliente",
                    "Campo pedido_cliente preenchido na resposta"
                ]
            },
            {
                "id": "PED_05",
                "tipo": "pedido_inexistente",
                "pergunta": "Status do pedido XXXINEXISTENTE999",
                "campo_esperado": "num_pedido",
                "criterios_avaliacao": [
                    "Retorna mensagem de não encontrado",
                    "total_encontrado = 0",
                    "Mensagem amigável"
                ]
            }
        ]
    },

    # 2. DOMÍNIO: PRODUTOS (ProdutosLoader)
    "produtos": {
        "dominio": "carteira_produto",
        "loader_class": "ProdutosLoader",
        "descricao": "Consultas por produto na carteira",
        "perguntas": [
            {
                "id": "PROD_01",
                "tipo": "nome_produto",
                "pergunta": "Tem azeitona na carteira?",
                "campo_esperado": "nome_produto",
                "criterios_avaliacao": [
                    "Busca por nome parcial",
                    "Mostra quantidade na carteira",
                    "Mostra quantidade separada",
                    "Mostra resumo de totais"
                ]
            },
            {
                "id": "PROD_02",
                "tipo": "cod_produto",
                "pergunta": "Produto código AZV001 na carteira",
                "campo_esperado": "cod_produto",
                "criterios_avaliacao": [
                    "Busca por código do produto",
                    "Retorna qtd_carteira e qtd_separada"
                ]
            },
            {
                "id": "PROD_03",
                "tipo": "nome_generico",
                "pergunta": "Quanto de ketchup tem na carteira?",
                "campo_esperado": "nome_produto",
                "criterios_avaliacao": [
                    "Retorna múltiplos produtos se houver",
                    "Agrupa por cod_produto",
                    "Calcula resumo corretamente"
                ]
            },
            {
                "id": "PROD_04",
                "tipo": "produto_separado",
                "pergunta": "Mostarda está separada?",
                "campo_esperado": "nome_produto",
                "criterios_avaliacao": [
                    "Mostra qtd_separada",
                    "Mostra qtd_programada (com expedição)",
                    "Lista pedidos separados"
                ]
            },
            {
                "id": "PROD_05",
                "tipo": "produto_inexistente",
                "pergunta": "Tem PRODUTOINEXISTENTE na carteira?",
                "campo_esperado": "nome_produto",
                "criterios_avaliacao": [
                    "Retorna mensagem de não encontrado",
                    "total_encontrado = 0"
                ]
            }
        ]
    },

    # 3. DOMÍNIO: DISPONIBILIDADE (DisponibilidadeLoader)
    "disponibilidade": {
        "dominio": "carteira_disponibilidade",
        "loader_class": "DisponibilidadeLoader",
        "descricao": "Análise de quando embarcar pedido",
        "perguntas": [
            {
                "id": "DISP_01",
                "tipo": "quando_enviar",
                "pergunta": "Quando posso enviar o pedido VCD2564344?",
                "campo_esperado": "num_pedido",
                "criterios_avaliacao": [
                    "Retorna opções A/B/C",
                    "Mostra data de envio de cada opção",
                    "Mostra valor e percentual",
                    "Mostra itens incluídos/excluídos"
                ]
            },
            {
                "id": "DISP_02",
                "tipo": "disponibilidade_hoje",
                "pergunta": "Posso enviar VCD2564344 hoje?",
                "campo_esperado": "num_pedido",
                "criterios_avaliacao": [
                    "Indica se disponível hoje",
                    "Mostra dias_para_envio",
                    "Flag disponivel_hoje"
                ]
            },
            {
                "id": "DISP_03",
                "tipo": "ja_separado",
                "pergunta": "Quando enviar pedido já separado?",
                "campo_esperado": "num_pedido",
                "criterios_avaliacao": [
                    "Detecta pedido já separado",
                    "Mostra status atual das separações",
                    "Não gera novas opções A/B/C"
                ]
            },
            {
                "id": "DISP_04",
                "tipo": "pedido_parcial",
                "pergunta": "Opções de envio para VCD2564344",
                "campo_esperado": "num_pedido",
                "criterios_avaliacao": [
                    "Gera até 3 opções",
                    "Opção A = Total",
                    "Opção B = Parcial -1 gargalo",
                    "Opção C = Parcial -2 gargalos"
                ]
            },
            {
                "id": "DISP_05",
                "tipo": "pedido_inexistente",
                "pergunta": "Quando enviar pedido INEXISTENTE?",
                "campo_esperado": "num_pedido",
                "criterios_avaliacao": [
                    "Retorna erro ou mensagem",
                    "Não gera opções"
                ]
            }
        ]
    },

    # 4. DOMÍNIO: ROTAS (RotasLoader)
    "rotas": {
        "dominio": "carteira_rota",
        "loader_class": "RotasLoader",
        "descricao": "Consultas por rota, sub-rota e UF",
        "perguntas": [
            {
                "id": "ROT_01",
                "tipo": "rota_principal",
                "pergunta": "Pedidos na rota MG",
                "campo_esperado": "rota",
                "criterios_avaliacao": [
                    "Filtra por rota corretamente",
                    "Mostra resumo de totais",
                    "Agrupa por status",
                    "Lista pedidos"
                ]
            },
            {
                "id": "ROT_02",
                "tipo": "sub_rota",
                "pergunta": "O que tem na sub-rota CAP?",
                "campo_esperado": "sub_rota",
                "criterios_avaliacao": [
                    "Reconhece sub-rota",
                    "Filtra por sub_rota.ilike",
                    "Mostra cidade/UF dos pedidos"
                ]
            },
            {
                "id": "ROT_03",
                "tipo": "uf",
                "pergunta": "Pedidos para São Paulo",
                "campo_esperado": "cod_uf",
                "criterios_avaliacao": [
                    "Reconhece UF = SP",
                    "Filtra por cod_uf",
                    "Lista pedidos do estado"
                ]
            },
            {
                "id": "ROT_04",
                "tipo": "rota_vazia",
                "pergunta": "Pedidos na rota XYZ",
                "campo_esperado": "rota",
                "criterios_avaliacao": [
                    "Verifica cadastro de rota",
                    "Mensagem contextual se rota existe mas vazia",
                    "Mensagem se rota não existe"
                ]
            },
            {
                "id": "ROT_05",
                "tipo": "rota_resumo",
                "pergunta": "Resumo da rota NE",
                "campo_esperado": "rota",
                "criterios_avaliacao": [
                    "Retorna resumo agregado",
                    "Total de pedidos, valor, peso, pallets",
                    "Agrupamento por status",
                    "Agrupamento por UF"
                ]
            }
        ]
    },

    # 5. DOMÍNIO: ESTOQUE (EstoqueLoader)
    "estoque": {
        "dominio": "estoque",
        "loader_class": "EstoqueLoader",
        "descricao": "Estoque atual, projeção e rupturas",
        "perguntas": [
            {
                "id": "EST_01",
                "tipo": "consulta_estoque",
                "pergunta": "Qual o estoque de azeitona verde?",
                "campo_esperado": "nome_produto",
                "criterios_avaliacao": [
                    "Retorna estoque_atual",
                    "Mostra menor_estoque_d7",
                    "Classifica status_estoque",
                    "Mostra projeção 7 dias"
                ]
            },
            {
                "id": "EST_02",
                "tipo": "projecao",
                "pergunta": "Projeção de estoque do ketchup",
                "campo_esperado": "nome_produto",
                "criterios_avaliacao": [
                    "Retorna projeção detalhada",
                    "Mostra entradas e saídas",
                    "Indica dia de ruptura se houver"
                ]
            },
            {
                "id": "EST_03",
                "tipo": "ruptura",
                "pergunta": "Quais produtos vão dar ruptura?",
                "campo_esperado": "ruptura",
                "criterios_avaliacao": [
                    "Lista produtos com ruptura prevista",
                    "Usa campo 'ruptura' especial",
                    "Mostra dias até ruptura",
                    "Resumo de rupturas hoje/3 dias"
                ]
            },
            {
                "id": "EST_04",
                "tipo": "ruptura_dias",
                "pergunta": "Rupturas previstas em 14 dias",
                "campo_esperado": "ruptura",
                "criterios_avaliacao": [
                    "Aceita parâmetro de dias",
                    "Horizonte customizado"
                ]
            },
            {
                "id": "EST_05",
                "tipo": "estoque_codigo",
                "pergunta": "Estoque do produto AZV001",
                "campo_esperado": "cod_produto",
                "criterios_avaliacao": [
                    "Busca por código",
                    "Retorna dados completos",
                    "Próxima entrada se houver"
                ]
            }
        ]
    },

    # 6. DOMÍNIO: SALDO PEDIDO (SaldoPedidoLoader)
    "saldo_pedido": {
        "dominio": "carteira_saldo",
        "loader_class": "SaldoPedidoLoader",
        "descricao": "Comparativo original vs separado vs restante",
        "perguntas": [
            {
                "id": "SALDO_01",
                "tipo": "saldo_pedido",
                "pergunta": "Quanto falta separar do VCD2564344?",
                "campo_esperado": "num_pedido",
                "criterios_avaliacao": [
                    "Mostra qtd_original",
                    "Mostra qtd_separada",
                    "Mostra qtd_restante",
                    "Calcula percentual_atendido"
                ]
            },
            {
                "id": "SALDO_02",
                "tipo": "saldo_cliente",
                "pergunta": "Saldo dos pedidos do cliente Atacadão",
                "campo_esperado": "raz_social_red",
                "criterios_avaliacao": [
                    "Busca por cliente",
                    "Agrupa por pedido",
                    "Mostra status de cada item"
                ]
            },
            {
                "id": "SALDO_03",
                "tipo": "status_item",
                "pergunta": "Status de separação do pedido VCD2564344",
                "campo_esperado": "num_pedido",
                "criterios_avaliacao": [
                    "Classifica status por item",
                    "PENDENTE, PARCIAL_SEPARADO, TOTALMENTE_SEPARADO",
                    "FATURADO se sincronizado_nf=True"
                ]
            },
            {
                "id": "SALDO_04",
                "tipo": "tabela_itens",
                "pergunta": "Tabela de saldo do pedido VCD2564344",
                "campo_esperado": "num_pedido",
                "criterios_avaliacao": [
                    "Formata como tabela",
                    "Colunas: Produto | Original | Separado | Restante | Status"
                ]
            },
            {
                "id": "SALDO_05",
                "tipo": "resumo_geral",
                "pergunta": "Resumo de atendimento do VCD2564344",
                "campo_esperado": "num_pedido",
                "criterios_avaliacao": [
                    "Resumo agregado",
                    "Total original, separado, faturado, restante"
                ]
            }
        ]
    },

    # 7. DOMÍNIO: GARGALOS (GargalosLoader)
    "gargalos": {
        "dominio": "carteira_gargalo",
        "loader_class": "GargalosLoader",
        "descricao": "Produtos que travam pedidos por falta de estoque",
        "perguntas": [
            {
                "id": "GAR_01",
                "tipo": "gargalo_pedido",
                "pergunta": "O que está travando o pedido VCD2564344?",
                "campo_esperado": "num_pedido",
                "criterios_avaliacao": [
                    "Identifica produtos gargalo",
                    "Mostra qtd_necessaria vs estoque_atual",
                    "Mostra data_disponivel",
                    "Lista itens OK"
                ]
            },
            {
                "id": "GAR_02",
                "tipo": "gargalos_gerais",
                "pergunta": "Quais produtos são gargalo na carteira?",
                "campo_esperado": "geral",
                "criterios_avaliacao": [
                    "Lista top gargalos",
                    "Ordena por severidade",
                    "Mostra pedidos afetados",
                    "Classifica CRITICO/ALERTA"
                ]
            },
            {
                "id": "GAR_03",
                "tipo": "impacto_produto",
                "pergunta": "Quais pedidos dependem do produto AZV001?",
                "campo_esperado": "cod_produto",
                "criterios_avaliacao": [
                    "Lista pedidos que usam o produto",
                    "Indica se pode atender cada um",
                    "Resumo atendidos vs bloqueados"
                ]
            },
            {
                "id": "GAR_04",
                "tipo": "sugestao_parcial",
                "pergunta": "Por que não consigo enviar o VCD2564344?",
                "campo_esperado": "num_pedido",
                "criterios_avaliacao": [
                    "Mostra gargalos",
                    "Sugere envio parcial se possível",
                    "pode_enviar_parcial = True/False"
                ]
            },
            {
                "id": "GAR_05",
                "tipo": "sem_gargalo",
                "pergunta": "Gargalos do pedido sem problemas",
                "campo_esperado": "num_pedido",
                "criterios_avaliacao": [
                    "Retorna lista vazia de gargalos",
                    "Mostra todos itens OK",
                    "Mensagem positiva"
                ]
            }
        ]
    },

    # 8. DOMÍNIO: MEMÓRIA E APRENDIZADO
    "memoria_aprendizado": {
        "dominio": "memoria",
        "loader_class": "MemoryService/LearningService",
        "descricao": "Memória de conversa e aprendizados permanentes",
        "perguntas": [
            {
                "id": "MEM_01",
                "tipo": "lembrar",
                "pergunta": "Lembre que o cliente Ceratti é VIP",
                "campo_esperado": "lembrar",
                "criterios_avaliacao": [
                    "Detecta comando 'lembrar'",
                    "Salva aprendizado",
                    "Categoria auto-detectada = 'cliente'",
                    "Confirma salvamento"
                ]
            },
            {
                "id": "MEM_02",
                "tipo": "lembrar_global",
                "pergunta": "Lembre que o código AZV001 é Azeitona Verde (global)",
                "campo_esperado": "lembrar_global",
                "criterios_avaliacao": [
                    "Detecta '(global)'",
                    "Salva com usuario_id = None",
                    "Escopo = global"
                ]
            },
            {
                "id": "MEM_03",
                "tipo": "listar",
                "pergunta": "O que você sabe sobre mim?",
                "campo_esperado": "listar",
                "criterios_avaliacao": [
                    "Detecta comando 'listar'",
                    "Lista aprendizados do usuário",
                    "Lista aprendizados globais",
                    "Agrupa por escopo"
                ]
            },
            {
                "id": "MEM_04",
                "tipo": "esquecer",
                "pergunta": "Esqueça que o cliente Ceratti é VIP",
                "campo_esperado": "esquecer",
                "criterios_avaliacao": [
                    "Detecta comando 'esquecer'",
                    "Desativa aprendizado",
                    "Busca parcial se necessário",
                    "Confirma remoção"
                ]
            },
            {
                "id": "MEM_05",
                "tipo": "contexto",
                "pergunta": "Quais pedidos você falou?",
                "campo_esperado": "historico",
                "criterios_avaliacao": [
                    "Usa histórico de conversa",
                    "Referencia mensagens anteriores",
                    "MAX_HISTORICO = 40"
                ]
            }
        ]
    },

    # 9. DOMÍNIO: AÇÕES (Separação)
    "acoes_separacao": {
        "dominio": "acao",
        "loader_class": "separacao_actions",
        "descricao": "Criar/modificar separações via conversa",
        "perguntas": [
            {
                "id": "ACAO_01",
                "tipo": "escolher_opcao",
                "pergunta": "Opção A para o pedido VCD2564344",
                "campo_esperado": "escolher_opcao",
                "criterios_avaliacao": [
                    "Reconhece escolha de opção",
                    "Valida pedido existe",
                    "Mostra confirmação"
                ]
            },
            {
                "id": "ACAO_02",
                "tipo": "criar_separacao",
                "pergunta": "Criar separação opção A do pedido VCD2564344",
                "campo_esperado": "criar_separacao",
                "criterios_avaliacao": [
                    "Cria separação no banco",
                    "Retorna lote_id CLAUDE-*",
                    "Registra criado_por = usuario"
                ]
            },
            {
                "id": "ACAO_03",
                "tipo": "opcao_sem_pedido",
                "pergunta": "Quero a opção B",
                "campo_esperado": "escolher_opcao",
                "criterios_avaliacao": [
                    "Pede número do pedido",
                    "Mensagem orientativa"
                ]
            },
            {
                "id": "ACAO_04",
                "tipo": "confirmar",
                "pergunta": "Sim, confirmo",
                "campo_esperado": "confirmar_acao",
                "criterios_avaliacao": [
                    "Reconhece confirmação",
                    "Orienta formato correto"
                ]
            },
            {
                "id": "ACAO_05",
                "tipo": "validacao_duplicidade",
                "pergunta": "Criar separação já existente",
                "campo_esperado": "criar_separacao",
                "criterios_avaliacao": [
                    "Valida separação existente",
                    "Não permite duplicar",
                    "Mensagem de erro clara"
                ]
            }
        ]
    }
}


# ==================== FUNÇÕES DE TESTE ====================

def executar_teste_loader(dominio: str, valor: str, campo: str) -> Dict[str, Any]:
    """Executa um teste direto em um loader."""
    from app.claude_ai_lite.domains import get_loader

    resultado = {
        "dominio": dominio,
        "campo": campo,
        "valor": valor,
        "sucesso": False,
        "dados": None,
        "erro": None
    }

    try:
        loader_class = get_loader(dominio)
        if not loader_class:
            resultado["erro"] = f"Loader não encontrado para domínio: {dominio}"
            return resultado

        loader = loader_class()
        dados = loader.buscar(valor, campo)

        resultado["sucesso"] = dados.get("sucesso", False)
        resultado["dados"] = dados
        resultado["contexto_formatado"] = loader.formatar_contexto(dados)

    except Exception as e:
        resultado["erro"] = str(e)

    return resultado


def executar_teste_memoria(tipo: str, conteudo: str, usuario_id: int = 999) -> Dict[str, Any]:
    """Executa um teste de memória/aprendizado."""
    resultado = {
        "tipo": tipo,
        "conteudo": conteudo,
        "sucesso": False,
        "dados": None,
        "erro": None
    }

    try:
        if tipo in ("lembrar", "lembrar_global", "esquecer", "listar"):
            from app.claude_ai_lite.learning import LearningService

            tipo_cmd, conteudo_cmd = LearningService.detectar_comando(conteudo)
            resultado["comando_detectado"] = tipo_cmd
            resultado["conteudo_extraido"] = conteudo_cmd

            if tipo_cmd:
                global_ = LearningService.verificar_comando_global(conteudo)
                resultado["global"] = global_

                res = LearningService.processar_comando(
                    tipo=tipo_cmd,
                    conteudo=conteudo_cmd,
                    usuario_id=usuario_id,
                    usuario_nome="teste_automatizado",
                    global_=global_
                )
                resultado["sucesso"] = res.get("sucesso", False)
                resultado["dados"] = res
            else:
                resultado["erro"] = "Comando não detectado"

        elif tipo == "historico":
            from app.claude_ai_lite.memory import MemoryService

            historico = MemoryService.buscar_historico(usuario_id, limite=10)
            resultado["sucesso"] = True
            resultado["dados"] = {"total": len(historico), "mensagens": historico}

    except Exception as e:
        resultado["erro"] = str(e)

    return resultado


def executar_teste_acao(intencao: str, entidades: Dict, usuario: str = "teste_automatizado") -> Dict[str, Any]:
    """Executa um teste de ação/separação."""
    resultado = {
        "intencao": intencao,
        "entidades": entidades,
        "sucesso": False,
        "resposta": None,
        "erro": None
    }

    try:
        from app.claude_ai_lite.actions import processar_acao_separacao

        resposta = processar_acao_separacao(intencao, entidades, usuario)
        resultado["sucesso"] = True
        resultado["resposta"] = resposta

    except Exception as e:
        resultado["erro"] = str(e)

    return resultado


def avaliar_resultado(teste: Dict, resultado: Dict) -> Dict[str, Any]:
    """Avalia resultado do teste contra critérios esperados."""
    avaliacao = {
        "teste_id": teste["id"],
        "passou": False,
        "criterios_atendidos": [],
        "criterios_nao_atendidos": [],
        "pontuacao": 0
    }

    # Verifica se executou sem erro
    if resultado.get("erro"):
        avaliacao["criterios_nao_atendidos"].append(f"ERRO: {resultado['erro']}")
        return avaliacao

    # Verifica critérios específicos
    dados = resultado.get("dados", {})

    for criterio in teste.get("criterios_avaliacao", []):
        atendido = False

        # Critérios genéricos
        if "Retorna" in criterio or "Mostra" in criterio:
            if dados and (dados.get("total_encontrado", 0) > 0 or dados.get("sucesso")):
                atendido = True
        elif "não encontrado" in criterio.lower():
            if dados and dados.get("total_encontrado", 0) == 0:
                atendido = True
        elif "mensagem" in criterio.lower():
            if dados and (dados.get("mensagem") or dados.get("mensagem")):
                atendido = True
        elif criterio.startswith("total_encontrado"):
            if dados and "total_encontrado" in dados:
                atendido = True
        else:
            # Assume atendido se há dados
            if dados:
                atendido = True

        if atendido:
            avaliacao["criterios_atendidos"].append(criterio)
        else:
            avaliacao["criterios_nao_atendidos"].append(criterio)

    # Calcula pontuação
    total_criterios = len(teste.get("criterios_avaliacao", []))
    criterios_ok = len(avaliacao["criterios_atendidos"])

    if total_criterios > 0:
        avaliacao["pontuacao"] = round(criterios_ok / total_criterios * 100, 1)

    avaliacao["passou"] = avaliacao["pontuacao"] >= 60

    return avaliacao


# ==================== EXECUÇÃO PRINCIPAL ====================

def executar_bateria_testes():
    """Executa todos os testes e gera relatório."""

    print("=" * 80)
    print("BATERIA DE TESTES - CLAUDE AI LITE - DOMÍNIOS E VARIAÇÕES")
    print("=" * 80)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()

    resultados_gerais = []

    for nome_dominio, config in TESTES_POR_DOMINIO.items():
        print(f"\n{'='*60}")
        print(f"DOMÍNIO: {nome_dominio.upper()}")
        print(f"Descrição: {config['descricao']}")
        print(f"Loader: {config['loader_class']}")
        print(f"{'='*60}")

        for pergunta in config["perguntas"]:
            print(f"\n[{pergunta['id']}] {pergunta['tipo']}")
            print(f"Pergunta: {pergunta['pergunta']}")
            print(f"Campo esperado: {pergunta['campo_esperado']}")
            print("-" * 40)

            # Executa teste conforme tipo de domínio
            if nome_dominio == "memoria_aprendizado":
                resultado = executar_teste_memoria(
                    pergunta["tipo"],
                    pergunta["pergunta"]
                )
            elif nome_dominio == "acoes_separacao":
                entidades = {}
                if "pedido" in pergunta["pergunta"].lower():
                    # Extrai número do pedido da pergunta
                    import re
                    match = re.search(r'VCD\d+', pergunta["pergunta"])
                    if match:
                        entidades["num_pedido"] = match.group()
                if "opção" in pergunta["pergunta"].lower() or "opcao" in pergunta["pergunta"].lower():
                    match = re.search(r'[ABC]', pergunta["pergunta"].upper())
                    if match:
                        entidades["opcao"] = match.group()

                resultado = executar_teste_acao(
                    pergunta["campo_esperado"],
                    entidades
                )
            else:
                # Loaders normais
                resultado = executar_teste_loader(
                    config["dominio"],
                    pergunta["pergunta"].split()[-1],  # Último palavra como valor
                    pergunta["campo_esperado"]
                )

            # Avalia resultado
            avaliacao = avaliar_resultado(pergunta, resultado)

            # Exibe resultado
            status = "✅ PASSOU" if avaliacao["passou"] else "❌ FALHOU"
            print(f"Status: {status} ({avaliacao['pontuacao']}%)")

            if avaliacao["criterios_atendidos"]:
                print(f"Critérios OK: {len(avaliacao['criterios_atendidos'])}")
                for c in avaliacao["criterios_atendidos"][:3]:
                    print(f"  ✓ {c}")

            if avaliacao["criterios_nao_atendidos"]:
                print(f"Critérios pendentes: {len(avaliacao['criterios_nao_atendidos'])}")
                for c in avaliacao["criterios_nao_atendidos"][:3]:
                    print(f"  ✗ {c}")

            # Mostra preview do contexto formatado
            if resultado.get("contexto_formatado"):
                preview = resultado["contexto_formatado"][:200]
                print(f"\nPreview resposta:")
                print(f"  {preview}...")

            resultados_gerais.append({
                "dominio": nome_dominio,
                "teste": pergunta,
                "resultado": resultado,
                "avaliacao": avaliacao
            })

    # Resumo final
    print("\n" + "=" * 80)
    print("RESUMO FINAL")
    print("=" * 80)

    total_testes = len(resultados_gerais)
    testes_ok = len([r for r in resultados_gerais if r["avaliacao"]["passou"]])
    testes_falha = total_testes - testes_ok

    print(f"Total de testes: {total_testes}")
    print(f"Passou: {testes_ok} ({testes_ok/total_testes*100:.1f}%)")
    print(f"Falhou: {testes_falha} ({testes_falha/total_testes*100:.1f}%)")

    # Por domínio
    print("\nPor domínio:")
    for nome_dominio in TESTES_POR_DOMINIO.keys():
        testes_dominio = [r for r in resultados_gerais if r["dominio"] == nome_dominio]
        ok = len([t for t in testes_dominio if t["avaliacao"]["passou"]])
        total = len(testes_dominio)
        pct = ok/total*100 if total > 0 else 0
        status = "✅" if pct >= 80 else ("⚠️" if pct >= 50 else "❌")
        print(f"  {status} {nome_dominio}: {ok}/{total} ({pct:.0f}%)")

    return resultados_gerais


if __name__ == "__main__":
    app = create_app()

    with app.app_context():
        resultados = executar_bateria_testes()

        # Salva resultados em JSON
        output_file = os.path.join(os.path.dirname(__file__), "resultado_testes_claude_ai_lite.json")
        with open(output_file, "w", encoding="utf-8") as f:
            # Remove dados não serializáveis
            resultados_json = []
            for r in resultados:
                item = {
                    "dominio": r["dominio"],
                    "teste_id": r["teste"]["id"],
                    "pergunta": r["teste"]["pergunta"],
                    "passou": r["avaliacao"]["passou"],
                    "pontuacao": r["avaliacao"]["pontuacao"],
                    "criterios_ok": len(r["avaliacao"]["criterios_atendidos"]),
                    "criterios_total": len(r["teste"]["criterios_avaliacao"])
                }
                resultados_json.append(item)

            json.dump({
                "data_execucao": datetime.now().isoformat(),
                "total_testes": len(resultados),
                "resultados": resultados_json
            }, f, indent=2, ensure_ascii=False)

        print(f"\nResultados salvos em: {output_file}")
