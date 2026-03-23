"""
Rotas de Exportacao Excel CarVia — Todas as entidades
"""

import logging
from io import BytesIO

import pandas as pd
from flask import request, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.carvia.models import (
    CarviaNf, CarviaOperacao,
    CarviaSubcontrato, CarviaCteComplementar,
    CarviaCustoEntrega, CarviaFaturaCliente,
    CarviaFaturaTransportadora, CarviaDespesa,
    CarviaReceita,
)
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


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
    # 1. NFs
    # =====================================================================
    @bp.route('/api/exportar/nfs')
    @login_required
    def exportar_nfs():
        """Exporta NFs para Excel com mesmos filtros da listagem"""
        if _check_access():
            return redirect(url_for('main.dashboard'))

        busca = request.args.get('busca', '')
        tipo_filtro = request.args.get('tipo_fonte', '')
        status_filtro = request.args.get('status', '')
        sort = request.args.get('sort', 'criado_em')
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

        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaNf.numero_nf.ilike(busca_like),
                    CarviaNf.nome_emitente.ilike(busca_like),
                    CarviaNf.cnpj_emitente.ilike(busca_like),
                    CarviaNf.nome_destinatario.ilike(busca_like),
                    CarviaNf.chave_acesso_nf.ilike(busca_like),
                )
            )

        sortable_columns = {
            'numero_nf': func.lpad(func.coalesce(CarviaNf.numero_nf, ''), 20, '0'),
            'emitente': CarviaNf.nome_emitente,
            'valor_total': CarviaNf.valor_total,
            'criado_em': CarviaNf.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaNf.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        items = query.all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_nfs'))

        data = []
        for nf in items:
            data.append({
                'Numero NF': nf.numero_nf,
                'Serie': nf.serie_nf or '',
                'Chave Acesso': nf.chave_acesso_nf or '',
                'Data Emissao': _fmt_date(nf.data_emissao),
                'CNPJ Emitente': nf.cnpj_emitente or '',
                'Nome Emitente': nf.nome_emitente or '',
                'UF Emitente': nf.uf_emitente or '',
                'CNPJ Destinatario': nf.cnpj_destinatario or '',
                'Nome Destinatario': nf.nome_destinatario or '',
                'UF Destino': nf.uf_destinatario or '',
                'Valor Total': float(nf.valor_total or 0),
                'Peso Bruto': float(nf.peso_bruto or 0),
                'Qtd Volumes': nf.quantidade_volumes or 0,
                'Tipo Fonte': nf.tipo_fonte or '',
                'Status': nf.status or '',
                'Criado Em': _fmt_datetime(nf.criado_em),
                'Criado Por': nf.criado_por or '',
            })

        df = pd.DataFrame(data)
        return _gerar_excel(df, 'NFs', 'nfs')

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
        sort = request.args.get('sort', 'criado_em')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaOperacao)

        if status_filtro:
            query = query.filter(CarviaOperacao.status == status_filtro)
        if tipo_filtro:
            query = query.filter(CarviaOperacao.tipo_entrada == tipo_filtro)
        if uf_filtro:
            query = query.filter(CarviaOperacao.uf_destino == uf_filtro.upper())
        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaOperacao.nome_cliente.ilike(busca_like),
                    CarviaOperacao.cnpj_cliente.ilike(busca_like),
                    CarviaOperacao.cte_numero.ilike(busca_like),
                    CarviaOperacao.cidade_destino.ilike(busca_like),
                )
            )

        sortable_columns = {
            'cte_numero': func.lpad(func.coalesce(CarviaOperacao.cte_numero, ''), 20, '0'),
            'nome_cliente': CarviaOperacao.nome_cliente,
            'peso_utilizado': CarviaOperacao.peso_utilizado,
            'cte_valor': CarviaOperacao.cte_valor,
            'status': CarviaOperacao.status,
            'criado_em': CarviaOperacao.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaOperacao.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        items = query.all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_operacoes'))

        # Buscar faturas vinculadas para coluna Fatura
        fat_map = {}
        fat_ids = [op.fatura_cliente_id for op in items if op.fatura_cliente_id]
        if fat_ids:
            faturas = db.session.query(
                CarviaFaturaCliente.id, CarviaFaturaCliente.numero_fatura
            ).filter(CarviaFaturaCliente.id.in_(fat_ids)).all()
            fat_map = {f_id: num for f_id, num in faturas}

        data = []
        for op in items:
            data.append({
                'ID': op.id,
                'CTe Numero': op.cte_numero or '',
                'Cliente': op.nome_cliente or '',
                'CNPJ Cliente': op.cnpj_cliente or '',
                'Origem': f'{op.cidade_origem or ""}/{op.uf_origem or ""}',
                'Destino': f'{op.cidade_destino or ""}/{op.uf_destino or ""}',
                'Peso Bruto': float(op.peso_bruto or 0),
                'Peso Cubado': float(op.peso_cubado or 0),
                'Peso Utilizado': float(op.peso_utilizado or 0),
                'Valor CTe': float(op.cte_valor or 0),
                'Valor Mercadoria': float(op.valor_mercadoria or 0),
                'Tipo Entrada': op.tipo_entrada or '',
                'Status': op.status or '',
                'Fatura': fat_map.get(op.fatura_cliente_id, ''),
                'Criado Em': _fmt_datetime(op.criado_em),
                'Criado Por': op.criado_por or '',
            })

        df = pd.DataFrame(data)
        return _gerar_excel(df, 'Operacoes', 'operacoes')

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
        sort = request.args.get('sort', 'criado_em')
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
            'valor_final': func.coalesce(CarviaSubcontrato.valor_acertado, CarviaSubcontrato.valor_cotado),
            'status': CarviaSubcontrato.status,
            'criado_em': CarviaSubcontrato.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaSubcontrato.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        items = query.all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_subcontratos'))

        data = []
        for sub in items:
            data.append({
                'ID': sub.id,
                'Operacao ID': sub.operacao_id,
                'Transportadora': sub.transportadora.razao_social if sub.transportadora else '',
                'CTe Numero': sub.cte_numero or '',
                'Valor CTe': float(sub.cte_valor or 0),
                'Valor Cotado': float(sub.valor_cotado or 0),
                'Valor Acertado': float(sub.valor_acertado or 0) if sub.valor_acertado else '',
                'Valor Final': float(sub.valor_final or 0) if sub.valor_final else 0,
                'Status': sub.status or '',
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
        sort = request.args.get('sort', 'criado_em')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaCteComplementar)

        if operacao_filtro:
            query = query.filter(CarviaCteComplementar.operacao_id == int(operacao_filtro))
        if status_filtro:
            query = query.filter(CarviaCteComplementar.status == status_filtro)
        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaCteComplementar.numero_comp.ilike(busca_like),
                    CarviaCteComplementar.cnpj_cliente.ilike(busca_like),
                    CarviaCteComplementar.nome_cliente.ilike(busca_like),
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
        sort_col = sortable_columns.get(sort, CarviaCteComplementar.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        items = query.all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_ctes_complementares'))

        # Buscar faturas vinculadas
        fat_map = {}
        fat_ids = [c.fatura_cliente_id for c in items if c.fatura_cliente_id]
        if fat_ids:
            faturas = db.session.query(
                CarviaFaturaCliente.id, CarviaFaturaCliente.numero_fatura
            ).filter(CarviaFaturaCliente.id.in_(fat_ids)).all()
            fat_map = {f_id: num for f_id, num in faturas}

        # Buscar CTe numero da operacao pai
        op_ids = list({c.operacao_id for c in items})
        op_map = {}
        if op_ids:
            ops = db.session.query(
                CarviaOperacao.id, CarviaOperacao.cte_numero
            ).filter(CarviaOperacao.id.in_(op_ids)).all()
            op_map = {o_id: cte for o_id, cte in ops}

        data = []
        for c in items:
            data.append({
                'Numero Comp': c.numero_comp or '',
                'CTe Numero': op_map.get(c.operacao_id, ''),
                'Operacao ID': c.operacao_id,
                'Cliente': c.nome_cliente or '',
                'CNPJ Cliente': c.cnpj_cliente or '',
                'Valor CTe': float(c.cte_valor or 0),
                'Data Emissao': _fmt_date(c.cte_data_emissao),
                'Status': c.status or '',
                'Fatura': fat_map.get(c.fatura_cliente_id, ''),
                'Criado Em': _fmt_datetime(c.criado_em),
                'Criado Por': c.criado_por or '',
            })

        df = pd.DataFrame(data)
        return _gerar_excel(df, 'CTe Complementares', 'ctes_complementares')

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

        data = []
        for c in items:
            data.append({
                'Numero Custo': c.numero_custo or '',
                'Operacao ID': c.operacao_id,
                'CTe Comp': comp_map.get(c.cte_complementar_id, ''),
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
        """Exporta faturas cliente para Excel com mesmos filtros da listagem"""
        if _check_access():
            return redirect(url_for('main.dashboard'))

        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        tipo_frete_filtro = request.args.get('tipo_frete', '')
        sort = request.args.get('sort', 'criado_em')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaFaturaCliente)

        if status_filtro:
            query = query.filter(CarviaFaturaCliente.status == status_filtro)
        if tipo_frete_filtro:
            query = query.filter(CarviaFaturaCliente.tipo_frete == tipo_frete_filtro)
        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaFaturaCliente.nome_cliente.ilike(busca_like),
                    CarviaFaturaCliente.cnpj_cliente.ilike(busca_like),
                    CarviaFaturaCliente.numero_fatura.ilike(busca_like),
                )
            )

        sortable_columns = {
            'numero_fatura': func.lpad(func.coalesce(CarviaFaturaCliente.numero_fatura, ''), 20, '0'),
            'nome_cliente': CarviaFaturaCliente.nome_cliente,
            'data_emissao': CarviaFaturaCliente.data_emissao,
            'vencimento': CarviaFaturaCliente.vencimento,
            'valor_total': CarviaFaturaCliente.valor_total,
            'status': CarviaFaturaCliente.status,
            'criado_em': CarviaFaturaCliente.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaFaturaCliente.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        items = query.all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_faturas_cliente'))

        data = []
        for f in items:
            data.append({
                'Numero Fatura': f.numero_fatura or '',
                'Cliente': f.nome_cliente or '',
                'CNPJ Cliente': f.cnpj_cliente or '',
                'Data Emissao': _fmt_date(f.data_emissao),
                'Vencimento': _fmt_date(f.vencimento),
                'Valor Total': float(f.valor_total or 0),
                'Tipo Frete': f.tipo_frete or '',
                'Status': f.status or '',
                'Pago Em': _fmt_datetime(f.pago_em),
                'Pago Por': f.pago_por or '',
                'Conciliado': _fmt_bool(f.conciliado),
                'Total Conciliado': float(f.total_conciliado or 0),
                'Criado Em': _fmt_datetime(f.criado_em),
                'Criado Por': f.criado_por or '',
            })

        df = pd.DataFrame(data)
        return _gerar_excel(df, 'Faturas Cliente', 'faturas_cliente')

    # =====================================================================
    # 7. Faturas Transportadora
    # =====================================================================
    @bp.route('/api/exportar/faturas-transportadora')
    @login_required
    def exportar_faturas_transportadora():
        """Exporta faturas transportadora para Excel com mesmos filtros da listagem"""
        if _check_access():
            return redirect(url_for('main.dashboard'))

        status_filtro = request.args.get('status', '')
        pagamento_filtro = request.args.get('pagamento', '')
        busca = request.args.get('busca', '')
        sort = request.args.get('sort', 'criado_em')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaFaturaTransportadora)

        if status_filtro:
            query = query.filter(
                CarviaFaturaTransportadora.status_conferencia == status_filtro
            )
        if pagamento_filtro:
            query = query.filter(
                CarviaFaturaTransportadora.status_pagamento == pagamento_filtro
            )
        if busca:
            from app.transportadoras.models import Transportadora
            busca_like = f'%{busca}%'
            query = query.outerjoin(
                Transportadora,
                CarviaFaturaTransportadora.transportadora_id == Transportadora.id,
            ).filter(
                db.or_(
                    CarviaFaturaTransportadora.numero_fatura.ilike(busca_like),
                    Transportadora.razao_social.ilike(busca_like),
                    Transportadora.cnpj.ilike(busca_like),
                )
            )

        sortable_columns = {
            'numero_fatura': func.lpad(func.coalesce(CarviaFaturaTransportadora.numero_fatura, ''), 20, '0'),
            'data_emissao': CarviaFaturaTransportadora.data_emissao,
            'vencimento': CarviaFaturaTransportadora.vencimento,
            'valor_total': CarviaFaturaTransportadora.valor_total,
            'status_conferencia': CarviaFaturaTransportadora.status_conferencia,
            'criado_em': CarviaFaturaTransportadora.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaFaturaTransportadora.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        items = query.all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_faturas_transportadora'))

        data = []
        for f in items:
            data.append({
                'Numero Fatura': f.numero_fatura or '',
                'Transportadora': f.transportadora.razao_social if f.transportadora else '',
                'Data Emissao': _fmt_date(f.data_emissao),
                'Vencimento': _fmt_date(f.vencimento),
                'Valor Total': float(f.valor_total or 0),
                'Status Conferencia': f.status_conferencia or '',
                'Conferido Por': f.conferido_por or '',
                'Conferido Em': _fmt_datetime(f.conferido_em),
                'Status Pagamento': f.status_pagamento or '',
                'Pago Em': _fmt_datetime(f.pago_em),
                'Pago Por': f.pago_por or '',
                'Conciliado': _fmt_bool(f.conciliado),
                'Total Conciliado': float(f.total_conciliado or 0),
                'Criado Em': _fmt_datetime(f.criado_em),
                'Criado Por': f.criado_por or '',
            })

        df = pd.DataFrame(data)
        return _gerar_excel(df, 'Faturas Transportadora', 'faturas_transportadora')

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
