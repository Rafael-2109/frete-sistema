# -*- coding: utf-8 -*-
"""
Utilitários compartilhados para resolução de favorecidos/pagadores
==================================================================

Funções de tokenização, normalização e constantes usadas tanto pelo
FavorecidoResolverService (saída) quanto pelo RecebimentoResolverService (entrada).

Autor: Sistema de Fretes
Data: 2026-02-11
"""

import re
import logging
import unicodedata
from typing import List, Optional, Set, Tuple

from app import db

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES DE TOKENIZAÇÃO
# =============================================================================

# Stop words para tokenização de nomes de fornecedores/clientes
STOP_WORDS_NOME: Set[str] = {
    # Sufixos legais
    'LTDA', 'SA', 'ME', 'EIRELI', 'EPP', 'LTD', 'CIA', 'SS', 'SCP',
    # Genéricos de indústria (presentes em 30%+ dos fornecedores)
    'TRANSPORTES', 'TRANSPORTE', 'TRANSP', 'LOGISTICA', 'LOG',
    'INDUSTRIA', 'COMERCIO', 'COMERCIAL', 'COML', 'COMER', 'COM',
    'DISTRIBUICAO', 'DISTRIBUIDORA', 'DISTRIBUIDOR', 'DIST',
    'ALIMENTOS', 'ALIMENTICIOS', 'ALIM', 'PRODUTOS', 'PROD',
    'SERVICOS', 'EMBALAGENS', 'REPRESENTACAO', 'REPRESENTACOES',
    'REPRESENT', 'ASSESSORIA', 'RODOVIARIOS', 'RODOVIARIO', 'ROD',
    # Preposições e artigos
    'DE', 'DO', 'DA', 'DOS', 'DAS', 'EM', 'NO', 'NA', 'E', 'A', 'O',
    # Geográficos genéricos
    'BRASIL', 'CARGAS', 'CARGA',
}

# Tokens conhecidos que NÃO devem ser removidos por parecerem truncados
TOKENS_CURTOS_VALIDOS: Set[str] = {
    'LA', 'JM', 'VPS', 'GR', 'JBS', 'BRF', '3M', 'LG', 'HP',
}


# =============================================================================
# FUNÇÕES DE NORMALIZAÇÃO
# =============================================================================

def normalizar_cnpj(cnpj_raw: str) -> str:
    """
    Normaliza CNPJ para formato XX.XXX.XXX/XXXX-XX ou CPF para XXX.XXX.XXX-XX.

    Args:
        cnpj_raw: CNPJ/CPF em qualquer formato

    Returns:
        CNPJ/CPF formatado ou string original se inválido
    """
    if not cnpj_raw:
        return ''
    digitos = re.sub(r'\D', '', cnpj_raw)
    if len(digitos) == 14:
        return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:14]}"
    if len(digitos) == 11:
        return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:11]}"
    return cnpj_raw


def normalizar_cnpj_somente_digitos(cnpj_raw: str) -> str:
    """
    Remove todos os caracteres não numéricos do CNPJ/CPF.

    Args:
        cnpj_raw: CNPJ/CPF em qualquer formato

    Returns:
        Apenas dígitos (ex: '61724241000178')
    """
    if not cnpj_raw:
        return ''
    return re.sub(r'\D', '', cnpj_raw)


def extrair_raiz_cnpj(cnpj: str) -> str:
    """
    Extrai os 8 primeiros dígitos (raiz) de um CNPJ.

    Args:
        cnpj: CNPJ em qualquer formato

    Returns:
        8 dígitos da raiz ou string vazia
    """
    digitos = normalizar_cnpj_somente_digitos(cnpj)
    return digitos[:8] if len(digitos) >= 8 else ''


def remover_acentos(texto: str) -> str:
    """
    Remove acentos de uma string.

    Args:
        texto: Texto com possíveis acentos

    Returns:
        Texto sem acentos
    """
    nfkd = unicodedata.normalize('NFKD', texto)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


# =============================================================================
# FUNÇÕES DE TOKENIZAÇÃO
# =============================================================================

def tokenizar_nome(nome: str) -> List[str]:
    """
    Tokeniza um nome de fornecedor/cliente, removendo stop words e tokens genéricos.

    Retorna apenas tokens discriminantes para busca.

    Args:
        nome: Nome completo (razão social, nome fantasia, etc.)

    Returns:
        Lista de tokens discriminantes (uppercase, sem acentos)
    """
    if not nome:
        return []

    # Normalizar: UPPER, remover acentos, remover pontuação
    nome_upper = remover_acentos(nome.upper())
    nome_limpo = re.sub(r'[.\-/,()\'\"&]', ' ', nome_upper)

    # Tokenizar
    tokens = nome_limpo.split()

    # Filtrar: remover stop words e tokens curtos (≤ 2 chars)
    tokens_filtrados = [
        t for t in tokens
        if t not in STOP_WORDS_NOME and (len(t) > 2 or t in TOKENS_CURTOS_VALIDOS)
    ]

    # Remover último token se parecer truncado (< 5 chars, não é token conhecido)
    if tokens_filtrados:
        ultimo = tokens_filtrados[-1]
        if (len(ultimo) < 5
                and ultimo not in TOKENS_CURTOS_VALIDOS
                and ultimo not in STOP_WORDS_NOME):
            tokens_filtrados = tokens_filtrados[:-1]

    return tokens_filtrados


# =============================================================================
# FUNÇÕES DE BUSCA POR TOKENIZAÇÃO
# =============================================================================

def resolver_por_tokenizacao(
    nome: str,
    model_class,
    campo_razao_social: str = 'raz_social',
    campo_cnpj: str = 'cnpj',
    campo_filtro_ativo: str = 'parcela_paga',
    filtro_ativo_valor: bool = False
) -> Optional[Tuple[str, str, int]]:
    """
    Tenta resolver um nome via tokenização e busca no banco.

    Genérico: funciona com ContasAPagar e ContasAReceber.

    Args:
        nome: Nome do fornecedor/cliente (pode estar truncado)
        model_class: Classe SQLAlchemy (ContasAPagar ou ContasAReceber)
        campo_razao_social: Nome do campo de razão social no model
        campo_cnpj: Nome do campo de CNPJ no model
        campo_filtro_ativo: Campo para filtrar registros ativos
        filtro_ativo_valor: Valor do campo para filtrar (False = não pago)

    Returns:
        Tuple (cnpj, raz_social, confiança) ou None se não resolver
    """
    tokens = tokenizar_nome(nome)

    if not tokens:
        return None

    # Construir query com ILIKE para cada token discriminante
    try:
        query = model_class.query.filter(
            getattr(model_class, campo_filtro_ativo) == filtro_ativo_valor
        )

        for token in tokens:
            query = query.filter(
                db.func.upper(getattr(model_class, campo_razao_social)).like(f'%{token}%')
            )

        resultados = query.limit(5).all()

    except Exception as e:
        logger.warning(f"Erro na busca por tokenização ({tokens}): {e}")
        return None

    if not resultados:
        # Tentar com N-1 tokens (tolerância para truncamento)
        if len(tokens) > 1:
            return _resolver_com_menos_tokens(
                tokens, model_class, campo_razao_social,
                campo_cnpj, campo_filtro_ativo, filtro_ativo_valor
            )
        return None

    # Deduplicar por CNPJ raiz (8 primeiros dígitos)
    cnpjs_unicos = {}
    for r in resultados:
        cnpj_valor = getattr(r, campo_cnpj, None)
        if cnpj_valor:
            raiz = re.sub(r'\D', '', cnpj_valor)[:8]
            if raiz not in cnpjs_unicos:
                cnpjs_unicos[raiz] = r

    if len(cnpjs_unicos) == 1:
        # Match único (mesmo CNPJ raiz)
        registro = list(cnpjs_unicos.values())[0]
        cnpj_normalizado = normalizar_cnpj(getattr(registro, campo_cnpj, ''))
        raz_social = getattr(registro, campo_razao_social, '') or ''
        return cnpj_normalizado, raz_social, 85

    if len(cnpjs_unicos) == 0 and resultados:
        # Resultados sem CNPJ
        registro = resultados[0]
        raz_social = getattr(registro, campo_razao_social, '') or ''
        return '', raz_social, 60

    # Múltiplos CNPJs diferentes — ambíguo
    if len(cnpjs_unicos) <= 3:
        registro = list(cnpjs_unicos.values())[0]
        cnpj_normalizado = normalizar_cnpj(getattr(registro, campo_cnpj, ''))
        raz_social = getattr(registro, campo_razao_social, '') or ''
        return cnpj_normalizado, raz_social, 60

    return None


def _resolver_com_menos_tokens(
    tokens: List[str],
    model_class,
    campo_razao_social: str,
    campo_cnpj: str,
    campo_filtro_ativo: str,
    filtro_ativo_valor: bool
) -> Optional[Tuple[str, str, int]]:
    """
    Tenta resolver removendo o último token (tolerância para truncamento).
    """
    tokens_reduzidos = tokens[:-1]

    if not tokens_reduzidos:
        return None

    try:
        query = model_class.query.filter(
            getattr(model_class, campo_filtro_ativo) == filtro_ativo_valor
        )

        for token in tokens_reduzidos:
            query = query.filter(
                db.func.upper(getattr(model_class, campo_razao_social)).like(f'%{token}%')
            )

        resultados = query.limit(5).all()

    except Exception as e:
        logger.warning(f"Erro na busca com tokens reduzidos ({tokens_reduzidos}): {e}")
        return None

    if not resultados:
        return None

    # Deduplicar por CNPJ raiz
    cnpjs_unicos = {}
    for r in resultados:
        cnpj_valor = getattr(r, campo_cnpj, None)
        if cnpj_valor:
            raiz = re.sub(r'\D', '', cnpj_valor)[:8]
            if raiz not in cnpjs_unicos:
                cnpjs_unicos[raiz] = r

    if len(cnpjs_unicos) == 1:
        registro = list(cnpjs_unicos.values())[0]
        cnpj_normalizado = normalizar_cnpj(getattr(registro, campo_cnpj, ''))
        raz_social = getattr(registro, campo_razao_social, '') or ''
        return cnpj_normalizado, raz_social, 70

    return None


def buscar_nome_por_cnpj(cnpj: str, model_class, campo_cnpj: str = 'cnpj') -> Optional[str]:
    """
    Busca nome de fornecedor/cliente pelo CNPJ.

    Args:
        cnpj: CNPJ formatado ou só dígitos
        model_class: Classe SQLAlchemy
        campo_cnpj: Nome do campo de CNPJ

    Returns:
        Nome (raz_social ou raz_social_red) ou None
    """
    if not cnpj:
        return None

    cnpj_limpo = re.sub(r'\D', '', cnpj)

    try:
        resultado = model_class.query.filter(
            db.func.regexp_replace(
                getattr(model_class, campo_cnpj), r'\D', '', 'g'
            ) == cnpj_limpo
        ).first()

        if resultado:
            return getattr(resultado, 'raz_social', None) or getattr(resultado, 'raz_social_red', None)

    except Exception as e:
        logger.warning(f"Erro ao buscar nome por CNPJ ({cnpj}): {e}")

    return None


def resolver_por_semantica(
    nome: str,
    entity_type: str = 'supplier',
    min_similarity: float = 0.45,
) -> Optional[Tuple[str, str, int]]:
    """
    Resolve nome via busca semantica em financial_entity_embeddings.

    Complementa resolver_por_tokenizacao() para nomes truncados/abreviados
    que ILIKE nao consegue resolver (ex: "MEZZANI ALIM", "ABC FRETES").

    Args:
        nome: Nome do fornecedor/cliente
        entity_type: 'supplier' ou 'customer'
        min_similarity: Threshold minimo de similaridade

    Returns:
        Tuple (cnpj_completo, nome_canonico, confianca) ou None
        Confianca: 80 (similarity > 0.7), 65 (> 0.5), 55 (> 0.45)
    """
    try:
        from app.embeddings.entity_search import buscar_entidade_semantica
        from app.embeddings.config import FINANCIAL_SEMANTIC_SEARCH
    except ImportError:
        return None

    if not FINANCIAL_SEMANTIC_SEARCH:
        return None

    if not nome or not nome.strip():
        return None

    try:
        resultados = buscar_entidade_semantica(
            nome, entity_type=entity_type, limite=3, min_similarity=min_similarity
        )
    except Exception as e:
        logger.warning(f"Busca semantica falhou para '{nome}': {e}")
        return None

    if not resultados:
        return None

    melhor = resultados[0]
    similarity = melhor['similarity']

    # Calcular confianca baseada em similarity
    if similarity > 0.7:
        confianca = 80
    elif similarity > 0.5:
        confianca = 65
    else:
        confianca = 55

    # Boost se todos os top results tem o mesmo CNPJ raiz (indica match forte)
    if len(resultados) >= 2:
        raizes = {r['cnpj_raiz'] for r in resultados}
        if len(raizes) == 1:
            confianca = min(confianca + 5, 85)

    cnpj = melhor.get('cnpj_completo') or ''
    nome_canonico = melhor.get('nome') or ''

    # Normalizar CNPJ se presente
    if cnpj:
        cnpj = normalizar_cnpj(cnpj)

    return cnpj, nome_canonico, confianca


def prefetch_partner_cnpjs(connection, partner_ids: List[int], cache: dict) -> None:
    """
    Busca CNPJs de parceiros Odoo em batch e atualiza o cache.

    Args:
        connection: Conexão Odoo autenticada
        partner_ids: Lista de IDs de res.partner
        cache: Dict para atualizar {partner_id: {'cnpj': str, 'name': str}}
    """
    if not partner_ids:
        return

    # Filtrar IDs que já estão no cache
    ids_faltando = [pid for pid in partner_ids if pid not in cache]

    if not ids_faltando:
        return

    # Deduplicar
    ids_faltando = list(set(ids_faltando))

    try:
        parceiros = connection.read(
            'res.partner',
            ids_faltando,
            fields=['id', 'l10n_br_cnpj', 'name']
        )

        for p in parceiros:
            pid = p['id']
            cnpj = p.get('l10n_br_cnpj') or ''
            nome = p.get('name') or ''
            cache[pid] = {
                'cnpj': cnpj.strip() if cnpj else '',
                'name': nome.strip() if nome else '',
            }

        logger.info(f"Cache de parceiros carregado: {len(ids_faltando)} IDs")

    except Exception as e:
        logger.warning(f"Erro ao buscar parceiros Odoo: {e}")
