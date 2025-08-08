"""
Blueprint de Relatórios de Produção
Exportação de dados de estoque e movimentações
"""

from flask import Blueprint, jsonify, send_file
from datetime import datetime, date, timedelta
import pandas as pd
import io
from sqlalchemy import func
from app import db
from app.estoque.models import UnificacaoCodigos
from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
from app.producao.models import CadastroPalletizacao
import logging

logger = logging.getLogger(__name__)

# Criar o blueprint de relatórios
relatorios_producao_bp = Blueprint('relatorios_producao', __name__, url_prefix='/producao/relatorios')

@relatorios_producao_bp.route('/exportar', methods=['GET'])
def exportar_relatorios_producao():
    """Exportar relatórios de produção com estoque e movimentações previstas"""
    try:
        # Preparar dados de estoque
        dados_estoque = []
        
        # Query de estoque em tempo real
        estoques = EstoqueTempoReal.query.order_by(EstoqueTempoReal.cod_produto).all()
        
        # Buscar informações de palletização
        palletizacoes = {p.cod_produto: p for p in CadastroPalletizacao.query.all()}
        
        for estoque in estoques:
            # Verificar unificação de códigos
            codigos_unificados = []
            try:
                # Converter código do produto para inteiro se possível
                cod_produto_int = int(estoque.cod_produto) if estoque.cod_produto.isdigit() else None
                if cod_produto_int:
                    # Buscar códigos unificados onde este produto é o destino
                    unificacoes = UnificacaoCodigos.query.filter_by(
                        codigo_destino=cod_produto_int,
                        ativo=True
                    ).all()
                    if unificacoes:
                        codigos_unificados = [str(u.codigo_origem) for u in unificacoes]
            except (ValueError, AttributeError):
                pass
            
            # Buscar informações de palletização
            pallet_info = palletizacoes.get(estoque.cod_produto, None)
            
            dados_estoque.append({
                'Código Produto': estoque.cod_produto,
                'Nome Produto': estoque.nome_produto,
                'Saldo Atual': float(estoque.saldo_atual or 0),
                'Menor Estoque D+7': float(estoque.menor_estoque_d7 or 0),
                'Data Ruptura': estoque.dia_ruptura.strftime('%d/%m/%Y') if estoque.dia_ruptura else '',
                'Códigos Unificados': ', '.join(codigos_unificados) if codigos_unificados else '',
                'Peso Bruto (kg)': float(pallet_info.peso_bruto) if pallet_info else 0,
                'Palletização': float(pallet_info.palletizacao) if pallet_info else 0,
                'Categoria': pallet_info.categoria_produto if pallet_info else '',
                'Subcategoria': pallet_info.subcategoria if pallet_info else '',
                'Última Atualização': estoque.atualizado_em.strftime('%d/%m/%Y %H:%M') if estoque.atualizado_em else ''
            })
        
        df_estoque = pd.DataFrame(dados_estoque)
        
        # Preparar dados de movimentações previstas
        dados_movimentacoes = []
        
        # Query de movimentações previstas para os próximos 30 dias
        data_limite = date.today() + timedelta(days=30)
        
        query_mov = MovimentacaoPrevista.query.filter(
            MovimentacaoPrevista.data_prevista <= data_limite
        ).order_by(
            MovimentacaoPrevista.data_prevista,
            MovimentacaoPrevista.cod_produto
        )
        
        movimentacoes = query_mov.all()
        
        # Debug: verificar se há entradas
        logger.info(f"Total de movimentações encontradas: {len(movimentacoes)}")
        for m in movimentacoes[:5]:  # Mostrar primeiras 5 para debug
            logger.info(f"Produto {m.cod_produto} em {m.data_prevista}: entrada={m.entrada_prevista}, saída={m.saida_prevista}")
        
        for mov in movimentacoes:
            # Buscar nome do produto do EstoqueTempoReal
            produto = EstoqueTempoReal.query.filter_by(cod_produto=mov.cod_produto).first()
            nome_produto = produto.nome_produto if produto else mov.cod_produto
            
            # Adicionar entrada se houver
            entrada_val = float(mov.entrada_prevista) if mov.entrada_prevista else 0
            if entrada_val > 0:
                dados_movimentacoes.append({
                    'Data Prevista': mov.data_prevista.strftime('%d/%m/%Y') if mov.data_prevista else '',
                    'Código Produto': mov.cod_produto,
                    'Nome Produto': nome_produto,
                    'Tipo Movimento': 'Entrada',
                    'Quantidade': entrada_val,
                    'Observações': 'Produção/Entrada prevista'
                })
            
            # Adicionar saída se houver
            saida_val = float(mov.saida_prevista) if mov.saida_prevista else 0
            if saida_val > 0:
                dados_movimentacoes.append({
                    'Data Prevista': mov.data_prevista.strftime('%d/%m/%Y') if mov.data_prevista else '',
                    'Código Produto': mov.cod_produto,
                    'Nome Produto': nome_produto,
                    'Tipo Movimento': 'Saída',
                    'Quantidade': saida_val,
                    'Observações': 'Separação/Expedição prevista'
                })
        
        df_movimentacoes = pd.DataFrame(dados_movimentacoes)
        
        # Gerar Excel com duas abas
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Aba de Estoque
            df_estoque.to_excel(writer, sheet_name='Estoque Atual', index=False)
            
            # Formatar aba de estoque
            workbook = writer.book
            worksheet_estoque = writer.sheets['Estoque Atual']
            
            # Formato para cabeçalho
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4CAF50',
                'font_color': 'white',
                'border': 1
            })
            
            # Formato para números
            number_format = workbook.add_format({
                'num_format': '#,##0.00',
                'border': 1
            })
            
            # Aplicar formatos
            for col_num, col_name in enumerate(df_estoque.columns):
                worksheet_estoque.write(0, col_num, col_name, header_format)
                if 'Saldo' in col_name or 'Peso' in col_name or 'Palletização' in col_name:
                    worksheet_estoque.set_column(col_num, col_num, 15, number_format)
                else:
                    column_width = max(df_estoque[col_name].astype(str).map(len).max() if len(df_estoque) > 0 else 10, len(col_name)) + 2
                    worksheet_estoque.set_column(col_num, col_num, min(column_width, 50))
            
            # Aba de Movimentações Previstas
            df_movimentacoes.to_excel(writer, sheet_name='Movimentações Previstas', index=False)
            
            worksheet_mov = writer.sheets['Movimentações Previstas']
            
            # Aplicar formatos na aba de movimentações
            for col_num, col_name in enumerate(df_movimentacoes.columns):
                worksheet_mov.write(0, col_num, col_name, header_format)
                column_width = max(df_movimentacoes[col_name].astype(str).map(len).max() if len(df_movimentacoes) > 0 else 10, len(col_name)) + 2
                worksheet_mov.set_column(col_num, col_num, min(column_width, 50))
            
            # Adicionar formatação condicional para tipos de movimento
            if len(df_movimentacoes) > 0:
                entrada_format = workbook.add_format({'bg_color': '#E8F5E9'})
                saida_format = workbook.add_format({'bg_color': '#FFEBEE'})
                
                for row_num in range(1, len(df_movimentacoes) + 1):
                    tipo_mov = df_movimentacoes.iloc[row_num - 1]['Tipo Movimento']
                    if tipo_mov == 'Entrada':
                        worksheet_mov.set_row(row_num, None, entrada_format)
                    elif tipo_mov == 'Saída':
                        worksheet_mov.set_row(row_num, None, saida_format)
        
        output.seek(0)
        
        filename = f'relatorio_producao_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Erro ao exportar relatórios de produção: {str(e)}")
        return jsonify({'error': str(e)}), 500