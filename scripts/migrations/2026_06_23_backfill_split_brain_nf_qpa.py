"""Backfill corretivo: NFs Q.P.A. split-brain (double-match trap).

Contexto (2026-06-23, carga histórica Rayssa): quando NÃO há separação viva,
`ajustar_separacao_pela_nf` (S1=b) cria a AssaiSeparacao já em status FATURADA e
emite eventos SEPARADA+FATURADA por chassi. Logo depois, `_calcular_match` roda
mas seu JOIN EXCLUI separações FATURADA -> não enxerga a sep recém-criada -> grava
`nf.status_match=NAO_RECONCILIADO` e deixa `AssaiNfQpaItem.separacao_item_id=NULL`.
Resultado: estado SPLIT-BRAIN (chassis já FATURADA + sep FATURADA, mas a NF parece
órfã). Ver app/motos_assai/CLAUDE.md "Guards de import de NF Q.P.A.".

Este script CORRIGE apenas as NFs em estado COMPROVADAMENTE consistente:
  - status_match = NAO_RECONCILIADO
  - separacao_id aponta para uma sep status=FATURADA
  - TODO item da NF casa (por chassi) com um AssaiSeparacaoItem dessa sep
  - TODO chassi da NF tem último evento = FATURADA
Para cada uma: religa `separacao_item_id` (NULL -> id do sep item) e seta
`status_match=BATEU`. NÃO re-emite eventos (já existem) nem dispara espelho Nacom
(a moto já saiu fisicamente). NFs com qualquer inconsistência são PULADAS e listadas.

Idempotente (só toca NAO_RECONCILIADO + separacao_item_id IS NULL).
Dry-run é o DEFAULT; use --apply para efetivar. --db-url ou env DB_URL_BACKFILL
(default: DATABASE_URL_PROD do .env).

Uso:
  python scripts/migrations/2026_06_23_backfill_split_brain_nf_qpa.py            # dry-run
  python scripts/migrations/2026_06_23_backfill_split_brain_nf_qpa.py --apply    # efetiva
"""
import argparse
import os
import sys

import psycopg2


SELECT_LIMPAS = """
select nf.id, nf.numero, nf.separacao_id,
       (select count(*) from assai_nf_qpa_item i where i.nf_id=nf.id) as itens,
       (select count(*) from assai_nf_qpa_item i where i.nf_id=nf.id
          and i.separacao_item_id is null) as itens_sem_link
from assai_nf_qpa nf
join assai_separacao sep on sep.id = nf.separacao_id
where nf.status_match = 'NAO_RECONCILIADO'
  and sep.status = 'FATURADA'
  and not exists (
        select 1 from assai_nf_qpa_item i
        where i.nf_id = nf.id
          and not exists (
            select 1 from assai_separacao_item si
            where si.separacao_id = nf.separacao_id and si.chassi = i.chassi)
      )
  and not exists (
        select 1 from assai_nf_qpa_item i
        where i.nf_id = nf.id
          and (select e.tipo from assai_moto_evento e
               where e.chassi = i.chassi
               order by e.ocorrido_em desc, e.id desc limit 1) is distinct from 'FATURADA'
      )
order by nf.numero
"""

RELINK = """
update assai_nf_qpa_item i
   set separacao_item_id = si.id
  from assai_separacao_item si
 where i.nf_id = %s
   and si.separacao_id = %s
   and si.chassi = i.chassi
   and i.separacao_item_id is null
"""

FLIP = "update assai_nf_qpa set status_match='BATEU' where id=%s and status_match='NAO_RECONCILIADO'"


def _db_url():
    url = os.environ.get('DB_URL_BACKFILL')
    if url:
        return url
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    for ln in open(os.path.abspath(env_path)):
        if ln.strip().startswith('DATABASE_URL_PROD='):
            return ln.split('=', 1)[1].strip()
    raise SystemExit('DATABASE_URL_PROD nao encontrado (.env) e DB_URL_BACKFILL nao setado')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='Efetiva (default: dry-run)')
    ap.add_argument('--db-url', default=None)
    args = ap.parse_args()

    conn = psycopg2.connect(args.db_url or _db_url())
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute(SELECT_LIMPAS)
    limpas = cur.fetchall()

    print(f"NFs split-brain CONSISTENTES (alvo do backfill): {len(limpas)}")
    print(f"  {'NF':>8} {'sep_id':>8} {'itens':>6} {'sem_link':>9}")
    total_relink = 0
    for nfid, numero, sepid, itens, sem_link in limpas:
        print(f"  {numero:>8} {sepid:>8} {itens:>6} {sem_link:>9}")
        total_relink += sem_link

    print(f"\nPlano: religar {total_relink} itens + flip {len(limpas)} NFs NAO_RECONCILIADO->BATEU")

    if not args.apply:
        print("\nDRY-RUN (nada gravado). Use --apply para efetivar.")
        conn.rollback()
        return

    for nfid, numero, sepid, itens, sem_link in limpas:
        cur.execute(RELINK, (nfid, sepid))
        cur.execute(FLIP, (nfid,))
    conn.commit()
    print(f"\nAPLICADO: {len(limpas)} NFs -> BATEU, {total_relink} itens religados. Commit OK.")
    conn.close()


if __name__ == '__main__':
    sys.exit(main())
