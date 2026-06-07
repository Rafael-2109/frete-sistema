"""Testes do calculo de comissao + relatorio (roadmap #28, Fatia 3).

Comissao conta quando FATURADO. Isolamento: faixas limpas no inicio; vendedores
com nome uuid (relatorio filtra so os do teste). Ver [[gotcha_testes_hora_residuo]].
"""
import uuid
from decimal import Decimal

from app import db as _db
from app.hora.services import comissao_service
from app.hora.models import (
    HoraVenda, HoraVendaItem, HoraVendaItemPeca, HoraMoto, HoraModelo,
    HoraComissaoFaixaDesconto,
)
from app.utils.timezone import agora_utc_naive


def _limpar_faixas():
    HoraComissaoFaixaDesconto.query.delete()
    _db.session.commit()


def _chassi():
    return f'CC{uuid.uuid4().hex.upper()}'[:25].ljust(25, '0')


def _venda_faturada(loja, vendedor, desconto=Decimal('0'), status='FATURADO'):
    modelo = HoraModelo(nome_modelo=f'TST-{uuid.uuid4().hex[:8].upper()}', ativo=True)
    _db.session.add(modelo)
    _db.session.flush()
    chassi = _chassi()
    _db.session.add(HoraMoto(numero_chassi=chassi, modelo_id=modelo.id, cor='PRETA'))
    _db.session.flush()
    v = HoraVenda(
        loja_id=loja.id, cpf_cliente='12345678909', nome_cliente='Cli',
        valor_total=Decimal('1000') - desconto, status=status,
        data_venda=agora_utc_naive().date(), faturado_em=agora_utc_naive(),
        vendedor=vendedor, origem_criacao='MANUAL',
    )
    _db.session.add(v)
    _db.session.flush()
    _db.session.add(HoraVendaItem(
        venda_id=v.id, numero_chassi=chassi,
        preco_tabela_referencia=Decimal('1000'),
        desconto_aplicado=desconto, desconto_percentual=0,
        preco_final=Decimal('1000') - desconto,
    ))
    _db.session.flush()
    return v


def test_comissao_moto_sem_desconto(db, loja_factory):
    _limpar_faixas()
    comissao_service.set_comissao_base_moto('100')
    v = _venda_faturada(loja_factory(), 'V1', desconto=Decimal('0'))
    r = comissao_service.calcular_comissao_venda(v)
    assert r['comissao_motos'] == Decimal('100')
    assert r['total'] == Decimal('100')


def test_comissao_moto_com_faixa_reduz(db, loja_factory):
    _limpar_faixas()
    comissao_service.set_comissao_base_moto('100')
    comissao_service.criar_faixa('100', '300', '20')  # desconto 100-300 reduz 20
    v = _venda_faturada(loja_factory(), 'V1', desconto=Decimal('200'))
    r = comissao_service.calcular_comissao_venda(v)
    assert r['comissao_motos'] == Decimal('80')  # 100 - 20


def test_comissao_pecas(db, loja_factory, peca_factory):
    _limpar_faixas()
    comissao_service.set_comissao_base_moto('0')
    p = peca_factory()
    p.valor_comissao = Decimal('10')
    _db.session.flush()
    v = _venda_faturada(loja_factory(), 'V1', desconto=Decimal('0'))
    _db.session.add(HoraVendaItemPeca(
        venda_id=v.id, peca_id=p.id, qtd=Decimal('3'),
        preco_unitario_referencia=Decimal('50'), preco_final=Decimal('150'),
    ))
    _db.session.flush()
    r = comissao_service.calcular_comissao_venda(v)
    assert r['comissao_pecas'] == Decimal('30')  # 10 * 3


def test_relatorio_agrupa_por_vendedor_so_faturado(db, loja_factory):
    _limpar_faixas()
    comissao_service.set_comissao_base_moto('100')
    loja = loja_factory()
    vend_a = f'VA-{uuid.uuid4().hex[:6]}'
    vend_b = f'VB-{uuid.uuid4().hex[:6]}'
    _venda_faturada(loja, vend_a, desconto=Decimal('0'))
    _venda_faturada(loja, vend_a, desconto=Decimal('0'))
    _venda_faturada(loja, vend_b, desconto=Decimal('0'))
    _venda_faturada(loja, vend_a, desconto=Decimal('0'), status='COTACAO')  # ignorada
    rel = comissao_service.relatorio_comissao()
    por = {r['vendedor']: r for r in rel}
    assert por[vend_a]['qtd_vendas'] == 2  # so as 2 FATURADAS de A
    assert por[vend_a]['total'] == Decimal('200')
    assert por[vend_b]['qtd_vendas'] == 1
