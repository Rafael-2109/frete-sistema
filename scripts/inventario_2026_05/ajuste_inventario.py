# etapa: orquestrador
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""ajuste_inventario.py — Orquestrador GENERICO de ajuste de inventario por planilha.

Consolida (substitui FUNCIONALMENTE, sem apagar) os scripts da "Familia A":
  11_ajuste_negativo_cd, 12_ajuste_positivo_cd, 13_ajuste_positivo_fb,
  14_ajuste_positivo_cd_v2, criar_saldo_positivo_lf.

Arquitetura: este script SO orquestra (le planilha, resolve produto/lote,
decide os args). A operacao atomica de ajuste de 1 quant fica na PRIMITIVA
reutilizavel `StockQuantAdjustmentService.ajustar_quant`. Cada linha da
planilha vira 1 chamada a primitiva (delta = valor da coluna de quantidade).

Constantes vem dos modulos centrais (NAO redefinidas aqui):
  - company_id  <- app.odoo.constants.operacoes_fiscais.CODIGO_PARA_COMPANY_ID
  - location_id <- app.odoo.constants.locations.COMPANY_LOCATIONS

Semantica de --sinal (filtro de escopo + comportamento de criacao):
  pos  : processa so linhas qtd > 0 ; cria lote/quant se faltar
  neg  : processa so linhas qtd < 0 ; exige quant existente (nao cria)
  auto : processa qualquer linha    ; cria se a propria linha for qtd > 0

Schema da planilha via --col-* (defaults EMP/COD/LOTE/AJUSTE). Se --col-emp
nao existir na planilha, todas as linhas sao tratadas como a empresa de --empresa.

Mapeamento dos scripts originais:
  11_ajuste_negativo_cd       -> --empresa CD --sinal neg
  12 / 14_ajuste_positivo_cd  -> --empresa CD --sinal pos
  13_ajuste_positivo_fb       -> --empresa FB --sinal pos
  criar_saldo_positivo_lf     -> --empresa LF --sinal pos --col-qtd "AJUSTE POSITIVO"

Uso:
  python scripts/inventario_2026_05/ajuste_inventario.py --empresa CD --sinal neg --xlsx PATH            # dry-run
  python scripts/inventario_2026_05/ajuste_inventario.py --empresa CD --sinal pos --xlsx PATH --confirmar
"""
import argparse
import json
import logging
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

import pandas as pd  # noqa: E402

from app import create_app  # noqa: E402
from app.odoo.constants.locations import COMPANY_LOCATIONS  # noqa: E402
from app.odoo.constants.operacoes_fiscais import CODIGO_PARA_COMPANY_ID  # noqa: E402
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.services.stock_quant_adjustment_service import (  # noqa: E402
    StockQuantAdjustmentService,
)
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('ajuste_inventario')

CASAS_DECIMAIS = 6


def banner(t: str, c: str = '=') -> None:
    print()
    print(c * 78)
    print(f'  {t}')
    print(c * 78)


def _norm_cod(raw) -> str:
    s = str(raw).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s


def _norm_lote(raw) -> Optional[str]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    if not s or s.lower() == 'nan':
        return None
    if s.endswith('.0'):  # lote numerico lido como float
        s = s[:-2]
    return s


def _parse_qtd(raw) -> Optional[float]:
    """Converte celula de quantidade em float; vazio/nan/invalido -> None.

    Aceita formato EN (ponto decimal, ex. '5.5' — como pandas le numeros) E
    formato BR (virgula decimal, ponto de milhar, ex. '5,5' / '1.234,56').
    """
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    if not s or s.lower() == 'nan':
        return None
    try:
        val = float(s)                                  # EN / pandas (ponto decimal)
    except (TypeError, ValueError):
        try:
            val = float(s.replace('.', '').replace(',', '.'))  # BR (milhar . / decimal ,)
        except (TypeError, ValueError):
            return None
    if pd.isna(val):  # float('nan') nao levanta — barrar aqui
        return None
    return round(val, CASAS_DECIMAIS)


def carregar_planilha(
    path: str, *, col_emp: str, col_cod: str, col_lote: str, col_qtd: str,
) -> List[Dict]:
    """Le XLSX usando os nomes de coluna informados (case-insensitive)."""
    df = pd.read_excel(path, dtype=str)
    df.columns = [c.strip().upper() for c in df.columns]
    col_emp_u = col_emp.strip().upper() if col_emp else ''
    col_cod_u, col_lote_u, col_qtd_u = (
        col_cod.strip().upper(), col_lote.strip().upper(), col_qtd.strip().upper(),
    )

    faltando = [c for c in (col_cod_u, col_qtd_u) if c not in df.columns]
    if faltando:
        raise ValueError(
            f'Planilha sem colunas obrigatorias {faltando}. '
            f'Colunas presentes: {list(df.columns)}'
        )
    tem_emp = bool(col_emp_u) and col_emp_u in df.columns
    tem_lote = col_lote_u in df.columns

    registros = []
    for pos, (_, row) in enumerate(df.iterrows()):
        qtd_raw = row[col_qtd_u]
        registros.append({
            'idx': pos + 1,
            'emp': str(row[col_emp_u]).strip() if tem_emp else None,
            'cod': _norm_cod(row[col_cod_u]),
            'lote_nome': _norm_lote(row[col_lote_u]) if tem_lote else None,
            'qtd': _parse_qtd(qtd_raw),
            'qtd_raw': str(qtd_raw),
        })
    return registros


def resolver_produto(odoo, cod: str) -> Optional[Dict]:
    res = odoo.search_read(
        'product.product', [['default_code', '=', cod]],
        ['id', 'active', 'tracking', 'name'], limit=10,
    )
    if not res:
        return None
    ativos = [r for r in res if r.get('active')]
    escolhido = ativos[0] if ativos else res[0]
    return {
        'pid': escolhido['id'],
        'tracking': escolhido.get('tracking') or 'none',
        'name': escolhido.get('name'),
        'active': bool(escolhido.get('active')),
        'n_matches': len(res),
    }


def processar_linha(
    *,
    svc_adj: StockQuantAdjustmentService,
    lot_svc: StockLotService,
    odoo,
    item: Dict,
    empresa: str,
    company_id: int,
    location_id: int,
    sinal: str,
    dry_run: bool,
) -> Dict:
    """Resolve produto/lote e delega o ajuste de 1 quant a primitiva."""
    r = {**item, 'empresa': empresa, 'company_id': company_id,
         'location_id': location_id, 'inicio': datetime.now().isoformat(timespec='seconds')}

    # 1. Filtro empresa (se a planilha tem coluna EMP)
    if item['emp'] is not None and item['emp'] != empresa:
        r['status'] = 'SKIP_EMP'
        r['erro'] = f'EMP {item["emp"]!r} != {empresa}'
        return r

    # 2. Quantidade valida
    qtd = item['qtd']
    if qtd is None:
        r['status'] = 'FALHA_QTD'
        r['erro'] = f'qtd nao numerica: {item.get("qtd_raw")!r}'
        return r

    # 3. Filtro de sinal (escopo do run)
    if sinal == 'pos' and qtd <= 0:
        r['status'] = 'SKIP_FORA_ESCOPO'
        r['erro'] = f'qtd={qtd} <= 0 (escopo: pos)'
        return r
    if sinal == 'neg' and qtd >= 0:
        r['status'] = 'SKIP_FORA_ESCOPO'
        r['erro'] = f'qtd={qtd} >= 0 (escopo: neg)'
        return r
    if qtd == 0:
        r['status'] = 'SKIP_QTD_ZERO'
        return r

    criar = qtd > 0  # positivo cria lote/quant; negativo exige existente

    # 4. Resolver produto
    prod = resolver_produto(odoo, item['cod'])
    if not prod:
        r['status'] = 'FALHA_PRODUCT'
        r['erro'] = f'default_code {item["cod"]!r} nao encontrado'
        return r
    r['product_id'] = prod['pid']
    r['tracking'] = prod['tracking']
    r['produto_odoo'] = prod['name']
    if prod['n_matches'] > 1:
        r['warning_multiplos_codigos'] = prod['n_matches']
    if not prod['active']:
        r['warning_produto_inativo'] = True

    if prod['tracking'] == 'serial':
        r['status'] = 'BLOQUEADO_SERIAL'
        r['erro'] = 'produto tracking=serial — ajuste por qtd nao suportado'
        return r

    # 5. Resolver lote
    lot_id: Optional[int] = None
    lote_will_create = False
    if prod['tracking'] == 'lot':
        if not item['lote_nome']:
            r['status'] = 'FALHA_LOTE_OBRIGATORIO'
            r['erro'] = 'produto tracking=lot mas planilha sem LOTE'
            return r
        existente = lot_svc.buscar_por_nome(item['lote_nome'], prod['pid'], company_id)
        if existente:
            lot_id = existente
            r['lote_acao'] = 'reused'
        elif not criar:
            r['status'] = 'FALHA_LOTE'
            r['erro'] = (
                f'lote {item["lote_nome"]!r} nao existe e sinal=neg nao cria'
            )
            return r
        elif dry_run:
            lote_will_create = True
            r['lote_acao'] = 'will_create'
        else:
            try:
                lot_id, criado = lot_svc.criar_se_nao_existe(
                    item['lote_nome'], prod['pid'], company_id, expiration_date=None,
                )
                r['lote_acao'] = 'created' if criado else 'reused'
            except Exception as exc:
                r['status'] = 'FALHA_CRIAR_LOTE'
                r['erro'] = f'criar lote {item["lote_nome"]!r}: {exc}'
                return r
    else:  # tracking == 'none'
        lot_id = None
        if item['lote_nome']:
            r['warning_lote_ignorado'] = (
                f'tracking=none — lote {item["lote_nome"]!r} ignorado'
            )

    # 6. Caso lote novo em dry-run: quant tambem nao existe -> sintetiza plano
    if lote_will_create:
        r['status'] = 'DRY_RUN_OK'
        r['quant_acao'] = 'will_create'
        r['qty_antes'] = 0.0
        r['qty_apos'] = qtd
        r['ajuste_aplicado'] = qtd
        return r

    # 7. Delegar a primitiva (ajuste atomico de 1 quant)
    res = svc_adj.ajustar_quant(
        product_id=prod['pid'],
        company_id=company_id,
        location_id=location_id,
        lot_id=lot_id,
        delta=qtd,
        criar_se_faltar=criar,
        validar_nao_negativar=True,
        validar_nao_abaixo_reserva=True,
        casas_decimais=CASAS_DECIMAIS,
        dry_run=dry_run,
    )
    # mescla resultado da primitiva (status, qty_antes/apos, acao, etc.)
    for k in ('status', 'qty_antes', 'qty_apos', 'ajuste_aplicado',
              'reservada', 'acao', 'quant_id', 'tempo_ms', 'erro'):
        if k in res:
            r[k] = res[k]
    r['quant_acao'] = res.get('acao')
    return r


def main():
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--empresa', required=True, choices=sorted(CODIGO_PARA_COMPANY_ID),
                        help='FB | CD | LF')
    parser.add_argument('--sinal', default='auto', choices=['pos', 'neg', 'auto'])
    parser.add_argument('--xlsx', required=True, type=str)
    parser.add_argument('--col-emp', default='EMP', help='coluna empresa (vazio = ignora filtro)')
    parser.add_argument('--col-cod', default='COD')
    parser.add_argument('--col-lote', default='LOTE')
    parser.add_argument('--col-qtd', default='AJUSTE')
    parser.add_argument('--apenas-linhas', default='', help='CSV idx 1-based: 1,5,7')
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--confirmar', action='store_true', default=False)
    parser.add_argument('--log-json', default='')
    args = parser.parse_args()

    dry_run = not args.confirmar
    company_id = CODIGO_PARA_COMPANY_ID[args.empresa]
    if company_id not in COMPANY_LOCATIONS:
        logger.error(f'empresa {args.empresa} (company_id={company_id}) sem '
                     f'entrada em COMPANY_LOCATIONS {sorted(COMPANY_LOCATIONS)}')
        return 2
    location_id = COMPANY_LOCATIONS[company_id]

    if not Path(args.xlsx).exists():
        logger.error(f'XLSX nao encontrado: {args.xlsx}')
        return 2

    try:
        registros = carregar_planilha(
            args.xlsx, col_emp=args.col_emp, col_cod=args.col_cod,
            col_lote=args.col_lote, col_qtd=args.col_qtd,
        )
    except ValueError as exc:
        logger.error(str(exc))
        return 2

    if args.apenas_linhas:
        alvo = {int(s) for s in args.apenas_linhas.split(',') if s.strip()}
        registros = [r for r in registros if r['idx'] in alvo]

    banner(
        f'AJUSTE INVENTARIO {args.empresa} (company={company_id} loc={location_id}) '
        f'sinal={args.sinal} — {"DRY-RUN" if dry_run else "EXEC REAL"} '
        f'({len(registros)} linhas)'
    )
    logger.info(f'XLSX: {args.xlsx} | colunas: emp={args.col_emp!r} cod={args.col_cod!r} '
                f'lote={args.col_lote!r} qtd={args.col_qtd!r}')
    soma = sum(r['qtd'] for r in registros if r['qtd'] is not None)
    print(f'  Soma {args.col_qtd!r} da planilha: {soma:,.6f} un')

    app = create_app()
    resultados = []
    t_global = time.time()
    with app.app_context():
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        svc_adj = StockQuantAdjustmentService(odoo=odoo, lot_svc=lot_svc)
        for item in registros:
            r = processar_linha(
                svc_adj=svc_adj, lot_svc=lot_svc, odoo=odoo, item=item,
                empresa=args.empresa, company_id=company_id,
                location_id=location_id, sinal=args.sinal, dry_run=dry_run,
            )
            resultados.append(r)
            s = r['status']
            base = (f'[{r["idx"]:>3}] {s:18s} cod={item["cod"]:>9} '
                    f'lote={str(item["lote_nome"]):>14} qtd={item["qtd"]}')
            if s in ('EXECUTADO', 'DRY_RUN_OK', 'NOOP'):
                logger.info(f'{base} | qty {r.get("qty_antes")}->{r.get("qty_apos")} '
                            f'lote_acao={r.get("lote_acao", "-")} quant={r.get("quant_acao", "-")}')
            else:
                logger.warning(f'{base} | {r.get("erro")}')

    banner('RESUMO')
    cont = Counter(r['status'] for r in resultados)
    total = len(resultados)
    for status, n in cont.most_common():
        print(f'  {status:28s} {n:4d}  ({n / total * 100 if total else 0:5.1f}%)')
    print(f'  {"TOTAL":28s} {total:4d}')

    soma_ok = sum(
        r['qtd'] for r in resultados
        if r['qtd'] is not None and r['status'] in ('EXECUTADO', 'DRY_RUN_OK')
    )
    print(f'\n  Soma ajustes OK: {soma_ok:,.6f} un | tempo {time.time() - t_global:.1f}s')

    avisos = [r for r in resultados if any(k.startswith('warning') for k in r)]
    if avisos:
        banner('AVISOS', c='-')
        for r in avisos:
            ws = {k: v for k, v in r.items() if k.startswith('warning')}
            print(f'  cod={r["cod"]} lote={r.get("lote_nome")}: {ws}')

    log_path = args.log_json
    if not log_path:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        modo = 'dryrun' if dry_run else 'real'
        log_path = str(
            _THIS.parent / 'auditoria'
            / f'log_ajuste_inv_{args.empresa}_{args.sinal}_{modo}_{ts}.json'
        )
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({
            'args': vars(args),
            'dry_run': dry_run,
            'empresa': args.empresa,
            'company_id': company_id,
            'location_id': location_id,
            'total': total,
            'contagem_status': dict(cont),
            'soma_planilha': soma,
            'soma_ok': soma_ok,
            'resultados': resultados,
        }, f, indent=2, default=str, ensure_ascii=False)
    print(f'\n  Log JSON: {log_path}')

    if dry_run:
        print('\n  DRY-RUN — nada gravado. Use --confirmar para aplicar.')

    falhas = sum(1 for r in resultados
                 if r['status'].startswith('FALHA') or r['status'].startswith('BLOQUEADO'))
    return 0 if falhas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
