"""
Rotas para CRUD de Recursos de Produção
Gerencia capacidades produtivas, linhas de produção e eficiências
"""

from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from app import db
from app.manufatura.models import RecursosProducao
from sqlalchemy import or_
from decimal import Decimal
import pandas as pd
from io import BytesIO
from datetime import datetime

recursos_bp = Blueprint('recursos_producao', __name__, url_prefix='/manufatura/recursos')


@recursos_bp.route('/')
@login_required
def listar():
    """Lista todos os recursos de produção"""
    return render_template('manufatura/recursos_producao.html')


@recursos_bp.route('/api/listar')
@login_required
def api_listar():
    """API para listar recursos com filtros e paginação"""
    try:
        # Parâmetros de filtro
        search = request.args.get('search', '').strip()
        linha = request.args.get('linha', '').strip()
        disponivel = request.args.get('disponivel', '')

        # Ordenação
        sort_by = request.args.get('sort_by', 'cod_produto')
        sort_order = request.args.get('sort_order', 'asc')

        # Query base
        query = RecursosProducao.query

        # Filtros
        if search:
            query = query.filter(
                or_(
                    RecursosProducao.cod_produto.ilike(f'%{search}%'),
                    RecursosProducao.nome_produto.ilike(f'%{search}%')
                )
            )

        if linha:
            query = query.filter(RecursosProducao.linha_producao.ilike(f'%{linha}%'))

        if disponivel:
            query = query.filter(RecursosProducao.disponivel == (disponivel == 'true'))

        # Ordenação
        if sort_order == 'desc':
            query = query.order_by(getattr(RecursosProducao, sort_by).desc())
        else:
            query = query.order_by(getattr(RecursosProducao, sort_by).asc())

        recursos = query.all()

        # Converter para dict
        dados = []
        for r in recursos:
            dados.append({
                'id': r.id,
                'cod_produto': r.cod_produto,
                'nome_produto': r.nome_produto,
                'linha_producao': r.linha_producao,
                'qtd_unidade_por_caixa': r.qtd_unidade_por_caixa,
                'capacidade_unidade_minuto': float(r.capacidade_unidade_minuto),
                'capacidade_dia': float(r.capacidade_unidade_minuto) * 60 * 8,  # 8h por dia
                'qtd_lote_ideal': float(r.qtd_lote_ideal) if r.qtd_lote_ideal else 0,
                'qtd_lote_minimo': float(r.qtd_lote_minimo) if r.qtd_lote_minimo else 0,
                'eficiencia_media': float(r.eficiencia_media),
                'tempo_setup': r.tempo_setup,
                'disponivel': r.disponivel,
                'criado_em': r.criado_em.strftime('%d/%m/%Y %H:%M') if r.criado_em else None
            })

        return jsonify({'success': True, 'dados': dados, 'total': len(dados)})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@recursos_bp.route('/api/criar', methods=['POST'])
@login_required
def api_criar():
    """API para criar novo recurso de produção"""
    try:
        data = request.get_json()

        # Validação básica
        campos_obrigatorios = ['cod_produto', 'linha_producao', 'qtd_unidade_por_caixa', 'capacidade_unidade_minuto']
        for campo in campos_obrigatorios:
            if not data.get(campo):
                return jsonify({'success': False, 'message': f'Campo obrigatório: {campo}'}), 400

        # Criar novo recurso
        recurso = RecursosProducao(
            cod_produto=data['cod_produto'].strip().upper(),
            nome_produto=data.get('nome_produto', '').strip(),
            linha_producao=data['linha_producao'].strip(),
            qtd_unidade_por_caixa=int(data['qtd_unidade_por_caixa']),
            capacidade_unidade_minuto=Decimal(str(data['capacidade_unidade_minuto'])),
            qtd_lote_ideal=Decimal(str(data.get('qtd_lote_ideal', 0))) if data.get('qtd_lote_ideal') else None,
            qtd_lote_minimo=Decimal(str(data.get('qtd_lote_minimo', 0))) if data.get('qtd_lote_minimo') else None,
            eficiencia_media=Decimal(str(data.get('eficiencia_media', 85))),
            tempo_setup=int(data.get('tempo_setup', 30)),
            disponivel=data.get('disponivel', True)
        )

        db.session.add(recurso)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Recurso criado com sucesso!',
            'id': recurso.id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@recursos_bp.route('/api/atualizar/<int:id>', methods=['PUT'])
@login_required
def api_atualizar(id):
    """API para atualizar recurso de produção"""
    try:
        recurso = RecursosProducao.query.get_or_404(id)
        data = request.get_json()

        # Atualizar campos
        if 'cod_produto' in data:
            recurso.cod_produto = data['cod_produto'].strip().upper()
        if 'nome_produto' in data:
            recurso.nome_produto = data['nome_produto'].strip()
        if 'linha_producao' in data:
            recurso.linha_producao = data['linha_producao'].strip()
        if 'qtd_unidade_por_caixa' in data:
            recurso.qtd_unidade_por_caixa = int(data['qtd_unidade_por_caixa'])
        if 'capacidade_unidade_minuto' in data:
            recurso.capacidade_unidade_minuto = Decimal(str(data['capacidade_unidade_minuto']))
        if 'qtd_lote_ideal' in data:
            recurso.qtd_lote_ideal = Decimal(str(data['qtd_lote_ideal'])) if data['qtd_lote_ideal'] else None
        if 'qtd_lote_minimo' in data:
            recurso.qtd_lote_minimo = Decimal(str(data['qtd_lote_minimo'])) if data['qtd_lote_minimo'] else None
        if 'eficiencia_media' in data:
            recurso.eficiencia_media = Decimal(str(data['eficiencia_media']))
        if 'tempo_setup' in data:
            recurso.tempo_setup = int(data['tempo_setup'])
        if 'disponivel' in data:
            recurso.disponivel = data['disponivel']

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Recurso atualizado com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@recursos_bp.route('/api/deletar/<int:id>', methods=['DELETE'])
@login_required
def api_deletar(id):
    """API para deletar recurso de produção"""
    try:
        recurso = RecursosProducao.query.get_or_404(id)

        db.session.delete(recurso)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Recurso deletado com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@recursos_bp.route('/api/linhas-producao')
@login_required
def api_linhas_producao():
    """API para listar linhas de produção únicas"""
    try:
        linhas = db.session.query(RecursosProducao.linha_producao).distinct().order_by(RecursosProducao.linha_producao).all()
        return jsonify({
            'success': True,
            'linhas': [linha[0] for linha in linhas if linha[0]]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==============================================================
# EXPORTAÇÃO E IMPORTAÇÃO XLSX
# ==============================================================

@recursos_bp.route('/exportar-xlsx')
@login_required
def exportar_xlsx():
    """Exporta todos os recursos de produção para XLSX"""
    try:
        recursos = RecursosProducao.query.order_by(RecursosProducao.cod_produto, RecursosProducao.linha_producao).all()

        # Nomes das colunas (iguais para export e import)
        dados = []
        for r in recursos:
            dados.append({
                'cod_produto': r.cod_produto,
                'nome_produto': r.nome_produto or '',
                'linha_producao': r.linha_producao,
                'qtd_unidade_por_caixa': r.qtd_unidade_por_caixa,
                'capacidade_unidade_minuto': float(r.capacidade_unidade_minuto),
                'qtd_lote_ideal': float(r.qtd_lote_ideal) if r.qtd_lote_ideal else '',
                'qtd_lote_minimo': float(r.qtd_lote_minimo) if r.qtd_lote_minimo else '',
                'eficiencia_media': float(r.eficiencia_media),
                'tempo_setup': r.tempo_setup,
                'disponivel': 'SIM' if r.disponivel else 'NAO'
            })

        # Criar DataFrame
        df = pd.DataFrame(dados)

        # Criar arquivo Excel em memória
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Recursos de Produção')

            # Ajustar largura das colunas
            worksheet = writer.sheets['Recursos de Produção']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).map(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)

        output.seek(0)

        # Nome do arquivo com data
        filename = f'recursos_producao_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@recursos_bp.route('/template-xlsx')
@login_required
def template_xlsx():
    """Gera template XLSX para importação"""
    try:
        # Template com as colunas esperadas e exemplos
        dados_exemplo = [{
            'cod_produto': 'EXEMPLO001',
            'nome_produto': 'Produto Exemplo',
            'linha_producao': 'LINHA 1',
            'qtd_unidade_por_caixa': 100,
            'capacidade_unidade_minuto': 50.5,
            'qtd_lote_ideal': 1000,
            'qtd_lote_minimo': 500,
            'eficiencia_media': 85.0,
            'tempo_setup': 30,
            'disponivel': 'SIM'
        }]

        df = pd.DataFrame(dados_exemplo)

        # Criar arquivo Excel em memória
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Template')

            worksheet = writer.sheets['Template']

            # Ajustar largura e adicionar comentários
            comentarios = {
                'A1': 'Código do produto (obrigatório)',
                'B1': 'Nome do produto (opcional)',
                'C1': 'Linha de produção (obrigatório)',
                'D1': 'Qtd unidades por caixa (obrigatório - inteiro)',
                'E1': 'Capacidade unidades/minuto (obrigatório)',
                'F1': 'Lote ideal (opcional)',
                'G1': 'Lote mínimo (opcional)',
                'H1': 'Eficiência média em % (padrão: 85)',
                'I1': 'Tempo setup em minutos (padrão: 30)',
                'J1': 'Disponível: SIM ou NAO (padrão: SIM)'
            }

            for col_idx, col in enumerate(df.columns):
                col_letter = chr(65 + col_idx)
                worksheet.column_dimensions[col_letter].width = 25

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='template_recursos_producao.xlsx'
        )

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@recursos_bp.route('/importar-xlsx', methods=['POST'])
@login_required
def importar_xlsx():
    """Importa recursos de produção de arquivo XLSX"""
    try:
        if 'arquivo' not in request.files:
            return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'}), 400

        arquivo = request.files['arquivo']

        if arquivo.filename == '':
            return jsonify({'success': False, 'message': 'Arquivo vazio'}), 400

        if not arquivo.filename.endswith('.xlsx'):
            return jsonify({'success': False, 'message': 'Apenas arquivos .xlsx são permitidos'}), 400

        # Ler Excel
        df = pd.read_excel(arquivo)

        # Validar colunas obrigatórias
        colunas_obrigatorias = ['cod_produto', 'linha_producao', 'qtd_unidade_por_caixa', 'capacidade_unidade_minuto']
        colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]

        if colunas_faltantes:
            return jsonify({
                'success': False,
                'message': f'Colunas obrigatórias faltando: {", ".join(colunas_faltantes)}'
            }), 400

        # Processar dados
        recursos_criados = 0
        recursos_atualizados = 0
        erros = []

        for idx, row in df.iterrows():
            try:
                # Validar campos obrigatórios
                if pd.isna(row['cod_produto']) or pd.isna(row['linha_producao']) or pd.isna(row['qtd_unidade_por_caixa']) or pd.isna(row['capacidade_unidade_minuto']):
                    erros.append(f'Linha {idx + 2}: Campos obrigatórios vazios') # type: ignore
                    continue

                cod_produto = str(row['cod_produto']).strip().upper()
                linha_producao = str(row['linha_producao']).strip()

                # Buscar recurso existente
                recurso = RecursosProducao.query.filter_by(
                    cod_produto=cod_produto,
                    linha_producao=linha_producao
                ).first()

                # Preparar dados
                disponivel_str = str(row.get('disponivel', 'SIM')).strip().upper()
                disponivel = disponivel_str in ['SIM', 'TRUE', '1', 'S']

                if recurso:
                    # Atualizar existente
                    recurso.nome_produto = str(row.get('nome_produto', '')) if not pd.isna(row.get('nome_produto')) else ''
                    recurso.qtd_unidade_por_caixa = int(row['qtd_unidade_por_caixa'])
                    recurso.capacidade_unidade_minuto = Decimal(str(row['capacidade_unidade_minuto']))
                    recurso.qtd_lote_ideal = Decimal(str(row['qtd_lote_ideal'])) if not pd.isna(row.get('qtd_lote_ideal')) else None
                    recurso.qtd_lote_minimo = Decimal(str(row['qtd_lote_minimo'])) if not pd.isna(row.get('qtd_lote_minimo')) else None
                    recurso.eficiencia_media = Decimal(str(row.get('eficiencia_media', 85)))
                    recurso.tempo_setup = int(row.get('tempo_setup', 30))
                    recurso.disponivel = disponivel
                    recursos_atualizados += 1
                else:
                    # Criar novo
                    recurso = RecursosProducao(
                        cod_produto=cod_produto,
                        nome_produto=str(row.get('nome_produto', '')) if not pd.isna(row.get('nome_produto')) else '',
                        linha_producao=linha_producao,
                        qtd_unidade_por_caixa=int(row['qtd_unidade_por_caixa']),
                        capacidade_unidade_minuto=Decimal(str(row['capacidade_unidade_minuto'])),
                        qtd_lote_ideal=Decimal(str(row['qtd_lote_ideal'])) if not pd.isna(row.get('qtd_lote_ideal')) else None,
                        qtd_lote_minimo=Decimal(str(row['qtd_lote_minimo'])) if not pd.isna(row.get('qtd_lote_minimo')) else None,
                        eficiencia_media=Decimal(str(row.get('eficiencia_media', 85))),
                        tempo_setup=int(row.get('tempo_setup', 30)),
                        disponivel=disponivel
                    )
                    db.session.add(recurso)
                    recursos_criados += 1

            except Exception as e:
                erros.append(f'Linha {idx + 2}: {str(e)}') # type: ignore
                continue

        # Commit se houver sucesso
        if recursos_criados > 0 or recursos_atualizados > 0:
            db.session.commit()

        # Preparar resposta
        mensagem = f'Importação concluída! Criados: {recursos_criados}, Atualizados: {recursos_atualizados}'
        if erros:
            mensagem += f'\n\nErros encontrados ({len(erros)}):\n' + '\n'.join(erros[:10])
            if len(erros) > 10:
                mensagem += f'\n... e mais {len(erros) - 10} erros'

        return jsonify({
            'success': True,
            'message': mensagem,
            'criados': recursos_criados,
            'atualizados': recursos_atualizados,
            'erros': len(erros)
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erro ao importar: {str(e)}'}), 500


# ==============================================================
# PROGRAMAÇÃO POR LINHA - NOVA TELA
# ==============================================================

@recursos_bp.route('/programacao-linhas')
@login_required
def programacao_linhas():
    """Tela de Programação por Linha de Produção"""
    return render_template('manufatura/programacao_linhas.html')


@recursos_bp.route('/api/programacao-linhas/dados')
@login_required
def api_programacao_linhas_dados():
    """API para buscar dados de todas as linhas com programações"""
    try:
        from app.producao.models import ProgramacaoProducao
        from app.estoque.models import MovimentacaoEstoque
        from datetime import date, timedelta
        from collections import defaultdict
        from sqlalchemy import func

        # Parâmetros
        mes = request.args.get('mes', type=int)
        ano = request.args.get('ano', type=int)
        com_historico = request.args.get('com_historico', 'false').lower() == 'true'  # ✅ NOVO parâmetro

        if not mes or not ano:
            hoje = date.today()
            mes = hoje.month
            ano = hoje.year

        # Data início e fim do mês
        data_inicio = date(ano, mes, 1)
        if mes == 12:
            data_fim = date(ano + 1, 1, 1) - timedelta(days=1)
        else:
            data_fim = date(ano, mes + 1, 1) - timedelta(days=1)

        # Buscar todas as linhas de produção únicas
        linhas_query = db.session.query(
            RecursosProducao.linha_producao
        ).filter(
            RecursosProducao.disponivel == True
        ).distinct().order_by(RecursosProducao.linha_producao).all()

        linhas_producao = [linha[0] for linha in linhas_query if linha[0]]

        # ✅ NOVO: Buscar dados de produção real se com_historico=True
        producao_por_linha = {}
        if com_historico:
            # Query agrupada: SUM(qtd_movimentacao) por (local_movimentacao, data_movimentacao, cod_produto)
            # ✅ NORMALIZAÇÃO AGRESSIVA: Remove espaços + TRIM + UPPER para garantir match
            producao_query = db.session.query(
                func.replace(func.trim(func.upper(MovimentacaoEstoque.local_movimentacao)), ' ', '').label('linha_normalizada'),
                MovimentacaoEstoque.data_movimentacao,
                MovimentacaoEstoque.cod_produto,
                MovimentacaoEstoque.nome_produto,
                func.sum(MovimentacaoEstoque.qtd_movimentacao).label('qtd_produzida')
            ).filter(
                MovimentacaoEstoque.tipo_movimentacao == 'PRODUÇÃO',
                MovimentacaoEstoque.data_movimentacao >= data_inicio,
                MovimentacaoEstoque.data_movimentacao <= data_fim,
                MovimentacaoEstoque.ativo == True
            ).group_by(
                func.replace(func.trim(func.upper(MovimentacaoEstoque.local_movimentacao)), ' ', ''),
                MovimentacaoEstoque.data_movimentacao,
                MovimentacaoEstoque.cod_produto,
                MovimentacaoEstoque.nome_produto
            ).all()

            # Organizar em dict: {linha: {data: {cod_produto: qtd}}}
            for linha_norm, data_mov, cod_prod, nome_prod, qtd_prod in producao_query:
                if linha_norm not in producao_por_linha:
                    producao_por_linha[linha_norm] = {}

                dia_key = data_mov.strftime('%Y-%m-%d')
                if dia_key not in producao_por_linha[linha_norm]:
                    producao_por_linha[linha_norm][dia_key] = {}  # ✅ CORRIGIDO: Criar dict do dia, não sobrescrever linha

                producao_por_linha[linha_norm][dia_key][cod_prod] = {
                    'qtd_produzida': float(qtd_prod),
                    'nome_produto': nome_prod
                }

        # Para cada linha, buscar seus dados e programações
        resultado = []

        for linha_nome in linhas_producao:
            # Buscar primeiro recurso da linha para pegar dados gerais
            recurso_exemplo = RecursosProducao.query.filter_by(
                linha_producao=linha_nome,
                disponivel=True
            ).first()

            if not recurso_exemplo:
                continue

            # Buscar programações da linha no mês
            programacoes = ProgramacaoProducao.query.filter(
                ProgramacaoProducao.linha_producao == linha_nome,
                ProgramacaoProducao.data_programacao >= data_inicio,
                ProgramacaoProducao.data_programacao <= data_fim
            ).order_by(ProgramacaoProducao.data_programacao).all()

            # ✅ NOVO: Agrupar programações por data E identificar produtos já processados
            prog_por_dia = defaultdict(list)
            produtos_processados = defaultdict(set)  # {dia_key: set(cod_produto)}

            for prog in programacoes:
                dia_key = prog.data_programacao.strftime('%Y-%m-%d')

                # ✅ BUSCAR dados de recursos do produto específico
                recurso_produto = RecursosProducao.query.filter_by(
                    cod_produto=prog.cod_produto,
                    linha_producao=linha_nome,
                    disponivel=True
                ).first()

                # Se não encontrar, usar valores padrão do recurso_exemplo
                capacidade = float(recurso_produto.capacidade_unidade_minuto) if recurso_produto else float(recurso_exemplo.capacidade_unidade_minuto)
                qtd_un_caixa = recurso_produto.qtd_unidade_por_caixa if recurso_produto else recurso_exemplo.qtd_unidade_por_caixa

                # ✅ NOVO: Buscar quantidade produzida se com_historico=True
                qtd_produzida = 0
                linha_normalizada = linha_nome.strip().upper().replace(' ', '')  # ✅ Remove espaços
                if com_historico and linha_normalizada in producao_por_linha:
                    producao_dia = producao_por_linha[linha_normalizada].get(dia_key, {})
                    if prog.cod_produto in producao_dia:
                        qtd_produzida = producao_dia[prog.cod_produto]['qtd_produzida']

                prog_por_dia[dia_key].append({
                    'id': prog.id,  # ✅ Adicionar ID para edição
                    'cod_produto': prog.cod_produto,
                    'nome_produto': prog.nome_produto,
                    'data_programacao': dia_key,  # ✅ Adicionar data para edição
                    'qtd_programada': float(prog.qtd_programada),
                    'qtd_produzida': qtd_produzida,
                    'capacidade_unidade_minuto': capacidade,
                    'qtd_unidade_por_caixa': qtd_un_caixa,
                    'observacao_pcp': prog.observacao_pcp,  # ✅ Adicionar observação
                    'ordem_producao': prog.ordem_producao,  # ✅ Número da OP
                    'cliente_produto': prog.cliente_produto,  # ✅ Adicionar cliente
                    'is_extra_producao': False  # ✅ Flag: não é produção extra
                })

                # Marcar produto+dia como processado
                produtos_processados[dia_key].add(prog.cod_produto)

            # ✅ NOVO: Adicionar itens produzidos que NÃO estavam programados
            if com_historico:
                linha_normalizada = linha_nome.strip().upper().replace(' ', '')  # ✅ Remove espaços
                if linha_normalizada in producao_por_linha:
                    for dia_key, produtos_dia in producao_por_linha[linha_normalizada].items():
                        for cod_produto, dados_prod in produtos_dia.items():
                            # Se produto NÃO estava programado neste dia, adicionar como "extra"
                            if cod_produto not in produtos_processados.get(dia_key, set()):
                                # Buscar dados de recursos do produto
                                recurso_produto = RecursosProducao.query.filter_by(
                                    cod_produto=cod_produto,
                                    linha_producao=linha_nome,
                                    disponivel=True
                                ).first()

                                capacidade = float(recurso_produto.capacidade_unidade_minuto) if recurso_produto else float(recurso_exemplo.capacidade_unidade_minuto)
                                qtd_un_caixa = recurso_produto.qtd_unidade_por_caixa if recurso_produto else recurso_exemplo.qtd_unidade_por_caixa

                                prog_por_dia[dia_key].append({
                                    'id': 0,  # Sem ID pois não tem programação
                                    'cod_produto': cod_produto,
                                    'nome_produto': dados_prod['nome_produto'],
                                    'data_programacao': dia_key,
                                    'qtd_programada': 0,  # ✅ Zero programado
                                    'qtd_produzida': dados_prod['qtd_produzida'],  # ✅ Quantidade produzida
                                    'capacidade_unidade_minuto': capacidade,
                                    'qtd_unidade_por_caixa': qtd_un_caixa,
                                    'observacao_pcp': None,
                                    'ordem_producao': None,  # ✅ Sem OP pois é extra
                                    'cliente_produto': None,
                                    'is_extra_producao': True  # ✅ Flag: é produção extra (não programada)
                                })

            # Montar objeto da linha
            resultado.append({
                'linha_producao': linha_nome,
                'capacidade_unidade_minuto': float(recurso_exemplo.capacidade_unidade_minuto),
                'qtd_unidade_por_caixa': recurso_exemplo.qtd_unidade_por_caixa,
                'qtd_lote_ideal': float(recurso_exemplo.qtd_lote_ideal) if recurso_exemplo.qtd_lote_ideal else 0,
                'eficiencia_media': float(recurso_exemplo.eficiencia_media),
                'tempo_setup': recurso_exemplo.tempo_setup,
                'programacoes': dict(prog_por_dia)
            })

        return jsonify({
            'linhas': resultado,
            'mes': mes,
            'ano': ano
        })

    except Exception as e:
        import logging
        logging.error(f"[PROGRAMACAO LINHAS] Erro: {str(e)}", exc_info=True)
        return jsonify({'erro': str(e)}), 500


@recursos_bp.route('/api/separacoes-estoque')
@login_required
def api_separacoes_estoque():
    """API para buscar separações e estoque projetado de um produto em período"""
    try:
        from app.separacao.models import Separacao
        from app.producao.models import CadastroPalletizacao
        from app.estoque.models import UnificacaoCodigos
        from datetime import datetime, timedelta
        from collections import defaultdict

        # Parâmetros
        cod_produto = request.args.get('cod_produto')
        data_inicio_str = request.args.get('data_inicio')
        data_fim_str = request.args.get('data_fim')
        data_referencia = request.args.get('data_referencia')

        if not all([cod_produto, data_inicio_str, data_fim_str]):
            return jsonify({'erro': 'Parâmetros obrigatórios faltando'}), 400

        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()

        # ✅ UNIFICAÇÃO: Obter todos os códigos relacionados
        codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)

        # Buscar nome do produto
        cadastro = CadastroPalletizacao.query.filter_by(
            cod_produto=cod_produto,
            ativo=True
        ).first()
        nome_produto = cadastro.nome_produto if cadastro else cod_produto

        # ✅ CORRIGIDO: Buscar separações usando códigos relacionados
        separacoes = Separacao.query.filter(
            Separacao.cod_produto.in_(codigos_relacionados),
            Separacao.expedicao >= data_inicio,
            Separacao.expedicao <= data_fim,
            Separacao.sincronizado_nf == False
        ).all()

        # Agrupar saídas por data
        saidas_por_dia = defaultdict(float)
        for sep in separacoes:
            if sep.expedicao:
                dia_key = sep.expedicao.strftime('%Y-%m-%d')
                saidas_por_dia[dia_key] += float(sep.qtd_saldo or 0)

        # ✅ CORRIGIDO: Buscar programações usando códigos relacionados
        from app.producao.models import ProgramacaoProducao
        programacoes = ProgramacaoProducao.query.filter(
            ProgramacaoProducao.cod_produto.in_(codigos_relacionados),
            ProgramacaoProducao.data_programacao >= data_inicio,
            ProgramacaoProducao.data_programacao <= data_fim
        ).all()

        # Agrupar entradas por data
        entradas_por_dia = defaultdict(float)
        for prog in programacoes:
            if prog.data_programacao:
                dia_key = prog.data_programacao.strftime('%Y-%m-%d')
                entradas_por_dia[dia_key] += float(prog.qtd_programada or 0)

        # ✅ BUSCAR ESTOQUE INICIAL (primeiro dia do período)
        from app.estoque.services.estoque_simples import ServicoEstoqueSimples
        estoque_inicial = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)

        # Calcular projeção dia a dia
        dias = []
        estoque_atual = estoque_inicial
        dia_atual = data_inicio

        while dia_atual <= data_fim:
            dia_key = dia_atual.strftime('%Y-%m-%d')
            entradas = entradas_por_dia.get(dia_key, 0)
            saidas = saidas_por_dia.get(dia_key, 0)

            # Estoque final = inicial + entradas - saídas
            estoque_final = estoque_atual + entradas - saidas

            dias.append({
                'data': dia_key,
                'est_inicial': estoque_atual,
                'entradas': entradas,
                'saidas': saidas,
                'est_final': estoque_final
            })

            # Estoque final vira inicial do próximo dia
            estoque_atual = estoque_final
            dia_atual += timedelta(days=1)

        # ✅ BUSCAR PEDIDOS (Separacao com sincronizado_nf=False no período)
        from app.carteira.models import CarteiraPrincipal

        # ✅ CORRIGIDO: Buscar separações detalhadas usando códigos relacionados
        separacoes_detalhadas = Separacao.query.filter(
            Separacao.cod_produto.in_(codigos_relacionados),
            Separacao.expedicao >= data_inicio,
            Separacao.expedicao <= data_fim,
            Separacao.sincronizado_nf == False
        ).order_by(Separacao.expedicao, Separacao.num_pedido).all()

        # ✅ OTIMIZAÇÃO: Buscar TODAS as datas de entrega de UMA VEZ (evitar N+1)
        pedidos_numeros = [sep.num_pedido for sep in separacoes_detalhadas]
        carteira_map = {}
        if pedidos_numeros:
            # ✅ CORRIGIDO: Buscar carteira usando códigos relacionados
            carteira_items = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.num_pedido.in_(pedidos_numeros),
                CarteiraPrincipal.cod_produto.in_(codigos_relacionados)
            ).all()

            # Criar mapa: num_pedido -> data_entrega_pedido
            for item in carteira_items:
                carteira_map[item.num_pedido] = item.data_entrega_pedido

        # Montar lista de pedidos
        pedidos = []
        for sep in separacoes_detalhadas:
            data_entrega = carteira_map.get(sep.num_pedido)

            pedidos.append({
                'separacao_lote_id': sep.separacao_lote_id,  # ✅ NOVO: Para abrir modal de detalhes
                'num_pedido': sep.num_pedido,
                'cnpj_cpf': sep.cnpj_cpf,
                'raz_social_red': sep.raz_social_red,
                'qtd': float(sep.qtd_saldo or 0),
                'expedicao': sep.expedicao.strftime('%Y-%m-%d') if sep.expedicao else None,
                'agendamento': sep.agendamento.strftime('%Y-%m-%d') if sep.agendamento else None,
                'agendamento_confirmado': sep.agendamento_confirmado or False,
                'data_entrega_pedido': data_entrega.strftime('%Y-%m-%d') if data_entrega else None
            })

        # ✅ NOVO: Buscar programação de produção D0-D60 agrupada por linha
        from app.manufatura.models import RecursosProducao
        from datetime import date as date_cls

        hoje = date_cls.today()
        data_fim_d60 = hoje + timedelta(days=60)

        # ✅ CORRIGIDO: Buscar recursos considerando códigos relacionados
        # Como RecursosProducao pode ter registros para cada código, buscar por todos
        recursos = RecursosProducao.query.filter(
            RecursosProducao.cod_produto.in_(codigos_relacionados),
            RecursosProducao.disponivel == True
        ).all()

        # Buscar programações de TODOS os produtos nas linhas onde este produto pode ser produzido
        linhas_producao = [r.linha_producao for r in recursos]
        programacoes_linhas = {}

        if linhas_producao:
            # Buscar programações de hoje até D60 para as linhas
            programacoes = ProgramacaoProducao.query.filter(
                ProgramacaoProducao.linha_producao.in_(linhas_producao),
                ProgramacaoProducao.data_programacao >= hoje,
                ProgramacaoProducao.data_programacao <= data_fim_d60
            ).order_by(ProgramacaoProducao.linha_producao, ProgramacaoProducao.data_programacao).all()

            # Agrupar por linha e data
            for prog in programacoes:
                if prog.linha_producao not in programacoes_linhas:
                    programacoes_linhas[prog.linha_producao] = {
                        'total_programado': 0,
                        'datas': defaultdict(list)  # data -> [lista de programações]
                    }

                data_key = prog.data_programacao.strftime('%Y-%m-%d')
                programacoes_linhas[prog.linha_producao]['datas'][data_key].append({
                    'id': prog.id,  # ✅ NOVO: ID para edição/exclusão
                    'data_programacao': data_key,  # ✅ NOVO: Data para edição
                    'cod_produto': prog.cod_produto,
                    'nome_produto': prog.nome_produto,
                    'qtd_programada': float(prog.qtd_programada),
                    'cliente_produto': prog.cliente_produto,
                    'observacao_pcp': prog.observacao_pcp,
                    'eh_produto_modal': prog.cod_produto in codigos_relacionados  # ✅ CORRIGIDO: Usar códigos relacionados
                })

                # ✅ CORRIGIDO: Somar total programado para TODOS os códigos relacionados
                if prog.cod_produto in codigos_relacionados:
                    programacoes_linhas[prog.linha_producao]['total_programado'] += float(prog.qtd_programada)

            # Converter defaultdict para dict normal
            for linha in programacoes_linhas:
                programacoes_linhas[linha]['datas'] = dict(programacoes_linhas[linha]['datas'])

        return jsonify({
            'nome_produto': nome_produto,
            'cod_produto': cod_produto,
            'data_referencia': data_referencia,
            'dias': dias,
            'pedidos': pedidos,
            'programacoes_linhas': programacoes_linhas,  # ✅ NOVO
            'linhas_producao': [{'linha': r.linha_producao, 'qtd_unidade_por_caixa': r.qtd_unidade_por_caixa} for r in recursos]  # ✅ NOVO
        })

    except Exception as e:
        import logging
        logging.error(f"[SEPARACOES ESTOQUE] Erro: {str(e)}", exc_info=True)
        return jsonify({'erro': str(e)}), 500


# ============================================================
# ROTAS DE EDIÇÃO DE PROGRAMAÇÃO DE PRODUÇÃO
# ============================================================

@recursos_bp.route('/api/programacao/<int:id>', methods=['PUT'])
@login_required
def api_atualizar_programacao(id):
    """API para atualizar programação de produção"""
    try:
        from app.producao.models import ProgramacaoProducao
        from datetime import datetime

        programacao = ProgramacaoProducao.query.get_or_404(id)
        data = request.get_json()

        # Atualizar campos se fornecidos
        if 'data_programacao' in data and data['data_programacao']:
            programacao.data_programacao = datetime.strptime(data['data_programacao'], '%Y-%m-%d').date()

        if 'qtd_programada' in data and data['qtd_programada'] is not None:
            programacao.qtd_programada = float(data['qtd_programada'])

        if 'observacao_pcp' in data:
            programacao.observacao_pcp = data['observacao_pcp'].strip() if data['observacao_pcp'] else None

        if 'ordem_producao' in data:
            programacao.ordem_producao = data['ordem_producao'].strip() if data['ordem_producao'] else None

        # Auditoria
        programacao.updated_by = current_user.email if hasattr(current_user, 'email') else 'sistema'

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': 'Programação atualizada com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f"[PROGRAMACAO PUT] Erro: {str(e)}", exc_info=True)
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@recursos_bp.route('/api/programacao/<int:id>', methods=['DELETE'])
@login_required
def api_excluir_programacao(id):
    """API para excluir programação de produção"""
    try:
        from app.producao.models import ProgramacaoProducao

        programacao = ProgramacaoProducao.query.get_or_404(id)

        db.session.delete(programacao)
        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': 'Programação excluída com sucesso!'
        })

    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f"[PROGRAMACAO DELETE] Erro: {str(e)}", exc_info=True)
        return jsonify({'sucesso': False, 'erro': str(e)}), 500
