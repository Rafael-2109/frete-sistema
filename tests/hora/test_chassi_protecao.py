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
