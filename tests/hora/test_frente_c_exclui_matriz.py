"""TDD Frente C: a matriz (is_matriz=True) some das superficies de VENDA.

A matriz permanece ativa (default de NF de entrada + resolver de divergencia),
mas NAO pode aparecer como loja de venda: SELECT de pedido, dropdowns gerenciais,
contagem de "Lojas ativas". Usa o flag is_matriz (nao mais o CNPJ hardcoded).
"""
import uuid

from app import db as _db
from app.hora.models import HoraLoja
from app.hora.services import cadastro_service
from app.utils.timezone import agora_utc_naive


def _loja(is_matriz=False):
    loja = HoraLoja(
        cnpj=''.join(c for c in uuid.uuid4().hex if c.isdigit()).ljust(14, '0')[:14],
        apelido=f'L-{uuid.uuid4().hex[:6]}', nome='Loja Teste', uf='SP',
        ativa=True, is_matriz=is_matriz, atualizado_em=agora_utc_naive(),
    )
    _db.session.add(loja)
    _db.session.flush()
    return loja


def test_select_pedido_venda_exclui_matriz_por_flag(db):
    # matriz com CNPJ ALEATORIO (!= hardcoded) -> prova que o flag generaliza.
    matriz = _loja(is_matriz=True)
    real = _loja(is_matriz=False)
    out = cadastro_service.listar_lojas_para_pedido_venda(lojas_permitidas_ids=None)
    ids = {l.id for l in out}
    assert real.id in ids
    assert matriz.id not in ids


def test_gerencial_dropdown_exclui_matriz(db):
    from app.hora.routes.gerencial import _lojas_disponiveis
    matriz = _loja(is_matriz=True)
    real = _loja(is_matriz=False)
    ids = {l.id for l in _lojas_disponiveis(None)}  # None = irrestrito
    assert real.id in ids
    assert matriz.id not in ids
