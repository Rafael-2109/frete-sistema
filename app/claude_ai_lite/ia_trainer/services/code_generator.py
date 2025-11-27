"""
CodeGenerator - Geracao de codigo via Claude.

Recebe a decomposicao do usuario e gera:
- Filtros SQL/ORM
- Prompts para classificacao
- Loaders completos
- Entidades e conceitos

Segue o ROTEIRO DE SEGURANCA para geracao.

Limite: 350 linhas
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CodeGenerator:
    """
    Gera codigo usando Claude baseado nas explicacoes do usuario.

    Uso:
        generator = CodeGenerator()
        resultado = generator.gerar_codigo(
            pergunta="Tem item parcial pendente pro Atacadao 183?",
            decomposicao=[
                {"parte": "item parcial pendente", "explicacao": "...", "tipo": "filtro"},
                {"parte": "Atacadao 183", "explicacao": "cliente", "campo": "raz_social_red"}
            ]
        )
    """

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Lazy loading do cliente Claude."""
        if self._client is None:
            from ...claude_client import get_claude_client
            self._client = get_claude_client()
        return self._client

    def gerar_codigo(
        self,
        pergunta: str,
        decomposicao: List[Dict],
        contexto_codigo: str = None,
        conhecimento_negocio: str = None
    ) -> Dict[str, Any]:
        """
        Gera codigo baseado na decomposicao da pergunta.

        Args:
            pergunta: Pergunta original nao respondida
            decomposicao: Lista de partes explicadas pelo usuario
            contexto_codigo: Contexto adicional do codigo-fonte (opcional)
            conhecimento_negocio: NOVO v3.5.2 - Aprendizados de negocio (opcional)

        Returns:
            Dict com codigo gerado e metadados
        """
        # Monta o prompt para o Claude
        prompt_sistema = self._montar_prompt_sistema(contexto_codigo, conhecimento_negocio)
        prompt_usuario = self._montar_prompt_usuario(pergunta, decomposicao)

        # Chama o Claude
        client = self._get_client()
        resposta = client.completar(prompt_usuario, prompt_sistema, use_cache=False)

        # Parseia a resposta
        return self._parsear_resposta(resposta, pergunta, decomposicao)

    def _montar_prompt_sistema(self, contexto_codigo: str = None, conhecimento_negocio: str = None) -> str:
        """Monta o prompt de sistema para geracao de codigo."""

        # Busca contexto do codigo se nao fornecido
        if not contexto_codigo:
            from .codebase_reader import CodebaseReader
            reader = CodebaseReader()
            contexto_codigo = reader.gerar_contexto_para_claude()

        # NOVO v3.5.2: Inclui conhecimento de negocio se disponivel
        secao_conhecimento = ""
        if conhecimento_negocio:
            secao_conhecimento = f"""
=== CONHECIMENTO DO NEGOCIO (APRENDIZADOS) ===
{conhecimento_negocio}
=== FIM DO CONHECIMENTO ===

Use o conhecimento acima para entender melhor os termos de negocio
e gerar codigo mais preciso.
"""

        return f"""Voce e um gerador de codigo para consultas no sistema.

{contexto_codigo}
{secao_conhecimento}

=== IMPORTANTE: REGRAS DE NEGOCIO ===
As regras de negocio (quais campos usar, significado de cada Model, filtros corretos)
estao documentadas no CLAUDE.md acima. SIGA ESSAS REGRAS, nao invente.

=== SEGURANCA ===
- Codigo APENAS para CONSULTA (read-only)
- NUNCA gere commit(), add(), delete(), update()
- Sempre use .limit() para evitar milhares de registros

=== FORMATO DE RESPOSTA ===
Retorne APENAS um JSON valido:
{{
    "tipo_codigo": "loader|filtro|prompt|conceito|entidade",
    "nome": "nome_snake_case",
    "dominio": "carteira|estoque|fretes|etc",
    "gatilhos": ["palavra1", "variacao"],
    "definicao_tecnica": "objeto JSON para loader OU string para filtro simples",
    "models_referenciados": ["Model1"],
    "campos_referenciados": ["campo1"],
    "descricao_claude": "Quando usar este codigo",
    "exemplos_uso": ["Exemplo 1"],
    "raciocinio": "Seu raciocinio"
}}

=== TIPOS DE CODIGO ===

1. LOADER (preferido): JSON estruturado para consultas
   {{
       "modelo_base": "NomeModel",
       "filtros": [{{"campo": "x", "operador": "==", "valor": y}}],
       "campos_retorno": ["campo1", "campo2"],
       "ordenar": [{{"campo": "x", "direcao": "asc"}}],
       "limite": 100
   }}

2. FILTRO: Expressao simples (apenas quando nao precisa de JOINs/agregacoes)

3. CONCEITO: Definicao de termo de negocio

=== OPERADORES PERMITIDOS ===
Comparacao: "==", "!=", ">", ">=", "<", "<="
Texto: "ilike", "like", "contains", "startswith", "endswith"
Listas: "in", "not_in"
Nulos: "is_null", "is_not_null"
Range: "between" (valor = [min, max])
Data: "date_today", "date_gte_today", "date_lte_today", "date_this_week",
      "date_last_7_days", "date_this_month", "date_last_30_days",
      "date_gte_days_ago", "date_lte_days_ago"

=== QUANDO USAR LOADER vs FILTRO ===
Use LOADER quando: JOINs, agregacoes, filtros combinados, filtros de DATA
Use FILTRO apenas para: comparacoes simples de um campo

=== REGRA CRITICA DE DATA ===
Para filtros de data, SEMPRE use os operadores de data (date_this_week, etc).
NUNCA use func.date_trunc ou codigo Python como string.

Retorne SOMENTE o JSON."""

    def _montar_prompt_usuario(self, pergunta: str, decomposicao: List[Dict]) -> str:
        """Monta o prompt do usuario com a decomposicao."""

        partes_formatadas = []
        for i, parte in enumerate(decomposicao, 1):
            texto = f"{i}. \"{parte.get('parte', '')}\"\n"
            texto += f"   Explicacao: {parte.get('explicacao', '')}\n"
            if parte.get('tipo'):
                texto += f"   Tipo sugerido: {parte['tipo']}\n"
            if parte.get('campo'):
                texto += f"   Campo relacionado: {parte['campo']}\n"
            if parte.get('model'):
                texto += f"   Model: {parte['model']}\n"
            partes_formatadas.append(texto)

        return f"""PERGUNTA ORIGINAL NAO RESPONDIDA:
"{pergunta}"

DECOMPOSICAO EXPLICADA PELO USUARIO:

{chr(10).join(partes_formatadas)}

Com base nessa decomposicao, gere o codigo necessario para que eu consiga responder essa pergunta no futuro.

Considere:
1. Qual tipo de codigo e mais adequado (filtro, loader, prompt, etc)?
2. Como combinar as partes da decomposicao?
3. Quais Models e campos sao necessarios?
4. Quais variacoes da pergunta tambem devem funcionar?

Retorne o JSON com o codigo gerado."""

    def _parsear_resposta(
        self,
        resposta: str,
        pergunta: str,
        decomposicao: List[Dict]
    ) -> Dict[str, Any]:
        """Parseia a resposta do Claude."""

        try:
            # Verifica resposta vazia
            if not resposta or not resposta.strip():
                return {
                    'sucesso': False,
                    'erro': 'Resposta vazia do Claude. Verifique a conexao com a API.',
                    'resposta_raw': resposta
                }

            # Limpa resposta
            resposta_limpa = resposta.strip()

            # Remove blocos de codigo markdown se houver
            if resposta_limpa.startswith("```"):
                linhas = resposta_limpa.split("\n")
                # Remove primeira e ultima linha (``` json e ```)
                resposta_limpa = "\n".join(linhas[1:-1]).strip()

            # Se ainda estiver vazio apos limpeza
            if not resposta_limpa:
                return {
                    'sucesso': False,
                    'erro': 'Resposta do Claude estava vazia apos limpeza',
                    'resposta_raw': resposta
                }

            # Extrai o PRIMEIRO JSON valido da resposta
            # Isso evita "Extra data" quando Claude retorna texto adicional apos JSON
            codigo_gerado = self._extrair_primeiro_json(resposta_limpa)

            # Valida campos obrigatorios
            campos_obrigatorios = ['tipo_codigo', 'nome', 'definicao_tecnica', 'descricao_claude']
            for campo in campos_obrigatorios:
                if campo not in codigo_gerado:
                    return {
                        'sucesso': False,
                        'erro': f'Campo obrigatorio ausente: {campo}',
                        'resposta_raw': resposta
                    }

            # Adiciona metadados
            codigo_gerado['sucesso'] = True
            codigo_gerado['pergunta_original'] = pergunta
            codigo_gerado['decomposicao_usada'] = decomposicao
            codigo_gerado['gerado_em'] = datetime.now().isoformat()

            return codigo_gerado

        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON do Claude: {e}")
            return {
                'sucesso': False,
                'erro': f'Erro ao parsear resposta: {e}',
                'resposta_raw': resposta
            }

    def _extrair_primeiro_json(self, texto: str) -> Dict:
        """
        Extrai o PRIMEIRO objeto JSON valido de um texto.

        Usa um algoritmo de contagem de chaves para encontrar
        onde o JSON termina, evitando "Extra data" quando ha
        texto adicional apos o JSON.

        Args:
            texto: Texto contendo JSON (possivelmente com texto extra)

        Returns:
            Dict parseado do primeiro JSON encontrado

        Raises:
            json.JSONDecodeError: Se nao encontrar JSON valido
        """
        # Encontra o inicio do JSON
        inicio = texto.find('{')
        if inicio == -1:
            raise json.JSONDecodeError("Nenhum objeto JSON encontrado", texto, 0)

        # Conta chaves para encontrar o fim do JSON
        nivel = 0
        em_string = False
        escape = False
        fim = -1

        for i, char in enumerate(texto[inicio:], inicio):
            if escape:
                escape = False
                continue

            if char == '\\' and em_string:
                escape = True
                continue

            if char == '"' and not escape:
                em_string = not em_string
                continue

            if em_string:
                continue

            if char == '{':
                nivel += 1
            elif char == '}':
                nivel -= 1
                if nivel == 0:
                    fim = i + 1
                    break

        if fim == -1:
            raise json.JSONDecodeError("JSON mal formatado - chaves nao balanceadas", texto, inicio)

        # Extrai apenas o JSON
        json_str = texto[inicio:fim]

        # Parseia
        return json.loads(json_str)

    def refinar_codigo(
        self,
        codigo_atual: Dict,
        feedback: str,
        contexto_codigo: str = None
    ) -> Dict[str, Any]:
        """
        Refina codigo baseado no feedback do usuario.

        Args:
            codigo_atual: Codigo gerado anteriormente
            feedback: Feedback/questionamento do usuario
            contexto_codigo: Contexto adicional

        Returns:
            Dict com codigo refinado
        """
        prompt_sistema = self._montar_prompt_sistema(contexto_codigo)

        prompt_usuario = f"""CODIGO ATUAL GERADO:
```json
{json.dumps(codigo_atual, indent=2, ensure_ascii=False)}
```

FEEDBACK DO USUARIO:
{feedback}

Por favor, refine o codigo considerando o feedback. Mantenha o mesmo formato JSON.
Se o feedback indicar que algo esta errado, corrija.
Se for uma pergunta, responda no campo "raciocinio" e ajuste se necessario.

Retorne o JSON refinado."""

        client = self._get_client()
        resposta = client.completar(prompt_usuario, prompt_sistema, use_cache=False)

        return self._parsear_resposta(
            resposta,
            codigo_atual.get('pergunta_original', ''),
            codigo_atual.get('decomposicao_usada', [])
        )

    def sugerir_decomposicao(self, pergunta: str) -> Dict[str, Any]:
        """
        Sugere uma decomposicao inicial para a pergunta.

        Ajuda o usuario a comecar a decomposicao.
        """
        prompt = f"""Analise esta pergunta que o sistema nao conseguiu responder:

"{pergunta}"

Sugira como decompo-la em partes para ensinar o sistema. Para cada parte:
1. Identifique o termo/conceito
2. Explique o que provavelmente significa
3. Sugira o tipo (filtro, entidade, conceito)
4. Indique possivel campo/Model relacionado

Retorne um JSON com:
{{
    "sugestoes": [
        {{
            "parte": "texto da parte",
            "explicacao_sugerida": "o que provavelmente significa",
            "tipo_sugerido": "filtro|entidade|conceito",
            "campo_sugerido": "nome do campo se aplicavel",
            "model_sugerido": "nome do Model se aplicavel",
            "confianca": 0.0 a 1.0
        }}
    ],
    "analise": "Analise geral da pergunta",
    "dificuldade": "baixa|media|alta"
}}"""

        prompt_sistema = """Voce e um assistente que ajuda a decompor perguntas de negocio em partes tecnicas.
Conhece o sistema de logistica com Models como CarteiraPrincipal, Separacao, Pedido, etc.
Retorne APENAS o JSON solicitado."""

        client = self._get_client()
        resposta = client.completar(prompt, prompt_sistema, use_cache=False)

        try:
            resposta_limpa = resposta.strip()
            if resposta_limpa.startswith("```"):
                linhas = resposta_limpa.split("\n")
                resposta_limpa = "\n".join(linhas[1:-1])

            return {
                'sucesso': True,
                **json.loads(resposta_limpa)
            }
        except Exception as e:
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta_raw': resposta
            }
