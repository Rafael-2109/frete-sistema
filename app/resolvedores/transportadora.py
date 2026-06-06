"""Resolucao de transportadora (unica entidade so-na-split antes da consolidacao).

Port de resolvendo-entidades/scripts/resolver_transportadora.py — assume app_context (sem create_app).
3 estrategias em ordem: CNPJ normalizado / semantico (carrier_embeddings >=0.65) / ILIKE.
Raw SQL ja parametrizado (sem SQL-injection). 'similaridade' so no modo SEMANTICO.
"""
import re


def resolver_transportadora(termo: str, limite: int = 10) -> dict:
    """Resolve termo de transportadora para registros do banco.

    Returns dict: {sucesso, termo_original, estrategia('CNPJ'|'SEMANTICO'|'ILIKE'),
                   transportadoras:[{id,cnpj,razao_social,cidade,uf,ativo,similaridade?}], total, erro?}.
    """
    from app import db
    from sqlalchemy import text

    termo = (termo or '').strip()

    resultado = {
        'sucesso': False,
        'termo_original': termo,
        'estrategia': None,
        'transportadoras': [],
        'total': 0
    }

    if not termo or len(termo) < 2:
        resultado['erro'] = 'Termo muito curto (minimo 2 caracteres)'
        return resultado

    # Estrategia 1: CNPJ direto
    digitos = re.sub(r'\D', '', termo)
    if len(digitos) >= 8:
        rows = db.session.execute(text("""
            SELECT id, cnpj, razao_social, cidade, uf, ativo
            FROM transportadoras
            WHERE REPLACE(REPLACE(REPLACE(cnpj, '.', ''), '/', ''), '-', '') LIKE :cnpj
            ORDER BY ativo DESC, razao_social
            LIMIT :limite
        """), {"cnpj": f"%{digitos}%", "limite": limite}).fetchall()

        if rows:
            resultado['estrategia'] = 'CNPJ'
            resultado['transportadoras'] = [
                {'id': r[0], 'cnpj': r[1], 'razao_social': r[2], 'cidade': r[3], 'uf': r[4], 'ativo': r[5]}
                for r in rows
            ]
            resultado['total'] = len(rows)
            resultado['sucesso'] = True
            return resultado

    # Estrategia 2: Busca semantica
    try:
        from app.embeddings.config import CARRIER_SEMANTIC_SEARCH, EMBEDDINGS_ENABLED
        if EMBEDDINGS_ENABLED and CARRIER_SEMANTIC_SEARCH:
            from app.embeddings.service import EmbeddingService
            svc = EmbeddingService()
            sem_results = svc.search_carriers(termo, limit=limite, min_similarity=0.65)

            if sem_results:
                transportadoras = []
                for sr in sem_results:
                    carrier_name = sr.get('carrier_name', '')
                    cnpj = sr.get('cnpj')
                    similarity = sr.get('similarity', 0)

                    if cnpj:
                        row = db.session.execute(text("""
                            SELECT id, cnpj, razao_social, cidade, uf, ativo
                            FROM transportadoras
                            WHERE cnpj = :cnpj
                            LIMIT 1
                        """), {"cnpj": cnpj}).fetchone()
                    else:
                        row = db.session.execute(text("""
                            SELECT id, cnpj, razao_social, cidade, uf, ativo
                            FROM transportadoras
                            WHERE UPPER(razao_social) = :nome
                            LIMIT 1
                        """), {"nome": carrier_name.upper()}).fetchone()

                    if row:
                        transportadoras.append({
                            'id': row[0], 'cnpj': row[1], 'razao_social': row[2],
                            'cidade': row[3], 'uf': row[4], 'ativo': row[5],
                            'similaridade': round(similarity, 3),
                        })
                    else:
                        transportadoras.append({
                            'id': None, 'cnpj': cnpj, 'razao_social': carrier_name,
                            'cidade': None, 'uf': None, 'ativo': None,
                            'similaridade': round(similarity, 3),
                        })

                if transportadoras:
                    resultado['estrategia'] = 'SEMANTICO'
                    resultado['transportadoras'] = transportadoras
                    resultado['total'] = len(transportadoras)
                    resultado['sucesso'] = True
                    return resultado
    except Exception:
        pass  # Fallback para ILIKE

    # Estrategia 3: ILIKE (fallback)
    rows = db.session.execute(text("""
        SELECT id, cnpj, razao_social, cidade, uf, ativo
        FROM transportadoras
        WHERE UPPER(razao_social) LIKE :termo
        ORDER BY ativo DESC, razao_social
        LIMIT :limite
    """), {"termo": f"%{termo.upper()}%", "limite": limite}).fetchall()

    if rows:
        resultado['estrategia'] = 'ILIKE'
        resultado['transportadoras'] = [
            {'id': r[0], 'cnpj': r[1], 'razao_social': r[2], 'cidade': r[3], 'uf': r[4], 'ativo': r[5]}
            for r in rows
        ]
        resultado['total'] = len(rows)
        resultado['sucesso'] = True
        return resultado

    resultado['erro'] = f'Nenhuma transportadora encontrada para "{termo}"'
    return resultado
