"""TDD: a UF do emitente (base do CFOP) vem da MATRIZ, nunca da loja de venda.

O emitente fiscal e sempre a matriz (invariante CLAUDE.md secao 7). Apos o
saneamento de loja_id, `venda.loja` pode ser None (loja a definir) ou de outra
UF — `_uf_emitente` NAO pode depender disso, senao o CFOP fica errado / quebra.
"""
import types
import uuid

from app import db as _db
from app.hora.models import HoraLoja
from app.hora.services.tagplus.payload_builder import PayloadBuilder
from app.utils.timezone import agora_utc_naive


def _matriz_sp():
    loja = HoraLoja(
        cnpj=''.join(c for c in uuid.uuid4().hex if c.isdigit()).ljust(14, '0')[:14],
        apelido=f'MATRIZ-{uuid.uuid4().hex[:6]}', nome='Matriz Teste', uf='SP',
        ativa=True, is_matriz=True, atualizado_em=agora_utc_naive(),
    )
    _db.session.add(loja)
    _db.session.flush()
    return loja


def test_uf_emitente_ignora_loja_da_venda_e_usa_matriz(db):
    _matriz_sp()
    # venda com loja de OUTRA UF (MG) — o emitente continua a matriz (SP).
    venda = types.SimpleNamespace(loja=types.SimpleNamespace(uf='MG'))
    assert PayloadBuilder._uf_emitente(None, venda) == 'SP'


def test_uf_emitente_loja_none_nao_quebra(db):
    _matriz_sp()
    venda = types.SimpleNamespace(loja=None)  # loja a definir (pos-saneamento)
    assert PayloadBuilder._uf_emitente(None, venda) == 'SP'
