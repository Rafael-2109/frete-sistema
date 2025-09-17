"""
Blueprint de Relatórios de Produção
Exportação de dados de estoque e movimentações
"""

from flask import Blueprint, jsonify, send_file
from datetime import datetime, date
import pandas as pd
import io
from app.estoque.models import UnificacaoCodigos
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
            projecao = estoque_info.get('projecao')

            # Verificar se projecao existe e é uma lista
            if projecao and isinstance(projecao, list):
                # Pegar os primeiros 7 dias da projeção
                projecao_7d = projecao[:7]
                if projecao_7d:
                    estoques_7d = []
                    for dia in projecao_7d:
                        # Verificar se dia é um dicionário antes de usar .get()
                        if isinstance(dia, dict):
                            try:
                                saldo = float(dia.get('saldo_final', 0) or 0)
                                estoques_7d.append(saldo)
                            except (TypeError, ValueError):
                                estoques_7d.append(0)
                        else:
                            logger.warning(f"Elemento da projeção não é dicionário: {type(dia)}")

                    if estoques_7d:
                        menor_estoque_d7 = min(estoques_7d)

                    # Encontrar dia de ruptura (primeiro dia com estoque <= 0)
                    for dia in projecao:
                        if isinstance(dia, dict):
                            try:
                                saldo = float(dia.get('saldo_final', 0) or 0)
                                if saldo <= 0:
                                    data_ruptura = dia.get('data')
                                    break
                            except (TypeError, ValueError):
                                continue
                        else:
                            logger.warning(f"Elemento da projeção não é dicionário: {type(dia)}")
            
            # Converter data_ruptura para datetime object para ordenação correta no Excel
            data_ruptura_obj = None
            if data_ruptura:
                if hasattr(data_ruptura, 'strftime'):
                    # Já é um objeto datetime/date
                    data_ruptura_obj = data_ruptura
                else:
                    # É uma string - converter para datetime
                    try:
                        data_str = str(data_ruptura)[:10]  # YYYY-MM-DD
                        if '-' in data_str and len(data_str) == 10:
                            ano, mes, dia = data_str.split('-')
                            data_ruptura_obj = datetime(int(ano), int(mes), int(dia))
                    except Exception as e:
                        logger.warning(f"Erro ao converter data_ruptura para datetime: {e}")

            dados_estoque.append({
                'Código Produto': cod_produto,
                'Nome Produto': estoque_info.get('nome_produto', ''),
                'Saldo Atual': int(estoque_info.get('estoque_atual', 0)),  # Sem casas decimais
                'Menor Estoque D+7': int(menor_estoque_d7),  # Sem casas decimais
                'Data Ruptura': data_ruptura_obj,  # Usar objeto datetime
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

            # Verificar se há projeção e se é uma lista
            projecao = estoque_info.get('projecao')
            if projecao and isinstance(projecao, list):
                produtos_com_projecao += 1
                logger.info(f"Produto {cod_produto} tem {len(projecao)} dias de projeção")

                for dia in projecao[:30]:  # Limitar a 30 dias
                    # Verificar se o dia é um dicionário válido
                    if not isinstance(dia, dict):
                        logger.warning(f"Dia na projeção não é dict para produto {cod_produto}: {type(dia)}")
                        continue

                    # Obter data - pode estar como string ou objeto
                    data_prevista = dia.get('data')
                    if not data_prevista:
                        continue

                    # Converter data para datetime object para ordenação correta
                    data_obj = None
                    data_str = ''
                    if hasattr(data_prevista, 'strftime'):
                        # Já é datetime/date
                        data_obj = data_prevista
                        data_str = data_prevista.strftime('%Y-%m-%d')
                    else:
                        # É string - converter para datetime
                        data_str = str(data_prevista)[:10]  # YYYY-MM-DD
                        try:
                            if '-' in data_str and len(data_str) == 10:
                                ano, mes, dia_parte = data_str.split('-')
                                data_obj = datetime(int(ano), int(mes), int(dia_parte))
                        except Exception as e:
                            logger.warning(f"Erro ao converter data {data_str} para datetime: {e}")
                            continue  # Pular este dia se não conseguir converter

                    # Obter valores com tratamento de erro
                    try:
                        entrada_val = float(dia.get('entrada', 0) or dia.get('producao', 0) or 0)
                        saida_val = float(dia.get('saida', 0) or dia.get('saidas', 0) or 0)
                        saldo_val = float(dia.get('saldo_final', 0) or dia.get('estoque_final', 0) or 0)
                    except (TypeError, ValueError) as e:
                        logger.warning(f"Erro ao converter valores para produto {cod_produto}: {e}")
                        entrada_val = saida_val = saldo_val = 0

                    # Adicionar apenas se houver entrada OU saída
                    if entrada_val > 0 or saida_val > 0:
                        total_dias_com_movimento += 1
                        chave = (data_str, cod_produto)
                        movimentacoes_por_dia_produto[chave] = {
                            'data_str': data_str,
                            'data_obj': data_obj,  # Objeto datetime para ordenação correta
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
                'Data': mov['data_obj'],  # Usar datetime object para ordenação correta
                'Código Produto': mov['cod_produto'],
                'Nome Produto': mov['nome_produto'],
                'Saídas Previstas': int(mov['saida']),  # Sem decimais
                'Entradas Previstas': int(mov['entrada']),  # Sem decimais
                'Saldo Projetado': int(mov['saldo'])  # Sem decimais
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

            # Formatos para números com padrão brasileiro (separador de milhar com ponto)
            # Formato sem decimais com separador de milhar
            formato_inteiro = workbook.add_format({
                'num_format': '#.##0',  # Separador de milhar com ponto, sem decimais
                'border': 1
            })

            # Formato com 2 decimais e separador de milhar
            formato_decimal = workbook.add_format({
                'num_format': '#.##0,00',  # Separador de milhar com ponto, decimal com vírgula
                'border': 1
            })

            # Formato para datas
            formato_data = workbook.add_format({
                'num_format': 'dd/mm/yyyy',
                'border': 1
            })
            
            # Aplicar formatos
            for col_num, col_name in enumerate(df_estoque.columns):
                worksheet_estoque.write(0, col_num, col_name, header_format)

                if col_name == 'Saldo Atual' or col_name == 'Menor Estoque D+7':
                    # Formato inteiro com separador de milhar
                    worksheet_estoque.set_column(col_num, col_num, 15, formato_inteiro)
                elif col_name == 'Data Ruptura':
                    # Formato de data
                    worksheet_estoque.set_column(col_num, col_num, 12, formato_data)
                elif 'Peso' in col_name or 'Palletização' in col_name:
                    # Formato com 2 decimais
                    worksheet_estoque.set_column(col_num, col_num, 15, formato_decimal)
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

                    # Definir larguras específicas de coluna e formatos
                    if col_name == 'Data':
                        worksheet_mov.set_column(col_num, col_num, 12, formato_data)
                    elif col_name == 'Código Produto':
                        worksheet_mov.set_column(col_num, col_num, 15)
                    elif col_name == 'Nome Produto':
                        worksheet_mov.set_column(col_num, col_num, 40)
                    elif 'Saídas Previstas' in col_name or 'Entradas Previstas' in col_name:
                        # Formato inteiro com separador de milhar para entradas e saídas
                        worksheet_mov.set_column(col_num, col_num, 18, formato_inteiro)
                    elif 'Saldo Projetado' in col_name:
                        # Formato inteiro com separador de milhar para saldo
                        worksheet_mov.set_column(col_num, col_num, 18, formato_inteiro)

                # Adicionar formatação condicional para as linhas com formato de número brasileiro
                # Formato para células com números e cor de fundo
                entrada_format_num = workbook.add_format({
                    'bg_color': '#E8F5E9',
                    'border': 1,
                    'num_format': '#.##0'  # Separador de milhar com ponto
                })
                entrada_format = workbook.add_format({'bg_color': '#E8F5E9', 'border': 1})

                saida_format_num = workbook.add_format({
                    'bg_color': '#FFEBEE',
                    'border': 1,
                    'num_format': '#.##0'  # Separador de milhar com ponto
                })
                saida_format = workbook.add_format({'bg_color': '#FFEBEE', 'border': 1})

                # Formato para saldo negativo (vermelho escuro, sem decimais)
                saldo_negativo_format = workbook.add_format({
                    'bg_color': '#FF5252',
                    'font_color': 'white',
                    'border': 1,
                    'num_format': '#.##0'  # Sem decimais, separador com ponto
                })

                # Formato neutro
                neutro_format_num = workbook.add_format({
                    'border': 1,
                    'num_format': '#.##0'  # Separador de milhar com ponto
                })
                neutro_format = workbook.add_format({'border': 1})

                # Formato para datas com cor de fundo
                data_format_verde = workbook.add_format({
                    'bg_color': '#E8F5E9',
                    'border': 1,
                    'num_format': 'dd/mm/yyyy'
                })
                data_format_vermelho = workbook.add_format({
                    'bg_color': '#FFEBEE',
                    'border': 1,
                    'num_format': 'dd/mm/yyyy'
                })
                data_format_neutro = workbook.add_format({
                    'border': 1,
                    'num_format': 'dd/mm/yyyy'
                })

                # Aplicar formatação linha por linha
                for row_num in range(1, len(df_movimentacoes) + 1):
                    row_data = df_movimentacoes.iloc[row_num - 1]

                    # Determinar cor de fundo baseado em entrada/saída
                    has_entrada = row_data['Entradas Previstas'] > 0
                    has_saida = row_data['Saídas Previstas'] > 0
                    saldo_negativo = row_data['Saldo Projetado'] < 0

                    # Determinar formatos baseado no tipo de movimentação
                    if has_entrada and not has_saida:
                        # Só entrada - verde
                        formato_texto = entrada_format
                        formato_numero = entrada_format_num
                        formato_data_linha = data_format_verde
                    elif has_saida and not has_entrada:
                        # Só saída - vermelho claro
                        formato_texto = saida_format
                        formato_numero = saida_format_num
                        formato_data_linha = data_format_vermelho
                    else:
                        # Ambos ou nenhum - neutro
                        formato_texto = neutro_format
                        formato_numero = neutro_format_num
                        formato_data_linha = data_format_neutro

                    # Aplicar formato em cada célula da linha
                    for col_num, col_name in enumerate(df_movimentacoes.columns):
                        valor = row_data.iloc[col_num]

                        # Aplicar formato específico por tipo de coluna
                        if col_name == 'Data':
                            worksheet_mov.write(row_num, col_num, valor, formato_data_linha)
                        elif col_name in ['Código Produto', 'Nome Produto']:
                            worksheet_mov.write(row_num, col_num, valor, formato_texto)
                        elif col_name == 'Saldo Projetado' and saldo_negativo:
                            # Saldo negativo - formato especial vermelho escuro
                            worksheet_mov.write(row_num, col_num, valor, saldo_negativo_format)
                        elif col_name in ['Saídas Previstas', 'Entradas Previstas', 'Saldo Projetado']:
                            # Colunas numéricas
                            worksheet_mov.write(row_num, col_num, valor, formato_numero)
                        else:
                            worksheet_mov.write(row_num, col_num, valor, formato_texto)
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