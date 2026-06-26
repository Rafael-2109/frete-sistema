"""cep_service.resolver_cep — ViaCEP mockado (sem rede)."""

from app.utils import cep_service


class _Resp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_resolver_cep_ok(monkeypatch):
    monkeypatch.setattr(
        cep_service.requests, 'get',
        lambda url, timeout=None: _Resp(
            {'localidade': 'Sorocaba', 'uf': 'SP', 'ibge': '3552205'}
        ),
    )
    out = cep_service.resolver_cep('18000-000')
    assert out == {
        'cep': '18000000', 'cidade': 'Sorocaba', 'uf': 'SP', 'codigo_ibge': '3552205',
    }


def test_resolver_cep_invalido_curto():
    assert cep_service.resolver_cep('123') is None
    assert cep_service.resolver_cep('') is None


def test_resolver_cep_erro_api(monkeypatch):
    monkeypatch.setattr(
        cep_service.requests, 'get',
        lambda url, timeout=None: _Resp({'erro': True}),
    )
    assert cep_service.resolver_cep('00000000') is None


def test_resolver_cep_timeout(monkeypatch):
    def _boom(url, timeout=None):
        raise cep_service.requests.Timeout('timeout')
    monkeypatch.setattr(cep_service.requests, 'get', _boom)
    assert cep_service.resolver_cep('18000000') is None
