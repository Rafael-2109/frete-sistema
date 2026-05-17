"""Testes do reprocessamento de recebimentos apos edicao de chassi em item de NF.

Cobre o cenario reportado pelo usuario (2026-05-16):

  - NF tem chassi X, operador recebe fisicamente chassi Y, registra Y como
    CHASSI_EXTRA, finaliza recebimento -> conferencia batch MOTO_FALTANDO
    para X eh criada.
  - Operador percebe o engano e edita a NF: chassi X -> Y.
  - Sistema deveria reprocessar: deletar batch X, reavaliar Y (deixa de ser
    CHASSI_EXTRA) e recalcular status (vira CONCLUIDO).

Usa `loja_factory` (CNPJ UUID) para isolamento — evita colisao com dados
residuais de fixtures escopadas em sessoes anteriores.
"""
import uuid
from datetime import date as _date

from app import db as _db
from app.hora.models import (
    HoraConferenciaDivergencia,
    HoraModelo,
    HoraMoto,
    HoraMotoEvento,
    HoraNfEntrada,
    HoraNfEntradaItem,
    HoraRecebimento,
    HoraRecebimentoConferencia,
)
from app.hora.services import nf_entrada_service, recebimento_service
from app.utils.timezone import agora_utc_naive


def _chassi(prefix: str) -> str:
    """Gera chassi unico de 25 chars com prefixo identificavel."""
    uid = uuid.uuid4().hex.upper()
    return f'{prefix}{uid}'[:25].ljust(25, '0')


def _criar_modelo() -> HoraModelo:
    nome = f'TST-MODEL-{uuid.uuid4().hex[:8].upper()}'
    m = HoraModelo(nome_modelo=nome, ativo=True)
    _db.session.add(m)
    _db.session.flush()
    return m


def _criar_nf_local(loja, modelo, chassis: list[str]) -> HoraNfEntrada:
    uid = uuid.uuid4().hex[:12].upper()
    nf = HoraNfEntrada(
        chave_44=uid.zfill(44),
        numero_nf=uid[:8],
        cnpj_emitente='12345678000199',
        cnpj_destinatario=loja.cnpj,
        loja_destino_id=loja.id,
        data_emissao=_date.today(),
        valor_total=1000,
        criado_em=agora_utc_naive(),
    )
    _db.session.add(nf)
    _db.session.flush()
    for chassi in chassis:
        if not HoraMoto.query.get(chassi):
            m = HoraMoto(numero_chassi=chassi, modelo_id=modelo.id, cor='PRETA')
            _db.session.add(m)
            _db.session.flush()
        item = HoraNfEntradaItem(
            nf_id=nf.id, numero_chassi=chassi, preco_real=1000,
            modelo_texto_original=modelo.nome_modelo,
            cor_texto_original='PRETA',
        )
        _db.session.add(item)
    _db.session.flush()
    return nf


def _conferir_chassi_e_finalizar(rec, modelo, chassi):
    """Conferencia cega + finalizacao."""
    if not HoraMoto.query.get(chassi):
        m = HoraMoto(numero_chassi=chassi, modelo_id=modelo.id, cor='PRETA')
        _db.session.add(m)
        _db.session.flush()
    recebimento_service.registrar_conferencia_cega(
        recebimento_id=rec.id,
        numero_chassi=chassi,
        modelo_id_conferido=modelo.id,
        cor_conferida='PRETA',
        avaria_fisica=False,
        operador='tester',
    )


def _setup_cenario_usuario(loja, modelo, chassi_nf, chassi_conferido):
    """NF com chassi_nf + conferencia de chassi_conferido (CHASSI_EXTRA) +
    finalizacao -> batch MOTO_FALTANDO para chassi_nf."""
    nf = _criar_nf_local(loja, modelo, [chassi_nf])
    rec = recebimento_service.iniciar_recebimento(
        nf_id=nf.id, loja_id=loja.id, operador='tester',
    )
    recebimento_service.definir_qtd_declarada(
        recebimento_id=rec.id, qtd=1, usuario='tester',
    )
    _conferir_chassi_e_finalizar(rec, modelo, chassi_conferido)
    rec = recebimento_service.finalizar_recebimento(
        recebimento_id=rec.id, operador='tester',
    )
    return rec, nf


def test_reprocessamento_corrige_chassi_e_zera_divergencias(db, loja_factory):
    """Cenario completo do usuario.

    NF tinha chassi X. Operador conferiu Y (CHASSI_EXTRA). Finalizou: X virou
    batch MOTO_FALTANDO. Operador edita NF: X -> Y. Esperado: batch X some,
    Y deixa de ser CHASSI_EXTRA, status = CONCLUIDO.
    """
    loja = loja_factory()
    modelo = _criar_modelo()
    chassi_x = _chassi('XRP')
    chassi_y = _chassi('YRP')

    rec, nf = _setup_cenario_usuario(loja, modelo, chassi_x, chassi_y)

    # Pre-condicoes (sanity)
    assert rec.status == 'COM_DIVERGENCIA'

    confs_x_antes = [
        c for c in rec.conferencias
        if c.numero_chassi == chassi_x and not c.substituida
    ]
    assert len(confs_x_antes) == 1
    assert confs_x_antes[0].tipo_divergencia == 'MOTO_FALTANDO'

    confs_y_antes = [
        c for c in rec.conferencias
        if c.numero_chassi == chassi_y and not c.substituida
    ]
    assert len(confs_y_antes) == 1
    tipos_y_antes = {d.tipo for d in confs_y_antes[0].divergencias}
    assert 'CHASSI_EXTRA' in tipos_y_antes

    evento_faltando_antes = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi_x, tipo='MOTO_FALTANDO')
        .count()
    )
    assert evento_faltando_antes == 1

    # Acao: edita o unico item da NF de X -> Y
    nf_item = nf.itens[0]
    resultado = nf_entrada_service.editar_nf_item_manual(
        nf_id=nf.id,
        nf_item_id=nf_item.id,
        numero_chassi=chassi_y,
        operador='tester',
    )
    assert resultado['ok'] is True
    assert resultado['numero_chassi'] == chassi_y

    _db.session.expire_all()

    # 1) Conferencia batch X foi removida
    confs_x_depois = (
        HoraRecebimentoConferencia.query
        .filter_by(recebimento_id=rec.id, numero_chassi=chassi_x, substituida=False)
        .all()
    )
    assert confs_x_depois == [], (
        f'Conferencia batch de X deveria ter sido removida, ainda existe: '
        f'{[(c.id, c.tipo_divergencia) for c in confs_x_depois]}'
    )

    # 2) Evento MOTO_FALTANDO de X foi removido
    evento_faltando_depois = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi_x, tipo='MOTO_FALTANDO')
        .count()
    )
    assert evento_faltando_depois == 0

    # 3) Conferencia Y continua, sem CHASSI_EXTRA
    confs_y_depois = (
        HoraRecebimentoConferencia.query
        .filter_by(recebimento_id=rec.id, numero_chassi=chassi_y, substituida=False)
        .all()
    )
    assert len(confs_y_depois) == 1
    tipos_y_depois = {d.tipo for d in confs_y_depois[0].divergencias}
    assert 'CHASSI_EXTRA' not in tipos_y_depois, (
        f'CHASSI_EXTRA deveria ter sumido apos a edicao. tipos={tipos_y_depois}'
    )

    # 4) Status virou CONCLUIDO (zerou divergencias)
    rec_atual = HoraRecebimento.query.get(rec.id)
    assert rec_atual.status == 'CONCLUIDO', (
        f'Status esperado=CONCLUIDO, obtido={rec_atual.status}. '
        f'Divs: {HoraConferenciaDivergencia.query.filter(HoraConferenciaDivergencia.conferencia_id.in_([c.id for c in rec_atual.conferencias])).all()}'
    )


def test_reprocessamento_no_op_quando_chassi_nao_muda(db, loja_factory):
    """Chamar reprocessar_recebimentos_para_nf com chassi_antigo=None ou igual
    ao novo nao deve alterar nada (idempotente + short-circuit)."""
    loja = loja_factory()
    modelo = _criar_modelo()
    chassi_x = _chassi('XNOOP')
    chassi_y = _chassi('YNOOP')
    rec, nf = _setup_cenario_usuario(loja, modelo, chassi_x, chassi_y)
    assert rec.status == 'COM_DIVERGENCIA'

    # Caso 1: chassi_antigo=None
    res = recebimento_service.reprocessar_recebimentos_para_nf(
        nf_id=nf.id, chassi_antigo=None, chassi_novo=chassi_x, operador='tester',
    )
    assert res['recebimentos_afetados'] == 0
    assert res['confs_batch_removidas'] == 0

    # Caso 2: chassi_antigo == chassi_novo
    res2 = recebimento_service.reprocessar_recebimentos_para_nf(
        nf_id=nf.id, chassi_antigo=chassi_x, chassi_novo=chassi_x, operador='tester',
    )
    assert res2['recebimentos_afetados'] == 0

    rec_atual = HoraRecebimento.query.get(rec.id)
    assert rec_atual.status == 'COM_DIVERGENCIA'


def test_reprocessamento_cria_batch_para_chassi_novo_quando_recebimento_finalizado(
    db, loja_factory,
):
    """Cenario: NF tinha X conferido OK. Operador edita NF: X -> Z (chassi novo
    sem conferencia). Esperado: X vira CHASSI_EXTRA (real, mantida), Z vira
    batch MOTO_FALTANDO. Status = COM_DIVERGENCIA."""
    loja = loja_factory()
    modelo = _criar_modelo()
    chassi_x = _chassi('XBATCH')
    chassi_z = _chassi('ZBATCH')

    # NF com X
    nf = _criar_nf_local(loja, modelo, [chassi_x])

    # Recebe e confere X normalmente (sem divergencias)
    rec = recebimento_service.iniciar_recebimento(
        nf_id=nf.id, loja_id=loja.id, operador='tester',
    )
    recebimento_service.definir_qtd_declarada(
        recebimento_id=rec.id, qtd=1, usuario='tester',
    )
    _conferir_chassi_e_finalizar(rec, modelo, chassi_x)
    rec = recebimento_service.finalizar_recebimento(
        recebimento_id=rec.id, operador='tester',
    )
    assert rec.status == 'CONCLUIDO'

    # Edita NF: X -> Z (chassi_z nao tem conferencia)
    nf_item = nf.itens[0]
    nf_entrada_service.editar_nf_item_manual(
        nf_id=nf.id,
        nf_item_id=nf_item.id,
        numero_chassi=chassi_z,
        operador='tester',
    )

    _db.session.expire_all()

    # X (conferencia REAL): mantida, agora com CHASSI_EXTRA
    confs_x = (
        HoraRecebimentoConferencia.query
        .filter_by(recebimento_id=rec.id, numero_chassi=chassi_x, substituida=False)
        .all()
    )
    assert len(confs_x) == 1, 'Conferencia real de X deve continuar (nao eh batch)'
    tipos_x = {d.tipo for d in confs_x[0].divergencias}
    assert 'CHASSI_EXTRA' in tipos_x

    # Z: batch MOTO_FALTANDO criada
    confs_z = (
        HoraRecebimentoConferencia.query
        .filter_by(recebimento_id=rec.id, numero_chassi=chassi_z, substituida=False)
        .all()
    )
    assert len(confs_z) == 1
    tipos_z = {d.tipo for d in confs_z[0].divergencias}
    assert 'MOTO_FALTANDO' in tipos_z

    # Evento MOTO_FALTANDO para Z gravado
    evento_z = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi_z, tipo='MOTO_FALTANDO')
        .count()
    )
    assert evento_z == 1

    # Status: COM_DIVERGENCIA
    rec_atual = HoraRecebimento.query.get(rec.id)
    assert rec_atual.status == 'COM_DIVERGENCIA'


def test_metricas_recebimento_conta_recebidas_extras_e_faltando(
    db, loja_factory,
):
    """`metricas_recebimento` deve discriminar recebidas (reais),
    faltando (batch sintetico) e extra. Antes da refatoracao, o template
    somava tudo como "conferidas" — gerando contagem confusa."""
    loja = loja_factory()
    modelo = _criar_modelo()
    chassi_x = _chassi('XMET')
    chassi_y = _chassi('YMET')

    # NF com X, operador confere Y (extra), finaliza -> batch faltando X
    rec, nf = _setup_cenario_usuario(loja, modelo, chassi_x, chassi_y)

    m = recebimento_service.metricas_recebimento(rec)
    assert m['qtd_nf'] == 1
    assert m['qtd_recebidas'] == 1, (
        f'Y foi recebido (conferencia real), batch X NAO conta. m={m}'
    )
    assert m['qtd_faltando'] == 1, f'X virou batch MOTO_FALTANDO. m={m}'
    assert m['qtd_extra'] == 1, f'Y nao esta na NF. m={m}'
    assert m['qtd_divergencias'] == 2, f'X (faltando) + Y (extra) = 2. m={m}'
    assert m['qtd_ok'] == 0


def test_metricas_recebimento_tudo_ok(db, loja_factory):
    """Quando NF e conferencia batem 100%, metricas mostram qtd_ok > 0 e
    zero divergencias."""
    loja = loja_factory()
    modelo = _criar_modelo()
    chassi_x = _chassi('XOK')

    nf = _criar_nf_local(loja, modelo, [chassi_x])
    rec = recebimento_service.iniciar_recebimento(
        nf_id=nf.id, loja_id=loja.id, operador='tester',
    )
    recebimento_service.definir_qtd_declarada(
        recebimento_id=rec.id, qtd=1, usuario='tester',
    )
    _conferir_chassi_e_finalizar(rec, modelo, chassi_x)
    rec = recebimento_service.finalizar_recebimento(
        recebimento_id=rec.id, operador='tester',
    )
    assert rec.status == 'CONCLUIDO'

    m = recebimento_service.metricas_recebimento(rec)
    assert m['qtd_nf'] == 1
    assert m['qtd_recebidas'] == 1
    assert m['qtd_divergencias'] == 0
    assert m['qtd_faltando'] == 0
    assert m['qtd_extra'] == 0
    assert m['qtd_ok'] == 1


def test_reprocessamento_idempotente(db, loja_factory):
    """Chamar reprocessar 2x deve produzir o mesmo resultado (idempotente)."""
    loja = loja_factory()
    modelo = _criar_modelo()
    chassi_x = _chassi('XIDM')
    chassi_y = _chassi('YIDM')

    rec, nf = _setup_cenario_usuario(loja, modelo, chassi_x, chassi_y)

    nf_item = nf.itens[0]
    nf_entrada_service.editar_nf_item_manual(
        nf_id=nf.id, nf_item_id=nf_item.id,
        numero_chassi=chassi_y, operador='tester',
    )

    # Chama o reprocessamento de novo com o mesmo par antigo->novo.
    # Como o chassi ja foi alterado, agora a conferencia batch X ja sumiu
    # -> deve ser no-op (sem mudancas).
    res = recebimento_service.reprocessar_recebimentos_para_nf(
        nf_id=nf.id, chassi_antigo=chassi_x, chassi_novo=chassi_y,
        operador='tester',
    )
    assert res['confs_batch_removidas'] == 0

    rec_atual = HoraRecebimento.query.get(rec.id)
    assert rec_atual.status == 'CONCLUIDO'
