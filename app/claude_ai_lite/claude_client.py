"""
Cliente da API Claude - Wrapper simples e direto
Limite: 300 linhas (REGRA DE OURO)
"""

import os
import logging
import hashlib
import json
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

from app.claude_ai_lite.config import get_max_tokens

logger = logging.getLogger(__name__)

# Cache simples em memória (produção: usar Redis)
_cache: Dict[str, Dict] = {}
CACHE_TTL_SECONDS = 300  # 5 minutos


class ClaudeClient:
    """
    Cliente para API do Claude (Anthropic).
    Responsabilidade única: enviar prompts e receber respostas.
    """

    def __init__(self):
        self.api_key = os.environ.get('ANTHROPIC_API_KEY')
        self.model = "claude-opus-4-5-20251101"  # Claude Opus 4.5
        self.max_tokens = get_max_tokens('opus')  # Usa config dinâmica (16384 para opus)
        self._client = None

        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY nao configurada")

    def _get_client(self):
        """Lazy loading do cliente Anthropic"""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                logger.error("Biblioteca 'anthropic' nao instalada. Execute: pip install anthropic")
                raise
        return self._client

    def completar(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        use_cache: bool = True
    ) -> str:
        """
        Envia prompt para Claude e retorna resposta.

        Args:
            prompt: Pergunta/instrução do usuário
            system_prompt: Contexto do sistema (opcional)
            use_cache: Se deve usar cache (default: True)

        Returns:
            Resposta do Claude como string
        """
        if not self.api_key:
            return "Erro: API do Claude nao configurada. Verifique ANTHROPIC_API_KEY."

        # Verifica cache
        if use_cache:
            cache_key = self._gerar_cache_key(prompt, system_prompt)
            cached = self._get_from_cache(cache_key)
            if cached:
                logger.debug(f"Cache hit para consulta")
                return cached

        try:
            client = self._get_client()

            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": messages
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = client.messages.create(**kwargs)

            # Extrai texto da resposta
            resultado = response.content[0].text

            # Salva no cache
            if use_cache:
                self._save_to_cache(cache_key, resultado)

            logger.info(f"Claude respondeu com {len(resultado)} caracteres")
            return resultado

        except Exception as e:
            logger.error(f"Erro ao chamar Claude API: {e}")
            return f"Erro na comunicacao com Claude: {str(e)}"

    # =============================================================================
    # MÉTODOS REMOVIDOS (27/11/2025) - CÓDIGO MORTO
    # =============================================================================
    # - identificar_intencao(): Substituído por IntelligentExtractor
    # - responder_com_contexto(): Substituído por ResponseGenerator (responder.py)
    #
    # A extração de intenções é feita pelo IntelligentExtractor (intelligent_extractor.py)
    # que carrega capabilities dinamicamente do ToolRegistry.
    #
    # A geração de respostas é feita pelo ResponseGenerator (responder.py)
    # que usa system_base.py com capacidades dinâmicas.
    # =============================================================================

    def _gerar_cache_key(self, prompt: str, system_prompt: Optional[str]) -> str:
        """Gera chave única para cache"""
        conteudo = f"{prompt}:{system_prompt or ''}"
        return hashlib.md5(conteudo.encode()).hexdigest()

    def _get_from_cache(self, key: str) -> Optional[str]:
        """Recupera do cache se não expirou"""
        if key in _cache:
            item = _cache[key]
            if datetime.now() < item['expira']:
                return item['valor']
            else:
                del _cache[key]
        return None

    def _save_to_cache(self, key: str, valor: str):
        """Salva no cache com TTL"""
        _cache[key] = {
            'valor': valor,
            'expira': datetime.now() + timedelta(seconds=CACHE_TTL_SECONDS)
        }

        # Limpa cache antigo (máximo 100 itens)
        if len(_cache) > 100:
            self._limpar_cache_antigo()

    def _limpar_cache_antigo(self):
        """Remove itens expirados do cache"""
        agora = datetime.now()
        chaves_expiradas = [k for k, v in _cache.items() if agora >= v['expira']]
        for k in chaves_expiradas:
            del _cache[k]


# Instância global (singleton)
_cliente_global: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    """Retorna instância global do cliente Claude"""
    global _cliente_global
    if _cliente_global is None:
        _cliente_global = ClaudeClient()
    return _cliente_global
