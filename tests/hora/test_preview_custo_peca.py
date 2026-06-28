"""Preview da NF: margem usa o CUSTO da peca vendida, nao o preco de venda.

Migration hora_59 adicionou hora_peca.custo + hora_venda_item_peca.custo_unitario
(snapshot). O preview soma `qtd * custo_unitario` em custo_pecas_total e subtrai
do liquido — antes a peca entrava na receita sem custo (margem inflada).
"""
from decimal import Decimal

from app import db as _db
from app.hora.models import HoraVenda, HoraVendaItemPeca
from app.hora.services import venda_service, venda_preview_service
from app.utils.timezone import agora_utc_naive


def _venda(loja, total):
    v = HoraVenda(
        loja_id=loja.id, cpf_cliente='12345678909', nome_cliente='Cliente Teste',
        valor_total=Decimal(str(total)), status='COTACAO',
        data_venda=agora_utc_naive().date(), origem_criacao='MANUAL',
    )
    _db.session.add(v)
    _db.session.flush()
    return v


def _item_peca(venda, peca, qtd, preco_final, custo_unitario):
    ip = HoraVendaItemPeca(
        venda_id=venda.id, peca_id=peca.id, qtd=Decimal(str(qtd)),
        preco_unitario_referencia=Decimal(str(preco_final)),
        desconto_aplicado=Decimal('0'),
        preco_final=Decimal(str(preco_final)),
        custo_unitario=Decimal(str(custo_unitario)),
    )
    _db.session.add(ip)
    _db.session.flush()
    return ip


def test_preview_subtrai_custo_peca_vendida(db, loja_factory, peca_factory):
    v = _venda(loja_factory(), total=200)
    p = peca_factory(descricao='BATERIA')
    _item_peca(v, p, qtd=2, preco_final=200, custo_unitario=30)
    _db.session.refresh(v)

    preview = venda_preview_service.montar_preview(v)
    assert preview['custo_pecas_total'] == Decimal('60')   # 2 * 30
    assert preview['liquido'] == Decimal('200') - Decimal('60')
    assert preview['margem_bruta'] == Decimal('60')
    assert preview['tem_peca_sem_custo'] is False


def test_preview_marca_peca_sem_custo(db, loja_factory, peca_factory):
    v = _venda(loja_factory(), total=200)
    p = peca_factory(descricao='RETROVISOR')
    _item_peca(v, p, qtd=1, preco_final=200, custo_unitario=0)
    _db.session.refresh(v)

    preview = venda_preview_service.montar_preview(v)
    assert preview['tem_peca_sem_custo'] is True
    assert preview['custo_pecas_total'] == Decimal('0')


def test_adicionar_item_peca_grava_snapshot_custo(db, loja_factory, peca_factory):
    """adicionar_item_peca grava custo_unitario = peca.custo no momento da venda."""
    from app.hora.services import peca_estoque_service

    loja = loja_factory()
    v = _venda(loja, total=0)
    p = peca_factory(descricao='CAPACETE')
    p.preco_venda_padrao = Decimal('150')  # != custo
    p.custo = Decimal('45')
    _db.session.flush()
    # dar saldo de estoque para a peca na loja
    peca_estoque_service.registrar_movimento(
        peca_id=p.id, loja_id=loja.id, tipo='ENTRADA_NF', qtd=Decimal('5'),
        ref_tabela='teste', ref_id=0, motivo='setup', operador='t',
    )
    _db.session.flush()

    item = venda_service.adicionar_item_peca(
        venda_id=v.id, peca_id=p.id, qtd=2, valor_unitario_final=Decimal('150'),
        usuario='t',
    )
    assert item.custo_unitario == Decimal('45')  # snapshot do custo, nao do preco
