"""Testes de chassi_protegido — chassi vinculado a pedido/NF entrada."""


def test_chassi_novo_nao_protegido(db):
    from app.hora.services import chassi_protecao_service
    assert chassi_protecao_service.chassi_protegido('CHASSI-NUNCA-VISTO-XX') is False


def test_chassi_em_pedido_protegido(db, pedido_compra_factory):
    from app.hora.services import chassi_protecao_service
    chassi = '9ABCDPED1111111111111111'
    pedido_compra_factory(chassis=[chassi])
    assert chassi_protecao_service.chassi_protegido(chassi) is True


def test_chassi_em_nf_entrada_protegido(db, nf_entrada_factory):
    from app.hora.services import chassi_protecao_service
    chassi = '9ABCDNF22222222222222222'
    nf_entrada_factory(chassis=[chassi])
    assert chassi_protecao_service.chassi_protegido(chassi) is True


def test_chassi_vazio_nao_protegido(db):
    from app.hora.services import chassi_protecao_service
    assert chassi_protecao_service.chassi_protegido('') is False
    assert chassi_protecao_service.chassi_protegido(None) is False


def test_motivos_protecao_lista(db, pedido_compra_factory, nf_entrada_factory):
    from app.hora.services import chassi_protecao_service
    chassi = '9ABCDDUO333333333333333'
    pedido_compra_factory(chassis=[chassi])
    nf_entrada_factory(chassis=[chassi])
    motivos = chassi_protecao_service.motivos_protecao(chassi)
    origens = {m['origem'] for m in motivos}
    assert origens == {'pedido', 'nf_entrada'}


def test_chassi_protegido_por_conferencia_recebimento(db, loja_factory, modelo_moto):
    """Chassi que só existe em conferência de recebimento provisório é protegido.

    Cenário: moto chegou via recebimento sem NF (provisório). Ainda não existe
    HoraPedidoItem nem HoraNfEntradaItem para este chassi. A conferência ativa
    (substituida=False) deve ser suficiente para proteger o chassi contra o
    backfill TagPlus.
    """
    import uuid as _uuid
    from app.hora.services.chassi_protecao_service import chassi_protegido
    from app.hora.services import recebimento_service

    loja = loja_factory()
    chassi = ('CONF' + _uuid.uuid4().hex.upper())[:25].ljust(25, '0')

    rec = recebimento_service.criar_recebimento_sem_nf(loja_id=loja.id, operador='t')
    recebimento_service.definir_qtd_declarada(recebimento_id=rec.id, qtd=1, usuario='t')
    recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id,
        numero_chassi=chassi,
        modelo_id_conferido=modelo_moto.id,
        cor_conferida='PRETA',
        avaria_fisica=False,
        qr_code_lido=True,
        operador='t',
    )

    from app import db as _db
    _db.session.expire_all()
    assert chassi_protegido(chassi) is True
