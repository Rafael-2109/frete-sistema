"""Tests do casamento de transferencias entre contas proprias."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app import db as _db
from app.pessoal.models import PessoalConta, PessoalImportacao, PessoalTransacao
from app.pessoal.services import transferencia_service as svc


def _conta(ctx, membro, nome, numero):
    c = PessoalConta(
        nome=f'{nome} {uuid4().hex[:6]}', tipo='conta_corrente', banco='teste',
        numero_conta=numero, membro_id=membro.id, ativa=True,
    )
    _db.session.add(c)
    _db.session.commit()
    ctx['contas'].append(c.id)
    return c


def _imp(ctx, conta):
    imp = PessoalImportacao(
        conta_id=conta.id, nome_arquivo=f'{uuid4().hex[:6]}.ofx',
        tipo_arquivo='extrato_cc', total_linhas=0, linhas_importadas=0, status='IMPORTADO',
    )
    _db.session.add(imp)
    _db.session.commit()
    ctx['importacoes'].append(imp.id)
    return imp


def _tx(ctx, imp, conta, **kw):
    defaults = dict(
        importacao_id=imp.id, conta_id=conta.id, data=date(2025, 8, 1),
        historico='X', historico_completo='X', valor=Decimal('100.00'),
        tipo='debito', status='PENDENTE', excluir_relatorio=False,
        hash_transacao=f'h{uuid4().hex[:16]}',
    )
    defaults.update(kw)
    t = PessoalTransacao(**defaults)
    _db.session.add(t)
    _db.session.commit()
    ctx['transacoes'].append(t.id)
    return t


@pytest.fixture
def cenario(pessoal_ctx, membro):
    """Bradesco CC (128948-9) + NuConta + um deposito Bradesco->NuConta (2 pontas)."""
    bradesco = _conta(pessoal_ctx, membro, 'Bradesco CC', '128948-9')
    nuconta = _conta(pessoal_ctx, membro, 'NuConta', '63685323-8')
    imp_b = _imp(pessoal_ctx, bradesco)
    imp_n = _imp(pessoal_ctx, nuconta)

    # Data futura + valor incomum: isola o cenario de dados residuais do banco dev.
    debito = _tx(
        pessoal_ctx, imp_b, bradesco, tipo='debito', valor=Decimal('3333.77'),
        data=date(2099, 8, 1), historico='PIX ENVIADO NUBANK',
        historico_completo='PIX ENVIADO NUBANK',
    )
    credito = _tx(
        pessoal_ctx, imp_n, nuconta, tipo='credito', valor=Decimal('3333.77'),
        data=date(2099, 8, 1),
        historico='Transferencia recebida pelo Pix - BCO BRADESCO Conta: 128948-9',
        historico_completo='TRANSFERENCIA RECEBIDA PELO PIX - BCO BRADESCO CONTA: 128948-9',
    )
    return {'bradesco': bradesco, 'nuconta': nuconta, 'debito': debito, 'credito': credito}


_JANELA = dict(janela_dias=5, data_inicio=date(2099, 8, 1), data_fim=date(2099, 8, 1))


def test_sugerir_pares_encontra_deposito(cenario):
    sugs = svc.sugerir_pares(**_JANELA)
    par = next(
        (s for s in sugs
         if s['debito']['id'] == cenario['debito'].id
         and s['credito']['id'] == cenario['credito'].id),
        None,
    )
    assert par is not None
    assert par['valor'] == 3333.77
    assert par['memo_cruzado'] is True  # credito cita a conta Bradesco


def test_sugerir_pares_ignora_valor_diferente(cenario):
    cenario['credito'].valor = Decimal('2222.11')
    _db.session.commit()
    sugs = svc.sugerir_pares(**_JANELA)
    casou = any(
        s['debito']['id'] == cenario['debito'].id
        and s['credito']['id'] == cenario['credito'].id
        for s in sugs
    )
    assert casou is False


def test_vincular_marca_ambas_pontas(cenario):
    svc.vincular(cenario['debito'].id, cenario['credito'].id)
    d = _db.session.get(PessoalTransacao, cenario['debito'].id)
    c = _db.session.get(PessoalTransacao, cenario['credito'].id)
    assert d.transferencia_par_id == c.id
    assert c.transferencia_par_id == d.id
    assert d.eh_transferencia_propria and c.eh_transferencia_propria
    assert d.excluir_relatorio and c.excluir_relatorio


def test_vincular_rejeita_mesma_conta_ou_ja_pareado(cenario):
    svc.vincular(cenario['debito'].id, cenario['credito'].id)
    with pytest.raises(ValueError):
        svc.vincular(cenario['debito'].id, cenario['credito'].id)


def test_desvincular_reverte(cenario):
    svc.vincular(cenario['debito'].id, cenario['credito'].id)
    svc.desvincular(cenario['debito'].id)
    d = _db.session.get(PessoalTransacao, cenario['debito'].id)
    c = _db.session.get(PessoalTransacao, cenario['credito'].id)
    assert d.transferencia_par_id is None
    assert c.transferencia_par_id is None
    assert d.eh_transferencia_propria is False
    assert d.excluir_relatorio is False  # sem outro motivo de exclusao


def test_delete_de_uma_ponta_limpa_flags_do_sobrevivente(cenario):
    """Bug 1: deletar uma ponta deve limpar eh_transferencia_propria/excluir_relatorio
    do par sobrevivente (FK SET NULL so zera transferencia_par_id)."""
    svc.vincular(cenario['debito'].id, cenario['credito'].id)
    deb_id = cenario['debito'].id
    cred = _db.session.get(PessoalTransacao, cenario['credito'].id)
    _db.session.delete(cred)
    _db.session.commit()

    deb = _db.session.get(PessoalTransacao, deb_id)
    _db.session.refresh(deb)
    assert deb.transferencia_par_id is None
    assert deb.eh_transferencia_propria is False
    assert deb.excluir_relatorio is False  # sem outro motivo remanescente
