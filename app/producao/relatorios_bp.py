"""
Blueprint de Relatórios de Produção
Exportação de dados de estoque e movimentações
"""

from flask import Blueprint, jsonify, send_file
from datetime import datetime
import pandas as pd
import io
from sqlalchemy import func
from app import db
from app.estoque.models import UnificacaoCodigos
from app.estoque.api_tempo_real import APIEstoqueTempoReal
from app.producao.models import CadastroPalletizacao
from app.separacao.models import Separacao
from app.carteira.models import CarteiraPrincipal
import logging
import math
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


def sanitizar_numero(valor):
    """
    Sanitiza um valor numérico para evitar NaN/Inf no Excel.

    Converte NaN e Inf em 0 para que o XlsxWriter possa processar.

    Args:
        valor: Valor a ser sanitizado

    Returns:
        float: Valor sanitizado (0 se NaN/Inf, valor original caso contrário)
    """
    try:
        # Verificar se é NaN ou Inf
        if pd.isna(valor) or math.isinf(float(valor)) or math.isnan(float(valor)):
            return 0
        return float(valor)
    except (TypeError, ValueError):
        return 0

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

        # 🆕 Buscar quantidades em Separação (sincronizado_nf=False)
        separacoes_query = db.session.query(
            Separacao.cod_produto,
            func.sum(Separacao.qtd_saldo).label('qtd_separacao')
        ).filter(
            Separacao.sincronizado_nf == False
        ).group_by(Separacao.cod_produto).all()

        qtd_separacao_dict = {s.cod_produto: float(s.qtd_separacao or 0) for s in separacoes_query}

        # 🆕 Buscar quantidades na Carteira Principal
        carteira_query = db.session.query(
            CarteiraPrincipal.cod_produto,
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('qtd_carteira')
        ).group_by(CarteiraPrincipal.cod_produto).all()

        qtd_carteira_dict = {c.cod_produto: float(c.qtd_carteira or 0) for c in carteira_query}

        # 🆕 Buscar quantidades programadas de produção
        from app.producao.models import ProgramacaoProducao
        producao_query = db.session.query(
            ProgramacaoProducao.cod_produto,
            func.sum(ProgramacaoProducao.qtd_programada).label('qtd_programada')
        ).group_by(ProgramacaoProducao.cod_produto).all()

        qtd_programada_dict = {p.cod_produto: float(p.qtd_programada or 0) for p in producao_query}

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

            # Buscar nome do produto de CadastroPalletizacao (fonte correta)
            nome_produto_correto = pallet_info.nome_produto if pallet_info else f"Produto {cod_produto}"

            # 🆕 Buscar quantidades de Separação, Carteira e Programação
            qtd_separacao = qtd_separacao_dict.get(cod_produto, 0)
            qtd_carteira = qtd_carteira_dict.get(cod_produto, 0)
            qtd_programada = qtd_programada_dict.get(cod_produto, 0)

            dados_estoque.append({
                'Código Produto': cod_produto,
                'Nome Produto': nome_produto_correto,  # Usar nome de CadastroPalletizacao
                'Saldo Atual': int(estoque_info.get('estoque_atual', 0)),  # Sem casas decimais
                'Qtd em Separação': int(qtd_separacao),  # 🆕 NOVA COLUNA
                'Qtd Total Carteira': int(qtd_carteira),  # 🆕 NOVA COLUNA
                'Qtd Programada Produção': int(qtd_programada),  # 🆕 NOVA COLUNA
                'Menor Estoque D+7': int(menor_estoque_d7),  # Sem casas decimais
                'Data Ruptura': data_ruptura_obj,  # Usar objeto datetime
                'Códigos Unificados': ', '.join(codigos_unificados) if codigos_unificados else '',
                'Peso Bruto (kg)': float(pallet_info.peso_bruto) if pallet_info else 0,
                'Palletização': float(pallet_info.palletizacao) if pallet_info else 0,
                'Categoria': pallet_info.categoria_produto if pallet_info else '',
                'Linha': pallet_info.linha_producao if pallet_info else '',  # ✅ NOVA COLUNA
                'MP': pallet_info.tipo_materia_prima if pallet_info else '',  # ✅ NOVA COLUNA
                'Emb.': pallet_info.tipo_embalagem if pallet_info else '',  # ✅ NOVA COLUNA
                'Última Atualização': agora_utc_naive()  # Manter como datetime para formatação correta
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
            # Buscar nome e categorias de CadastroPalletizacao
            pallet_info_mov = palletizacoes.get(cod_produto, None)
            nome_produto = pallet_info_mov.nome_produto if pallet_info_mov else f"Produto {cod_produto}"
            categoria_produto = pallet_info_mov.categoria_produto if pallet_info_mov else ''
            linha_producao = pallet_info_mov.linha_producao if pallet_info_mov else ''
            tipo_materia_prima = pallet_info_mov.tipo_materia_prima if pallet_info_mov else ''
            tipo_embalagem = pallet_info_mov.tipo_embalagem if pallet_info_mov else ''

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
                            'categoria': categoria_produto,
                            'linha_producao': linha_producao,
                            'tipo_materia_prima': tipo_materia_prima,
                            'tipo_embalagem': tipo_embalagem,
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
                'Linha': mov['linha_producao'],  # ✅ NOVA COLUNA após Data
                'Código Produto': mov['cod_produto'],
                'Nome Produto': mov['nome_produto'],
                'Categoria': mov['categoria'],
                'MP': mov['tipo_materia_prima'],  # ✅ NOVA COLUNA após Categoria
                'Emb.': mov['tipo_embalagem'],  # ✅ NOVA COLUNA após MP
                'Saídas Previstas': int(round(mov['saida'])),  # Inteiro puro
                'Entradas Previstas': int(round(mov['entrada'])),  # Inteiro puro
                'Saldo Projetado': int(round(mov['saldo']))  # Inteiro puro
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

        # 🆕 PREPARAR DADOS DE SAÍDAS PREVISTAS (SEM PROGRAMAÇÃO DE PRODUÇÃO)
        dados_saidas_previstas = []

        # Iterar pelos produtos que têm saídas previstas
        for cod_produto, estoque_info in estoques_dict.items():
            # Buscar informações de palletização
            pallet_info_saidas = palletizacoes.get(cod_produto, None)
            nome_produto = pallet_info_saidas.nome_produto if pallet_info_saidas else f"Produto {cod_produto}"
            linha_producao = pallet_info_saidas.linha_producao if pallet_info_saidas else ''  # ✅ NOVA
            tipo_materia_prima = pallet_info_saidas.tipo_materia_prima if pallet_info_saidas else ''  # ✅ NOVA

            # Verificar se há projeção
            projecao = estoque_info.get('projecao')
            if projecao and isinstance(projecao, list):
                # Estoque atual (D0)
                estoque_atual = estoque_info.get('estoque_atual', 0)

                # Processar cada dia da projeção
                for idx, dia in enumerate(projecao[:30]):  # Limitar a 30 dias
                    if not isinstance(dia, dict):
                        continue

                    # Obter data
                    data_prevista = dia.get('data')
                    if not data_prevista:
                        continue

                    # Converter data para datetime object
                    data_obj = None
                    if hasattr(data_prevista, 'strftime'):
                        data_obj = data_prevista
                    else:
                        try:
                            data_str = str(data_prevista)[:10]
                            if '-' in data_str and len(data_str) == 10:
                                ano, mes, dia_parte = data_str.split('-')
                                data_obj = datetime(int(ano), int(mes), int(dia_parte))
                        except Exception as e:
                            continue

                    # Obter saída do dia (SEM considerar entrada/produção)
                    try:
                        saida_dia = float(dia.get('saida', 0) or dia.get('saidas', 0) or 0)
                    except (TypeError, ValueError):
                        saida_dia = 0

                    # Apenas adicionar linhas com saída > 0
                    if saida_dia > 0:
                        # Calcular saída acumulada até este dia
                        saida_acumulada = 0
                        for d in projecao[:idx+1]:
                            if isinstance(d, dict):
                                try:
                                    saida_acumulada += float(d.get('saida', 0) or d.get('saidas', 0) or 0)
                                except (TypeError, ValueError):
                                    pass

                        # Calcular saldo SEM programação de produção
                        # saldo = estoque_atual - saída_acumulada
                        saldo_sem_producao = estoque_atual - saida_acumulada

                        dados_saidas_previstas.append({
                            'Código Produto': cod_produto,
                            'Nome Produto': nome_produto,
                            'Linha': linha_producao,  # ✅ NOVA COLUNA
                            'MP': tipo_materia_prima,  # ✅ NOVA COLUNA
                            'Data': data_obj,
                            'Estoque Atual': int(estoque_atual),
                            'Saída do Dia': int(round(saida_dia)),
                            'Saída Acumulada': int(round(saida_acumulada)),
                            'Saldo sem Produção': int(round(saldo_sem_producao))
                        })

        df_saidas_previstas = pd.DataFrame(dados_saidas_previstas)

        # 🆕 PREPARAR DADOS DA ABA SEPARAÇÃO
        dados_separacao = []

        # Buscar todos os registros de separação não sincronizados
        separacoes_detalhadas = Separacao.query.filter_by(
            sincronizado_nf=False
        ).order_by(
            Separacao.expedicao.asc(),
            Separacao.num_pedido.asc()
        ).all()

        for sep in separacoes_detalhadas:
            # ✅ Buscar informações de palletização para obter Linha e MP
            pallet_info_sep = palletizacoes.get(sep.cod_produto, None)
            linha_producao_sep = pallet_info_sep.linha_producao if pallet_info_sep else ''
            tipo_materia_prima_sep = pallet_info_sep.tipo_materia_prima if pallet_info_sep else ''

            dados_separacao.append({
                'Número Pedido': sep.num_pedido or '',
                'CNPJ': sep.cnpj_cpf or '',
                'Cliente': sep.raz_social_red or '',
                'Data Expedição': sep.expedicao,  # Objeto date
                'Código Produto': sep.cod_produto or '',
                'Nome Produto': sep.nome_produto or '',
                'Linha': linha_producao_sep,  # ✅ NOVA COLUNA
                'MP': tipo_materia_prima_sep,  # ✅ NOVA COLUNA
                'Quantidade': int(round(sep.qtd_saldo)) if sep.qtd_saldo else 0
            })

        df_separacao = pd.DataFrame(dados_separacao)

        # 📊 Gerar Excel com quatro abas:
        # 1. Estoque Atual
        # 2. Movimentações Previstas (com entradas de produção)
        # 3. Saídas Previstas (SEM programação de produção) 🆕
        # 4. Separação (dados detalhados) 🆕
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

            # Formatos para números
            # Formato inteiro sem decimais
            formato_inteiro = workbook.add_format({
                'num_format': '0',  # Inteiro simples sem decimais
                'border': 1
            })

            # Formato com 2 decimais e separador de milhar
            formato_decimal = workbook.add_format({
                'num_format': '#.##0,00',  # Separador de milhar com ponto, decimal com vírgula
                'border': 1
            })

            # Formato para datas DD/MM/YYYY
            formato_data = workbook.add_format({
                'num_format': 'dd/mm/yyyy',
                'border': 1
            })

            # Formato para data e hora
            formato_data_hora = workbook.add_format({
                'num_format': 'dd/mm/yyyy hh:mm',
                'border': 1
            })

            # Reescrever cabeçalhos e aplicar formatos
            for col_num, col_name in enumerate(df_estoque.columns):
                worksheet_estoque.write(0, col_num, col_name, header_format)

            # Reescrever dados com formatos corretos
            for row_num in range(len(df_estoque)):
                for col_num, col_name in enumerate(df_estoque.columns):
                    valor = df_estoque.iloc[row_num, col_num]

                    if col_name in ['Saldo Atual', 'Menor Estoque D+7', 'Qtd em Separação', 'Qtd Total Carteira', 'Qtd Programada Produção']:
                        # Escrever número inteiro com formato de milhar (sanitizado)
                        worksheet_estoque.write_number(row_num + 1, col_num, sanitizar_numero(valor), formato_inteiro)
                    elif col_name == 'Data Ruptura':
                        # Escrever data com formato DD/MM/YYYY
                        if pd.notna(valor):
                            worksheet_estoque.write_datetime(row_num + 1, col_num, valor, formato_data)
                        else:
                            worksheet_estoque.write(row_num + 1, col_num, '', formato_data)
                    elif col_name == 'Última Atualização':
                        # Escrever data e hora com formato
                        if pd.notna(valor):
                            worksheet_estoque.write_datetime(row_num + 1, col_num, valor, formato_data_hora)
                        else:
                            worksheet_estoque.write(row_num + 1, col_num, '', formato_data_hora)
                    elif col_name in ['Peso Bruto (kg)', 'Palletização']:
                        # Escrever número decimal com formato (sanitizado)
                        worksheet_estoque.write_number(row_num + 1, col_num, sanitizar_numero(valor), formato_decimal)
                    else:
                        # Escrever texto normal
                        worksheet_estoque.write(row_num + 1, col_num, str(valor) if pd.notna(valor) else '')

            # Ajustar larguras das colunas
            for col_num, col_name in enumerate(df_estoque.columns):
                if col_name in ['Saldo Atual', 'Menor Estoque D+7', 'Peso Bruto (kg)', 'Palletização']:
                    worksheet_estoque.set_column(col_num, col_num, 15)
                elif col_name in ['Qtd em Separação', 'Qtd Total Carteira']:  # 🆕 NOVAS COLUNAS
                    worksheet_estoque.set_column(col_num, col_num, 18)
                elif col_name == 'Qtd Programada Produção':  # 🆕 NOVA COLUNA
                    worksheet_estoque.set_column(col_num, col_num, 22)
                elif col_name in ['Data Ruptura', 'Última Atualização']:
                    worksheet_estoque.set_column(col_num, col_num, 18)
                elif col_name == 'Linha':
                    worksheet_estoque.set_column(col_num, col_num, 15)  # ✅ NOVA
                elif col_name == 'MP':
                    worksheet_estoque.set_column(col_num, col_num, 15)  # ✅ NOVA
                elif col_name == 'Emb.':
                    worksheet_estoque.set_column(col_num, col_num, 12)  # ✅ NOVA
                else:
                    column_width = max(df_estoque[col_name].fillna('').astype(str).map(len).max() if len(df_estoque) > 0 else 10, len(col_name)) + 2
                    worksheet_estoque.set_column(col_num, col_num, min(column_width, 50))
            
            # Aba de Movimentações Previstas - NOVO FORMATO COM 3 COLUNAS
            if len(df_movimentacoes) > 0:
                df_movimentacoes.to_excel(writer, sheet_name='Movimentações Previstas', index=False)
                worksheet_mov = writer.sheets['Movimentações Previstas']

                # Reescrever cabeçalhos
                for col_num, col_name in enumerate(df_movimentacoes.columns):
                    worksheet_mov.write(0, col_num, col_name, header_format)

                # Ajustar larguras das colunas
                for col_num, col_name in enumerate(df_movimentacoes.columns):
                    if col_name == 'Data':
                        worksheet_mov.set_column(col_num, col_num, 12)
                    elif col_name == 'Linha':
                        worksheet_mov.set_column(col_num, col_num, 15)  # ✅ NOVA
                    elif col_name == 'Código Produto':
                        worksheet_mov.set_column(col_num, col_num, 15)
                    elif col_name == 'Nome Produto':
                        worksheet_mov.set_column(col_num, col_num, 40)
                    elif col_name == 'Categoria':
                        worksheet_mov.set_column(col_num, col_num, 20)
                    elif col_name == 'MP':
                        worksheet_mov.set_column(col_num, col_num, 15)  # ✅ NOVA
                    elif col_name == 'Emb.':
                        worksheet_mov.set_column(col_num, col_num, 12)  # ✅ NOVA
                    elif col_name in ['Saídas Previstas', 'Entradas Previstas', 'Saldo Projetado']:
                        worksheet_mov.set_column(col_num, col_num, 18)

                # Adicionar formatação condicional para as linhas com formato de número brasileiro
                # Formato para células com números e cor de fundo
                entrada_format_num = workbook.add_format({
                    'bg_color': '#E8F5E9',
                    'border': 1,
                    'num_format': '0'  # Inteiro simples
                })
                entrada_format = workbook.add_format({'bg_color': '#E8F5E9', 'border': 1})

                saida_format_num = workbook.add_format({
                    'bg_color': '#FFEBEE',
                    'border': 1,
                    'num_format': '0'  # Inteiro simples
                })
                saida_format = workbook.add_format({'bg_color': '#FFEBEE', 'border': 1})

                # Formato para saldo negativo (vermelho escuro, sem decimais)
                saldo_negativo_format = workbook.add_format({
                    'bg_color': '#FF5252',
                    'font_color': 'white',
                    'border': 1,
                    'num_format': '0'  # Inteiro simples
                })

                # Formato neutro
                neutro_format_num = workbook.add_format({
                    'border': 1,
                    'num_format': '0'  # Inteiro simples
                })
                neutro_format = workbook.add_format({'border': 1})

                # Formato para datas com cor de fundo dd/mm/yyyy
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
                            worksheet_mov.write_datetime(row_num, col_num, valor, formato_data_linha)
                        elif col_name in ['Código Produto', 'Nome Produto', 'Categoria', 'Linha', 'MP', 'Emb.']:
                            worksheet_mov.write(row_num, col_num, str(valor) if pd.notna(valor) else '', formato_texto)
                        elif col_name == 'Saldo Projetado' and saldo_negativo:
                            # Saldo negativo - formato especial vermelho escuro (sanitizado)
                            worksheet_mov.write_number(row_num, col_num, sanitizar_numero(valor), saldo_negativo_format)
                        elif col_name in ['Saídas Previstas', 'Entradas Previstas', 'Saldo Projetado']:
                            # Colunas numéricas com formato de milhar (sanitizado)
                            worksheet_mov.write_number(row_num, col_num, sanitizar_numero(valor), formato_numero)
                        else:
                            worksheet_mov.write(row_num, col_num, str(valor) if pd.notna(valor) else '', formato_texto)
            else:
                # Criar aba vazia se não houver movimentações
                logger.warning("Criando aba vazia de Movimentações Previstas")
                df_vazia = pd.DataFrame(columns=['Data', 'Linha', 'Código Produto', 'Nome Produto',
                                                 'Categoria', 'MP', 'Emb.',
                                                 'Saídas Previstas', 'Entradas Previstas', 'Saldo Projetado'])
                df_vazia.to_excel(writer, sheet_name='Movimentações Previstas', index=False)
                worksheet_mov = writer.sheets['Movimentações Previstas']

                # Adicionar cabeçalho mesmo vazio
                for col_num, col_name in enumerate(df_vazia.columns):
                    worksheet_mov.write(0, col_num, col_name, header_format)

            # 🆕 ABA DE SAÍDAS PREVISTAS (SEM PROGRAMAÇÃO DE PRODUÇÃO)
            if len(df_saidas_previstas) > 0:
                df_saidas_previstas.to_excel(writer, sheet_name='Saídas Previstas', index=False)
                worksheet_saidas = writer.sheets['Saídas Previstas']

                # Reescrever cabeçalhos
                for col_num, col_name in enumerate(df_saidas_previstas.columns):
                    worksheet_saidas.write(0, col_num, col_name, header_format)

                # Formatos para esta aba
                formato_inteiro_saida = workbook.add_format({
                    'num_format': '0',
                    'border': 1
                })

                formato_data_saida = workbook.add_format({
                    'num_format': 'dd/mm/yyyy',
                    'border': 1
                })

                # Formato para saldo negativo (vermelho)
                formato_saldo_negativo = workbook.add_format({
                    'bg_color': '#FF5252',
                    'font_color': 'white',
                    'border': 1,
                    'num_format': '0'
                })

                formato_texto_saida = workbook.add_format({'border': 1})

                # Aplicar formatação linha por linha
                for row_num in range(1, len(df_saidas_previstas) + 1):
                    row_data = df_saidas_previstas.iloc[row_num - 1]

                    for col_num, col_name in enumerate(df_saidas_previstas.columns):
                        valor = row_data.iloc[col_num]

                        if col_name == 'Data':
                            worksheet_saidas.write_datetime(row_num, col_num, valor, formato_data_saida)
                        elif col_name in ['Código Produto', 'Nome Produto', 'Linha', 'MP']:  # ✅ Incluir novas colunas
                            worksheet_saidas.write(row_num, col_num, str(valor) if pd.notna(valor) else '', formato_texto_saida)
                        elif col_name == 'Saldo sem Produção' and valor < 0:
                            # Saldo negativo - formato especial vermelho (sanitizado)
                            worksheet_saidas.write_number(row_num, col_num, sanitizar_numero(valor), formato_saldo_negativo)
                        elif col_name in ['Estoque Atual', 'Saída do Dia', 'Saída Acumulada', 'Saldo sem Produção']:
                            # Colunas numéricas (sanitizado)
                            worksheet_saidas.write_number(row_num, col_num, sanitizar_numero(valor), formato_inteiro_saida)
                        else:
                            worksheet_saidas.write(row_num, col_num, str(valor) if pd.notna(valor) else '', formato_texto_saida)

                # Ajustar larguras das colunas
                worksheet_saidas.set_column(0, 0, 15)  # Código Produto
                worksheet_saidas.set_column(1, 1, 40)  # Nome Produto
                worksheet_saidas.set_column(2, 2, 15)  # ✅ Linha
                worksheet_saidas.set_column(3, 3, 15)  # ✅ MP
                worksheet_saidas.set_column(4, 4, 12)  # Data
                worksheet_saidas.set_column(5, 5, 15)  # Estoque Atual
                worksheet_saidas.set_column(6, 6, 15)  # Saída do Dia
                worksheet_saidas.set_column(7, 7, 18)  # Saída Acumulada
                worksheet_saidas.set_column(8, 8, 20)  # Saldo sem Produção
            else:
                # Criar aba vazia se não houver saídas previstas
                logger.warning("Criando aba vazia de Saídas Previstas")
                df_vazia_saidas = pd.DataFrame(columns=[
                    'Código Produto', 'Nome Produto', 'Linha', 'MP', 'Data',  # ✅ Incluir Linha e MP
                    'Estoque Atual', 'Saída do Dia',
                    'Saída Acumulada', 'Saldo sem Produção'
                ])
                df_vazia_saidas.to_excel(writer, sheet_name='Saídas Previstas', index=False)
                worksheet_saidas = writer.sheets['Saídas Previstas']

                # Adicionar cabeçalho mesmo vazio
                for col_num, col_name in enumerate(df_vazia_saidas.columns):
                    worksheet_saidas.write(0, col_num, col_name, header_format)

            # 🆕 ABA DE SEPARAÇÃO (DADOS DETALHADOS)
            if len(df_separacao) > 0:
                df_separacao.to_excel(writer, sheet_name='Separação', index=False)
                worksheet_sep = writer.sheets['Separação']

                # Reescrever cabeçalhos
                for col_num, col_name in enumerate(df_separacao.columns):
                    worksheet_sep.write(0, col_num, col_name, header_format)

                # Formatos para esta aba
                formato_inteiro_sep = workbook.add_format({
                    'num_format': '0',
                    'border': 1
                })

                formato_data_sep = workbook.add_format({
                    'num_format': 'dd/mm/yyyy',
                    'border': 1
                })

                formato_texto_sep = workbook.add_format({'border': 1})

                # Aplicar formatação linha por linha
                for row_num in range(1, len(df_separacao) + 1):
                    row_data = df_separacao.iloc[row_num - 1]

                    for col_num, col_name in enumerate(df_separacao.columns):
                        valor = row_data.iloc[col_num]

                        if col_name == 'Data Expedição':
                            # Escrever data com formato DD/MM/YYYY
                            if pd.notna(valor):
                                worksheet_sep.write_datetime(row_num, col_num, valor, formato_data_sep)
                            else:
                                worksheet_sep.write(row_num, col_num, '', formato_data_sep)
                        elif col_name == 'Quantidade':
                            # Coluna numérica (sanitizado)
                            worksheet_sep.write_number(row_num, col_num, sanitizar_numero(valor), formato_inteiro_sep)
                        else:
                            # Colunas de texto (inclui Linha e MP)
                            worksheet_sep.write(row_num, col_num, str(valor) if pd.notna(valor) else '', formato_texto_sep)

                # Ajustar larguras das colunas
                worksheet_sep.set_column(0, 0, 15)  # Número Pedido
                worksheet_sep.set_column(1, 1, 18)  # CNPJ
                worksheet_sep.set_column(2, 2, 35)  # Cliente
                worksheet_sep.set_column(3, 3, 15)  # Data Expedição
                worksheet_sep.set_column(4, 4, 15)  # Código Produto
                worksheet_sep.set_column(5, 5, 40)  # Nome Produto
                worksheet_sep.set_column(6, 6, 15)  # ✅ Linha
                worksheet_sep.set_column(7, 7, 15)  # ✅ MP
                worksheet_sep.set_column(8, 8, 12)  # Quantidade
            else:
                # Criar aba vazia se não houver dados de separação
                logger.warning("Criando aba vazia de Separação")
                df_vazia_sep = pd.DataFrame(columns=[
                    'Número Pedido', 'CNPJ', 'Cliente', 'Data Expedição',
                    'Código Produto', 'Nome Produto', 'Linha', 'MP', 'Quantidade'  # ✅ Incluir Linha e MP
                ])
                df_vazia_sep.to_excel(writer, sheet_name='Separação', index=False)
                worksheet_sep = writer.sheets['Separação']

                # Adicionar cabeçalho mesmo vazio
                for col_num, col_name in enumerate(df_vazia_sep.columns):
                    worksheet_sep.write(0, col_num, col_name, header_format)

        output.seek(0)
        
        filename = f'relatorio_producao_{agora_utc_naive().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Erro ao exportar relatórios de produção: {str(e)}")
        return jsonify({'error': str(e)}), 500