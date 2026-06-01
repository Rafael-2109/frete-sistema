"""TDD — resolucao de transportadora (toca banco: transportadoras + carrier_embeddings).

Port de resolvendo-entidades/scripts/resolver_transportadora.py (unica entidade so-na-split).
3 estrategias: CNPJ normalizado / semantico (search_carriers >=0.65) / ILIKE. Assume app_context.
"""
from app.resolvedores.transportadora import resolver_transportadora


def _razao_social_real():
    from app import db
    from sqlalchemy import text
    return db.session.execute(text(
        "SELECT razao_social FROM transportadoras WHERE razao_social IS NOT NULL "
        "AND length(razao_social) >= 5 LIMIT 1"
    )).fetchone()


class TestResolverTransportadora:
    def test_termo_muito_curto(self, db):
        r = resolver_transportadora('a')
        assert r['sucesso'] is False
        assert 'erro' in r

    def test_inexistente(self, db):
        r = resolver_transportadora('zzqxwtransportadorainexistente')
        assert r['sucesso'] is False
        assert 'erro' in r

    def test_shape_topo(self, db):
        r = resolver_transportadora('zzqxwtransportadorainexistente')
        for k in ('sucesso', 'termo_original', 'estrategia', 'transportadoras', 'total'):
            assert k in r

    def test_caminho_feliz(self, db):
        row = _razao_social_real()
        assert row is not None, "esperado >=1 transportadora no banco local"
        termo = row[0][:5]
        r = resolver_transportadora(termo)
        assert r['sucesso'] is True
        assert r['transportadoras']
        for k in ('id', 'cnpj', 'razao_social', 'cidade', 'uf', 'ativo'):
            assert k in r['transportadoras'][0]
