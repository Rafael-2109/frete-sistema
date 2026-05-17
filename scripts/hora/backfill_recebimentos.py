"""Backfill de recebimentos HORA + criacao de aliases NOME_NF majoritarios.

Substitui TODOS os recebimentos existentes por recebimentos automaticos gerados
a partir das NFs de entrada (chassi/modelo/cor da NF respeitando triggers
normais: eventos hora_moto_evento, divergencias, UPDATE SOT em hora_moto.cor /
modelo_id quando aplicavel).

Fluxo:
  1. Para cada texto NF que NAO resolve canonico via alias hoje, calcula o
     modelo canonico majoritario dos chassis que usam esse texto (lookup em
     hora_moto.modelo_id). Cria HoraModeloAlias(tipo=NOME_NF) se >=80% dos
     chassis convergirem no mesmo canonico.
  2. Exclui os recebimentos atuais (com verificacao de bloqueios antes).
  3. Roda `criar_recebimento_automatico_da_nf` para cada NF com loja_destino_id.

Uso:
    python scripts/hora/backfill_recebimentos.py              # dry-run
    python scripts/hora/backfill_recebimentos.py --confirmar  # executa
    python scripts/hora/backfill_recebimentos.py --apenas-novas  # so NFs sem recebimento

Idempotencia (importante para execucao via build.sh):
  Se TODOS os recebimentos existentes tiverem `operador=BACKFILL_2026_05_16`,
  o script considera que ja foi executado e nao faz nada.

Side effects esperados (PROD 2026-05-16):
  - 14 aliases NOME_NF criados (top: MOTO ELETR. X12-10, JOY SUPER MOTO CHEFE, MIA TRI MOTO CHEFE...)
  - DELETE 5 recebimentos atuais + ~56 confs + ~47 divs + ~33 audits + ~54 eventos
  - INSERT 114 recebimentos + ~739 confs + ~739 eventos RECEBIDA + auditorias
  - UPDATE em ~390 motos (cor) + ~3 motos (modelo: 1 GIGA->JET MAX + 2 JET->X12-10)
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import func  # noqa: E402

from app import create_app, db  # noqa: E402
from app.hora.models import (  # noqa: E402
    ALIAS_TIPO_NOME_NF,
    HoraModelo,
    HoraModeloAlias,
    HoraMoto,
    HoraMotoEvento,
    HoraNfEntrada,
    HoraNfEntradaItem,
    HoraRecebimento,
    HoraRecebimentoConferencia,
)
from app.hora.services.recebimento_service import (  # noqa: E402
    criar_recebimento_automatico_da_nf,
    excluir_recebimento,
    verificar_bloqueios_exclusao,
)

OPERADOR = 'BACKFILL_2026_05_16'
ALIAS_THRESHOLD = 0.80  # >=80% dos chassis precisam convergir no mesmo canonico


# ========================================================================
# Idempotencia
# ========================================================================

def ja_executado() -> bool:
    """True se todos recebimentos atuais foram criados por este script."""
    recs = HoraRecebimento.query.all()
    if not recs:
        return False  # nenhum recebimento — pode ser primeira execucao (sem nada para excluir)
    return all(r.operador == OPERADOR for r in recs)


# ========================================================================
# Fase 1 — Plano de aliases
# ========================================================================

def analisar_aliases_faltantes() -> list[dict]:
    """Para cada texto NF nao resolvido, calcula canonico majoritario.

    Retorna lista de dicts com:
      - texto_nf
      - modelo_id (canonico majoritario)
      - modelo_nome
      - total_chassis (chassis com esse texto)
      - qtd_no_canonico (chassis cujo hora_moto.modelo_id == modelo_id majoritario)
      - percent (qtd_no_canonico/total_chassis)
      - distribuicao: [(nome_modelo, qtd), ...] ordenado
      - acao: 'CRIAR' (>=THRESHOLD) ou 'PULAR' (ambiguo)
    """
    # 1. textos NF nao resolvidos hoje (sem alias E sem nome direto)
    sub_alias = db.session.query(HoraModeloAlias.nome_alias).join(
        HoraModelo, HoraModelo.id == HoraModeloAlias.modelo_id
    ).filter(HoraModelo.merged_em_id.is_(None))
    sub_nomes = db.session.query(HoraModelo.nome_modelo).filter(HoraModelo.merged_em_id.is_(None))

    textos_nao_resolvidos = [
        row[0] for row in (
            db.session.query(HoraNfEntradaItem.modelo_texto_original)
            .distinct()
            .filter(HoraNfEntradaItem.modelo_texto_original.isnot(None))
            .filter(HoraNfEntradaItem.modelo_texto_original != '')
            .filter(~func.upper(HoraNfEntradaItem.modelo_texto_original).in_(
                db.session.query(func.upper(sub_alias.subquery().c.nome_alias))
            ))
            .filter(~func.upper(HoraNfEntradaItem.modelo_texto_original).in_(
                db.session.query(func.upper(sub_nomes.subquery().c.nome_modelo))
            ))
            .all()
        )
    ]

    plano: list[dict] = []
    for texto in textos_nao_resolvidos:
        # distribuicao: canonico atual dos chassis com esse texto_nf
        rows = (
            db.session.query(HoraModelo.id, HoraModelo.nome_modelo, func.count('*'))
            .join(HoraMoto, HoraMoto.modelo_id == HoraModelo.id)
            .join(HoraNfEntradaItem, HoraNfEntradaItem.numero_chassi == HoraMoto.numero_chassi)
            .filter(HoraNfEntradaItem.modelo_texto_original == texto)
            .filter(HoraModelo.merged_em_id.is_(None))
            .group_by(HoraModelo.id, HoraModelo.nome_modelo)
            .order_by(func.count('*').desc())
            .all()
        )
        if not rows:
            continue
        total = sum(qtd for _, _, qtd in rows)
        top_id, top_nome, top_qtd = rows[0]
        percent = top_qtd / total if total else 0.0
        acao = 'CRIAR' if percent >= ALIAS_THRESHOLD else 'PULAR'
        plano.append({
            'texto_nf': texto,
            'modelo_id': top_id,
            'modelo_nome': top_nome,
            'total_chassis': total,
            'qtd_no_canonico': top_qtd,
            'percent': percent,
            'distribuicao': [(nome, qtd) for _, nome, qtd in rows],
            'acao': acao,
        })
    # ordena por qtd descrescente
    plano.sort(key=lambda d: d['total_chassis'], reverse=True)
    return plano


def imprimir_plano_aliases(plano: list[dict]) -> None:
    print(f'Aliases NOME_NF a CRIAR (threshold {int(ALIAS_THRESHOLD*100)}%):')
    if not plano:
        print('  (nenhum)')
        return
    for p in plano:
        marca = '+' if p['acao'] == 'CRIAR' else '?'
        dist_str = ', '.join(f'{n}={q}' for n, q in p['distribuicao'])
        print(
            f"  [{marca}] {p['texto_nf']!r:<55s} -> {p['modelo_nome']:<15s} "
            f"({p['qtd_no_canonico']}/{p['total_chassis']} = {p['percent']*100:.0f}%; "
            f"dist: {dist_str})"
        )
    print(f'  CRIAR={sum(1 for p in plano if p["acao"]=="CRIAR")}  PULAR={sum(1 for p in plano if p["acao"]=="PULAR")}')


def executar_criacao_aliases(plano: list[dict]) -> int:
    """Cria aliases NOME_NF. Idempotente — pula se ja existir."""
    criados = 0
    for p in plano:
        if p['acao'] != 'CRIAR':
            continue
        existe = (
            HoraModeloAlias.query
            .filter(func.upper(HoraModeloAlias.nome_alias) == p['texto_nf'].upper())
            .filter(HoraModeloAlias.tipo == ALIAS_TIPO_NOME_NF)
            .first()
        )
        if existe:
            continue
        db.session.add(HoraModeloAlias(
            modelo_id=p['modelo_id'],
            nome_alias=p['texto_nf'],
            tipo=ALIAS_TIPO_NOME_NF,
            criado_por=OPERADOR,
            observacao=(
                f"Auto-criado pelo backfill: {p['qtd_no_canonico']}/{p['total_chassis']} chassis "
                f"({p['percent']*100:.0f}%) ja apontam para {p['modelo_nome']}."
            ),
        ))
        criados += 1
    db.session.commit()
    return criados


# ========================================================================
# Fase 2 — Exclusao recebimentos
# ========================================================================

def coletar_recebimentos_existentes() -> list[HoraRecebimento]:
    return HoraRecebimento.query.order_by(HoraRecebimento.id).all()


def verificar_bloqueios(recebimentos: list[HoraRecebimento]) -> list[str]:
    bloqueios: list[str] = []
    for r in recebimentos:
        info = verificar_bloqueios_exclusao(r.id)
        if info['bloqueios']:
            bloqueios.extend(f'#{r.id}: {b}' for b in info['bloqueios'])
    return bloqueios


def executar_exclusao(recebimentos: list[HoraRecebimento]) -> dict:
    totais = {'rec_excluidos': 0, 'confs': 0, 'eventos': 0, 'divs': 0}
    for r in recebimentos:
        print(f'  excluindo #{r.id} (NF {r.nf.numero_nf})...', end=' ', flush=True)
        res = excluir_recebimento(r.id, operador=OPERADOR)
        totais['rec_excluidos'] += 1
        totais['confs'] += res['confs_deletadas']
        totais['eventos'] += res['eventos_deletados']
        totais['divs'] += res['divs_deletadas']
        print(f'OK (confs={res["confs_deletadas"]} eventos={res["eventos_deletados"]} divs={res["divs_deletadas"]})')
    return totais


# ========================================================================
# Fase 3 — Recebimentos automaticos
# ========================================================================

def coletar_nfs_alvo(apenas_sem_recebimento: bool) -> list[HoraNfEntrada]:
    q = HoraNfEntrada.query.filter(HoraNfEntrada.loja_destino_id.isnot(None))
    if apenas_sem_recebimento:
        ids_com_rec = {r.nf_id for r in HoraRecebimento.query.all()}
        if ids_com_rec:
            q = q.filter(~HoraNfEntrada.id.in_(ids_com_rec))
    return q.order_by(HoraNfEntrada.id).all()


def executar_recebimentos(nfs: list[HoraNfEntrada]) -> dict:
    totais = {
        'criados': 0,
        'concluido': 0,
        'com_divergencia': 0,
        'conferencias': 0,
        'chassis_sem_canonico': 0,
        'falhas': [],
    }
    for idx, nf in enumerate(nfs, start=1):
        print(
            f'  [{idx}/{len(nfs)}] NF {nf.numero_nf} (#{nf.id}, '
            f'loja={nf.loja_destino_id}, itens={len(nf.itens)})...',
            end=' ', flush=True,
        )
        try:
            res = criar_recebimento_automatico_da_nf(nf_id=nf.id, operador=OPERADOR)
            totais['criados'] += 1
            totais['conferencias'] += res['conferencias_criadas']
            totais['chassis_sem_canonico'] += len(res['chassis_sem_modelo_canonico'])
            if res['status_final'] == 'CONCLUIDO':
                totais['concluido'] += 1
            else:
                totais['com_divergencia'] += 1
            print(
                f'rec#{res["recebimento_id"]} status={res["status_final"]} '
                f'sem_canon={len(res["chassis_sem_modelo_canonico"])}'
            )
        except Exception as exc:  # noqa: BLE001
            totais['falhas'].append({'nf_id': nf.id, 'numero_nf': nf.numero_nf, 'erro': str(exc)})
            print(f'FALHOU: {exc}')
            db.session.rollback()
    return totais


# ========================================================================
# Resumos
# ========================================================================

def imprimir_resumo_pre(
    recebimentos: list[HoraRecebimento],
    nfs_alvo: list[HoraNfEntrada],
    plano_aliases: list[dict],
) -> None:
    print('=' * 80)
    print('BACKFILL RECEBIMENTOS HORA — RESUMO PRE-EXECUCAO')
    print('=' * 80)
    print()
    imprimir_plano_aliases(plano_aliases)
    print()
    print(f'Recebimentos a EXCLUIR: {len(recebimentos)}')
    for r in recebimentos:
        confs_total = HoraRecebimentoConferencia.query.filter_by(recebimento_id=r.id).count()
        eventos = (
            HoraMotoEvento.query
            .filter(HoraMotoEvento.origem_tabela == 'hora_recebimento_conferencia')
            .filter(
                HoraMotoEvento.origem_id.in_(
                    db.session.query(HoraRecebimentoConferencia.id).filter_by(recebimento_id=r.id)
                )
            )
            .count()
        )
        nf_num = r.nf.numero_nf if r.nf else '?'
        loja_nome = r.loja.nome if r.loja else '?'
        print(
            f'  #{r.id}  NF {nf_num}  loja={loja_nome[:30]:<30s}  '
            f'status={r.status:<18s}  confs={confs_total:<3d}  eventos={eventos}'
        )
    print()
    print(f'NFs a RECEBER AUTOMATICAMENTE: {len(nfs_alvo)}')
    if nfs_alvo:
        total_itens = sum(len(nf.itens) for nf in nfs_alvo)
        print(f'  total de itens NF: {total_itens}')
    print()


def imprimir_resumo_pos(
    aliases_criados: int,
    totais_excl: dict,
    totais_rec: dict,
    t_inicio: float,
) -> None:
    elapsed = time.time() - t_inicio
    print()
    print('=' * 80)
    print('BACKFILL — RESUMO POS-EXECUCAO')
    print('=' * 80)
    print(f'  tempo total: {elapsed:.1f}s')
    print()
    print(f'ALIASES NOME_NF criados: {aliases_criados}')
    print()
    print('EXCLUIDOS:')
    for k, v in totais_excl.items():
        print(f'  {k}: {v}')
    print()
    print('RECEBIMENTOS AUTOMATICOS:')
    print(f'  criados: {totais_rec["criados"]}')
    print(f'  CONCLUIDO: {totais_rec["concluido"]}')
    print(f'  COM_DIVERGENCIA: {totais_rec["com_divergencia"]}')
    print(f'  conferencias totais: {totais_rec["conferencias"]}')
    print(f'  chassis sem canonico (residual): {totais_rec["chassis_sem_canonico"]}')
    print(f'  falhas: {len(totais_rec["falhas"])}')
    if totais_rec['falhas']:
        for f in totais_rec['falhas']:
            print(f'    - NF {f["numero_nf"]} (#{f["nf_id"]}): {f["erro"]}')
    print()


# ========================================================================
# Main
# ========================================================================

def main():
    parser = argparse.ArgumentParser(description='Backfill recebimentos HORA')
    parser.add_argument(
        '--confirmar', action='store_true',
        help='executa de fato (sem essa flag, so dry-run)',
    )
    parser.add_argument(
        '--apenas-novas', action='store_true',
        help='nao exclui recebimentos atuais; so cria novos para NFs sem recebimento',
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        # Idempotencia: se ja rodou antes, sair sem fazer nada
        if not args.apenas_novas and ja_executado():
            print(f'BACKFILL ja executado (todos recebimentos atuais com operador={OPERADOR}).')
            print('Idempotencia ativa — nao re-executa.')
            return

        plano_aliases = analisar_aliases_faltantes()

        if args.apenas_novas:
            recebimentos_atuais: list[HoraRecebimento] = []
        else:
            recebimentos_atuais = coletar_recebimentos_existentes()
        nfs_alvo_inicial = coletar_nfs_alvo(apenas_sem_recebimento=args.apenas_novas)

        imprimir_resumo_pre(recebimentos_atuais, nfs_alvo_inicial, plano_aliases)

        bloqueios = verificar_bloqueios(recebimentos_atuais)
        if bloqueios:
            print('!! BLOQUEIOS DE EXCLUSAO DETECTADOS:')
            for b in bloqueios:
                print(f'   - {b}')
            print('!! Resolva-os antes de executar com --confirmar.')
            sys.exit(2)

        if not args.confirmar:
            print('*** DRY-RUN — nenhuma alteracao foi feita. Use --confirmar para executar. ***')
            return

        print('*** EXECUTANDO COM --confirmar ***')
        t0 = time.time()

        # Fase 1: aliases (precisa rodar antes da exclusao para que o auto-recebimento
        # ja use os aliases novos no resolver_modelo).
        print()
        print('Criando aliases NOME_NF majoritarios...')
        aliases_criados = executar_criacao_aliases(plano_aliases)
        print(f'  {aliases_criados} alias(es) criado(s).')

        # Fase 2: exclusao
        totais_excl = {'rec_excluidos': 0, 'confs': 0, 'eventos': 0, 'divs': 0}
        if recebimentos_atuais:
            print()
            print(f'Excluindo {len(recebimentos_atuais)} recebimento(s)...')
            totais_excl = executar_exclusao(recebimentos_atuais)

        # Fase 3: recebimentos automaticos. Recoletar NFs apos exclusao porque
        # o universo pode ter mudado (NFs que tinham recebimento agora estao sem).
        nfs_alvo = coletar_nfs_alvo(apenas_sem_recebimento=False)
        print()
        print(f'Criando {len(nfs_alvo)} recebimento(s) automatico(s)...')
        totais_rec = executar_recebimentos(nfs_alvo)

        imprimir_resumo_pos(aliases_criados, totais_excl, totais_rec, t0)


if __name__ == '__main__':
    main()
