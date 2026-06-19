"""Backfill: pendencia resolvida das 143 motos Assai FATURADAS-com-defeito.

CONTEXTO (carga historica Rayssa, 2026-06-19): a planilha "ATUALIZACAO CHASSI.xlsx"
traz 143 motos com STATUS=FATURADAS e a coluna PROBLEMA NO CHASSI preenchida
(defeito descoberto na MONTAGEM — as motos vem em caixa, o defeito nao aparece no
recebimento). No sistema essas 143 estao em ESTOQUE, sem o defeito registrado. A
regra do modulo e: moto so e faturada APOS resolver a pendencia. Este backfill
registra, por chassi, a sequencia historica:

    ESTOQUE (ja existe) -> PENDENTE -> PENDENCIA_RESOLVIDA -> MONTADA

deixando a moto pronta para o faturamento posterior (import de NF Q.P.A.), sem
quebrar a invariante Pendencia -> Resolucao -> Faturamento.

Datas (ocorrido_em retroativo, via emitir_evento(ocorrido_em=) integrado em
2026-06-19, commit 7dbd82f4b):
- PENDENTE            = DATA DE CHEGADA (defeito constatado na montagem pos-chegada)
- PENDENCIA_RESOLVIDA = DATA DE FATURAMENTO (resolvido antes de faturar)
- MONTADA            = DATA DE FATURAMENTO (status_efetivo final = MONTADA)
  (guard: se faturamento < chegada ou ausente, usa a chegada — ordem garantida)

Idempotente: processa apenas chassi com status_efetivo == ESTOQUE (apos rodar,
ficam MONTADA -> re-execucao pula). NAO toca os 34 PENDENTE / 55 DISPONIVEL ja
gravados, nem cor/modelo da moto. Append-only.

USO:
    # dry-run contra PROD (nada escrito):
    python scripts/migrations/2026_06_19_backfill_pendencia_resolvida_assai_143.py --prod
    # aplicar:
    python scripts/migrations/2026_06_19_backfill_pendencia_resolvida_assai_143.py --prod --confirmar
"""
import os
import sys
import glob
import argparse
from datetime import datetime

from dotenv import load_dotenv

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
load_dotenv(os.path.join(_ROOT, '.env'))

OPERADOR_ID = 78  # Rayssa Alves (dona da operacao; consistente com os 144 eventos ja gravados)
CHASSI_PADRAO = '/mnt/c/Users/rafael.nascimento/Downloads/ATUALIZA*CHASSI*.xlsx'
BACKFILL_TAG = '2026-06-19 pendencia-resolvida 143 FATURADAS (carga historica Rayssa)'


def _norm_chassi(v):
    if v is None:
        return None
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    if isinstance(v, int):
        return str(v)
    return str(v).strip()


def _tem(v):
    return v is not None and str(v).strip() != ''


def _extrair_143(planilha_glob):
    import openpyxl
    cands = sorted(glob.glob(planilha_glob))
    if not cands:
        sys.exit(f'ERRO: planilha nao encontrada em {planilha_glob}')
    fp = cands[0]
    wb = openpyxl.load_workbook(fp, data_only=True, read_only=True)
    ws = wb.active
    rows = [r for r in ws.iter_rows(values_only=True)]
    header = [str(c).strip() if c is not None else '' for c in rows[0]]
    idx = {h: i for i, h in enumerate(header)}

    def col(r, name):
        i = idx.get(name)
        return r[i] if (i is not None and i < len(r)) else None

    reg = []
    for r in rows[1:]:
        if all(c is None for c in r):
            continue
        if not str(col(r, 'STATUS')).strip().upper().startswith('FATURAD'):
            continue
        if not _tem(col(r, 'PROBLEMA NO CHASSI')):
            continue
        cheg = col(r, 'DATA DE CHEGADA')
        fat = col(r, 'DATA DE FATURAMENTO')
        reg.append({
            'chassi': _norm_chassi(col(r, 'CHASSI')),
            'problema': str(col(r, 'PROBLEMA NO CHASSI')).strip(),
            'data_chegada': cheg if isinstance(cheg, datetime) else None,
            'data_faturamento': fat if isinstance(fat, datetime) else None,
        })
    return fp, reg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--planilha', default=CHASSI_PADRAO)
    ap.add_argument('--prod', action='store_true', help='usa DATABASE_URL_PROD')
    ap.add_argument('--confirmar', action='store_true', help='aplica (default: dry-run)')
    a = ap.parse_args()

    if a.prod:
        if not os.environ.get('DATABASE_URL_PROD'):
            sys.exit('ERRO: DATABASE_URL_PROD ausente no .env')
        os.environ['DATABASE_URL'] = os.environ['DATABASE_URL_PROD']

    fp, reg = _extrair_143(a.planilha)
    print(f'Planilha: {fp}')
    print(f'FATURADAS-com-observacao extraidas: {len(reg)}')

    from app import create_app, db
    from app.motos_assai.models import (
        AssaiMoto, EVENTO_ESTOQUE, EVENTO_PENDENTE,
        EVENTO_PENDENCIA_RESOLVIDA, EVENTO_MONTADA,
    )
    from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo

    app = create_app()
    with app.app_context():
        plano, pular = [], []
        for x in reg:
            ch = x['chassi']
            if not ch or len(x['problema']) < 3:
                pular.append((ch, 'chassi vazio / obs <3 chars')); continue
            if not x['data_chegada']:
                pular.append((ch, 'sem data de chegada')); continue
            if not AssaiMoto.query.filter_by(chassi=ch).first():
                pular.append((ch, 'inexistente em assai_moto')); continue
            st = status_efetivo(ch)
            if st != EVENTO_ESTOQUE:
                pular.append((ch, f'status={st} (ja processado/idempotente)')); continue
            plano.append(x)

        print(f'\nA PROCESSAR: {len(plano)} | PULAR: {len(pular)}')
        for ch, m in pular:
            print(f'  PULAR {ch}: {m}')
        print('\nAmostra (3) do que sera criado:')
        for x in plano[:3]:
            cheg = x['data_chegada']
            fat = x['data_faturamento'] if (x['data_faturamento'] and x['data_faturamento'] >= cheg) else cheg
            print(f"  {x['chassi']}: PENDENTE@{cheg.date()} -> RESOLVIDA/MONTADA@{fat.date()} | obs={x['problema'][:45]!r}")

        if not a.confirmar:
            print(f'\n[DRY-RUN] Nada escrito. Aplicaria {len(plano) * 3} eventos ({len(plano)} motos x 3).')
            return

        # ---- ESCRITA: transacao unica (emitir_evento faz flush, nao commit) ----
        criados = 0
        try:
            for x in plano:
                ch = x['chassi']
                cheg = x['data_chegada']
                fat = x['data_faturamento'] if (x['data_faturamento'] and x['data_faturamento'] >= cheg) else cheg
                de = {
                    'descricao': x['problema'], 'chassi_doador': None,
                    'fonte': 'ATUALIZACAO CHASSI.xlsx', 'backfill': BACKFILL_TAG,
                    'backfill_por': 'claude-code 4-maos',
                }
                emitir_evento(ch, EVENTO_PENDENTE, operador_id=OPERADOR_ID,
                              observacao=x['problema'], dados_extras=de, ocorrido_em=cheg)
                emitir_evento(ch, EVENTO_PENDENCIA_RESOLVIDA, operador_id=OPERADOR_ID,
                              observacao='Backfill carga historica: pendencia resolvida antes do faturamento',
                              dados_extras={'backfill': BACKFILL_TAG}, ocorrido_em=fat)
                emitir_evento(ch, EVENTO_MONTADA, operador_id=OPERADOR_ID,
                              dados_extras={'backfill': BACKFILL_TAG}, ocorrido_em=fat)
                criados += 3

            assert criados == len(plano) * 3, f'sanity gate: {criados} != {len(plano) * 3}'
            db.session.commit()
            print(f'\n[COMMITTED] {criados} eventos ({len(plano)} motos x 3).')
        except Exception as e:
            db.session.rollback()
            print(f'\n[ROLLBACK] {type(e).__name__}: {e}')
            raise

        # ---- validacao pos-commit (re-query) ----
        chs = [x['chassi'] for x in plano]
        montada = sum(1 for c in chs if status_efetivo(c) == EVENTO_MONTADA)
        print(f'[VALIDACAO] status_efetivo=MONTADA: {montada}/{len(plano)}')


if __name__ == '__main__':
    main()
