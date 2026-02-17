"""
API de Relatórios da Carteira
Exportação de dados para Excel com filtros de data
"""

from flask import jsonify, request, send_file
from datetime import datetime
import pandas as pd
import io
from sqlalchemy import func
from app import db
from app.carteira.main_routes import carteira_bp
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.producao.models import CadastroPalletizacao
import logging
from app.utils.timezone import agora_utc_naive
logger = logging.getLogger(__name__)

# Função exportar_pre_separacoes REMOVIDA - Obsoleta após migração para Separacao

@carteira_bp.route('/api/relatorios/separacoes', methods=['POST'])
def exportar_separacoes():
    """Exportar separações não sincronizadas"""
    try:
        data = request.json or {}
        data_inicio = data.get('data_inicio') if data else None
        data_fim = data.get('data_fim') if data else None
        
        # MIGRADO: Removido JOIN com Pedido VIEW, usa sincronizado_nf=False
        query = Separacao.query
        
        incluir_faturado = data.get('incluir_faturado', False) if data else False
        if not incluir_faturado:
            query = query.filter(
                Separacao.sincronizado_nf == False
            )
        
        # Aplicar filtro de datas se fornecido
        if data_inicio and data_fim:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            query = query.filter(
                Separacao.expedicao.between(data_inicio, data_fim)
            )
        
        # Buscar dados
        separacoes = query.all()
        
        # Converter para DataFrame
        dados = []
        for sep in separacoes:
            dados.append({
                'Lote Separação': sep.separacao_lote_id,
                'Status': sep.status or '',  # Status da própria Separacao
                'Status Calculado': sep.status_calculado or '',  # Status calculado dinamicamente
                'Nº Pedido': sep.num_pedido,
                'CNPJ/CPF': sep.cnpj_cpf,
                'Razão Social': sep.raz_social_red,
                'Cidade': sep.nome_cidade,
                'UF': sep.cod_uf,
                'Cód. Produto': sep.cod_produto,
                'Nome Produto': sep.nome_produto,
                'Qtd': float(sep.qtd_saldo) if sep.qtd_saldo else 0,
                'Valor': float(sep.valor_saldo) if sep.valor_saldo else 0,
                'Peso': float(sep.peso) if sep.peso else 0,
                'Pallet': float(sep.pallet) if sep.pallet else 0,
                'Data Pedido': sep.data_pedido if sep.data_pedido else None,
                'Data Expedição': sep.expedicao if sep.expedicao else None,
                'Data Agendamento': sep.agendamento if sep.agendamento else None,
                'Protocolo': sep.protocolo or '',
                'Agendamento Confirmado': sep.agendamento_confirmado or '',
                'Observações da Sep': sep.obs_separacao or '',
                'Nota Fiscal': sep.numero_nf or '',  # Campo correto: numero_nf
                'Sincronizado com NF': sep.sincronizado_nf or '',
                'Tipo Envio': sep.tipo_envio,
                'Transportadora': sep.roteirizacao or '',
                'Rota': sep.rota or '',
                'Sub-Rota': sep.sub_rota or '',
                'Observações do Pdd': sep.observ_ped_1 or '',
                'Criado Em': sep.criado_em if sep.criado_em else None
            })
        
        df = pd.DataFrame(dados)
        
        # Gerar Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Separações', index=False)

            workbook = writer.book
            worksheet = writer.sheets['Separações']

            # Formatos de data brasileiros
            formato_data = workbook.add_format({'num_format': 'dd/mm/yyyy'})
            formato_datetime = workbook.add_format({'num_format': 'dd/mm/yyyy hh:mm'})

            # Colunas de data
            colunas_data = {
                'Data Pedido': formato_data,
                'Data Expedição': formato_data,
                'Data Agendamento': formato_data,
                'Criado Em': formato_datetime
            }

            # Aplicar formato e ajustar largura
            for i, col in enumerate(df.columns):
                # Aplicar formato de data se for coluna de data
                if col in colunas_data:
                    worksheet.set_column(i, i, 12, colunas_data[col])
                else:
                    column_width = max(df[col].fillna('').astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(i, i, min(column_width, 50))
        
        output.seek(0)
        
        filename = f'separacoes_{agora_utc_naive().strftime("%Y%m%d_%H%M%S")}.xlsx'
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
        # NOTA: Campo expedicao foi REMOVIDO de CarteiraPrincipal - usar data_pedido
        if data_inicio and data_fim:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            query = query.filter(
                CarteiraPrincipal.data_pedido.between(data_inicio, data_fim)
            )
        
        # Buscar dados
        items = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        )
        
        # Converter para DataFrame
        # NOTA: CarteiraPrincipal contém apenas dados do pedido original do Odoo
        # Campos de agendamento/expedição estão em Separacao (fonte única da verdade)
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
                'Data Pedido': item.data_pedido if item.data_pedido else None,
                'Data Entrega Prevista': item.data_entrega_pedido if item.data_entrega_pedido else None,
                'Observações': item.observ_ped_1 or '',
                'Pedido Cliente': item.pedido_cliente or '',
                'Cond. Pagamento': item.cond_pgto_pedido or '',
                'Forma Pagamento': item.forma_pgto_pedido or '',
                'Incoterm': item.incoterm or ''
            })
        
        df = pd.DataFrame(dados)
        
        # Gerar Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Carteira de Pedidos', index=False)

            workbook = writer.book
            worksheet = writer.sheets['Carteira de Pedidos']

            # Formatos de data brasileiros
            formato_data = workbook.add_format({'num_format': 'dd/mm/yyyy'})

            # Colunas de data
            colunas_data = {
                'Data Pedido': formato_data,
                'Data Entrega Prevista': formato_data
            }

            # Aplicar formato e ajustar largura
            for i, col in enumerate(df.columns):
                # Aplicar formato de data se for coluna de data
                if col in colunas_data:
                    worksheet.set_column(i, i, 12, colunas_data[col])
                else:
                    column_width = max(df[col].fillna('').astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(i, i, min(column_width, 50))
        
        output.seek(0)
        
        filename = f'carteira_pedidos_{agora_utc_naive().strftime("%Y%m%d_%H%M%S")}.xlsx'
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
        query_pedidos = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        )
        
        # Aplicar filtro de datas se fornecido
        # NOTA: Campo expedicao foi REMOVIDO de CarteiraPrincipal - usar data_pedido
        if data_inicio and data_fim:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            query_pedidos = query_pedidos.filter(
                CarteiraPrincipal.data_pedido.between(data_inicio, data_fim)
            )
        
        # Buscar pedidos
        pedidos = query_pedidos.order_by(
            CarteiraPrincipal.num_pedido,
            CarteiraPrincipal.cod_produto
        ).all()
        
        # OTIMIZAÇÃO: Buscar TODAS as somas de separações em UMA query
        # Agrupando por num_pedido + cod_produto
        somas_separacoes = db.session.query(
            Separacao.num_pedido,
            Separacao.cod_produto,
            func.sum(Separacao.qtd_saldo).label('qtd_total')
        ).filter(
            Separacao.sincronizado_nf == False  
        ).group_by(
            Separacao.num_pedido,
            Separacao.cod_produto
        ).all()
        
        # Criar índice para acesso rápido O(1)
        soma_por_pedido_produto = {}
        for soma in somas_separacoes:
            chave = (soma.num_pedido, soma.cod_produto)
            soma_por_pedido_produto[chave] = float(soma.qtd_total or 0)
        
        # OTIMIZAÇÃO: Buscar fatores de conversão (palletizacao e peso_bruto) uma vez
        # Pegar todos os produtos únicos dos pedidos
        produtos_unicos = list(set(p.cod_produto for p in pedidos))
        fatores_conversao = db.session.query(
            CadastroPalletizacao.cod_produto,
            CadastroPalletizacao.palletizacao,
            CadastroPalletizacao.peso_bruto
        ).filter(
            CadastroPalletizacao.cod_produto.in_(produtos_unicos),
            CadastroPalletizacao.ativo == True
        ).all()
        
        # Criar índice de fatores de conversão
        fatores_por_produto = {}
        for fator in fatores_conversao:
            fatores_por_produto[fator.cod_produto] = {
                'palletizacao': float(fator.palletizacao or 1),  # Evita divisão por zero
                'peso_bruto': float(fator.peso_bruto or 0)
            }
        
        # OTIMIZAÇÃO: Buscar TODAS as separações detalhadas em UMA query
        todas_separacoes = db.session.query(
            Separacao,
            CarteiraPrincipal.pedido_cliente,
            CarteiraPrincipal.cond_pgto_pedido,
            CarteiraPrincipal.forma_pgto_pedido,
            CarteiraPrincipal.incoterm
        ).outerjoin(
            CarteiraPrincipal,
            db.and_(
                CarteiraPrincipal.num_pedido == Separacao.num_pedido,
                CarteiraPrincipal.cod_produto == Separacao.cod_produto,
                CarteiraPrincipal.ativo == True
            )
        ).filter(
            Separacao.sincronizado_nf == False  # Não sincronizadas
        ).all()
        
        # Criar índice para acesso rápido por pedido+produto
        separacoes_por_pedido_produto = {}
        for sep_data in todas_separacoes:
            sep = sep_data[0]
            chave = (sep.num_pedido, sep.cod_produto)
            if chave not in separacoes_por_pedido_produto:
                separacoes_por_pedido_produto[chave] = []
            separacoes_por_pedido_produto[chave].append(sep_data)
        
        # Preparar DataFrame
        dados = []
        
        for pedido in pedidos:
            # Buscar soma do índice em O(1) em vez de fazer query
            chave = (pedido.num_pedido, pedido.cod_produto)
            qtd_sep = soma_por_pedido_produto.get(chave, 0)
                        
            # Calcular valores para o pedido
            preco_unit = float(pedido.preco_produto_pedido or 0)
            qtd_original = float(pedido.qtd_produto_pedido or 0)
            qtd_saldo_atual = float(pedido.qtd_saldo_produto_pedido or 0)
            
            # CORREÇÃO: Usar fatores de conversão do CadastroPalletizacao
            # Conforme CLAUDE.md linhas 446-479
            fatores = fatores_por_produto.get(pedido.cod_produto, {
                'palletizacao': 1,  # Default se não encontrar
                'peso_bruto': 0
            })
            
            # Valores de saldo (após descontar separações)
            qtd_saldo_liquido = qtd_saldo_atual - float(qtd_sep)
            valor_saldo = qtd_saldo_liquido * preco_unit
            
            # CÁLCULOS CORRETOS conforme CLAUDE.md:
            # Peso = quantidade * peso_bruto (multiplicação)
            peso_saldo = qtd_saldo_liquido * fatores['peso_bruto']
            
            # Pallet = quantidade / palletizacao (divisão)
            if fatores['palletizacao'] > 0:
                pallet_saldo = qtd_saldo_liquido / fatores['palletizacao']
            else:
                pallet_saldo = 0
            
            # Linha do pedido
            # NOTA: CarteiraPrincipal não tem campos de agendamento/expedição/protocolo
            # Esses dados estão em Separacao (fonte única da verdade)
            linha_pedido = {
                'Tipo': 'PEDIDO',
                'Lote': '',
                'Nº Pedido': pedido.num_pedido,
                'Cód. Produto': pedido.cod_produto,
                'Nome Produto': pedido.nome_produto,
                'CNPJ/CPF': pedido.cnpj_cpf,
                'Razão Social': pedido.raz_social_red,
                'Município': pedido.municipio,
                'UF': pedido.estado,
                'Vendedor': pedido.vendedor,
                'Equipe': pedido.equipe_vendas,
                'Qtd': qtd_saldo_liquido,
                'Valor': valor_saldo,
                'Pallet': pallet_saldo,
                'Peso': peso_saldo,
                'Cond. Pagamento': pedido.cond_pgto_pedido or '',
                'Forma Pagamento': pedido.forma_pgto_pedido or '',
                'Incoterm': pedido.incoterm or '',
                'Data Expedição': None,  # Campo não existe em CarteiraPrincipal
                'Entrega Prevista': pedido.data_entrega_pedido if pedido.data_entrega_pedido else None,
                'Data Agendada': '',  # Dados de agendamento estão em Separacao
                'Protocolo': '',  # Dados de protocolo estão em Separacao
                'Observações': pedido.observ_ped_1 or '',
                'Pedido Cliente': pedido.pedido_cliente or '',
                'Status': 'ABERTO',
                'Criado Em': None,
                'Criado Por': ''
            }
            dados.append(linha_pedido)
            
            
            # OTIMIZAÇÃO: Buscar separações do índice em O(1) em vez de fazer query
            # Cada linha é por separacao_lote_id + cod_produto
            seps = separacoes_por_pedido_produto.get(chave, [])
            
            for sep_data in seps:
                sep, pedido_cliente_sep, cond_pgto_sep, forma_pgto_sep, incoterm_sep = sep_data
                
                # Valores da separação
                qtd_sep = float(sep.qtd_saldo or 0)
                valor_sep = float(sep.valor_saldo or 0)
                peso_sep = float(sep.peso or 0)
                pallet_sep = float(sep.pallet or 0)
                
                # Determinar valor da coluna "Data Agendada" para separação
                if sep.agendamento_confirmado:
                    data_agendada_sep = sep.agendamento if sep.agendamento else None
                else:
                    data_agendada_sep = 'Aguardando Aprovação' if sep.agendamento else ''

                tipo_label = 'PRÉ-SEPARAÇÃO' if sep.status == 'PREVISAO' else 'SEPARAÇÃO'
                linha_sep = {
                    'Tipo': tipo_label,
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
                    'Qtd': qtd_sep,  # Removido sufixo "Saldo"
                    'Valor': valor_sep,  # Removido sufixo "Saldo"
                    'Pallet': pallet_sep,  # Removido sufixo "Saldo"
                    'Peso': peso_sep,  # Removido sufixo "Saldo"
                    'Cond. Pagamento': cond_pgto_sep or pedido.cond_pgto_pedido or '',
                    'Forma Pagamento': forma_pgto_sep or pedido.forma_pgto_pedido or '',
                    'Incoterm': incoterm_sep or pedido.incoterm or '',
                    'Data Expedição': sep.expedicao if sep.expedicao else None,
                    'Entrega Prevista': sep.agendamento if sep.agendamento else None,
                    'Data Agendada': data_agendada_sep,
                    'Protocolo': sep.protocolo or '',
                    'Observações': sep.observ_ped_1 or '',
                    'Pedido Cliente': pedido_cliente_sep or pedido.pedido_cliente or '',
                    'Status': sep.status or '',  # Status da própria Separação
                    'Criado Em': sep.criado_em if sep.criado_em else None,
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
            
            # Formatos de linha
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

            # Formatos de data brasileiros
            formato_data = workbook.add_format({'num_format': 'dd/mm/yyyy'})
            formato_datetime = workbook.add_format({'num_format': 'dd/mm/yyyy hh:mm'})
            
            # Aplicar formatos por tipo de linha
            for row_num in range(1, len(df) + 1):
                tipo = df.iloc[row_num - 1]['Tipo']
                if tipo == 'PEDIDO':
                    worksheet.set_row(row_num, None, pedido_format)
                elif tipo == 'PRÉ-SEPARAÇÃO':
                    worksheet.set_row(row_num, None, pre_sep_format)
                elif tipo == 'SEPARAÇÃO':
                    worksheet.set_row(row_num, None, sep_format)
            
            # Aplicar formato de data e ajustar largura das colunas
            colunas_data_simples = ['Data Expedição', 'Entrega Prevista', 'Data Agendada']
            colunas_datetime = ['Criado Em']

            for i, col in enumerate(df.columns):
                # Aplicar formato de data
                if col in colunas_data_simples:
                    worksheet.set_column(i, i, 12, formato_data)
                elif col in colunas_datetime:
                    worksheet.set_column(i, i, 16, formato_datetime)
                else:
                    column_width = max(df[col].fillna('').astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(i, i, min(column_width, 50))
        
        output.seek(0)
        
        filename = f'carteira_detalhada_{agora_utc_naive().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Erro ao exportar carteira detalhada: {str(e)}")
        return jsonify({'error': str(e)}), 500