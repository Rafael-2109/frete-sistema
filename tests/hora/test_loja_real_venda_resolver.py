"""TDD: a loja REAL da venda nunca pode ser a matriz (emitente fiscal).

Toda NFe da HORA sai com o CNPJ da matriz (invariante CLAUDE.md secao 7), mas a
matriz NAO vende. `_resolver_loja_real_venda` deve resolver a loja fisica pelo
de-para de departamento; cair para o CNPJ emitente APENAS se ele nao for a matriz;
caso contrario retornar None (loja a definir), nunca a matriz.
"""
import uuid

from app import db as _db
from app.hora.models import HoraLoja, HoraTagPlusDepartamentoMap
from app.hora.services import venda_service
from app.utils.timezone import agora_utc_naive


def _cnpj():
    return ''.join(c for c in uuid.uuid4().hex if c.isdigit()).ljust(14, '0')[:14]


def _loja(is_matriz=False):
    loja = HoraLoja(
        cnpj=_cnpj(), apelido=f'L-{uuid.uuid4().hex[:6]}', nome='Loja Teste',
        ativa=True, is_matriz=is_matriz, atualizado_em=agora_utc_naive(),
    )
    _db.session.add(loja)
    _db.session.flush()
    return loja


def _mapa(departamento_norm, loja_id):
    m = HoraTagPlusDepartamentoMap(
        departamento_norm=departamento_norm, departamento_raw=departamento_norm,
        loja_id=loja_id, qtd_vendas_observadas=1,
    )
    _db.session.add(m)
    _db.session.flush()
    return m


def test_resolver_loja_real_ignora_matriz_pelo_cnpj(db):
    matriz = _loja(is_matriz=True)
    assert venda_service._resolver_loja_real_venda(matriz.cnpj, None) is None


def test_resolver_loja_real_aceita_loja_nao_matriz_pelo_cnpj(db):
    loja = _loja(is_matriz=False)
    out = venda_service._resolver_loja_real_venda(loja.cnpj, None)
    assert out is not None and out.id == loja.id


def test_resolver_loja_real_prioriza_departamento_sobre_matriz(db):
    matriz = _loja(is_matriz=True)
    real = _loja(is_matriz=False)
    _mapa('tatuape', real.id)
    out = venda_service._resolver_loja_real_venda(matriz.cnpj, 'Tatuapé')
    assert out is not None and out.id == real.id


def test_resolver_loja_real_cnpj_desconhecido_retorna_none(db):
    assert venda_service._resolver_loja_real_venda(_cnpj(), None) is None


def test_resolver_loja_por_departamento_sem_mapa_ou_vazio(db):
    assert venda_service._resolver_loja_por_departamento('Inexistente') is None
    assert venda_service._resolver_loja_por_departamento(None) is None


def test_resolver_loja_por_departamento_mapa_sem_loja_retorna_none(db):
    # departamento observado mas ainda sem loja atribuida (loja_id NULL) -> None
    _mapa('administrativo', None)
    assert venda_service._resolver_loja_por_departamento('Administrativo') is None
