"""fat_lf_02_carregar.py — Carrega RELACAO FATURAMENTO LF.xlsx em AjusteEstoqueInventario.

Ciclo ISOLADO: FATURAMENTO_LF_2026_05_20 (nao colide com os 1742 registros
existentes de INVENTARIO_2026_05 onda-1).

Mapeamento de acao (TIPO FATURAMENTO + tipo_produto = 1o digito do cod):
  INDUSTRIALIZAÇÃO            -> INDUSTRIALIZACAO_FB_LF  (FB->LF, fp 25, CFOP 5901)
  PERDA  tipo 1/2/3           -> PERDA_LF_FB             (LF->FB, fp 91, CFOP 5903)
  PERDA  tipo 4/6 (demais)    -> DEV_LF_FB               (LF->FB, fp 89, CFOP 5949) [user 2026-05-20]

Agrega por (cod, TIPO FATURAMENTO) -> 1 ajuste por cod (soma QTD).
Lote vazio no Excel = placeholder 'P-15/05' (user 2026-05-20) — informativo,
nao afeta FIFO de origem.
lote_destino: INDUSTR -> Para-Lote (alvo na LF) ; PERDA/DEV -> 'MIGRACAO' (consolidador FB).

Classifica viabilidade (estoque real vs QTD) e SO cria ajustes executaveis:
  - OK            : estoque na location principal (LF/Estoque 42 ou FB/Estoque 8) >= QTD -> cria
  - FORA_ESTOQUE  : estoque total da empresa >= QTD mas em sub-locais -> cria + marca p/ pre-stage
  - SEM_STOCK     : estoque total = 0 -> NAO cria (reporta)
  - SEM_PID       : produto nao existe no Odoo -> NAO cria (reporta)

Tambem limpa barcodes invalidos (G035) de todos os cods criados.

Uso:
  python scripts/inventario_2026_05/fat_lf_02_carregar.py            # dry-run (so classifica)
  python scripts/inventario_2026_05/fat_lf_02_carregar.py --confirmar  # cria registros + limpa barcodes
"""
import argparse
import json
import os
import sys
import warnings
from collections import defaultdict
from decimal import Decimal

warnings.simplefilter('ignore')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pandas as pd  # noqa: E402

from app import create_app, db  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402
from app.odoo.utils.gtin_validator import clear_invalid_barcodes  # noqa: E402
from app.utils.timezone import agora_utc_naive  # noqa: E402

XLSX = '/mnt/c/Users/rafael.nascimento/Downloads/RELACAO FATURAMENTO LF.xlsx'
CICLO = 'FATURAMENTO_LF_2026_05_20'
CLASSIF_JSON = '/tmp/fat_lf_classificacao.json'
LF_ESTOQUE = 42
FB_ESTOQUE = 8
PLACEHOLDER_LOTE = 'P-15/05'


def mapear_acao(tipo_fat: str, tipo_prod: int):
    """(acao_decidida, company_origem) a partir do tipo de faturamento + tipo de produto."""
    if tipo_fat == 'INDUSTRIALIZAÇÃO':
        return 'INDUSTRIALIZACAO_FB_LF', 1   # FB->LF
    # PERDA
    if tipo_prod in (1, 2, 3):
        return 'PERDA_LF_FB', 5              # LF->FB
    return 'DEV_LF_FB', 5                    # tipo 4/6/demais: LF->FB dev-industrializacao


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true', help='cria registros e limpa barcodes')
    args = ap.parse_args()

    df = pd.read_excel(XLSX)
    df['cod'] = df['cod'].astype(str).str.strip()
    # Excluir cod malformado (nao numerico, ex "29" com nan? na verdade "29" e numerico mas invalido)
    df['tipo_fat'] = df['TIPO FATURAMENTO'].astype(str).str.strip()

    # Agregar por (cod, tipo_fat) -> soma QTD ; guardar Para-Lote dominante (INDUSTR)
    agg = (df.groupby(['cod', 'tipo_fat'])
             .agg(qtd=('QTD', 'sum'),
                  para_lote=('Para - Lote', lambda s: s.dropna().astype(str).iloc[0] if s.dropna().size else PLACEHOLDER_LOTE),
                  nome=('nome_produto', 'first'))
             .reset_index())

    app = create_app()
    with app.app_context():
        from app.odoo.models.ajuste_estoque_inventario import AjusteEstoqueInventario
        odoo = get_odoo_connection()

        # Locations internal por company
        locs = odoo.search_read('stock.location',
                                [['usage', '=', 'internal'], ['company_id', 'in', [1, 5]]],
                                ['id', 'company_id'])
        loc_company = {l['id']: (l['company_id'][0] if l.get('company_id') else None) for l in locs}

        # Resolver pids
        cods = sorted(df['cod'].unique().tolist())
        prod = odoo.search_read('product.product', [['default_code', 'in', cods]],
                                ['id', 'default_code', 'standard_price'])
        cod_pid = {p['default_code']: p['id'] for p in prod}
        pid_cod = {p['id']: p['default_code'] for p in prod}
        cod_custo = {p['default_code']: abs(float(p.get('standard_price') or 0)) or 0.01 for p in prod}

        # Estoque livre por (cod, location principal vs total empresa)
        pids = list(pid_cod.keys())
        quants = odoo.search_read('stock.quant',
                                  [['product_id', 'in', pids],
                                   ['quantity', '!=', 0]],
                                  ['product_id', 'location_id', 'quantity', 'reserved_quantity'])
        # empresa de origem por cod depende da acao (calculada por linha abaixo)
        quants_por_cod = defaultdict(list)
        for q in quants:
            cod = pid_cod.get(q['product_id'][0])
            if cod:
                quants_por_cod[cod].append(q)

        criados = 0
        classif = {'OK': [], 'FORA_ESTOQUE': [], 'SEM_STOCK': [], 'SEM_PID': []}
        prestage = {}  # cod -> {company, principal_loc, faltam, fontes:{loc:qty}}

        # Idempotencia: limpar ciclo antes de recriar (so em --confirmar)
        if args.confirmar:
            n_del = AjusteEstoqueInventario.query.filter_by(ciclo=CICLO).delete()
            db.session.commit()
            print(f'  Limpou {n_del} registros pre-existentes do ciclo {CICLO}')

        for _, r in agg.iterrows():
            cod = r['cod']
            tipo_fat = r['tipo_fat']
            qtd = float(r['qtd'])
            if not cod.isdigit():
                classif['SEM_PID'].append({'cod': cod, 'qtd': qtd, 'motivo': 'cod nao numerico'})
                continue
            tipo_prod = int(cod[0])
            acao, comp_origem = mapear_acao(tipo_fat, tipo_prod)
            principal_loc = FB_ESTOQUE if comp_origem == 1 else LF_ESTOQUE

            if cod not in cod_pid:
                classif['SEM_PID'].append({'cod': cod, 'qtd': qtd})
                continue

            # estoque na empresa de origem
            qp = 0.0   # principal
            qt = 0.0   # total empresa
            locfont = {}
            for q in quants_por_cod.get(cod, []):
                lid = q['location_id'][0]
                if loc_company.get(lid) != comp_origem:
                    continue
                livre = float(q['quantity']) - float(q.get('reserved_quantity') or 0)
                if livre == 0:
                    continue
                qt += livre
                locfont[lid] = locfont.get(lid, 0) + livre
                if lid == principal_loc:
                    qp += livre

            if qt <= 0.5:
                classif['SEM_STOCK'].append({'cod': cod, 'qtd': qtd, 'acao': acao})
                continue

            # lote_destino
            if acao == 'INDUSTRIALIZACAO_FB_LF':
                lote_dest = str(r['para_lote']) if r['para_lote'] and str(r['para_lote']) != 'nan' else PLACEHOLDER_LOTE
            else:
                lote_dest = 'MIGRACAO'

            cat = 'OK' if qp >= qtd - 0.5 else 'FORA_ESTOQUE'
            classif[cat].append({'cod': cod, 'qtd': qtd, 'acao': acao,
                                 'principal': round(qp, 2), 'total': round(qt, 2)})
            if cat == 'FORA_ESTOQUE':
                # quanto falta na principal e de quais sub-locais tirar
                prestage[cod] = {
                    'company': comp_origem,
                    'principal_loc': principal_loc,
                    'faltam': round(qtd - qp, 2),
                    'fontes': {str(lid): round(v, 2) for lid, v in locfont.items()
                               if lid != principal_loc},
                }

            if args.confirmar:
                aj = AjusteEstoqueInventario(
                    ciclo=CICLO,
                    cod_produto=cod,
                    tipo_produto=tipo_prod,
                    company_id=comp_origem,
                    qtd_inventario=Decimal(str(qtd)),
                    qtd_odoo=Decimal('0'),
                    qtd_ajuste=Decimal(str(qtd if acao == 'INDUSTRIALIZACAO_FB_LF' else -qtd)),
                    custo_medio=Decimal(str(cod_custo.get(cod, 0.01))),
                    acao_decidida=acao,
                    lote_destino=lote_dest,
                    status='APROVADO',
                    aprovado_em=agora_utc_naive(),
                    aprovado_por='claude_fat_lf',
                    fase_pipeline=None,
                    criado_por='claude_fat_lf',
                )
                db.session.add(aj)
                criados += 1

        if args.confirmar:
            db.session.commit()
            print(f'  CRIADOS {criados} ajustes no ciclo {CICLO}')
            # G035: limpar barcodes invalidos dos cods criados
            cods_criados = [c['cod'] for c in classif['OK'] + classif['FORA_ESTOQUE']]
            n_bc = clear_invalid_barcodes(odoo, cods_produto=cods_criados)
            print(f'  G035: {n_bc} barcodes invalidos limpos (set False)')

        # Resumo
        print('\n=== CLASSIFICACAO ===')
        for k in ('OK', 'FORA_ESTOQUE', 'SEM_STOCK', 'SEM_PID'):
            itens = classif[k]
            print(f'  {k}: {len(itens)}')
            if k in ('SEM_STOCK', 'SEM_PID'):
                for it in itens:
                    print(f'      {it}')
        with open(CLASSIF_JSON, 'w') as f:
            json.dump({'classif': classif, 'prestage': prestage}, f, indent=2, default=str)
        print(f'\n  Classificacao salva em {CLASSIF_JSON}')
        print(f'  Produtos p/ pre-stage (FORA_ESTOQUE): {len(prestage)}')


if __name__ == '__main__':
    main()
