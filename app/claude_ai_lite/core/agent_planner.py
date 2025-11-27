"""
AgentPlanner - Planeja e executa ferramentas em múltiplas etapas.

FILOSOFIA:
- É uma CAMADA dentro do orchestrator, não um orquestrador paralelo
- Substitui o trecho: find_capability() -> cap.executar()
- Permite até 5 etapas de execução
- Usa resultado de etapas anteriores para alimentar próximas

FLUXO:
1. Recebe pergunta + domínio + entidades
2. Claude planeja quais ferramentas usar e em que ordem
3. Executa cada etapa, passando resultados anteriores
4. Retorna dados consolidados para o responder

REGRAS DE FALLBACK:
- Se nenhuma ferramenta resolve: tenta AutoLoader (apenas para consultas)
- AutoLoader só roda se não resolveu em 5 etapas
- AutoLoader marca resultado como "experimental"

Criado em: 26/11/2025
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Máximo de etapas permitidas
MAX_ETAPAS = 5


class AgentPlanner:
    """
    Planeja e executa ferramentas de forma autônoma.

    Uso:
        planner = AgentPlanner()
        resultado = planner.plan_and_execute(
            consulta="Quais pedidos do Atacadão têm produtos sem estoque?",
            dominio="carteira",
            entidades={"raz_social_red": "ATACADAO"},
            usuario_id=123
        )
    """

    def __init__(self):
        self._claude_client = None
        self._tool_registry = None

    def _get_claude_client(self):
        """Lazy loading do cliente Claude."""
        if self._claude_client is None:
            from ..claude_client import get_claude_client
            self._claude_client = get_claude_client()
        return self._claude_client

    def _get_tool_registry(self):
        """Lazy loading do ToolRegistry."""
        if self._tool_registry is None:
            from .tool_registry import get_tool_registry
            self._tool_registry = get_tool_registry()
        return self._tool_registry

    def plan_and_execute(
        self,
        consulta: str,
        dominio: str,
        entidades: Dict[str, Any],
        intencao_original: str = None,
        usuario_id: int = None,
        usuario: str = "sistema",
        contexto_estruturado: str = None,
        conhecimento_negocio: str = None
    ) -> Dict[str, Any]:
        """
        Planeja e executa ferramentas para responder a consulta.

        Args:
            consulta: Pergunta do usuário
            dominio: Domínio detectado (carteira, estoque, etc)
            entidades: Entidades extraídas
            intencao_original: Intenção detectada pelo extrator (para fallback)
            usuario_id: ID do usuário
            usuario: Nome do usuário
            contexto_estruturado: JSON do estado da conversa
            conhecimento_negocio: Aprendizados do negócio

        Returns:
            Dict com:
            - sucesso: bool
            - dados: dados consolidados de todas as etapas
            - etapas_executadas: lista de etapas com resultados
            - experimental: bool (True se usou AutoLoader)
            - erro: mensagem de erro se falhou
        """
        resultado = {
            'sucesso': False,
            'dados': [],
            'etapas_executadas': [],
            'total_encontrado': 0,
            'experimental': False,
            'erro': None
        }

        try:
            # 1. Obtém ferramentas disponíveis para o domínio
            registry = self._get_tool_registry()
            ferramentas = registry.listar_ferramentas(dominio=dominio)
            ferramentas_prompt = registry.formatar_para_prompt(ferramentas)
            schema_prompt = registry.formatar_schema_resumido(dominio)

            # 2. Claude planeja as etapas
            plano = self._planejar(
                consulta=consulta,
                ferramentas_prompt=ferramentas_prompt,
                schema_prompt=schema_prompt,
                entidades=entidades,
                contexto_estruturado=contexto_estruturado,
                conhecimento_negocio=conhecimento_negocio
            )

            if not plano.get('etapas'):
                # Claude não conseguiu planejar
                logger.warning(f"[AGENT_PLANNER] Claude não retornou etapas para: {consulta[:50]}")
                return self._tentar_fallback(
                    consulta, dominio, entidades, intencao_original,
                    usuario_id, usuario, conhecimento_negocio, resultado
                )

            # 3. Executa cada etapa (máximo MAX_ETAPAS)
            # DUAS LISTAS: brutos (com dados) para encadeamento, resumo para log
            resultados_brutos = []
            etapas_resumo = []
            dados_acumulados = []

            for i, etapa in enumerate(plano['etapas'][:MAX_ETAPAS]):
                logger.info(f"[AGENT_PLANNER] Executando etapa {i+1}/{len(plano['etapas'])}: {etapa.get('ferramenta')}")

                # Executa a etapa (passa resultados brutos para encadeamento)
                resultado_etapa = self._executar_etapa(
                    etapa=etapa,
                    entidades=entidades,
                    resultados_anteriores=resultados_brutos,
                    usuario_id=usuario_id,
                    usuario=usuario
                )

                # Guarda resultado bruto (com dados) para próximas etapas
                resultados_brutos.append(resultado_etapa)

                # Guarda resumo (sem dados) para log/retorno
                etapas_resumo.append({
                    'etapa': i + 1,
                    'ferramenta': etapa.get('ferramenta'),
                    'sucesso': resultado_etapa.get('sucesso', False),
                    'total': resultado_etapa.get('total', 0),
                    'erro': resultado_etapa.get('erro')
                })

                # Acumula dados
                if resultado_etapa.get('sucesso') and resultado_etapa.get('dados'):
                    dados_acumulados.extend(resultado_etapa.get('dados', []))

            # 4. Consolida resultados
            resultado['etapas_executadas'] = etapas_resumo
            resultado['dados'] = dados_acumulados
            resultado['total_encontrado'] = len(dados_acumulados)

            # Verifica se teve sucesso em pelo menos uma etapa
            algum_sucesso = any(e.get('sucesso') for e in etapas_resumo)

            if algum_sucesso:
                resultado['sucesso'] = True
            else:
                # Nenhuma etapa funcionou, tenta fallback
                return self._tentar_fallback(
                    consulta, dominio, entidades, intencao_original,
                    usuario_id, usuario, conhecimento_negocio, resultado
                )

        except Exception as e:
            logger.error(f"[AGENT_PLANNER] Erro: {e}")
            resultado['erro'] = str(e)

        return resultado

    def _planejar(
        self,
        consulta: str,
        ferramentas_prompt: str,
        schema_prompt: str,
        entidades: Dict,
        contexto_estruturado: str = None,
        conhecimento_negocio: str = None
    ) -> Dict[str, Any]:
        """
        Claude planeja quais ferramentas usar e em que ordem.

        Returns:
            Dict com 'etapas': lista de etapas a executar
        """
        hoje = datetime.now().strftime("%d/%m/%Y")

        # Monta contexto
        contexto_extra = ""
        if contexto_estruturado:
            contexto_extra += f"\n=== ESTADO DA CONVERSA ===\n{contexto_estruturado}\n"
        if conhecimento_negocio:
            contexto_extra += f"\n=== CONHECIMENTO DO NEGÓCIO ===\n{conhecimento_negocio}\n"

        system_prompt = f"""Você é um planejador de consultas para um sistema de logística.

DATA DE HOJE: {hoje}

{ferramentas_prompt}

{schema_prompt}
{contexto_extra}

=== SUA TAREFA ===

Analise a pergunta e planeje quais ferramentas usar para respondê-la.

REGRAS:
1. Use a ferramenta mais ESPECÍFICA disponível (capability > codigo_gerado > loader_generico)
2. Se uma ferramenta resolve tudo, use apenas ela (1 etapa)
3. Se precisar combinar dados, use múltiplas etapas (máximo {MAX_ETAPAS})
4. Passe os parâmetros corretos baseado nas entidades disponíveis

⚠️ REGRAS CRÍTICAS:

FILTROS OBRIGATÓRIOS:
- Se há raz_social_red nas entidades, SEMPRE inclua filtro de cliente em TODAS as queries
- Se há num_pedido nas entidades, SEMPRE inclua filtro de pedido em TODAS as queries
- Se há cod_produto nas entidades, SEMPRE inclua filtro de produto em TODAS as queries
- NUNCA retorne dados de TODOS os clientes quando há um cliente específico no contexto
- Use operador "ilike" com "%" para buscas de texto (ex: "%ATACADAO%")

CAMPOS_RETORNO OBRIGATÓRIOS:
- Se filtrar por raz_social_red, SEMPRE inclua "raz_social_red" em campos_retorno
- Se filtrar por num_pedido, SEMPRE inclua "num_pedido" em campos_retorno
- Se filtrar por cod_produto, SEMPRE inclua "cod_produto" e "nome_produto" em campos_retorno
- SEMPRE inclua os campos de identificação para que o usuário saiba de quem são os dados

ENTIDADES DISPONÍVEIS (USE TODAS COMO FILTROS QUANDO APLICÁVEL):
{json.dumps(entidades, ensure_ascii=False, indent=2)}

=== FORMATO DE RESPOSTA ===

Retorne APENAS um JSON válido:

Para ferramentas normais (capability ou codigo_gerado):
{{
    "etapas": [
        {{
            "ferramenta": "nome_da_ferramenta",
            "params": {{"param1": "valor1", "param2": "valor2"}},
            "usar_resultado_de": null,
            "descricao": "o que essa etapa faz"
        }}
    ],
    "explicacao": "Por que esse plano resolve a pergunta"
}}

Para loader_generico (query customizada):
{{
    "etapas": [
        {{
            "ferramenta": "loader_generico",
            "params": {{}},
            "loader_json": {{
                "modelo_base": "NomeDoModel",
                "filtros": [
                    {{"campo": "nome_campo", "operador": "==", "valor": "valor"}}
                ],
                "campos_retorno": ["campo1", "campo2"],
                "limite": 100
            }},
            "usar_resultado_de": null,
            "descricao": "o que essa etapa faz"
        }}
    ],
    "explicacao": "Por que esse plano resolve a pergunta"
}}

Para loader_generico COM AGREGAÇÃO (para perguntas de "quanto", "total", "soma"):
{{
    "etapas": [
        {{
            "ferramenta": "loader_generico",
            "params": {{}},
            "loader_json": {{
                "modelo_base": "FaturamentoProduto",
                "filtros": [
                    {{"campo": "data_fatura", "operador": "==", "valor": "2025-11-25"}}
                ],
                "agregacao": {{
                    "tipo": "agrupar",
                    "por": [],
                    "funcoes": [
                        {{"func": "sum", "campo": "valor_produto_faturado", "alias": "total_valor"}},
                        {{"func": "count", "campo": "id", "alias": "total_registros"}}
                    ]
                }}
            }},
            "descricao": "Calcula total de faturamento do dia"
        }}
    ],
    "explicacao": "Usa agregação SQL para calcular soma/contagem"
}}

FUNÇÕES DE AGREGAÇÃO DISPONÍVEIS: sum, count, avg, min, max
USE AGREGAÇÃO quando o usuário perguntar "quanto", "total", "soma", "quantos"

=== USAR RESULTADO DE ETAPA ANTERIOR ===

Se etapa 2 precisa do resultado da etapa 1, use:
{{
    "etapas": [
        {{
            "ferramenta": "consultar_pedido",
            "params": {{"raz_social_red": "ATACADAO"}},
            "usar_resultado_de": null,
            "descricao": "Busca pedidos do cliente"
        }},
        {{
            "ferramenta": "loader_generico",
            "loader_json": {{ ... }},
            "usar_resultado_de": 0,
            "descricao": "Usa pedidos da etapa anterior para filtrar estoque"
        }}
    ]
}}

Quando usar_resultado_de não é null, os dados da etapa indicada (0-indexed)
são injetados em _dados_anteriores nos params.

=== EXEMPLOS ===

EXEMPLO 1 - Pergunta simples:
Pergunta: "Pedidos do cliente Atacadão"
{{
    "etapas": [
        {{
            "ferramenta": "consultar_pedido",
            "params": {{"raz_social_red": "ATACADAO"}},
            "usar_resultado_de": null,
            "descricao": "Busca pedidos do Atacadão"
        }}
    ],
    "explicacao": "A capability consultar_pedido resolve diretamente"
}}

EXEMPLO 2 - Query customizada:
Pergunta: "Pedidos sem agendamento do Atacadão"
{{
    "etapas": [
        {{
            "ferramenta": "loader_generico",
            "params": {{}},
            "loader_json": {{
                "modelo_base": "Separacao",
                "filtros": [
                    {{"campo": "raz_social_red", "operador": "ilike", "valor": "%ATACADAO%"}},
                    {{"campo": "agendamento", "operador": "is_null"}},
                    {{"campo": "sincronizado_nf", "operador": "==", "valor": false}}
                ],
                "campos_retorno": ["num_pedido", "raz_social_red", "agendamento", "expedicao"],
                "limite": 100
            }},
            "usar_resultado_de": null,
            "descricao": "Busca pedidos sem agendamento na carteira ativa"
        }}
    ],
    "explicacao": "Não há capability para filtrar agendamento, usando loader_generico"
}}

Retorne APENAS o JSON, sem explicações adicionais."""

        try:
            client = self._get_claude_client()
            resposta = client.completar(consulta, system_prompt, use_cache=False)
            return self._parse_plano(resposta)
        except Exception as e:
            logger.error(f"[AGENT_PLANNER] Erro ao planejar: {e}")
            return {'etapas': []}

    def _parse_plano(self, resposta: str) -> Dict[str, Any]:
        """Parseia resposta JSON do planejamento."""
        try:
            resposta_limpa = resposta.strip()

            # Remove blocos markdown
            if resposta_limpa.startswith("```"):
                linhas = resposta_limpa.split("\n")
                resposta_limpa = "\n".join(
                    linhas[1:-1] if linhas[-1].strip() == "```" else linhas[1:]
                )

            plano = json.loads(resposta_limpa)

            # Valida estrutura mínima
            if 'etapas' not in plano:
                plano['etapas'] = []

            return plano

        except json.JSONDecodeError as e:
            logger.warning(f"[AGENT_PLANNER] JSON inválido no plano: {e}")
            return {'etapas': []}

    def _executar_etapa(
        self,
        etapa: Dict,
        entidades: Dict,
        resultados_anteriores: List[Dict],
        usuario_id: int = None,
        usuario: str = "sistema"
    ) -> Dict[str, Any]:
        """
        Executa uma etapa do plano.

        Args:
            etapa: Definição da etapa (ferramenta, params, etc)
            entidades: Entidades originais da consulta
            resultados_anteriores: Resultados BRUTOS de etapas anteriores (com 'dados')
            usuario_id: ID do usuário
            usuario: Nome do usuário

        Returns:
            Dict com sucesso, dados, total, erro
        """
        ferramenta_nome = etapa.get('ferramenta')
        params = etapa.get('params', {})

        # Merge params com entidades (params tem prioridade)
        params_final = {**entidades, **params}

        # Se deve usar resultado de etapa anterior
        usar_de = etapa.get('usar_resultado_de')
        if usar_de is not None and 0 <= usar_de < len(resultados_anteriores):
            etapa_anterior = resultados_anteriores[usar_de]
            if etapa_anterior.get('dados'):
                params_final['_dados_anteriores'] = etapa_anterior['dados']
                logger.debug(f"[AGENT_PLANNER] Injetando {len(etapa_anterior['dados'])} registros da etapa {usar_de}")

        # Busca a ferramenta
        registry = self._get_tool_registry()
        ferramenta = registry.obter_ferramenta(ferramenta_nome)

        if not ferramenta:
            return {'sucesso': False, 'erro': f'Ferramenta não encontrada: {ferramenta_nome}'}

        # Executa conforme o tipo
        tipo = ferramenta.get('tipo')

        if tipo == 'capability':
            return self._executar_capability(ferramenta['objeto'], params_final, usuario_id, usuario)

        elif tipo == 'codigo_gerado':
            return self._executar_codigo_gerado(ferramenta['objeto'], params_final)

        elif tipo == 'loader_generico':
            loader_json = etapa.get('loader_json', {})
            return self._executar_loader_generico(loader_json, params_final)

        else:
            return {'sucesso': False, 'erro': f'Tipo de ferramenta desconhecido: {tipo}'}

    def _executar_capability(
        self,
        capability,
        params: Dict,
        usuario_id: int,
        usuario: str
    ) -> Dict[str, Any]:
        """Executa uma capability."""
        try:
            contexto = {
                'usuario_id': usuario_id,
                'usuario': usuario
            }
            resultado = capability.executar(params, contexto)

            return {
                'sucesso': resultado.get('sucesso', False),
                'dados': resultado.get('dados', []),
                'total': resultado.get('total_encontrado', 0),
                'erro': resultado.get('erro')
            }

        except Exception as e:
            logger.error(f"[AGENT_PLANNER] Erro ao executar capability: {e}")
            return {'sucesso': False, 'erro': str(e)}

    def _executar_codigo_gerado(self, codigo, params: Dict) -> Dict[str, Any]:
        """Executa um CodigoSistemaGerado."""
        try:
            from ..ia_trainer.services.loader_executor import executar_loader

            # Parseia definição técnica
            definicao = codigo.definicao_tecnica
            if isinstance(definicao, str):
                definicao = json.loads(definicao)

            # Monta parâmetros no formato $param
            parametros = {}
            for k, v in params.items():
                if k.startswith('_'):
                    continue  # Ignora params internos como _dados_anteriores
                if not k.startswith('$'):
                    parametros[f'${k}'] = v
                else:
                    parametros[k] = v

            resultado = executar_loader(definicao, parametros)

            return {
                'sucesso': resultado.get('sucesso', False),
                'dados': resultado.get('dados', []),
                'total': resultado.get('total', 0),
                'erro': resultado.get('erro')
            }

        except Exception as e:
            logger.error(f"[AGENT_PLANNER] Erro ao executar código gerado: {e}")
            return {'sucesso': False, 'erro': str(e)}

    def _executar_loader_generico(self, loader_json: Dict, params: Dict) -> Dict[str, Any]:
        """Executa um loader JSON genérico."""
        try:
            from ..ia_trainer.services.loader_executor import executar_loader

            # Monta parâmetros no formato $param
            parametros = {}
            for k, v in params.items():
                if k.startswith('_'):
                    continue  # Ignora params internos como _dados_anteriores
                if not k.startswith('$'):
                    parametros[f'${k}'] = v
                else:
                    parametros[k] = v

            resultado = executar_loader(loader_json, parametros)

            return {
                'sucesso': resultado.get('sucesso', False),
                'dados': resultado.get('dados', []),
                'total': resultado.get('total', 0),
                'erro': resultado.get('erro')
            }

        except Exception as e:
            logger.error(f"[AGENT_PLANNER] Erro ao executar loader genérico: {e}")
            return {'sucesso': False, 'erro': str(e)}

    def _tentar_fallback(
        self,
        consulta: str,
        dominio: str,
        entidades: Dict,
        intencao_original: str,
        usuario_id: int,
        usuario: str,
        conhecimento_negocio: str,
        resultado: Dict
    ) -> Dict[str, Any]:
        """
        Tenta AutoLoader como fallback.

        REGRAS:
        - Só tenta para consultas (não para ações)
        - Marca resultado como experimental
        - Salva em CodigoSistemaGerado para revisão
        """
        # Não tenta AutoLoader para ações
        if dominio == 'acao':
            resultado['erro'] = 'Nenhuma ferramenta encontrada para esta ação'
            return resultado

        logger.info(f"[AGENT_PLANNER] Tentando AutoLoader para: {consulta[:50]}...")

        try:
            from ..ia_trainer.services.auto_loader import tentar_responder_automaticamente

            # Monta intenção completa para AutoLoader
            intencao = {
                'dominio': dominio,
                'intencao': intencao_original,
                'entidades': entidades
            }

            auto_resultado = tentar_responder_automaticamente(
                consulta=consulta,
                intencao=intencao,
                usuario_id=usuario_id,
                usuario=usuario,
                conhecimento_negocio=conhecimento_negocio
            )

            if auto_resultado.get('sucesso'):
                resultado['sucesso'] = True
                resultado['experimental'] = True
                resultado['resposta_auto'] = auto_resultado.get('resposta')
                resultado['loader_id'] = auto_resultado.get('loader_id')
                logger.info(f"[AGENT_PLANNER] AutoLoader funcionou! Loader #{auto_resultado.get('loader_id')}")
            else:
                resultado['erro'] = auto_resultado.get('erro', 'AutoLoader não conseguiu responder')
                # Registra pergunta não respondida
                self._registrar_nao_respondida(consulta, dominio, intencao_original, entidades, usuario_id)

        except Exception as e:
            logger.error(f"[AGENT_PLANNER] Erro no AutoLoader: {e}")
            resultado['erro'] = f'Erro no fallback: {e}'
            self._registrar_nao_respondida(consulta, dominio, intencao_original, entidades, usuario_id)

        return resultado

    def _registrar_nao_respondida(
        self,
        consulta: str,
        dominio: str,
        intencao: str,
        entidades: Dict,
        usuario_id: int
    ):
        """Registra pergunta que não foi respondida."""
        try:
            from ..models import ClaudePerguntaNaoRespondida

            ClaudePerguntaNaoRespondida.registrar(
                consulta=consulta,
                motivo_falha='sem_capacidade',
                usuario_id=usuario_id,
                intencao={
                    'dominio': dominio,
                    'intencao': intencao,
                    'entidades': entidades
                }
            )
            logger.info(f"[AGENT_PLANNER] Pergunta registrada para análise posterior")

        except Exception as e:
            logger.warning(f"[AGENT_PLANNER] Erro ao registrar pergunta: {e}")


# Singleton
_planner: Optional[AgentPlanner] = None


def get_agent_planner() -> AgentPlanner:
    """Retorna instância singleton do AgentPlanner."""
    global _planner
    if _planner is None:
        _planner = AgentPlanner()
    return _planner


def plan_and_execute(
    consulta: str,
    dominio: str,
    entidades: Dict[str, Any],
    intencao_original: str = None,
    usuario_id: int = None,
    usuario: str = "sistema",
    contexto_estruturado: str = None,
    conhecimento_negocio: str = None
) -> Dict[str, Any]:
    """Função de conveniência para planejar e executar."""
    return get_agent_planner().plan_and_execute(
        consulta=consulta,
        dominio=dominio,
        entidades=entidades,
        intencao_original=intencao_original,
        usuario_id=usuario_id,
        usuario=usuario,
        contexto_estruturado=contexto_estruturado,
        conhecimento_negocio=conhecimento_negocio
    )
