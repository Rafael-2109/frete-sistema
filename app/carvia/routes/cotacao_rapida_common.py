"""Helpers compartilhados entre a Cotacao Rapida (com login) e a Cotacao Publica.

Normalizacao do payload (itens + regiao + cnpj, resolvendo CEP) e catalogos.
Fonte unica — nao duplicar nas duas familias de rota."""
import logging

logger = logging.getLogger(__name__)

UF_ORIGEM = 'SP'


def modelos_orm():
    """Modelos ativos (ORM) com a categoria carregada — para LLM/normalizacao."""
    from sqlalchemy.orm import joinedload
    from app.carvia.models import CarviaModeloMoto
    return (
        CarviaModeloMoto.query
        .options(joinedload(CarviaModeloMoto.categoria))
        .filter_by(ativo=True)
        .order_by(CarviaModeloMoto.nome.asc())
        .all()
    )


def ufs_destino_disponiveis():
    """UFs de destino que tem alguma tabela CarVia ativa com origem SP."""
    from app import db
    from app.carvia.models import CarviaTabelaFrete
    rows = (
        db.session.query(CarviaTabelaFrete.uf_destino)
        .filter(
            CarviaTabelaFrete.uf_origem == UF_ORIGEM,
            CarviaTabelaFrete.ativo == True,  # noqa: E712
        )
        .distinct()
        .all()
    )
    return sorted({r[0] for r in rows if r[0]})


def resolver_contexto(payload):
    """Normaliza o payload (itens + regiao + cnpj), resolvendo CEP se preciso.

    Retorna `{itens, uf_destino, cidade_destino, codigo_ibge, cnpj_cliente}` ou
    `{erro}`."""
    itens = payload.get('itens') or []
    if not isinstance(itens, list) or not itens:
        return {'erro': 'Informe pelo menos uma moto + quantidade.'}

    uf_destino = (payload.get('uf_destino') or '').strip().upper()
    cidade_destino = (payload.get('cidade_destino') or '').strip() or None
    codigo_ibge = (str(payload.get('codigo_ibge') or '').strip() or None)
    cep = (payload.get('cep') or '').strip()

    if cep and (not uf_destino or not cidade_destino or not codigo_ibge):
        from app.utils.cep_service import resolver_cep
        dados_cep = resolver_cep(cep)
        if dados_cep:
            uf_destino = uf_destino or dados_cep['uf']
            cidade_destino = cidade_destino or dados_cep['cidade']
            codigo_ibge = codigo_ibge or dados_cep.get('codigo_ibge')

    if not uf_destino and not codigo_ibge:
        return {'erro': 'Informe a UF de destino (ou um CEP valido).'}

    return {
        'itens': itens,
        'uf_destino': uf_destino,
        'cidade_destino': cidade_destino,
        'codigo_ibge': codigo_ibge,
        'cnpj_cliente': (payload.get('cnpj_cliente') or '').strip() or None,
    }
