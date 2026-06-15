"""Testes de ajustes de comissao CarVia (debito/credito) + helpers flush-only.

Os metodos NOVOS do service sao flush-only (compativel com o fixture `db` em
savepoint). `criar_fechamento`/`excluir_cte`/`marcar_pago`/`vincular_vendedor`
comitam (legado) — usam sufixos unicos para serem re-executaveis no banco dev.
"""
import uuid
from datetime import date
from decimal import Decimal

import pytest


def _sfx():
    return uuid.uuid4().hex[:6]


def _chave44(prefixo='3525'):
    return (prefixo + uuid.uuid4().hex).ljust(44, '0')[:44]


def _criar_usuario(db, *, email=None, nome='Jessica Tereza'):
    from app.auth.models import Usuario
    u = Usuario(
        nome=nome,
        email=email or f'vend_{_sfx()}@ex.com',
        senha_hash='x',
        perfil='vendedor',
        status='ativo',
        sistema_carvia=True,
        acesso_comissao_carvia=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _criar_op(db, *, cte_valor='1000.00', status='RASCUNHO', emissao=date(2026, 4, 1)):
    from app.carvia.models import CarviaOperacao
    op = CarviaOperacao(
        cte_numero=f'CTe-{_sfx()}',
        cte_chave_acesso=_chave44(),
        cte_valor=Decimal(cte_valor),
        cte_data_emissao=emissao,
        cnpj_cliente='12345678000100', nome_cliente='Cliente',
        uf_origem='SP', cidade_origem='SP',
        uf_destino='RJ', cidade_destino='RJ',
        status=status, tipo_entrada='IMPORTADO', criado_por='test',
    )
    db.session.add(op)
    db.session.flush()
    return op


def _criar_fechamento(db, usuario, ops, *, percentual=Decimal('0.05'), status='PENDENTE'):
    """Cria fechamento + junctions com snapshots, flush-only (sem service)."""
    from app.carvia.models.comissao import (
        CarviaComissaoFechamento, CarviaComissaoFechamentoCte,
    )
    f = CarviaComissaoFechamento(
        numero_fechamento=f'COM-{_sfx()}',
        vendedor_usuario_id=usuario.id,
        vendedor_nome=usuario.nome, vendedor_email=usuario.email,
        data_inicio=date(2026, 4, 1), data_fim=date(2026, 4, 30),
        percentual=percentual, status=status, criado_por='test',
    )
    db.session.add(f)
    db.session.flush()
    for op in ops:
        valor = Decimal(str(op.cte_valor))
        db.session.add(CarviaComissaoFechamentoCte(
            fechamento_id=f.id, operacao_id=op.id,
            cte_numero=op.cte_numero, cte_data_emissao=op.cte_data_emissao,
            valor_cte_snapshot=valor, percentual_snapshot=percentual,
            valor_comissao=(valor * percentual).quantize(Decimal('0.01')),
            incluido_por='test',
        ))
    db.session.flush()
    f.recalcular_totais()
    return f


# --------------------------------------------------------------------------
# Task 1 — model smoke
# --------------------------------------------------------------------------

def test_model_ajuste_smoke(db):
    from app.carvia.models import CarviaComissaoAjuste  # noqa: F401
    u = _criar_usuario(db)
    op = _criar_op(db)
    f = _criar_fechamento(db, u, [op])
    aj = CarviaComissaoAjuste(
        operacao_id=op.id, fechamento_origem_id=f.id,
        vendedor_usuario_id=u.id, vendedor_nome=u.nome, vendedor_email=u.email,
        motivo='ALTERACAO_VALOR', cte_numero=op.cte_numero,
        valor_cte_anterior=Decimal('1000.00'), valor_cte_novo=Decimal('1200.00'),
        percentual_snapshot=Decimal('0.05'), delta_comissao=Decimal('10.00'),
        criado_por='test',
    )
    db.session.add(aj)
    db.session.flush()
    assert aj.id is not None
    assert aj.status == 'PENDENTE'


# --------------------------------------------------------------------------
# Task 2 — recalcular_totais inclui ajustes aplicados
# --------------------------------------------------------------------------

def test_recalcular_totais_inclui_ajustes_aplicados(db):
    from app.carvia.models.comissao import CarviaComissaoAjuste
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    f = _criar_fechamento(db, u, [op])  # comissao CTes = 50.00 (5%)
    assert f.total_comissao == Decimal('50.00')

    db.session.add(CarviaComissaoAjuste(
        operacao_id=op.id, fechamento_origem_id=f.id, fechamento_aplicado_id=f.id,
        vendedor_usuario_id=u.id, vendedor_nome=u.nome, vendedor_email=u.email,
        motivo='ALTERACAO_VALOR', cte_numero=op.cte_numero,
        valor_cte_anterior=Decimal('1000.00'), valor_cte_novo=Decimal('1200.00'),
        percentual_snapshot=Decimal('0.05'), delta_comissao=Decimal('10.00'),
        status='APLICADO', criado_por='test',
    ))
    db.session.flush()
    f.recalcular_totais()
    assert f.total_ajustes == Decimal('10.00')
    assert f.total_comissao == Decimal('60.00')


# --------------------------------------------------------------------------
# Task 3 — sincronizar_ajustes_cte
# --------------------------------------------------------------------------

def test_sincronizar_gera_credito_quando_valor_sobe(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    _criar_fechamento(db, u, [op])
    op.cte_valor = Decimal('1200.00')
    db.session.flush()
    criados = ComissaoService.sincronizar_ajustes_cte(op.id, Decimal('1200.00'), 'ALTERACAO_VALOR', 'test')
    assert len(criados) == 1
    assert criados[0].delta_comissao == Decimal('10.00')
    assert criados[0].motivo == 'ALTERACAO_VALOR'
    assert criados[0].vendedor_usuario_id == u.id


def test_sincronizar_gera_debito_no_cancelamento(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    _criar_fechamento(db, u, [op])
    criados = ComissaoService.sincronizar_ajustes_cte(op.id, 0, 'CANCELAMENTO_CTE', 'test')
    assert len(criados) == 1
    assert criados[0].delta_comissao == Decimal('-50.00')


def test_sincronizar_base_corrente_em_multiplas_alteracoes(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    _criar_fechamento(db, u, [op])
    ComissaoService.sincronizar_ajustes_cte(op.id, Decimal('1200.00'), 'ALTERACAO_VALOR', 'test')
    criados2 = ComissaoService.sincronizar_ajustes_cte(op.id, Decimal('900.00'), 'ALTERACAO_VALOR', 'test')
    assert criados2[0].valor_cte_anterior == Decimal('1200.00')
    assert criados2[0].delta_comissao == Decimal('-15.00')


def test_sincronizar_delta_zero_nao_cria(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    _criar_fechamento(db, u, [op])
    criados = ComissaoService.sincronizar_ajustes_cte(op.id, Decimal('1000.00'), 'ALTERACAO_VALOR', 'test')
    assert criados == []


def test_sincronizar_ignora_fechamento_cancelado(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    _criar_fechamento(db, u, [op], status='CANCELADO')
    criados = ComissaoService.sincronizar_ajustes_cte(op.id, Decimal('1200.00'), 'ALTERACAO_VALOR', 'test')
    assert criados == []


# --------------------------------------------------------------------------
# Task 4 — _incorporar_ajustes_pendentes + guard negativo
# --------------------------------------------------------------------------

def test_incorporar_aplica_ajustes_pendentes(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    u = _criar_usuario(db)
    op_velho = _criar_op(db, cte_valor='1000.00')
    _criar_fechamento(db, u, [op_velho])
    ComissaoService.sincronizar_ajustes_cte(op_velho.id, Decimal('1200.00'), 'ALTERACAO_VALOR', 'test')

    op_novo = _criar_op(db, cte_valor='2000.00')
    f_novo = _criar_fechamento(db, u, [op_novo])  # comissao CTes = 100.00

    pendentes = ComissaoService._incorporar_ajustes_pendentes(f_novo, 'test')
    assert len(pendentes) == 1
    assert pendentes[0].status == 'APLICADO'
    assert pendentes[0].fechamento_aplicado_id == f_novo.id
    assert f_novo.total_ajustes == Decimal('10.00')
    assert f_novo.total_comissao == Decimal('110.00')


def test_incorporar_guard_total_negativo(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    u = _criar_usuario(db)
    op_velho = _criar_op(db, cte_valor='10000.00')
    _criar_fechamento(db, u, [op_velho])
    ComissaoService.sincronizar_ajustes_cte(op_velho.id, 0, 'CANCELAMENTO_CTE', 'test')  # -500

    op_novo = _criar_op(db, cte_valor='1000.00')
    f_novo = _criar_fechamento(db, u, [op_novo])  # comissao = 50; 50 - 500 < 0

    with pytest.raises(ValueError, match='excedem'):
        ComissaoService._incorporar_ajustes_pendentes(f_novo, 'test')


def test_incorporar_sem_vinculo_nao_aplica(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    f = _criar_fechamento(db, u, [op])
    f.vendedor_usuario_id = None
    db.session.flush()
    pendentes = ComissaoService._incorporar_ajustes_pendentes(f, 'test')
    assert pendentes == []


# --------------------------------------------------------------------------
# Task 5 — _montar_fechamento (flush-only)
# --------------------------------------------------------------------------

def test_montar_fechamento_resolve_vendedor_e_incorpora(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    u = _criar_usuario(db, nome='Jessica Tereza')
    op_velho = _criar_op(db, cte_valor='1000.00')
    _criar_fechamento(db, u, [op_velho])
    ComissaoService.sincronizar_ajustes_cte(op_velho.id, Decimal('1200.00'), 'ALTERACAO_VALOR', 'test')  # +10

    op_novo = _criar_op(db, cte_valor='2000.00', emissao=date(2026, 5, 10))
    f = ComissaoService._montar_fechamento(
        vendedor_usuario_id=u.id, data_fim=date(2026, 5, 31),
        operacao_ids=[op_novo.id], criado_por='admin@ex.com',
        percentual=Decimal('0.05'), observacoes=None,
    )
    assert f.vendedor_usuario_id == u.id
    assert f.vendedor_nome == 'Jessica Tereza'
    assert f.data_inicio == date(2026, 5, 10)
    assert f.total_comissao == Decimal('110.00')
    assert f.total_ajustes == Decimal('10.00')


# --------------------------------------------------------------------------
# Task 6 — buscar_ctes_elegiveis por data de corte
# --------------------------------------------------------------------------

def test_buscar_elegiveis_so_data_fim(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    op_dentro = _criar_op(db, cte_valor='100.00', status='CONFIRMADO', emissao=date(2026, 3, 1))
    op_fora = _criar_op(db, cte_valor='100.00', status='CONFIRMADO', emissao=date(2026, 6, 1))
    ids = {o.id for o in ComissaoService.buscar_ctes_elegiveis(date(2026, 4, 30))}
    assert op_dentro.id in ids
    assert op_fora.id not in ids


# --------------------------------------------------------------------------
# Task 7 — excluir_cte cancela ajustes (comita — sufixos unicos)
# --------------------------------------------------------------------------

def test_excluir_cte_cancela_ajustes_pendentes_da_junction(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    from app.carvia.models.comissao import CarviaComissaoAjuste
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    f = _criar_fechamento(db, u, [op])
    ComissaoService.sincronizar_ajustes_cte(op.id, Decimal('1200.00'), 'ALTERACAO_VALOR', 'test')
    ComissaoService.excluir_cte(f.id, op.id, 'test')
    ajustes = CarviaComissaoAjuste.query.filter_by(
        fechamento_origem_id=f.id, operacao_id=op.id,
    ).all()
    assert ajustes and all(a.status == 'CANCELADO' for a in ajustes)


# --------------------------------------------------------------------------
# Task 8 — contrato do hook de cancelamento
# --------------------------------------------------------------------------

def test_hook_cancelamento_gera_debito_via_sincronizar(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    from app.carvia.models.comissao import CarviaComissaoAjuste
    u = _criar_usuario(db)
    op = _criar_op(db, cte_valor='1000.00')
    _criar_fechamento(db, u, [op])
    op.status = 'CANCELADO'
    db.session.flush()
    ComissaoService.sincronizar_ajustes_cte(op.id, 0, 'CANCELAMENTO_CTE', 'test')
    debitos = CarviaComissaoAjuste.query.filter_by(operacao_id=op.id, motivo='CANCELAMENTO_CTE').all()
    assert len(debitos) == 1 and debitos[0].delta_comissao == Decimal('-50.00')


# --------------------------------------------------------------------------
# vincular_vendedor (usado por editar_comissao + resolucao manual)
# --------------------------------------------------------------------------

def test_vincular_vendedor_atualiza_snapshot_e_ajustes_orfaos(db):
    from app.carvia.services.financeiro.comissao_service import ComissaoService
    from app.carvia.models.comissao import (
        CarviaComissaoFechamento, CarviaComissaoAjuste,
    )
    u = _criar_usuario(db, nome='Jessica Tereza')
    op = _criar_op(db, cte_valor='1000.00')
    # fechamento SEM vinculo + 1 ajuste orfao (vendedor_usuario_id NULL)
    f = CarviaComissaoFechamento(
        numero_fechamento=f'COM-{_sfx()}',
        vendedor_usuario_id=None, vendedor_nome='Antigo', vendedor_email=None,
        data_inicio=date(2026, 4, 1), data_fim=date(2026, 4, 30),
        percentual=Decimal('0.05'), status='PENDENTE', criado_por='test',
    )
    db.session.add(f)
    db.session.flush()
    aj = CarviaComissaoAjuste(
        operacao_id=op.id, fechamento_origem_id=f.id, vendedor_usuario_id=None,
        vendedor_nome='Antigo', motivo='ALTERACAO_VALOR', cte_numero=op.cte_numero,
        valor_cte_anterior=Decimal('1000.00'), valor_cte_novo=Decimal('1100.00'),
        percentual_snapshot=Decimal('0.05'), delta_comissao=Decimal('5.00'),
        status='PENDENTE', criado_por='test',
    )
    db.session.add(aj)
    db.session.flush()

    ComissaoService.vincular_vendedor(f.id, u.id, 'admin@ex.com')

    assert f.vendedor_usuario_id == u.id
    assert f.vendedor_nome == 'Jessica Tereza'   # snapshot ressincronizado
    assert f.vendedor_email == u.email
    db.session.refresh(aj)
    assert aj.vendedor_usuario_id == u.id         # ajuste orfao herdou o vinculo
