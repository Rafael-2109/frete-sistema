"""
CodigoLoader - Carrega e cacheia codigos gerados pelo IA Trainer.

Responsabilidades:
1. Carregar codigos ativos do banco
2. Cachear em Redis (com fallback para memoria)
3. Filtrar por tipo (prompt, filtro, conceito, etc)
4. Buscar por gatilhos (trigger words)
5. Invalidar cache quando necessario

Uso pelo sistema:
- intent_prompt.py: busca prompts e conceitos ativos
- orchestrator.py: busca filtros a aplicar
- classifier.py: busca entidades aprendidas

Limite: 250 linhas
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache em memoria como fallback
_cache_memoria: Dict[str, Any] = {}
_cache_memoria_timestamp: Optional[datetime] = None
_cache_ttl = timedelta(minutes=5)


def _cache_valido_memoria() -> bool:
    """Verifica se cache em memoria ainda e valido."""
    global _cache_memoria_timestamp
    if _cache_memoria_timestamp is None:
        return False
    return datetime.now() - _cache_memoria_timestamp < _cache_ttl


def _redis_disponivel() -> bool:
    """Verifica se Redis esta disponivel para cache."""
    try:
        from ...cache import get_codigos_ativos  # noqa: F401
        return True
    except ImportError:
        return False


def invalidar_cache():
    """Invalida o cache (Redis e memoria)."""
    global _cache_memoria, _cache_memoria_timestamp

    # Invalida memoria
    _cache_memoria = {}
    _cache_memoria_timestamp = None

    # Invalida Redis se disponivel
    if _redis_disponivel():
        try:
            from ...cache import invalidar_codigos_ativos
            invalidar_codigos_ativos()
        except Exception:
            pass

    logger.info("[CODIGO_LOADER] Cache invalidado (Redis + memoria)")


def _carregar_do_banco() -> Dict[str, Any]:
    """Carrega todos os codigos ativos do banco e organiza."""
    try:
        from ..models import CodigoSistemaGerado

        codigos = CodigoSistemaGerado.query.filter_by(ativo=True).all()

        # Organiza por tipo
        cache_data = {
            'prompt': [],
            'filtro': [],
            'conceito': [],
            'entidade': [],
            'loader': [],
            'capability': [],
            'todos': [],
            'por_gatilho': {},
            'timestamp': datetime.now().isoformat()
        }

        for codigo in codigos:
            # Serializa codigo para cache
            codigo_dict = codigo.to_dict()
            cache_data['todos'].append(codigo_dict)
            tipo = codigo.tipo_codigo

            if tipo in cache_data:
                cache_data[tipo].append(codigo_dict)

            # Indexa por gatilhos
            for gatilho in (codigo.gatilhos or []):
                gatilho_lower = gatilho.lower().strip()
                if gatilho_lower not in cache_data['por_gatilho']:
                    cache_data['por_gatilho'][gatilho_lower] = []
                cache_data['por_gatilho'][gatilho_lower].append(codigo_dict)

        logger.info(f"[CODIGO_LOADER] Carregado do banco: {len(codigos)} codigos ativos")
        return cache_data

    except Exception as e:
        logger.error(f"[CODIGO_LOADER] Erro ao carregar do banco: {e}")
        return _cache_vazio()


def _cache_vazio() -> Dict[str, Any]:
    """Retorna estrutura de cache vazia."""
    return {
        'prompt': [], 'filtro': [], 'conceito': [],
        'entidade': [], 'loader': [], 'capability': [],
        'todos': [], 'por_gatilho': {}, 'timestamp': None
    }


def _garantir_cache() -> Dict[str, Any]:
    """Garante que o cache esteja carregado e valido."""
    global _cache_memoria, _cache_memoria_timestamp

    # Tenta Redis primeiro
    try:
        from ...cache import get_codigos_ativos, set_codigos_ativos

        cached = get_codigos_ativos()
        if cached:
            return cached

        # Redis miss - carrega do banco e cacheia
        dados = _carregar_do_banco()
        set_codigos_ativos(dados)
        return dados

    except Exception as e:
        logger.debug(f"[CODIGO_LOADER] Redis indisponivel, usando memoria: {e}")

    # Fallback para memoria
    if _cache_valido_memoria() and _cache_memoria:
        return _cache_memoria

    # Carrega do banco para memoria
    _cache_memoria = _carregar_do_banco()
    _cache_memoria_timestamp = datetime.now()
    return _cache_memoria


def listar_por_tipo(tipo: str) -> List[Dict]:
    """Lista codigos ativos de um tipo especifico."""
    cache = _garantir_cache()
    return cache.get(tipo, [])


def listar_todos() -> List[Dict]:
    """Lista todos os codigos ativos."""
    cache = _garantir_cache()
    return cache.get('todos', [])


def buscar_por_gatilho(texto: str) -> List[Dict]:
    """
    Busca codigos que correspondem a gatilhos no texto.

    Usa matching inteligente:
    1. Matching exato primeiro (mais confiável)
    2. Matching normalizado (sem acentos)
    3. Matching fuzzy com palavras-chave (para variações)

    Args:
        texto: Texto da pergunta do usuário

    Returns:
        Lista de códigos que matcharam, ordenados por relevância
    """
    cache = _garantir_cache()
    texto_lower = texto.lower()
    texto_normalizado = _normalizar_texto(texto_lower)
    palavras_texto = set(texto_normalizado.split())

    codigos_encontrados = []
    ids_vistos = set()

    # === FASE 1: Matching exato (mais confiável) ===
    for gatilho, codigos in cache.get('por_gatilho', {}).items():
        if gatilho in texto_lower:
            for codigo in codigos:
                codigo_id = codigo.get('id')
                if codigo_id not in ids_vistos:
                    codigo_com_score = codigo.copy()
                    codigo_com_score['_match_score'] = 100  # Score máximo
                    codigo_com_score['_match_tipo'] = 'exato'
                    codigos_encontrados.append(codigo_com_score)
                    ids_vistos.add(codigo_id)

    # === FASE 2: Matching normalizado (sem acentos) ===
    for gatilho, codigos in cache.get('por_gatilho', {}).items():
        gatilho_normalizado = _normalizar_texto(gatilho)
        if gatilho_normalizado in texto_normalizado:
            for codigo in codigos:
                codigo_id = codigo.get('id')
                if codigo_id not in ids_vistos:
                    codigo_com_score = codigo.copy()
                    codigo_com_score['_match_score'] = 90
                    codigo_com_score['_match_tipo'] = 'normalizado'
                    codigos_encontrados.append(codigo_com_score)
                    ids_vistos.add(codigo_id)

    # === FASE 3: Matching por palavras-chave (fuzzy) ===
    for gatilho, codigos in cache.get('por_gatilho', {}).items():
        palavras_gatilho = set(_normalizar_texto(gatilho).split())

        # Se todas as palavras do gatilho estão no texto (em qualquer ordem)
        if palavras_gatilho and palavras_gatilho.issubset(palavras_texto):
            for codigo in codigos:
                codigo_id = codigo.get('id')
                if codigo_id not in ids_vistos:
                    codigo_com_score = codigo.copy()
                    codigo_com_score['_match_score'] = 70
                    codigo_com_score['_match_tipo'] = 'palavras'
                    codigos_encontrados.append(codigo_com_score)
                    ids_vistos.add(codigo_id)

    # === FASE 4: Matching parcial (pelo menos 60% das palavras) ===
    for gatilho, codigos in cache.get('por_gatilho', {}).items():
        palavras_gatilho = set(_normalizar_texto(gatilho).split())
        if len(palavras_gatilho) >= 2:  # Apenas para gatilhos com 2+ palavras
            intersecao = palavras_gatilho.intersection(palavras_texto)
            cobertura = len(intersecao) / len(palavras_gatilho) if palavras_gatilho else 0

            if cobertura >= 0.6:  # 60% de cobertura
                for codigo in codigos:
                    codigo_id = codigo.get('id')
                    if codigo_id not in ids_vistos:
                        codigo_com_score = codigo.copy()
                        codigo_com_score['_match_score'] = int(50 * cobertura)
                        codigo_com_score['_match_tipo'] = 'parcial'
                        codigos_encontrados.append(codigo_com_score)
                        ids_vistos.add(codigo_id)

    # Ordena por score (maior primeiro)
    codigos_encontrados.sort(key=lambda x: x.get('_match_score', 0), reverse=True)

    return codigos_encontrados


def _normalizar_texto(texto: str) -> str:
    """
    Normaliza texto removendo acentos e caracteres especiais.

    Útil para matching fuzzy de gatilhos.
    """
    import unicodedata
    import re

    # Remove acentos
    texto_sem_acento = unicodedata.normalize('NFD', texto)
    texto_sem_acento = ''.join(
        c for c in texto_sem_acento
        if unicodedata.category(c) != 'Mn'
    )

    # Remove pontuação exceto espaço
    texto_limpo = re.sub(r'[^\w\s]', ' ', texto_sem_acento)

    # Normaliza espaços
    texto_limpo = re.sub(r'\s+', ' ', texto_limpo).strip()

    return texto_limpo.lower()


def buscar_filtros_para_dominio(dominio: str) -> List[Dict]:
    """Busca filtros ativos para um dominio especifico."""
    cache = _garantir_cache()
    filtros = cache.get('filtro', [])
    return [f for f in filtros if f.get('dominio') == dominio or f.get('dominio') is None]


def gerar_contexto_prompts() -> str:
    """Gera texto com prompts aprendidos para classificacao."""
    cache = _garantir_cache()
    prompts = cache.get('prompt', [])

    if not prompts:
        return ""

    linhas = ["=== REGRAS APRENDIDAS ==="]

    for prompt in prompts:
        gatilhos_str = ", ".join(f'"{g}"' for g in (prompt.get('gatilhos') or []))
        linhas.append(f"- Quando usuario diz: {gatilhos_str}")
        linhas.append(f"  -> {prompt.get('descricao_claude', '')}")
        if prompt.get('exemplos_uso'):
            for ex in prompt['exemplos_uso'][:2]:
                linhas.append(f"  Exemplo: \"{ex}\"")

    linhas.append("=== FIM DAS REGRAS APRENDIDAS ===\n")
    return "\n".join(linhas)


def gerar_contexto_conceitos() -> str:
    """Gera texto com conceitos de negocio aprendidos."""
    cache = _garantir_cache()
    conceitos = cache.get('conceito', [])

    if not conceitos:
        return ""

    linhas = ["=== CONCEITOS DE NEGOCIO APRENDIDOS ==="]

    for conceito in conceitos:
        gatilhos_str = ", ".join(f'"{g}"' for g in (conceito.get('gatilhos') or []))
        linhas.append(f"- {conceito.get('nome', '')} (termos: {gatilhos_str}):")
        linhas.append(f"  {conceito.get('descricao_claude', '')}")

    linhas.append("=== FIM DOS CONCEITOS ===\n")
    return "\n".join(linhas)


def gerar_contexto_entidades() -> str:
    """Gera texto com entidades customizadas para extracao."""
    cache = _garantir_cache()
    entidades = cache.get('entidade', [])

    if not entidades:
        return ""

    linhas = ["=== ENTIDADES CUSTOMIZADAS ==="]

    for entidade in entidades:
        linhas.append(f"- {entidade.get('nome', '')}: {entidade.get('descricao_claude', '')}")
        if entidade.get('exemplos_uso'):
            exemplos = ", ".join(f'"{e}"' for e in entidade['exemplos_uso'][:3])
            linhas.append(f"  Exemplos: {exemplos}")

    linhas.append("=== FIM DAS ENTIDADES ===\n")
    return "\n".join(linhas)


def buscar_codigo_por_nome(nome: str) -> Optional[Dict]:
    """Busca um codigo especifico pelo nome."""
    cache = _garantir_cache()

    for codigo in cache.get('todos', []):
        if codigo.get('nome') == nome:
            return codigo

    return None


def estatisticas() -> Dict[str, Any]:
    """Retorna estatisticas do cache."""
    cache = _garantir_cache()

    # Detecta tipo de cache em uso
    if _redis_disponivel():
        try:
            from ...cache import get_codigos_ativos
            tipo_cache = 'redis' if get_codigos_ativos() is not None else 'memoria'
        except Exception:
            tipo_cache = 'memoria'
    else:
        tipo_cache = 'memoria'

    return {
        'total': len(cache.get('todos', [])),
        'por_tipo': {
            'prompt': len(cache.get('prompt', [])),
            'filtro': len(cache.get('filtro', [])),
            'conceito': len(cache.get('conceito', [])),
            'entidade': len(cache.get('entidade', [])),
            'loader': len(cache.get('loader', [])),
            'capability': len(cache.get('capability', []))
        },
        'gatilhos_indexados': len(cache.get('por_gatilho', {})),
        'tipo_cache': tipo_cache,
        'timestamp': cache.get('timestamp')
    }
