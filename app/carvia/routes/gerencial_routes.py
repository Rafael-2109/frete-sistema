"""
Rotas Gerenciais CarVia — Metricas analiticas (admin-only)
==========================================================

Tela com valor por UF/mes, valor por unidade (moto), valor por kg cubado.
Exportacao do relatorio gerencial NF x CTe com rateio cascateado.
"""

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

import pandas as pd
from flask import render_template, request, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.utils.auth_decorators import require_admin
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


def register_gerencial_routes(bp):

    @bp.route('/gerencial')  # type: ignore
    @login_required
    @require_admin
    def gerencial():  # type: ignore
        """Tela gerencial — metricas agregadas por UF/mes"""
        if not getattr(current_user, 'sistema_carvia', False):
            from flask import flash, redirect, url_for
            flash('Acesso negado. Voce nao tem permissao para o sistema CarVia.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.financeiro.gerencial_service import GerencialService
        from app.utils.timezone import agora_brasil_naive

        hoje = agora_brasil_naive().date()

        # Defaults: mes atual
        data_inicio_str = request.args.get('data_inicio')
        data_fim_str = request.args.get('data_fim')

        try:
            data_inicio = (
                date.fromisoformat(data_inicio_str)
                if data_inicio_str
                else hoje.replace(day=1)
            )
        except ValueError:
            data_inicio = hoje.replace(day=1)

        try:
            data_fim = (
                date.fromisoformat(data_fim_str)
                if data_fim_str
                else hoje
            )
        except ValueError:
            data_fim = hoje

        service = GerencialService()

        try:
            metricas = service.obter_metricas_por_uf_mes(data_inicio, data_fim)
            totais = service.obter_totais_periodo(data_inicio, data_fim)
        except Exception as e:
            logger.error(f"Erro ao carregar metricas gerenciais CarVia: {e}")
            metricas = []
            totais = {
                'valor_total': 0,
                'qtd_motos': 0,
                'peso_efetivo': 0,
                'valor_por_unidade': None,
                'valor_por_kg_cubado': None,
                'total_despesas': 0,
            }

        try:
            itens_rateio = service.obter_itens_nf_com_rateio(data_inicio, data_fim)
        except Exception as e:
            logger.error(f"Erro ao carregar itens NF com rateio CarVia: {e}")
            itens_rateio = []

        return render_template(
            'carvia/gerencial.html',
            metricas=metricas,
            totais=totais,
            itens_rateio=itens_rateio,
            data_inicio=data_inicio.isoformat(),
            data_fim=data_fim.isoformat(),
        )

    @bp.route('/api/exportar/relatorio-gerencial')
    @login_required
    @require_admin
    def exportar_relatorio_gerencial():  # type: ignore
        """Exporta relatorio gerencial NF x CTe com rateio cascateado.

        Rateio para 1 CTe : N NFs (mesmo criterio para todas NFs do CTe):
        1. Motos: se QUALQUER NF do grupo tem motos → rateia por qtd motos
        2. Peso: se nenhuma NF tem motos mas tem peso → rateia por peso_bruto
        3. Divisao igual: se nao tem motos nem peso → divide igualmente
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import (
            CarviaNf, CarviaOperacao, CarviaOperacaoNf,
            CarviaNfVeiculo, CarviaFaturaCliente,
        )

        # --- 1. Query principal: NFs + Operacao + Fatura + Motos ---
        motos_subq = (
            db.session.query(
                CarviaNfVeiculo.nf_id,
                func.count(CarviaNfVeiculo.id).label('qtd_motos'),
            )
            .group_by(CarviaNfVeiculo.nf_id)
            .subquery()
        )

        nfs_por_op_subq = (
            db.session.query(
                CarviaOperacaoNf.operacao_id,
                func.count(CarviaOperacaoNf.nf_id).label('total_nfs_no_cte'),
            )
            .group_by(CarviaOperacaoNf.operacao_id)
            .subquery()
        )

        rows = (
            db.session.query(
                CarviaNf.id.label('nf_id'),
                CarviaNf.numero_nf,
                CarviaNf.serie_nf,
                CarviaNf.data_emissao.label('data_nf'),
                CarviaNf.cnpj_emitente,
                CarviaNf.nome_emitente,
                CarviaNf.cnpj_destinatario,
                CarviaNf.nome_destinatario,
                CarviaNf.uf_destinatario,
                CarviaNf.cidade_destinatario,
                CarviaNf.valor_total.label('valor_nf'),
                CarviaNf.peso_bruto,
                CarviaNf.quantidade_volumes,
                CarviaOperacao.id.label('operacao_id'),
                CarviaOperacao.cte_numero,
                CarviaOperacao.cte_valor,
                CarviaOperacao.cte_data_emissao.label('data_cte'),
                CarviaOperacao.nome_cliente,
                CarviaOperacao.status.label('status_operacao'),
                CarviaFaturaCliente.numero_fatura,
                CarviaFaturaCliente.data_emissao.label('data_fatura'),
                func.coalesce(motos_subq.c.qtd_motos, 0).label('qtd_motos'),
                func.coalesce(nfs_por_op_subq.c.total_nfs_no_cte, 1).label('total_nfs_no_cte'),
            )
            .outerjoin(CarviaOperacaoNf, CarviaOperacaoNf.nf_id == CarviaNf.id)
            .outerjoin(CarviaOperacao, CarviaOperacao.id == CarviaOperacaoNf.operacao_id)
            .outerjoin(CarviaFaturaCliente, CarviaFaturaCliente.id == CarviaOperacao.fatura_cliente_id)
            .outerjoin(motos_subq, motos_subq.c.nf_id == CarviaNf.id)
            .outerjoin(nfs_por_op_subq, nfs_por_op_subq.c.operacao_id == CarviaOperacao.id)
            .filter(CarviaNf.status == 'ATIVA')
            .order_by(CarviaNf.data_emissao.desc().nullslast(), CarviaNf.numero_nf)
            .all()
        )

        # --- 2. Rateio cascateado ---
        by_op = defaultdict(list)
        sem_op = []
        for r in rows:
            row_dict = {
                'nf_id': r.nf_id,
                'numero_nf': r.numero_nf,
                'serie_nf': r.serie_nf,
                'data_nf': r.data_nf,
                'cnpj_emitente': r.cnpj_emitente,
                'nome_emitente': r.nome_emitente,
                'cnpj_destinatario': r.cnpj_destinatario,
                'nome_destinatario': r.nome_destinatario,
                'uf_destinatario': r.uf_destinatario,
                'cidade_destinatario': r.cidade_destinatario,
                'valor_nf': float(r.valor_nf) if r.valor_nf else None,
                'peso_bruto': float(r.peso_bruto) if r.peso_bruto else None,
                'quantidade_volumes': r.quantidade_volumes,
                'operacao_id': r.operacao_id,
                'cte_numero': r.cte_numero,
                'cte_valor': float(r.cte_valor) if r.cte_valor else None,
                'data_cte': r.data_cte,
                'nome_cliente': r.nome_cliente,
                'status_operacao': r.status_operacao,
                'numero_fatura': r.numero_fatura,
                'data_fatura': r.data_fatura,
                'qtd_motos': r.qtd_motos or 0,
                'total_nfs_no_cte': r.total_nfs_no_cte or 1,
            }
            if r.operacao_id is not None:
                by_op[r.operacao_id].append(row_dict)
            else:
                row_dict['cte_valor_rateado'] = None
                row_dict['criterio_rateio'] = None
                sem_op.append(row_dict)

        for op_id, nfs in by_op.items():
            cte_valor = Decimal(str(nfs[0]['cte_valor'])) if nfs[0]['cte_valor'] else Decimal('0')

            if len(nfs) == 1:
                nfs[0]['cte_valor_rateado'] = float(cte_valor)
                nfs[0]['criterio_rateio'] = 'Direto (1:1)'
                continue

            # Determinar criterio para o GRUPO
            total_motos = sum(n['qtd_motos'] for n in nfs)
            pesos = [Decimal(str(n['peso_bruto'])) if n['peso_bruto'] else Decimal('0') for n in nfs]
            total_peso = sum(pesos)

            if total_motos > 0:
                criterio = 'Motos'
                for n in nfs:
                    proporcao = Decimal(str(n['qtd_motos'])) / Decimal(str(total_motos))
                    n['cte_valor_rateado'] = float(
                        (cte_valor * proporcao).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    )
                    n['criterio_rateio'] = criterio
            elif total_peso > 0:
                criterio = 'Peso'
                for i, n in enumerate(nfs):
                    proporcao = pesos[i] / total_peso
                    n['cte_valor_rateado'] = float(
                        (cte_valor * proporcao).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    )
                    n['criterio_rateio'] = criterio
            else:
                criterio = 'Qtd NFs'
                valor_por_nf = cte_valor / len(nfs)
                for n in nfs:
                    n['cte_valor_rateado'] = float(
                        valor_por_nf.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    )
                    n['criterio_rateio'] = criterio

            # Ajuste de centavos na primeira NF para soma exata
            soma = sum(Decimal(str(n['cte_valor_rateado'])) for n in nfs)
            diff = cte_valor - soma
            if diff != 0:
                nfs[0]['cte_valor_rateado'] = float(Decimal(str(nfs[0]['cte_valor_rateado'])) + diff)

        # --- 3. Montar DataFrame ---
        all_rows = []
        for nfs in by_op.values():
            all_rows.extend(nfs)
        all_rows.extend(sem_op)
        all_rows.sort(key=lambda r: (r.get('data_nf') or date.min, r.get('numero_nf') or ''))

        def _fmt(val):
            return val.strftime('%d/%m/%Y') if val else ''

        data = []
        for r in all_rows:
            data.append({
                'Numero NF': r['numero_nf'],
                'Serie': r['serie_nf'],
                'Data NF': _fmt(r['data_nf']),
                'Emitente': r['nome_emitente'],
                'CNPJ Emitente': r['cnpj_emitente'],
                'Destinatario': r['nome_destinatario'],
                'UF Destino': r['uf_destinatario'],
                'Cidade Destino': r['cidade_destinatario'],
                'Valor NF': r['valor_nf'],
                'Peso Bruto (kg)': r['peso_bruto'],
                'Qtd Motos': r['qtd_motos'] if r['qtd_motos'] else None,
                'Qtd Volumes': r['quantidade_volumes'],
                'N CTe': r['cte_numero'],
                'Data CTe': _fmt(r['data_cte']),
                'Valor CTe Total': r['cte_valor'],
                'Valor CTe Rateado': r.get('cte_valor_rateado'),
                'Criterio Rateio': r.get('criterio_rateio'),
                'NFs no CTe': r['total_nfs_no_cte'] if r.get('operacao_id') else None,
                'N Fatura': r['numero_fatura'],
                'Data Fatura': _fmt(r['data_fatura']),
                'Status Operacao': r['status_operacao'],
            })

        df = pd.DataFrame(data)

        # --- 4. Gerar Excel ---
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='NFs x CTe CarVia')
            ws = writer.sheets['NFs x CTe CarVia']

            # Ajustar larguras
            for idx, col in enumerate(df.columns):
                max_len = max(
                    df[col].fillna('').astype(str).map(len).max(),
                    len(str(col))
                )
                col_letter = chr(65 + idx) if idx < 26 else chr(64 + idx // 26) + chr(65 + idx % 26)
                ws.column_dimensions[col_letter].width = min(max_len + 2, 50)

            ws.freeze_panes = 'A2'
            ws.auto_filter.ref = ws.dimensions

            # Aba de resumo de rateio
            resumo = []
            for op_id, nfs in sorted(by_op.items(), key=lambda x: x[1][0].get('cte_numero') or ''):
                cte_valor = nfs[0]['cte_valor'] or 0
                soma = sum(n['cte_valor_rateado'] for n in nfs)
                diff = round(cte_valor - soma, 2)
                resumo.append({
                    'CTe': nfs[0].get('cte_numero'),
                    'Valor Total': cte_valor,
                    'Qtd NFs': len(nfs),
                    'Criterio': nfs[0].get('criterio_rateio'),
                    'Soma Rateada': round(soma, 2),
                    'Diferenca': diff,
                    'Status': 'OK' if abs(diff) < 0.01 else 'ERRO',
                })

            if resumo:
                df_resumo = pd.DataFrame(resumo)
                df_resumo.to_excel(writer, index=False, sheet_name='Resumo Rateio')
                ws2 = writer.sheets['Resumo Rateio']
                for idx, col in enumerate(df_resumo.columns):
                    max_len = max(
                        df_resumo[col].fillna('').astype(str).map(len).max(),
                        len(str(col))
                    )
                    col_letter = chr(65 + idx)
                    ws2.column_dimensions[col_letter].width = min(max_len + 2, 20)

            # --- Sheet 3: Itens NF × CTe com rateio ---
            from app.carvia.services.financeiro.gerencial_service import GerencialService as _GS

            # Usar a menor e maior data dos dados exportados (sem filtro de data)
            datas_cte = [r['data_cte'] for r in all_rows if r.get('data_cte')]
            if datas_cte:
                _svc = _GS()
                _itens = _svc.obter_itens_nf_com_rateio(
                    min(datas_cte), max(datas_cte),
                )
                if _itens:
                    itens_data = []
                    for it in _itens:
                        itens_data.append({
                            'Numero NF': it['numero_nf'],
                            'Serie': it.get('serie_nf'),
                            'Data NF': _fmt(it.get('data_nf')),
                            'Emitente': it.get('nome_emitente'),
                            'Destinatario': it.get('nome_destinatario'),
                            'UF Destino': it.get('uf_destinatario'),
                            'Codigo Produto': it.get('codigo_produto'),
                            'Descricao': it.get('descricao_item'),
                            'Modelo Moto': it.get('modelo_moto_nome'),
                            'Peso Cubado Modelo': it.get('peso_cubado_modelo'),
                            'Quantidade': it.get('quantidade'),
                            'Valor Unitario': it.get('valor_unitario'),
                            'Valor Total Item': it.get('valor_total_item'),
                            'Peso Bruto NF (kg)': it.get('peso_bruto'),
                            'Qtd Motos NF': it.get('qtd_motos_nf') or 0,
                            'N CTe': it.get('cte_numero'),
                            'Valor CTe Total': it.get('cte_valor'),
                            'R$/Unid|Kg': it.get('valor_por_unidade_kg'),
                            'Tipo (Unid|Kg)': it.get('unidade_label'),
                            'Valor CTe Rateado (NF)': it.get('rateio_nf'),
                            'Valor CTe Rateado (Item)': it.get('rateio_item'),
                            'Criterio Rateio': it.get('criterio_rateio'),
                            'Status Operacao': it.get('status_operacao'),
                        })
                    df_itens = pd.DataFrame(itens_data)
                    df_itens.to_excel(writer, index=False, sheet_name='Itens NF x CTe')
                    ws3 = writer.sheets['Itens NF x CTe']
                    for idx, col in enumerate(df_itens.columns):
                        max_len = max(
                            df_itens[col].fillna('').astype(str).map(len).max(),
                            len(str(col))
                        )
                        col_letter = (
                            chr(65 + idx) if idx < 26
                            else chr(64 + idx // 26) + chr(65 + idx % 26)
                        )
                        ws3.column_dimensions[col_letter].width = min(max_len + 2, 50)
                    ws3.freeze_panes = 'A2'
                    ws3.auto_filter.ref = ws3.dimensions

        output.seek(0)
        timestamp = agora_utc_naive().strftime('%Y%m%d_%H%M')
        filename = f'carvia_relatorio_gerencial_{timestamp}.xlsx'

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename,
        )
