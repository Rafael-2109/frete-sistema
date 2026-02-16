"""
Busca hibrida de produtos: ILIKE + semantica.

Funcao reutilizavel que combina busca por texto (abreviacoes + ILIKE)
com busca semantica (embeddings Voyage AI + pgvector).

Uso:
    from app.embeddings.product_search import buscar_produtos_hibrido

    resultados = buscar_produtos_hibrido("champignon fatiado")
    # Retorna produtos com "COGUMELO FATIADO" via sinonimia semantica

    resultados = buscar_produtos_hibrido("AZ VF", modo="hibrida")
    # Abreviacoes funcionam + semantica complementa

    resultados = buscar_produtos_hibrido("palmito", modo="texto")
    # Apenas ILIKE (comportamento original)
"""

import logging
from typing import List, Dict

from sqlalchemy import text

from app import db
from app.embeddings.config import EMBEDDINGS_ENABLED

logger = logging.getLogger(__name__)


# ============================================================
# ABREVIACOES DE PRODUTO
# Replicado de resolver_entidades.py — fonte canonica para
# modulos que importam buscar_produtos_hibrido()
# ============================================================
ABREVIACOES_PRODUTO = {
    # Tipo Materia Prima (tipo_materia_prima) - busca EXATA
    'CI': {'campo': 'tipo_materia_prima', 'valor': 'CI', 'tipo': 'exato', 'descricao': 'Cogumelo Inteiro'},
    'CF': {'campo': 'tipo_materia_prima', 'valor': 'CF', 'tipo': 'exato', 'descricao': 'Cogumelo Fatiado'},
    'AZ VF': {'campo': 'tipo_materia_prima', 'valor': 'AZ VF', 'tipo': 'exato', 'descricao': 'Azeitona Verde Fatiada'},
    'AZ PF': {'campo': 'tipo_materia_prima', 'valor': 'AZ PF', 'tipo': 'exato', 'descricao': 'Azeitona Preta Fatiada'},
    'AZ VI': {'campo': 'tipo_materia_prima', 'valor': 'AZ VI', 'tipo': 'exato', 'descricao': 'Azeitona Verde Inteira'},
    'AZ PI': {'campo': 'tipo_materia_prima', 'valor': 'AZ PI', 'tipo': 'exato', 'descricao': 'Azeitona Preta Inteira'},
    'AZ VR': {'campo': 'tipo_materia_prima', 'valor': 'AZ VR', 'tipo': 'exato', 'descricao': 'Azeitona Verde Recheada'},
    'AZ VSC': {'campo': 'tipo_materia_prima', 'valor': 'AZ VSC', 'tipo': 'exato', 'descricao': 'Azeitona Verde Sem Caroco'},

    # Alias curtos para tipo_materia_prima
    'VF': {'campo': 'tipo_materia_prima', 'valor': '%VF%', 'tipo': 'like', 'descricao': 'Verde Fatiada'},
    'PF': {'campo': 'tipo_materia_prima', 'valor': '%PF%', 'tipo': 'like', 'descricao': 'Preta Fatiada'},

    # Tipo Embalagem (tipo_embalagem) - busca EXATA ou LIKE
    'BARRICA': {'campo': 'tipo_embalagem', 'valor': 'BARRICA', 'tipo': 'exato', 'descricao': 'Barrica'},
    'BR': {'campo': 'tipo_embalagem', 'valor': 'BARRICA', 'tipo': 'exato', 'descricao': 'Barrica (alias)'},
    'BD': {'campo': 'tipo_embalagem', 'valor': 'BD%', 'tipo': 'like', 'descricao': 'Balde'},
    'BALDE': {'campo': 'tipo_embalagem', 'valor': 'BD%', 'tipo': 'like', 'descricao': 'Balde'},
    'POUCH': {'campo': 'tipo_embalagem', 'valor': 'POUCH%', 'tipo': 'like', 'descricao': 'Pouch'},
    'SACHET': {'campo': 'tipo_embalagem', 'valor': 'SACHET%', 'tipo': 'like', 'descricao': 'Sachet'},
    'VIDRO': {'campo': 'tipo_embalagem', 'valor': 'VIDRO%', 'tipo': 'like', 'descricao': 'Vidro'},
    'VD': {'campo': 'tipo_embalagem', 'valor': 'VIDRO%', 'tipo': 'like', 'descricao': 'Vidro (alias)'},
    'GALAO': {'campo': 'tipo_embalagem', 'valor': 'GALAO%', 'tipo': 'like', 'descricao': 'Galao'},
    'GL': {'campo': 'tipo_embalagem', 'valor': 'GALAO%', 'tipo': 'like', 'descricao': 'Galao (alias)'},

    # Categorias/Marcas (categoria_produto) - busca EXATA
    'CAMPO BELO': {'campo': 'categoria_produto', 'valor': 'CAMPO BELO', 'tipo': 'exato', 'descricao': 'Marca Campo Belo'},
    'MEZZANI': {'campo': 'categoria_produto', 'valor': 'MEZZANI', 'tipo': 'exato', 'descricao': 'Marca Mezzani'},
    'BENASSI': {'campo': 'categoria_produto', 'valor': 'BENASSI', 'tipo': 'exato', 'descricao': 'Marca Benassi'},
    'IMPERIAL': {'campo': 'categoria_produto', 'valor': 'IMPERIAL', 'tipo': 'exato', 'descricao': 'Marca Imperial'},
    'INDUSTRIA': {'campo': 'categoria_produto', 'valor': 'INDUSTRIA', 'tipo': 'exato', 'descricao': 'Destinado a industria'},
    'IND': {'campo': 'categoria_produto', 'valor': 'INDUSTRIA', 'tipo': 'exato', 'descricao': 'Industria (alias)'},
}


def detectar_abreviacoes(tokens: list) -> tuple:
    """
    Detecta abreviacoes em lista de tokens, incluindo combinacoes.

    Exemplo: ['az', 'vf', 'pouch'] -> detecta 'AZ VF' como combinacao

    Args:
        tokens: Lista de tokens (ex: ['az', 'vf', 'pouch'])

    Returns:
        tuple: (abreviacoes_encontradas, tokens_restantes)
    """
    abreviacoes = []
    tokens_usados = set()

    # Primeiro, tentar combinacoes de 2 tokens (ex: 'AZ VF')
    for i in range(len(tokens) - 1):
        combo = f"{tokens[i]} {tokens[i + 1]}".upper()
        if combo in ABREVIACOES_PRODUTO:
            abreviacoes.append(ABREVIACOES_PRODUTO[combo])
            tokens_usados.add(i)
            tokens_usados.add(i + 1)

    # Depois, tentar tokens individuais
    for i, token in enumerate(tokens):
        if i in tokens_usados:
            continue
        token_upper = token.upper()
        if token_upper in ABREVIACOES_PRODUTO:
            abreviacoes.append(ABREVIACOES_PRODUTO[token_upper])
            tokens_usados.add(i)

    # Tokens restantes
    tokens_restantes = [t for i, t in enumerate(tokens) if i not in tokens_usados]

    return abreviacoes, tokens_restantes


# ============================================================
# BUSCA POR TEXTO (ILIKE + abreviacoes)
# ============================================================

def _buscar_texto(
    termo: str,
    limite: int = 50,
    filtro_ativo: bool = True,
    filtro_vendido: bool = True,
) -> List[Dict]:
    """
    Busca por texto puro (ILIKE + abreviacoes).

    Mesma logica de resolver_produto() em resolver_entidades.py,
    retornando formato padronizado com campo source.

    Args:
        termo: Termo de busca
        limite: Maximo de resultados
        filtro_ativo: Filtrar apenas produtos ativos
        filtro_vendido: Filtrar apenas produtos vendidos

    Returns:
        Lista de dicts com cod_produto, nome_produto, score, source
    """
    termo = termo.strip().lower()
    if not termo:
        return []

    tokens = termo.split()
    abreviacoes, tokens_restantes = detectar_abreviacoes(tokens)

    # Montar filtros SQL
    filtros = []
    params = {}

    # Filtros base
    if filtro_ativo:
        filtros.append("ativo = true")
    if filtro_vendido:
        filtros.append("produto_vendido = true")

    # Filtros para abreviacoes (busca EXATA ou LIKE no campo especifico)
    filtros_produto = []
    for i, abrev in enumerate(abreviacoes):
        campo = abrev['campo']
        valor = abrev['valor']
        tipo = abrev['tipo']
        param_name = f'abrev_{i}'

        if tipo == 'exato':
            filtros_produto.append(f"UPPER({campo}) = UPPER(:{param_name})")
            params[param_name] = valor
        else:  # tipo == 'like'
            filtros_produto.append(f"{campo} ILIKE :{param_name}")
            params[param_name] = valor

    # Filtros para tokens restantes (busca PARCIAL em qualquer campo)
    for i, token in enumerate(tokens_restantes):
        param_name = f'token_{i}'
        filtros_produto.append(
            f"(cod_produto ILIKE :{param_name}"
            f" OR nome_produto ILIKE :{param_name}"
            f" OR tipo_materia_prima ILIKE :{param_name}"
            f" OR tipo_embalagem ILIKE :{param_name}"
            f" OR categoria_produto ILIKE :{param_name}"
            f" OR subcategoria ILIKE :{param_name})"
        )
        params[param_name] = f'%{token}%'

    if not filtros_produto:
        return []

    where_parts = filtros + filtros_produto
    where_sql = " AND ".join(where_parts)

    sql = f"""
        SELECT cod_produto, nome_produto, tipo_embalagem, tipo_materia_prima,
               categoria_produto, subcategoria, palletizacao, peso_bruto
        FROM cadastro_palletizacao
        WHERE {where_sql}
        ORDER BY nome_produto
        LIMIT :limite
    """
    params['limite'] = limite * 2

    result = db.session.execute(text(sql), params)
    rows = result.fetchall()

    if not rows:
        return []

    # Calcular score de relevancia (mesmo algoritmo de resolver_produto)
    resultados = []
    for row in rows:
        prod = {
            'cod_produto': row[0],
            'nome_produto': row[1],
            'tipo_embalagem': row[2],
            'tipo_materia_prima': row[3],
            'categoria_produto': row[4],
            'subcategoria': row[5],
            'palletizacao': float(row[6]) if row[6] else 0,
            'peso_bruto': float(row[7]) if row[7] else 0,
            'score': 0,
            'matches': [],
            'source': 'texto',
        }

        # Score para abreviacoes (peso alto)
        for abrev in abreviacoes:
            campo = abrev['campo']
            valor_prod = prod.get(campo, '')
            if valor_prod:
                prod['score'] += 4
                prod['matches'].append(f"{campo}:{abrev['descricao']}")

        # Score para tokens restantes
        for token in tokens_restantes:
            token_lower = token.lower()

            if prod['cod_produto'] and token_lower in prod['cod_produto'].lower():
                prod['score'] += 5
                prod['matches'].append(f"cod_produto:{token}")

            if prod['nome_produto'] and token_lower in prod['nome_produto'].lower():
                prod['score'] += 3
                prod['matches'].append(f"nome_produto:{token}")

            if prod['tipo_materia_prima'] and token_lower in prod['tipo_materia_prima'].lower():
                prod['score'] += 2

            if prod['tipo_embalagem'] and token_lower in prod['tipo_embalagem'].lower():
                prod['score'] += 2

            if prod['categoria_produto'] and token_lower in prod['categoria_produto'].lower():
                prod['score'] += 2

        resultados.append(prod)

    resultados.sort(key=lambda x: -x['score'])
    return resultados[:limite]


# ============================================================
# BUSCA SEMANTICA (embeddings)
# ============================================================

def _buscar_semantica(
    termo: str,
    limite: int = 20,
    min_similarity: float = 0.35,
) -> List[Dict]:
    """
    Busca semantica via embeddings (EmbeddingService.search_products).

    Args:
        termo: Termo de busca
        limite: Maximo de resultados
        min_similarity: Score minimo de similaridade (0-1)

    Returns:
        Lista de dicts enriquecidos com dados do cadastro
    """
    if not EMBEDDINGS_ENABLED:
        return []

    try:
        from app.embeddings.service import EmbeddingService
        svc = EmbeddingService()
        results = svc.search_products(termo, limit=limite, min_similarity=min_similarity)

        if not results:
            return []

        # Enriquecer com dados completos do cadastro_palletizacao
        cod_produtos = [r['cod_produto'] for r in results]
        placeholders = ', '.join(f':cod_{i}' for i in range(len(cod_produtos)))
        params = {f'cod_{i}': cod for i, cod in enumerate(cod_produtos)}

        cadastro_result = db.session.execute(text(f"""
            SELECT cod_produto, nome_produto, tipo_embalagem, tipo_materia_prima,
                   categoria_produto, subcategoria, palletizacao, peso_bruto
            FROM cadastro_palletizacao
            WHERE cod_produto IN ({placeholders})
        """), params)

        cadastro_map = {}
        for row in cadastro_result.fetchall():
            cadastro_map[row[0]] = {
                'nome_produto': row[1],
                'tipo_embalagem': row[2],
                'tipo_materia_prima': row[3],
                'categoria_produto': row[4],
                'subcategoria': row[5],
                'palletizacao': float(row[6]) if row[6] else 0,
                'peso_bruto': float(row[7]) if row[7] else 0,
            }

        enriched = []
        for r in results:
            dados = cadastro_map.get(r['cod_produto'], {})
            enriched.append({
                'cod_produto': r['cod_produto'],
                'nome_produto': dados.get('nome_produto', r.get('nome_produto', '')),
                'tipo_embalagem': dados.get('tipo_embalagem'),
                'tipo_materia_prima': r.get('tipo_materia_prima') or dados.get('tipo_materia_prima'),
                'categoria_produto': dados.get('categoria_produto'),
                'subcategoria': dados.get('subcategoria'),
                'palletizacao': dados.get('palletizacao', 0),
                'peso_bruto': dados.get('peso_bruto', 0),
                'score': r['similarity'],
                'similarity': r['similarity'],
                'matches': [f"semantica:{r['similarity']:.3f}"],
                'source': 'semantica',
            })

        return enriched

    except Exception as e:
        logger.warning(f"[product_search] Busca semantica falhou: {e}")
        return []


# ============================================================
# BUSCA HIBRIDA (texto + semantica)
# ============================================================

def buscar_produtos_hibrido(
    termo: str,
    modo: str = "hibrida",
    limite: int = 20,
    min_similarity: float = 0.35,
    filtro_ativo: bool = True,
    filtro_vendido: bool = True,
) -> List[Dict]:
    """
    Busca hibrida: ILIKE (abreviacoes + tokens) + semantica (embeddings).

    Modo "texto": apenas ILIKE (comportamento atual)
    Modo "semantica": apenas embeddings
    Modo "hibrida": ambos, deduplicado por cod_produto, score combinado

    Score combinado (modo hibrida):
    - Match texto normalizado: score_texto / max_score_texto (0-1)
    - Match semantico: similarity direto do pgvector (0-1)
    - Score final: 0.6 * score_texto + 0.4 * score_semantico (quando ambos)
    - Deduplicacao por cod_produto, mantendo maior score

    Args:
        termo: Termo de busca (pode ser abreviacao, nome parcial, sinonimo)
        modo: "texto", "semantica" ou "hibrida"
        limite: Maximo de resultados
        min_similarity: Score minimo para busca semantica (0-1)
        filtro_ativo: Filtrar apenas produtos ativos
        filtro_vendido: Filtrar apenas produtos vendidos

    Returns:
        Lista de dicts com:
        - cod_produto, nome_produto, tipo_embalagem, tipo_materia_prima
        - categoria_produto, subcategoria, palletizacao, peso_bruto
        - score (float), matches (list), source ("texto"|"semantica"|"ambos")
    """
    if modo == "texto":
        return _buscar_texto(termo, limite, filtro_ativo, filtro_vendido)

    if modo == "semantica":
        results = _buscar_semantica(termo, limite, min_similarity)
        if not results:
            logger.info("[product_search] Semantica vazia, fallback para texto")
            return _buscar_texto(termo, limite, filtro_ativo, filtro_vendido)
        return results

    # ============================================================
    # Modo hibrida: combinar texto + semantica
    # ============================================================
    texto_results = _buscar_texto(termo, limite, filtro_ativo, filtro_vendido)
    semantica_results = _buscar_semantica(termo, limite, min_similarity)

    # Se semantica falhou, retornar apenas texto
    if not semantica_results:
        return texto_results

    # Se texto falhou, retornar apenas semantica
    if not texto_results:
        return semantica_results

    # Normalizar scores de texto (0-1)
    max_score_texto = max(r['score'] for r in texto_results)
    if max_score_texto == 0:
        max_score_texto = 1

    # Indexar por cod_produto
    combined: Dict[str, Dict] = {}

    for r in texto_results:
        cod = r['cod_produto']
        score_norm = r['score'] / max_score_texto
        combined[cod] = {
            **r,
            'score_texto': score_norm,
            'score_semantico': 0.0,
            'source': 'texto',
        }

    for r in semantica_results:
        cod = r['cod_produto']
        sim = r.get('similarity', r.get('score', 0))

        if cod in combined:
            # Produto encontrado em ambos — score combinado
            combined[cod]['score_semantico'] = sim
            combined[cod]['source'] = 'ambos'
            combined[cod]['similarity'] = sim
            # Merge matches
            combined[cod]['matches'] = combined[cod].get('matches', []) + r.get('matches', [])
        else:
            combined[cod] = {
                **r,
                'score_texto': 0.0,
                'score_semantico': sim,
                'source': 'semantica',
            }

    # Calcular score final hibrido
    PESO_TEXTO = 0.6
    PESO_SEMANTICO = 0.4

    for r in combined.values():
        if r['source'] == 'ambos':
            r['score'] = PESO_TEXTO * r['score_texto'] + PESO_SEMANTICO * r['score_semantico']
        elif r['source'] == 'texto':
            r['score'] = PESO_TEXTO * r['score_texto']
        else:  # semantica
            r['score'] = PESO_SEMANTICO * r['score_semantico']

    # Ordenar por score combinado e limitar
    resultados = sorted(combined.values(), key=lambda x: -x['score'])
    return resultados[:limite]
