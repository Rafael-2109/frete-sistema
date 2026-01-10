"""
MemoryAgent - Subagente Haiku para gerenciamento inteligente de memorias.

Arquitetura simples:
- PRE-HOOK: get_relevant_context() - Analisa memorias + prompt → retorna contexto relevante
- POST-HOOK: analyze_and_save() - Analisa conversa → salva padroes/correcoes silenciosamente

Usa claude-haiku-4-5-20251001 para custo baixo (~$0.003/mensagem).
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

import anthropic

logger = logging.getLogger(__name__)

# Modelo Haiku para custo baixo
HAIKU_MODEL = "claude-haiku-4-5-20251001"

# =============================================================================
# PROMPTS DO SUBAGENTE DE MEMORIA (Haiku)
# Contexto: Sistema de logistica da Nacom Goya
# =============================================================================

PRE_HOOK_PROMPT = """Voce eh um agente de memoria para um sistema de logistica. Analise as memorias existentes e o prompt atual, retornando APENAS informacoes relevantes.

CONTEXTO DO SISTEMA:
- Gestao de pedidos, estoque, separacoes e fretes
- Clientes como Atacadao, Assai, Carrefour
- Produtos como palmito, azeitona, conservas
- Roteirizacao e expedicao

<memorias>
{memories}
</memorias>

<prompt>
{prompt}
</prompt>

BUSQUE MEMORIAS RELEVANTES SOBRE:
- Termos e sinonimos usados pelo usuario (ex: "VCD" = pedido)
- Regras de negocio especificas (ex: "FOB sempre manda completo")
- Padroes de trabalho do usuario (ex: "analisa Atacadao primeiro")
- Correcoes anteriores (ex: "campo X se chama Y")
- Preferencias de comunicacao

RESPOSTA (max 200 chars, texto direto):
- Se encontrou: [resumo das memorias relevantes]
- Se nao encontrou: NENHUMA

NAO invente informacoes."""

POST_HOOK_PROMPT = """Voce eh um agente de memoria para logistica. Analise a conversa e SALVE informacoes uteis.

<conversa>
USUARIO: {prompt}
ASSISTENTE: {response}
</conversa>

<memorias_existentes>
{memories}
</memorias_existentes>

SALVAR SEMPRE (prioridade alta):

1. COMANDOS EXPLICITOS DO USUARIO
   - "lembre que...", "anote que...", "guarde isso..."
   - "prefiro...", "gosto de...", "nao gosto de..."
   - "sempre faco...", "nunca faco..."
   → Salvar EXATAMENTE o que o usuario pediu

2. CORRECOES E FEEDBACK
   - Usuario corrige o agente: "nao eh assim", "errado", "na verdade..."
   - Usuario expressa frustacao: "ja falei", "de novo?"
   - Usuario elogia formato: "assim que eu gosto", "perfeito"
   → Salvar a correcao ou preferencia

3. PREFERENCIAS DE COMUNICACAO
   - "seja mais direto", "mais detalhes", "resumido"
   - "sem emoji", "pode usar emoji"
   - "formato de tabela", "lista simples"
   → Salvar preferencia de estilo

4. REGRAS DE NEGOCIO MENCIONADAS
   - Qualquer regra especifica: "cliente X sempre...", "produto Y nunca..."
   - Prioridades: "primeiro faz X, depois Y"
   - Restricoes: "nao pode...", "obrigatorio..."

5. PADROES DE TRABALHO
   - Rotinas: "toda segunda eu...", "antes de embarcar sempre..."
   - Sequencias preferidas de consulta
   - Clientes/produtos que acompanha frequentemente

6. FATOS SOBRE O USUARIO
   - Cargo, responsabilidades, equipe
   - Clientes que gerencia
   - Area de atuacao

NAO SALVAR (baixa prioridade):
- Numeros de pedidos especificos temporarios
- Informacao IDENTICA ja existente nas memorias

IMPORTANTE: Na duvida, SALVE. Eh melhor ter informacao extra do que perder algo util.

RESPOSTA (JSON estrito):
{{"action": "save", "type": "comando|correcao|preferencia|regra|padrao|fato", "category": "explicito|comunicacao|negocio|workflow|usuario", "content": "descricao clara e concisa", "tags": ["tag1", "tag2"]}}

OU se REALMENTE nada relevante:
{{"action": "none"}}

JSON APENAS:"""


class MemoryAgent:
    """
    Subagente Haiku para gerenciamento inteligente de memorias.

    Substitui o sistema complexo de hooks por chamadas diretas ao Haiku.
    """

    def __init__(self, app=None):
        self._app = app
        self._client = None

    def _get_client(self) -> anthropic.Anthropic:
        """Obtem cliente Anthropic (lazy load)."""
        if self._client is None:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY nao configurada")
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def _get_app(self):
        """Obtem Flask app."""
        if self._app:
            return self._app
        from flask import current_app
        return current_app._get_current_object()

    def _load_memories_sync(self, user_id: int) -> str:
        """Carrega memorias do usuario como string formatada."""
        from ..models import AgentMemory

        app = self._get_app()
        memories_text = []

        with app.app_context():
            memories = AgentMemory.query.filter_by(
                user_id=user_id,
                is_directory=False,
            ).all()

            for memory in memories:
                path = memory.path
                content = memory.content or ''
                memories_text.append(f"[{path}]\n{content}")

        return "\n\n".join(memories_text) if memories_text else "(nenhuma memoria salva)"

    def _save_memory_sync(self, user_id: int, path: str, content: str) -> bool:
        """
        Salva memoria no banco (APPEND se arquivo existir).

        Acumula memorias no mesmo arquivo para manter historico.
        """
        from ..models import AgentMemory
        from app import db

        app = self._get_app()

        try:
            with app.app_context():
                existing = AgentMemory.get_by_path(user_id, path)

                if existing:
                    # APPEND: Adiciona nova memoria ao conteudo existente
                    old_content = existing.content or ""
                    # Separa memorias com linha em branco
                    existing.content = f"{old_content}\n\n{content}".strip()
                else:
                    AgentMemory.create_file(user_id, path, content)

                db.session.commit()
                logger.info(f"[MEMORY_AGENT] Salvo: {path}")
                return True

        except Exception as e:
            logger.error(f"[MEMORY_AGENT] Erro ao salvar {path}: {e}")
            return False

    def get_relevant_context(self, user_id: int, prompt: str) -> str:
        """
        PRE-HOOK: Analisa memorias e retorna contexto relevante.

        Args:
            user_id: ID do usuario
            prompt: Prompt atual do usuario

        Returns:
            String com contexto relevante ou vazio
        """
        try:
            # Carrega memorias
            memories = self._load_memories_sync(user_id)

            # Se nao tem memorias, retorna vazio
            if memories == "(nenhuma memoria salva)":
                return ""

            # Chama Haiku para analisar
            client = self._get_client()

            response = client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": PRE_HOOK_PROMPT.format(
                        memories=memories,
                        prompt=prompt[:1000]  # Limita tamanho
                    )
                }]
            )

            result = response.content[0].text.strip()

            # Se nao encontrou nada relevante
            if result.upper() == "NENHUMA" or not result:
                return ""

            logger.debug(f"[MEMORY_AGENT] PRE-HOOK: {result[:100]}...")
            return result

        except Exception as e:
            logger.warning(f"[MEMORY_AGENT] Erro no PRE-HOOK: {e}")
            return ""

    def analyze_and_save(
        self,
        user_id: int,
        prompt: str,
        response: str,
    ) -> Dict[str, Any]:
        """
        POST-HOOK: Analisa conversa e salva padroes/correcoes.

        Args:
            user_id: ID do usuario
            prompt: Prompt do usuario
            response: Resposta do assistente

        Returns:
            Dict com resultado da analise
        """
        import json

        try:
            # Carrega memorias existentes
            memories = self._load_memories_sync(user_id)

            # Chama Haiku para analisar
            client = self._get_client()

            haiku_response = client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": POST_HOOK_PROMPT.format(
                        prompt=prompt[:1500],
                        response=response[:2000],
                        memories=memories[:3000]
                    )
                }]
            )

            result_text = haiku_response.content[0].text.strip()

            # Tenta parsear JSON
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                # Tenta extrair JSON do texto
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    logger.debug(f"[MEMORY_AGENT] Resposta nao-JSON: {result_text[:100]}")
                    return {"action": "none", "error": "invalid_json"}

            # Processa resultado
            if result.get("action") == "save":
                memory_type = result.get("type", "unknown")
                category = result.get("category", "geral")
                content = result.get("content", "")
                tags = result.get("tags", [])

                if content:
                    # Define path baseado na categoria
                    path_map = {
                        # Novas categorias (mais agressivas)
                        "explicito": "/memories/learned/explicito.xml",
                        "comunicacao": "/memories/preferences.xml",
                        "negocio": "/memories/learned/regras.xml",
                        "workflow": "/memories/learned/patterns.xml",
                        "usuario": "/memories/context/usuario.xml",
                        # Categorias legadas (compatibilidade)
                        "sinonimos": "/memories/learned/termos.xml",
                        "dominio": "/memories/corrections/dominio.xml",
                    }
                    path = path_map.get(category, "/memories/learned/auto.xml")

                    # Monta conteudo estruturado
                    tags_str = ", ".join(tags) if tags else ""
                    full_content = f"""<memoria type="{memory_type}" category="{category}">
<content>{content}</content>
<tags>{tags_str}</tags>
<detected_at>{datetime.now(timezone.utc).isoformat()}</detected_at>
<source>auto_haiku</source>
</memoria>"""

                    saved = self._save_memory_sync(user_id, path, full_content)

                    logger.info(
                        f"[MEMORY_AGENT] Salvo: type={memory_type} "
                        f"category={category} tags={tags}"
                    )

                    return {
                        "action": "saved",
                        "type": memory_type,
                        "category": category,
                        "path": path,
                        "tags": tags,
                        "saved": saved
                    }

            return {"action": "none"}

        except Exception as e:
            logger.warning(f"[MEMORY_AGENT] Erro no POST-HOOK: {e}")
            return {"action": "error", "error": str(e)}


# Singleton
_memory_agent: Optional[MemoryAgent] = None


def get_memory_agent(app=None) -> MemoryAgent:
    """Obtem instancia do MemoryAgent (singleton)."""
    global _memory_agent
    if _memory_agent is None:
        _memory_agent = MemoryAgent(app)
    return _memory_agent


def reset_memory_agent():
    """Reseta singleton."""
    global _memory_agent
    _memory_agent = None
