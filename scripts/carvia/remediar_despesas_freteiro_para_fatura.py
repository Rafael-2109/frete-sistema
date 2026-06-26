#!/usr/bin/env python
# etapa: remediacao de pagamentos de freteiro lancados como Despesa (2026-06-25)
# doc-dono: app/carvia/FINANCEIRO.md (R11) + app/fretes/CLAUDE.md (Lancamento de Freteiros)
"""Remedia pagamentos de freteiro lancados como CarviaDespesa em vez de Fatura.

CONTEXTO (diagnostico Rafael 2026-06-25): antes da unificacao do Lancamento de
Freteiros, pagamentos a freteiros CarVia foram lancados manualmente como
`CarviaDespesa` (tipo OUTROS/SEGURO, "Despesa da Empresa") e conciliados contra
o extrato bancario (PAGO). Os `CarviaFrete` correspondentes ficaram PENDENTE
(valor_cte NULL) aparecendo no Lancamento de Freteiros. Este script reverte cada
caso para o estado CORRETO:

    desconciliar despesa -> DELETAR despesa (decisao Rafael: hard delete)
    -> gerar Fatura de Transportadora (espelho do Lancamento de Freteiros,
       valor = valor PAGO da linha de extrato, rateado entre os fretes
       proporcional ao valor_cotado) -> reconciliar a FT na MESMA linha.

Resultado por grupo = identico ao que teria acontecido se o fluxo unificado
tivesse sido usado: FT CONFERIDA + fretes FATURADO + FT.status_pagamento=PAGO,
sobre a mesma linha de extrato (saldo bancario inalterado).

ESCOPO CONSERVADOR: apenas os grupos com match CONFIRMADO por NOME do freteiro
(= razao_social da transportadora) E numero de NF presente na observacao da
despesa. Casos sem essa dupla confirmacao (ANDRE/ERICK RODRIGUES/FABIO/GILBERTO/
MARCIA — ver REVISAR_MANUAL) NAO sao tocados.

GARANTIAS:
  - dry-run e o DEFAULT (nada grava). --confirmar efetiva.
  - --prod aponta para DATABASE_URL_PROD (os dados reais estao no Render).
  - idempotente: grupo ja remediado (despesas deletadas + fretes faturados) e
    PULADO; estado misto/inconsistente e reportado e NAO tocado.
  - transacao POR GRUPO (commit isolado): falha de um grupo nao desfaz os outros.
  - cada grupo so age se TODAS as validacoes passarem (linha conciliada, valores
    batem, fretes pendentes do freteiro certo).

USO:
  # dry-run contra producao (recomendado primeiro — so leitura):
  python scripts/carvia/remediar_despesas_freteiro_para_fatura.py --prod
  # efetivar:
  python scripts/carvia/remediar_despesas_freteiro_para_fatura.py --prod --confirmar
  # 1 grupo so (pelo indice G#, p/ piloto):
  python scripts/carvia/remediar_despesas_freteiro_para_fatura.py --prod --confirmar --grupo 1
"""
import argparse
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

USUARIO = 'remediacao-freteiros@script'
USUARIO_NOME = 'Remediacao Freteiros (script 2026-06-25)'

# -----------------------------------------------------------------------------
# MAPA DE REMEDIACAO — 1 grupo por LINHA de extrato.
# Derivado do match read-only (nome do freteiro + NF na observacao da despesa),
# validado contra producao em 2026-06-25. valor_linha = valor PAGO (= |valor| da
# linha de extrato = soma das despesas conciliadas naquela linha).
# Campos sao re-validados em runtime; divergencia ABORTA o grupo.
# -----------------------------------------------------------------------------
GRUPOS = [
    # G, freteiro,            transp, linha,  valor,    despesas,      conciliacoes,      fretes
    (1,  'ABENER',            7,      1484,   1360.00,  [90],          [363],             [226, 227, 228, 229, 230, 246]),
    (2,  'ADILSON',           253,    1507,   2516.00,  [109],         [413],             [325, 334]),
    (3,  'AILTON',            300,    1562,   700.00,   [129],         [495],             [433]),
    (4,  'CESAR',             256,    1566,   520.00,   [131],         [491],             [389]),
    (5,  'ERICK RHUAN',       274,    1505,   3225.00,  [111],         [411],             [333]),
    (6,  'ERICK RHUAN',       274,    1561,   1550.00,  [135],         [496],             [449, 450, 451]),
    (7,  'FELIPE',            352,    1506,   350.00,   [110],         [412],             [345]),
    (8,  'HUDSON',            60,     1660,   170.24,   [154],         [591],             [452]),
    (9,  'ISRAEL',            186,    1662,   142.51,   [155],         [589],             [459]),
    (10, 'JOSE JESUS',        269,    1565,   350.00,   [134],         [492],             [393]),
    (11, 'LUIZ GUSTAVO',      81,     1467,   1440.00,  [67],          [345],             [202, 204]),
    (12, 'UMBERTO',           137,    1481,   1343.00,  [92],          [360],             [244]),
    (13, 'UMBERTO',           137,    1658,   243.41,   [157],         [593],             [562, 563]),
    (14, 'VANDERLEI',         140,    1534,   900.00,   [119],         [433],             [346]),
    (15, 'VANDERLEI',         140,    1560,   750.00,   [132],         [497],             [354, 355, 356, 357]),
    (16, 'WALDERIKS',         406,    1489,   2300.00,  [97, 98, 99],  [368, 369, 370],   [218, 219]),
    (17, 'WELINGTON',         183,    1468,   1500.00,  [68],          [346],             [184]),
    (18, 'WELINGTON',         183,    1483,   2050.00,  [93],          [362],             [232]),
    # --- 2a leva (2026-06-25): casos antes em REVISAR_MANUAL, confirmados ---
    # G19/G20: NF confere (FABIO=transposicao 37380<->37830; GILBERTO=0406/0399).
    # G21: ERICK sem NF, mas data da despesa (17/04) = criacao do frete 46 +
    #      unico frete pendente do freteiro — aprovado pelo Rafael 2026-06-25.
    (19, 'FABIO',             367,    1463,   190.00,   [66],          [341],             [175]),
    (20, 'GILBERTO',          240,    1482,   300.00,   [91],          [361],             [234, 233]),
    (21, 'ERICK RODRIGUES',   201,    1344,   500.00,   [54],          [298],             [46]),
]

# Casos NAO remediados — sem match confiavel (decisao final 2026-06-25):
REVISAR_MANUAL = [
    ('MARCIA REGINA',      'desp 60 (R$400) "FRETE CARVIA 08/05"; frete 101 cotado 40,27 (pago 10x, '
                           'sem NF) — Rafael decidiu NAO remediar (incerto)'),
    ('ANDRE SILVA BARROS', 'desp 130 (R$260) = "NFE 4537 COLETA MOTOS" — coleta de outra NF, '
                           'NAO e o frete 212 (NF 749). desp 43 (R$130) esta PENDENTE/nao conciliada'),
    ('RAFAEL ALVES',       'desp 39/53 (mar/abr) + 158 (NFs 38915,2010...) NAO intersectam os 14 '
                           'fretes pendentes do emb.6008 (jun, NFs 39138...) — sem match'),
]


def _ratear(valor_linha, fretes_cotado):
    """Rateia valor_linha entre os fretes proporcional ao valor_cotado.

    fretes_cotado: list[(frete_id, cotado)]. Retorna {frete_id: Decimal(2)}.
    Garante soma EXATA = valor_linha (ajuste do resto no ultimo). Se cotado_total
    <= 0 ou algum item ficaria 0, usa rateio IGUALITARIO (todos > 0).
    """
    from decimal import Decimal, ROUND_HALF_UP

    valor = Decimal(str(valor_linha)).quantize(Decimal('0.01'))
    n = len(fretes_cotado)
    cotado_total = sum(Decimal(str(c or 0)) for _, c in fretes_cotado)

    out = {}
    if cotado_total <= 0:
        base = (valor / n).quantize(Decimal('0.01'), ROUND_HALF_UP)
        for fid, _ in fretes_cotado:
            out[fid] = base
    else:
        for fid, c in fretes_cotado:
            out[fid] = (valor * Decimal(str(c or 0)) / cotado_total).quantize(
                Decimal('0.01'), ROUND_HALF_UP
            )
        # se algum ficou <= 0, cai p/ igualitario (emitir exige valor > 0)
        if any(v <= 0 for v in out.values()):
            base = (valor / n).quantize(Decimal('0.01'), ROUND_HALF_UP)
            out = {fid: base for fid, _ in fretes_cotado}

    # ajuste do resto no ultimo frete p/ fechar exato
    soma = sum(out.values())
    if soma != valor:
        ultimo = fretes_cotado[-1][0]
        out[ultimo] = (out[ultimo] + (valor - soma)).quantize(Decimal('0.01'))
    return out


def _classificar(grupo, db):
    """Retorna (estado, dados|motivo). estado in PENDENTE|FEITO|INCONSISTENTE|INVALIDO."""
    from decimal import Decimal
    from app.carvia.models import (
        CarviaDespesa, CarviaFrete, CarviaExtratoLinha, CarviaConciliacao,
    )
    (_g, _nome, transp_id, linha_id, valor_linha, desp_ids, conc_ids, frete_ids) = grupo
    valor_linha = Decimal(str(valor_linha)).quantize(Decimal('0.01'))

    despesas = {d: db.session.get(CarviaDespesa, d) for d in desp_ids}
    fretes = {f: db.session.get(CarviaFrete, f) for f in frete_ids}
    n_desp_vivas = sum(1 for v in despesas.values() if v is not None)
    n_frete_faturado = sum(
        1 for v in fretes.values() if v is not None and v.fatura_transportadora_id
    )

    # idempotencia: ja remediado
    if n_desp_vivas == 0 and n_frete_faturado == len(frete_ids):
        return 'FEITO', 'despesas deletadas e fretes faturados'
    # estado misto
    if n_desp_vivas not in (0, len(desp_ids)) or (
        0 < n_frete_faturado < len(frete_ids)
    ):
        return 'INCONSISTENTE', (
            f'{n_desp_vivas}/{len(desp_ids)} despesas vivas, '
            f'{n_frete_faturado}/{len(frete_ids)} fretes faturados'
        )

    # validacoes para PENDENTE
    erros = []
    linha = db.session.get(CarviaExtratoLinha, linha_id)
    if not linha:
        erros.append(f'linha {linha_id} inexistente')
    else:
        if abs(Decimal(str(linha.valor))) != valor_linha:
            erros.append(
                f'linha valor |{linha.valor}| != esperado {valor_linha}'
            )
    # despesas existem, PAGO, somam valor_linha
    soma_desp = Decimal('0')
    for d, obj in despesas.items():
        if not obj:
            erros.append(f'despesa {d} inexistente')
            continue
        if obj.status != 'PAGO':
            erros.append(f'despesa {d} status={obj.status} (esperado PAGO)')
        soma_desp += Decimal(str(obj.valor))
    if despesas and soma_desp != valor_linha:
        erros.append(f'soma despesas {soma_desp} != valor_linha {valor_linha}')
    # conciliacoes alvo existem, na linha certa, somam valor_linha
    soma_conc = Decimal('0')
    for c in conc_ids:
        conc = db.session.get(CarviaConciliacao, c)
        if not conc:
            erros.append(f'conciliacao {c} inexistente')
            continue
        if conc.extrato_linha_id != linha_id:
            erros.append(f'conciliacao {c} aponta linha {conc.extrato_linha_id} != {linha_id}')
        if conc.tipo_documento != 'despesa' or conc.documento_id not in desp_ids:
            erros.append(f'conciliacao {c} nao e despesa-alvo')
        soma_conc += Decimal(str(conc.valor_alocado))
    if soma_conc != valor_linha:
        erros.append(f'soma conciliacoes {soma_conc} != valor_linha {valor_linha}')
    # fretes elegiveis
    cotado = []
    for f, obj in fretes.items():
        if not obj:
            erros.append(f'frete {f} inexistente')
            continue
        if obj.transportadora_id != transp_id:
            erros.append(f'frete {f} transp {obj.transportadora_id} != {transp_id}')
        if obj.status == 'CANCELADO':
            erros.append(f'frete {f} CANCELADO')
        if obj.valor_cte is not None:
            erros.append(f'frete {f} ja tem valor_cte ({obj.valor_cte})')
        if obj.fatura_transportadora_id:
            erros.append(f'frete {f} ja vinculado FT {obj.fatura_transportadora_id}')
        cotado.append((f, obj.valor_cotado or 0))

    if erros:
        return 'INVALIDO', '; '.join(erros)
    return 'PENDENTE', {'linha': linha, 'cotado': cotado, 'valor_linha': valor_linha}


def _executar(grupo, dados, db):
    """Executa a remediacao de UM grupo (NAO comita — caller comita)."""
    from app.carvia.models import CarviaDespesa
    from app.carvia.services.financeiro.carvia_conciliacao_service import (
        CarviaConciliacaoService,
    )
    from app.carvia.services.financeiro.lancamento_freteiro_service import (
        emitir_fatura_freteiro_carvia,
    )
    (_g, _nome, transp_id, linha_id, _vl, desp_ids, conc_ids, _frete_ids) = grupo
    linha = dados['linha']
    valor_linha = dados['valor_linha']
    rateio = _ratear(valor_linha, dados['cotado'])

    # 1. desconciliar cada conciliacao despesa->linha (linha + despesa voltam PENDENTE)
    for c in conc_ids:
        CarviaConciliacaoService.desconciliar(c, USUARIO)

    # 2. DELETAR fisicamente as despesas (decisao Rafael — hard delete)
    for d in desp_ids:
        obj = db.session.get(CarviaDespesa, d)
        if obj:
            db.session.delete(obj)
    db.session.flush()

    # 3. gerar a Fatura de Transportadora (espelho Lancamento de Freteiros)
    data_venc = linha.data  # data do pagamento real
    itens = [{'frete_id': fid, 'valor_considerado': float(v)} for fid, v in rateio.items()]
    obs = (
        f'Remediacao 2026-06-25: substitui Despesa(s) #{",".join(map(str, desp_ids))} '
        f'(deletada — pagamento de freteiro lancado erroneamente como despesa) por '
        f'Fatura de Transportadora; pagamento ja conciliado na linha de extrato '
        f'#{linha_id}.'
    )
    res = emitir_fatura_freteiro_carvia(
        transportadora_id=transp_id,
        itens=itens,
        data_vencimento=data_venc,
        usuario_nome=USUARIO_NOME,
        observacoes=obs,
    )

    # 4. reconciliar a FT na MESMA linha (=> FT.status_pagamento = PAGO)
    CarviaConciliacaoService.conciliar(
        linha_id,
        [{
            'tipo_documento': 'fatura_transportadora',
            'documento_id': res['fatura_id'],
            'valor_alocado': float(valor_linha),
        }],
        USUARIO,
    )
    return res, rateio


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prod', action='store_true', help='usa DATABASE_URL_PROD')
    ap.add_argument('--confirmar', action='store_true', help='aplica (default: dry-run)')
    ap.add_argument('--grupo', type=int, default=None, help='roda so o grupo G# (piloto)')
    args = ap.parse_args()

    if args.prod:
        if not os.environ.get('DATABASE_URL_PROD'):
            sys.exit('ERRO: DATABASE_URL_PROD ausente no .env')
        os.environ['DATABASE_URL'] = os.environ['DATABASE_URL_PROD']

    from app import create_app, db
    app = create_app()

    grupos = [g for g in GRUPOS if args.grupo is None or g[0] == args.grupo]
    if not grupos:
        sys.exit(f'Grupo {args.grupo} nao existe (1..{len(GRUPOS)}).')

    modo = 'EXECUCAO (--confirmar)' if args.confirmar else 'DRY-RUN'
    print('=' * 78)
    print(f'REMEDIACAO Despesa-freteiro -> Fatura | {modo} | '
          f'{"PROD" if args.prod else "LOCAL"} | {len(grupos)} grupo(s)')
    print('=' * 78)

    contagem = {'FEITO': 0, 'PENDENTE': 0, 'INCONSISTENTE': 0, 'INVALIDO': 0,
                'EXECUTADO': 0, 'FALHA': 0}
    total_valor = 0.0

    with app.app_context():
        for grupo in grupos:
            (g, nome, transp_id, linha_id, valor_linha, desp_ids, conc_ids, frete_ids) = grupo
            estado, dados = _classificar(grupo, db)
            print(f'\n[G{g:>2}] {nome:<16} transp={transp_id} linha={linha_id} '
                  f'R$ {valor_linha:>9.2f} | despesas={desp_ids} fretes={frete_ids}')

            if estado != 'PENDENTE':
                contagem[estado] += 1
                tag = {'FEITO': 'JA REMEDIADO (skip)',
                       'INCONSISTENTE': 'ESTADO MISTO — NAO TOCADO',
                       'INVALIDO': 'VALIDACAO FALHOU — NAO TOCADO'}[estado]
                print(f'       -> {tag}: {dados}')
                continue

            contagem['PENDENTE'] += 1
            rateio = _ratear(dados['valor_linha'], dados['cotado'])
            print(f'       plano: desconciliar {conc_ids} -> DELETAR despesas {desp_ids} '
                  f'-> FT R$ {valor_linha:.2f} (venc {dados["linha"].data}) '
                  f'-> reconciliar linha {linha_id}')
            print(f'       rateio por frete (proporcional ao cotado): '
                  + ', '.join(f'{fid}=R${float(v):.2f}' for fid, v in rateio.items()))

            if not args.confirmar:
                total_valor += float(valor_linha)
                continue

            try:
                res, _ = _executar(grupo, dados, db)
                db.session.commit()
                contagem['EXECUTADO'] += 1
                total_valor += float(valor_linha)
                print(f'       OK: FT #{res["fatura_id"]} {res["numero_fatura"]} '
                      f'criada e conciliada ({res["fretes"]} fretes, '
                      f'{res["subcontratos_criados"]} subs).')
            except Exception as e:
                db.session.rollback()
                contagem['FALHA'] += 1
                print(f'       FALHA (rollback do grupo): {e}')

    print('\n' + '=' * 78)
    print('RESUMO:', ', '.join(f'{k}={v}' for k, v in contagem.items() if v))
    print(f'Valor {"processado" if args.confirmar else "a processar"}: R$ {total_valor:,.2f}')
    if REVISAR_MANUAL and args.grupo is None:
        print('\nFORA DE ESCOPO (revisar manualmente — match so por nome, NF nao confere):')
        for nome, motivo in REVISAR_MANUAL:
            print(f'  - {nome}: {motivo}')
    if not args.confirmar:
        print('\nDRY-RUN: nada gravado. Repita com --confirmar para efetivar.')
    print('=' * 78)


if __name__ == '__main__':
    main()
