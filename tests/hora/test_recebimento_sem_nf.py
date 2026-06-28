import uuid
from datetime import date as _date
from app import db as _db
from app.hora.models import (
    HoraNfEntrada, HoraRecebimento, HoraRecebimentoEsperado, HoraMoto,
)
from app.hora.services import recebimento_service
from app.hora.services.moto_service import status_atual
from app.utils.timezone import agora_utc_naive


def _chassi(prefix: str) -> str:
    return f'{prefix}{uuid.uuid4().hex.upper()}'[:25].ljust(25, '0')


def test_nf_provisoria_property(db, loja_factory):
    loja = loja_factory()
    nf = HoraNfEntrada(
        chave_44='PROV' + uuid.uuid4().hex, numero_nf='PROV-1',
        cnpj_emitente='', cnpj_destinatario=loja.cnpj,
        loja_destino_id=loja.id, data_emissao=_date.today(),
        valor_total=0, tipo='PROVISORIA', criado_em=agora_utc_naive(),
    )
    _db.session.add(nf); _db.session.flush()
    assert nf.provisoria is True
    nf.tipo = 'REAL'
    assert nf.provisoria is False


def test_criar_recebimento_sem_nf_materializa_snapshot(db, loja_factory, pedido_compra_factory):
    from app.hora.models import HoraPedido
    chassi_a = _chassi('AAA')
    pedido = pedido_compra_factory([chassi_a])          # status ABERTO, loja = loja_origem
    loja_id = pedido.loja_destino_id

    rec = recebimento_service.criar_recebimento_sem_nf(loja_id=loja_id, operador='tester')
    _db.session.expire_all()

    nf = HoraNfEntrada.query.get(rec.nf_id)
    assert nf.provisoria is True
    esperados = HoraRecebimentoEsperado.query.filter_by(recebimento_id=rec.id).all()
    assert len(esperados) == 1
    assert esperados[0].chassi_esperado == chassi_a
    assert esperados[0].pedido_id == pedido.id


def test_conferencia_provisoria_casa_modelo_e_chassi_extra(db, loja_factory, pedido_compra_factory, modelo_moto):
    chassi_ped = _chassi('PED')           # item do pedido COM chassi
    pedido = pedido_compra_factory([chassi_ped])
    loja_id = pedido.loja_destino_id
    rec = recebimento_service.criar_recebimento_sem_nf(loja_id=loja_id, operador='tester')
    recebimento_service.definir_qtd_declarada(recebimento_id=rec.id, qtd=2, usuario='tester')

    # (a) chassi do snapshot -> RECEBIDA/CONFERIDA, sem CHASSI_EXTRA
    recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi_ped,
        modelo_id_conferido=modelo_moto.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=True, operador='tester',
    )
    # (b) chassi fora do snapshot -> CHASSI_EXTRA, sem bloquear
    chassi_extra = _chassi('EXT')
    recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi_extra,
        modelo_id_conferido=modelo_moto.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=True, operador='tester',
    )
    _db.session.expire_all()
    assert status_atual(chassi_ped) in ('RECEBIDA', 'CONFERIDA')
    assert HoraMoto.query.get(chassi_ped) is not None
    # chassi do snapshot CASA (nao vira CHASSI_EXTRA) e consome o slot
    conf_ped = next(c for c in rec.conferencias if c.numero_chassi == chassi_ped)
    assert not any(d.tipo == 'CHASSI_EXTRA' for d in conf_ped.divergencias)
    esperado = HoraRecebimentoEsperado.query.filter_by(
        recebimento_id=rec.id, chassi_esperado=chassi_ped).first()
    assert esperado is not None and esperado.consumido_por_conferencia_id == conf_ped.id
    conf_extra = next(c for c in rec.conferencias if c.numero_chassi == chassi_extra)
    assert any(d.tipo == 'CHASSI_EXTRA' for d in conf_extra.divergencias)

    rec = recebimento_service.finalizar_recebimento(recebimento_id=rec.id, operador='tester')
    _db.session.expire_all()
    # D8: provisorio NAO gera MOTO_FALTANDO
    faltando = [c for c in rec.conferencias if c.tipo_divergencia == 'MOTO_FALTANDO']
    assert faltando == []


def test_anexar_nf_real_promove_e_reprocessa(db, loja_factory, pedido_compra_factory, modelo_moto):
    chassi = _chassi('REAL')
    pedido = pedido_compra_factory([chassi])
    loja_id = pedido.loja_destino_id
    rec = recebimento_service.criar_recebimento_sem_nf(loja_id=loja_id, operador='tester')
    recebimento_service.definir_qtd_declarada(recebimento_id=rec.id, qtd=1, usuario='tester')
    recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi,
        modelo_id_conferido=modelo_moto.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=True, operador='tester')
    recebimento_service.finalizar_recebimento(recebimento_id=rec.id, operador='tester')

    payload = {
        'nf': {'chave_44': uuid.uuid4().hex.zfill(44), 'numero_nf': '12345',
               'cnpj_emitente': '12345678000199', 'cnpj_destinatario': '00000000000000',
               'data_emissao': _date.today(), 'valor_total': 5000},
        'itens': [{'numero_chassi': chassi, 'preco_real': 5000,
                   'modelo_texto_original': modelo_moto.nome_modelo, 'cor_texto_original': 'PRETA'}],
    }
    nf = recebimento_service.anexar_nf_real_ao_recebimento(
        recebimento_id=rec.id, pdf_bytes=b'', operador='tester', payload=payload)
    _db.session.expire_all()
    assert nf.tipo == 'REAL'
    assert nf.numero_nf == '12345'
    from app.hora.models import HoraNfEntradaItem
    assert HoraNfEntradaItem.query.filter_by(nf_id=nf.id, numero_chassi=chassi).count() == 1


# ---------------------------------------------------------------------------
# Task 9: isolamento fiscal + invariante assert_item_moto_consistente (R1)
# ---------------------------------------------------------------------------

def test_nf_provisoria_isolada_de_listas_de_nf(db, loja_factory, pedido_compra_factory):
    """Step A: NF provisória nunca aparece no autocomplete sem_recebimento=True.

    A NF provisória sempre tem recebimento (criado em criar_recebimento_sem_nf),
    portanto o filtro ~HoraNfEntrada.recebimentos.any() já a exclui.
    Nenhuma alteração de código é necessária — este teste documenta a invariante.
    """
    from app.hora.services import autocomplete_service
    pedido = pedido_compra_factory([_chassi('ISO')])
    recebimento_service.criar_recebimento_sem_nf(
        loja_id=pedido.loja_destino_id, operador='t')
    _db.session.expire_all()
    # autocomplete de NFs sem_recebimento nunca traz provisória (ela já tem recebimento)
    res = autocomplete_service.nfs_entrada(
        'PROV', lojas_permitidas_ids=None, sem_recebimento=True)
    assert all(not (r['numero_nf'] or '').startswith('PROV') for r in res)


def test_assert_item_moto_consistente_nao_falha_apos_anexar_nf_real(
        db, loja_factory, pedido_compra_factory, modelo_moto):
    """Step B: R1 não se materializa.

    Moto criada via conferência provisória (sem HoraNfEntradaItem) torna-se
    consistente logo após anexar_nf_real_ao_recebimento, que cria os itens.
    assert_item_moto_consistente NÃO deve levantar AssertionError.

    Adicionalmente, desconsiderar_item_nf deve ser bloqueado (ValueError) porque
    a moto provisória tem eventos (RECEBIDA) e porque a NF já entrou em recebimento —
    garantindo que a moto não seja apagada por engano.
    """
    from app.hora.models import HoraNfEntradaItem
    from app.hora.services.nf_entrada_service import (
        assert_item_moto_consistente, desconsiderar_item_nf,
    )

    chassi = _chassi('R1TST')
    pedido = pedido_compra_factory([chassi])
    loja_id = pedido.loja_destino_id

    # Cria recebimento provisório, faz conferência cega e finaliza
    rec = recebimento_service.criar_recebimento_sem_nf(loja_id=loja_id, operador='tester')
    recebimento_service.definir_qtd_declarada(recebimento_id=rec.id, qtd=1, usuario='tester')
    recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi,
        modelo_id_conferido=modelo_moto.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=True, operador='tester',
    )
    recebimento_service.finalizar_recebimento(recebimento_id=rec.id, operador='tester')

    # Anexa NF real — cria HoraNfEntradaItem para os chassis conferidos
    payload = {
        'nf': {
            'chave_44': uuid.uuid4().hex.zfill(44),
            'numero_nf': 'NF-R1TST',
            'cnpj_emitente': '12345678000199',
            'cnpj_destinatario': '00000000000000',
            'data_emissao': _date.today(),
            'valor_total': 5000,
        },
        'itens': [{'numero_chassi': chassi, 'preco_real': 5000,
                   'modelo_texto_original': modelo_moto.nome_modelo,
                   'cor_texto_original': 'PRETA'}],
    }
    nf = recebimento_service.anexar_nf_real_ao_recebimento(
        recebimento_id=rec.id, pdf_bytes=b'', operador='tester', payload=payload)
    _db.session.expire_all()

    # Invariante: todos os itens da NF real devem ser consistentes (não levanta)
    itens = HoraNfEntradaItem.query.filter_by(nf_id=nf.id).all()
    assert len(itens) == 1, 'Esperado 1 item após anexar NF real'
    for item in itens:
        assert_item_moto_consistente(item)  # não deve levantar AssertionError

    # Guard: desconsiderar é bloqueado (moto tem eventos + NF em recebimento)
    item = itens[0]
    try:
        desconsiderar_item_nf(item.id, operador='tester')
        assert False, 'Esperado ValueError ao tentar desconsiderar moto provisória'
    except ValueError:
        pass  # comportamento correto — moto está bloqueada


# ---------------------------------------------------------------------------
# Fix-wave: slot do snapshot deve continuar disponível para a MESMA conferência
# (re-derivação) e para a conferência que SUBSTITUI uma inativa (reconferência).
# ---------------------------------------------------------------------------

def test_reconferir_mesmo_chassi_nao_vira_chassi_extra(
        db, loja_factory, pedido_compra_factory, modelo_moto):
    """Re-submeter/ajustar o MESMO chassi (is_new=False) re-roda
    _redefinir_divergencias para a mesma conferência. O slot do snapshot, já
    consumido por ela, deve continuar disponível — caso contrário a 2ª derivação
    marca CHASSI_EXTRA falso e vira COM_DIVERGENCIA.
    """
    chassi_ped = _chassi('SAME')
    pedido = pedido_compra_factory([chassi_ped])
    loja_id = pedido.loja_destino_id
    rec = recebimento_service.criar_recebimento_sem_nf(loja_id=loja_id, operador='tester')
    recebimento_service.definir_qtd_declarada(recebimento_id=rec.id, qtd=1, usuario='tester')

    # 1a conferência: casa o slot do snapshot (limpo, sem CHASSI_EXTRA)
    recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi_ped,
        modelo_id_conferido=modelo_moto.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=True, operador='tester')
    _db.session.expire_all()
    conf = next(c for c in rec.conferencias
                if c.numero_chassi == chassi_ped and not c.substituida)
    assert not any(d.tipo == 'CHASSI_EXTRA' for d in conf.divergencias)

    # 2a conferência do MESMO chassi (is_new=False) — toggla avaria/cor
    recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi_ped,
        modelo_id_conferido=modelo_moto.id, cor_conferida='AZUL',
        avaria_fisica=True, qr_code_lido=True, operador='tester')
    _db.session.expire_all()
    conf = next(c for c in rec.conferencias
                if c.numero_chassi == chassi_ped and not c.substituida)
    assert not any(d.tipo == 'CHASSI_EXTRA' for d in conf.divergencias), \
        'Re-derivar o mesmo chassi não pode virar CHASSI_EXTRA'


def test_reconferencia_nao_vira_chassi_extra(
        db, loja_factory, pedido_compra_factory, modelo_moto):
    """Reconferência marca a conf antiga como substituida=True e cria uma NOVA
    conf ativa para o mesmo chassi. O slot do snapshot, consumido pela conf
    inativa, deve voltar a ficar disponível para a nova — senão vira CHASSI_EXTRA.
    """
    chassi_ped = _chassi('RECO')
    pedido = pedido_compra_factory([chassi_ped])
    loja_id = pedido.loja_destino_id
    rec = recebimento_service.criar_recebimento_sem_nf(loja_id=loja_id, operador='tester')
    recebimento_service.definir_qtd_declarada(recebimento_id=rec.id, qtd=1, usuario='tester')

    conf = recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi_ped,
        modelo_id_conferido=modelo_moto.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=True, operador='tester')
    conf_id = conf.id
    recebimento_service.finalizar_recebimento(recebimento_id=rec.id, operador='tester')

    # Reconferência: substitui a conf antiga e enfileira uma nova pendente
    recebimento_service.reiniciar_conferencia_para_chassis(
        recebimento_id=rec.id, conferencia_ids=[conf_id], operador='tester')

    # Re-confere o MESMO chassi -> atualiza a nova conf ativa
    recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id, numero_chassi=chassi_ped,
        modelo_id_conferido=modelo_moto.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=True, operador='tester')
    _db.session.expire_all()

    conf_ativa = next(c for c in rec.conferencias
                      if c.numero_chassi == chassi_ped and not c.substituida)
    assert conf_ativa.id != conf_id
    assert not any(d.tipo == 'CHASSI_EXTRA' for d in conf_ativa.divergencias), \
        'Reconferência do mesmo chassi não pode virar CHASSI_EXTRA'


# ---------------------------------------------------------------------------
# excluir_recebimento sobre PROVISORIO: as FKs de hora_recebimento_esperado não
# têm ON DELETE/cascade — o snapshot precisa ser apagado antes do delete(rec),
# senão estoura IntegrityError (HTTP 500) de forma determinística.
# ---------------------------------------------------------------------------

def test_excluir_recebimento_provisorio_sem_conferencia_remove_snapshot(
        db, loja_factory, pedido_compra_factory):
    """CASO A: provisório com slots de snapshot mas SEM conferência. Sem o fix,
    SQLAlchemy tenta nulificar recebimento_id (NOT NULL) -> NotNullViolation."""
    chassi = _chassi('DELA')
    pedido = pedido_compra_factory([chassi])
    rec = recebimento_service.criar_recebimento_sem_nf(
        loja_id=pedido.loja_destino_id, operador='tester')
    rec_id = rec.id
    _db.session.expire_all()
    assert HoraRecebimentoEsperado.query.filter_by(recebimento_id=rec_id).count() >= 1

    res = recebimento_service.excluir_recebimento(recebimento_id=rec_id, operador='tester')
    _db.session.expire_all()
    assert res['ok'] is True
    assert HoraRecebimento.query.get(rec_id) is None
    assert HoraRecebimentoEsperado.query.filter_by(recebimento_id=rec_id).count() == 0


def test_excluir_recebimento_provisorio_com_conferencia_remove_snapshot(
        db, loja_factory, pedido_compra_factory, modelo_moto):
    """CASO B: slot já CONSUMIDO por uma conferência. O cascade deleta a
    conferência; sem apagar o slot antes, a FK consumido_por_conferencia_id
    estoura ForeignKeyViolation."""
    chassi = _chassi('DELB')
    pedido = pedido_compra_factory([chassi])
    rec = recebimento_service.criar_recebimento_sem_nf(
        loja_id=pedido.loja_destino_id, operador='tester')
    rec_id = rec.id
    recebimento_service.definir_qtd_declarada(recebimento_id=rec_id, qtd=1, usuario='tester')
    recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec_id, numero_chassi=chassi,
        modelo_id_conferido=modelo_moto.id, cor_conferida='PRETA',
        avaria_fisica=False, qr_code_lido=True, operador='tester')
    _db.session.expire_all()
    slot = HoraRecebimentoEsperado.query.filter_by(recebimento_id=rec_id).first()
    assert slot.consumido_por_conferencia_id is not None

    res = recebimento_service.excluir_recebimento(recebimento_id=rec_id, operador='tester')
    _db.session.expire_all()
    assert res['ok'] is True
    assert HoraRecebimento.query.get(rec_id) is None
    assert HoraRecebimentoEsperado.query.filter_by(recebimento_id=rec_id).count() == 0
