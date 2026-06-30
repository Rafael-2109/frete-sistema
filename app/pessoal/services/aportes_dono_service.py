"""Aportes do dono (Rafael) por conta de destino (Caso 2).

Regra de negocio (assimetria por conta):
  - Deposito do dono na conta-mae Bradesco -> RECEBIMENTO (Salario, visivel)
  - Deposito do dono na NuConta Nubank      -> TRANSFERENCIA entre contas (excluido)

O dono e identificado por "RAFAEL DE CARVALHO" ou "RAFAEL NASCIMENTO" (a prova de
homonimos: PERRELLA / GUSTAVO FERREIRA / AFERREIRA nao casam).

- seed_regras_dono(): desativa a regra generica do dono (sem conta) e cria 4 regras
  conta-especificas (2 padroes x 2 contas), idempotente.
- reprocessar_dono(): re-roda o motor nas entradas ja importadas do dono e aplica.

Parametros injetaveis (IDs/padroes) para teste; em producao resolvem por criterio.
"""
import logging

from sqlalchemy import or_

from app import db
from app.pessoal.models import (
    PessoalConta, PessoalCategoria, PessoalRegraCategorizacao, PessoalTransacao,
)
from app.pessoal.services.aprendizado_service import normalizar_padrao
from app.pessoal.services.categorizacao_service import categorizar_transacao
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

PADROES_DONO = ["RAFAEL DE CARVALHO", "RAFAEL NASCIMENTO"]


def _resolver():
    bradesco = PessoalConta.query.filter(
        PessoalConta.banco.ilike('bradesco'), PessoalConta.tipo == 'conta_corrente'
    ).order_by(PessoalConta.id).first()
    nubank = PessoalConta.query.filter(
        PessoalConta.banco.ilike('nubank'), PessoalConta.tipo == 'conta_corrente'
    ).order_by(PessoalConta.id).first()
    cat_sal = PessoalCategoria.query.filter(
        PessoalCategoria.grupo == 'Receitas', PessoalCategoria.nome.ilike('%salario%')
    ).first()
    cat_transf = PessoalCategoria.query.filter(
        PessoalCategoria.grupo == 'Desconsiderar', PessoalCategoria.nome.ilike('%transfer%')
    ).first()
    return bradesco, nubank, cat_sal, cat_transf


def _get_or_create_regra(padrao_norm, conta_id, categoria_id):
    """Idempotente: regra PADRAO com este padrao restrita a esta conta."""
    candidatas = PessoalRegraCategorizacao.query.filter_by(
        padrao_historico=padrao_norm, tipo_regra='PADRAO'
    ).all()
    for r in candidatas:
        if r.get_contas_ids() == [conta_id]:
            r.categoria_id = categoria_id
            r.ativo = True
            r.atualizado_em = agora_utc_naive()
            return r, False
    nova = PessoalRegraCategorizacao(
        padrao_historico=padrao_norm, tipo_regra='PADRAO', categoria_id=categoria_id,
        origem='manual', ativo=True, confianca=100,
    )
    nova.set_contas_ids([conta_id])
    db.session.add(nova)
    return nova, True


def seed_regras_dono(bradesco_cc_id=None, nubank_cc_id=None,
                     cat_salario_id=None, cat_transf_id=None,
                     padroes=None, commit=True) -> dict:
    """Desativa a regra generica do dono e cria as 4 regras conta-especificas."""
    padroes = padroes or PADROES_DONO
    if None in (bradesco_cc_id, nubank_cc_id, cat_salario_id, cat_transf_id):
        bradesco, nubank, cat_sal, cat_transf = _resolver()
        bradesco_cc_id = bradesco_cc_id or (bradesco.id if bradesco else None)
        nubank_cc_id = nubank_cc_id or (nubank.id if nubank else None)
        cat_salario_id = cat_salario_id or (cat_sal.id if cat_sal else None)
        cat_transf_id = cat_transf_id or (cat_transf.id if cat_transf else None)
    faltando = [n for n, v in [
        ('bradesco_cc', bradesco_cc_id), ('nubank_cc', nubank_cc_id),
        ('cat_salario', cat_salario_id), ('cat_transf', cat_transf_id),
    ] if v is None]
    if faltando:
        raise RuntimeError(f"Nao resolvi: {', '.join(faltando)}")

    padroes_norm = [normalizar_padrao(p) for p in padroes]

    # 1. Desativar genericas do dono (sem conta) que competiriam pelo length
    desativadas = []
    todas = PessoalRegraCategorizacao.query.filter_by(tipo_regra='PADRAO', ativo=True).all()
    for r in todas:
        if r.get_contas_ids():
            continue  # ja conta-especifica (inclui as minhas)
        ph = (r.padrao_historico or '').upper()
        if any(p in ph for p in padroes_norm):
            r.ativo = False
            r.atualizado_em = agora_utc_naive()
            desativadas.append(r.id)

    # 2. Criar/atualizar as regras conta-especificas
    criadas, atualizadas = [], []
    plano = [(bradesco_cc_id, cat_salario_id), (nubank_cc_id, cat_transf_id)]
    for conta_id, categoria_id in plano:
        for pn in padroes_norm:
            _, nova = _get_or_create_regra(pn, conta_id, categoria_id)
            (criadas if nova else atualizadas).append((pn, conta_id))

    if commit:
        db.session.commit()
    else:
        db.session.flush()
    logger.info('seed_regras_dono: %d desativadas, %d criadas, %d atualizadas',
                len(desativadas), len(criadas), len(atualizadas))
    return {
        'desativadas': desativadas, 'criadas': criadas, 'atualizadas': atualizadas,
        'bradesco_cc_id': bradesco_cc_id, 'nubank_cc_id': nubank_cc_id,
        'cat_salario_id': cat_salario_id, 'cat_transf_id': cat_transf_id,
    }


def reprocessar_dono(conta_ids=None, padroes=None, commit=True) -> dict:
    """Re-roda o motor nas entradas (credito) ja importadas do dono e aplica o resultado."""
    padroes = padroes or PADROES_DONO
    if conta_ids is None:
        bradesco, nubank, _, _ = _resolver()
        conta_ids = [c.id for c in (bradesco, nubank) if c]
    if not conta_ids:
        return {'reprocessadas': 0, 'total': 0}

    like_clauses = [
        db.func.upper(
            db.func.coalesce(PessoalTransacao.historico_completo, PessoalTransacao.historico)
        ).like(f'%{normalizar_padrao(p)}%') for p in padroes
    ]
    candidatas = PessoalTransacao.query.filter(
        PessoalTransacao.conta_id.in_(conta_ids),
        PessoalTransacao.tipo == 'credito',
        or_(*like_clauses),
    ).all()

    reprocessadas = 0
    for t in candidatas:
        res = categorizar_transacao(t)
        if res.status != 'CATEGORIZADO' or not res.categoria_id:
            continue
        t.categoria_id = res.categoria_id
        t.regra_id = res.regra_id
        t.categorizacao_auto = True
        t.categorizacao_confianca = res.categorizacao_confianca
        t.excluir_relatorio = res.excluir_relatorio
        t.eh_transferencia_propria = res.eh_transferencia_propria
        t.status = 'CATEGORIZADO'
        t.categorizado_em = agora_utc_naive()
        t.categorizado_por = 'sistema (reprocessamento dono)'
        reprocessadas += 1

    if commit:
        db.session.commit()
    logger.info('reprocessar_dono: %d/%d entradas reprocessadas', reprocessadas, len(candidatas))
    return {'reprocessadas': reprocessadas, 'total': len(candidatas)}
