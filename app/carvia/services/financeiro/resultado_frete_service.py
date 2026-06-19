"""ResultadoFreteService — resultado (receita − custo) por frete, rateado por moto.

Receita = CarviaOperacao.cte_valor; custo = Σ subcontratos da operacao + coleta.
Receita e custo descem a NF pela MESMA base (cascata motos→peso→nº NFs) — por
construcao a soma fecha em qualquer eixo de resumo (CTe/embarque/UF-mes).
"""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func

from app import db
from app.carvia.services.financeiro.gerencial_service import (
    _build_moto_count_per_nf_subquery,
)

ZERO = Decimal('0')
CENT = Decimal('0.01')


def _ratear(valor_total, nfs, key):
    """Distribui valor_total entre nfs (list de dict com 'motos','peso') -> nf[key].

    Cascata: 1 NF=direto; senao Motos; senao Peso; senao Qtd NFs. Ajuste de
    centavos na 1a NF. Espelha gerencial_service._aplicar_rateio_itens (NF-level).
    """
    if not nfs:
        return
    total_motos = sum(n['motos'] for n in nfs)
    total_peso = sum(n['peso'] for n in nfs)
    if len(nfs) == 1:
        nfs[0][key] = valor_total
        return
    if total_motos > 0:
        for n in nfs:
            prop = Decimal(n['motos']) / Decimal(total_motos)
            n[key] = (valor_total * prop).quantize(CENT, ROUND_HALF_UP)
    elif total_peso > 0:
        for n in nfs:
            prop = n['peso'] / total_peso
            n[key] = (valor_total * prop).quantize(CENT, ROUND_HALF_UP)
    else:
        v = (valor_total / len(nfs)).quantize(CENT, ROUND_HALF_UP)
        for n in nfs:
            n[key] = v
    soma = sum(n[key] for n in nfs)
    diff = valor_total - soma
    if diff != 0:
        nfs[0][key] += diff


class ResultadoFreteService:

    def detalhe_por_nf(self, data_inicio, data_fim, uf=None):
        from app.carvia.models import (
            CarviaNf, CarviaOperacao, CarviaOperacaoNf, CarviaSubcontrato,
            CarviaColeta, CarviaColetaNf, CarviaFrete,
        )
        moto_nf = _build_moto_count_per_nf_subquery('moto_nf_rf')

        q = (
            db.session.query(
                CarviaNf.id.label('nf_id'),
                CarviaNf.numero_nf,
                CarviaNf.cidade_destinatario,
                CarviaNf.uf_destinatario,
                CarviaNf.peso_bruto,
                CarviaOperacao.id.label('operacao_id'),
                CarviaOperacao.cte_numero,
                CarviaOperacao.cte_valor,
                CarviaOperacao.cte_data_emissao,
                func.coalesce(moto_nf.c.qtd_motos, 0).label('qtd_motos_nf'),
            )
            .join(CarviaOperacaoNf, CarviaOperacaoNf.nf_id == CarviaNf.id)
            .join(CarviaOperacao, CarviaOperacao.id == CarviaOperacaoNf.operacao_id)
            .outerjoin(moto_nf, moto_nf.c.nf_id == CarviaNf.id)
            .filter(
                CarviaNf.status == 'ATIVA',
                CarviaOperacao.status != 'CANCELADO',
                CarviaOperacao.cte_data_emissao.isnot(None),
                CarviaOperacao.cte_data_emissao >= data_inicio,
                CarviaOperacao.cte_data_emissao <= data_fim,
            )
        )
        if uf:
            q = q.filter(CarviaNf.uf_destinatario == uf)
        rows = q.all()
        if not rows:
            return []

        op_ids = {r.operacao_id for r in rows}
        nf_ids = {r.nf_id for r in rows}

        # custo subcontrato por operacao (SUM; flag REAL se houver cte_valor)
        sub_por_op = {}
        for s in (db.session.query(CarviaSubcontrato)
                  .filter(CarviaSubcontrato.operacao_id.in_(op_ids)).all()):
            valor = s.cte_valor if s.cte_valor is not None else (
                s.valor_acertado if s.valor_acertado is not None else s.valor_cotado)
            acc, real = sub_por_op.get(s.operacao_id, (ZERO, False))
            sub_por_op[s.operacao_id] = (
                acc + (Decimal(str(valor)) if valor else ZERO),
                real or (s.cte_valor is not None),
            )

        # embarque por operacao (eixo)
        emb_por_op = {}
        for op_id, emb_id in (db.session.query(CarviaFrete.operacao_id, CarviaFrete.embarque_id)
                              .filter(CarviaFrete.operacao_id.in_(op_ids),
                                      CarviaFrete.embarque_id.isnot(None)).all()):
            emb_por_op.setdefault(op_id, emb_id)

        # coleta: rateio do valor_coleta pela qtd_motos das linhas (papel de pao)
        coleta_de_nf = {}
        for ln in (db.session.query(CarviaColetaNf)
                   .filter(CarviaColetaNf.carvia_nf_id.in_(nf_ids)).all()):
            coleta_de_nf[ln.carvia_nf_id] = ln.coleta_id
        coleta_ids = set(coleta_de_nf.values())
        coleta_valor, coleta_total_motos, linha_motos = {}, defaultdict(int), {}
        if coleta_ids:
            for c in (db.session.query(CarviaColeta)
                      .filter(CarviaColeta.id.in_(coleta_ids)).all()):
                coleta_valor[c.id] = Decimal(str(c.valor_coleta)) if c.valor_coleta else ZERO
            for ln in (db.session.query(CarviaColetaNf)
                       .filter(CarviaColetaNf.coleta_id.in_(coleta_ids)).all()):
                coleta_total_motos[ln.coleta_id] += (ln.qtd_motos or 0)
                if ln.carvia_nf_id:
                    linha_motos[ln.carvia_nf_id] = ln.qtd_motos or 0

        # agrupar por operacao e ratear receita + custo subcontrato
        by_op = defaultdict(list)
        for r in rows:
            by_op[r.operacao_id].append(r)

        detalhe = []
        for op_id, op_rows in by_op.items():
            cte_valor = Decimal(str(op_rows[0].cte_valor or 0))
            sub_total, sub_real = sub_por_op.get(op_id, (ZERO, False))
            nfs = [{'r': r, 'motos': int(r.qtd_motos_nf or 0),
                    'peso': Decimal(str(r.peso_bruto or 0))} for r in op_rows]
            _ratear(cte_valor, nfs, 'receita')
            _ratear(sub_total, nfs, 'sub')
            for n in nfs:
                r = n['r']
                custo_coleta = ZERO
                cid = coleta_de_nf.get(r.nf_id)
                if cid and coleta_total_motos.get(cid):
                    custo_coleta = (
                        coleta_valor.get(cid, ZERO)
                        * Decimal(linha_motos.get(r.nf_id, 0))
                        / Decimal(coleta_total_motos[cid])
                    ).quantize(CENT, ROUND_HALF_UP)
                receita, custo_sub = n['receita'], n['sub']
                resultado = receita - custo_sub - custo_coleta
                motos = n['motos']
                detalhe.append({
                    'nf_id': r.nf_id, 'numero_nf': r.numero_nf,
                    'cidade': r.cidade_destinatario, 'uf': r.uf_destinatario,
                    'operacao_id': op_id, 'cte_numero': r.cte_numero,
                    'data_cte': r.cte_data_emissao,
                    'embarque_id': emb_por_op.get(op_id),
                    'motos': motos,
                    'receita': float(receita),
                    'custo_sub': float(custo_sub),
                    'custo_sub_flag': 'REAL' if sub_real else ('ESTIMADO' if sub_total > 0 else '—'),
                    'custo_coleta': float(custo_coleta),
                    'resultado': float(resultado),
                    'resultado_moto': float((resultado / motos).quantize(CENT, ROUND_HALF_UP)) if motos > 0 else None,
                })
        detalhe.sort(key=lambda d: d['resultado'])  # piores primeiro
        return detalhe

    def resumo(self, eixo, data_inicio, data_fim, uf=None):
        det = self.detalhe_por_nf(data_inicio, data_fim, uf)
        grupos = {}
        for d in det:
            if eixo == 'embarque':
                chave = d['embarque_id'] or 'sem'
                label = f"Embarque #{d['embarque_id']}" if d['embarque_id'] else 'Sem embarque'
            elif eixo == 'uf_mes':
                mes = d['data_cte'].strftime('%Y-%m') if d['data_cte'] else 'sem-data'
                chave = (d['uf'], mes)
                label = f"{d['uf'] or '—'} / {mes}"
            else:  # cte
                chave = d['operacao_id']
                label = d['cte_numero'] or f"op {d['operacao_id']}"
            g = grupos.setdefault(chave, {
                'label': label, 'receita': 0.0, 'custo_sub': 0.0,
                'custo_coleta': 0.0, 'resultado': 0.0, 'motos': 0,
            })
            g['receita'] += d['receita']
            g['custo_sub'] += d['custo_sub']
            g['custo_coleta'] += d['custo_coleta']
            g['resultado'] += d['resultado']
            g['motos'] += d['motos']
        out = []
        for g in grupos.values():
            motos = g['motos']
            custo_total = g['custo_sub'] + g['custo_coleta']
            out.append({
                **g,
                'custo_total': round(custo_total, 2),
                'receita_moto': round(g['receita'] / motos, 2) if motos else None,
                'custo_moto': round(custo_total / motos, 2) if motos else None,
                'resultado_moto': round(g['resultado'] / motos, 2) if motos else None,
                'margem_pct': round(g['resultado'] / g['receita'] * 100, 1) if g['receita'] else None,
            })
        out.sort(key=lambda x: x['resultado'])
        return out
