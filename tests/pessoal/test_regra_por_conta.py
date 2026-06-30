"""Tests da condicao por conta de destino nas regras (Caso 2).

Uma regra pode ser restrita a uma ou mais contas (contas_ids). Isso permite duas
regras com o MESMO padrao textual e contas diferentes (ex.: "RAFAEL" no Bradesco ->
Salario; "RAFAEL" no Nubank -> Transferencia). Regra restrita (com conta) tem
prioridade sobre a generica (sem conta) quando a conta de destino bate.
"""
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app import db as _db
from app.pessoal.models import (
    PessoalConta, PessoalCategoria, PessoalImportacao,
    PessoalTransacao, PessoalRegraCategorizacao,
)
from app.pessoal.services.categorizacao_service import categorizar_transacao


def _conta(ctx, membro, nome):
    c = PessoalConta(
        nome=f'{nome} {uuid4().hex[:6]}', tipo='conta_corrente', banco='teste',
        membro_id=membro.id, ativa=True,
    )
    _db.session.add(c)
    _db.session.commit()
    ctx['contas'].append(c.id)
    return c


def _cat(ctx, nome):
    c = PessoalCategoria(nome=f'{nome}_{uuid4().hex[:6]}', grupo=f'G_{uuid4().hex[:6]}', ativa=True)
    _db.session.add(c)
    _db.session.commit()
    ctx['categorias'].append(c.id)
    return c


def _imp(ctx, conta):
    imp = PessoalImportacao(
        conta_id=conta.id, nome_arquivo=f'{uuid4().hex[:6]}.csv',
        tipo_arquivo='extrato_cc', total_linhas=0, linhas_importadas=0, status='IMPORTADO',
    )
    _db.session.add(imp)
    _db.session.commit()
    ctx['importacoes'].append(imp.id)
    return imp


def _tx(ctx, imp, conta, historico, **kw):
    defaults = dict(
        importacao_id=imp.id, conta_id=conta.id, data=date(2099, 5, 1),
        historico=historico, historico_completo=historico, valor=Decimal('500.00'),
        tipo='credito', status='PENDENTE', excluir_relatorio=False,
        hash_transacao=f'h{uuid4().hex[:16]}',
    )
    defaults.update(kw)
    t = PessoalTransacao(**defaults)
    _db.session.add(t)
    _db.session.commit()
    ctx['transacoes'].append(t.id)
    return t


@pytest.fixture
def regra_ids():
    ids = []
    yield ids
    if ids:
        # Limpar referencia regra_id nas transacoes (FK RESTRICT) antes de deletar a regra.
        _db.session.query(PessoalTransacao).filter(
            PessoalTransacao.regra_id.in_(ids)
        ).update({'regra_id': None}, synchronize_session=False)
        for rid in ids:
            _db.session.query(PessoalRegraCategorizacao).filter_by(id=rid).delete()
        _db.session.commit()


def _regra(regra_ids, padrao, categoria_id, contas_ids=None, confianca=100):
    r = PessoalRegraCategorizacao(
        padrao_historico=padrao, tipo_regra='PADRAO', categoria_id=categoria_id,
        origem='manual', ativo=True, confianca=confianca,
    )
    if contas_ids:
        r.set_contas_ids(contas_ids)
    _db.session.add(r)
    _db.session.commit()
    regra_ids.append(r.id)
    return r


def test_regra_com_conta_so_casa_na_conta_certa(pessoal_ctx, membro, regra_ids):
    bradesco = _conta(pessoal_ctx, membro, 'Bradesco')
    nubank = _conta(pessoal_ctx, membro, 'Nubank')
    cat = _cat(pessoal_ctx, 'AlvoConta')
    _regra(regra_ids, 'ZZACMECONTAXYZ', cat.id, contas_ids=[bradesco.id])

    imp_b = _imp(pessoal_ctx, bradesco)
    imp_n = _imp(pessoal_ctx, nubank)

    # Mesmo historico nas 2 contas; so a do Bradesco casa a regra restrita.
    t_b = _tx(pessoal_ctx, imp_b, bradesco, 'ZZACMECONTAXYZ DEPOSITO')
    t_n = _tx(pessoal_ctx, imp_n, nubank, 'ZZACMECONTAXYZ DEPOSITO')

    assert categorizar_transacao(t_b).categoria_id == cat.id
    assert categorizar_transacao(t_n).categoria_id != cat.id


def test_regra_especifica_vence_generica_na_conta(pessoal_ctx, membro, regra_ids):
    bradesco = _conta(pessoal_ctx, membro, 'Bradesco')
    nubank = _conta(pessoal_ctx, membro, 'Nubank')
    cat_generica = _cat(pessoal_ctx, 'Generica')
    cat_especifica = _cat(pessoal_ctx, 'Especifica')
    # Mesmo padrao textual; uma generica (qualquer conta), outra restrita ao Nubank.
    _regra(regra_ids, 'ZZPADRAOPRIOXYZ', cat_generica.id, contas_ids=None)
    _regra(regra_ids, 'ZZPADRAOPRIOXYZ', cat_especifica.id, contas_ids=[nubank.id])

    imp_b = _imp(pessoal_ctx, bradesco)
    imp_n = _imp(pessoal_ctx, nubank)

    t_n = _tx(pessoal_ctx, imp_n, nubank, 'ZZPADRAOPRIOXYZ ALGO')
    t_b = _tx(pessoal_ctx, imp_b, bradesco, 'ZZPADRAOPRIOXYZ ALGO')

    # No Nubank a especifica vence; no Bradesco (especifica nao casa) cai na generica.
    assert categorizar_transacao(t_n).categoria_id == cat_especifica.id
    assert categorizar_transacao(t_b).categoria_id == cat_generica.id


def test_regra_sem_conta_casa_qualquer_conta(pessoal_ctx, membro, regra_ids):
    """Regra sem contas_ids (NULL) continua valendo para qualquer conta (retrocompat)."""
    conta = _conta(pessoal_ctx, membro, 'Qualquer')
    cat = _cat(pessoal_ctx, 'Livre')
    _regra(regra_ids, 'ZZSEMCONTAXYZ', cat.id, contas_ids=None)
    imp = _imp(pessoal_ctx, conta)
    t = _tx(pessoal_ctx, imp, conta, 'ZZSEMCONTAXYZ COMPRA')
    assert categorizar_transacao(t).categoria_id == cat.id


def test_propagacao_regra_com_conta_so_afeta_conta_certa(pessoal_ctx, membro, regra_ids):
    """propagar_regra_para_pendentes respeita contas_ids: so categoriza a conta da regra."""
    from app.pessoal.services import aprendizado_service as aprend

    bradesco = _conta(pessoal_ctx, membro, 'Bradesco')
    nubank = _conta(pessoal_ctx, membro, 'Nubank')
    cat = _cat(pessoal_ctx, 'AlvoProp')
    regra = _regra(regra_ids, 'ZZPROPCONTAXYZ', cat.id, contas_ids=[bradesco.id])

    imp_b = _imp(pessoal_ctx, bradesco)
    imp_n = _imp(pessoal_ctx, nubank)
    t_b = _tx(pessoal_ctx, imp_b, bradesco, 'ZZPROPCONTAXYZ DEP', status='PENDENTE')
    t_n = _tx(pessoal_ctx, imp_n, nubank, 'ZZPROPCONTAXYZ DEP', status='PENDENTE')

    aprend.propagar_regra_para_pendentes(regra)
    _db.session.commit()

    assert _db.session.get(PessoalTransacao, t_b.id).categoria_id == cat.id
    assert _db.session.get(PessoalTransacao, t_n.id).categoria_id is None


def test_aprender_com_contas_diferentes_cria_regras_distintas(pessoal_ctx, membro, regra_ids):
    """_mesmo_escopo_regra inclui contas_ids: mesmo padrao + contas diferentes coexistem."""
    from app.pessoal.services import aprendizado_service as aprend

    bradesco = _conta(pessoal_ctx, membro, 'Bradesco')
    nubank = _conta(pessoal_ctx, membro, 'Nubank')
    cat_b = _cat(pessoal_ctx, 'Salario')
    cat_n = _cat(pessoal_ctx, 'Transf')
    imp_b = _imp(pessoal_ctx, bradesco)
    imp_n = _imp(pessoal_ctx, nubank)
    t_b = _tx(pessoal_ctx, imp_b, bradesco, 'ZZAPRENDEDXYZ FULANO')
    t_n = _tx(pessoal_ctx, imp_n, nubank, 'ZZAPRENDEDXYZ FULANO')

    r_b = aprend.aprender_de_categorizacao(
        t_b.id, cat_b.id, padrao_historico='ZZAPRENDEDXYZ FULANO', contas_ids=[bradesco.id])
    r_n = aprend.aprender_de_categorizacao(
        t_n.id, cat_n.id, padrao_historico='ZZAPRENDEDXYZ FULANO', contas_ids=[nubank.id])
    _db.session.commit()
    if r_b:
        regra_ids.append(r_b.id)
    if r_n:
        regra_ids.append(r_n.id)

    # Devem ser regras DISTINTAS (nao fundidas), cada uma com sua conta/categoria.
    assert r_b is not None and r_n is not None
    assert r_b.id != r_n.id
    assert r_b.get_contas_ids() == [bradesco.id]
    assert r_n.get_contas_ids() == [nubank.id]


def _cat_grupo(ctx, nome, grupo):
    c = PessoalCategoria(nome=f'{nome}_{uuid4().hex[:5]}', grupo=grupo, ativa=True)
    _db.session.add(c)
    _db.session.commit()
    ctx['categorias'].append(c.id)
    return c


def test_seed_e_reprocessamento_dono(pessoal_ctx, membro, regra_ids):
    """seed_regras_dono desativa a generica e cria as conta-especificas;
    reprocessar_dono aplica a assimetria Bradesco=Salario / Nubank=Transferencia."""
    from app.pessoal.services import aportes_dono_service as das
    from app.pessoal.services.categorizacao_service import invalidar_cache_desconsiderar
    from app.pessoal.services.aprendizado_service import normalizar_padrao

    PADRAO = 'ZZDONOTESTXYZ'
    bradesco = _conta(pessoal_ctx, membro, 'BradescoTest')
    nubank = _conta(pessoal_ctx, membro, 'NubankTest')
    cat_sal = _cat_grupo(pessoal_ctx, 'Salario', 'Receitas')
    cat_transf = _cat_grupo(pessoal_ctx, 'Transferencia', 'Desconsiderar')
    invalidar_cache_desconsiderar()

    # Generica do dono (sem conta) — competiria pelo length; deve ser desativada
    generica = _regra(regra_ids, PADRAO, cat_sal.id, contas_ids=None)

    imp_b = _imp(pessoal_ctx, bradesco)
    imp_n = _imp(pessoal_ctx, nubank)
    t_brad = _tx(pessoal_ctx, imp_b, bradesco, f'{PADRAO} DEP RAFAEL')
    t_nub = _tx(pessoal_ctx, imp_n, nubank, f'{PADRAO} DEP RAFAEL')

    seed = das.seed_regras_dono(
        bradesco_cc_id=bradesco.id, nubank_cc_id=nubank.id,
        cat_salario_id=cat_sal.id, cat_transf_id=cat_transf.id,
        padroes=[PADRAO], commit=True,
    )
    # Registrar regras conta-especificas criadas para cleanup
    for r in PessoalRegraCategorizacao.query.filter_by(
        padrao_historico=normalizar_padrao(PADRAO)
    ).all():
        if r.id not in regra_ids:
            regra_ids.append(r.id)

    das.reprocessar_dono(conta_ids=[bradesco.id, nubank.id], padroes=[PADRAO], commit=True)
    invalidar_cache_desconsiderar()

    g = _db.session.get(PessoalRegraCategorizacao, generica.id)
    t_b = _db.session.get(PessoalTransacao, t_brad.id)
    t_n = _db.session.get(PessoalTransacao, t_nub.id)

    assert generica.id in seed['desativadas']
    assert g.ativo is False
    # Bradesco -> Salario (Receita visivel)
    assert t_b.categoria_id == cat_sal.id
    assert t_b.excluir_relatorio is False
    # Nubank -> Transferencia entre contas (Desconsiderar, excluido)
    assert t_n.categoria_id == cat_transf.id
    assert t_n.excluir_relatorio is True
