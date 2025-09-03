"""
Blueprint de Relatórios de Produção
Exportação de dados de estoque e movimentações
"""

from flask import Blueprint, jsonify, send_file
from datetime import datetime, date, timedelta
import pandas as pd
import io
from app.estoque.models import UnificacaoCodigos
# MIGRADO: EstoqueTempoReal e MovimentacaoPrevista -> ServicoEstoqueSimples (02/09/2025)
from app.estoque.services.estoque_simples import ServicoEstoqueSimples
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
        
        # Obter estoque completo usando novo serviço
        estoques_dict = ServicoEstoqueSimples.exportar_estoque_completo()
        
        # Buscar informações de palletização
        palletizacoes = {p.cod_produto: p for p in CadastroPalletizacao.query.all()}
        
        # Converter dados do serviço para formato do relatório
        for cod_produto, estoque_info in estoques_dict.items():
            # Verificar unificação de códigos
            codigos_unificados = []
            try:
                # Converter código do produto para inteiro se possível
                cod_produto_int = int(cod_produto) if cod_produto.isdigit() else None
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
            pallet_info = palletizacoes.get(cod_produto, None)
            
            # Calcular menor estoque D+7 se houver projeção
            menor_estoque_d7 = 0
            data_ruptura = None
            if estoque_info.get('projecao'):
                # Pegar os primeiros 7 dias da projeção
                projecao_7d = estoque_info['projecao'][:7]
                if projecao_7d:
                    estoques_7d = [dia.get('saldo_final', 0) for dia in projecao_7d]
                    menor_estoque_d7 = min(estoques_7d)
                    # Encontrar dia de ruptura (primeiro dia com estoque <= 0)
                    for dia in estoque_info['projecao']:
                        if dia.get('saldo_final', 0) <= 0:
                            data_ruptura = dia.get('data')
                            break
            
            dados_estoque.append({
                'Código Produto': cod_produto,
                'Nome Produto': estoque_info.get('nome_produto', ''),
                'Saldo Atual': float(estoque_info.get('estoque_atual', 0)),
                'Menor Estoque D+7': float(menor_estoque_d7),
                'Data Ruptura': data_ruptura.strftime('%d/%m/%Y') if data_ruptura else '',
                'Códigos Unificados': ', '.join(codigos_unificados) if codigos_unificados else '',
                'Peso Bruto (kg)': float(pallet_info.peso_bruto) if pallet_info else 0,
                'Palletização': float(pallet_info.palletizacao) if pallet_info else 0,
                'Categoria': pallet_info.categoria_produto if pallet_info else '',
                'Subcategoria': pallet_info.subcategoria if pallet_info else '',
                'Última Atualização': datetime.now().strftime('%d/%m/%Y %H:%M')
            })
        
        df_estoque = pd.DataFrame(dados_estoque)
        
        # Preparar dados de movimentações previstas
        dados_movimentacoes = []
        
        # Buscar movimentações previstas usando o novo serviço
        data_limite = date.today() + timedelta(days=30)
        
        # Obter todas as movimentações para os próximos 30 dias
        # Vamos iterar pelos produtos que temos no estoque
        for cod_produto, estoque_info in estoques_dict.items():
            nome_produto = estoque_info.get('nome_produto', cod_produto)
            
            # Se houver projeção, usar os dados dela
            if estoque_info.get('projecao'):
                for dia in estoque_info['projecao'][:30]:  # Limitar a 30 dias
                    data_prevista = dia.get('data')
                    if not data_prevista:
                        continue
                        
                    # Adicionar entrada se houver
                    entrada_val = float(dia.get('entrada', 0))
                    if entrada_val > 0:
                        dados_movimentacoes.append({
                            'Data Prevista': data_prevista.strftime('%d/%m/%Y') if hasattr(data_prevista, 'strftime') else str(data_prevista),
                            'Código Produto': cod_produto,
                            'Nome Produto': nome_produto,
                            'Tipo Movimento': 'Entrada',
                            'Quantidade': entrada_val,
                            'Observações': 'Produção/Entrada prevista'
                        })
                    
                    # Adicionar saída se houver
                    saida_val = float(dia.get('saida', 0))
                    if saida_val > 0:
                        dados_movimentacoes.append({
                            'Data Prevista': data_prevista.strftime('%d/%m/%Y') if hasattr(data_prevista, 'strftime') else str(data_prevista),
                            'Código Produto': cod_produto,
                            'Nome Produto': nome_produto,
                            'Tipo Movimento': 'Saída',
                            'Quantidade': saida_val,
                            'Observações': 'Separação/Expedição prevista'
                        })
        
        # Debug: verificar se há entradas
        logger.info(f"Total de movimentações encontradas: {len(dados_movimentacoes)}")
        for m in dados_movimentacoes[:5]:  # Mostrar primeiras 5 para debug
            logger.info(f"Produto {m['Código Produto']} em {m['Data Prevista']}: {m['Tipo Movimento']}={m['Quantidade']}")
        
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