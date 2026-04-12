#!/usr/bin/env python3
"""
Auditoria de dados historicos do modulo CarVia.

READ-ONLY — apenas identifica inconsistencias, nao modifica dados.

Verifica:
1. Operacoes FATURADO com CTe Complementar ou CustoEntrega ativos
2. NFs CANCELADA ainda em junctions (CarviaOperacaoNf) com operacao ativa
3. NFs CANCELADA em items de fatura
4. Documentos conciliados com movimentacao FC duplicada (conflito dual-path)
5. Subcontratos com tabela_frete_id apontando para tabela inativa
6. CarviaFrete.operacao_id apontando para operacao inexistente/cancelada
7. CarviaFrete.subcontrato_id (deprecated) ainda populado
8. Operacoes com fatura_cliente_id para fatura CANCELADA
9. Despesas tipo COMISSAO sem vinculo com CarviaComissaoFechamento
10. Fatura cliente.valor_total divergente da soma de ops+ctes_comp vinculados

Uso:
  source .venv/bin/activate
  python scripts/carvia/audit_dados_historicos.py
  python scripts/carvia/audit_dados_historicos.py --json      # output JSON
  python scripts/carvia/audit_dados_historicos.py --check 1,3 # apenas checks 1 e 3
"""

import argparse
import json
import sys
from pathlib import Path

# Root do projeto
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import func  # noqa: E402


def check_1_operacoes_faturadas_com_filhos_ativos():
    """Op FATURADO com CTe Complementar ou CustoEntrega ativos.

    Principio violado: fluxo unidirecional — filhos ativos bloqueiam mudancas
    no pai. Ops faturadas nao deveriam ter CE/CTe Comp em estados editaveis.
    """
    from app.carvia.models import (
        CarviaOperacao, CarviaCteComplementar, CarviaCustoEntrega,
    )

    problemas = []

    # Operacoes FATURADO com CTe Comp ativo
    q = db.session.query(
        CarviaOperacao.id,
        CarviaOperacao.cte_numero,
        func.count(CarviaCteComplementar.id).label('qtd_ativos'),
    ).join(
        CarviaCteComplementar,
        CarviaCteComplementar.operacao_id == CarviaOperacao.id,
    ).filter(
        CarviaOperacao.status == 'FATURADO',
        CarviaCteComplementar.status.in_(['RASCUNHO', 'EMITIDO']),
    ).group_by(CarviaOperacao.id, CarviaOperacao.cte_numero).all()

    for op_id, cte_num, qtd in q:
        problemas.append({
            'tipo': 'OP_FATURADO_COM_CTE_COMP_ATIVO',
            'operacao_id': op_id,
            'cte_numero': cte_num,
            'qtd_ctes_comp_ativos': qtd,
        })

    # Operacoes FATURADO com CustoEntrega ativo
    q = db.session.query(
        CarviaOperacao.id,
        CarviaOperacao.cte_numero,
        func.count(CarviaCustoEntrega.id).label('qtd_ativos'),
    ).join(
        CarviaCustoEntrega,
        CarviaCustoEntrega.operacao_id == CarviaOperacao.id,
    ).filter(
        CarviaOperacao.status == 'FATURADO',
        CarviaCustoEntrega.status == 'PENDENTE',
    ).group_by(CarviaOperacao.id, CarviaOperacao.cte_numero).all()

    for op_id, cte_num, qtd in q:
        problemas.append({
            'tipo': 'OP_FATURADO_COM_CUSTO_ENTREGA_PENDENTE',
            'operacao_id': op_id,
            'cte_numero': cte_num,
            'qtd_custos_pendentes': qtd,
        })

    return problemas


def check_2_nfs_canceladas_em_operacoes_ativas():
    """NFs CANCELADA ainda em junctions com operacao nao-CANCELADA.

    Principio violado: se NF foi cancelada, nao deveria estar em CTe ativo.
    """
    from app.carvia.models import CarviaNf, CarviaOperacao, CarviaOperacaoNf

    q = db.session.query(
        CarviaNf.id.label('nf_id'),
        CarviaNf.numero_nf,
        CarviaOperacao.id.label('op_id'),
        CarviaOperacao.cte_numero,
        CarviaOperacao.status.label('op_status'),
    ).join(
        CarviaOperacaoNf, CarviaOperacaoNf.nf_id == CarviaNf.id,
    ).join(
        CarviaOperacao, CarviaOperacao.id == CarviaOperacaoNf.operacao_id,
    ).filter(
        CarviaNf.status == 'CANCELADA',
        CarviaOperacao.status != 'CANCELADO',
    ).all()

    return [
        {
            'tipo': 'NF_CANCELADA_EM_OP_ATIVA',
            'nf_id': r.nf_id,
            'numero_nf': r.numero_nf,
            'operacao_id': r.op_id,
            'cte_numero': r.cte_numero,
            'op_status': r.op_status,
        }
        for r in q
    ]


def check_3_nfs_canceladas_em_faturas():
    """NFs CANCELADA em items de fatura (cliente ou transportadora).

    A fatura pode estar historicamente correta, mas a NF cancelada
    cria inconsistencia de display/relatorio.
    """
    from app.carvia.models import (
        CarviaNf, CarviaFaturaCliente, CarviaFaturaClienteItem,
        CarviaFaturaTransportadora, CarviaFaturaTransportadoraItem,
    )

    problemas = []

    # Fatura cliente
    q = db.session.query(
        CarviaNf.id, CarviaNf.numero_nf, CarviaFaturaCliente.numero_fatura,
    ).join(
        CarviaFaturaClienteItem, CarviaFaturaClienteItem.nf_id == CarviaNf.id,
    ).join(
        CarviaFaturaCliente,
        CarviaFaturaClienteItem.fatura_cliente_id == CarviaFaturaCliente.id,
    ).filter(CarviaNf.status == 'CANCELADA').all()

    for nf_id, nf_num, fat_num in q:
        problemas.append({
            'tipo': 'NF_CANCELADA_EM_FATURA_CLIENTE',
            'nf_id': nf_id,
            'numero_nf': nf_num,
            'numero_fatura': fat_num,
        })

    # Fatura transportadora
    q = db.session.query(
        CarviaNf.id, CarviaNf.numero_nf, CarviaFaturaTransportadora.numero_fatura,
    ).join(
        CarviaFaturaTransportadoraItem,
        CarviaFaturaTransportadoraItem.nf_id == CarviaNf.id,
    ).join(
        CarviaFaturaTransportadora,
        CarviaFaturaTransportadoraItem.fatura_transportadora_id == CarviaFaturaTransportadora.id,
    ).filter(CarviaNf.status == 'CANCELADA').all()

    for nf_id, nf_num, fat_num in q:
        problemas.append({
            'tipo': 'NF_CANCELADA_EM_FATURA_TRANSP',
            'nf_id': nf_id,
            'numero_nf': nf_num,
            'numero_fatura': fat_num,
        })

    return problemas


def check_4_docs_conciliados_com_fc_duplicado():
    """Documentos com ContaMovimentacao E Conciliacao ativa (dual-path).

    Principio violado: Conciliacao e SOT, FC deve respeitar.
    Estados dual-path podem estar presos por guards cruzados.
    """
    from app.carvia.models import CarviaConciliacao, CarviaContaMovimentacao

    q = db.session.query(
        CarviaContaMovimentacao.tipo_doc,
        CarviaContaMovimentacao.doc_id,
        func.count(CarviaConciliacao.id).label('qtd_conc'),
    ).join(
        CarviaConciliacao,
        db.and_(
            CarviaConciliacao.tipo_documento == CarviaContaMovimentacao.tipo_doc,
            CarviaConciliacao.documento_id == CarviaContaMovimentacao.doc_id,
        ),
    ).filter(
        CarviaContaMovimentacao.tipo_doc.in_([
            'fatura_cliente', 'fatura_transportadora',
            'despesa', 'custo_entrega', 'receita',
        ])
    ).group_by(
        CarviaContaMovimentacao.tipo_doc, CarviaContaMovimentacao.doc_id,
    ).all()

    return [
        {
            'tipo': 'DOC_DUAL_PATH_FC_E_CONCILIACAO',
            'tipo_doc': r.tipo_doc,
            'doc_id': r.doc_id,
            'qtd_conciliacoes': r.qtd_conc,
        }
        for r in q
    ]


def check_5_subs_com_tabela_inativa():
    """Subcontratos com tabela_frete_id apontando para tabela inativa."""
    from app.carvia.models import CarviaSubcontrato
    from app.tabelas.models import TabelaFrete

    q = db.session.query(
        CarviaSubcontrato.id,
        CarviaSubcontrato.cte_numero,
        TabelaFrete.id.label('tabela_id'),
        TabelaFrete.nome_tabela,
    ).join(
        TabelaFrete, TabelaFrete.id == CarviaSubcontrato.tabela_frete_id,
    ).filter(
        CarviaSubcontrato.status.notin_(['CANCELADO', 'FATURADO', 'CONFERIDO']),
        TabelaFrete.ativo.is_(False),
    ).all()

    return [
        {
            'tipo': 'SUB_COM_TABELA_INATIVA',
            'sub_id': r.id,
            'cte_numero': r.cte_numero,
            'tabela_id': r.tabela_id,
            'nome_tabela': r.nome_tabela,
        }
        for r in q
    ]


def check_6_carvia_frete_operacao_inexistente():
    """CarviaFrete.operacao_id apontando para operacao inexistente."""
    from app.carvia.models import CarviaFrete, CarviaOperacao

    # Subquery: IDs validos
    ids_validos = db.session.query(CarviaOperacao.id).subquery()

    q = db.session.query(
        CarviaFrete.id,
        CarviaFrete.operacao_id,
    ).filter(
        CarviaFrete.operacao_id.isnot(None),
        ~CarviaFrete.operacao_id.in_(db.session.query(ids_validos.c.id)),
    ).all()

    return [
        {
            'tipo': 'CARVIA_FRETE_OPERACAO_INEXISTENTE',
            'frete_id': r.id,
            'operacao_id_fk_pendente': r.operacao_id,
        }
        for r in q
    ]


def check_7_carvia_frete_subcontrato_id_deprecated():
    """CarviaFrete.subcontrato_id (deprecated) ainda populado."""
    from app.carvia.models import CarviaFrete

    q = db.session.query(
        CarviaFrete.id, CarviaFrete.subcontrato_id,
    ).filter(CarviaFrete.subcontrato_id.isnot(None)).all()

    return [
        {
            'tipo': 'CARVIA_FRETE_SUBCONTRATO_ID_DEPRECATED',
            'frete_id': r.id,
            'subcontrato_id': r.subcontrato_id,
        }
        for r in q
    ]


def check_8_operacao_com_fatura_cancelada():
    """CarviaOperacao com fatura_cliente_id para fatura CANCELADA."""
    from app.carvia.models import CarviaOperacao, CarviaFaturaCliente

    q = db.session.query(
        CarviaOperacao.id,
        CarviaOperacao.cte_numero,
        CarviaOperacao.status,
        CarviaFaturaCliente.numero_fatura,
    ).join(
        CarviaFaturaCliente,
        CarviaOperacao.fatura_cliente_id == CarviaFaturaCliente.id,
    ).filter(CarviaFaturaCliente.status == 'CANCELADA').all()

    return [
        {
            'tipo': 'OP_COM_FATURA_CANCELADA',
            'operacao_id': r.id,
            'cte_numero': r.cte_numero,
            'op_status': r.status,
            'numero_fatura_cancelada': r.numero_fatura,
        }
        for r in q
    ]


def check_9_despesas_comissao_orfas():
    """Despesas tipo COMISSAO sem vinculo com CarviaComissaoFechamento."""
    from app.carvia.models import CarviaDespesa, CarviaComissaoFechamento

    ids_fechamentos = db.session.query(
        CarviaComissaoFechamento.despesa_id,
    ).filter(CarviaComissaoFechamento.despesa_id.isnot(None)).subquery()

    q = db.session.query(
        CarviaDespesa.id, CarviaDespesa.tipo_despesa, CarviaDespesa.valor,
    ).filter(
        CarviaDespesa.tipo_despesa == 'COMISSAO',
        ~CarviaDespesa.id.in_(db.session.query(ids_fechamentos.c.despesa_id)),
    ).all()

    return [
        {
            'tipo': 'DESPESA_COMISSAO_ORFA',
            'despesa_id': r.id,
            'valor': float(r.valor or 0),
        }
        for r in q
    ]


def check_10_fatura_valor_divergente():
    """Fatura cliente.valor_total divergente da soma de ops+ctes_comp vinculados.

    Nao e necessariamente bug — fatura e independente por design. Mas grandes
    divergencias (>5%) podem indicar problemas.
    """
    from app.carvia.models import (
        CarviaFaturaCliente, CarviaOperacao, CarviaCteComplementar,
    )

    problemas = []

    faturas = CarviaFaturaCliente.query.filter(
        CarviaFaturaCliente.status.in_(['PENDENTE', 'PAGA']),
    ).all()

    for fatura in faturas:
        soma_ops = db.session.query(
            func.coalesce(func.sum(CarviaOperacao.cte_valor), 0)
        ).filter(CarviaOperacao.fatura_cliente_id == fatura.id).scalar() or 0

        soma_comp = db.session.query(
            func.coalesce(func.sum(CarviaCteComplementar.cte_valor), 0)
        ).filter(CarviaCteComplementar.fatura_cliente_id == fatura.id).scalar() or 0

        soma_total = float(soma_ops) + float(soma_comp)
        valor_fatura = float(fatura.valor_total or 0)

        if valor_fatura == 0 and soma_total == 0:
            continue

        divergencia = abs(valor_fatura - soma_total)
        percentual = (divergencia / valor_fatura * 100) if valor_fatura > 0 else 100

        if percentual > 5:  # Tolerancia de 5%
            problemas.append({
                'tipo': 'FATURA_VALOR_DIVERGENTE',
                'fatura_id': fatura.id,
                'numero_fatura': fatura.numero_fatura,
                'valor_fatura': valor_fatura,
                'soma_calculada': round(soma_total, 2),
                'divergencia': round(divergencia, 2),
                'percentual': round(percentual, 2),
            })

    return problemas


CHECKS = [
    ('1', 'Operacoes FATURADO com filhos ativos', check_1_operacoes_faturadas_com_filhos_ativos),
    ('2', 'NFs CANCELADA em operacoes ativas', check_2_nfs_canceladas_em_operacoes_ativas),
    ('3', 'NFs CANCELADA em faturas', check_3_nfs_canceladas_em_faturas),
    ('4', 'Docs com dual-path FC + Conciliacao', check_4_docs_conciliados_com_fc_duplicado),
    ('5', 'Subs com tabela_frete inativa', check_5_subs_com_tabela_inativa),
    ('6', 'CarviaFrete com operacao_id inexistente', check_6_carvia_frete_operacao_inexistente),
    ('7', 'CarviaFrete.subcontrato_id deprecated', check_7_carvia_frete_subcontrato_id_deprecated),
    ('8', 'Operacoes com fatura CANCELADA', check_8_operacao_com_fatura_cancelada),
    ('9', 'Despesas COMISSAO orfas', check_9_despesas_comissao_orfas),
    ('10', 'Faturas com valor divergente (>5%)', check_10_fatura_valor_divergente),
]


def main():
    parser = argparse.ArgumentParser(
        description='Auditoria de dados historicos do modulo CarVia (READ-ONLY).',
    )
    parser.add_argument(
        '--json', action='store_true',
        help='Output em JSON (machine-readable)',
    )
    parser.add_argument(
        '--check', type=str,
        help='Rodar apenas checks especificos (ex: 1,3,5)',
    )
    args = parser.parse_args()

    checks_a_rodar = CHECKS
    if args.check:
        ids_filtro = set(args.check.split(','))
        checks_a_rodar = [c for c in CHECKS if c[0] in ids_filtro]

    app = create_app()
    with app.app_context():
        resultado = {}
        total_problemas = 0

        for check_id, check_nome, check_func in checks_a_rodar:
            try:
                problemas = check_func()
            except Exception as e:
                resultado[check_id] = {
                    'nome': check_nome,
                    'erro': str(e),
                    'problemas': [],
                }
                continue

            resultado[check_id] = {
                'nome': check_nome,
                'problemas': problemas,
                'qtd': len(problemas),
            }
            total_problemas += len(problemas)

        if args.json:
            print(json.dumps(resultado, indent=2, default=str))
        else:
            print('=' * 70)
            print('AUDITORIA DE DADOS HISTORICOS — MODULO CARVIA')
            print('=' * 70)
            print()
            for check_id, data in resultado.items():
                nome = data['nome']
                if 'erro' in data:
                    print(f'[{check_id}] {nome} — ERRO: {data["erro"]}')
                    continue
                qtd = data['qtd']
                status = 'OK' if qtd == 0 else f'{qtd} problema(s)'
                print(f'[{check_id}] {nome}: {status}')
                if qtd > 0 and qtd <= 10:
                    for p in data['problemas']:
                        print(f'    → {p}')
                elif qtd > 10:
                    for p in data['problemas'][:5]:
                        print(f'    → {p}')
                    print(f'    ... (+{qtd - 5} outros — use --json para lista completa)')
            print()
            print('-' * 70)
            print(f'TOTAL: {total_problemas} inconsistencia(s) identificada(s)')
            print('-' * 70)

        return 0 if total_problemas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
