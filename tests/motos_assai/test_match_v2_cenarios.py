"""Testes especificos por cenario de _calcular_match v2 + ajustar_separacao_pela_nf v2.

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md §3.3 + §6 Fase 7
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase4-nf-divergencias.md Tasks 3-5

P2 fix 6 (2026-05-13): cobre gaps de cobertura por cenario:
- D5: NF ignora sep FATURADA no match
- S1=b: NF chegou antes da sep — cria sep em FATURADA
- A7: detecta CHASSI_OUTRA_LOJA antes do match
- A11: Excel v1 gerado com motivo='criada_via_nf_importada' quando sep criada via NF
- S19=b: NF parcial (chassi nao cadastrado gera CHASSI_NAO_CADASTRADO)
- A14: idempotencia — NF CANCELADA nao re-roda match
"""
import uuid
from decimal import Decimal

import pytest

from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaLoja, AssaiPedidoVendaItem,
    AssaiLoja, AssaiModelo,
    AssaiMoto, AssaiSeparacao, AssaiSeparacaoItem, AssaiNfQpa, AssaiNfQpaItem,
    AssaiDivergencia, AssaiPedidoExcel,
    PEDIDO_STATUS_ABERTO,
    SEPARACAO_STATUS_FATURADA, SEPARACAO_STATUS_FECHADA,
    NF_STATUS_BATEU, NF_STATUS_CANCELADA, NF_STATUS_NAO_RECONCILIADO,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL, EVENTO_FATURADA,
    DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA,
    DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO,
)
from app.motos_assai.services import (
    registrar_chassi, finalizar_separacao,
    criar_separacao_com_saldos,
    emitir_evento,
)
from app.motos_assai.services.separacao_service import ajustar_separacao_pela_nf
from app.motos_assai.services.parsers.nf_qpa_adapter import _calcular_match


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _criar_pedido(admin, loja, qtd=1):
    """Helper: cria pedido + PVL + item DOT."""
    modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()
    uid = _uid()
    p = AssaiPedidoVenda(
        numero=f'TST-MV2-{uid}', status=PEDIDO_STATUS_ABERTO,
        criado_por_id=admin.id,
    )
    db.session.add(p); db.session.flush()
    pvl = AssaiPedidoVendaLoja(pedido_id=p.id, loja_id=loja.id)
    db.session.add(pvl); db.session.flush()
    db.session.add(AssaiPedidoVendaItem(
        pedido_id=p.id, pedido_loja_id=pvl.id, loja_id=loja.id, modelo_id=modelo_dot.id,
        qtd_pedida=qtd, valor_unitario=Decimal('6900'),
        valor_total=Decimal('6900') * qtd,
    ))
    db.session.flush()
    return p, modelo_dot


def _criar_moto_disponivel(admin, chassi, modelo):
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin.id)
    emitir_evento(chassi, EVENTO_MONTADA, admin.id)
    emitir_evento(chassi, EVENTO_DISPONIVEL, admin.id)


def _criar_nf_e_itens(admin, loja, chave, chassis_modelo_valor):
    """Cria AssaiNfQpa + AssaiNfQpaItem sem rodar match."""
    nf = AssaiNfQpa(
        chave_44=chave,
        numero=chave[:6],
        emitente_cnpj='12345678000190',
        destinatario_cnpj='98765432000101',
        destinatario_nome=f'ASSAI LJ{loja.numero}',
        valor_total=sum(v for _, _, v in chassis_modelo_valor),
        loja_id=loja.id,
        status_match=NF_STATUS_NAO_RECONCILIADO,
        importada_por_id=admin.id,
    )
    db.session.add(nf); db.session.flush()
    for chassi, modelo, valor in chassis_modelo_valor:
        db.session.add(AssaiNfQpaItem(
            nf_id=nf.id, chassi=chassi,
            modelo_extraido=modelo, valor_extraido=valor,
        ))
    db.session.flush()
    return nf


# ─────────────────────────────────────────────────────────────────
# D5: NF ignora sep FATURADA no match (sep_alvo procura nao-FATURADA)
# ─────────────────────────────────────────────────────────────────

def test_d5_match_ignora_sep_faturada(app, admin_user):
    """D5: _calcular_match nao reutiliza sep FATURADA — sep FATURADA fica intocada,
    nova sep criada via S1=b para a NF nova."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()

        # 1. Sep_A FATURADA com chassi_a
        p1, _ = _criar_pedido(admin_user, loja, qtd=1)
        chassi_a = f'TST_D5_A_{_uid()}'
        _criar_moto_disponivel(admin_user, chassi_a, modelo_dot)
        db.session.commit()
        criar_separacao_com_saldos(
            pedido_id=p1.id, loja_id=loja.id,
            alocacoes=[{'modelo_id': modelo_dot.id, 'qtd': 1}],
            operador_id=admin_user.id,
        )
        db.session.commit()
        registrar_chassi(p1.id, loja.id, chassi_a, admin_user.id)
        sep_a = AssaiSeparacao.query.filter_by(pedido_id=p1.id, loja_id=loja.id).first()
        finalizar_separacao(sep_a.id, admin_user.id)
        sep_a.status = SEPARACAO_STATUS_FATURADA  # simula FATURADA
        db.session.commit()
        sep_a_id = sep_a.id

        # 2. NF nova com chassi_b (chassi diferente, mesma loja)
        chassi_b = f'TST_D5_B_{_uid()}'
        _criar_moto_disponivel(admin_user, chassi_b, modelo_dot)

        # Cria pedido 2 com sep ativa para chassi_b
        p2, _ = _criar_pedido(admin_user, loja, qtd=1)
        criar_separacao_com_saldos(
            pedido_id=p2.id, loja_id=loja.id,
            alocacoes=[{'modelo_id': modelo_dot.id, 'qtd': 1}],
            operador_id=admin_user.id,
        )
        db.session.commit()
        registrar_chassi(p2.id, loja.id, chassi_b, admin_user.id)
        sep_b = AssaiSeparacao.query.filter_by(pedido_id=p2.id, loja_id=loja.id).first()
        finalizar_separacao(sep_b.id, admin_user.id)
        db.session.commit()

        chave = '1' * 30 + _uid() + '0' * (44 - 30 - 8)
        chave = chave[:44]
        nf = _criar_nf_e_itens(
            admin_user, loja, chave,
            [(chassi_b, 'DOT', Decimal('6900'))],
        )
        db.session.commit()

        # Roda match — deve vincular a sep_b (FECHADA), NAO sep_a (FATURADA)
        _calcular_match(nf, admin_user.id)
        db.session.commit()

        item = AssaiNfQpaItem.query.filter_by(nf_id=nf.id).first()
        assert item.separacao_item_id is not None
        sep_item = AssaiSeparacaoItem.query.get(item.separacao_item_id)
        assert sep_item.separacao_id == sep_b.id, \
            f'Match deveria ter usado sep_b (FECHADA), nao sep_a (FATURADA). '\
            f'Usou: {sep_item.separacao_id}, esperado: {sep_b.id} (a {sep_a_id})'

        db.session.rollback()


# ─────────────────────────────────────────────────────────────────
# A7: ajustar_separacao_pela_nf detecta CHASSI_OUTRA_LOJA antes do match
# ─────────────────────────────────────────────────────────────────

def test_a7_chassi_outra_loja_detectado_antes_match(app, admin_user):
    """A7: chassi em sep ativa de OUTRA loja -> divergencia CHASSI_OUTRA_LOJA."""
    with app.app_context():
        lojas = AssaiLoja.query.limit(2).all()
        assert len(lojas) >= 2, 'Seed >= 2 lojas obrigatorio'
        loja_a, loja_b = lojas[0], lojas[1]
        modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()

        chassi = f'TST_A7_{_uid()}'
        _criar_moto_disponivel(admin_user, chassi, modelo_dot)

        # Sep ativa na loja_a com o chassi
        p_a, _ = _criar_pedido(admin_user, loja_a, qtd=1)
        criar_separacao_com_saldos(
            pedido_id=p_a.id, loja_id=loja_a.id,
            alocacoes=[{'modelo_id': modelo_dot.id, 'qtd': 1}],
            operador_id=admin_user.id,
        )
        db.session.commit()
        registrar_chassi(p_a.id, loja_a.id, chassi, admin_user.id)
        sep_a = AssaiSeparacao.query.filter_by(pedido_id=p_a.id, loja_id=loja_a.id).first()
        finalizar_separacao(sep_a.id, admin_user.id)
        db.session.commit()

        # NF na loja_b com o mesmo chassi
        chave = '2' * 30 + _uid() + '0' * (44 - 30 - 8)
        chave = chave[:44]
        nf = _criar_nf_e_itens(
            admin_user, loja_b, chave,
            [(chassi, 'DOT', Decimal('6900'))],
        )
        db.session.commit()

        # ajustar_separacao_pela_nf deve detectar CHASSI_OUTRA_LOJA
        resultado = ajustar_separacao_pela_nf(nf.id, admin_user.id)
        db.session.commit()

        assert chassi in resultado.get('chassis_outra_loja', []), \
            f'A7 deveria ter detectado CHASSI_OUTRA_LOJA. Resultado: {resultado}'

        div = AssaiDivergencia.query.filter_by(
            tipo=DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA, chassi=chassi,
        ).first()
        assert div is not None, 'Divergencia CHASSI_OUTRA_LOJA deveria ter sido criada'

        db.session.rollback()


# ─────────────────────────────────────────────────────────────────
# A11: Excel v1 com motivo='criada_via_nf_importada' quando sep nasce da NF
# ─────────────────────────────────────────────────────────────────

def test_a11_sep_criada_via_nf_gera_excel_v1(app, admin_user):
    """A11+S1=b: NF chega antes da sep -> cria sep em FATURADA + gera Excel v1
    com motivo_regeneracao='criada_via_nf_importada'.

    Cria LOJA ISOLADA com 1 unico pedido + PVL para evitar ambiguidade ao inferir
    pedido (banco compartilhado pode ter outros pedidos ABERTOS na loja default).
    """
    with app.app_context():
        modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()
        uid = _uid()

        # Loja ISOLADA so pra esse teste
        loja_iso = AssaiLoja(
            numero=int(uid[:4], 16) % 9000 + 80000,
            cnpj=f'00{uid}00{uid[:4]}',  # CNPJ unico
            nome=f'LJ-ISO-A11-{uid}',
            razao_social=f'LJ-ISO RZ {uid}',
        )
        db.session.add(loja_iso); db.session.flush()

        # Pedido unico na loja isolada
        p, _ = _criar_pedido(admin_user, loja_iso, qtd=1)
        chassi = f'TST_A11_{_uid()}'
        _criar_moto_disponivel(admin_user, chassi, modelo_dot)
        db.session.commit()

        # NF chega antes da sep
        chave = '3' * 30 + uid + '0' * (44 - 30 - 8)
        chave = chave[:44]
        nf = _criar_nf_e_itens(
            admin_user, loja_iso, chave,
            [(chassi, 'DOT', Decimal('6900'))],
        )
        db.session.commit()

        # ajustar_separacao_pela_nf agora consegue inferir o unico pedido da loja
        resultado = ajustar_separacao_pela_nf(nf.id, admin_user.id)
        db.session.commit()

        assert resultado.get('sep_criada_via_nf') is True, \
            f'sep_criada_via_nf deveria ser True. Resultado: {resultado}'
        sep_alvo_id = resultado.get('sep_alvo_id')
        assert sep_alvo_id is not None

        # Verifica Excel v1 com motivo correto (A11)
        excel = AssaiPedidoExcel.query.filter_by(
            separacao_id=sep_alvo_id, versao=1,
        ).first()
        assert excel is not None, 'Excel v1 deveria ter sido gerado'
        assert excel.motivo_regeneracao == 'criada_via_nf_importada', \
            f'Motivo esperado criada_via_nf_importada, veio: {excel.motivo_regeneracao}'

        db.session.rollback()


# ─────────────────────────────────────────────────────────────────
# S19=b + S8: NF parcial com chassi nao cadastrado gera divergencia
# ─────────────────────────────────────────────────────────────────

def test_s19_nf_parcial_chassi_nao_cadastrado_gera_divergencia(app, admin_user):
    """S19=b + S8: chassi inexistente em assai_moto -> divergencia CHASSI_NAO_CADASTRADO."""
    with app.app_context():
        loja = AssaiLoja.query.first()

        chassi_inexistente = f'TST_S19_INEX_{_uid()}'
        # NAO cria a moto — chassi nao cadastrado

        chave = '4' * 30 + _uid() + '0' * (44 - 30 - 8)
        chave = chave[:44]
        nf = _criar_nf_e_itens(
            admin_user, loja, chave,
            [(chassi_inexistente, 'DOT', Decimal('6900'))],
        )
        db.session.commit()

        _calcular_match(nf, admin_user.id)
        db.session.commit()

        # Divergencia CHASSI_NAO_CADASTRADO criada
        div = AssaiDivergencia.query.filter_by(
            tipo=DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO,
            chassi=chassi_inexistente,
        ).first()
        assert div is not None, \
            'Divergencia CHASSI_NAO_CADASTRADO deveria ter sido criada'

        db.session.rollback()


# ─────────────────────────────────────────────────────────────────
# A14: NF CANCELADA bloqueia re-execucao de _calcular_match (idempotencia)
# ─────────────────────────────────────────────────────────────────

def test_a14_nf_cancelada_nao_re_roda_match(app, admin_user):
    """A14: _calcular_match em NF CANCELADA early-return sem efeitos."""
    with app.app_context():
        loja = AssaiLoja.query.first()
        modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()

        chassi = f'TST_A14_{_uid()}'
        _criar_moto_disponivel(admin_user, chassi, modelo_dot)
        db.session.commit()

        chave = '5' * 30 + _uid() + '0' * (44 - 30 - 8)
        chave = chave[:44]
        nf = _criar_nf_e_itens(
            admin_user, loja, chave,
            [(chassi, 'DOT', Decimal('6900'))],
        )
        nf.status_match = NF_STATUS_CANCELADA
        db.session.commit()

        # status_match ANTES
        status_pre = nf.status_match

        # Roda match — deve early-return sem alterar nada
        _calcular_match(nf, admin_user.id)
        db.session.commit()

        nf_after = AssaiNfQpa.query.get(nf.id)
        assert nf_after.status_match == status_pre == NF_STATUS_CANCELADA, \
            'A14: status nao deveria mudar para NF CANCELADA'

        # Item da NF nao deveria ter separacao_item_id vinculado
        item = AssaiNfQpaItem.query.filter_by(nf_id=nf.id).first()
        assert item.separacao_item_id is None, \
            'A14: nao deveria vincular separacao_item_id em NF CANCELADA'

        db.session.rollback()
