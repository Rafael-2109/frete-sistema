"""
Rotas de Exportacao Excel CarVia — Todas as entidades
"""

import logging
from datetime import datetime
from io import BytesIO

import pandas as pd
from flask import request, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.carvia.models import (
    CarviaNf, CarviaOperacao, CarviaOperacaoNf,
    CarviaSubcontrato, CarviaCteComplementar,
    CarviaCustoEntrega, CarviaFaturaCliente,
    CarviaFaturaTransportadora, CarviaDespesa,
    CarviaReceita,
    CarviaModeloMoto, CarviaCategoriaMoto,
    CarviaCidadeAtendida, CarviaTabelaFrete,
    CarviaGrupoCliente, CarviaPrecoCategoriaMoto,
    CarviaComissaoFechamento, CarviaComissaoFechamentoCte,
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
            # Subquery: NF ids vinculadas a CTe com numero ou CTRC matching
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

        # Filtro UF destinatario (exact match)
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

        items = query.all()

        if not items:
            flash('Nenhum dado para exportar.', 'warning')
            return redirect(url_for('carvia.listar_nfs'))

        # Cross-links: custos e ctes comp por NF (via operacoes)
        nf_ids_all = [nf.id for nf in items]
        # Mapa nf_id -> [operacao_ids]
        from collections import defaultdict
        nf_op_map = defaultdict(set)
        if nf_ids_all:
            junctions = db.session.query(
                CarviaOperacaoNf.nf_id, CarviaOperacaoNf.operacao_id
            ).filter(CarviaOperacaoNf.nf_id.in_(nf_ids_all)).all()
            for j_nf_id, j_op_id in junctions:
                nf_op_map[j_nf_id].add(j_op_id)

        all_op_ids = set()
        for ops in nf_op_map.values():
            all_op_ids.update(ops)

        # Buscar CTe + CTRC das operacoes vinculadas
        cte_por_op = {}
        ctrc_por_op = {}
        if all_op_ids:
            op_rows = db.session.query(
                CarviaOperacao.id, CarviaOperacao.cte_numero, CarviaOperacao.ctrc_numero
            ).filter(CarviaOperacao.id.in_(all_op_ids)).all()
            cte_por_op = {o_id: cte for o_id, cte, _ in op_rows}
            ctrc_por_op = {o_id: ctrc for o_id, _, ctrc in op_rows}

        custos_por_op = defaultdict(int)
        custos_valor_por_op = defaultdict(float)
        comps_por_op = defaultdict(int)
        comps_valor_por_op = defaultdict(float)
        if all_op_ids:
            custos_rows = db.session.query(
                CarviaCustoEntrega.operacao_id,
                func.count(CarviaCustoEntrega.id),
                func.coalesce(func.sum(CarviaCustoEntrega.valor), 0),
            ).filter(
                CarviaCustoEntrega.operacao_id.in_(all_op_ids)
            ).group_by(CarviaCustoEntrega.operacao_id).all()
            for op_id, cnt, val in custos_rows:
                custos_por_op[op_id] = cnt
                custos_valor_por_op[op_id] = float(val)

            comps_rows = db.session.query(
                CarviaCteComplementar.operacao_id,
                func.count(CarviaCteComplementar.id),
                func.coalesce(func.sum(CarviaCteComplementar.cte_valor), 0),
            ).filter(
                CarviaCteComplementar.operacao_id.in_(all_op_ids)
            ).group_by(CarviaCteComplementar.operacao_id).all()
            for op_id, cnt, val in comps_rows:
                comps_por_op[op_id] = cnt
                comps_valor_por_op[op_id] = float(val)

        data = []
        for nf in items:
            ops = nf_op_map.get(nf.id, set())
            qtd_custos = sum(custos_por_op.get(o, 0) for o in ops)
            total_custos = sum(custos_valor_por_op.get(o, 0) for o in ops)
            qtd_comps = sum(comps_por_op.get(o, 0) for o in ops)
            total_comps = sum(comps_valor_por_op.get(o, 0) for o in ops)

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
                'CTe': ', '.join(filter(None, [cte_por_op.get(o) for o in ops])),
                'CTRC': ', '.join(filter(None, [ctrc_por_op.get(o) for o in ops])),
                'Tipo Fonte': nf.tipo_fonte or '',
                'Status': nf.status or '',
                'Qtd Custos Entrega': qtd_custos,
                'Valor Custos Entrega': total_custos,
                'Qtd CTes Complementares': qtd_comps,
                'Valor CTes Complementares': total_comps,
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

        # Buscar faturas vinculadas para coluna Fatura
        fat_map = {}
        fat_ids = [op.fatura_cliente_id for op in items if op.fatura_cliente_id]
        if fat_ids:
            faturas = db.session.query(
                CarviaFaturaCliente.id, CarviaFaturaCliente.numero_fatura
            ).filter(CarviaFaturaCliente.id.in_(fat_ids)).all()
            fat_map = {f_id: num for f_id, num in faturas}

        # Batch: primeira NF por operacao (regra CTe = 1 par unico) para
        # preencher colunas Emitente / Destinatario
        from app.carvia.utils.tomador import tomador_label_para_export
        op_ids = [op.id for op in items]
        primeira_nf_por_op = {}
        if op_ids:
            rows = db.session.query(
                CarviaOperacaoNf.operacao_id,
                CarviaNf.nome_emitente, CarviaNf.cnpj_emitente,
                CarviaNf.nome_destinatario, CarviaNf.cnpj_destinatario,
            ).join(
                CarviaNf, CarviaNf.id == CarviaOperacaoNf.nf_id
            ).filter(
                CarviaOperacaoNf.operacao_id.in_(op_ids)
            ).all()
            for row in rows:
                oid = row[0]
                if oid not in primeira_nf_por_op:
                    primeira_nf_por_op[oid] = {
                        'emit_nome': row[1] or '',
                        'emit_cnpj': row[2] or '',
                        'dest_nome': row[3] or '',
                        'dest_cnpj': row[4] or '',
                    }

        data = []
        for op in items:
            nf_info = primeira_nf_por_op.get(op.id) or {}
            # Fallback para op.cnpj_cliente quando nao ha NF vinculada (manual/freteiro)
            emit_nome = nf_info.get('emit_nome') or op.nome_cliente or ''
            emit_cnpj = nf_info.get('emit_cnpj') or op.cnpj_cliente or ''
            data.append({
                'ID': op.id,
                'CTe Numero': op.cte_numero or '',
                'CTRC': op.ctrc_numero or '',
                'Emitente': emit_nome,
                'CNPJ Emitente': emit_cnpj,
                'Destinatario': nf_info.get('dest_nome', ''),
                'CNPJ Destinatario': nf_info.get('dest_cnpj', ''),
                'Tomador': tomador_label_para_export(op.cte_tomador),
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
            # Hierarquia alinhada com listagem (fatura_routes.py:1241) e card
            # Analise de Valores: valor_pago > valor_considerado > valor_acertado > valor_cotado.
            'valor_final': func.coalesce(
                CarviaSubcontrato.valor_pago,
                CarviaSubcontrato.valor_considerado,
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

        data = []
        for sub in items:
            op = sub_op_map.get(sub.operacao_id)
            # Valor Final alinhado com listagem + card Analise (hierarquia de 4 niveis)
            valor_final_hierarquico = (
                sub.valor_pago
                or sub.valor_considerado
                or sub.valor_acertado
                or sub.valor_cotado
                or 0
            )
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
                'Valor Considerado': float(sub.valor_considerado or 0) if sub.valor_considerado else '',
                'Valor Pago': float(sub.valor_pago or 0) if sub.valor_pago else '',
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

        # Buscar faturas vinculadas
        fat_map = {}
        fat_ids = [c.fatura_cliente_id for c in items if c.fatura_cliente_id]
        if fat_ids:
            faturas = db.session.query(
                CarviaFaturaCliente.id, CarviaFaturaCliente.numero_fatura
            ).filter(CarviaFaturaCliente.id.in_(fat_ids)).all()
            fat_map = {f_id: num for f_id, num in faturas}

        # Buscar CTe numero + CTRC da operacao pai
        op_ids = list({c.operacao_id for c in items})
        op_map = {}
        op_ctrc_map = {}
        if op_ids:
            ops = db.session.query(
                CarviaOperacao.id, CarviaOperacao.cte_numero, CarviaOperacao.ctrc_numero
            ).filter(CarviaOperacao.id.in_(op_ids)).all()
            op_map = {o_id: cte for o_id, cte, _ in ops}
            op_ctrc_map = {o_id: ctrc for o_id, _, ctrc in ops}

        # Custos vinculados por cte_complementar_id
        from collections import defaultdict
        custos_por_comp = defaultdict(int)
        custos_valor_por_comp = defaultdict(float)
        comp_item_ids = [c.id for c in items]
        if comp_item_ids:
            for comp_id, cnt, val in db.session.query(
                CarviaCustoEntrega.cte_complementar_id,
                func.count(CarviaCustoEntrega.id),
                func.coalesce(func.sum(CarviaCustoEntrega.valor), 0),
            ).filter(
                CarviaCustoEntrega.cte_complementar_id.in_(comp_item_ids)
            ).group_by(CarviaCustoEntrega.cte_complementar_id).all():
                custos_por_comp[comp_id] = cnt
                custos_valor_por_comp[comp_id] = float(val)

        data = []
        for c in items:
            data.append({
                'Numero Comp': c.numero_comp or '',
                'CTe Numero': op_map.get(c.operacao_id, ''),
                'CTRC CTe Pai': op_ctrc_map.get(c.operacao_id, ''),
                'CTRC': c.ctrc_numero or '',
                'Operacao ID': c.operacao_id,
                'Cliente': c.nome_cliente or '',
                'CNPJ Cliente': c.cnpj_cliente or '',
                'Valor CTe': float(c.cte_valor or 0),
                'Data Emissao': _fmt_date(c.cte_data_emissao),
                'Status': c.status or '',
                'Fatura': fat_map.get(c.fatura_cliente_id, ''),
                'Qtd Custos Entrega': custos_por_comp.get(c.id, 0),
                'Valor Custos Entrega': custos_valor_por_comp.get(c.id, 0),
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
        """Exporta faturas cliente para Excel com mesmos filtros da listagem"""
        if _check_access():
            return redirect(url_for('main.dashboard'))

        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        cliente_filtro = request.args.get('cliente', '')
        tipo_frete_filtro = request.args.get('tipo_frete', '')
        data_emissao_de = request.args.get('data_emissao_de', '')
        data_emissao_ate = request.args.get('data_emissao_ate', '')
        sort = request.args.get('sort', 'data_emissao')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaFaturaCliente)

        if status_filtro:
            query = query.filter(CarviaFaturaCliente.status == status_filtro)
        if tipo_frete_filtro:
            query = query.filter(CarviaFaturaCliente.tipo_frete == tipo_frete_filtro)
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

        # Custos de entrega via operacoes vinculadas a fatura
        from collections import defaultdict
        fat_ids_all = [f.id for f in items]
        fat_custos = defaultdict(int)
        fat_custos_valor = defaultdict(float)
        if fat_ids_all:
            # operacoes por fatura
            fat_op_rows = db.session.query(
                CarviaOperacao.fatura_cliente_id,
                CarviaOperacao.id,
            ).filter(
                CarviaOperacao.fatura_cliente_id.in_(fat_ids_all)
            ).all()

            fat_op_map = defaultdict(set)
            all_fc_op_ids = set()
            for fc_id, o_id in fat_op_rows:
                fat_op_map[fc_id].add(o_id)
                all_fc_op_ids.add(o_id)

            if all_fc_op_ids:
                custos_rows = db.session.query(
                    CarviaCustoEntrega.operacao_id,
                    func.count(CarviaCustoEntrega.id),
                    func.coalesce(func.sum(CarviaCustoEntrega.valor), 0),
                ).filter(
                    CarviaCustoEntrega.operacao_id.in_(all_fc_op_ids)
                ).group_by(CarviaCustoEntrega.operacao_id).all()

                op_custo_cnt = {}
                op_custo_val = {}
                for o_id, cnt, val in custos_rows:
                    op_custo_cnt[o_id] = cnt
                    op_custo_val[o_id] = float(val)

                for fc_id, op_set in fat_op_map.items():
                    for o_id in op_set:
                        fat_custos[fc_id] += op_custo_cnt.get(o_id, 0)
                        fat_custos_valor[fc_id] += op_custo_val.get(o_id, 0)

        # Batch: primeira (nf + cte_tomador) por fatura via join triplo
        # fatura -> operacao -> junction -> nf
        from app.carvia.utils.tomador import tomador_label_para_export
        primeira_nf_por_fatura = {}
        if fat_ids_all:
            rows_papeis = db.session.query(
                CarviaOperacao.fatura_cliente_id,
                CarviaOperacao.cte_tomador,
                CarviaNf.nome_emitente, CarviaNf.cnpj_emitente,
                CarviaNf.nome_destinatario, CarviaNf.cnpj_destinatario,
            ).join(
                CarviaOperacaoNf, CarviaOperacaoNf.operacao_id == CarviaOperacao.id
            ).join(
                CarviaNf, CarviaNf.id == CarviaOperacaoNf.nf_id
            ).filter(
                CarviaOperacao.fatura_cliente_id.in_(fat_ids_all)
            ).all()
            for row in rows_papeis:
                fid, cte_tom, emit_nome, emit_cnpj, dest_nome, dest_cnpj = row
                if fid in primeira_nf_por_fatura:
                    # Atualiza tomador se ainda nao setado
                    if not primeira_nf_por_fatura[fid]['tomador'] and cte_tom:
                        primeira_nf_por_fatura[fid]['tomador'] = cte_tom
                    continue
                primeira_nf_por_fatura[fid] = {
                    'emit_nome': emit_nome or '',
                    'emit_cnpj': emit_cnpj or '',
                    'dest_nome': dest_nome or '',
                    'dest_cnpj': dest_cnpj or '',
                    'tomador': cte_tom,
                }

        data = []
        for f in items:
            papeis = primeira_nf_por_fatura.get(f.id) or {}
            data.append({
                'Numero Fatura': f.numero_fatura or '',
                'Emitente': papeis.get('emit_nome', ''),
                'CNPJ Emitente': papeis.get('emit_cnpj', ''),
                'Destinatario': papeis.get('dest_nome', ''),
                'CNPJ Destinatario': papeis.get('dest_cnpj', ''),
                'Tomador': tomador_label_para_export(papeis.get('tomador')),
                'Data Emissao': _fmt_date(f.data_emissao),
                'Vencimento': _fmt_date(f.vencimento),
                'Valor Total': float(f.valor_total or 0),
                'Tipo Frete': f.tipo_frete or '',
                'Status': f.status or '',
                'Qtd Custos Entrega': fat_custos.get(f.id, 0),
                'Valor Custos Entrega': fat_custos_valor.get(f.id, 0),
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

        # Custos e CTes comp via subcontratos -> operacoes
        from collections import defaultdict
        ft_ids_all = [f.id for f in items]
        ft_custos = defaultdict(int)
        ft_custos_valor = defaultdict(float)
        ft_comps = defaultdict(int)
        ft_comps_valor = defaultdict(float)
        if ft_ids_all:
            sub_rows = db.session.query(
                CarviaSubcontrato.fatura_transportadora_id,
                CarviaSubcontrato.operacao_id,
            ).filter(
                CarviaSubcontrato.fatura_transportadora_id.in_(ft_ids_all),
                CarviaSubcontrato.operacao_id.isnot(None),
            ).all()

            ft_op_map = defaultdict(set)
            all_ft_op_ids = set()
            for ft_id, o_id in sub_rows:
                ft_op_map[ft_id].add(o_id)
                all_ft_op_ids.add(o_id)

            if all_ft_op_ids:
                op_custo_cnt = {}
                op_custo_val = {}
                for o_id, cnt, val in db.session.query(
                    CarviaCustoEntrega.operacao_id,
                    func.count(CarviaCustoEntrega.id),
                    func.coalesce(func.sum(CarviaCustoEntrega.valor), 0),
                ).filter(
                    CarviaCustoEntrega.operacao_id.in_(all_ft_op_ids)
                ).group_by(CarviaCustoEntrega.operacao_id).all():
                    op_custo_cnt[o_id] = cnt
                    op_custo_val[o_id] = float(val)

                op_comp_cnt = {}
                op_comp_val = {}
                for o_id, cnt, val in db.session.query(
                    CarviaCteComplementar.operacao_id,
                    func.count(CarviaCteComplementar.id),
                    func.coalesce(func.sum(CarviaCteComplementar.cte_valor), 0),
                ).filter(
                    CarviaCteComplementar.operacao_id.in_(all_ft_op_ids)
                ).group_by(CarviaCteComplementar.operacao_id).all():
                    op_comp_cnt[o_id] = cnt
                    op_comp_val[o_id] = float(val)

                for ft_id, op_set in ft_op_map.items():
                    for o_id in op_set:
                        ft_custos[ft_id] += op_custo_cnt.get(o_id, 0)
                        ft_custos_valor[ft_id] += op_custo_val.get(o_id, 0)
                        ft_comps[ft_id] += op_comp_cnt.get(o_id, 0)
                        ft_comps_valor[ft_id] += op_comp_val.get(o_id, 0)

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
                'Qtd Custos Entrega': ft_custos.get(f.id, 0),
                'Valor Custos Entrega': ft_custos_valor.get(f.id, 0),
                'Qtd CTes Comp': ft_comps.get(f.id, 0),
                'Valor CTes Comp': ft_comps_valor.get(f.id, 0),
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
