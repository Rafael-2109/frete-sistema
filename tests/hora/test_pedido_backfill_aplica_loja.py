"""TDD: o backfill de pedido auto-aplica a loja real quando o departamento mapeia.

Antes, `_aplicar_pedido_em_venda` so gravava `tagplus_departamento` e deixava o
`loja_id` (matriz/NULL) para o botao/script de de-para. Gap fechado: quando o
departamento ja resolve uma loja real, aplica via `definir_loja_venda` (corrige
loja_id + re-emite VENDIDA).
"""
import uuid
from datetime import date
from decimal import Decimal

from app import db as _db
from app.hora.models import (
    HoraLoja, HoraMoto, HoraMotoEvento, HoraTagPlusDepartamentoMap,
    HoraVenda, HoraVendaItem,
)
from app.hora.models.venda import VENDA_STATUS_FATURADO
from app.hora.services.moto_service import registrar_evento
from app.hora.services.tagplus import pedido_backfill_service, pedido_service
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


def test_backfill_pedido_aplica_loja_do_departamento(db, modelo_moto, monkeypatch):
    matriz = _loja(is_matriz=True)
    real = _loja(is_matriz=False)
    _db.session.add(HoraTagPlusDepartamentoMap(
        departamento_norm='tatuape', departamento_raw='Tatuapé',
        loja_id=real.id, qtd_vendas_observadas=1,
    ))

    chassi = f'CHV{uuid.uuid4().hex[:9].upper()}'
    _db.session.add(HoraMoto(
        numero_chassi=chassi, modelo_id=modelo_moto.id, cor='PRETA',
        criado_por='setup',
    ))
    venda = HoraVenda(
        loja_id=matriz.id, cpf_cliente='12345678909', nome_cliente='Cli',
        valor_total=Decimal('9990.00'), status=VENDA_STATUS_FATURADO,
        cnpj_emitente=matriz.cnpj, nf_saida_chave_44=_cnpj() + _cnpj() + '0000000000000000',
        origem_criacao='TAGPLUS_API', data_venda=date(2026, 6, 1),
    )
    _db.session.add(venda)
    _db.session.flush()
    item = HoraVendaItem(
        venda_id=venda.id, numero_chassi=chassi, preco_final=Decimal('9990.00'),
        preco_tabela_referencia=Decimal('9990.00'), desconto_aplicado=Decimal('0'),
    )
    _db.session.add(item)
    _db.session.flush()
    registrar_evento(
        numero_chassi=chassi, tipo='VENDIDA', loja_id=matriz.id,
        origem_tabela='hora_venda_item', origem_id=item.id, operador='setup',
    )
    _db.session.flush()

    pedido = {
        'id': 123, 'departamento': {'descricao': 'Tatuapé'},
        'vendedor': {'nome': 'Vendedor X'}, 'faturas': [],
    }
    monkeypatch.setattr(pedido_service, 'importar_pedido', lambda api, pid: pedido)

    pedido_backfill_service._aplicar_pedido_em_venda(
        api=None, venda=venda, pedido_id_tp=123, operador='tester',
    )

    assert venda.tagplus_departamento == 'Tatuapé'
    # GAP fechado: loja_id corrigida para a loja real (nao mais a matriz).
    assert venda.loja_id == real.id

    # Evento VENDIDA re-emitido com a loja correta (vence por MAX id).
    ult_vendida = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi, tipo='VENDIDA')
        .order_by(HoraMotoEvento.id.desc())
        .first()
    )
    assert ult_vendida.loja_id == real.id
