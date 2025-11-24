"""
Cache Redis para Claude AI Lite.

Centraliza todo cache do modulo:
- Codigos aprendidos (IA Trainer)
- Contexto do README
- Classificacoes recentes
- Respostas frequentes

Usa o redis_cache global do sistema.
TTLs configurados por tipo de dado.

Limite: 200 linhas
"""

import logging
import hashlib
from typing import Any, Optional, Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)

# TTLs em segundos
TTL_CODIGOS_ATIVOS = 300      # 5 min - codigos do IA Trainer
TTL_README_CONTEXTO = 3600    # 1 hora - README muda pouco
TTL_CLASSIFICACAO = 60        # 1 min - classificacoes recentes
TTL_RESPOSTA = 180            # 3 min - respostas frequentes

# Prefixos de chave
PREFIX = "claude_lite"


def _get_redis():
    """Obtem instancia do Redis cache."""
    try:
        from app.utils.redis_cache import redis_cache
        return redis_cache
    except Exception as e:
        logger.debug(f"Redis nao disponivel: {e}")
        return None


def _gerar_chave(*parts) -> str:
    """Gera chave de cache padronizada."""
    return f"{PREFIX}:{':'.join(str(p) for p in parts)}"


def _hash_texto(texto: str) -> str:
    """Gera hash curto de texto para chave."""
    return hashlib.md5(texto.encode()).hexdigest()[:12]


# ==========================================
# CACHE DE CODIGOS ATIVOS (IA Trainer)
# ==========================================

def get_codigos_ativos() -> Optional[Dict]:
    """Busca codigos ativos do cache."""
    redis = _get_redis()
    if not redis or not redis.disponivel:
        return None

    return redis.get(_gerar_chave("codigos", "ativos"))


def set_codigos_ativos(codigos: Dict) -> bool:
    """Armazena codigos ativos no cache."""
    redis = _get_redis()
    if not redis or not redis.disponivel:
        return False

    return redis.set(
        _gerar_chave("codigos", "ativos"),
        codigos,
        TTL_CODIGOS_ATIVOS
    )


def invalidar_codigos_ativos():
    """Invalida cache de codigos ativos."""
    redis = _get_redis()
    if redis and redis.disponivel:
        redis.delete(_gerar_chave("codigos", "ativos"))
        logger.info("[CACHE] Codigos ativos invalidados")


# ==========================================
# CACHE DO README (Contexto para baixa confianca)
# ==========================================

def get_readme_contexto() -> Optional[str]:
    """Busca contexto do README do cache."""
    redis = _get_redis()
    if not redis or not redis.disponivel:
        return None

    return redis.get(_gerar_chave("readme", "contexto"))


def set_readme_contexto(contexto: str) -> bool:
    """Armazena contexto do README no cache."""
    redis = _get_redis()
    if not redis or not redis.disponivel:
        return False

    return redis.set(
        _gerar_chave("readme", "contexto"),
        contexto,
        TTL_README_CONTEXTO
    )


def carregar_readme_contexto() -> str:
    """
    Carrega contexto util do README.md.

    Extrai apenas secoes relevantes para classificacao:
    - Capacidades disponiveis
    - Intencoes reconhecidas
    - Exemplos de perguntas

    Usa cache Redis se disponivel.
    """
    # Tentar cache primeiro
    cached = get_readme_contexto()
    if cached:
        logger.debug("[CACHE] README contexto do cache")
        return cached

    # Carregar do arquivo
    try:
        readme_path = Path(__file__).parent / "README.md"

        if not readme_path.exists():
            logger.warning("[CACHE] README.md nao encontrado")
            return ""

        conteudo = readme_path.read_text(encoding='utf-8')

        # Extrair secoes relevantes
        contexto = _extrair_secoes_uteis(conteudo)

        # Cachear
        set_readme_contexto(contexto)
        logger.info(f"[CACHE] README carregado e cacheado ({len(contexto)} chars)")

        return contexto

    except Exception as e:
        logger.error(f"[CACHE] Erro ao carregar README: {e}")
        return ""


def _extrair_secoes_uteis(conteudo: str) -> str:
    """
    Extrai apenas secoes uteis do README para contexto.

    Secoes extraidas:
    - Capacidades Disponiveis (tabelas)
    - Intencoes Reconhecidas (tabela)
    - Sistema de Sugestoes (exemplos)
    """
    linhas = conteudo.split('\n')
    secoes_uteis = []

    # Secoes que queremos extrair
    secoes_alvo = [
        "## Capacidades Disponiveis",
        "## Intencoes Reconhecidas",
        "## Sistema de Sugestoes Inteligentes",
        "### Capacidades Simples",
        "### Capacidades Compostas"
    ]

    em_secao = False
    secao_atual = ""

    for i, linha in enumerate(linhas):
        # Detecta inicio de secao alvo
        for secao in secoes_alvo:
            if linha.strip().startswith(secao.replace("## ", "").replace("### ", "")):
                em_secao = True
                secao_atual = linha
                secoes_uteis.append(f"\n{linha}")
                break

        # Detecta fim de secao (proximo ## ou ###)
        if em_secao and linha.startswith("## ") and linha != secao_atual:
            if not any(linha.strip().startswith(s.replace("## ", "").replace("### ", "")) for s in secoes_alvo):
                em_secao = False
                continue

        # Adiciona linha se estamos em secao util
        if em_secao and not linha.startswith("## "):
            # Pula linhas vazias consecutivas
            if linha.strip() or (secoes_uteis and secoes_uteis[-1].strip()):
                secoes_uteis.append(linha)

    resultado = '\n'.join(secoes_uteis)

    # Limita tamanho maximo (para nao estourar prompt)
    max_chars = 4000
    if len(resultado) > max_chars:
        resultado = resultado[:max_chars] + "\n[... truncado ...]"

    return resultado


# ==========================================
# CACHE DE CLASSIFICACOES
# ==========================================

def get_classificacao(consulta: str, contexto_hash: str = "") -> Optional[Dict]:
    """Busca classificacao do cache."""
    redis = _get_redis()
    if not redis or not redis.disponivel:
        return None

    chave = _gerar_chave("class", _hash_texto(consulta + contexto_hash))
    return redis.get(chave)


def set_classificacao(consulta: str, classificacao: Dict, contexto_hash: str = "") -> bool:
    """Armazena classificacao no cache."""
    redis = _get_redis()
    if not redis or not redis.disponivel:
        return False

    chave = _gerar_chave("class", _hash_texto(consulta + contexto_hash))
    return redis.set(chave, classificacao, TTL_CLASSIFICACAO)


# ==========================================
# ESTATISTICAS
# ==========================================

def get_stats() -> Dict[str, Any]:
    """Retorna estatisticas do cache do Claude AI Lite."""
    redis = _get_redis()

    if not redis or not redis.disponivel:
        return {
            "disponivel": False,
            "motivo": "Redis nao conectado"
        }

    try:
        # Conta chaves do claude_lite
        chaves = redis.client.keys(f"{PREFIX}:*")

        return {
            "disponivel": True,
            "total_chaves": len(chaves) if chaves else 0,
            "ttls": {
                "codigos_ativos": TTL_CODIGOS_ATIVOS,
                "readme_contexto": TTL_README_CONTEXTO,
                "classificacao": TTL_CLASSIFICACAO,
                "resposta": TTL_RESPOSTA
            },
            "redis_info": redis.get_info_cache()
        }
    except Exception as e:
        return {
            "disponivel": False,
            "erro": str(e)
        }


def invalidar_tudo():
    """Invalida todo cache do Claude AI Lite."""
    redis = _get_redis()
    if redis and redis.disponivel:
        removidos = redis.flush_pattern(PREFIX)
        logger.info(f"[CACHE] Todo cache invalidado: {removidos} chaves")
        return removidos
    return 0
