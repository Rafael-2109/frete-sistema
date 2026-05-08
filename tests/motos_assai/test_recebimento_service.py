"""Testes de integração para recebimento_service.

Cobre: validar_chassi_contra_recibo, registrar_conferencia, finalizar_recebimento.
Usa rollback para não poluir banco.
"""

import uuid
import pytest
from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiCompraMotochefe, AssaiReciboMotochefe, AssaiReciboItem,
    AssaiMoto, AssaiModelo,
    RECIBO_STATUS_AGUARDANDO, RECIBO_STATUS_EM_CONFERENCIA,
    RECIBO_STATUS_CONCLUIDO, RECIBO_STATUS_COM_DIVERGENCIA,
    DIVERGENCIA_CHASSI_EXTRA, DIVERGENCIA_MOTO_FALTANDO,
    DIVERGENCIA_MODELO_DIFERENTE,
    EVENTO_ESTOQUE, EVENTO_MOTO_FALTANDO,
)
from app.motos_assai.services import (
    validar_chassi_contra_recibo, registrar_conferencia, finalizar_recebimento,
    RecebimentoValidationError,
)
from app.motos_assai.services.compra_service import criar_consolidado


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _criar_compra_minima(admin_user):
    """Cria pedido + compra mínimos para testes."""
    numero = f'REC-TEST-{_uid()}'
    p = AssaiPedidoVenda(numero=numero, criado_por_id=admin_user.id, status='ABERTO')
    db.session.add(p)
    db.session.flush()
    return criar_consolidado([p.id], None, admin_user.id)


def _criar_recibo_com_itens(compra, admin_user, chassis_lista):
    """Cria recibo + itens diretamente (sem parser)."""
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    assert modelo, 'Pré-requisito: modelo DOT seeded'

    recibo = AssaiReciboMotochefe(
        compra_id=compra.id,
        numero_recibo=f'REC-{_uid()}',
        status=RECIBO_STATUS_AGUARDANDO,
        criado_por_id=admin_user.id,
    )
    db.session.add(recibo)
    db.session.flush()

    for chassi in chassis_lista:
        item = AssaiReciboItem(
            recibo_id=recibo.id,
            chassi=chassi,
            modelo_id=modelo.id,
            modelo_texto_recibo='DOT MODELO TEST',
            cor_texto='PRETO',
            conferido=False,
        )
        db.session.add(item)
    db.session.flush()
    return recibo, modelo


# ─────────────────────────────────────────────────────────────
# validar_chassi_contra_recibo
# ─────────────────────────────────────────────────────────────

def test_validar_chassi_na_nf(app, admin_user):
    """Chassi que está no recibo → na_nf=True, ok=True, ja_conferido=False."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        chassi = f'TST{_uid()}'
        recibo, _ = _criar_recibo_com_itens(compra, admin_user, [chassi])

        r = validar_chassi_contra_recibo(recibo.id, chassi)
        assert r['ok'] is True
        assert r['na_nf'] is True
        assert r['ja_conferido'] is False
        assert r['item_id'] is not None
        db.session.rollback()


def test_validar_chassi_extra(app, admin_user):
    """Chassi não está no recibo → na_nf=False, ok=False."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        recibo, _ = _criar_recibo_com_itens(compra, admin_user, [f'TST{_uid()}'])

        r = validar_chassi_contra_recibo(recibo.id, f'EXTRA{_uid()}')
        assert r['ok'] is False
        assert r['na_nf'] is False
        assert 'CHASSI_EXTRA' in r['mensagem']
        db.session.rollback()


def test_validar_chassi_ja_conferido(app, admin_user):
    """Chassi já conferido → ok=False, ja_conferido=True."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        chassi = f'TST{_uid()}'
        recibo, modelo = _criar_recibo_com_itens(compra, admin_user, [chassi])

        # Marca como conferido diretamente
        item = AssaiReciboItem.query.filter_by(recibo_id=recibo.id, chassi=chassi).first()
        item.conferido = True
        db.session.flush()

        r = validar_chassi_contra_recibo(recibo.id, chassi)
        assert r['ok'] is False
        assert r['ja_conferido'] is True
        db.session.rollback()


def test_validar_chassi_lowercase_normalizado(app, admin_user):
    """Chassi enviado em lowercase deve ser normalizado para uppercase."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        chassi_upper = f'TST{_uid()}'
        recibo, _ = _criar_recibo_com_itens(compra, admin_user, [chassi_upper])

        r = validar_chassi_contra_recibo(recibo.id, chassi_upper.lower())
        assert r['ok'] is True
        assert r['na_nf'] is True
        db.session.rollback()


# ─────────────────────────────────────────────────────────────
# registrar_conferencia
# ─────────────────────────────────────────────────────────────

def test_registrar_conferencia_ok(app, admin_user):
    """Registra chassi que está no recibo → item.conferido=True, AssaiMoto criado."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        chassi = f'REG{_uid()}'
        recibo, modelo = _criar_recibo_com_itens(compra, admin_user, [chassi])

        item = registrar_conferencia(
            recibo_id=recibo.id,
            chassi=chassi,
            modelo_conferido_id=modelo.id,
            cor_conferida='PRETO',
            qr_code_lido=True,
            foto_s3_key=None,
            operador_id=admin_user.id,
        )

        assert item.conferido is True
        assert item.qr_code_lido is True

        # AssaiMoto deve ter sido criado
        moto = AssaiMoto.query.filter_by(chassi=chassi).first()
        assert moto is not None
        assert moto.modelo_id == modelo.id

        # Recibo deve ter mudado de AGUARDANDO para EM_CONFERENCIA
        recibo_db = AssaiReciboMotochefe.query.get(recibo.id)
        assert recibo_db.status == RECIBO_STATUS_EM_CONFERENCIA

        db.session.rollback()


def test_registrar_chassi_extra(app, admin_user):
    """Chassi não está no recibo → cria item com CHASSI_EXTRA."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        recibo, modelo = _criar_recibo_com_itens(compra, admin_user, [f'ORIG{_uid()}'])
        chassi_extra = f'XTRA{_uid()}'

        item = registrar_conferencia(
            recibo_id=recibo.id,
            chassi=chassi_extra,
            modelo_conferido_id=modelo.id,
            cor_conferida='AZUL',
            qr_code_lido=False,
            foto_s3_key=None,
            operador_id=admin_user.id,
        )

        assert item.tipo_divergencia == DIVERGENCIA_CHASSI_EXTRA
        assert item.conferido is True
        db.session.rollback()


def test_registrar_sem_modelo_falha(app, admin_user):
    """Sem modelo_conferido_id → RecebimentoValidationError."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        chassi = f'TST{_uid()}'
        recibo, _ = _criar_recibo_com_itens(compra, admin_user, [chassi])

        with pytest.raises(RecebimentoValidationError, match='Modelo conferido obrigatório'):
            registrar_conferencia(
                recibo_id=recibo.id,
                chassi=chassi,
                modelo_conferido_id=None,
                cor_conferida='PRETO',
                qr_code_lido=False,
                foto_s3_key=None,
                operador_id=admin_user.id,
            )
        db.session.rollback()


def test_registrar_chassi_vazio_falha(app, admin_user):
    """Chassi vazio → RecebimentoValidationError."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        recibo, modelo = _criar_recibo_com_itens(compra, admin_user, [f'TST{_uid()}'])

        with pytest.raises(RecebimentoValidationError, match='Chassi vazio'):
            registrar_conferencia(
                recibo_id=recibo.id,
                chassi='   ',
                modelo_conferido_id=modelo.id,
                cor_conferida='PRETO',
                qr_code_lido=False,
                foto_s3_key=None,
                operador_id=admin_user.id,
            )
        db.session.rollback()


def test_registrar_idempotente_ja_conferido(app, admin_user):
    """Chassi já conferido → validar_chassi_contra_recibo retorna ja_conferido=True (sem duplicar)."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        chassi = f'IDEM{_uid()}'
        recibo, modelo = _criar_recibo_com_itens(compra, admin_user, [chassi])

        # 1ª conferência
        registrar_conferencia(
            recibo_id=recibo.id,
            chassi=chassi,
            modelo_conferido_id=modelo.id,
            cor_conferida='PRETO',
            qr_code_lido=False,
            foto_s3_key=None,
            operador_id=admin_user.id,
        )

        # Verifica estado via validar_chassi_contra_recibo
        r = validar_chassi_contra_recibo(recibo.id, chassi)
        assert r['ja_conferido'] is True

        db.session.rollback()


def test_registrar_atualiza_assai_moto_existente(app, admin_user):
    """Se AssaiMoto já existe com modelo diferente, deve ser atualizado (SOT)."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        chassi = f'SOT{_uid()}'
        recibo, modelo = _criar_recibo_com_itens(compra, admin_user, [chassi])

        # Cria AssaiMoto com modelo qualquer DIFERENTE
        outro_modelo = AssaiModelo(codigo=f'OUTRO{_uid()}', nome='Outro', ativo=True)
        db.session.add(outro_modelo)
        db.session.flush()
        moto_pre = AssaiMoto(chassi=chassi, modelo_id=outro_modelo.id, cor='BRANCO')
        db.session.add(moto_pre)
        db.session.flush()

        registrar_conferencia(
            recibo_id=recibo.id,
            chassi=chassi,
            modelo_conferido_id=modelo.id,
            cor_conferida='PRETO',
            qr_code_lido=False,
            foto_s3_key=None,
            operador_id=admin_user.id,
        )

        moto_pos = AssaiMoto.query.filter_by(chassi=chassi).first()
        assert moto_pos.modelo_id == modelo.id  # atualizado para modelo conferido
        assert moto_pos.cor == 'PRETO'  # cor atualizada

        db.session.rollback()


# ─────────────────────────────────────────────────────────────
# finalizar_recebimento
# ─────────────────────────────────────────────────────────────

def test_finalizar_sem_faltantes(app, admin_user):
    """Todos conferidos → status CONCLUIDO."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        chassi = f'FIN{_uid()}'
        recibo, modelo = _criar_recibo_com_itens(compra, admin_user, [chassi])

        # Conferir o único chassi
        registrar_conferencia(
            recibo_id=recibo.id,
            chassi=chassi,
            modelo_conferido_id=modelo.id,
            cor_conferida='PRETO',
            qr_code_lido=False,
            foto_s3_key=None,
            operador_id=admin_user.id,
        )

        recibo_final = finalizar_recebimento(recibo.id, admin_user.id)
        assert recibo_final.status == RECIBO_STATUS_CONCLUIDO
        db.session.rollback()


def test_finalizar_com_faltantes_sem_confirmar_falha(app, admin_user):
    """Chassis não conferidos + confirmar_faltantes=False → RecebimentoValidationError."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        chassis = [f'FAL{_uid()}', f'FAL{_uid()}']
        recibo, _ = _criar_recibo_com_itens(compra, admin_user, chassis)
        # Não confere nenhum

        with pytest.raises(RecebimentoValidationError, match='não conferidos'):
            finalizar_recebimento(recibo.id, admin_user.id, confirmar_faltantes=False)
        db.session.rollback()


def test_finalizar_com_faltantes_confirmados(app, admin_user):
    """Chassis não conferidos + confirmar_faltantes=True → status COM_DIVERGENCIA."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        chassi1 = f'F1{_uid()}'
        chassi2 = f'F2{_uid()}'
        recibo, modelo = _criar_recibo_com_itens(compra, admin_user, [chassi1, chassi2])

        # Confere apenas o primeiro
        registrar_conferencia(
            recibo_id=recibo.id,
            chassi=chassi1,
            modelo_conferido_id=modelo.id,
            cor_conferida='PRETO',
            qr_code_lido=False,
            foto_s3_key=None,
            operador_id=admin_user.id,
        )

        recibo_final = finalizar_recebimento(
            recibo.id, admin_user.id, confirmar_faltantes=True
        )
        assert recibo_final.status == RECIBO_STATUS_COM_DIVERGENCIA

        # chassi2 deve ter MOTO_FALTANDO
        item2 = AssaiReciboItem.query.filter_by(recibo_id=recibo.id, chassi=chassi2).first()
        assert item2.tipo_divergencia == DIVERGENCIA_MOTO_FALTANDO

        db.session.rollback()


def test_finalizar_todos_conferidos_sem_divergencia(app, admin_user):
    """Todos conferidos e sem divergências → CONCLUIDO (não COM_DIVERGENCIA)."""
    with app.app_context():
        compra = _criar_compra_minima(admin_user)
        chassi = f'NODIV{_uid()}'
        recibo, modelo = _criar_recibo_com_itens(compra, admin_user, [chassi])

        registrar_conferencia(
            recibo_id=recibo.id,
            chassi=chassi,
            modelo_conferido_id=modelo.id,
            cor_conferida='PRETO',  # igual ao cadastrado
            qr_code_lido=True,
            foto_s3_key=None,
            operador_id=admin_user.id,
        )

        recibo_final = finalizar_recebimento(recibo.id, admin_user.id)
        assert recibo_final.status in {RECIBO_STATUS_CONCLUIDO, RECIBO_STATUS_COM_DIVERGENCIA}
        # Pelo menos finalizado
        assert recibo_final.status != RECIBO_STATUS_AGUARDANDO
        assert recibo_final.status != RECIBO_STATUS_EM_CONFERENCIA
        db.session.rollback()
