"""
Propagacao do cancelamento de EmbarqueItem CarVia ao CarviaFrete.

Bug (causa confirmada): cancelar o EmbarqueItem CarVia individualmente reseta o
CarviaPedido mas NAO toca o CarviaFrete — que fica PENDENTE com item morto
(fantasmas 374/549/580/581 em prod). A Fase B3 de `lancar_frete_carvia` cancelaria
fretes orfaos, mas so roda quando AINDA ha item CarVia ativo (early-return em
`_processar` linha 127). Quando o ULTIMO item e cancelado, a B3 nunca executa.

`cancelar_fretes_orfaos_embarque` cobre esse caso: cancela CarviaFrete do embarque
cujo cnpj_destino nao tem mais EmbarqueItem CarVia ATIVO — com os MESMOS guards da
B3 (so PENDENTE, sem CTe, sem operacao/subcontrato; demais ficam para revisao).
"""
import uuid


def _setup_frete(db, *, item_status='ativo', valor_cte=None, frete_status='PENDENTE'):
    """Cria transportadora + embarque + EmbarqueItem CarVia + CarviaFrete vinculados."""
    from app.transportadoras.models import Transportadora
    from app.embarques.models import Embarque, EmbarqueItem
    from app.carvia.models import CarviaFrete
    from app.utils.timezone import agora_utc_naive

    sufixo = uuid.uuid4().hex[:8]
    cnpj_dest = f'1234567800{sufixo[:4]}'
    nf = f'NF{sufixo}'

    transp = Transportadora(razao_social=f'TRANSP TESTE {sufixo}',
                            cnpj=f'9988776600{sufixo[:4]}', ativo=True,
                            cidade='SAO PAULO', uf='SP')
    db.session.add(transp)
    db.session.flush()

    emb = Embarque(numero=int(sufixo, 16) % 9000000, status='ativo',
                   transportadora_id=transp.id, tipo_carga='FRACIONADA',
                   criado_por='test', criado_em=agora_utc_naive())
    db.session.add(emb)
    db.session.flush()

    item = EmbarqueItem(
        embarque_id=emb.id, separacao_lote_id=f'CARVIA-PED-{sufixo}',
        cnpj_cliente=cnpj_dest, cliente='CLIENTE TESTE', pedido=f'PED-{sufixo}',
        nota_fiscal=nf, peso=100, valor=1000, status=item_status,
        provisorio=False, uf_destino='SP', cidade_destino='SAO PAULO',
    )
    db.session.add(item)

    frete = CarviaFrete(
        embarque_id=emb.id, transportadora_id=transp.id,
        cnpj_emitente='11111111000111', cnpj_destino=cnpj_dest,
        uf_destino='SP', cidade_destino='SAO PAULO', tipo_carga='FRACIONADA',
        peso_total=100, valor_total_nfs=1000, quantidade_nfs=1, numeros_nfs=nf,
        valor_cotado=50, valor_cte=valor_cte,
        status=frete_status, criado_por='test',
    )
    db.session.add(frete)
    db.session.flush()
    return emb, item, frete


def test_cancela_frete_orfao_quando_item_cancelado(db):
    """Item cancelado + frete PENDENTE sem CTe/op/sub -> frete CANCELADO."""
    from app.carvia.services.documentos.embarque_carvia_service import (
        cancelar_fretes_orfaos_embarque,
    )
    emb, item, frete = _setup_frete(db, item_status='cancelado')

    cancelados = cancelar_fretes_orfaos_embarque(emb.id, 'test')

    assert frete.id in cancelados
    assert frete.status == 'CANCELADO'


def test_nao_cancela_frete_com_item_ativo(db):
    """Item AINDA ativo -> frete preservado."""
    from app.carvia.services.documentos.embarque_carvia_service import (
        cancelar_fretes_orfaos_embarque,
    )
    emb, item, frete = _setup_frete(db, item_status='ativo')

    cancelar_fretes_orfaos_embarque(emb.id, 'test')

    assert frete.status == 'PENDENTE'


def test_nao_cancela_frete_com_cte_real(db):
    """Item cancelado mas frete tem CTe (custo real) -> NAO cancela."""
    from app.carvia.services.documentos.embarque_carvia_service import (
        cancelar_fretes_orfaos_embarque,
    )
    emb, item, frete = _setup_frete(db, item_status='cancelado', valor_cte=170.0)

    cancelar_fretes_orfaos_embarque(emb.id, 'test')

    assert frete.status == 'PENDENTE'


def test_nao_cancela_frete_com_operacao(db):
    """Item cancelado mas frete tem operacao (CTe CarVia) -> revisao manual, NAO cancela."""
    from app.carvia.services.documentos.embarque_carvia_service import (
        cancelar_fretes_orfaos_embarque,
    )
    emb, item, frete = _setup_frete(db, item_status='cancelado')

    # no_autoflush: seta operacao_id so para exercer o guard, sem persistir a FK
    with db.session.no_autoflush:
        frete.operacao_id = 99999
        cancelar_fretes_orfaos_embarque(emb.id, 'test')

    assert frete.status == 'PENDENTE'
