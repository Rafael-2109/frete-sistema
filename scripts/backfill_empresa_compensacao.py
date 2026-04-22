"""Backfill: categoriza transacoes intra-empresa + auto-match 1x1 intra-day.

REGRAS:
1. Identifica transacoes em CC cuja contraparte eh empresa do grupo
   (La Famiglia, AANP, Sogima, NG Promo, Parnaplast, Nacom Goya).
2. Atribui categoria 'Empresa - Entrada' (credito) ou 'Empresa - Saida' (debito)
   do grupo 'Movimentacoes Empresa'. Reset excluir_relatorio=False (estava marcada
   pela heuristica legada EXCLUSOES_EMPRESA).
3. Compensa AUTOMATICAMENTE apenas dias com EXATAMENTE 1 entrada + 1 saida empresa
   (par inequivocamente unico). Outros dias ficam para match manual.

USO:
    python scripts/backfill_empresa_compensacao.py --dry-run   # simula
    python scripts/backfill_empresa_compensacao.py             # aplica

Idempotente: se transacao ja tem categoria empresa e compensada, pula.
"""
from __future__ import annotations

import argparse
import logging
import re
from collections import defaultdict
from datetime import date

from sqlalchemy import func

from app import create_app, db
from app.pessoal.models import (
    PessoalCategoria, PessoalConta, PessoalTransacao,
)
from app.pessoal.services.compensacao_service import aplicar_compensacao

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('backfill_empresa')

# Empresas do grupo (padrao de match em descricao OU historico)
EMPRESAS_GRUPO = [
    'LA FAMIGLIA',
    'AANP',
    'SOGIMA',
    'NG PROMO',
    'PARNAPLAST',
    'NACOM GOYA',
]


def _norm(s: str) -> str:
    return re.sub(r'\s+', ' ', (s or '').upper().strip())


def _match_empresa(t: PessoalTransacao) -> bool:
    """Retorna True se historico/descricao contem alguma empresa do grupo."""
    haystack = ' '.join([
        _norm(t.descricao or ''),
        _norm(t.historico or ''),
        _norm(t.historico_completo or ''),
    ])
    return any(emp in haystack for emp in EMPRESAS_GRUPO)


def _buscar_categorias() -> tuple[PessoalCategoria, PessoalCategoria]:
    entrada = PessoalCategoria.query.filter_by(
        grupo='Movimentacoes Empresa', nome='Empresa - Entrada',
    ).first()
    saida = PessoalCategoria.query.filter_by(
        grupo='Movimentacoes Empresa', nome='Empresa - Saida',
    ).first()
    if not entrada or not saida:
        raise RuntimeError(
            'Categorias Movimentacoes Empresa nao encontradas. '
            'Rode antes: python scripts/migrations/pessoal_movimentacoes_empresa.py'
        )
    return entrada, saida


def passo1_categorizar(dry_run: bool) -> dict:
    """Categoriza transacoes de CC com contraparte empresa do grupo."""
    entrada_cat, saida_cat = _buscar_categorias()

    cc_ids = [r[0] for r in db.session.query(PessoalConta.id).filter(
        PessoalConta.tipo == 'conta_corrente',
    ).all()]

    txs = PessoalTransacao.query.filter(
        PessoalTransacao.conta_id.in_(cc_ids),
    ).all()

    candidatas = [t for t in txs if _match_empresa(t)]
    logger.info('Candidatas a categorizacao empresa: %d', len(candidatas))

    alterados = 0
    ja_categorizadas = 0
    for t in candidatas:
        target_cat = entrada_cat if t.tipo == 'credito' else saida_cat
        if t.categoria_id == target_cat.id:
            ja_categorizadas += 1
            continue

        if dry_run:
            logger.info(
                '[DRY] %s tx=%d data=%s valor=%.2f hist=%s -> %s (excluir_relatorio=%s -> False)',
                t.tipo, t.id, t.data, float(t.valor),
                (t.descricao or t.historico)[:40],
                target_cat.nome, t.excluir_relatorio,
            )
        else:
            t.categoria_id = target_cat.id
            t.categorizacao_auto = True
            t.status = 'CATEGORIZADO'
            # Reset excluir_relatorio para permitir compensacao funcionar
            # (vai ser True de novo quando valor_compensado >= valor)
            t.excluir_relatorio = False
        alterados += 1

    if not dry_run and alterados > 0:
        db.session.commit()
        logger.info('[OK] Categorizadas %d transacoes (+ %d ja estavam)', alterados, ja_categorizadas)
    else:
        logger.info('[DRY] Categorizaria %d (ja categorizadas: %d)', alterados, ja_categorizadas)

    return {'alterados': alterados, 'ja_categorizadas': ja_categorizadas}


def passo2_compensar_1x1(dry_run: bool) -> dict:
    """Aplica compensacao AUTOMATICA apenas para dias com exatamente 1 entrada + 1 saida."""
    entrada_cat, saida_cat = _buscar_categorias()

    # valor > COALESCE(valor_compensado, 0) — defensivo contra rows sem default
    tx_entradas = PessoalTransacao.query.filter(
        PessoalTransacao.categoria_id == entrada_cat.id,
        PessoalTransacao.tipo == 'credito',
        PessoalTransacao.valor > func.coalesce(PessoalTransacao.valor_compensado, 0),
    ).all()
    tx_saidas = PessoalTransacao.query.filter(
        PessoalTransacao.categoria_id == saida_cat.id,
        PessoalTransacao.tipo == 'debito',
        PessoalTransacao.valor > func.coalesce(PessoalTransacao.valor_compensado, 0),
    ).all()

    # Agrupa por data
    por_dia_ent: dict[date, list[PessoalTransacao]] = defaultdict(list)
    por_dia_sai: dict[date, list[PessoalTransacao]] = defaultdict(list)
    for t in tx_entradas:
        por_dia_ent[t.data].append(t)
    for t in tx_saidas:
        por_dia_sai[t.data].append(t)

    todos_dias = sorted(set(por_dia_ent.keys()) | set(por_dia_sai.keys()))

    pareados_1x1 = 0
    ambiguos = []
    orfaos = 0

    for dia in todos_dias:
        ent = por_dia_ent.get(dia, [])
        sai = por_dia_sai.get(dia, [])

        if len(ent) == 1 and len(sai) == 1:
            e = ent[0]
            s = sai[0]
            v_match = min(
                float(e.valor) - float(e.valor_compensado or 0),
                float(s.valor) - float(s.valor_compensado or 0),
            )
            if v_match <= 0.01:
                continue
            if dry_run:
                logger.info(
                    '[DRY] 1x1 dia=%s saida=%d(%.2f) <-> entrada=%d(%.2f) match=%.2f',
                    dia, s.id, float(s.valor), e.id, float(e.valor), v_match,
                )
                pareados_1x1 += 1
            else:
                # Savepoint por iteracao: se falhar, rollback parcial apenas desse par
                savepoint = db.session.begin_nested()
                try:
                    aplicar_compensacao(
                        saida_id=s.id, entrada_id=e.id, valor=v_match,
                        origem='auto', criado_por='backfill_empresa',
                        observacao=f'Auto-match 1x1 {dia}',
                        commit=False,
                    )
                    savepoint.commit()
                    pareados_1x1 += 1
                except Exception as ex:
                    logger.error('Falha em %s: %s', dia, ex)
                    savepoint.rollback()
                    continue
        elif len(ent) >= 1 and len(sai) >= 1:
            ambiguos.append({
                'data': dia.isoformat(),
                'n_entradas': len(ent),
                'n_saidas': len(sai),
                'soma_entradas': sum(float(t.valor) - float(t.valor_compensado or 0) for t in ent),
                'soma_saidas': sum(float(t.valor) - float(t.valor_compensado or 0) for t in sai),
            })
        else:
            orfaos += 1

    if not dry_run and pareados_1x1 > 0:
        db.session.commit()
        logger.info('[OK] Compensacoes 1x1 aplicadas: %d', pareados_1x1)

    logger.info('Dias 1x1 pareados: %d | Ambiguos (2+ pontas): %d | Orfaos: %d',
                pareados_1x1, len(ambiguos), orfaos)
    if ambiguos:
        logger.info('Ambiguos (para tela manual):')
        for a in ambiguos[:20]:
            logger.info('  %s: %d ent (soma %.2f) vs %d sai (soma %.2f) | diff=%.2f',
                        a['data'], a['n_entradas'], a['soma_entradas'],
                        a['n_saidas'], a['soma_saidas'],
                        a['soma_entradas'] - a['soma_saidas'])
        if len(ambiguos) > 20:
            logger.info('  ... +%d dias', len(ambiguos) - 20)

    return {'pareados_1x1': pareados_1x1, 'ambiguos': len(ambiguos), 'orfaos': orfaos}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dry-run', action='store_true', help='Simula sem aplicar')
    args = p.parse_args()

    app = create_app()
    with app.app_context():
        logger.info('=== PASSO 1: Categorizacao ===')
        r1 = passo1_categorizar(args.dry_run)

        logger.info('=== PASSO 2: Compensacao automatica 1x1 ===')
        r2 = passo2_compensar_1x1(args.dry_run)

        print('\n=== RESUMO ===')
        print(f'Categorizadas: {r1["alterados"]} (ja estavam: {r1["ja_categorizadas"]})')
        print(f'Pareamentos 1x1 aplicados: {r2["pareados_1x1"]}')
        print(f'Dias ambiguos (2+ pontas, ir para tela manual): {r2["ambiguos"]}')
        print(f'Dias orfaos (so entrada OU so saida, fica no fluxo): {r2["orfaos"]}')

        if args.dry_run:
            print('\n[DRY-RUN] Nenhuma alteracao foi persistida. Remova --dry-run para aplicar.')


if __name__ == '__main__':
    main()
