"""
AgentPlanner - PROMPT 2: PLANEJAMENTO

RESPONSABILIDADE:
- Receber domínio, intenção e entidades do PROMPT 1 (intelligent_extractor)
- Planejar quais ferramentas usar e em que ordem
- Executar as etapas e consolidar resultados

FONTE DE DADOS (dinâmica):
- Ferramentas: via ToolRegistry.formatar_para_prompt()
- Schema: via ToolRegistry.formatar_schema_resumido()
- Configurações: via config.py

FILOSOFIA:
- É uma CAMADA dentro do orchestrator, não um orquestrador paralelo
- Substitui o trecho: find_capability() -> cap.executar()
- Permite múltiplas etapas de execução (default: 5, máximo: 10)
- Claude pode solicitar mais etapas com justificativa
- Usa resultado de etapas anteriores para alimentar próximas

FLUXO:
1. Recebe pergunta + domínio + entidades (do PROMPT 1)
2. Claude planeja quais ferramentas usar e em que ordem
3. Executa cada etapa, passando resultados anteriores
4. Retorna dados consolidados para o responder (PROMPT 3)

REGRAS DE FALLBACK:
- Se nenhuma ferramenta resolve: tenta AutoLoader (apenas para consultas)
- AutoLoader só roda se não resolveu nas etapas permitidas
- AutoLoader marca resultado como "experimental"

Criado em: 26/11/2025
Atualizado: 27/11/2025 - Documentação arquitetura de prompts
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


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
            # 1. Obtém ferramentas disponíveis
            # IMPORTANTE: NÃO filtra por domínio - Claude deve ter acesso a TUDO
            # O domínio é apenas uma SUGESTÃO do extrator, não uma RESTRIÇÃO
            registry = self._get_tool_registry()

            # Ferramentas: traz do domínio + loader_generico (sempre disponível)
            ferramentas = registry.listar_ferramentas(dominio=dominio)
            ferramentas_prompt = registry.formatar_para_prompt(ferramentas)

            # Schema: SEMPRE completo - Claude precisa saber de TODAS as tabelas
            # Isso permite que ele use loader_generico para qualquer consulta
            schema_prompt = registry.formatar_schema_resumido(dominio=None)  # None = COMPLETO

            # 2. Claude planeja as etapas
            plano = self._planejar(
                consulta=consulta,
                ferramentas_prompt=ferramentas_prompt,
                schema_prompt=schema_prompt,
                entidades=entidades,
                contexto_estruturado=contexto_estruturado,
                conhecimento_negocio=conhecimento_negocio
            )

            # 2.1 VALIDAÇÃO: Garante que entidades críticas estão nos filtros
            if plano.get('etapas'):
                plano = self._validar_e_corrigir_plano(plano, entidades)

            if not plano.get('etapas'):
                # Claude não conseguiu planejar
                logger.warning(f"[AGENT_PLANNER] Claude não retornou etapas para: {consulta[:50]}")
                return self._tentar_fallback(
                    consulta, dominio, entidades, intencao_original,
                    usuario_id, usuario, conhecimento_negocio, resultado
                )

            # 3. Executa cada etapa (máximo dinâmico via config)
            # DUAS LISTAS: brutos (com dados) para encadeamento, resumo para log
            resultados_brutos = []
            etapas_resumo = []
            dados_acumulados = []

            # Obtém máximo de etapas (pode ser maior se Claude justificou)
            from ..config import get_max_etapas
            max_etapas = get_max_etapas(plano)

            for i, etapa in enumerate(plano['etapas'][:max_etapas]):
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

                # IMPORTANTE: Preserva campos especiais de capabilities (opcoes, analise, etc)
                # Isso permite que capabilities como analisar_disponibilidade funcionem
                # v2.0: Adicionado tipo_consulta, resumo para pedidos_abertos_disponibilidade
                for campo_especial in ['opcoes', 'analise', 'carga_sugerida', 'ja_separado',
                                       'num_pedido', 'cliente', 'valor_total_pedido', 'total_pallets',
                                       'tipo_consulta', 'resumo']:
                    if resultado_etapa.get(campo_especial) is not None:
                        resultado[campo_especial] = resultado_etapa[campo_especial]

            # 4. Consolida resultados
            resultado['etapas_executadas'] = etapas_resumo
            resultado['dados'] = dados_acumulados

            # total_encontrado usa dados OU total de opcoes (o que for maior)
            total_opcoes = len(resultado.get('opcoes', []))
            resultado['total_encontrado'] = max(len(dados_acumulados), total_opcoes)

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

        # Obtém configurações de etapas
        from ..config import get_config
        config = get_config()
        max_etapas_default = config.planejamento.max_etapas_default
        max_etapas_complexas = config.planejamento.max_etapas_complexas
        usar_diretrizes = config.planejamento.usar_diretrizes_flexiveis

        # Monta contexto
        contexto_extra = ""
        if contexto_estruturado:
            contexto_extra += f"\n=== ESTADO DA CONVERSA ===\n{contexto_estruturado}\n"
        if conhecimento_negocio:
            contexto_extra += f"\n=== CONHECIMENTO DO NEGÓCIO ===\n{conhecimento_negocio}\n"

        # Monta seção de filtros (flexível ou rígida baseado na config)
        if usar_diretrizes:
            secao_filtros = """=== DIRETRIZES DE FILTROS ===

SEGURANÇA DE DADOS (obrigatório):
- Quando há cliente/pedido específico no contexto, inclua o filtro correspondente
- Exceção: consultas agregadas/estatísticas (ex: "total faturado hoje") podem não filtrar por cliente

BOAS PRÁTICAS (recomendado):
- Inclua campos de identificação (raz_social_red, num_pedido) no retorno
- Use "ilike" com "%" para buscas de texto (ex: "%ATACADAO%")
- Retorne apenas dados relevantes para a pergunta

SE PRECISAR DIVERGIR DAS DIRETRIZES:
- Adicione "justificativa_filtro": "motivo" no JSON
- Exemplo: ranking de clientes não filtra por cliente específico"""
        else:
            secao_filtros = """⚠️ REGRAS CRÍTICAS:

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
- SEMPRE inclua os campos de identificação para que o usuário saiba de quem são os dados"""

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
3. Se precisar combinar dados, use múltiplas etapas (default: {max_etapas_default})
   - Se precisar de MAIS etapas para consultas complexas, adicione no JSON:
     "etapas_necessarias": N,
     "justificativa_etapas_extras": "explicação do motivo"
   - Máximo absoluto: {max_etapas_complexas} etapas
4. Passe os parâmetros corretos baseado nas entidades disponíveis

{secao_filtros}

ENTIDADES DISPONÍVEIS (USE COMO FILTROS QUANDO APLICÁVEL):
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
                "ordenar": [{{"campo": "nome_campo", "direcao": "desc"}}],
                "limite": 100
            }},
            "usar_resultado_de": null,
            "descricao": "o que essa etapa faz"
        }}
    ],
    "explicacao": "Por que esse plano resolve a pergunta"
}}

Para loader_generico COM ORDENAÇÃO (para "maiores", "menores", "top N"):
{{
    "etapas": [
        {{
            "ferramenta": "loader_generico",
            "params": {{}},
            "loader_json": {{
                "modelo_base": "CarteiraPrincipal",
                "filtros": [
                    {{"campo": "data_pedido", "operador": ">=", "valor": "2025-11-24"}}
                ],
                "campos_retorno": ["num_pedido", "raz_social_red", "valor_total_calculado"],
                "ordenar": [{{"campo": "qtd_saldo_produto_pedido", "direcao": "desc"}}],
                "limite": 3
            }},
            "descricao": "Busca os 3 maiores pedidos por quantidade"
        }}
    ],
    "explicacao": "Usa ordenação para encontrar maiores/menores"
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

ORDENAÇÃO DISPONÍVEL: "ordenar": [{{"campo": "nome", "direcao": "desc|asc"}}]
USE ORDENAÇÃO quando o usuário perguntar "maiores", "menores", "top", "ranking"

=== AUTONOMIA DO LOADER_GENERICO ===

O loader_generico é sua FERRAMENTA PRINCIPAL para consultas não cobertas por capabilities.
Você tem AUTONOMIA para usá-lo em QUALQUER tabela listada no schema.

TABELAS DISPONÍVEIS (use o nome exato):
- CarteiraPrincipal: pedidos na carteira (qtd_saldo_produto_pedido, preco_produto_pedido)
- Separacao: separações criadas (qtd_saldo, valor_saldo, sincronizado_nf)
- Pedido: VIEW agregada (valor_saldo_total, peso_total)
- FaturamentoProduto: NFs emitidas (valor_produto_faturado, qtd_produto_faturado, data_fatura)
- Embarque: embarques (valor_total, peso_total, pallet_total)
- MovimentacaoEstoque: movimentações de estoque
- CadastroPalletizacao: dados de produtos (palletizacao, peso_bruto)
- Frete: fretes

CAMPOS COMUNS DE VALOR:
- CarteiraPrincipal: Para valor total use expressão "preco_produto_pedido * qtd_saldo_produto_pedido"
- FaturamentoProduto: valor_produto_faturado (JÁ É o valor total do item - use este!)
- Separacao: valor_saldo (campo direto de valor)
- Pedido: valor_saldo_total (VIEW com valor já calculado)
- Embarque: valor_total

EXPRESSÕES MATEMÁTICAS SUPORTADAS NA AGREGAÇÃO:
- Formato: "campo1 * campo2" (com espaços ao redor do operador)
- Operadores: *, +, -, /
- Exemplo para valor total de pedido:
  {{"func": "sum", "campo": "preco_produto_pedido * qtd_saldo_produto_pedido", "alias": "valor_total"}}

DICA PARA "MAIORES PEDIDOS POR VALOR":
- Use agregação com expressão: sum(preco_produto_pedido * qtd_saldo_produto_pedido)
- Agrupe por num_pedido e raz_social_red
- Ordene pelo alias (ex: valor_total DESC)

CAMPOS COMUNS DE DATA:
- CarteiraPrincipal: data_pedido
- FaturamentoProduto: data_fatura
- Separacao: criado_em, expedicao, agendamento
- Embarque: data_prevista_embarque, data_embarque

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

=== ENRIQUECER CONTEXTO (AUTONOMIA TOTAL) ===

Use enriquecer_contexto quando identificar que FALTA INFORMAÇÃO para responder.
VOCÊ define O QUE precisa e COMO buscar. O sistema apenas executa.

QUANDO USAR:
- Termo ambíguo: "João" pode ser cliente, vendedor ou produto
- Validação necessária: Verificar se pedido/cliente existe antes de prosseguir
- Contexto incompleto: Estado não tem info que você precisa

FORMATO:
{{
    "ferramenta": "enriquecer_contexto",
    "params": {{
        "motivo": "Explicação de POR QUE você precisa dessa informação",
        "loader_json": {{
            "modelo_base": "TabelaQueVoceEscolher",
            "filtros": [...],
            "campos_retorno": [...],
            "limite": N
        }}
    }},
    "descricao": "O que essa busca adicional faz"
}}

EXEMPLO - Resolver ambiguidade:
{{
    "ferramenta": "enriquecer_contexto",
    "params": {{
        "motivo": "Usuário mencionou 'João' sem especificar se é cliente ou vendedor",
        "loader_json": {{
            "modelo_base": "CarteiraPrincipal",
            "filtros": [{{"campo": "vendedor", "operador": "ilike", "valor": "%JOAO%"}}],
            "campos_retorno": ["vendedor"],
            "agregacao": {{"por": ["vendedor"], "funcoes": []}},
            "limite": 5
        }}
    }},
    "descricao": "Verifica se João é vendedor"
}}

DICA: Use enriquecer_contexto ANTES das etapas principais quando perceber ambiguidade.
O resultado fica disponível para as etapas seguintes via usar_resultado_de.

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

=== NOTA SOBRE OS EXEMPLOS ===

Os exemplos acima são ILUSTRATIVOS. Você pode:
- Adaptar a estrutura para casos únicos
- Combinar abordagens de diferentes exemplos
- Criar estruturas diferentes se necessário

O importante é que o JSON seja válido e tenha:
- "etapas": lista de etapas a executar (obrigatório)
- Cada etapa com "ferramenta" e "descricao" (obrigatório)
- "etapas_necessarias" e "justificativa_etapas_extras" (se precisar de mais etapas)
- "justificativa_filtro" (se precisar divergir das diretrizes de filtro)

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

    # Métodos sugeridos pelo Claude para melhoria do plano

    def _extrair_filtros_flat(self, filtros) -> List[Dict]:
        """
        Extrai filtros de estrutura aninhada (and/or) para lista flat.
        
        Suporta:
        - Lista simples: [filtro1, filtro2]
        - Dict com and/or: {"and": [filtro1, filtro2]}
        - Aninhados: {"and": [filtro1, {"or": [filtro2, filtro3]}]}
        """
        if not filtros:
            return []
        
        if isinstance(filtros, list):
            resultado = []
            for f in filtros:
                resultado.extend(self._extrair_filtros_flat(f))
            return resultado
        
        if isinstance(filtros, dict):
            if 'and' in filtros:
                return self._extrair_filtros_flat(filtros['and'])
            if 'or' in filtros:
                return self._extrair_filtros_flat(filtros['or'])
            if 'campo' in filtros:
                return [filtros]
        
        return []

    def _validar_e_corrigir_plano(self, plano: Dict, entidades: Dict) -> Dict:
        """
        Valida que o plano respeita as entidades extraídas.
        Se filtros obrigatórios estiverem ausentes, INJETA automaticamente.
        
        Args:
            plano: Plano gerado pelo Claude
            entidades: Entidades extraídas (devem virar filtros)
        
        Returns:
            Plano corrigido (pode ser o mesmo se já estava correto)
        """
        if not plano.get('etapas'):
            return plano
        
        # Campos que DEVEM estar nos filtros se presentes nas entidades
        # Formato: campo -> (operador, função para formatar valor)
        campos_obrigatorios = {
            'raz_social_red': ('ilike', lambda v: f'%{v.upper()}%'),
            'num_pedido': ('==', lambda v: v),
            'cod_produto': ('ilike', lambda v: f'%{v}%'),
        }
        
        correcoes_feitas = []
        
        for i, etapa in enumerate(plano.get('etapas', [])):
            loader_json = etapa.get('loader_json')
            if not loader_json:
                continue
            
            filtros = loader_json.get('filtros', [])
            
            # Extrai campos já presentes nos filtros
            filtros_flat = self._extrair_filtros_flat(filtros)
            campos_presentes = {f.get('campo') for f in filtros_flat}
            
            # Verifica cada campo obrigatório
            for campo, (operador, formatar_valor) in campos_obrigatorios.items():
                valor_entidade = entidades.get(campo)
                
                # Se entidade existe mas não está nos filtros -> INJETAR
                if valor_entidade and campo not in campos_presentes:
                    novo_filtro = {
                        'campo': campo,
                        'operador': operador,
                        'valor': formatar_valor(valor_entidade)
                    }
                    
                    # Injeta o filtro
                    if isinstance(filtros, list):
                        filtros.append(novo_filtro)
                    elif isinstance(filtros, dict):
                        if 'and' in filtros:
                            filtros['and'].append(novo_filtro)
                        elif 'or' in filtros:
                            # Transforma em AND com o OR existente + novo filtro
                            loader_json['filtros'] = {'and': [filtros, novo_filtro]}
                        else:
                            # Filtro único, transforma em lista
                            loader_json['filtros'] = [filtros, novo_filtro]
                    else:
                        # Sem filtros, cria lista nova
                        loader_json['filtros'] = [novo_filtro]
                    
                    correcoes_feitas.append(f"Etapa {i+1}: injetado {campo}={valor_entidade}")
            
            # Garante que campos de identificação estão no retorno
            campos_retorno = loader_json.get('campos_retorno', [])
            for campo in ['raz_social_red', 'num_pedido']:
                if campo in entidades and entidades[campo]:
                    if campo not in campos_retorno:
                        campos_retorno.append(campo)
                        correcoes_feitas.append(f"Etapa {i+1}: adicionado {campo} ao retorno")
            
            if campos_retorno:
                loader_json['campos_retorno'] = campos_retorno
        
        if correcoes_feitas:
            logger.warning(f"[AGENT_PLANNER] Plano corrigido: {correcoes_feitas}")
        
        return plano            

    # Fim dos métodos sugeridos pelo Claude

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

        elif tipo == 'enriquecer_contexto':
            return self._executar_enriquecer_contexto(params_final, usuario_id)

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

    def _obter_filtros_aprendidos(self, usuario_id: int) -> List[Dict]:
        """
        Obtém filtros aprendidos do IA Trainer.
        
        Busca em CodigoSistemaGerado onde tipo_codigo='filtro' e ativo=True.
        
        Returns:
            Lista de filtros no formato estruturado que aplicar_filtros_aprendidos espera
        """
        try:
            from ..ia_trainer.models import CodigoSistemaGerado
            import json
            
            # Busca filtros ativos
            codigos = CodigoSistemaGerado.query.filter_by(
                tipo_codigo='filtro',
                ativo=True
            ).all()
            
            filtros = []
            for codigo in codigos:
                try:
                    # definicao_tecnica pode ser JSON string ou dict
                    definicao = codigo.definicao_tecnica
                    if isinstance(definicao, str):
                        # Tenta parsear como JSON estruturado
                        try:
                            definicao_dict = json.loads(definicao)
                            # Formato estruturado: {"campo": "x", "operador": "==", "valor": "y"}
                            if 'campo' in definicao_dict and 'operador' in definicao_dict:
                                filtros.append({
                                    'nome': codigo.nome,
                                    'campo': definicao_dict['campo'],
                                    'operador': definicao_dict['operador'],
                                    'valor': definicao_dict.get('valor'),
                                    'modelo': codigo.models_referenciados[0] if codigo.models_referenciados else None
                                })
                                continue
                        except json.JSONDecodeError:
                            pass
                        
                        # Formato SQL direto (legado)
                        filtros.append({
                            'nome': codigo.nome,
                            'filtro': definicao,  # SQL direto
                            'modelo': codigo.models_referenciados[0] if codigo.models_referenciados else None
                        })
                    elif isinstance(definicao, dict):
                        # Já é dict estruturado
                        filtros.append({
                            'nome': codigo.nome,
                            'campo': definicao.get('campo'),
                            'operador': definicao.get('operador'),
                            'valor': definicao.get('valor'),
                            'modelo': codigo.models_referenciados[0] if codigo.models_referenciados else None
                        })
                        
                except Exception as e:
                    logger.warning(f"[AGENT_PLANNER] Erro ao processar filtro '{codigo.nome}': {e}")
                    continue
            
            if filtros:
                logger.info(f"[AGENT_PLANNER] {len(filtros)} filtros aprendidos carregados")
            
            return filtros
            
        except Exception as e:
            logger.warning(f"[AGENT_PLANNER] Erro ao carregar filtros aprendidos: {e}")
            return []

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

    def _executar_enriquecer_contexto(self, params: Dict, usuario_id: int) -> Dict[str, Any]:
        """
        Enriquece o contexto permitindo que Claude defina O QUE e COMO buscar.

        Esta ferramenta dá TOTAL AUTONOMIA ao Claude:
        - Claude define o motivo (por que precisa)
        - Claude define o loader_json (como buscar)
        - O sistema apenas executa

        Params esperados:
        - motivo: Por que Claude precisa dessa informação
        - loader_json: Query JSON para buscar (mesmo formato do loader_generico)

        Exemplo de uso pelo Claude:
        {
            "ferramenta": "enriquecer_contexto",
            "params": {
                "motivo": "Preciso validar se 'João' é cliente ou vendedor antes de prosseguir",
                "loader_json": {
                    "modelo_base": "CarteiraPrincipal",
                    "filtros": [{"campo": "vendedor", "operador": "ilike", "valor": "%JOAO%"}],
                    "campos_retorno": ["vendedor"],
                    "agregacao": {"por": ["vendedor"], "funcoes": []},
                    "limite": 5
                }
            },
            "descricao": "Verifica se João é vendedor"
        }
        """
        motivo = params.get('motivo', 'Não especificado')
        loader_json = params.get('loader_json', {})

        logger.info(f"[AGENT_PLANNER] Enriquecendo contexto: motivo='{motivo}'")

        # Se Claude não forneceu loader_json, tenta usar params como loader
        if not loader_json and 'modelo_base' in params:
            loader_json = {k: v for k, v in params.items() if k not in ('motivo', '_dados_anteriores')}

        if not loader_json:
            return {
                'sucesso': False,
                'erro': 'loader_json não fornecido. Claude deve definir como buscar.',
                'dados': [],
                'contexto_adicional': f"Motivo: {motivo}"
            }

        # Executa o loader definido pelo Claude
        try:
            from ..ia_trainer.services.loader_executor import executar_loader

            resultado = executar_loader(loader_json)

            return {
                'sucesso': resultado.get('sucesso', False),
                'dados': resultado.get('dados', []),
                'total': resultado.get('total', 0),
                'erro': resultado.get('erro'),
                'contexto_adicional': f"[Enriquecimento] {motivo}: {resultado.get('total', 0)} resultados"
            }

        except Exception as e:
            logger.error(f"[AGENT_PLANNER] Erro ao enriquecer contexto: {e}")
            return {'sucesso': False, 'erro': str(e), 'dados': []}

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
