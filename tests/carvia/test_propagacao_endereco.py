"""Propagação de cidade/UF do endereço destino CarVia para registros em aberto.

Fase A do plano docs/superpowers/plans/2026-06-23-carvia-propagacao-endereco-cce.md.
"""
from app import db as _db
from app.utils.propagacao_endereco_carvia import propagar_cidade_uf_carvia


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _embarque_item_carvia(numero_nf, cidade, uf, lote='CARVIA-NF-1', status='ativo'):
    from app.embarques.models import Embarque, EmbarqueItem
    from app.utils.timezone import agora_utc_naive
    emb = Embarque(numero=None, status=status, criado_em=agora_utc_naive())
    _db.session.add(emb)
    _db.session.flush()
    item = EmbarqueItem(
        embarque_id=emb.id, separacao_lote_id=lote, nota_fiscal=numero_nf,
        cliente='C', pedido='P', cidade_destino=cidade, uf_destino=uf, status=status,
    )
    _db.session.add(item)
    _db.session.flush()
    return item


def _entrega_carvia(numero_nf, cidade, uf, entregue=False):
    from app.monitoramento.models import EntregaMonitorada
    e = EntregaMonitorada(numero_nf=numero_nf, cliente='C', municipio=cidade, uf=uf,
                          origem='CARVIA', entregue=entregue)
    _db.session.add(e)
    _db.session.flush()
    return e


# --------------------------------------------------------------------------- #
# A1 — helper R1-safe                                                          #
# --------------------------------------------------------------------------- #

def test_propaga_cidade_uf_para_embarque_item_carvia_aberto(db):
    item = _embarque_item_carvia('555', 'Cidade Velha', 'RJ')
    res = propagar_cidade_uf_carvia(['555'], [], 'Cidade Nova', 'SP')
    db.session.refresh(item)
    assert item.cidade_destino == 'Cidade Nova'
    assert item.uf_destino == 'SP'
    assert res['embarque_itens'] == 1


def test_nao_toca_entrega_ja_entregue(db):
    e = _entrega_carvia('556', 'Cidade Velha', 'RJ', entregue=True)
    res = propagar_cidade_uf_carvia(['556'], [], 'Cidade Nova', 'SP')
    db.session.refresh(e)
    assert e.municipio == 'Cidade Velha'  # intacta
    assert res['entregas'] == 0


# --------------------------------------------------------------------------- #
# A2 — service de propagação                                                   #
# --------------------------------------------------------------------------- #

def _endereco_destino(cnpj='98765432000155', cidade='Cidade Velha', uf='RJ'):
    from app.carvia.models.clientes import CarviaCliente, CarviaClienteEndereco
    cli = CarviaCliente(nome_comercial='CLI', ativo=True, criado_por='t')
    _db.session.add(cli)
    _db.session.flush()
    end = CarviaClienteEndereco(
        cliente_id=cli.id, cnpj=cnpj, tipo='DESTINO',
        fisico_cidade=cidade, fisico_uf=uf, criado_por='t',
    )
    _db.session.add(end)
    _db.session.flush()
    return end


def test_propaga_nf_ativa_por_cnpj(db):
    from app.carvia.models.documentos import CarviaNf
    from app.carvia.services.clientes.propagacao_endereco_service import (
        CarviaPropagacaoEnderecoService,
    )
    end = _endereco_destino(cnpj='11222333000144')
    nf = CarviaNf(numero_nf='900', cnpj_emitente='1', nome_emitente='E',
                  cnpj_destinatario='11222333000144', nome_destinatario='D',
                  cidade_destinatario='Cidade Velha', uf_destinatario='RJ',
                  valor_total=1, tipo_fonte='MANUAL', status='ATIVA', criado_por='t')
    _db.session.add(nf)
    _db.session.flush()
    end.fisico_cidade = 'Cidade Nova'
    end.fisico_uf = 'SP'
    _db.session.flush()

    res = CarviaPropagacaoEnderecoService.propagar(end.id)
    db.session.refresh(nf)
    assert nf.cidade_destinatario == 'Cidade Nova'
    assert nf.uf_destinatario == 'SP'
    assert res['nfs'] == 1


def test_endereco_origem_nao_propaga(db):
    from app.carvia.services.clientes.propagacao_endereco_service import (
        CarviaPropagacaoEnderecoService,
    )
    end = _endereco_destino()
    end.tipo = 'ORIGEM'
    _db.session.flush()
    res = CarviaPropagacaoEnderecoService.propagar(end.id)
    assert res == {'cotacoes': 0, 'nfs': 0, 'operacoes': 0,
                   'embarque_itens': 0, 'entregas': 0}


# --------------------------------------------------------------------------- #
# A3 — hook no atualizar_endereco                                             #
# --------------------------------------------------------------------------- #

def test_atualizar_endereco_dispara_propagacao(db):
    from app.carvia.models.documentos import CarviaNf
    from app.carvia.services.clientes.cliente_service import CarviaClienteService
    end = _endereco_destino(cnpj='55666777000188', cidade='Velha', uf='RJ')
    nf = CarviaNf(numero_nf='950', cnpj_emitente='1', nome_emitente='E',
                  cnpj_destinatario='55666777000188', nome_destinatario='D',
                  cidade_destinatario='Velha', uf_destinatario='RJ',
                  valor_total=1, tipo_fonte='MANUAL', status='ATIVA', criado_por='t')
    _db.session.add(nf)
    _db.session.flush()

    ok, erro, ctx = CarviaClienteService.atualizar_endereco(
        end.id, {'fisico_cidade': 'Nova', 'fisico_uf': 'SP'})
    assert ok and erro is None
    assert ctx and ctx.get('propagacao', {}).get('nfs') == 1
    db.session.refresh(nf)
    assert nf.cidade_destinatario == 'Nova'


def test_atualizar_endereco_sem_mudar_cidade_uf_nao_propaga(db):
    from app.carvia.services.clientes.cliente_service import CarviaClienteService
    end = _endereco_destino(cnpj='10101010000110', cidade='Velha', uf='RJ')
    ok, erro, ctx = CarviaClienteService.atualizar_endereco(
        end.id, {'razao_social': 'Outra Razao'})
    assert ok
    assert (ctx or {}).get('propagacao') is None
