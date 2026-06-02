#!/usr/bin/env python3
"""Troca de NF Atacadao 881 — verificacao de reversao + devolucao automatica ao Indisponivel.

CONTEXTO (operacao TEMPORARIA — 2026-06-01):
  Para viabilizar uma TROCA de NF, foi transferido o saldo das 2 NFs faturadas
  para o Atacadao 881 de `CD/Indisponivel` (lote MIGRACAO) -> `CD/Estoque`
  (lote `P-01/06`), deixando o estoque DISPONIVEL no CD (ver Tarefa 1).

  Quando cada NF original for REVERTIDA (entrada via NF de credito, registrada em
  `movimentacao_estoque` como tipo=ENTRADA / local=REVERSAO), o saldo precisa
  VOLTAR para `CD/Indisponivel` (lote MIGRACAO) — desfazendo a Tarefa 1.

CRITERIO DE REVERSAO (definido com o usuario):
  Granularidade = "NF INTEIRA DE UMA VEZ": so devolve quando a NF estiver
  100% revertida (todos os produtos com qtd_revertida >= qtd_original). Devolve
  as qtds ORIGINAIS inteiras.

EXECUCAO (definido com o usuario):
  "Detectar e executar AUTO" — ao detectar 100% revertida, executa a volta
  automaticamente (transferir.py --confirmar).
  Estrategia de lote "tanto faz, desde que automatico" (decisao usuario): baixa
  a qtd da NF de CD/Estoque consumindo o lote P-01/06 PRIMEIRO e, se faltar,
  completando dos demais lotes de CD/Estoque com saldo LIVRE (maior primeiro).
  Consulta os quants AO VIVO no momento (consultar_quants.py).
  Salvaguardas:
    - planejamento + dry-run de cada movimento ANTES do real;
    - NAO toca saldo reservado; se nao houver saldo LIVRE suficiente em
      CD/Estoque, aborta a NF inteira e ALERTA (nunca parcial);
    - idempotencia via arquivo de estado (uma NF devolvida nunca repete).

FONTES DE DADOS:
  - LEITURA reversao: Render PROD via DATABASE_URL_PROD (NAO o localhost de teste).
  - ESCRITA volta: Odoo PROD via skill `transferindo-interno-odoo` (transferir.py).

USO:
  # checagem (default, NAO executa volta — so detecta e reporta):
  python verificar_reversao_e_devolver.py

  # executa a volta de verdade quando detectar NF 100% revertida:
  python verificar_reversao_e_devolver.py --confirmar

  # forcar reprocessamento (ignora estado) — debug:
  python verificar_reversao_e_devolver.py --confirmar --force

  # restringir a uma NF:
  python verificar_reversao_e_devolver.py --confirmar --nf 146390

CRONTAB (diario, junto ao horario do D8):
  30 11 * * * cd /home/rafaelnascimento/projetos/frete_sistema && \
    .venv/bin/python scripts/operacionais/troca_nf_atacadao881/verificar_reversao_e_devolver.py \
    --confirmar >> /tmp/troca_nf_881.log 2>&1

DESATIVAR (quando ambas as NFs forem devolvidas):
  remover a linha do crontab (`crontab -e`). O estado_reversao.json registra o que ja foi feito.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[3]  # scripts/operacionais/troca_nf_atacadao881/<f> -> repo root
sys.path.insert(0, str(_REPO_ROOT))

# ---------------------------------------------------------------------------
# CONFIG da operacao (auditavel — qtds ORIGINAIS das 2 NFs, fonte movimentacao_estoque/faturamento_produto)
# ---------------------------------------------------------------------------
EMPRESA = 'CD'                      # company_id=4 no Odoo
LOC_ESTOQUE = 32                    # CD/Estoque (location_id) — origem da VOLTA
LOC_INDISPONIVEL = 31090           # CD/Indisponivel (location_id) — destino da VOLTA
LOTE_TEMP = 'P-01/06'              # lote temporario criado na Tarefa 1 (origem da volta)
LOTE_MIGRACAO = 'MIGRAÇÃO'         # lote destino da volta (com cedilha — grafia confirmada ao vivo)

# numero_nf -> {cod_produto: qtd_original}
NFS: dict[str, dict[str, float]] = {
    '146390': {
        '4040161': 4, '4050176': 10, '4070176': 10, '4080178': 9, '4310146': 16,
        '4310152': 16, '4310162': 5, '4310177': 10, '43109068': 10, '4320154': 16,
        '4320162': 5, '4320172': 8, '4350150': 16, '4360147': 32, '4360155': 16,
        '4360162': 5, '4360172': 10, '4510145': 6, '4520145': 5, '4729098': 20,
        '4739099': 9,
    },
    '146608': {
        '4210176': 5, '4310148': 16, '4320147': 16,
    },
}

TRANSFERIR_PY = _REPO_ROOT / '.claude/skills/transferindo-interno-odoo/scripts/transferir.py'
CONSULTAR_QUANTS_PY = _REPO_ROOT / '.claude/skills/consultando-quant-odoo/scripts/consultar_quants.py'
ESTADO_PATH = _THIS.parent / 'estado_reversao.json'
CONCLUIDO_FLAG = _THIS.parent / 'CONCLUIDO.flag'  # criado quando TODAS as NFs viram DEVOLVIDA -> cron vira no-op
TZ_BR = ZoneInfo('America/Sao_Paulo')
TOL = 0.001  # tolerancia de comparacao de qtd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s | %(message)s',
)
logger = logging.getLogger('troca_nf_881')


def agora_br() -> str:
    return datetime.now(TZ_BR).strftime('%Y-%m-%d %H:%M:%S %Z')


# ---------------------------------------------------------------------------
# Estado (idempotencia)
# ---------------------------------------------------------------------------
def carregar_estado() -> dict:
    if ESTADO_PATH.exists():
        try:
            return json.loads(ESTADO_PATH.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            logger.warning('estado_reversao.json corrompido — recomecando do zero')
    return {}


def salvar_estado(estado: dict) -> None:
    ESTADO_PATH.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding='utf-8')


# ---------------------------------------------------------------------------
# Leitura PROD (Render) — detectar reversao
# ---------------------------------------------------------------------------
def _get_prod_dsn() -> str:
    """DATABASE_URL_PROD (Render). Carrega .env se necessario."""
    dsn = os.getenv('DATABASE_URL_PROD')
    if not dsn:
        try:
            from dotenv import load_dotenv
            load_dotenv(_REPO_ROOT / '.env')
        except ImportError:
            pass
        dsn = os.getenv('DATABASE_URL_PROD')
    if not dsn:
        raise RuntimeError('DATABASE_URL_PROD ausente no ambiente/.env — nao consigo ler o Render PROD')
    return dsn


def qtds_revertidas(nf: str) -> dict[str, float]:
    """Soma qtd revertida por produto da NF (ENTRADA/REVERSAO no Render PROD)."""
    import psycopg2

    dsn = _get_prod_dsn()
    sql = """
        SELECT cod_produto, COALESCE(SUM(qtd_movimentacao), 0) AS qtd_rev
        FROM movimentacao_estoque
        WHERE tipo_movimentacao = 'ENTRADA'
          AND local_movimentacao = 'REVERSAO'
          AND numero_nf = %s
          AND ativo = TRUE
        GROUP BY cod_produto
    """
    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (nf,))
            return {str(cod): float(q) for cod, q in cur.fetchall()}
    finally:
        conn.close()


def nf_100_revertida(nf: str, revertidas: dict[str, float]) -> tuple[bool, list[str]]:
    """True se TODOS os produtos originais da NF tem qtd_revertida >= qtd_original.

    Retorna (ok, faltantes) — faltantes = produtos ainda nao 100% revertidos.
    """
    faltantes = []
    for cod, qtd_orig in NFS[nf].items():
        rev = revertidas.get(cod, 0.0)
        if rev + TOL < qtd_orig:
            faltantes.append(f'{cod} (rev {rev:g} < orig {qtd_orig:g})')
    return (len(faltantes) == 0, faltantes)


# ---------------------------------------------------------------------------
# Escrita Odoo — VOLTA: CD/Estoque -> CD/Indisponivel/MIGRACAO
# ---------------------------------------------------------------------------
# Estrategia "tanto faz o lote, automatico" (decisao usuario): baixa a qtd da NF
# de CD/Estoque consumindo o lote P-01/06 PRIMEIRO (o ajuste dedicado) e, se faltar
# (caso a nova NF venha a consumi-lo), completando dos demais lotes de CD/Estoque
# com saldo LIVRE (maior primeiro). Destino sempre MIGRACAO/CD/Indisponivel.
# Saldo reservado NAO e tocado. Se CD/Estoque nao tiver saldo livre suficiente,
# aborta a NF inteira e ALERTA (nunca devolve parcial).

def _quants_cd_estoque(cod: str) -> list[dict]:
    """Quants do produto em CD/Estoque (loc 32) com saldo LIVRE > 0. [{'lote','available'}]."""
    cmd = [
        sys.executable, str(CONSULTAR_QUANTS_PY), '--modo', 'quants',
        '--empresas', EMPRESA, '--cods', str(cod), '--formato', 'json',
    ]
    proc = subprocess.run(cmd, cwd=str(_REPO_ROOT), capture_output=True, text=True, env=os.environ.copy())
    if proc.returncode != 0:
        raise RuntimeError(f'consulta quants falhou (cod {cod}): {proc.stderr.strip()[-300:]}')
    i = proc.stdout.find('{')
    if i < 0:
        raise RuntimeError(f'consulta quants sem JSON (cod {cod}): {proc.stdout.strip()[-200:]}')
    data = json.loads(proc.stdout[i:])
    res = []
    for q in data.get('quants', []):
        if q.get('location_id') == LOC_ESTOQUE and float(q.get('available') or 0) > TOL:
            res.append({'lote': q.get('lote'), 'available': float(q['available'])})
    return res


def _plano_devolucao(qty_total: float, quants: list[dict]) -> tuple[list[dict], float]:
    """Plano greedy: P-01/06 primeiro, depois maior saldo livre. Retorna (itens, faltante)."""
    ordenados = sorted(quants, key=lambda q: (q['lote'] != LOTE_TEMP, -q['available']))
    plano, restante = [], qty_total
    for q in ordenados:
        if restante <= TOL:
            break
        usar = min(q['available'], restante)
        if usar > TOL:
            plano.append({'lote': q['lote'], 'qty': round(usar, 6)})
            restante -= usar
    return plano, round(max(restante, 0.0), 6)


def _chamar_transferir(cod: str, lote_origem: str, qty: float, confirmar: bool) -> tuple[int, str]:
    """transferir.py MODO D: CD/Estoque/<lote_origem> -> CD/Indisponivel/MIGRACAO."""
    cmd = [
        sys.executable, str(TRANSFERIR_PY), '--quiet',
        '--cod', str(cod), '--empresa', EMPRESA, '--qty', str(qty),
        '--loc-e-lote',
        '--loc-origem', str(LOC_ESTOQUE), '--loc-destino', str(LOC_INDISPONIVEL),
        '--lote-origem', lote_origem, '--lote-destino', LOTE_MIGRACAO,
    ]
    if confirmar:
        cmd.append('--confirmar')
    proc = subprocess.run(
        cmd, cwd=str(_REPO_ROOT), capture_output=True, text=True, env=os.environ.copy()
    )
    return proc.returncode, (proc.stdout or '') + (proc.stderr or '')


def devolver_nf(nf: str, confirmar: bool) -> dict:
    """Devolve as qtds da NF de CD/Estoque -> MIGRACAO (greedy P-01/06 first). Tudo-ou-nada por NF.

    Fases: (0) planeja por produto consultando quants ao vivo; (1) dry-run de cada
    movimento; (2) se confirmar e todos dry-run OK, executa o real.
    """
    resultados = {'nf': nf, 'itens': [], 'ok': True, 'executado': confirmar}

    # FASE 0: planejar quais lotes de CD/Estoque baixar por produto
    planos: dict[str, list[dict]] = {}
    for cod, qty in NFS[nf].items():
        try:
            quants = _quants_cd_estoque(cod)
        except Exception as e:  # noqa: BLE001
            resultados['ok'] = False
            resultados['itens'].append({'cod': cod, 'qty': qty, 'status': 'ERRO_CONSULTA', 'detalhe': str(e)})
            logger.error('[%s] cod %s — erro ao consultar quants: %s', nf, cod, e)
            continue
        plano, faltante = _plano_devolucao(qty, quants)
        if faltante > TOL:
            resultados['ok'] = False
            resultados['itens'].append({'cod': cod, 'qty': qty, 'status': 'SALDO_INSUFICIENTE',
                                        'faltante': faltante, 'plano': plano})
            logger.error('[%s] cod %s qty %g — SALDO LIVRE INSUFICIENTE em CD/Estoque '
                         '(falta %g). NAO devolve.', nf, cod, qty, faltante)
        else:
            planos[cod] = plano

    if not resultados['ok']:
        logger.error('[%s] ABORTADA — ao menos 1 produto sem saldo livre suficiente em '
                     'CD/Estoque. Nenhuma escrita. REVISAR MANUALMENTE.', nf)
        return resultados

    # itens "achatados": um por (cod, lote)
    flat = [(cod, p['lote'], p['qty']) for cod, plano in planos.items() for p in plano]

    # FASE 1: dry-run de cada movimento
    for cod, lote, qty in flat:
        rc, out = _chamar_transferir(cod, lote, qty, confirmar=False)
        item = {'cod': cod, 'lote': lote, 'qty': qty, 'dryrun_rc': rc}
        if rc != 4:  # 4 = dry-run OK
            item['status'] = 'DRYRUN_FALHOU'
            item['detalhe'] = out.strip()[-500:]
            resultados['ok'] = False
            logger.error('[%s] cod %s lote %s qty %g — DRY-RUN FALHOU (rc=%s): %s',
                         nf, cod, lote, qty, rc, item['detalhe'])
        else:
            item['status'] = 'DRYRUN_OK'
        resultados['itens'].append(item)

    if not resultados['ok']:
        logger.error('[%s] ABORTADA — dry-run falhou em algum movimento. Nenhuma escrita. REVISAR.', nf)
        return resultados

    if not confirmar:
        logger.info('[%s] dry-run OK em %d movimento(s) (%d produtos). (checagem — use --confirmar)',
                    nf, len(flat), len(planos))
        return resultados

    # FASE 2: execucao real (so chega aqui se confirmar=True e todos dry-run OK)
    for item in resultados['itens']:
        cod, lote, qty = item['cod'], item['lote'], item['qty']
        rc, out = _chamar_transferir(cod, lote, qty, confirmar=True)
        item['real_rc'] = rc
        if rc == 0:  # 0 = efetivado
            item['status'] = 'DEVOLVIDO'
            logger.info('[%s] cod %s lote %s qty %g — DEVOLVIDO a CD/Indisponivel/MIGRACAO',
                        nf, cod, lote, qty)
        else:
            item['status'] = 'REAL_FALHOU'
            item['detalhe'] = out.strip()[-500:]
            resultados['ok'] = False
            logger.error('[%s] cod %s lote %s qty %g — REAL FALHOU (rc=%s): %s',
                         nf, cod, lote, qty, rc, item['detalhe'])

    return resultados


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description='Verifica reversao das NFs e devolve saldo ao Indisponivel')
    ap.add_argument('--confirmar', action='store_true',
                    help='executa a volta de verdade (sem isso = so checagem/dry-run)')
    ap.add_argument('--force', action='store_true',
                    help='ignora estado (reprocessa NF mesmo ja devolvida) — debug')
    ap.add_argument('--nf', choices=list(NFS.keys()), help='restringe a uma NF')
    ap.add_argument('--testar-devolucao', action='store_true',
                    help='TESTE: roda planejamento + dry-run da devolucao (pula checagem de reversao, '
                         'NUNCA confirma) — valida consulta de quants + plano + transferir dry-run')
    args = ap.parse_args()

    # Carrega .env logo no inicio — no cron o ambiente e minimo (sem DATABASE_URL_PROD/ODOO_*).
    # Popular os.environ aqui garante que os subprocessos (transferir.py) herdem as vars Odoo.
    try:
        from dotenv import load_dotenv
        load_dotenv(_REPO_ROOT / '.env')
    except ImportError:
        pass

    # Auto-neutralizacao: se a operacao ja foi concluida (ambas NFs devolvidas),
    # o cron vira no-op imediato — nao conecta em nada. A linha do crontab pode
    # ser removida com `sudo crontab -u rafaelnascimento -e` (opcional, ja e inocua).
    if CONCLUIDO_FLAG.exists() and not args.force:
        print(f'[{agora_br()}] Operacao CONCLUIDA ({CONCLUIDO_FLAG.name} presente) — no-op. '
              f'Pode remover a linha do crontab.')
        return 0

    # Modo TESTE: valida a cadeia de devolucao (quants -> plano -> dry-run) sem reversao real.
    if args.testar_devolucao:
        print('=' * 78)
        print(f'  TESTE DEVOLUCAO (dry-run forcado, NUNCA escreve) | {agora_br()}')
        print('=' * 78)
        for nf in ([args.nf] if args.nf else list(NFS.keys())):
            logger.info('[%s] simulando planejamento + dry-run da devolucao...', nf)
            res = devolver_nf(nf, confirmar=False)
            for it in res['itens']:
                print(f"  {nf} cod={it.get('cod')} lote={it.get('lote', '-')} "
                      f"qty={it.get('qty', '-')} -> {it.get('status')}")
            print(f"  [{nf}] plano OK={res['ok']}")
        return 0

    print('=' * 78)
    print(f'  TROCA NF ATACADAO 881 — verificacao de reversao | {agora_br()}')
    print(f'  modo: {"EXECUTAR (--confirmar)" if args.confirmar else "CHECAGEM (dry-run)"}'
          f'{" | --force" if args.force else ""}')
    print('=' * 78)

    estado = carregar_estado()
    alvos = [args.nf] if args.nf else list(NFS.keys())
    houve_erro = False
    algo_pendente = False

    for nf in alvos:
        st = estado.get(nf, {})
        if st.get('status') == 'DEVOLVIDA' and not args.force:
            logger.info('[%s] ja DEVOLVIDA em %s — pulando (use --force p/ reprocessar)',
                        nf, st.get('devolvida_em'))
            continue

        try:
            rev = qtds_revertidas(nf)
        except Exception as e:  # noqa: BLE001
            logger.error('[%s] erro ao consultar Render PROD: %s', nf, e)
            houve_erro = True
            continue

        ok100, faltantes = nf_100_revertida(nf, rev)
        if not ok100:
            algo_pendente = True
            logger.info('[%s] ainda NAO 100%% revertida. Faltam: %s', nf, ', '.join(faltantes) or '(nenhum dado de reversao ainda)')
            estado[nf] = {**st, 'status': 'AGUARDANDO_REVERSAO',
                          'ultima_checagem': agora_br(),
                          'revertidas_parciais': rev}
            continue

        logger.info('[%s] DETECTADA 100%% revertida! Iniciando devolucao ao Indisponivel...', nf)
        res = devolver_nf(nf, confirmar=args.confirmar)

        if res['ok'] and args.confirmar:
            estado[nf] = {'status': 'DEVOLVIDA', 'devolvida_em': agora_br(),
                          'itens': res['itens']}
            logger.info('[%s] CONCLUIDA — saldo devolvido ao CD/Indisponivel (lote MIGRACAO).', nf)
        elif res['ok'] and not args.confirmar:
            estado[nf] = {**st, 'status': 'PRONTA_PARA_DEVOLVER',
                          'ultima_checagem': agora_br()}
            logger.info('[%s] PRONTA para devolver (dry-run OK). Rode com --confirmar.', nf)
        else:
            houve_erro = True
            estado[nf] = {**st, 'status': 'ERRO_DEVOLUCAO',
                          'ultima_checagem': agora_br(), 'itens': res['itens']}

    salvar_estado(estado)

    # Auto-conclusao: se TODAS as NFs estao DEVOLVIDA, encerra a operacao.
    # Cria CONCLUIDO.flag (proximas execucoes viram no-op) e avisa no log.
    todas_devolvidas = all(estado.get(nf, {}).get('status') == 'DEVOLVIDA' for nf in NFS)
    if todas_devolvidas and not CONCLUIDO_FLAG.exists():
        CONCLUIDO_FLAG.write_text(
            f'Operacao troca NF Atacadao 881 CONCLUIDA em {agora_br()}.\n'
            f'Todas as NFs ({", ".join(NFS)}) foram revertidas e o saldo devolvido '
            f'a CD/Indisponivel (lote MIGRACAO).\n'
            f'Pode remover a linha do crontab: sudo crontab -u rafaelnascimento -e\n',
            encoding='utf-8',
        )
        print('*' * 78)
        print('  >>> OPERACAO CONCLUIDA — todas as NFs devolvidas ao CD/Indisponivel.')
        print('  >>> O cron virou no-op (CONCLUIDO.flag criado).')
        print('  >>> Pode remover a linha do crontab: sudo crontab -u rafaelnascimento -e')
        print('*' * 78)
        logger.warning('OPERACAO CONCLUIDA — todas NFs devolvidas. Cron neutralizado. '
                       'Remover linha do crontab quando quiser.')

    print('-' * 78)
    if houve_erro:
        print('  RESULTADO: houve ERRO — revisar log acima.')
        return 1
    if todas_devolvidas:
        print('  RESULTADO: CONCLUIDO — operacao encerrada.')
    elif algo_pendente:
        print('  RESULTADO: OK — alguma NF ainda aguardando reversao (normal).')
    else:
        print('  RESULTADO: OK — nada pendente.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
