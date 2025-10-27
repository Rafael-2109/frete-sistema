"""
Rotas para CRUD de Recursos de Produção
Gerencia capacidades produtivas, linhas de produção e eficiências
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file
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
                    erros.append(f'Linha {idx + 2}: Campos obrigatórios vazios')
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
                erros.append(f'Linha {idx + 2}: {str(e)}')
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
