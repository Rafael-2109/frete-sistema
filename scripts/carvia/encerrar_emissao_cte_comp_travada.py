#!/usr/bin/env python3
"""Encerra uma emissao de CTe Complementar travada em EM_PROCESSAMENTO.

Cenario (2026-06-22): o job RQ `emitir_cte_complementar_job` roda na fila
'high' (worker sistema-fretes-worker-atacadao), com job_timeout=10m. Quando o
work-horse e morto por um restart do worker (deploy / auto-recycle / OOM) ANTES
de concluir, o registro `CarviaEmissaoCteComplementar` fica preso em
EM_PROCESSAMENTO para sempre: o processo morreu antes do `except` poder gravar
ERRO, e o proprio timeout do RQ nao chega a disparar (precisaria do work-horse
vivo). Isso (a) trava o polling da UI em "Emissao SSW em andamento..." e
(b) bloqueia nova emissao para a mesma operacao (mutex em
CteComplementarService.criar_para_emissao_ssw checa PENDENTE/EM_PROCESSAMENTO).

Este script ENCERRA o tracking travado:
  1. Marca a emissao como ERRO (so se ainda PENDENTE/EM_PROCESSAMENTO — idempotente),
     com erro_ssw explicativo e etapa=None.
  2. Limpa o job orfao no Redis (StartedJobRegistry da fila 'high'), best-effort.

O QUE ESTE SCRIPT *NAO* FAZ (de proposito):
  - NAO re-emite o CTe Complementar. RE-EMITIR exige antes verificar no SSW
    (opcao 101 do CTRC pai) se o CTe ja foi transmitido ao SEFAZ — a etapa
    'PREENCHIMENTO' NAO e atualizada granularmente, entao o banco sozinho nao
    prova que o SEFAZ nao emitiu. Re-emitir as cegas pode DUPLICAR a nota.
  - NAO altera o CarviaCteComplementar (permanece RASCUNHO). Cancelar/avancar
    esse CTe e decisao de negocio separada.

dry-run e o DEFAULT. So efetiva com --confirmar.

Uso (no ambiente de PRODUCAO — Render Shell do worker ou web):
    source .venv/bin/activate
    # 1) inspecionar (dry-run):
    python scripts/carvia/encerrar_emissao_cte_comp_travada.py --emissao-id 22
    # 2) efetivar:
    python scripts/carvia/encerrar_emissao_cte_comp_travada.py --emissao-id 22 --confirmar
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402
from app.utils.timezone import agora_utc_naive  # noqa: E402

QUEUE_NAME = 'high'
ENCERRAVEIS = ('PENDENTE', 'EM_PROCESSAMENTO')


def _limpar_job_redis(job_id):
    """Remove o job orfao do Redis (StartedJobRegistry da fila 'high').

    Best-effort: o work-horse ja morreu, entao nao ha processo para sinalizar —
    so limpamos o registro pendurado. Sem retry configurado no enqueue, o job
    nao re-executa; isto e apenas higiene do registry. Retorna (ok, detalhe).
    """
    try:
        from app.portal.workers import get_redis_connection
        from rq.job import Job
        from rq.registry import StartedJobRegistry, FailedJobRegistry

        conn = get_redis_connection()
        try:
            job = Job.fetch(job_id, connection=conn)
            status = job.get_status(refresh=True)
        except Exception:
            job = None
            status = 'NAO_ENCONTRADO'

        # Tira o job dos registries onde possa estar pendurado.
        for Reg in (StartedJobRegistry, FailedJobRegistry):
            try:
                reg = Reg(QUEUE_NAME, connection=conn)
                if job_id in reg.get_job_ids():
                    reg.remove(job_id, delete_job=False)
            except Exception:
                pass

        if job is not None:
            try:
                job.delete()
            except Exception:
                pass

        return True, f'job status anterior={status}'
    except Exception as e:  # Redis indisponivel / RQ ausente — nao fatal
        return False, f'falha ao limpar Redis: {e}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--emissao-id', type=int, required=True,
                        help='ID do CarviaEmissaoCteComplementar travado')
    parser.add_argument('--confirmar', action='store_true',
                        help='Efetiva as mudancas (sem isso = dry-run)')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        print('=' * 64)
        print(f'Encerrar emissao CTe Complementar travada — id={args.emissao_id}')
        print(f'Modo: {"EFETIVAR" if args.confirmar else "DRY-RUN (nada sera gravado)"}')
        print('=' * 64)

        row = db.session.execute(text("""
            SELECT id, operacao_id, cte_complementar_id, ctrc_pai,
                   status, etapa, job_id, valor_calculado,
                   atualizado_em,
                   EXTRACT(EPOCH FROM (NOW() - atualizado_em))/60 - 180
                       AS parada_real_min
            FROM carvia_emissao_cte_complementar
            WHERE id = :id
        """), {'id': args.emissao_id}).mappings().first()

        if not row:
            print(f'ERRO: emissao {args.emissao_id} nao encontrada.')
            return 1

        print(f'  operacao_id        : {row["operacao_id"]}')
        print(f'  cte_complementar_id: {row["cte_complementar_id"]}')
        print(f'  ctrc_pai           : {row["ctrc_pai"]}')
        print(f'  status             : {row["status"]}')
        print(f'  etapa              : {row["etapa"]}')
        print(f'  job_id             : {row["job_id"]}')
        print(f'  valor_calculado    : {row["valor_calculado"]}')
        print(f'  parada_real (min)  : {float(row["parada_real_min"]):.1f}')
        print()

        if row['status'] not in ENCERRAVEIS:
            print(f'NO-OP: status ja e {row["status"]} (nao esta em '
                  f'{ENCERRAVEIS}). Nada a fazer.')
            return 0

        msg_erro = (
            f'Worker reiniciado durante a emissao (deploy/recycle) — job orfao '
            f'encerrado manualmente em {agora_utc_naive():%Y-%m-%d %H:%M} '
            f'(BRT). NAO re-emitir sem verificar no SSW (opcao 101 do CTRC pai '
            f'{row["ctrc_pai"]}) se o CTe ja foi transmitido ao SEFAZ.'
        )

        # ── 1) Encerrar o tracking no banco ──
        if args.confirmar:
            db.session.execute(text("""
                UPDATE carvia_emissao_cte_complementar
                SET status = 'ERRO',
                    etapa = NULL,
                    erro_ssw = :erro,
                    atualizado_em = :agora
                WHERE id = :id AND status IN ('PENDENTE', 'EM_PROCESSAMENTO')
            """), {'erro': msg_erro, 'agora': agora_utc_naive(),
                   'id': args.emissao_id})
            db.session.commit()
            print(f'[OK] emissao {args.emissao_id} -> status=ERRO (etapa=None).')
        else:
            print(f'[DRY-RUN] marcaria emissao {args.emissao_id} -> ERRO')
            print(f'          erro_ssw = "{msg_erro}"')

        # ── 2) Limpar job orfao no Redis ──
        if row['job_id']:
            if args.confirmar:
                ok, detalhe = _limpar_job_redis(row['job_id'])
                print(f'[{"OK" if ok else "AVISO"}] Redis: {detalhe}')
            else:
                print(f'[DRY-RUN] limparia job {row["job_id"]} do Redis '
                      f'(StartedJobRegistry da fila "{QUEUE_NAME}")')

        print()
        print('CTe Complementar permanece RASCUNHO — cancelar/re-emitir e '
              'decisao separada (ver aviso sobre SEFAZ acima).')
        return 0


if __name__ == '__main__':
    sys.exit(main())
