"""
Blueprint de Relatórios de Produção
Exportação de dados de estoque e movimentações
"""

from flask import Blueprint, jsonify, send_file
from datetime import datetime, date, timedelta
import pandas as pd
import io
from app.estoque.models import UnificacaoCodigos
from app.estoque.services.estoque_simples import ServicoEstoqueSimples
from app.estoque.api_tempo_real import APIEstoqueTempoReal
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
        
        # Obter estoque completo usando API de tempo real
        estoques_list = APIEstoqueTempoReal.exportar_estoque_completo()
        # Converter lista para dicionário indexado por cod_produto
        estoques_dict = {item['cod_produto']: item for item in estoques_list}
        
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
        
        # Preparar dados de movimentações previstas - FORMATO UNIFICADO
        # Uma linha por dia/produto com 3 colunas: saídas, entradas, saldo
        dados_movimentacoes = []
        movimentacoes_por_dia_produto = {}  # Chave: (data, cod_produto)

        # DEBUG: verificar estrutura dos dados
        logger.info(f"Total de produtos com estoque: {len(estoques_dict)}")
        produtos_com_projecao = 0
        total_dias_com_movimento = 0

        # Iterar pelos produtos que têm dados de estoque
        for cod_produto, estoque_info in estoques_dict.items():
            nome_produto = estoque_info.get('nome_produto', cod_produto)

            # Verificar se há projeção
            if estoque_info.get('projecao'):
                produtos_com_projecao += 1
                logger.info(f"Produto {cod_produto} tem {len(estoque_info['projecao'])} dias de projeção")

                for dia in estoque_info['projecao'][:30]:  # Limitar a 30 dias
                    # Obter data - pode estar como string ou objeto
                    data_prevista = dia.get('data')
                    if not data_prevista:
                        continue

                    # Converter data para string formatada consistente
                    if hasattr(data_prevista, 'strftime'):
                        data_str = data_prevista.strftime('%Y-%m-%d')
                        data_formatada = data_prevista.strftime('%d/%m/%Y')
                    else:
                        data_str = str(data_prevista)[:10]  # YYYY-MM-DD
                        data_formatada = data_str  # Formatar depois se necessário

                    # Obter valores - usar múltiplos nomes possíveis para compatibilidade
                    entrada_val = float(dia.get('entrada', 0) or dia.get('producao', 0))
                    saida_val = float(dia.get('saida', 0) or dia.get('saidas', 0))
                    saldo_val = float(dia.get('saldo_final', 0) or dia.get('estoque_final', 0))

                    # Adicionar apenas se houver entrada OU saída
                    if entrada_val > 0 or saida_val > 0:
                        total_dias_com_movimento += 1
                        chave = (data_str, cod_produto)
                        movimentacoes_por_dia_produto[chave] = {
                            'data_str': data_str,
                            'data_formatada': data_formatada,
                            'cod_produto': cod_produto,
                            'nome_produto': nome_produto,
                            'saida': saida_val,
                            'entrada': entrada_val,
                            'saldo': saldo_val
                        }

        logger.info(f"Produtos com projeção: {produtos_com_projecao}")
        logger.info(f"Total de dias com movimentação: {total_dias_com_movimento}")

        # Converter dicionário para lista ordenada por data e produto
        for (data_str, cod_produto), mov in sorted(movimentacoes_por_dia_produto.items()):
            dados_movimentacoes.append({
                'Data': mov['data_formatada'],
                'Código Produto': mov['cod_produto'],
                'Nome Produto': mov['nome_produto'],
                'Saídas Previstas': mov['saida'],
                'Entradas Previstas': mov['entrada'],
                'Saldo Projetado': mov['saldo']
            })
        
        # Debug: verificar movimentações
        logger.info(f"Total de linhas de movimentações (dia/produto): {len(dados_movimentacoes)}")
        if dados_movimentacoes:
            logger.info(f"Primeiras 3 movimentações:")
            for i, mov in enumerate(dados_movimentacoes[:3]):
                logger.info(f"  {i+1}. Data={mov['Data']}, Produto={mov['Código Produto']}, "
                           f"Saída={mov['Saídas Previstas']}, Entrada={mov['Entradas Previstas']}, "
                           f"Saldo={mov['Saldo Projetado']}")
        else:
            logger.warning("Nenhuma movimentação prevista encontrada!")
        
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
            
            # Aba de Movimentações Previstas - NOVO FORMATO COM 3 COLUNAS
            if len(df_movimentacoes) > 0:
                df_movimentacoes.to_excel(writer, sheet_name='Movimentações Previstas', index=False)
                worksheet_mov = writer.sheets['Movimentações Previstas']

                # Aplicar formatos no cabeçalho
                for col_num, col_name in enumerate(df_movimentacoes.columns):
                    worksheet_mov.write(0, col_num, col_name, header_format)

                    # Definir larguras específicas de coluna
                    if col_name == 'Data':
                        worksheet_mov.set_column(col_num, col_num, 12)
                    elif col_name == 'Código Produto':
                        worksheet_mov.set_column(col_num, col_num, 15)
                    elif col_name == 'Nome Produto':
                        worksheet_mov.set_column(col_num, col_num, 40)
                    elif 'Previstas' in col_name or 'Saldo' in col_name:
                        worksheet_mov.set_column(col_num, col_num, 18, number_format)

                # Adicionar formatação condicional para as linhas
                # Formato para linhas com entrada (verde claro)
                entrada_format = workbook.add_format({'bg_color': '#E8F5E9', 'border': 1})
                # Formato para linhas com saída (vermelho claro)
                saida_format = workbook.add_format({'bg_color': '#FFEBEE', 'border': 1})
                # Formato para saldo negativo (vermelho escuro)
                saldo_negativo_format = workbook.add_format({
                    'bg_color': '#FF5252',
                    'font_color': 'white',
                    'border': 1,
                    'num_format': '#,##0.00'
                })
                # Formato neutro com borda
                neutro_format = workbook.add_format({'border': 1})

                # Aplicar formatação linha por linha
                for row_num in range(1, len(df_movimentacoes) + 1):
                    row_data = df_movimentacoes.iloc[row_num - 1]

                    # Determinar cor de fundo baseado em entrada/saída
                    has_entrada = row_data['Entradas Previstas'] > 0
                    has_saida = row_data['Saídas Previstas'] > 0
                    saldo_negativo = row_data['Saldo Projetado'] < 0

                    if has_entrada and not has_saida:
                        # Só entrada - verde
                        row_format = entrada_format
                    elif has_saida and not has_entrada:
                        # Só saída - vermelho claro
                        row_format = saida_format
                    else:
                        # Ambos ou nenhum - neutro
                        row_format = neutro_format

                    # Aplicar formato em cada célula da linha
                    for col_num in range(len(df_movimentacoes.columns)):
                        valor = row_data.iloc[col_num]
                        # Se for saldo negativo, usar formato especial
                        if col_num == 5 and saldo_negativo:  # Coluna do Saldo Projetado
                            worksheet_mov.write(row_num, col_num, valor, saldo_negativo_format)
                        else:
                            worksheet_mov.write(row_num, col_num, valor, row_format)
            else:
                # Criar aba vazia se não houver movimentações
                logger.warning("Criando aba vazia de Movimentações Previstas")
                df_vazia = pd.DataFrame(columns=['Data', 'Código Produto', 'Nome Produto',
                                                 'Saídas Previstas', 'Entradas Previstas', 'Saldo Projetado'])
                df_vazia.to_excel(writer, sheet_name='Movimentações Previstas', index=False)
                worksheet_mov = writer.sheets['Movimentações Previstas']

                # Adicionar cabeçalho mesmo vazio
                for col_num, col_name in enumerate(df_vazia.columns):
                    worksheet_mov.write(0, col_num, col_name, header_format)
        
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