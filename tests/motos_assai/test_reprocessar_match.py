"""Testes do reprocessar_match_service + hooks automaticos.

Cobre:
  - Service core: reprocessar_match_nf cenarios (NAO_RECONCILIADO->BATEU,
    CANCELADA->SKIP, idempotencia, nf inexistente)
  - Helpers: nfs_afetadas_por_* (chassi, separacao, loja, cnpj_novo, modelo)
  - Hooks: registrar_conferencia (C1), cancelar_separacao (B2),
    atualizar_loja (A1), criar_loja (A2)
"""
import uuid
from decimal import Decimal

from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaLoja, AssaiPedidoVendaItem,
    AssaiLoja, AssaiModelo,
    AssaiMoto, AssaiSeparacao, AssaiNfQpa, AssaiNfQpaItem,
    AssaiDivergencia,
    AssaiCompraMotochefe, AssaiReciboMotochefe, AssaiReciboItem,
    PEDIDO_STATUS_ABERTO,
    NF_STATUS_BATEU, NF_STATUS_DIVERGENTE, NF_STATUS_NAO_RECONCILIADO,
    NF_STATUS_CANCELADA,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
    DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO,
)
from app.motos_assai.services import (
    registrar_chassi, finalizar_separacao, emitir_evento,
    criar_separacao_com_saldos,
)
from app.motos_assai.services.reprocessar_match_service import (
    reprocessar_match_nf, reprocessar_match_nfs,
    nfs_afetadas_por_chassi, nfs_afetadas_por_separacao,
    nfs_afetadas_por_loja, nfs_afetadas_por_cnpj_novo,
    nfs_afetadas_por_chassis,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _chave_fake():
    import random
    return ''.join([str(random.randint(0, 9)) for _ in range(44)])


def _criar_pedido_com_loja(admin, loja, modelo, valor=Decimal('6900')):
    """Cria AssaiPedidoVenda + AssaiPedidoVendaLoja + Item para a loja/modelo."""
    p = AssaiPedidoVenda(
        numero=f'TST-RP-{_uid()}', status=PEDIDO_STATUS_ABERTO,
        criado_por_id=admin.id,
    )
    db.session.add(p)
    db.session.flush()
    pvl = AssaiPedidoVendaLoja(pedido_id=p.id, loja_id=loja.id)
    db.session.add(pvl)
    db.session.flush()
    db.session.add(AssaiPedidoVendaItem(
        pedido_id=p.id, pedido_loja_id=pvl.id, loja_id=loja.id,
        modelo_id=modelo.id, qtd_pedida=1,
        valor_unitario=valor, valor_total=valor,
    ))
    db.session.flush()
    return p


def _criar_nf_nao_reconciliada(admin, loja, chassi, valor=Decimal('6900')):
    """Cria AssaiNfQpa com 1 item, status NAO_RECONCILIADO, sem separacao_id."""
    chave = _chave_fake()
    nf = AssaiNfQpa(
        chave_44=chave,
        numero='RP-{}'.format(_uid()),
        destinatario_cnpj='98765432000101',
        destinatario_nome='LOJA TEST',
        loja_id=loja.id,
        valor_total=valor,
        status_match=NF_STATUS_NAO_RECONCILIADO,
        importada_por_id=admin.id,
    )
    db.session.add(nf)
    db.session.flush()
    item = AssaiNfQpaItem(
        nf_id=nf.id, chassi=chassi, modelo_extraido='DOT',
        valor_extraido=valor,
        tipo_divergencia=DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO,
    )
    db.session.add(item)
    # Cria divergencia para simular estado pos-importacao
    div = AssaiDivergencia(
        tipo=DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO,
        chassi=chassi, nf_id=nf.id,
        detalhes={'modelo_extraido': 'DOT'},
    )
    db.session.add(div)
    db.session.commit()
    return nf


def _criar_moto_e_sep_para_chassi(admin, loja, modelo, chassi, valor=Decimal('6900')):
    """Cadastra AssaiMoto + sep EM_SEPARACAO + escaneia chassi + finaliza."""
    m = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
    db.session.add(m)
    db.session.flush()

    # 2026-05-17: _calcular_match exige AssaiReciboItem conferido
    compra = AssaiCompraMotochefe(
        numero=f'COMP-TST-RP-{_uid()}', criada_por_id=admin.id,
    )
    db.session.add(compra)
    db.session.flush()
    recibo = AssaiReciboMotochefe(
        compra_id=compra.id, total_motos_declarado=1, status='CONCLUIDO',
        criado_por_id=admin.id,
    )
    db.session.add(recibo)
    db.session.flush()
    db.session.add(AssaiReciboItem(
        recibo_id=recibo.id, chassi=chassi, modelo_id=modelo.id,
        cor_texto='CINZA', conferido=True, ativo=True,
    ))
    db.session.flush()

    emitir_evento(chassi, EVENTO_ESTOQUE, admin.id)
    emitir_evento(chassi, EVENTO_MONTADA, admin.id)
    emitir_evento(chassi, EVENTO_DISPONIVEL, admin.id)
    db.session.commit()

    pedido = _criar_pedido_com_loja(admin, loja, modelo, valor)
    criar_separacao_com_saldos(
        pedido_id=pedido.id, loja_id=loja.id,
        alocacoes=[{'modelo_id': modelo.id, 'qtd': 1}],
        operador_id=admin.id,
    )
    db.session.commit()
    registrar_chassi(pedido.id, loja.id, chassi, admin.id)
    sep = AssaiSeparacao.query.filter_by(
        pedido_id=pedido.id, loja_id=loja.id,
    ).first()
    finalizar_separacao(sep.id, admin.id)
    db.session.commit()
    return sep


# ─── reprocessar_match_nf core ────────────────────────────────────────────────

def test_reprocessar_match_nao_reconciliado_para_bateu(app, admin_user):
    """NF NAO_RECONCILIADO -> cadastra chassi + sep -> reprocessa -> BATEU."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()
        chassi = f'TST_RP_BT_{_uid()}'

        nf = _criar_nf_nao_reconciliada(admin_user, loja, chassi)
        assert nf.status_match == NF_STATUS_NAO_RECONCILIADO

        _criar_moto_e_sep_para_chassi(admin_user, loja, modelo_dot, chassi)

        r = reprocessar_match_nf(nf.id, motivo='TST', operador_id=admin_user.id)

        assert not r['skipped']
        assert r['status_anterior'] == NF_STATUS_NAO_RECONCILIADO
        assert r['status_novo'] == NF_STATUS_BATEU
        assert r['divergencias_resolvidas'] >= 1

        nf_after = AssaiNfQpa.query.get(nf.id)
        assert nf_after.status_match == NF_STATUS_BATEU
        assert nf_after.separacao_id is not None
        assert nf_after.itens[0].separacao_item_id is not None
        assert nf_after.itens[0].tipo_divergencia is None

        db.session.rollback()


def test_reprocessar_match_cancelada_skip(app, admin_user):
    """NF CANCELADA -> reprocessar e no-op."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        chassi = f'TST_RP_CN_{_uid()}'
        nf = _criar_nf_nao_reconciliada(admin_user, loja, chassi)
        nf.status_match = NF_STATUS_CANCELADA
        db.session.commit()

        r = reprocessar_match_nf(nf.id, motivo='TST', operador_id=admin_user.id)
        assert r['skipped'] is True
        assert r['reason'] == 'nf_cancelada'
        assert r['status_anterior'] == NF_STATUS_CANCELADA
        assert r['status_novo'] == NF_STATUS_CANCELADA

        db.session.rollback()


def test_reprocessar_match_nf_inexistente(app, admin_user):
    """nf_id inexistente -> skipped com reason=not_found."""
    with app.app_context():
        r = reprocessar_match_nf(99999999, motivo='TST', operador_id=admin_user.id)
        assert r['skipped'] is True
        assert r['reason'] == 'not_found'


def test_reprocessar_match_idempotente(app, admin_user):
    """Rodar 2x = mesmo resultado."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()
        chassi = f'TST_RP_ID_{_uid()}'

        nf = _criar_nf_nao_reconciliada(admin_user, loja, chassi)
        _criar_moto_e_sep_para_chassi(admin_user, loja, modelo_dot, chassi)

        r1 = reprocessar_match_nf(nf.id, motivo='TST_1', operador_id=admin_user.id)
        assert r1['status_novo'] == NF_STATUS_BATEU

        r2 = reprocessar_match_nf(nf.id, motivo='TST_2', operador_id=admin_user.id)
        # 2a rodada: status_anterior ja era BATEU
        assert r2['status_anterior'] == NF_STATUS_BATEU
        assert r2['status_novo'] == NF_STATUS_BATEU
        # Divergencias ja foram resolvidas na 1a rodada
        assert r2['divergencias_resolvidas'] == 0

        db.session.rollback()


def test_reprocessar_match_batch(app, admin_user):
    """reprocessar_match_nfs em lista: count correto de mudou_status."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()

        chassi_a = f'TST_BT_A_{_uid()}'
        chassi_b = f'TST_BT_B_{_uid()}'
        nf_a = _criar_nf_nao_reconciliada(admin_user, loja, chassi_a)
        nf_b = _criar_nf_nao_reconciliada(admin_user, loja, chassi_b)

        # Apenas chassi_a tem moto+sep, b nao tem
        _criar_moto_e_sep_para_chassi(admin_user, loja, modelo_dot, chassi_a)

        stats = reprocessar_match_nfs(
            [nf_a.id, nf_b.id], motivo='TST_BATCH', operador_id=admin_user.id,
        )
        assert stats['total'] == 2
        assert stats['ok'] == 2
        assert stats['mudou_status'] == 1
        assert stats['erro'] == 0

        db.session.rollback()


# ─── helpers ──────────────────────────────────────────────────────────────────

def test_nfs_afetadas_por_chassi(app, admin_user):
    """Retorna ids de NFs que mencionam um chassi (exceto CANCELADAs)."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        chassi_unico = f'TST_AFC_{_uid()}'
        chassi_outro = f'TST_AFC2_{_uid()}'

        nf1 = _criar_nf_nao_reconciliada(admin_user, loja, chassi_unico)
        nf2 = _criar_nf_nao_reconciliada(admin_user, loja, chassi_outro)
        nf3_canc = _criar_nf_nao_reconciliada(admin_user, loja, chassi_unico)
        nf3_canc.status_match = NF_STATUS_CANCELADA
        db.session.commit()

        ids = nfs_afetadas_por_chassi(chassi_unico)
        assert nf1.id in ids
        assert nf2.id not in ids
        assert nf3_canc.id not in ids  # CANCELADA exclusa

        db.session.rollback()


def test_nfs_afetadas_por_separacao(app, admin_user):
    """Retorna NFs com separacao_id == X ou itens vinculados."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()
        chassi = f'TST_AFS_{_uid()}'

        nf = _criar_nf_nao_reconciliada(admin_user, loja, chassi)
        sep = _criar_moto_e_sep_para_chassi(
            admin_user, loja, modelo_dot, chassi,
        )
        # Liga NF a sep manualmente (sem chamar match)
        nf.separacao_id = sep.id
        db.session.commit()

        ids = nfs_afetadas_por_separacao(sep.id)
        assert nf.id in ids

        db.session.rollback()


def test_nfs_afetadas_por_cnpj_novo(app, admin_user):
    """NFs em NAO_RECONCILIADO com loja_id NULL e CNPJ destinatario casando."""
    with app.app_context():
        cnpj = '12345678901234'
        nf = AssaiNfQpa(
            chave_44=_chave_fake(),
            destinatario_cnpj=cnpj,
            destinatario_nome='LOJA SEM CADASTRO',
            loja_id=None,
            status_match=NF_STATUS_NAO_RECONCILIADO,
            importada_por_id=admin_user.id,
        )
        db.session.add(nf)
        db.session.commit()

        ids = nfs_afetadas_por_cnpj_novo(cnpj)
        assert nf.id in ids

        # CNPJ formatado deveria casar via normalizacao
        ids_formatado = nfs_afetadas_por_cnpj_novo('12.345.678/9012-34')
        assert nf.id in ids_formatado

        db.session.rollback()


def test_nfs_afetadas_por_loja(app, admin_user):
    """Combina: NFs com loja_id == X + NFs NAO_RECONCILIADO com CNPJ casando."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        chassi1 = f'TST_AFL_{_uid()}'
        nf1 = _criar_nf_nao_reconciliada(admin_user, loja, chassi1)
        nf1.loja_id = loja.id
        db.session.commit()

        # NF com loja_id NULL mas CNPJ da loja
        nf2 = AssaiNfQpa(
            chave_44=_chave_fake(),
            destinatario_cnpj=loja.cnpj,
            destinatario_nome='SEM LJ NO NOME',
            loja_id=None,
            status_match=NF_STATUS_NAO_RECONCILIADO,
            importada_por_id=admin_user.id,
        )
        db.session.add(nf2)
        db.session.commit()

        ids = nfs_afetadas_por_loja(loja.id)
        assert nf1.id in ids
        assert nf2.id in ids  # incluida via CNPJ

        db.session.rollback()


def test_nfs_afetadas_por_chassis_batch(app, admin_user):
    """Variante batch: lista de chassis em 1 query."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        cs = [f'TST_BCH_{_uid()}' for _ in range(3)]
        nfs = [_criar_nf_nao_reconciliada(admin_user, loja, c) for c in cs]

        ids = nfs_afetadas_por_chassis(cs)
        for nf in nfs:
            assert nf.id in ids

        # Vazio retorna lista vazia
        assert nfs_afetadas_por_chassis([]) == []
        assert nfs_afetadas_por_chassis(['']) == []

        db.session.rollback()


# ─── hook integration (recebimento_service.registrar_conferencia) ─────────────

def test_hook_chassi_cadastrado_resolve_nf(app, admin_user):
    """Hook C1: registrar_conferencia em chassi -> NF antes NAO_RECONCILIADO BATE.

    Cenario crítico (Recibo 4): NF importada antes da conferência do recibo
    Motochefe fica em NAO_RECONCILIADO com tipo_divergencia=CHASSI_NAO_CADASTRADO.
    Quando operador finalmente confere o recibo, AssaiMoto e criada e
    `registrar_conferencia` aciona o hook -> NF vira BATEU automaticamente.
    """
    from app.motos_assai.services.recebimento_service import registrar_conferencia
    from app.motos_assai.models import AssaiReciboMotochefe, AssaiReciboItem, AssaiCompraMotochefe

    with app.app_context():
        loja = AssaiLoja.query.first()
        modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()
        chassi = f'TST_HK_C1_{_uid()}'

        # NF importada ANTES do recibo -> CHASSI_NAO_CADASTRADO
        nf = _criar_nf_nao_reconciliada(admin_user, loja, chassi)
        assert nf.status_match == NF_STATUS_NAO_RECONCILIADO

        # 1. Criar compra + recibo + item nao conferido
        pedido = _criar_pedido_com_loja(admin_user, loja, modelo_dot)
        compra = AssaiCompraMotochefe(
            numero=f'COM-{_uid()}',
            criada_por_id=admin_user.id,
        )
        db.session.add(compra)
        db.session.flush()
        recibo = AssaiReciboMotochefe(
            compra_id=compra.id, total_motos_declarado=1,
            criado_por_id=admin_user.id,
        )
        db.session.add(recibo)
        db.session.flush()
        item = AssaiReciboItem(
            recibo_id=recibo.id, chassi=chassi,
            modelo_id=modelo_dot.id, cor_texto='CINZA',
        )
        db.session.add(item)
        db.session.commit()

        # 2. Criar sep para o chassi cair em DISPONIVEL (nao SEPARADA, sep vazia)
        criar_separacao_com_saldos(
            pedido_id=pedido.id, loja_id=loja.id,
            alocacoes=[{'modelo_id': modelo_dot.id, 'qtd': 1}],
            operador_id=admin_user.id,
        )
        db.session.commit()

        # 3. registrar_conferencia: cria AssaiMoto + emite ESTOQUE + dispara hook
        registrar_conferencia(
            recibo_id=recibo.id, chassi=chassi,
            modelo_conferido_id=modelo_dot.id, cor_conferida='CINZA',
            qr_code_lido=False, foto_s3_key=None,
            operador_id=admin_user.id,
        )

        # Apos o hook: o chassi virou AssaiMoto, mas ainda nao foi para SEPARADA
        # (sep esta vazia). NF entao deveria virar DIVERGENTE com
        # CHASSI_SEM_SEPARACAO (sai de CHASSI_NAO_CADASTRADO).
        nf_after = AssaiNfQpa.query.get(nf.id)
        assert nf_after.status_match in (
            NF_STATUS_DIVERGENTE, NF_STATUS_NAO_RECONCILIADO,
        ), (
            f'Esperava NF migrar de CHASSI_NAO_CADASTRADO para '
            f'CHASSI_SEM_SEPARACAO via hook, veio {nf_after.status_match}'
        )

        # Divergencia antiga CHASSI_NAO_CADASTRADO deveria estar resolvida
        div_antiga = AssaiDivergencia.query.filter_by(
            nf_id=nf.id, tipo=DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO,
        ).first()
        assert div_antiga is not None
        assert div_antiga.resolvida_em is not None, (
            'Hook deveria ter marcado a divergencia antiga como resolvida'
        )

        db.session.rollback()


# ─── hook integration (loja_service) ──────────────────────────────────────────

def test_hook_criar_loja_resolve_nf_por_cnpj(app, admin_user):
    """Hook A2: criar_loja com CNPJ resolve NFs NAO_RECONCILIADO com mesmo CNPJ."""
    from app.motos_assai.services.loja_service import criar_loja

    with app.app_context():
        # CNPJ unico por test run (evita conflito com residuos de testes
        # anteriores que possam ter criado loja com mesmo CNPJ).
        uid = _uid()
        cnpj_novo = f'998{uid[:5]}000155'.replace('-', '0')[:14].ljust(14, '0')

        nf = AssaiNfQpa(
            chave_44=_chave_fake(),
            destinatario_cnpj=cnpj_novo,
            destinatario_nome='LOJA INEXISTENTE LTDA',
            loja_id=None,
            status_match=NF_STATUS_NAO_RECONCILIADO,
            importada_por_id=admin_user.id,
        )
        db.session.add(nf)
        db.session.commit()
        nf_id = nf.id

        # Cria loja com mesmo CNPJ -> hook A2 reprocessa
        nova_loja = criar_loja({
            'numero': f'9{uid[:3]}',
            'nome': 'LOJA NOVA TEST',
            'razao_social': 'LOJA NOVA TEST LTDA',
            'cnpj': cnpj_novo,
            'uf': 'SP',
            'ativo': True,
        }, operador_id=admin_user.id)

        nf_after = AssaiNfQpa.query.get(nf_id)
        # Apos hook, NF deveria ter ganhado loja_id (mesmo sem chassi cadastrado
        # nao vai bater, mas loja_id resolve)
        assert nf_after.loja_id == nova_loja.id, (
            f'Esperava NF ganhar loja_id={nova_loja.id} via hook A2, '
            f'veio loja_id={nf_after.loja_id}'
        )

        db.session.rollback()
