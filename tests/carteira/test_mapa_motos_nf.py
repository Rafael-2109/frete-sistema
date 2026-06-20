"""Mapa de pedidos: enriquecimento de pedido_info/totais com qtd_motos e NFs.

Cobre o caminho NACOM (motos=0; NFs vindas de Separacao.numero_nf, so quando
faturado). O caminho CarVia (cotacao MOTO -> qtd_total_motos; pedido -> SUM
quantidade dos itens COM modelo_moto_id + CarviaPedidoItem.numero_nf) foi
validado com dados reais (COT-37 -> 1 moto/sem NF; PED-33-1 -> 3 motos/NF 999001)
— fixtures CarVia completas (cliente+enderecos+modelo+cotacao+motos+pedido+itens)
sao custosas e a logica e isolada/aditiva.
"""
from unittest.mock import patch

from app.separacao.models import Separacao
from app.carteira.services.mapa_service import MapaService


def _sep(**kw):
    base = dict(cod_uf='SP', cnpj_cpf='12345678000199', raz_social_red='CLI_MAPA',
                nome_cidade='SAO PAULO', nf_cd=False, sincronizado_nf=False,
                qtd_saldo=10, cod_produto='P1')
    base.update(kw)
    return Separacao(**base)


def test_nacom_expoe_nf_quando_faturado_e_motos_zero(db):
    # Pedido faturado: saldo 0 + sincronizado + NF -> deve expor a NF
    db.session.add(_sep(separacao_lote_id='LOTE_MAPA_NF', num_pedido='VCDNF1',
                        numero_nf='12345', sincronizado_nf=True, qtd_saldo=0))
    # Pedido pendente: sem NF -> nfs vazio
    db.session.add(_sep(separacao_lote_id='LOTE_MAPA_SEMNF', num_pedido='VCDNF2',
                        cnpj_cpf='99999999000188', raz_social_red='CLI_MAPA2',
                        numero_nf=None, qtd_saldo=10))
    db.session.commit()

    svc = MapaService()
    with patch.object(MapaService, 'geocodificar_endereco', return_value=(-23.4, -46.8)):
        clientes = svc.obter_clientes_para_mapa(
            [], lotes=['LOTE_MAPA_NF', 'LOTE_MAPA_SEMNF'])

    by_ped = {p['num_pedido']: p for c in clientes for p in c['pedidos']}

    # NF exibida apenas quando existe
    assert by_ped['VCDNF1']['nfs'] == ['12345']
    assert by_ped['VCDNF2']['nfs'] == []

    # NACOM nunca tem motos (conservas)
    assert by_ped['VCDNF1']['qtd_motos'] == 0
    assert by_ped['VCDNF2']['qtd_motos'] == 0

    # totais.qtd_motos sempre presente (chave nova) e 0 p/ NACOM
    assert all(c['totais']['qtd_motos'] == 0 for c in clientes)


def test_nacom_dedup_nfs_do_mesmo_pedido(db):
    # Mesmo pedido com 2 itens, ambos faturados na MESMA NF -> nfs sem duplicar
    db.session.add(_sep(separacao_lote_id='LOTE_MAPA_DUP', num_pedido='VCDDUP',
                        cod_produto='PA', numero_nf='777', sincronizado_nf=True, qtd_saldo=0))
    db.session.add(_sep(separacao_lote_id='LOTE_MAPA_DUP', num_pedido='VCDDUP',
                        cod_produto='PB', numero_nf='777', sincronizado_nf=True, qtd_saldo=0))
    db.session.commit()

    svc = MapaService()
    with patch.object(MapaService, 'geocodificar_endereco', return_value=(-23.4, -46.8)):
        clientes = svc.obter_clientes_para_mapa([], lotes=['LOTE_MAPA_DUP'])

    pedidos = [p for c in clientes for p in c['pedidos']]
    assert len(pedidos) == 1
    assert pedidos[0]['nfs'] == ['777']
