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

        return f"""Voce e um gerador de codigo especializado para um sistema de logistica de uma industria de alimentos.

{contexto_codigo}
{secao_conhecimento}

=== ROTEIRO DE SEGURANCA - REGRAS OBRIGATORIAS ===

1. O codigo gerado deve ser APENAS PARA CONSULTA (READ-ONLY)
   - NUNCA gere codigo que altera, deleta ou insere dados
   - NUNCA use db.session.commit(), .add(), .delete(), .update()
   - NUNCA use SQL de escrita (INSERT, UPDATE, DELETE, DROP)

2. Imports permitidos (WHITELIST):
   - sqlalchemy: or_, and_, func, desc, asc
   - Models do app: CarteiraPrincipal, Separacao, Pedido, etc
   - datetime, Decimal
   - typing

3. Imports PROIBIDOS (BLACKLIST):
   - os, subprocess, sys, shutil
   - open(), file(), eval(), exec()
   - requests, urllib, socket

4. Performance:
   - Sempre use .limit() para evitar trazer milhares de registros
   - Evite SELECT sem filtros
   - Timeout maximo de 2 segundos

5. Validacao:
   - Todos os campos referenciados devem existir nos Models
   - Use nomes exatos dos campos conforme a estrutura mostrada

=== FORMATO DE RESPOSTA ===

Retorne APENAS um JSON valido com a estrutura:
{{
    "tipo_codigo": "filtro|loader|prompt|conceito|entidade",
    "nome": "nome_unico_snake_case",
    "dominio": "carteira|estoque|fretes|etc",
    "gatilhos": ["palavra1", "palavra2", "variacao"],
    "composicao": "descricao de como combina com outras partes (opcional)",
    "definicao_tecnica": "codigo/expressao para filtro/prompt/conceito OU objeto JSON para loader",
    "models_referenciados": ["Model1", "Model2"],
    "campos_referenciados": ["campo1", "campo2"],
    "descricao_claude": "Descricao para eu entender quando usar",
    "exemplos_uso": ["Exemplo de pergunta 1", "Exemplo 2"],
    "variacoes": "Notas sobre variacoes e casos especiais",
    "raciocinio": "Explique seu raciocinio e caminhos alternativos considerados"
}}

=== TIPOS DE CODIGO ===

1. FILTRO: Expressao ORM simples para filtrar dados
   definicao_tecnica: "CarteiraPrincipal.qtd_saldo_produto_pedido > 0"

2. LOADER: JSON ESTRUTURADO para consultas complexas (JOINs, agregacoes, filtros multiplos)
   definicao_tecnica deve ser um OBJETO JSON com esta estrutura:
   {{
       "modelo_base": "Separacao",
       "joins": [
           {{"modelo": "CarteiraPrincipal", "tipo": "left", "on": {{"local": "num_pedido", "remoto": "num_pedido"}}}}
       ],
       "filtros": [
           {{"campo": "raz_social_red", "operador": "ilike", "valor": "%$cliente%"}},
           {{"campo": "agendamento", "operador": "is_null"}},
           {{"campo": "sincronizado_nf", "operador": "==", "valor": false}}
       ],
       "campos_retorno": ["num_pedido", "raz_social_red", "qtd_saldo", "agendamento"],
       "agregacao": {{
           "tipo": "agrupar",
           "por": ["num_pedido", "raz_social_red"],
           "funcoes": [{{"func": "sum", "campo": "qtd_saldo", "alias": "total_qtd"}}]
       }},
       "ordenar": [{{"campo": "num_pedido", "direcao": "asc"}}],
       "limite": 100
   }}

   OPERADORES PERMITIDOS para filtros:
   - "==", "!=", ">", ">=", "<", "<=" (comparacao)
   - "ilike", "like" (texto, use % como wildcard)
   - "in", "not_in" (lista de valores)
   - "is_null", "is_not_null" (nulos)
   - "between" (intervalo, valor deve ser lista [min, max])
   - "contains", "startswith", "endswith" (texto)

   PARAMETROS DINAMICOS:
   - Use $nome_parametro para valores que serao substituidos na execucao
   - Ex: "%$cliente%" sera substituido pelo valor do parametro cliente

3. PROMPT: Regra para adicionar ao prompt de classificacao
   definicao_tecnica: "Se usuario perguntar sobre 'parcial pendente', significa..."

4. CONCEITO: Definicao de termo de negocio
   definicao_tecnica: "Item parcial pendente = parte faturada, parte na carteira"

5. ENTIDADE: Nova entidade para extracao de texto
   definicao_tecnica: "parcial_pendente: boolean"

=== PREFERENCIA POR LOADER ESTRUTURADO ===

SEMPRE prefira gerar LOADER quando:
- A pergunta envolve mais de um Model
- Precisa de JOINs entre tabelas
- Precisa de filtros combinados (AND/OR)
- Precisa de agregacoes (SUM, COUNT, etc)
- Envolve busca por cliente + alguma condicao

NUNCA gere codigo Python arbitrario. Use sempre o formato JSON estruturado para loaders.

Retorne SOMENTE o JSON, sem explicacoes adicionais fora do JSON."""

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
            # Limpa resposta
            resposta_limpa = resposta.strip()

            # Remove blocos de codigo markdown se houver
            if resposta_limpa.startswith("```"):
                linhas = resposta_limpa.split("\n")
                # Remove primeira e ultima linha (``` json e ```)
                resposta_limpa = "\n".join(linhas[1:-1])

            # Parseia JSON
            codigo_gerado = json.loads(resposta_limpa)

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
