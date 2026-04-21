"""Migracao e remocao de categorias — move vinculos de uma categoria para outra.

Uso tipico:
1. `contar_vinculos(cat_id)` -> dict com qtd de registros em cada tabela que apontam para a categoria.
2. `migrar_categoria(origem_id, destino_id)` -> move todos os vinculos; destino=None seta NULL.
3. (opcional) apos migrar, chamar `db.session.delete(cat_origem)` + commit para remover.

Tabelas afetadas por migracao:
- pessoal_transacoes.categoria_id
- pessoal_regras_categorizacao.categoria_id
- pessoal_orcamentos.categoria_id
- pessoal_grupos_analise_categorias (N:N — entradas da origem sao REMOVIDAS)
"""
from app import db
from app.pessoal.models import (
    PessoalCategoria, PessoalRegraCategorizacao,
    PessoalTransacao, PessoalOrcamento,
)


def contar_vinculos(cat_id: int) -> dict:
    """Retorna contagem de vinculos da categoria em cada tabela."""
    # N:N: conta direto via SQL (nao ha model mapeada para a tabela associativa)
    grupos_analise = db.session.execute(
        db.text("SELECT COUNT(*) FROM pessoal_grupos_analise_categorias WHERE categoria_id = :cid"),
        {'cid': cat_id},
    ).scalar() or 0
    return {
        'regras': PessoalRegraCategorizacao.query.filter_by(categoria_id=cat_id).count(),
        'transacoes': PessoalTransacao.query.filter_by(categoria_id=cat_id).count(),
        'orcamentos': PessoalOrcamento.query.filter_by(categoria_id=cat_id).count(),
        'grupos_analise': int(grupos_analise),
    }


def migrar_categoria(origem_id: int, destino_id=None, commit: bool = True) -> dict:
    """Move todos os vinculos de origem para destino. destino_id=None -> seta NULL.

    Args:
        origem_id: ID da categoria origem.
        destino_id: ID destino ou None (seta NULL).
        commit: se True, commita a transacao. Use False quando o caller precisa
                encadear outras operacoes atomicamente (ex: migrar + delete).

    Returns:
        dict com contagem de registros atualizados por tabela e entradas N:N removidas.

    Raises:
        ValueError: se origem == destino ou categorias nao existem.
    """
    if origem_id == destino_id:
        raise ValueError('Origem e destino sao iguais.')

    origem = db.session.get(PessoalCategoria, origem_id)
    if not origem:
        raise ValueError(f'Categoria origem id={origem_id} nao encontrada.')

    if destino_id is not None:
        destino = db.session.get(PessoalCategoria, destino_id)
        if not destino:
            raise ValueError(f'Categoria destino id={destino_id} nao encontrada.')

    updates = {}
    for model, key in [
        (PessoalTransacao, 'transacoes'),
        (PessoalRegraCategorizacao, 'regras'),
        (PessoalOrcamento, 'orcamentos'),
    ]:
        n = model.query.filter_by(categoria_id=origem_id).update(
            {'categoria_id': destino_id}, synchronize_session=False,
        )
        updates[key] = n

    # N:N: apenas remove entradas da origem (nao duplica para destino para evitar conflito de PK composta)
    resultado = db.session.execute(
        db.text("DELETE FROM pessoal_grupos_analise_categorias WHERE categoria_id = :cid"),
        {'cid': origem_id},
    )
    updates['grupos_analise_removidos'] = resultado.rowcount or 0

    if commit:
        db.session.commit()
        # Invalidar cache de IDs Desconsiderar (pode ter mudado)
        from app.pessoal.services.categorizacao_service import invalidar_cache_desconsiderar
        invalidar_cache_desconsiderar()

    return updates
