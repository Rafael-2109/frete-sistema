"""
Rotas de Exportacao Excel CarVia — Todas as entidades
"""

import logging
from collections import defaultdict
from datetime import datetime
from io import BytesIO

import pandas as pd
from flask import request, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.carvia.models import (
    CarviaNf, CarviaNfItem, CarviaOperacao, CarviaOperacaoNf,
    CarviaSubcontrato, CarviaCteComplementar,
    CarviaCustoEntrega, CarviaFaturaCliente,
    CarviaFaturaTransportadora, CarviaDespesa,
    CarviaReceita,
    CarviaModeloMoto, CarviaCategoriaMoto,
    CarviaCidadeAtendida, CarviaTabelaFrete,
    CarviaGrupoCliente, CarviaPrecoCategoriaMoto,
    CarviaComissaoFechamento, CarviaComissaoFechamentoCte,
    CarviaConciliacao, CarviaExtratoLinha,
)
from app.carvia.utils.excel_export_helper import (
    Campo, ColunaGrupo, gerar_excel_duplo_cabecalho, grupo_dinamico,
)
from app.carvia.utils.tomador import tomador_label_para_export
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


# Mapa modFrete SEFAZ -> label curto para Excel
_MOD_FRETE_LABEL = {
    '0': 'CIF',
    '1': 'FOB',
    '2': 'Terceiros',
    '3': 'Proprio-Rem',
    '4': 'Proprio-Dest',
    '9': 'Sem Transp',
}


def _modalidade_frete_label(codigo):
    """Converte '0'..'9' em label curto; None/'' -> ''."""
    if not codigo:
        return ''
    return _MOD_FRETE_LABEL.get(str(codigo), str(codigo))


def _coletar_conciliacoes(tipo_documento, documento_ids):
    """Retorna dict {doc_id: [(data, valor_alocado, descricao), ...]} ordenado por data.

    Busca carvia_conciliacoes + join carvia_extrato_linhas para data/descricao.
    """
    if not documento_ids:
        return {}
    rows = db.session.query(
        CarviaConciliacao.documento_id,
        CarviaExtratoLinha.data,
        CarviaConciliacao.valor_alocado,
        CarviaExtratoLinha.descricao,
        CarviaExtratoLinha.memo,
    ).join(
        CarviaExtratoLinha,
        CarviaExtratoLinha.id == CarviaConciliacao.extrato_linha_id,
    ).filter(
        CarviaConciliacao.tipo_documento == tipo_documento,
        CarviaConciliacao.documento_id.in_(list(documento_ids)),
    ).order_by(
        CarviaConciliacao.documento_id,
        CarviaExtratoLinha.data.asc(),
        CarviaConciliacao.conciliado_em.asc(),
    ).all()

    resultado = defaultdict(list)
    for doc_id, data, valor, descricao, memo in rows:
        desc = (descricao or memo or '').strip()
        resultado[doc_id].append((data, float(valor or 0), desc))
    return resultado


def _max_len(lista_de_listas):
    """Retorna maior comprimento entre listas (0 se vazio)."""
    if not lista_de_listas:
        return 0
    return max((len(x) for x in lista_de_listas), default=0)


def _fmt_date(val):
    """Formata date para DD/MM/YYYY ou string vazia."""
    return val.strftime('%d/%m/%Y') if val else ''


def _fmt_datetime(val):
    """Formata datetime para DD/MM/YYYY HH:MM ou string vazia."""
    return val.strftime('%d/%m/%Y %H:%M') if val else ''


def _fmt_bool(val):
    """Formata boolean para Sim/Nao."""
    return 'Sim' if val else 'Nao'


def _ajustar_largura_colunas(df, worksheet):
    """Ajusta largura das colunas do worksheet baseado no conteudo."""
    for idx, col in enumerate(df.columns):
        max_len = max(
            df[col].fillna('').astype(str).map(len).max(),
            len(str(col))
        )
        if idx < 26:
            col_letter = chr(65 + idx)
        else:
            col_letter = chr(64 + idx // 26) + chr(65 + idx % 26)
        worksheet.column_dimensions[col_letter].width = min(max_len + 2, 50)


def _gerar_excel(df, sheet_name, entity_name):
    """Gera arquivo Excel em memoria e retorna response send_file."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        worksheet = writer.sheets[sheet_name]
        _ajustar_largura_colunas(df, worksheet)

    output.seek(0)

    timestamp = agora_utc_naive().strftime('%Y%m%d_%H%M')
    filename = f'carvia_{entity_name}_{timestamp}.xlsx'

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename,
    )


def _check_access():
    """Verifica permissao CarVia. Retorna True se acesso negado."""
    return not getattr(current_user, 'sistema_carvia', False)


def register_exportacao_routes(bp):

    # =====================================================================
    # 1. NFs — granularidade: 1 linha por ITEM DE PRODUTO
    # Agrupamentos superiores: NF -> CTe -> CTe Comp (N x 3) -> Fatura -> Conciliacao (N x 3)
    # =====================================================================
    @bp.route('/api/exportar/nfs')
    @login_required
    def exportar_nfs():
        """Exporta NFs com duplo cabecalho hierarquico (1 linha por item).

        Regra: campos da propria entidade (produto + NF) + agrupamentos SUPERIORES
        (CTe, CTe Complementares, Fatura, Conciliacoes). Nenhuma NF faz agregacao
        de produtos — a granularidade da linha JA e o produto.
        """
        if _check_access():
            return redirect(url_for('main.dashboard'))

        busca = request.args.get('busca', '')
        tipo_filtro = request.args.get('tipo_fonte', '')
        status_filtro = request.args.get('status', '')
        uf_filtro = request.args.get('uf_destino', '')
        data_emissao_de = request.args.get('data_emissao_de', '')
        data_emissao_ate = request.args.get('data_emissao_ate', '')
        sort = request.args.get('sort', 'data_emissao')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaNf)

        if status_filtro == 'CANCELADA':
            query = query.filter(CarviaNf.status == 'CANCELADA')
        elif status_filtro == 'TODAS':
            pass
        else:
            query = query.filter(CarviaNf.status != 'CANCELADA')

        if tipo_filtro:
            query = query.filter(CarviaNf.tipo_fonte == tipo_filtro)

        if data_emissao_de:
            try:
                query = query.filter(CarviaNf.data_emissao >= datetime.strptime(data_emissao_de, '%Y-%m-%d').date())
            except ValueError:
                pass
        if data_emissao_ate:
            try:
                query = query.filter(CarviaNf.data_emissao <= datetime.strptime(data_emissao_ate, '%Y-%m-%d').date())
            except ValueError:
                pass

        if busca:
            busca_like = f'%{busca}%'
            cte_match_subq = db.session.query(
                CarviaOperacaoNf.nf_id
            ).join(
                CarviaOperacao,
                CarviaOperacaoNf.operacao_id == CarviaOperacao.id
            ).filter(
                db.or_(
                    CarviaOperacao.cte_numero.ilike(busca_like),
                    CarviaOperacao.ctrc_numero.ilike(busca_like),
                )
            ).subquery()

            query = query.filter(
                db.or_(
                    CarviaNf.numero_nf.ilike(busca_like),
                    CarviaNf.nome_emitente.ilike(busca_like),
                    CarviaNf.cnpj_emitente.ilike(busca_like),
                    CarviaNf.nome_destinatario.ilike(busca_like),
                    CarviaNf.chave_acesso_nf.ilike(busca_like),
                    CarviaNf.cidade_destinatario.ilike(busca_like),
                    CarviaNf.cnpj_destinatario.ilike(busca_like),
                    CarviaNf.id.in_(cte_match_subq),
                )
            )

        if uf_filtro:
            query = query.filter(CarviaNf.uf_destinatario == uf_filtro.upper())

        sortable_columns = {
            'numero_nf': func.lpad(func.coalesce(CarviaNf.numero_nf, ''), 20, '0'),
            'emitente': CarviaNf.nome_emitente,
            'valor_total': CarviaNf.valor_total,
            'data_emissao': CarviaNf.data_emissao,
            'criado_em': CarviaNf.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaNf.data_emissao)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        nfs = query.all()
        if not nfs:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_nfs'))

        nf_ids = [nf.id for nf in nfs]

        # ---- Itens de produto (1 por linha do Excel) ----
        itens = db.session.query(CarviaNfItem).filter(
            CarviaNfItem.nf_id.in_(nf_ids)
        ).order_by(CarviaNfItem.nf_id, CarviaNfItem.id).all()

        # Se alguma NF nao tem item, ainda assim exibir 1 linha com campos de produto vazios
        itens_por_nf = defaultdict(list)
        for it in itens:
            itens_por_nf[it.nf_id].append(it)

        # ---- Operacao (CTe) pai por NF (join via junction) ----
        junctions = db.session.query(
            CarviaOperacaoNf.nf_id, CarviaOperacaoNf.operacao_id
        ).filter(CarviaOperacaoNf.nf_id.in_(nf_ids)).all()
        nf_to_op = {j_nf: j_op for j_nf, j_op in junctions}  # 1:1 (primeira op)
        op_ids = list({op_id for op_id in nf_to_op.values() if op_id})
        operacoes = {
            op.id: op for op in db.session.query(CarviaOperacao).filter(
                CarviaOperacao.id.in_(op_ids)
            ).all()
        } if op_ids else {}

        # ---- CTe Complementares por operacao ----
        comps_por_op = defaultdict(list)
        if op_ids:
            for c in db.session.query(CarviaCteComplementar).filter(
                CarviaCteComplementar.operacao_id.in_(op_ids)
            ).order_by(CarviaCteComplementar.id).all():
                comps_por_op[c.operacao_id].append(c)

        max_comps = _max_len(comps_por_op.values())

        # ---- Fatura cliente pelos CTes pai ----
        fat_ids = list({op.fatura_cliente_id for op in operacoes.values() if op.fatura_cliente_id})
        faturas = {
            f.id: f for f in db.session.query(CarviaFaturaCliente).filter(
                CarviaFaturaCliente.id.in_(fat_ids)
            ).all()
        } if fat_ids else {}

        # ---- Conciliacoes da fatura (tipo_documento = 'FATURA_CLIENTE') ----
        concil_por_fat = _coletar_conciliacoes('fatura_cliente', fat_ids)
        max_concil = _max_len(concil_por_fat.values())

        # ---- Montar dados ----
        linhas = []
        for nf in nfs:
            op = operacoes.get(nf_to_op.get(nf.id))
            fatura = faturas.get(op.fatura_cliente_id) if op else None
            comps = comps_por_op.get(op.id, []) if op else []
            concils = concil_por_fat.get(fatura.id, []) if fatura else []

            itens_nf = itens_por_nf.get(nf.id) or [None]  # garante 1 linha mesmo sem item
            for item in itens_nf:
                linha = {
                    # PRODUTO
                    'produto_codigo': (item.codigo_produto if item else '') or '',
                    'produto_desc': (item.descricao if item else '') or '',
                    'produto_ncm': (item.ncm if item else '') or '',
                    'produto_cfop': (item.cfop if item else '') or '',
                    'produto_un': (item.unidade if item else '') or '',
                    'produto_qtd': float(item.quantidade or 0) if item else '',
                    'produto_vunit': float(item.valor_unitario or 0) if item else '',
                    'produto_vtotal': float(item.valor_total_item or 0) if item else '',
                    # NF
                    'nf_numero': nf.numero_nf or '',
                    'nf_serie': nf.serie_nf or '',
                    'nf_chave': nf.chave_acesso_nf or '',
                    'nf_data': nf.data_emissao,
                    'nf_emitente': nf.nome_emitente or '',
                    'nf_cnpj_emit': nf.cnpj_emitente or '',
                    'nf_dest': nf.nome_destinatario or '',
                    'nf_cnpj_dest': nf.cnpj_destinatario or '',
                    'nf_uf_dest': nf.uf_destinatario or '',
                    'nf_valor': float(nf.valor_total or 0),
                    'nf_peso': float(nf.peso_bruto or 0),
                    'nf_vol': nf.quantidade_volumes or 0,
                    'nf_modfrete': _modalidade_frete_label(getattr(nf, 'modalidade_frete', None)),
                    'nf_status': nf.status or '',
                    # CTe
                    'cte_numero': (op.cte_numero if op else '') or '',
                    'cte_ctrc': (op.ctrc_numero if op else '') or '',
                    'cte_valor': float(op.cte_valor or 0) if op else '',
                    'cte_tomador': tomador_label_para_export(op.cte_tomador) if op else '',
                    'cte_data': op.cte_data_emissao if op else None,
                    # FATURA
                    'fat_numero': (fatura.numero_fatura if fatura else '') or '',
                    'fat_cnpj_pagador': (fatura.cnpj_cliente if fatura else '') or '',
                    'fat_pagador': (fatura.nome_cliente if fatura else '') or '',
                    'fat_destino': (f'{fatura.pagador_cidade or ""}/{fatura.pagador_uf or ""}').strip('/') if fatura else '',
                    'fat_data': fatura.data_emissao if fatura else None,
                    'fat_valor': float(fatura.valor_total or 0) if fatura else '',
                    'fat_status': (fatura.status if fatura else '') or '',
                }
                # CTe Complementares (N slots)
                for i in range(1, max_comps + 1):
                    c = comps[i - 1] if i - 1 < len(comps) else None
                    linha[f'comp_numero_{i}'] = (c.numero_comp if c else '') or ''
                    linha[f'comp_valor_{i}'] = float(c.cte_valor or 0) if c else ''
                    linha[f'comp_motivo_{i}'] = (getattr(c, 'motivo', None) or getattr(c, 'observacoes', None) or '') if c else ''
                # Conciliacoes (N slots)
                for i in range(1, max_concil + 1):
                    k = concils[i - 1] if i - 1 < len(concils) else None
                    linha[f'concil_data_{i}'] = k[0] if k else None
                    linha[f'concil_valor_{i}'] = k[1] if k else ''
                    linha[f'concil_desc_{i}'] = k[2] if k else ''
                linhas.append(linha)

        # ---- Colunas com duplo cabecalho ----
        colunas = [
            ColunaGrupo('PRODUTO', [
                Campo('produto_codigo', 'Codigo'),
                Campo('produto_desc', 'Descricao'),
                Campo('produto_ncm', 'NCM'),
                Campo('produto_cfop', 'CFOP'),
                Campo('produto_un', 'Un'),
                Campo('produto_qtd', 'Qtd', fmt='money'),
                Campo('produto_vunit', 'V.Unit', fmt='money'),
                Campo('produto_vtotal', 'V.Total', fmt='money'),
            ]),
            ColunaGrupo('NF', [
                Campo('nf_numero', 'Numero'),
                Campo('nf_serie', 'Serie'),
                Campo('nf_chave', 'Chave'),
                Campo('nf_data', 'Data', fmt='date'),
                Campo('nf_emitente', 'Emitente'),
                Campo('nf_cnpj_emit', 'CNPJ Emit'),
                Campo('nf_dest', 'Destinatario'),
                Campo('nf_cnpj_dest', 'CNPJ Dest'),
                Campo('nf_uf_dest', 'UF'),
                Campo('nf_valor', 'Valor', fmt='money'),
                Campo('nf_peso', 'Peso', fmt='money'),
                Campo('nf_vol', 'Vol', fmt='int'),
                Campo('nf_modfrete', 'modFrete'),
                Campo('nf_status', 'Status'),
            ]),
            ColunaGrupo('CTe', [
                Campo('cte_numero', 'Numero'),
                Campo('cte_ctrc', 'CTRC'),
                Campo('cte_valor', 'Valor', fmt='money'),
                Campo('cte_tomador', 'Tomador'),
                Campo('cte_data', 'Data', fmt='date'),
            ]),
        ]
        colunas += grupo_dinamico('CTE COMP', max_comps, [
            Campo('comp_numero_{i}', 'Numero'),
            Campo('comp_valor_{i}', 'Valor', fmt='money'),
            Campo('comp_motivo_{i}', 'Motivo'),
        ])
        colunas.append(ColunaGrupo('FATURA', [
            Campo('fat_numero', 'Numero'),
            Campo('fat_cnpj_pagador', 'CNPJ Pagador'),
            Campo('fat_pagador', 'Pagador'),
            Campo('fat_destino', 'End. Pagador'),
            Campo('fat_data', 'Data', fmt='date'),
            Campo('fat_valor', 'Valor', fmt='money'),
            Campo('fat_status', 'Status'),
        ]))
        colunas += grupo_dinamico('CONCILIACAO', max_concil, [
            Campo('concil_data_{i}', 'Data', fmt='date'),
            Campo('concil_valor_{i}', 'Valor', fmt='money'),
            Campo('concil_desc_{i}', 'Descricao'),
        ])

        return gerar_excel_duplo_cabecalho(colunas, linhas, 'NFs', 'nfs')

    # =====================================================================
    # 2. Operacoes
    # =====================================================================
    @bp.route('/api/exportar/operacoes')
    @login_required
    def exportar_operacoes():
        """Exporta operacoes para Excel com mesmos filtros da listagem"""
        if _check_access():
            return redirect(url_for('main.dashboard'))

        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        tipo_filtro = request.args.get('tipo', '')
        uf_filtro = request.args.get('uf_destino', '')
        uf_origem_filtro = request.args.get('uf_origem', '')
        data_emissao_de = request.args.get('data_emissao_de', '')
        data_emissao_ate = request.args.get('data_emissao_ate', '')
        sort = request.args.get('sort', 'cte_data_emissao')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaOperacao)

        if status_filtro:
            query = query.filter(CarviaOperacao.status == status_filtro)
        if tipo_filtro:
            query = query.filter(CarviaOperacao.tipo_entrada == tipo_filtro)
        if uf_filtro:
            query = query.filter(CarviaOperacao.uf_destino == uf_filtro.upper())
        if uf_origem_filtro:
            query = query.filter(CarviaOperacao.uf_origem == uf_origem_filtro.upper())
        if data_emissao_de:
            try:
                query = query.filter(CarviaOperacao.cte_data_emissao >= datetime.strptime(data_emissao_de, '%Y-%m-%d').date())
            except ValueError:
                pass
        if data_emissao_ate:
            try:
                query = query.filter(CarviaOperacao.cte_data_emissao <= datetime.strptime(data_emissao_ate, '%Y-%m-%d').date())
            except ValueError:
                pass
        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaOperacao.nome_cliente.ilike(busca_like),
                    CarviaOperacao.cnpj_cliente.ilike(busca_like),
                    CarviaOperacao.cte_numero.ilike(busca_like),
                    CarviaOperacao.ctrc_numero.ilike(busca_like),
                    CarviaOperacao.cidade_destino.ilike(busca_like),
                )
            )

        sortable_columns = {
            'cte_numero': func.lpad(func.coalesce(CarviaOperacao.cte_numero, ''), 20, '0'),
            'nome_cliente': CarviaOperacao.nome_cliente,
            'peso_utilizado': CarviaOperacao.peso_utilizado,
            'cte_valor': CarviaOperacao.cte_valor,
            'status': CarviaOperacao.status,
            'cte_data_emissao': CarviaOperacao.cte_data_emissao,
            'criado_em': CarviaOperacao.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaOperacao.cte_data_emissao)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        items = query.all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_operacoes'))

        op_ids = [op.id for op in items]

        # ---- NFs vinculadas por operacao (granularidade do Excel) ----
        nfs_rows = db.session.query(
            CarviaOperacaoNf.operacao_id,
            CarviaNf,
        ).join(
            CarviaNf, CarviaNf.id == CarviaOperacaoNf.nf_id
        ).filter(
            CarviaOperacaoNf.operacao_id.in_(op_ids)
        ).order_by(
            CarviaOperacaoNf.operacao_id, CarviaNf.id
        ).all()
        nfs_por_op = defaultdict(list)
        for op_id, nf in nfs_rows:
            nfs_por_op[op_id].append(nf)

        # ---- CTes Complementares por operacao ----
        comps_por_op = defaultdict(list)
        for c in db.session.query(CarviaCteComplementar).filter(
            CarviaCteComplementar.operacao_id.in_(op_ids)
        ).order_by(CarviaCteComplementar.id).all():
            comps_por_op[c.operacao_id].append(c)
        max_comps = _max_len(comps_por_op.values())

        # ---- Fatura cliente pelos CTes ----
        fat_ids = list({op.fatura_cliente_id for op in items if op.fatura_cliente_id})
        faturas = {
            f.id: f for f in db.session.query(CarviaFaturaCliente).filter(
                CarviaFaturaCliente.id.in_(fat_ids)
            ).all()
        } if fat_ids else {}

        concil_por_fat = _coletar_conciliacoes('fatura_cliente', fat_ids)
        max_concil = _max_len(concil_por_fat.values())

        # ---- Montar dados: 1 linha por NF vinculada (1 linha vazia se sem NF) ----
        linhas = []
        for op in items:
            nfs = nfs_por_op.get(op.id) or [None]  # 1 linha vazia quando manual/freteiro
            comps = comps_por_op.get(op.id, [])
            fatura = faturas.get(op.fatura_cliente_id)
            concils = concil_por_fat.get(fatura.id, []) if fatura else []

            for nf in nfs:
                linha = {
                    # NF
                    'nf_numero': (nf.numero_nf if nf else '') or '',
                    'nf_serie': (nf.serie_nf if nf else '') or '',
                    'nf_chave': (nf.chave_acesso_nf if nf else '') or '',
                    'nf_data': nf.data_emissao if nf else None,
                    'nf_emitente': (nf.nome_emitente if nf else op.nome_cliente or '') or '',
                    'nf_cnpj_emit': (nf.cnpj_emitente if nf else op.cnpj_cliente or '') or '',
                    'nf_dest': (nf.nome_destinatario if nf else '') or '',
                    'nf_cnpj_dest': (nf.cnpj_destinatario if nf else '') or '',
                    'nf_uf_dest': (nf.uf_destinatario if nf else op.uf_destino or '') or '',
                    'nf_valor': float(nf.valor_total or 0) if nf else '',
                    'nf_peso': float(nf.peso_bruto or 0) if nf else '',
                    'nf_modfrete': _modalidade_frete_label(getattr(nf, 'modalidade_frete', None)) if nf else '',
                    # CTe
                    'cte_numero': op.cte_numero or '',
                    'cte_ctrc': op.ctrc_numero or '',
                    'cte_valor': float(op.cte_valor or 0),
                    'cte_tomador': tomador_label_para_export(op.cte_tomador),
                    'cte_origem': f'{op.cidade_origem or ""}/{op.uf_origem or ""}'.strip('/'),
                    'cte_destino': f'{op.cidade_destino or ""}/{op.uf_destino or ""}'.strip('/'),
                    'cte_peso_util': float(op.peso_utilizado or 0),
                    'cte_data': op.cte_data_emissao,
                    'cte_tipo': op.tipo_entrada or '',
                    'cte_status': op.status or '',
                    # FATURA
                    'fat_numero': (fatura.numero_fatura if fatura else '') or '',
                    'fat_cnpj_pagador': (fatura.cnpj_cliente if fatura else '') or '',
                    'fat_pagador': (fatura.nome_cliente if fatura else '') or '',
                    'fat_destino': (f'{fatura.pagador_cidade or ""}/{fatura.pagador_uf or ""}').strip('/') if fatura else '',
                    'fat_data': fatura.data_emissao if fatura else None,
                    'fat_valor': float(fatura.valor_total or 0) if fatura else '',
                    'fat_status': (fatura.status if fatura else '') or '',
                }
                for i in range(1, max_comps + 1):
                    c = comps[i - 1] if i - 1 < len(comps) else None
                    linha[f'comp_numero_{i}'] = (c.numero_comp if c else '') or ''
                    linha[f'comp_valor_{i}'] = float(c.cte_valor or 0) if c else ''
                    linha[f'comp_motivo_{i}'] = (getattr(c, 'motivo', None) or getattr(c, 'observacoes', None) or '') if c else ''
                for i in range(1, max_concil + 1):
                    k = concils[i - 1] if i - 1 < len(concils) else None
                    linha[f'concil_data_{i}'] = k[0] if k else None
                    linha[f'concil_valor_{i}'] = k[1] if k else ''
                    linha[f'concil_desc_{i}'] = k[2] if k else ''
                linhas.append(linha)

        colunas = [
            ColunaGrupo('NF', [
                Campo('nf_numero', 'Numero'),
                Campo('nf_serie', 'Serie'),
                Campo('nf_chave', 'Chave'),
                Campo('nf_data', 'Data', fmt='date'),
                Campo('nf_emitente', 'Emitente'),
                Campo('nf_cnpj_emit', 'CNPJ Emit'),
                Campo('nf_dest', 'Destinatario'),
                Campo('nf_cnpj_dest', 'CNPJ Dest'),
                Campo('nf_uf_dest', 'UF'),
                Campo('nf_valor', 'Valor', fmt='money'),
                Campo('nf_peso', 'Peso', fmt='money'),
                Campo('nf_modfrete', 'modFrete'),
            ]),
            ColunaGrupo('CTe', [
                Campo('cte_numero', 'Numero'),
                Campo('cte_ctrc', 'CTRC'),
                Campo('cte_valor', 'Valor', fmt='money'),
                Campo('cte_tomador', 'Tomador'),
                Campo('cte_origem', 'Origem'),
                Campo('cte_destino', 'Destino'),
                Campo('cte_peso_util', 'Peso Util', fmt='money'),
                Campo('cte_data', 'Data', fmt='date'),
                Campo('cte_tipo', 'Tipo Entrada'),
                Campo('cte_status', 'Status'),
            ]),
        ]
        colunas += grupo_dinamico('CTE COMP', max_comps, [
            Campo('comp_numero_{i}', 'Numero'),
            Campo('comp_valor_{i}', 'Valor', fmt='money'),
            Campo('comp_motivo_{i}', 'Motivo'),
        ])
        colunas.append(ColunaGrupo('FATURA', [
            Campo('fat_numero', 'Numero'),
            Campo('fat_cnpj_pagador', 'CNPJ Pagador'),
            Campo('fat_pagador', 'Pagador'),
            Campo('fat_destino', 'End. Pagador'),
            Campo('fat_data', 'Data', fmt='date'),
            Campo('fat_valor', 'Valor', fmt='money'),
            Campo('fat_status', 'Status'),
        ]))
        colunas += grupo_dinamico('CONCILIACAO', max_concil, [
            Campo('concil_data_{i}', 'Data', fmt='date'),
            Campo('concil_valor_{i}', 'Valor', fmt='money'),
            Campo('concil_desc_{i}', 'Descricao'),
        ])

        return gerar_excel_duplo_cabecalho(colunas, linhas, 'Operacoes', 'operacoes')

    # =====================================================================
    # 3. Subcontratos
    # =====================================================================
    @bp.route('/api/exportar/subcontratos')
    @login_required
    def exportar_subcontratos():
        """Exporta subcontratos para Excel com mesmos filtros da listagem"""
        if _check_access():
            return redirect(url_for('main.dashboard'))

        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        transp_filtro = request.args.get('transportadora', '')
        fatura_filtro = request.args.get('fatura', '')
        data_emissao_de = request.args.get('data_emissao_de', '')
        data_emissao_ate = request.args.get('data_emissao_ate', '')
        uf_origem_filtro = request.args.get('uf_origem', '')
        sort = request.args.get('sort', 'cte_data_emissao')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaSubcontrato).outerjoin(
            CarviaOperacao,
            CarviaSubcontrato.operacao_id == CarviaOperacao.id,
        )

        if status_filtro:
            query = query.filter(CarviaSubcontrato.status == status_filtro)

        if fatura_filtro == 'COM':
            query = query.filter(CarviaSubcontrato.fatura_transportadora_id.isnot(None))
        elif fatura_filtro == 'SEM':
            query = query.filter(CarviaSubcontrato.fatura_transportadora_id.is_(None))

        if data_emissao_de:
            try:
                query = query.filter(CarviaSubcontrato.cte_data_emissao >= datetime.strptime(data_emissao_de, '%Y-%m-%d').date())
            except ValueError:
                pass
        if data_emissao_ate:
            try:
                query = query.filter(CarviaSubcontrato.cte_data_emissao <= datetime.strptime(data_emissao_ate, '%Y-%m-%d').date())
            except ValueError:
                pass

        if uf_origem_filtro:
            query = query.filter(CarviaOperacao.uf_origem == uf_origem_filtro.upper())

        if transp_filtro or busca:
            from app.transportadoras.models import Transportadora
            query = query.outerjoin(
                Transportadora,
                CarviaSubcontrato.transportadora_id == Transportadora.id,
            )

        if transp_filtro:
            from app.transportadoras.models import Transportadora
            transp_like = f'%{transp_filtro}%'
            query = query.filter(Transportadora.razao_social.ilike(transp_like))

        if busca:
            from app.transportadoras.models import Transportadora
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    Transportadora.razao_social.ilike(busca_like),
                    Transportadora.cnpj.ilike(busca_like),
                    CarviaSubcontrato.cte_numero.ilike(busca_like),
                    CarviaOperacao.nome_cliente.ilike(busca_like),
                    CarviaOperacao.cidade_destino.ilike(busca_like),
                )
            )

        sortable_columns = {
            'seq': CarviaSubcontrato.numero_sequencial_transportadora,
            # Phase C (2026-04-14): valor_considerado migrou para CarviaFrete.
            # Fallback: acertado > cotado quando sem frete vinculado (legado).
            'valor_final': func.coalesce(
                CarviaSubcontrato.valor_acertado,
                CarviaSubcontrato.valor_cotado,
            ),
            'status': CarviaSubcontrato.status,
            'cte_data_emissao': CarviaSubcontrato.cte_data_emissao,
            'criado_em': CarviaSubcontrato.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaSubcontrato.cte_data_emissao)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        items = query.all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_subcontratos'))

        # Enriquecer com operacao (rota, cliente) e custos/ctes comp
        sub_op_ids = list({s.operacao_id for s in items if s.operacao_id})
        sub_op_map = {}
        if sub_op_ids:
            ops = db.session.query(CarviaOperacao).filter(
                CarviaOperacao.id.in_(sub_op_ids)
            ).all()
            sub_op_map = {o.id: o for o in ops}

        from collections import defaultdict
        custos_por_op = defaultdict(int)
        custos_valor_por_op = defaultdict(float)
        comps_por_op = defaultdict(int)
        if sub_op_ids:
            for op_id, cnt, val in db.session.query(
                CarviaCustoEntrega.operacao_id,
                func.count(CarviaCustoEntrega.id),
                func.coalesce(func.sum(CarviaCustoEntrega.valor), 0),
            ).filter(
                CarviaCustoEntrega.operacao_id.in_(sub_op_ids)
            ).group_by(CarviaCustoEntrega.operacao_id).all():
                custos_por_op[op_id] = cnt
                custos_valor_por_op[op_id] = float(val)

            for op_id, cnt in db.session.query(
                CarviaCteComplementar.operacao_id,
                func.count(CarviaCteComplementar.id),
            ).filter(
                CarviaCteComplementar.operacao_id.in_(sub_op_ids)
            ).group_by(CarviaCteComplementar.operacao_id).all():
                comps_por_op[op_id] = cnt

        # Valor Conciliado: pre-calcula rateio por fatura transportadora
        # (uma chamada ao helper por fatura, reusa entre subs).
        from app.carvia.services.financeiro.rateio_conciliacao_helper import (
            ratear_conciliacao_fatura,
        )
        from app.carvia.models import CarviaFaturaTransportadora
        fatura_ids = list({s.fatura_transportadora_id for s in items if s.fatura_transportadora_id})
        valor_conciliado_por_sub_id = {}
        if fatura_ids:
            faturas_map = {
                f.id: f for f in CarviaFaturaTransportadora.query.filter(
                    CarviaFaturaTransportadora.id.in_(fatura_ids)
                ).all()
            }
            # Subs e CEs de todas as faturas impactadas (batch unico)
            subs_por_fatura = defaultdict(list)
            for s in CarviaSubcontrato.query.filter(
                CarviaSubcontrato.fatura_transportadora_id.in_(fatura_ids),
                CarviaSubcontrato.status != 'CANCELADO',
            ).all():
                subs_por_fatura[s.fatura_transportadora_id].append(s)
            ces_por_fatura = defaultdict(list)
            for c in CarviaCustoEntrega.query.filter(
                CarviaCustoEntrega.fatura_transportadora_id.in_(fatura_ids),
                CarviaCustoEntrega.status != 'CANCELADO',
            ).all():
                ces_por_fatura[c.fatura_transportadora_id].append(c)
            for fid, fatura in faturas_map.items():
                rateio = ratear_conciliacao_fatura(
                    fatura,
                    subs_por_fatura.get(fid, []),
                    ces_por_fatura.get(fid, []),
                )
                for sub_id, v in rateio['por_sub'].items():
                    valor_conciliado_por_sub_id[sub_id] = float(v)

        data = []
        for sub in items:
            op = sub_op_map.get(sub.operacao_id)
            # Phase C (2026-04-14): valor_considerado migrou para CarviaFrete.
            # Leitura via sub.frete.
            valor_considerado = (
                sub.frete.valor_considerado if sub.frete else None
            )
            valor_final_hierarquico = (
                valor_considerado
                or sub.valor_acertado
                or sub.valor_cotado
                or 0
            )
            valor_conciliado = valor_conciliado_por_sub_id.get(sub.id, 0)
            data.append({
                'ID': sub.id,
                'Operacao ID': sub.operacao_id,
                'CTe CarVia': (op.cte_numero or '') if op else '',
                'Emitente': (op.nome_cliente or '') if op else '',
                'Origem': f'{op.cidade_origem or ""}/{op.uf_origem or ""}' if op else '',
                'Destino': f'{op.cidade_destino or ""}/{op.uf_destino or ""}' if op else '',
                'Transportadora': sub.transportadora.razao_social if sub.transportadora else '',
                'CTe Numero': sub.cte_numero or '',
                'Valor CTe': float(sub.cte_valor or 0),
                'Valor Cotado': float(sub.valor_cotado or 0),
                'Valor Acertado': float(sub.valor_acertado or 0) if sub.valor_acertado else '',
                'Valor Considerado': float(valor_considerado or 0) if valor_considerado else '',
                'Valor Conciliado': float(valor_conciliado) if valor_conciliado else '',
                'Valor Final': float(valor_final_hierarquico),
                'Status': sub.status or '',
                'Qtd Custos Entrega': custos_por_op.get(sub.operacao_id, 0),
                'Valor Custos Entrega': custos_valor_por_op.get(sub.operacao_id, 0),
                'Qtd CTes Comp': comps_por_op.get(sub.operacao_id, 0),
                'Criado Em': _fmt_datetime(sub.criado_em),
                'Criado Por': sub.criado_por or '',
            })

        df = pd.DataFrame(data)
        return _gerar_excel(df, 'Subcontratos', 'subcontratos')

    # =====================================================================
    # 4. CTe Complementares
    # =====================================================================
    @bp.route('/api/exportar/ctes-complementares')
    @login_required
    def exportar_ctes_complementares():
        """Exporta CTes complementares para Excel com mesmos filtros da listagem"""
        if _check_access():
            return redirect(url_for('main.dashboard'))

        operacao_filtro = request.args.get('operacao', '', type=str)
        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        data_emissao_de = request.args.get('data_emissao_de', '')
        data_emissao_ate = request.args.get('data_emissao_ate', '')
        sort = request.args.get('sort', 'cte_data_emissao')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaCteComplementar)

        if operacao_filtro:
            query = query.filter(CarviaCteComplementar.operacao_id == int(operacao_filtro))
        if status_filtro:
            query = query.filter(CarviaCteComplementar.status == status_filtro)

        if data_emissao_de:
            try:
                query = query.filter(CarviaCteComplementar.cte_data_emissao >= datetime.strptime(data_emissao_de, '%Y-%m-%d').date())
            except ValueError:
                pass
        if data_emissao_ate:
            try:
                query = query.filter(CarviaCteComplementar.cte_data_emissao <= datetime.strptime(data_emissao_ate, '%Y-%m-%d').date())
            except ValueError:
                pass

        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaCteComplementar.numero_comp.ilike(busca_like),
                    CarviaCteComplementar.cnpj_cliente.ilike(busca_like),
                    CarviaCteComplementar.nome_cliente.ilike(busca_like),
                    CarviaCteComplementar.ctrc_numero.ilike(busca_like),
                    CarviaCteComplementar.observacoes.ilike(busca_like),
                )
            )

        sortable_columns = {
            'numero_comp': CarviaCteComplementar.numero_comp,
            'cte_valor': CarviaCteComplementar.cte_valor,
            'cte_data_emissao': CarviaCteComplementar.cte_data_emissao,
            'status': CarviaCteComplementar.status,
            'criado_em': CarviaCteComplementar.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaCteComplementar.cte_data_emissao)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        items = query.all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_ctes_complementares'))

        # ---- Granularidade: 1 linha por CTe Complementar ----
        # Agrupamentos superiores: CTe Pai -> Fatura -> Conciliacoes
        op_ids = list({c.operacao_id for c in items})
        operacoes = {
            o.id: o for o in db.session.query(CarviaOperacao).filter(
                CarviaOperacao.id.in_(op_ids)
            ).all()
        } if op_ids else {}

        fat_ids = list({c.fatura_cliente_id for c in items if c.fatura_cliente_id})
        faturas = {
            f.id: f for f in db.session.query(CarviaFaturaCliente).filter(
                CarviaFaturaCliente.id.in_(fat_ids)
            ).all()
        } if fat_ids else {}

        concil_por_fat = _coletar_conciliacoes('fatura_cliente', fat_ids)
        max_concil = _max_len(concil_por_fat.values())

        linhas = []
        for c in items:
            op = operacoes.get(c.operacao_id)
            fatura = faturas.get(c.fatura_cliente_id)
            concils = concil_por_fat.get(fatura.id, []) if fatura else []

            linha = {
                # CTE COMP (entidade propria)
                'comp_numero': c.numero_comp or '',
                'comp_cte_numero': c.cte_numero or '',
                'comp_ctrc': c.ctrc_numero or '',
                'comp_cliente': c.nome_cliente or '',
                'comp_cnpj_cliente': c.cnpj_cliente or '',
                'comp_valor': float(c.cte_valor or 0),
                'comp_data': c.cte_data_emissao,
                'comp_motivo': getattr(c, 'motivo', None) or getattr(c, 'observacoes', None) or '',
                'comp_status': c.status or '',
                # CTE PAI (agrupamento superior)
                'cte_numero': (op.cte_numero if op else '') or '',
                'cte_ctrc': (op.ctrc_numero if op else '') or '',
                'cte_valor': float(op.cte_valor or 0) if op else '',
                'cte_tomador': tomador_label_para_export(op.cte_tomador) if op else '',
                # FATURA (agrupamento superior)
                'fat_numero': (fatura.numero_fatura if fatura else '') or '',
                'fat_cnpj_pagador': (fatura.cnpj_cliente if fatura else '') or '',
                'fat_pagador': (fatura.nome_cliente if fatura else '') or '',
                'fat_destino': (f'{fatura.pagador_cidade or ""}/{fatura.pagador_uf or ""}').strip('/') if fatura else '',
                'fat_valor': float(fatura.valor_total or 0) if fatura else '',
                'fat_status': (fatura.status if fatura else '') or '',
            }
            for i in range(1, max_concil + 1):
                k = concils[i - 1] if i - 1 < len(concils) else None
                linha[f'concil_data_{i}'] = k[0] if k else None
                linha[f'concil_valor_{i}'] = k[1] if k else ''
                linha[f'concil_desc_{i}'] = k[2] if k else ''
            linhas.append(linha)

        colunas = [
            ColunaGrupo('CTE COMPLEMENTAR', [
                Campo('comp_numero', 'Numero Comp'),
                Campo('comp_cte_numero', 'CTe Numero'),
                Campo('comp_ctrc', 'CTRC'),
                Campo('comp_cliente', 'Cliente'),
                Campo('comp_cnpj_cliente', 'CNPJ Cliente'),
                Campo('comp_valor', 'Valor', fmt='money'),
                Campo('comp_data', 'Data', fmt='date'),
                Campo('comp_motivo', 'Motivo'),
                Campo('comp_status', 'Status'),
            ]),
            ColunaGrupo('CTe PAI', [
                Campo('cte_numero', 'Numero'),
                Campo('cte_ctrc', 'CTRC'),
                Campo('cte_valor', 'Valor', fmt='money'),
                Campo('cte_tomador', 'Tomador'),
            ]),
            ColunaGrupo('FATURA', [
                Campo('fat_numero', 'Numero'),
                Campo('fat_cnpj_pagador', 'CNPJ Pagador'),
                Campo('fat_pagador', 'Pagador'),
                Campo('fat_destino', 'End. Pagador'),
                Campo('fat_valor', 'Valor', fmt='money'),
                Campo('fat_status', 'Status'),
            ]),
        ]
        colunas += grupo_dinamico('CONCILIACAO', max_concil, [
            Campo('concil_data_{i}', 'Data', fmt='date'),
            Campo('concil_valor_{i}', 'Valor', fmt='money'),
            Campo('concil_desc_{i}', 'Descricao'),
        ])

        return gerar_excel_duplo_cabecalho(colunas, linhas, 'CTe Comp', 'ctes_complementares')

    # =====================================================================
    # 5. Custos Entrega
    # =====================================================================
    @bp.route('/api/exportar/custos-entrega')
    @login_required
    def exportar_custos_entrega():
        """Exporta custos de entrega para Excel com mesmos filtros da listagem"""
        if _check_access():
            return redirect(url_for('main.dashboard'))

        operacao_filtro = request.args.get('operacao', '', type=str)
        tipo_filtro = request.args.get('tipo', '')
        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        sort = request.args.get('sort', 'criado_em')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaCustoEntrega)

        if operacao_filtro:
            query = query.filter(CarviaCustoEntrega.operacao_id == int(operacao_filtro))
        if tipo_filtro:
            query = query.filter(CarviaCustoEntrega.tipo_custo == tipo_filtro)
        if status_filtro:
            query = query.filter(CarviaCustoEntrega.status == status_filtro)
        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaCustoEntrega.numero_custo.ilike(busca_like),
                    CarviaCustoEntrega.descricao.ilike(busca_like),
                    CarviaCustoEntrega.fornecedor_nome.ilike(busca_like),
                    CarviaCustoEntrega.observacoes.ilike(busca_like),
                )
            )

        sortable_columns = {
            'numero_custo': CarviaCustoEntrega.numero_custo,
            'tipo_custo': CarviaCustoEntrega.tipo_custo,
            'valor': CarviaCustoEntrega.valor,
            'data_custo': CarviaCustoEntrega.data_custo,
            'data_vencimento': CarviaCustoEntrega.data_vencimento,
            'status': CarviaCustoEntrega.status,
            'criado_em': CarviaCustoEntrega.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaCustoEntrega.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        items = query.all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_custos_entrega'))

        # Buscar CTe Comp vinculados
        comp_ids = [c.cte_complementar_id for c in items if c.cte_complementar_id]
        comp_map = {}
        if comp_ids:
            comps = db.session.query(
                CarviaCteComplementar.id, CarviaCteComplementar.numero_comp
            ).filter(CarviaCteComplementar.id.in_(comp_ids)).all()
            comp_map = {c_id: num for c_id, num in comps}

        # Buscar operacoes para emitente/destinatario/rota
        op_ids = list({c.operacao_id for c in items})
        op_map = {}
        if op_ids:
            ops = db.session.query(CarviaOperacao).filter(
                CarviaOperacao.id.in_(op_ids)
            ).all()
            op_map = {o.id: o for o in ops}

        # Buscar faturas cliente via operacoes
        fat_cli_map = {}
        fat_cli_ids = [o.fatura_cliente_id for o in op_map.values() if o.fatura_cliente_id]
        if fat_cli_ids:
            fats = db.session.query(
                CarviaFaturaCliente.id, CarviaFaturaCliente.numero_fatura
            ).filter(CarviaFaturaCliente.id.in_(fat_cli_ids)).all()
            fat_cli_map = {f_id: num for f_id, num in fats}

        # Buscar subcontratos por operacao
        sub_map = {}  # op_id -> transportadora(s)
        if op_ids:
            subs = db.session.query(
                CarviaSubcontrato.operacao_id,
                CarviaSubcontrato.cte_numero,
            ).filter(
                CarviaSubcontrato.operacao_id.in_(op_ids)
            ).all()
            from collections import defaultdict
            sub_map = defaultdict(list)
            for s_op_id, s_cte in subs:
                sub_map[s_op_id].append(s_cte or '')

        data = []
        for c in items:
            op = op_map.get(c.operacao_id)
            data.append({
                'Numero Custo': c.numero_custo or '',
                'Operacao ID': c.operacao_id,
                'CTe CarVia': (op.cte_numero or '') if op else '',
                'CTRC': (op.ctrc_numero or '') if op else '',
                'Emitente': (op.nome_cliente or '') if op else '',
                'CNPJ Emitente': (op.cnpj_cliente or '') if op else '',
                'Origem': f'{op.cidade_origem or ""}/{op.uf_origem or ""}' if op else '',
                'Destino': f'{op.cidade_destino or ""}/{op.uf_destino or ""}' if op else '',
                'CTe Comp': comp_map.get(c.cte_complementar_id, ''),
                'Subcontratos': ', '.join(sub_map.get(c.operacao_id, [])),
                'Fatura CarVia': fat_cli_map.get(op.fatura_cliente_id, '') if op and op.fatura_cliente_id else '',
                'Tipo Custo': c.tipo_custo or '',
                'Descricao': c.descricao or '',
                'Valor': float(c.valor or 0),
                'Data Custo': _fmt_date(c.data_custo),
                'Data Vencimento': _fmt_date(c.data_vencimento),
                'Fornecedor': c.fornecedor_nome or '',
                'CNPJ Fornecedor': c.fornecedor_cnpj or '',
                'Status': c.status or '',
                'Pago Em': _fmt_datetime(c.pago_em),
                'Pago Por': c.pago_por or '',
                'Conciliado': _fmt_bool(c.conciliado),
                'Criado Em': _fmt_datetime(c.criado_em),
                'Criado Por': c.criado_por or '',
            })

        df = pd.DataFrame(data)
        return _gerar_excel(df, 'Custos Entrega', 'custos_entrega')

    # =====================================================================
    # 6. Faturas Cliente
    # =====================================================================
    @bp.route('/api/exportar/faturas-cliente')
    @login_required
    def exportar_faturas_cliente():
        """Exporta faturas cliente — 1 linha por fatura.

        Campos da propria entidade (pagador + destino) + conciliacoes (N x 3).
        NAO inclui CTes ou NFs (granularidade inferior). Para ver CTes, usar
        export de Operacoes.
        """
        if _check_access():
            return redirect(url_for('main.dashboard'))

        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        cliente_filtro = request.args.get('cliente', '')
        data_emissao_de = request.args.get('data_emissao_de', '')
        data_emissao_ate = request.args.get('data_emissao_ate', '')
        sort = request.args.get('sort', 'data_emissao')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaFaturaCliente)

        if status_filtro:
            query = query.filter(CarviaFaturaCliente.status == status_filtro)
        if cliente_filtro:
            cliente_like = f'%{cliente_filtro}%'
            query = query.filter(
                db.or_(
                    CarviaFaturaCliente.nome_cliente.ilike(cliente_like),
                    CarviaFaturaCliente.cnpj_cliente.ilike(cliente_like),
                )
            )
        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                CarviaFaturaCliente.numero_fatura.ilike(busca_like),
            )
        if data_emissao_de:
            try:
                query = query.filter(CarviaFaturaCliente.data_emissao >= datetime.strptime(data_emissao_de, '%Y-%m-%d').date())
            except ValueError:
                pass
        if data_emissao_ate:
            try:
                query = query.filter(CarviaFaturaCliente.data_emissao <= datetime.strptime(data_emissao_ate, '%Y-%m-%d').date())
            except ValueError:
                pass

        sortable_columns = {
            'numero_fatura': func.lpad(func.coalesce(CarviaFaturaCliente.numero_fatura, ''), 20, '0'),
            'nome_cliente': CarviaFaturaCliente.nome_cliente,
            'data_emissao': CarviaFaturaCliente.data_emissao,
            'vencimento': CarviaFaturaCliente.vencimento,
            'valor_total': CarviaFaturaCliente.valor_total,
            'status': CarviaFaturaCliente.status,
            'criado_em': CarviaFaturaCliente.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaFaturaCliente.data_emissao)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        items = query.all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_faturas_cliente'))

        fat_ids = [f.id for f in items]
        concil_por_fat = _coletar_conciliacoes('fatura_cliente', fat_ids)
        max_concil = _max_len(concil_por_fat.values())

        # Cliente comercial via CNPJ DESTINATARIO da NF (para ajudar cobranca).
        from app.carvia.services.clientes.cliente_service import CarviaClienteService
        clientes_por_fatura = CarviaClienteService.resolver_clientes_por_faturas_cliente(fat_ids)

        linhas = []
        for f in items:
            cli = clientes_por_fatura.get(f.id) or {}
            concils = concil_por_fat.get(f.id, [])
            destino = '/'.join(filter(None, [f.pagador_cidade, f.pagador_uf]))

            linha = {
                'fat_numero': f.numero_fatura or '',
                'fat_cliente_comercial': cli.get('nome_comercial') or '',
                'fat_cnpj_pagador': f.cnpj_cliente or '',
                'fat_pagador': f.nome_cliente or '',
                'fat_destino': destino,
                'fat_data': f.data_emissao,
                'fat_vencimento': f.vencimento,
                'fat_valor': float(f.valor_total or 0),
                'fat_status': f.status or '',
                'fat_total_conciliado': float(f.total_conciliado or 0),
                'fat_pago_em': f.pago_em,
                'fat_pago_por': f.pago_por or '',
            }
            for i in range(1, max_concil + 1):
                k = concils[i - 1] if i - 1 < len(concils) else None
                linha[f'concil_data_{i}'] = k[0] if k else None
                linha[f'concil_valor_{i}'] = k[1] if k else ''
                linha[f'concil_desc_{i}'] = k[2] if k else ''
            linhas.append(linha)

        colunas = [
            ColunaGrupo('FATURA', [
                Campo('fat_numero', 'Numero'),
                Campo('fat_cliente_comercial', 'Cliente Comercial'),
                Campo('fat_cnpj_pagador', 'CNPJ Pagador'),
                Campo('fat_pagador', 'Pagador'),
                Campo('fat_destino', 'End. Pagador'),
                Campo('fat_data', 'Emissao', fmt='date'),
                Campo('fat_vencimento', 'Vencimento', fmt='date'),
                Campo('fat_valor', 'Valor Total', fmt='money'),
                Campo('fat_status', 'Status'),
                Campo('fat_total_conciliado', 'Total Conciliado', fmt='money'),
                Campo('fat_pago_em', 'Pago Em', fmt='datetime'),
                Campo('fat_pago_por', 'Pago Por'),
            ]),
        ]
        colunas += grupo_dinamico('CONCILIACAO', max_concil, [
            Campo('concil_data_{i}', 'Data', fmt='date'),
            Campo('concil_valor_{i}', 'Valor', fmt='money'),
            Campo('concil_desc_{i}', 'Descricao'),
        ])

        return gerar_excel_duplo_cabecalho(colunas, linhas, 'Faturas Cliente', 'faturas_cliente')

    # =====================================================================
    # 7. Faturas Transportadora
    # =====================================================================
    @bp.route('/api/exportar/faturas-transportadora')
    @login_required
    def exportar_faturas_transportadora():
        """Exporta faturas transportadora para Excel com mesmos filtros da listagem"""
        if _check_access():
            return redirect(url_for('main.dashboard'))

        from datetime import date as date_type

        numero_fatura = request.args.get('numero_fatura', '')
        transportadora_id = request.args.get('transportadora_id', '')
        numero_subcontrato = request.args.get('numero_subcontrato', '')
        status_conferencia = request.args.get('status_conferencia', '') or request.args.get('status', '')
        status_pagamento = request.args.get('status_pagamento', '') or request.args.get('pagamento', '')
        data_emissao_de = request.args.get('data_emissao_de', '')
        data_emissao_ate = request.args.get('data_emissao_ate', '')
        data_vencimento_de = request.args.get('data_vencimento_de', '')
        data_vencimento_ate = request.args.get('data_vencimento_ate', '')
        sort = request.args.get('sort', 'id')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaFaturaTransportadora)

        if numero_fatura:
            query = query.filter(
                CarviaFaturaTransportadora.numero_fatura.ilike(f'%{numero_fatura}%')
            )
        if transportadora_id:
            query = query.filter(
                CarviaFaturaTransportadora.transportadora_id == int(transportadora_id)
            )
        if numero_subcontrato:
            faturas_com_sub = db.session.query(
                CarviaSubcontrato.fatura_transportadora_id
            ).filter(
                CarviaSubcontrato.cte_numero.ilike(f'%{numero_subcontrato}%'),
                CarviaSubcontrato.fatura_transportadora_id.isnot(None),
            ).distinct().subquery()
            query = query.filter(CarviaFaturaTransportadora.id.in_(faturas_com_sub))
        if status_conferencia:
            query = query.filter(
                CarviaFaturaTransportadora.status_conferencia == status_conferencia
            )
        if status_pagamento:
            query = query.filter(
                CarviaFaturaTransportadora.status_pagamento == status_pagamento
            )
        if data_emissao_de:
            query = query.filter(
                CarviaFaturaTransportadora.data_emissao >= date_type.fromisoformat(data_emissao_de)
            )
        if data_emissao_ate:
            query = query.filter(
                CarviaFaturaTransportadora.data_emissao <= date_type.fromisoformat(data_emissao_ate)
            )
        if data_vencimento_de:
            query = query.filter(
                CarviaFaturaTransportadora.vencimento >= date_type.fromisoformat(data_vencimento_de)
            )
        if data_vencimento_ate:
            query = query.filter(
                CarviaFaturaTransportadora.vencimento <= date_type.fromisoformat(data_vencimento_ate)
            )

        sortable_columns = {
            'id': CarviaFaturaTransportadora.id,
            'numero_fatura': func.lpad(func.coalesce(CarviaFaturaTransportadora.numero_fatura, ''), 20, '0'),
            'data_emissao': CarviaFaturaTransportadora.data_emissao,
            'vencimento': CarviaFaturaTransportadora.vencimento,
            'valor_total': CarviaFaturaTransportadora.valor_total,
            'status_conferencia': CarviaFaturaTransportadora.status_conferencia,
            'criado_em': CarviaFaturaTransportadora.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaFaturaTransportadora.id)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        items = query.all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_faturas_transportadora'))

        ft_ids = [f.id for f in items]
        concil_por_ft = _coletar_conciliacoes('fatura_transportadora', ft_ids)
        max_concil = _max_len(concil_por_ft.values())

        linhas = []
        for f in items:
            concils = concil_por_ft.get(f.id, [])
            linha = {
                'ft_numero': f.numero_fatura or '',
                'ft_transportadora': f.transportadora.razao_social if f.transportadora else '',
                'ft_data': f.data_emissao,
                'ft_vencimento': f.vencimento,
                'ft_valor': float(f.valor_total or 0),
                'ft_status_conf': f.status_conferencia or '',
                'ft_conf_por': f.conferido_por or '',
                'ft_conf_em': f.conferido_em,
                'ft_status_pag': f.status_pagamento or '',
                'ft_total_conciliado': float(f.total_conciliado or 0),
                'ft_pago_em': f.pago_em,
                'ft_pago_por': f.pago_por or '',
            }
            for i in range(1, max_concil + 1):
                k = concils[i - 1] if i - 1 < len(concils) else None
                linha[f'concil_data_{i}'] = k[0] if k else None
                linha[f'concil_valor_{i}'] = k[1] if k else ''
                linha[f'concil_desc_{i}'] = k[2] if k else ''
            linhas.append(linha)

        colunas = [
            ColunaGrupo('FATURA TRANSPORTADORA', [
                Campo('ft_numero', 'Numero'),
                Campo('ft_transportadora', 'Transportadora'),
                Campo('ft_data', 'Emissao', fmt='date'),
                Campo('ft_vencimento', 'Vencimento', fmt='date'),
                Campo('ft_valor', 'Valor Total', fmt='money'),
                Campo('ft_status_conf', 'Status Conferencia'),
                Campo('ft_conf_por', 'Conferido Por'),
                Campo('ft_conf_em', 'Conferido Em', fmt='datetime'),
                Campo('ft_status_pag', 'Status Pagamento'),
                Campo('ft_total_conciliado', 'Total Conciliado', fmt='money'),
                Campo('ft_pago_em', 'Pago Em', fmt='datetime'),
                Campo('ft_pago_por', 'Pago Por'),
            ]),
        ]
        colunas += grupo_dinamico('CONCILIACAO', max_concil, [
            Campo('concil_data_{i}', 'Data', fmt='date'),
            Campo('concil_valor_{i}', 'Valor', fmt='money'),
            Campo('concil_desc_{i}', 'Descricao'),
        ])

        return gerar_excel_duplo_cabecalho(colunas, linhas, 'Faturas Transp', 'faturas_transportadora')

    # =====================================================================
    # 8. Despesas
    # =====================================================================
    @bp.route('/api/exportar/despesas')
    @login_required
    def exportar_despesas():
        """Exporta despesas para Excel com mesmos filtros da listagem"""
        if _check_access():
            return redirect(url_for('main.dashboard'))

        tipo_filtro = request.args.get('tipo', '')
        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        sort = request.args.get('sort', 'criado_em')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaDespesa)

        if tipo_filtro:
            query = query.filter(CarviaDespesa.tipo_despesa == tipo_filtro)
        if status_filtro:
            query = query.filter(CarviaDespesa.status == status_filtro)
        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaDespesa.descricao.ilike(busca_like),
                    CarviaDespesa.observacoes.ilike(busca_like),
                )
            )

        sortable_columns = {
            'tipo_despesa': CarviaDespesa.tipo_despesa,
            'valor': CarviaDespesa.valor,
            'data_despesa': CarviaDespesa.data_despesa,
            'data_vencimento': CarviaDespesa.data_vencimento,
            'status': CarviaDespesa.status,
            'criado_em': CarviaDespesa.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaDespesa.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        items = query.all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_despesas'))

        data = []
        for d in items:
            data.append({
                'ID': d.id,
                'Tipo Despesa': d.tipo_despesa or '',
                'Descricao': d.descricao or '',
                'Valor': float(d.valor or 0),
                'Data Despesa': _fmt_date(d.data_despesa),
                'Data Vencimento': _fmt_date(d.data_vencimento),
                'Status': d.status or '',
                'Pago Em': _fmt_datetime(d.pago_em),
                'Pago Por': d.pago_por or '',
                'Conciliado': _fmt_bool(d.conciliado),
                'Total Conciliado': float(d.total_conciliado or 0),
                'Criado Em': _fmt_datetime(d.criado_em),
            })

        df = pd.DataFrame(data)
        return _gerar_excel(df, 'Despesas', 'despesas')

    # =====================================================================
    # 9. Receitas
    # =====================================================================
    @bp.route('/api/exportar/receitas')
    @login_required
    def exportar_receitas():
        """Exporta receitas para Excel com mesmos filtros da listagem"""
        if _check_access():
            return redirect(url_for('main.dashboard'))

        tipo_filtro = request.args.get('tipo', '')
        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        sort = request.args.get('sort', 'criado_em')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaReceita)

        if tipo_filtro:
            query = query.filter(CarviaReceita.tipo_receita == tipo_filtro)
        if status_filtro:
            query = query.filter(CarviaReceita.status == status_filtro)
        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaReceita.descricao.ilike(busca_like),
                    CarviaReceita.observacoes.ilike(busca_like),
                )
            )

        sortable_columns = {
            'tipo_receita': CarviaReceita.tipo_receita,
            'valor': CarviaReceita.valor,
            'data_receita': CarviaReceita.data_receita,
            'data_vencimento': CarviaReceita.data_vencimento,
            'status': CarviaReceita.status,
            'criado_em': CarviaReceita.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaReceita.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        items = query.all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_receitas'))

        data = []
        for r in items:
            data.append({
                'ID': r.id,
                'Tipo Receita': r.tipo_receita or '',
                'Descricao': r.descricao or '',
                'Valor': float(r.valor or 0),
                'Data Receita': _fmt_date(r.data_receita),
                'Data Vencimento': _fmt_date(r.data_vencimento),
                'Status': r.status or '',
                'Recebido Em': _fmt_datetime(r.recebido_em),
                'Recebido Por': r.recebido_por or '',
                'Conciliado': _fmt_bool(r.conciliado),
                'Total Conciliado': float(r.total_conciliado or 0),
                'Criado Em': _fmt_datetime(r.criado_em),
            })

        df = pd.DataFrame(data)
        return _gerar_excel(df, 'Receitas', 'receitas')

    # Sessoes Cotacao: REMOVIDO (feature obsoleta, 22/03/2026)

    # =====================================================================
    # 10. Modelos de Moto
    # =====================================================================
    @bp.route('/api/exportar/modelos-moto')
    @login_required
    def exportar_modelos_moto():
        """Exporta modelos de moto para Excel"""
        if _check_access():
            return redirect(url_for('main.dashboard'))

        items = CarviaModeloMoto.query.order_by(CarviaModeloMoto.nome.asc()).all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_modelos_moto'))

        data = []
        for m in items:
            comp = float(m.comprimento or 0)
            larg = float(m.largura or 0)
            alt = float(m.altura or 0)
            volume_m3 = comp * larg * alt / 1_000_000
            data.append({
                'Nome': m.nome or '',
                'Categoria': m.categoria.nome if m.categoria else '',
                'Comprimento (cm)': comp,
                'Largura (cm)': larg,
                'Altura (cm)': alt,
                'Cubagem (m3)': round(volume_m3, 4),
                'Peso Cubado (kg)': round(volume_m3 * 300, 3),
                'Regex Pattern': m.regex_pattern or '',
                'Ativo': _fmt_bool(m.ativo),
                'Criado Em': _fmt_datetime(m.criado_em),
                'Criado Por': m.criado_por or '',
            })

        df = pd.DataFrame(data)
        return _gerar_excel(df, 'Modelos Moto', 'modelos_moto')

    # =====================================================================
    # 11. Cidades Atendidas
    # =====================================================================
    @bp.route('/api/exportar/cidades-atendidas')
    @login_required
    def exportar_cidades_atendidas():
        """Exporta cidades atendidas para Excel"""
        if _check_access():
            return redirect(url_for('main.dashboard'))

        items = CarviaCidadeAtendida.query.order_by(
            CarviaCidadeAtendida.uf_destino.asc(),
            CarviaCidadeAtendida.nome_cidade.asc(),
        ).all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_cidades_carvia'))

        data = []
        for c in items:
            data.append({
                'Codigo IBGE': c.codigo_ibge or '',
                'Nome Cidade': c.nome_cidade or '',
                'UF Origem': c.uf_origem or '',
                'UF Destino': c.uf_destino or '',
                'Nome Tabela': c.nome_tabela or '',
                'Lead Time (dias)': c.lead_time if c.lead_time is not None else '',
                'Ativo': _fmt_bool(c.ativo),
                'Criado Em': _fmt_datetime(c.criado_em),
                'Criado Por': c.criado_por or '',
            })

        df = pd.DataFrame(data)
        return _gerar_excel(df, 'Cidades Atendidas', 'cidades_atendidas')

    # =====================================================================
    # 12. Tabelas de Frete
    # =====================================================================
    @bp.route('/api/exportar/tabelas-frete')
    @login_required
    def exportar_tabelas_frete():
        """Exporta tabelas de frete para Excel"""
        if _check_access():
            return redirect(url_for('main.dashboard'))

        query = CarviaTabelaFrete.query.order_by(
            CarviaTabelaFrete.nome_tabela.asc(),
            CarviaTabelaFrete.uf_origem.asc(),
            CarviaTabelaFrete.uf_destino.asc(),
            CarviaTabelaFrete.modalidade.asc(),
        )

        # Filtro opcional: so ativos
        ativo_filtro = request.args.get('ativo', '')
        if ativo_filtro == '1':
            query = query.filter(CarviaTabelaFrete.ativo.is_(True))

        items = query.all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_tabelas_carvia'))

        # Pre-cache grupos
        grupos = {g.id: g.nome for g in CarviaGrupoCliente.query.all()}

        data = []
        for t in items:
            data.append({
                'UF Origem': t.uf_origem or '',
                'UF Destino': t.uf_destino or '',
                'Nome Tabela': t.nome_tabela or '',
                'Tipo Carga': t.tipo_carga or '',
                'Modalidade': t.modalidade or '',
                'Grupo Cliente': grupos.get(t.grupo_cliente_id, '') if t.grupo_cliente_id else '',
                'R$/kg': float(t.valor_kg) if t.valor_kg is not None else '',
                'Frete Min Peso': float(t.frete_minimo_peso) if t.frete_minimo_peso is not None else '',
                '% Valor': float(t.percentual_valor) if t.percentual_valor is not None else '',
                'Frete Min Valor': float(t.frete_minimo_valor) if t.frete_minimo_valor is not None else '',
                '% GRIS': float(t.percentual_gris) if t.percentual_gris is not None else '',
                'GRIS Min': float(t.gris_minimo) if t.gris_minimo is not None else '',
                '% ADV': float(t.percentual_adv) if t.percentual_adv is not None else '',
                'ADV Min': float(t.adv_minimo) if t.adv_minimo is not None else '',
                '% RCA': float(t.percentual_rca) if t.percentual_rca is not None else '',
                'Pedagio/100kg': float(t.pedagio_por_100kg) if t.pedagio_por_100kg is not None else '',
                'Despacho': float(t.valor_despacho) if t.valor_despacho is not None else '',
                'CTe': float(t.valor_cte) if t.valor_cte is not None else '',
                'TAS': float(t.valor_tas) if t.valor_tas is not None else '',
                'ICMS Incluso': _fmt_bool(t.icms_incluso),
                'ICMS Proprio %': float(t.icms_proprio) if t.icms_proprio is not None else '',
                'Ativo': _fmt_bool(t.ativo),
                'Criado Em': _fmt_datetime(t.criado_em),
                'Criado Por': t.criado_por or '',
            })

        df = pd.DataFrame(data)

        # ----- Sheet 2: Precos por Categoria de Moto -----
        precos = CarviaPrecoCategoriaMoto.query.join(
            CarviaTabelaFrete,
            CarviaPrecoCategoriaMoto.tabela_frete_id == CarviaTabelaFrete.id,
        ).join(
            CarviaCategoriaMoto,
            CarviaPrecoCategoriaMoto.categoria_moto_id == CarviaCategoriaMoto.id,
        ).order_by(
            CarviaTabelaFrete.nome_tabela.asc(),
            CarviaCategoriaMoto.ordem.asc(),
        ).all()

        precos_data = []
        # Pre-cache tabelas por id para resolver campos
        tabelas_by_id = {t.id: t for t in items}
        cats_by_id = {
            c.id: c.nome
            for c in CarviaCategoriaMoto.query.all()
        }

        for p in precos:
            tab = tabelas_by_id.get(p.tabela_frete_id)
            if not tab:
                # Tabela filtrada (ex: inativa) — buscar direto
                tab = CarviaTabelaFrete.query.get(p.tabela_frete_id)
            if not tab:
                continue
            precos_data.append({
                'Nome Tabela': tab.nome_tabela or '',
                'UF Origem': tab.uf_origem or '',
                'UF Destino': tab.uf_destino or '',
                'Tipo Carga': tab.tipo_carga or '',
                'Modalidade': tab.modalidade or '',
                'Grupo Cliente': grupos.get(tab.grupo_cliente_id, '') if tab.grupo_cliente_id else '',
                'Categoria Moto': cats_by_id.get(p.categoria_moto_id, ''),
                'Valor Unitario': float(p.valor_unitario) if p.valor_unitario is not None else '',
                'Ativo': _fmt_bool(p.ativo),
            })

        df_precos = pd.DataFrame(precos_data)

        # Gerar Excel com 2 sheets
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Tabelas Frete')
            _ajustar_largura_colunas(df, writer.sheets['Tabelas Frete'])

            if not df_precos.empty:
                df_precos.to_excel(writer, index=False, sheet_name='Precos Moto')
                _ajustar_largura_colunas(df_precos, writer.sheets['Precos Moto'])

        output.seek(0)
        timestamp = agora_utc_naive().strftime('%Y%m%d_%H%M')
        filename = f'carvia_tabelas_frete_{timestamp}.xlsx'

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename,
        )

    # =====================================================================
    # 14. Comissoes
    # =====================================================================
    @bp.route('/api/exportar/comissoes')  # type: ignore
    @login_required
    def exportar_comissoes():  # type: ignore
        """Exporta comissoes para Excel (2 sheets: Fechamentos + CTes)"""
        if _check_access():
            return redirect(url_for('main.dashboard'))

        # Verificar acesso a comissao
        if not (
            getattr(current_user, 'acesso_comissao_carvia', False)
            or getattr(current_user, 'perfil', '') == 'administrador'
        ):
            return redirect(url_for('main.dashboard'))

        status_filtro = request.args.get('status', '')
        vendedor_filtro = request.args.get('vendedor', '')

        query = db.session.query(CarviaComissaoFechamento)
        if status_filtro:
            query = query.filter(CarviaComissaoFechamento.status == status_filtro)
        if vendedor_filtro:
            busca_like = f'%{vendedor_filtro}%'
            query = query.filter(
                db.or_(
                    CarviaComissaoFechamento.vendedor_nome.ilike(busca_like),
                    CarviaComissaoFechamento.vendedor_email.ilike(busca_like),
                )
            )

        fechamentos = query.order_by(CarviaComissaoFechamento.data_inicio.desc().nullslast()).all()

        # Sheet 1: Fechamentos
        fechamentos_data = []
        fechamento_ids = []
        for f in fechamentos:
            fechamentos_data.append({
                'Numero': f.numero_fechamento,
                'Vendedor': f.vendedor_nome,
                'Email Vendedor': f.vendedor_email or '',
                'Periodo Inicio': _fmt_date(f.data_inicio),
                'Periodo Fim': _fmt_date(f.data_fim),
                'Percentual (%)': float(f.percentual * 100) if f.percentual else 0,
                'Qtd CTes': f.qtd_ctes,
                'Total Bruto': float(f.total_bruto or 0),
                'Total Comissao': float(f.total_comissao or 0),
                'Status': f.status,
                'Data Pagamento': _fmt_date(f.data_pagamento),
                'Pago Por': f.pago_por or '',
                'Criado Em': _fmt_datetime(f.criado_em),
                'Criado Por': f.criado_por or '',
                'Observacoes': f.observacoes or '',
            })
            fechamento_ids.append(f.id)

        df_fechamentos = pd.DataFrame(fechamentos_data)

        # Sheet 2: CTes (de todos os fechamentos filtrados)
        ctes_data = []
        if fechamento_ids:
            ctes = CarviaComissaoFechamentoCte.query.filter(
                CarviaComissaoFechamentoCte.fechamento_id.in_(fechamento_ids),
                CarviaComissaoFechamentoCte.excluido.is_(False),
            ).order_by(
                CarviaComissaoFechamentoCte.fechamento_id.asc(),
                CarviaComissaoFechamentoCte.cte_data_emissao.asc(),
            ).all()

            for c in ctes:
                ctes_data.append({
                    'Fechamento': c.fechamento.numero_fechamento if c.fechamento else '',
                    'CTe Numero': c.cte_numero,
                    'Data Emissao': _fmt_date(c.cte_data_emissao),
                    'Valor CTe': float(c.valor_cte_snapshot or 0),
                    'Percentual (%)': float(c.percentual_snapshot * 100) if c.percentual_snapshot else 0,
                    'Valor Comissao': float(c.valor_comissao or 0),
                    'Cliente': c.operacao.nome_cliente if c.operacao else '',
                    'UF Destino': c.operacao.uf_destino if c.operacao else '',
                    'Incluido Por': c.incluido_por or '',
                    'Incluido Em': _fmt_datetime(c.incluido_em),
                })

        df_ctes = pd.DataFrame(ctes_data)

        # Gerar Excel com 2 sheets
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_fechamentos.to_excel(writer, index=False, sheet_name='Fechamentos')
            if not df_fechamentos.empty:
                _ajustar_largura_colunas(df_fechamentos, writer.sheets['Fechamentos'])

            df_ctes.to_excel(writer, index=False, sheet_name='CTes')
            if not df_ctes.empty:
                _ajustar_largura_colunas(df_ctes, writer.sheets['CTes'])

        output.seek(0)
        timestamp = agora_utc_naive().strftime('%Y%m%d_%H%M')
        filename = f'carvia_comissoes_{timestamp}.xlsx'

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename,
        )
