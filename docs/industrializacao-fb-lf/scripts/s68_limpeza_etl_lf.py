#!/usr/bin/env python3
"""S68 — LIMPEZA dos registros espurios do ETL (NFs de industrializacao LF->FB do piloto).

⚠️ ESCREVE no BANCO DE PRODUCAO da APP (NACOM, via DATABASE_URL_PROD) — NAO no Odoo.

Contexto (2026-06-15): o ETL `faturamento_service` importou as 2 NFs de saida LF
do piloto — 13313 (servico) + 13314 (insumos, total=0) — gerando registros
espurios: 17 FaturamentoProduto + 17 MovimentacaoEstoque que re-baixaram o estoque
interno dos insumos + PA. A carteira NAO foi tocada (0 separacoes vinculadas).

Limpeza CIRURGICA = passos 1+2 do `_processar_cancelamento_nf` (faturamento_service):
  (1) FaturamentoProduto.status_nf -> 'Cancelado'
  (2) MovimentacaoEstoque.ativo -> False, status_nf -> 'CANCELADO'  (restaura estoque)
NAO faz o passo 6 (_atualizar_saldos_carteira): a carteira esta INTACTA e o origem
dos espurios e' o origin sintetico 'RET-IND-4870112-PILOTO' (nao e' pedido real).

O filtro de company no ETL (commit do faturamento_service) impede NOVOS casos.

Modos:
  (default)    DRY-RUN — conta o que sera afetado (so SELECT)
  --confirmar  executa os 2 UPDATEs em UMA transacao; guard exige 17/17 senao ROLLBACK
"""
import os
import sys
from datetime import datetime, timezone

import psycopg2

NFS = ('13313', '13314')
TAG = 'limpeza-ETL-LF-piloto-s68-2026-06-15'
ESPERADO_FAT = 17
ESPERADO_MOV = 17
SEP = '=' * 80


def _load_prod_url():
    # carregar .env sem depender de python-dotenv
    url = os.environ.get('DATABASE_URL_PROD')
    if url:
        return url
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
    env_path = os.path.abspath(env_path)
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith('DATABASE_URL_PROD='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    raise RuntimeError('DATABASE_URL_PROD nao encontrado em env nem em .env')


def main():
    confirmar = '--confirmar' in sys.argv
    url = _load_prod_url()
    conn = psycopg2.connect(url)
    conn.autocommit = False
    cur = conn.cursor()

    print(SEP)
    print(f'S68 — limpeza ETL (NFs {NFS}) — {"EXECUTAR" if confirmar else "DRY-RUN"}')
    print(SEP)

    cur.execute("SELECT numero_nf, count(*) FROM faturamento_produto "
                "WHERE numero_nf IN %s AND status_nf <> 'Cancelado' GROUP BY numero_nf ORDER BY numero_nf", (NFS,))
    fat = cur.fetchall()
    cur.execute("SELECT numero_nf, count(*) FROM movimentacao_estoque "
                "WHERE numero_nf IN %s AND ativo = true GROUP BY numero_nf ORDER BY numero_nf", (NFS,))
    mov = cur.fetchall()
    tot_fat = sum(c for _, c in fat)
    tot_mov = sum(c for _, c in mov)
    print(f'  faturamento_produto a marcar Cancelado: {fat}  total={tot_fat} (esperado {ESPERADO_FAT})')
    print(f'  movimentacao_estoque a inativar:        {mov}  total={tot_mov} (esperado {ESPERADO_MOV})')

    if not confirmar:
        print('\n  [DRY-RUN] nada escrito. Para executar: --confirmar')
        print(SEP)
        conn.close()
        return

    if tot_fat != ESPERADO_FAT or tot_mov != ESPERADO_MOV:
        print(f'\n  ⚠️ contagem != esperado ({ESPERADO_FAT}/{ESPERADO_MOV}) — ABORT sem escrever')
        conn.close()
        return

    now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC (convencao do sistema)
    cur.execute("UPDATE faturamento_produto SET status_nf='Cancelado', updated_at=%s, updated_by=%s "
                "WHERE numero_nf IN %s AND status_nf <> 'Cancelado'", (now, TAG, NFS))
    n_fat = cur.rowcount
    cur.execute("UPDATE movimentacao_estoque SET ativo=false, status_nf='CANCELADO', atualizado_em=%s, atualizado_por=%s "
                "WHERE numero_nf IN %s AND ativo = true", (now, TAG, NFS))
    n_mov = cur.rowcount
    print(f'\n  UPDATE faturamento_produto -> {n_fat} linhas')
    print(f'  UPDATE movimentacao_estoque -> {n_mov} linhas')

    if n_fat != ESPERADO_FAT or n_mov != ESPERADO_MOV:
        print(f'  ⚠️ rowcount != esperado — ROLLBACK (nada gravado)')
        conn.rollback()
        conn.close()
        return

    conn.commit()
    print('  ✅ COMMIT OK — estoque interno dos insumos + PA restaurado, faturamento espurio cancelado')
    print(SEP)
    conn.close()


if __name__ == '__main__':
    main()
