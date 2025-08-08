"""
API de Relatórios da Carteira
Exportação de dados para Excel com filtros de data
"""

from flask import jsonify, request, send_file
from datetime import datetime, date
from decimal import Decimal
import pandas as pd
import io
from sqlalchemy import and_, or_, func
from app import db
from app.carteira.main_routes import carteira_bp
from app.carteira.models import CarteiraPrincipal, PreSeparacaoItem
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.faturamento.models import FaturamentoProduto
import logging

logger = logging.getLogger(__name__)

@carteira_bp.route('/api/relatorios/pre_separacoes', methods=['POST'])
def exportar_pre_separacoes():
    """Exportar pré-separações com status CRIADO e RECOMPOSTO"""
    try:
        data = request.json or {}
        data_inicio = data.get('data_inicio') if data else None
        data_fim = data.get('data_fim') if data else None
        
        # Query base
        query = PreSeparacaoItem.query.filter(
            PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
        )
        
        # Aplicar filtro de datas se fornecido
        if data_inicio and data_fim:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            query = query.filter(
                PreSeparacaoItem.data_expedicao_editada.between(data_inicio, data_fim)
            )
        
        # Buscar dados
        items = query.all()
        
        # Converter para DataFrame
        dados = []
        for item in items:
            dados.append({
                'Lote Pré-Separação': item.separacao_lote_id,
                'Nº Pedido': item.num_pedido,
                'Cód. Produto': item.cod_produto,
                'Nome Produto': item.nome_produto,
                'CNPJ Cliente': item.cnpj_cliente,
                'Qtd Original': float(item.qtd_original_carteira) if item.qtd_original_carteira else 0,
                'Qtd Selecionada': float(item.qtd_selecionada_usuario) if item.qtd_selecionada_usuario else 0,
                'Qtd Restante': float(item.qtd_restante_calculada) if item.qtd_restante_calculada else 0,
                'Valor': float(item.valor_original_item) if item.valor_original_item else 0,
                'Peso': float(item.peso_original_item) if item.peso_original_item else 0,
                'Data Expedição': item.data_expedicao_editada.strftime('%d/%m/%Y') if item.data_expedicao_editada else '',
                'Data Agendamento': item.data_agendamento_editada.strftime('%d/%m/%Y') if item.data_agendamento_editada else '',
                'Protocolo': item.protocolo_editado or '',
                'Status': item.status,
                'Recomposto': 'Sim' if item.recomposto else 'Não',
                'Tipo Envio': item.tipo_envio,
                'Observações': item.observacoes_usuario or '',
                'Criado Em': item.data_criacao.strftime('%d/%m/%Y %H:%M') if item.data_criacao else '',
                'Criado Por': item.criado_por or ''
            })
        
        df = pd.DataFrame(dados)
        
        # Gerar Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Pré-Separações', index=False)
            
            # Ajustar largura das colunas
            worksheet = writer.sheets['Pré-Separações']
            for i, col in enumerate(df.columns):
                column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(column_width, 50))
        
        output.seek(0)
        
        filename = f'pre_separacoes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Erro ao exportar pré-separações: {str(e)}")
        return jsonify({'error': str(e)}), 500


@carteira_bp.route('/api/relatorios/separacoes', methods=['POST'])
def exportar_separacoes():
    """Exportar separações com status do pedido"""
    try:
        data = request.json or {}
        data_inicio = data.get('data_inicio') if data else None
        data_fim = data.get('data_fim') if data else None
        
        # Query com join para pegar status do pedido
        query = db.session.query(
            Separacao,
            Pedido.status.label('status_pedido'),
            Pedido.nf
        ).outerjoin(
            Pedido,
            Separacao.separacao_lote_id == Pedido.separacao_lote_id
        )
        
        # Aplicar filtro de datas se fornecido
        if data_inicio and data_fim:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            query = query.filter(
                Separacao.expedicao.between(data_inicio, data_fim)
            )
        
        # Buscar dados
        resultados = query.all()
        
        # Converter para DataFrame
        dados = []
        for sep, status_pedido, nf in resultados:
            dados.append({
                'Lote Separação': sep.separacao_lote_id,
                'Nº Pedido': sep.num_pedido,
                'Cód. Produto': sep.cod_produto,
                'Nome Produto': sep.nome_produto,
                'CNPJ/CPF': sep.cnpj_cpf,
                'Razão Social': sep.raz_social_red,
                'Cidade': sep.nome_cidade,
                'UF': sep.cod_uf,
                'Qtd': float(sep.qtd_saldo) if sep.qtd_saldo else 0,
                'Valor': float(sep.valor_saldo) if sep.valor_saldo else 0,
                'Peso': float(sep.peso) if sep.peso else 0,
                'Pallet': float(sep.pallet) if sep.pallet else 0,
                'Data Pedido': sep.data_pedido.strftime('%d/%m/%Y') if sep.data_pedido else '',
                'Data Expedição': sep.expedicao.strftime('%d/%m/%Y') if sep.expedicao else '',
                'Data Agendamento': sep.agendamento.strftime('%d/%m/%Y') if sep.agendamento else '',
                'Protocolo': sep.protocolo or '',
                'Status Pedido': status_pedido or 'SEM PEDIDO',
                'Nota Fiscal': nf or '',
                'Tipo Envio': sep.tipo_envio,
                'Transportadora': sep.roteirizacao or '',
                'Rota': sep.rota or '',
                'Sub-Rota': sep.sub_rota or '',
                'Observações': sep.observ_ped_1 or '',
                'Criado Em': sep.criado_em.strftime('%d/%m/%Y %H:%M') if sep.criado_em else ''
            })
        
        df = pd.DataFrame(dados)
        
        # Gerar Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Separações', index=False)
            
            # Ajustar largura das colunas
            worksheet = writer.sheets['Separações']
            for i, col in enumerate(df.columns):
                column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(column_width, 50))
        
        output.seek(0)
        
        filename = f'separacoes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Erro ao exportar separações: {str(e)}")
        return jsonify({'error': str(e)}), 500


@carteira_bp.route('/api/relatorios/carteira_simples', methods=['POST'])
def exportar_carteira_simples():
    """Exportar carteira de pedidos simples"""
    try:
        data = request.json or {}
        data_inicio = data.get('data_inicio') if data else None
        data_fim = data.get('data_fim') if data else None
        
        # Query base
        query = CarteiraPrincipal.query
        
        # Aplicar filtro de datas se fornecido
        if data_inicio and data_fim:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            query = query.filter(
                CarteiraPrincipal.expedicao.between(data_inicio, data_fim)
            )
        
        # Buscar dados
        items = query.all()
        
        # Converter para DataFrame
        dados = []
        for item in items:
            dados.append({
                'Nº Pedido': item.num_pedido,
                'Cód. Produto': item.cod_produto,
                'Nome Produto': item.nome_produto,
                'CNPJ/CPF': item.cnpj_cpf,
                'Razão Social': item.raz_social,
                'Razão Social Red.': item.raz_social_red,
                'Município': item.municipio,
                'UF': item.estado,
                'Vendedor': item.vendedor,
                'Equipe': item.equipe_vendas,
                'Qtd Pedido': float(item.qtd_produto_pedido) if item.qtd_produto_pedido else 0,
                'Qtd Saldo': float(item.qtd_saldo_produto_pedido) if item.qtd_saldo_produto_pedido else 0,
                'Qtd Cancelada': float(item.qtd_cancelada_produto_pedido) if item.qtd_cancelada_produto_pedido else 0,
                'Preço': float(item.preco_produto_pedido) if item.preco_produto_pedido else 0,
                'Data Expedição': item.expedicao.strftime('%d/%m/%Y') if item.expedicao else '',
                'Data Agendamento': item.agendamento.strftime('%d/%m/%Y') if item.agendamento else '',
                'Hora Agendamento': item.hora_agendamento.strftime('%H:%M') if item.hora_agendamento else '',
                'Protocolo': item.protocolo or '',
                'Agendamento Confirmado': 'Sim' if item.agendamento_confirmado else 'Não',
                'Data Entrega': item.data_entrega.strftime('%d/%m/%Y') if item.data_entrega else '',
                'Observações': item.observ_ped_1 or '',
                'Pedido Cliente': item.pedido_cliente or '',
                'Estoque Atual': float(item.estoque) if item.estoque else 0,
                'Estoque na Expedição': float(item.saldo_estoque_pedido) if item.saldo_estoque_pedido else 0
            })
        
        df = pd.DataFrame(dados)
        
        # Gerar Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Carteira de Pedidos', index=False)
            
            # Ajustar largura das colunas
            worksheet = writer.sheets['Carteira de Pedidos']
            for i, col in enumerate(df.columns):
                column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(column_width, 50))
        
        output.seek(0)
        
        filename = f'carteira_pedidos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Erro ao exportar carteira simples: {str(e)}")
        return jsonify({'error': str(e)}), 500


@carteira_bp.route('/api/relatorios/carteira_detalhada', methods=['POST'])
def exportar_carteira_detalhada():
    """Exportar carteira detalhada com pedidos, pré-separações e separações"""
    try:
        data = request.json or {}
        data_inicio = data.get('data_inicio') if data else None
        data_fim = data.get('data_fim') if data else None
        
        # Query base para pedidos
        query_pedidos = CarteiraPrincipal.query
        
        # Aplicar filtro de datas se fornecido
        if data_inicio and data_fim:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            query_pedidos = query_pedidos.filter(
                CarteiraPrincipal.expedicao.between(data_inicio, data_fim)
            )
        
        # Buscar pedidos
        pedidos = query_pedidos.order_by(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.cod_produto
        ).all()
        
        # Preparar DataFrame
        dados = []
        
        for pedido in pedidos:
            # Calcular quantidades líquidas (abatendo pré-separações e separações)
            qtd_pre_sep = db.session.query(
                func.sum(PreSeparacaoItem.qtd_selecionada_usuario)
            ).filter(
                PreSeparacaoItem.num_pedido == pedido.num_pedido,
                PreSeparacaoItem.cod_produto == pedido.cod_produto,
                PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
            ).scalar() or 0
            
            qtd_sep = db.session.query(
                func.sum(Separacao.qtd_saldo)
            ).filter(
                Separacao.num_pedido == pedido.num_pedido,
                Separacao.cod_produto == pedido.cod_produto
            ).scalar() or 0
            
            qtd_liquida = float(pedido.qtd_saldo_produto_pedido or 0) - float(qtd_pre_sep) - float(qtd_sep)
            
            # Calcular valores para o pedido
            preco_unit = float(pedido.preco_produto_pedido or 0)
            qtd_original = float(pedido.qtd_produto_pedido or 0)
            qtd_saldo_atual = float(pedido.qtd_saldo_produto_pedido or 0)
            
            # Valores originais
            valor_original = qtd_original * preco_unit
            # Assumindo peso e pallet proporcionais (você pode ajustar se tiver campos específicos)
            peso_unit = float(pedido.peso or 0) / qtd_original if qtd_original > 0 and pedido.peso else 0
            pallet_unit = float(pedido.pallet or 0) / qtd_original if qtd_original > 0 and pedido.pallet else 0
            peso_original = qtd_original * peso_unit
            pallet_original = qtd_original * pallet_unit
            
            # Valores de saldo (após descontar pré-sep e sep)
            qtd_saldo_liquido = qtd_saldo_atual - float(qtd_pre_sep) - float(qtd_sep)
            valor_saldo = qtd_saldo_liquido * preco_unit
            peso_saldo = qtd_saldo_liquido * peso_unit
            pallet_saldo = qtd_saldo_liquido * pallet_unit
            
            # Linha do pedido
            linha_pedido = {
                'Tipo': 'PEDIDO',
                'Lote': '',
                'Nº Pedido': pedido.num_pedido,
                'Cód. Produto': pedido.cod_produto,
                'Nome Produto': pedido.nome_produto,
                'CNPJ/CPF': pedido.cnpj_cpf,
                'Razão Social': pedido.raz_social,
                'Município': pedido.municipio,
                'UF': pedido.estado,
                'Vendedor': pedido.vendedor,
                'Equipe': pedido.equipe_vendas,
                'Qtd Original': qtd_original,
                'Valor Original': valor_original,
                'Pallet Original': pallet_original,
                'Peso Original': peso_original,
                'Qtd Saldo': qtd_saldo_liquido,
                'Valor Saldo': valor_saldo,
                'Pallet Saldo': pallet_saldo,
                'Peso Saldo': peso_saldo,
                'Data Expedição': pedido.expedicao.strftime('%d/%m/%Y') if pedido.expedicao else '',
                'Data Agendamento': pedido.agendamento.strftime('%d/%m/%Y') if pedido.agendamento else '',
                'Protocolo': pedido.protocolo or '',
                'Observações': pedido.observ_ped_1 or '',
                'Pedido Cliente': pedido.pedido_cliente or '',
                'Status': 'ABERTO',
                'Criado Em': '',
                'Criado Por': ''
            }
            dados.append(linha_pedido)
            
            # Buscar pré-separações deste pedido/produto
            pre_seps = PreSeparacaoItem.query.filter(
                PreSeparacaoItem.num_pedido == pedido.num_pedido,
                PreSeparacaoItem.cod_produto == pedido.cod_produto,
                PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
            ).all()
            
            for pre_sep in pre_seps:
                # Calcular pallet e peso proporcional para pré-separação
                qtd_pre_sep = float(pre_sep.qtd_selecionada_usuario or 0)
                valor_pre_sep = float(pre_sep.valor_original_item or 0)
                peso_pre_sep = float(pre_sep.peso_original_item or 0) if hasattr(pre_sep, 'peso_original_item') else qtd_pre_sep * peso_unit
                pallet_pre_sep = qtd_pre_sep * pallet_unit  # Calcular proporcional
                
                linha_pre_sep = {
                    'Tipo': 'PRÉ-SEPARAÇÃO',
                    'Lote': pre_sep.separacao_lote_id or '',
                    'Nº Pedido': pre_sep.num_pedido,
                    'Cód. Produto': pre_sep.cod_produto,
                    'Nome Produto': pre_sep.nome_produto,
                    'CNPJ/CPF': pedido.cnpj_cpf,
                    'Razão Social': pedido.raz_social,
                    'Município': pedido.municipio,
                    'UF': pedido.estado,
                    'Vendedor': pedido.vendedor,
                    'Equipe': pedido.equipe_vendas,
                    'Qtd Original': '',
                    'Valor Original': '',
                    'Pallet Original': '',
                    'Peso Original': '',
                    'Qtd Saldo': qtd_pre_sep,
                    'Valor Saldo': valor_pre_sep,
                    'Pallet Saldo': pallet_pre_sep,
                    'Peso Saldo': peso_pre_sep,
                    'Data Expedição': pre_sep.data_expedicao_editada.strftime('%d/%m/%Y') if pre_sep.data_expedicao_editada else '',
                    'Data Agendamento': pre_sep.data_agendamento_editada.strftime('%d/%m/%Y') if pre_sep.data_agendamento_editada else '',
                    'Protocolo': pre_sep.protocolo_editado or '',
                    'Observações': pre_sep.observacoes_usuario or '',
                    'Pedido Cliente': '',
                    'Status': pre_sep.status,
                    'Criado Em': pre_sep.data_criacao.strftime('%d/%m/%Y %H:%M') if pre_sep.data_criacao else '',
                    'Criado Por': pre_sep.criado_por or ''
                }
                dados.append(linha_pre_sep)
            
            # Buscar separações deste pedido/produto
            seps = Separacao.query.filter(
                Separacao.num_pedido == pedido.num_pedido,
                Separacao.cod_produto == pedido.cod_produto
            ).all()
            
            for sep in seps:
                # Buscar status do pedido da separação
                pedido_sep = Pedido.query.filter_by(
                    separacao_lote_id=sep.separacao_lote_id
                ).first()
                
                # Valores da separação
                qtd_sep = float(sep.qtd_saldo or 0)
                valor_sep = float(sep.valor_saldo or 0)
                peso_sep = float(sep.peso or 0)
                pallet_sep = float(sep.pallet or 0)
                
                linha_sep = {
                    'Tipo': 'SEPARAÇÃO',
                    'Lote': sep.separacao_lote_id or '',
                    'Nº Pedido': sep.num_pedido,
                    'Cód. Produto': sep.cod_produto,
                    'Nome Produto': sep.nome_produto,
                    'CNPJ/CPF': sep.cnpj_cpf,
                    'Razão Social': sep.raz_social_red,
                    'Município': sep.nome_cidade,
                    'UF': sep.cod_uf,
                    'Vendedor': pedido.vendedor,
                    'Equipe': pedido.equipe_vendas,
                    'Qtd Original': '',
                    'Valor Original': '',
                    'Pallet Original': '',
                    'Peso Original': '',
                    'Qtd Saldo': qtd_sep,
                    'Valor Saldo': valor_sep,
                    'Pallet Saldo': pallet_sep,
                    'Peso Saldo': peso_sep,
                    'Data Expedição': sep.expedicao.strftime('%d/%m/%Y') if sep.expedicao else '',
                    'Data Agendamento': sep.agendamento.strftime('%d/%m/%Y') if sep.agendamento else '',
                    'Protocolo': sep.protocolo or '',
                    'Observações': sep.observ_ped_1 or '',
                    'Pedido Cliente': '',
                    'Status': pedido_sep.status if pedido_sep else 'SEM PEDIDO',
                    'Criado Em': sep.criado_em.strftime('%d/%m/%Y %H:%M') if sep.criado_em else '',
                    'Criado Por': ''
                }
                dados.append(linha_sep)
        
        df = pd.DataFrame(dados)
        
        # Gerar Excel com formatação
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Carteira Detalhada', index=False)
            
            # Formatação
            workbook = writer.book
            worksheet = writer.sheets['Carteira Detalhada']
            
            # Formatos
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D7E4BD',
                'border': 1
            })
            
            pedido_format = workbook.add_format({
                'bg_color': '#FFFFFF',
                'border': 1
            })
            
            pre_sep_format = workbook.add_format({
                'bg_color': '#FFF2CC',
                'border': 1
            })
            
            sep_format = workbook.add_format({
                'bg_color': '#E1F5FE',
                'border': 1
            })
            
            # Aplicar formatos por tipo de linha
            for row_num in range(1, len(df) + 1):
                tipo = df.iloc[row_num - 1]['Tipo']
                if tipo == 'PEDIDO':
                    worksheet.set_row(row_num, None, pedido_format)
                elif tipo == 'PRÉ-SEPARAÇÃO':
                    worksheet.set_row(row_num, None, pre_sep_format)
                elif tipo == 'SEPARAÇÃO':
                    worksheet.set_row(row_num, None, sep_format)
            
            # Ajustar largura das colunas
            for i, col in enumerate(df.columns):
                column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(column_width, 50))
        
        output.seek(0)
        
        filename = f'carteira_detalhada_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Erro ao exportar carteira detalhada: {str(e)}")
        return jsonify({'error': str(e)}), 500