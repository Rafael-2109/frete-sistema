"""
Rotas para leitura e processamento de PDFs de pedidos de redes de atacarejo

Fluxo:
1. Upload PDF → Armazena no S3
2. Identificador → Detecta Rede + Tipo
3. Extrator específico → Extrai dados
4. Conversão De-Para → Código Nacom
5. Validação de preços → vs TabelaRede
6. Revisão/Aprovação → Interface
7. Inserção Odoo → sale.order via XML-RPC
"""

from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import tempfile
from datetime import datetime
from decimal import Decimal

from .processor import PedidoProcessor
from app.utils.file_storage import get_file_storage
from app.portal.atacadao.models import ProdutoDeParaAtacadao
from app.pedidos.validacao import ValidadorPrecos, validar_precos_documento
from app.pedidos.integracao_odoo import get_odoo_service, RegistroPedidoOdoo
from app import db

bp = Blueprint('leitura_pedidos', __name__, url_prefix='/pedidos/leitura')

ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def serialize_data(data):
    """Converte Decimal e outros tipos para JSON serializável"""
    if isinstance(data, list):
        return [serialize_data(item) for item in data]
    elif isinstance(data, dict):
        return {k: serialize_data(v) for k, v in data.items()}
    elif isinstance(data, Decimal):
        return float(data)
    elif hasattr(data, 'isoformat'):  # datetime, date
        return data.isoformat()
    return data


@bp.route('/')
@login_required
def index():
    """Página principal da leitura de pedidos"""
    return render_template('pedidos/leitura/index.html')


@bp.route('/upload', methods=['POST'])
@login_required
def upload():
    """
    Upload e processamento de PDF

    Retorna:
    - Identificação do documento (rede, tipo, número)
    - Dados extraídos
    - Validação de preços
    - Lista de itens sem De-Para
    """
    try:
        # Verifica se arquivo foi enviado
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Tipo de arquivo não permitido. Use PDF'}), 400

        # Salva arquivo temporário para processamento
        filename = secure_filename(file.filename)
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"pedido_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}")
        file.save(temp_path)

        try:
            # Processa arquivo
            processor = PedidoProcessor()
            formato = request.form.get('formato', 'auto')

            result = processor.process_file(
                temp_path,
                formato=formato,
                validate=True
            )

            if not result['success']:
                os.remove(temp_path)
                return jsonify({
                    'success': False,
                    'errors': result.get('errors', ['Erro ao processar arquivo'])
                }), 400

            # Salva PDF no S3
            file.seek(0)  # Volta ao início do arquivo
            storage = get_file_storage()
            s3_path = storage.save_file(
                file,
                folder='pedidos_redes',
                filename=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}",
                allowed_extensions=['pdf']
            )

            # Remove arquivo temporário
            os.remove(temp_path)

            # Serializa dados
            data_serializable = serialize_data(result['data'])
            summary = serialize_data(result.get('summary', {}))
            identificacao = result.get('identificacao', {})

            # Extrai informações importantes
            rede = identificacao.get('rede', 'DESCONHECIDA')
            tipo_doc = identificacao.get('tipo', 'DESCONHECIDO')
            numero_doc = identificacao.get('numero_documento', '')

            # Valida preços contra TabelaRede
            validacao_precos = None
            tem_divergencia = False

            if summary.get('por_filial'):
                validador = ValidadorPrecos(tolerancia_percentual=0.0)
                validacoes_filiais = []

                for filial in summary['por_filial']:
                    uf = filial.get('estado', '')
                    produtos = filial.get('produtos', [])

                    if uf and produtos:
                        resultado_val = validador.validar(
                            rede=rede,
                            uf=uf,
                            itens=produtos
                        )

                        if resultado_val.tem_divergencia:
                            tem_divergencia = True

                        validacoes_filiais.append({
                            'cnpj': filial.get('cnpj'),
                            'uf': uf,
                            'regiao': resultado_val.regiao,
                            'itens_validados': resultado_val.itens_validados,
                            'itens_divergentes': resultado_val.itens_divergentes,
                            'itens_sem_tabela': resultado_val.itens_sem_tabela,
                            'tem_divergencia': resultado_val.tem_divergencia,
                            'valor_documento': resultado_val.valor_total_documento,
                            'valor_tabela': resultado_val.valor_total_tabela,
                            'validacoes': [
                                {
                                    'codigo': v.codigo,
                                    'preco_documento': v.preco_documento,
                                    'preco_tabela': v.preco_tabela,
                                    'divergente': v.divergente,
                                    'diferenca': v.diferenca,
                                    'diferenca_percentual': v.diferenca_percentual,
                                    'mensagem': v.mensagem
                                }
                                for v in resultado_val.validacoes
                            ]
                        })

                validacao_precos = {
                    'tem_divergencia': tem_divergencia,
                    'por_filial': validacoes_filiais
                }

            # Identifica itens sem De-Para
            itens_sem_depara = []
            for filial in summary.get('por_filial', []):
                for produto in filial.get('produtos', []):
                    if not produto.get('nosso_codigo'):
                        itens_sem_depara.append({
                            'cnpj_filial': filial.get('cnpj'),
                            'codigo_rede': produto.get('codigo'),
                            'descricao': produto.get('descricao'),
                            'quantidade': produto.get('quantidade'),
                            'valor_unitario': produto.get('valor_unitario')
                        })

            # Gera chave de sessão para armazenar dados
            session_key = f"pedido_data_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            session[session_key] = {
                'data': data_serializable,
                'summary': summary,
                'identificacao': identificacao,
                'validacao_precos': validacao_precos,
                'itens_sem_depara': itens_sem_depara,
                's3_path': s3_path,
                'filename': filename,
                'timestamp': datetime.now().isoformat(),
                'usuario': current_user.username if hasattr(current_user, 'username') else str(current_user.id)
            }

            # Determina se pode inserir no Odoo
            pode_inserir = len(itens_sem_depara) == 0

            response_data = {
                'success': True,
                'session_key': session_key,
                'identificacao': identificacao,
                'summary': summary,
                'data': data_serializable,
                'validacao_precos': validacao_precos,
                'tem_divergencia': tem_divergencia,
                'itens_sem_depara': itens_sem_depara,
                'pode_inserir': pode_inserir,
                's3_path': s3_path,
                'warnings': result.get('warnings', []),
                'errors': result.get('errors', [])
            }

            return jsonify(response_data)

        except Exception as e:
            # Remove arquivo temporário em caso de erro
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': f'Erro ao processar arquivo: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/criar-depara', methods=['POST'])
@login_required
def criar_depara():
    """
    Cria um novo registro De-Para para produto

    Body JSON:
    - codigo_rede: Código do produto na rede
    - codigo_nosso: Nosso código interno
    - descricao_rede: Descrição do produto na rede
    - descricao_nosso: Nossa descrição (opcional)
    - rede: Nome da rede (ATACADAO, TENDA, ASSAI)
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400

        codigo_rede = data.get('codigo_rede')
        codigo_nosso = data.get('codigo_nosso')
        rede = data.get('rede', 'ATACADAO').upper()

        if not codigo_rede or not codigo_nosso:
            return jsonify({'success': False, 'error': 'Código da rede e nosso código são obrigatórios'}), 400

        # Por enquanto, suporta apenas Atacadão
        if rede != 'ATACADAO':
            return jsonify({'success': False, 'error': f'Rede {rede} não suportada para De-Para'}), 400

        # Verifica se já existe
        existente = ProdutoDeParaAtacadao.query.filter_by(
            codigo_atacadao=codigo_rede,
            codigo_nosso=codigo_nosso,
            ativo=True
        ).first()

        if existente:
            return jsonify({
                'success': True,
                'message': 'De-Para já existe',
                'depara': {
                    'id': existente.id,
                    'codigo_rede': existente.codigo_atacadao,
                    'codigo_nosso': existente.codigo_nosso
                }
            })

        # Cria novo De-Para
        novo_depara = ProdutoDeParaAtacadao(
            codigo_atacadao=codigo_rede,
            codigo_nosso=codigo_nosso,
            descricao_atacadao=data.get('descricao_rede'),
            descricao_nosso=data.get('descricao_nosso'),
            criado_por=current_user.username if hasattr(current_user, 'username') else str(current_user.id),
            ativo=True
        )

        db.session.add(novo_depara)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'De-Para criado com sucesso',
            'depara': {
                'id': novo_depara.id,
                'codigo_rede': novo_depara.codigo_atacadao,
                'codigo_nosso': novo_depara.codigo_nosso
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/validar-produto-odoo', methods=['POST'])
@login_required
def validar_produto_odoo():
    """
    Valida se um código de produto existe no Odoo

    Body JSON:
    - codigo: Código do produto a validar
    """
    try:
        data = request.get_json()
        codigo = data.get('codigo')

        if not codigo:
            return jsonify({'success': False, 'error': 'Código não fornecido'}), 400

        service = get_odoo_service()
        product_id = service.buscar_produto_por_codigo(codigo)

        return jsonify({
            'success': True,
            'existe': product_id is not None,
            'product_id': product_id
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/inserir-odoo', methods=['POST'])
@login_required
def inserir_odoo():
    """
    Insere pedido(s) no Odoo

    Body JSON:
    - session_key: Chave da sessão com os dados processados
    - cnpj_filial: CNPJ específico para inserir (opcional, se não informado insere todos)
    - justificativa: Justificativa global (usado se não houver justificativa por filial)
    - justificativas_por_filial: Dict {cnpj: justificativa} para justificativas individuais
    """
    try:
        data = request.get_json()
        session_key = data.get('session_key')
        cnpj_filial = data.get('cnpj_filial')
        justificativa_global = data.get('justificativa', '')
        justificativas_por_filial = data.get('justificativas_por_filial', {})

        if not session_key or session_key not in session:
            return jsonify({'success': False, 'error': 'Sessão inválida ou expirada'}), 400

        pedido_data = session[session_key]
        summary = pedido_data.get('summary', {})
        identificacao = pedido_data.get('identificacao', {})
        validacao_precos = pedido_data.get('validacao_precos', {})
        itens_sem_depara = pedido_data.get('itens_sem_depara', [])

        rede = identificacao.get('rede', 'DESCONHECIDA')
        tipo_doc = identificacao.get('tipo', 'DESCONHECIDO')
        numero_doc = identificacao.get('numero_documento', '')
        s3_path = pedido_data.get('s3_path', '')
        usuario = pedido_data.get('usuario', str(current_user.id))

        # Obtém service do Odoo
        service = get_odoo_service()

        resultados = []
        filiais_para_inserir = summary.get('por_filial', [])

        # Filtra por CNPJ específico se informado
        if cnpj_filial:
            filiais_para_inserir = [f for f in filiais_para_inserir if f.get('cnpj') == cnpj_filial]

            # Verifica se há itens sem De-Para apenas para esta filial
            itens_sem_depara_filial = [i for i in itens_sem_depara if i.get('cnpj_filial') == cnpj_filial]
            if itens_sem_depara_filial:
                return jsonify({
                    'success': False,
                    'error': 'Esta filial possui itens sem De-Para. Complete o cadastro antes de inserir.',
                    'itens_sem_depara': itens_sem_depara_filial
                }), 400
        else:
            # Verifica se há itens sem De-Para (inserção global)
            if itens_sem_depara:
                return jsonify({
                    'success': False,
                    'error': 'Existem itens sem De-Para. Complete o cadastro antes de inserir.',
                    'itens_sem_depara': itens_sem_depara
                }), 400

        for filial in filiais_para_inserir:
            cnpj = filial.get('cnpj')
            produtos = filial.get('produtos', [])
            uf = filial.get('estado', '')
            nome_cliente = filial.get('nome_cliente', '')

            # Verifica divergência desta filial específica
            tem_divergencia_filial = False
            divergencias_filial = None
            if validacao_precos and validacao_precos.get('por_filial'):
                for val_filial in validacao_precos['por_filial']:
                    if val_filial.get('cnpj') == cnpj:
                        tem_divergencia_filial = val_filial.get('tem_divergencia', False)
                        if tem_divergencia_filial:
                            divergencias_filial = val_filial.get('validacoes', [])
                        break

            # Obtém justificativa (individual ou global)
            justificativa = justificativas_por_filial.get(cnpj, justificativa_global)

            # Verifica se precisa de justificativa para esta filial
            if tem_divergencia_filial and not justificativa:
                resultados.append({
                    'cnpj': cnpj,
                    'nome_cliente': nome_cliente,
                    'sucesso': False,
                    'order_id': None,
                    'order_name': None,
                    'mensagem': 'Justificativa obrigatória para filial com divergência de preços',
                    'erros': ['Informe uma justificativa'],
                    'registro_id': None
                })
                continue

            # Prepara itens para o Odoo (usando nosso_codigo)
            itens_odoo = []
            for produto in produtos:
                if produto.get('nosso_codigo'):
                    itens_odoo.append({
                        'nosso_codigo': produto.get('nosso_codigo'),
                        'quantidade': produto.get('quantidade', 0),
                        'preco': produto.get('valor_unitario', 0),
                        'uf': uf,
                        'nome_cliente': nome_cliente
                    })

            if not itens_odoo:
                resultados.append({
                    'cnpj': cnpj,
                    'nome_cliente': nome_cliente,
                    'sucesso': False,
                    'order_id': None,
                    'order_name': None,
                    'mensagem': 'Nenhum item válido para inserir',
                    'erros': [],
                    'registro_id': None
                })
                continue

            # Cria pedido no Odoo e registra
            resultado, registro = service.criar_pedido_e_registrar(
                cnpj_cliente=cnpj,
                itens=itens_odoo,
                rede=rede,
                tipo_documento=tipo_doc,
                numero_documento=numero_doc,
                arquivo_pdf_s3=s3_path,
                usuario=usuario,
                divergente=tem_divergencia_filial,
                divergencias=divergencias_filial,
                justificativa=justificativa if tem_divergencia_filial else None,
                aprovador=usuario if tem_divergencia_filial else None
            )

            resultados.append({
                'cnpj': cnpj,
                'nome_cliente': nome_cliente,
                'sucesso': resultado.sucesso,
                'order_id': resultado.order_id,
                'order_name': resultado.order_name,
                'mensagem': resultado.mensagem,
                'erros': resultado.erros,
                'registro_id': registro.id if registro else None
            })

        # Verifica sucesso geral
        todos_sucesso = all(r.get('sucesso') for r in resultados) if resultados else False
        algum_sucesso = any(r.get('sucesso') for r in resultados) if resultados else False

        return jsonify({
            'success': algum_sucesso,
            'todos_sucesso': todos_sucesso,
            'resultados': resultados,
            'message': 'Pedido(s) inserido(s) no Odoo' if todos_sucesso else 'Alguns pedidos falharam'
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/reprocessar', methods=['POST'])
@login_required
def reprocessar():
    """
    Reprocessa os dados da sessão após criar De-Para
    Atualiza os itens com os novos códigos convertidos
    """
    try:
        data = request.get_json()
        session_key = data.get('session_key')

        if not session_key or session_key not in session:
            return jsonify({'success': False, 'error': 'Sessão inválida ou expirada'}), 400

        pedido_data = session[session_key]
        summary = pedido_data.get('summary', {})
        identificacao = pedido_data.get('identificacao', {})
        rede = identificacao.get('rede', 'ATACADAO')

        # Reprocessa cada filial para atualizar De-Para
        itens_sem_depara = []

        for filial in summary.get('por_filial', []):
            for produto in filial.get('produtos', []):
                codigo_rede = produto.get('codigo')

                # Tenta buscar De-Para novamente
                if not produto.get('nosso_codigo') and codigo_rede:
                    if rede == 'ATACADAO':
                        nosso_codigo = ProdutoDeParaAtacadao.obter_nosso_codigo(codigo_rede)
                        if nosso_codigo:
                            produto['nosso_codigo'] = nosso_codigo

                # Verifica se ainda está sem De-Para
                if not produto.get('nosso_codigo'):
                    itens_sem_depara.append({
                        'cnpj_filial': filial.get('cnpj'),
                        'codigo_rede': codigo_rede,
                        'descricao': produto.get('descricao'),
                        'quantidade': produto.get('quantidade'),
                        'valor_unitario': produto.get('valor_unitario')
                    })

        # Atualiza sessão
        pedido_data['itens_sem_depara'] = itens_sem_depara
        pedido_data['summary'] = summary
        session[session_key] = pedido_data

        pode_inserir = len(itens_sem_depara) == 0

        return jsonify({
            'success': True,
            'summary': summary,
            'itens_sem_depara': itens_sem_depara,
            'pode_inserir': pode_inserir
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/historico')
@login_required
def historico():
    """Lista histórico de pedidos inseridos no Odoo"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        registros = RegistroPedidoOdoo.query.order_by(
            RegistroPedidoOdoo.criado_em.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        return render_template(
            'pedidos/leitura/historico.html',
            registros=registros
        )

    except Exception as e:
        flash(f'Erro ao carregar histórico: {str(e)}', 'danger')
        return redirect(url_for('leitura_pedidos.index'))


@bp.route('/export/<format>/<session_key>')
@login_required
def export(format, session_key):
    """Exporta dados processados para Excel ou CSV"""
    try:
        # Recupera dados da sessão
        if session_key not in session:
            flash('Dados não encontrados. Por favor, processe o arquivo novamente.', 'warning')
            return redirect(url_for('leitura_pedidos.index'))

        pedido_data = session[session_key]
        data = pedido_data['data']
        original_filename = pedido_data['filename'].rsplit('.', 1)[0]

        if not data:
            flash('Sem dados para exportar', 'warning')
            return redirect(url_for('leitura_pedidos.index'))

        # Cria arquivo temporário para export
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        processor = PedidoProcessor()

        if format == 'excel':
            output_path = os.path.join(temp_dir, f"{original_filename}_processado_{timestamp}.xlsx")
            processor.export_to_excel(data, output_path)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif format == 'csv':
            output_path = os.path.join(temp_dir, f"{original_filename}_processado_{timestamp}.csv")
            processor.export_to_csv(data, output_path)
            mimetype = 'text/csv'
        else:
            flash('Formato de exportação inválido', 'danger')
            return redirect(url_for('leitura_pedidos.index'))

        # Envia arquivo para download
        return send_file(
            output_path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=os.path.basename(output_path)
        )

    except Exception as e:
        flash(f'Erro ao exportar dados: {str(e)}', 'danger')
        return redirect(url_for('leitura_pedidos.index'))


# ============================================================================
# CRUD - Tabela de Preços por Rede/Região
# ============================================================================

from app.pedidos.validacao.models import TabelaRede, RegiaoTabelaRede


@bp.route('/tabela-precos')
@login_required
def tabela_precos():
    """Lista tabela de preços por rede"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    rede_filtro = request.args.get('rede', '')
    regiao_filtro = request.args.get('regiao', '')
    produto_filtro = request.args.get('produto', '')

    query = TabelaRede.query

    if rede_filtro:
        query = query.filter(TabelaRede.rede == rede_filtro.upper())
    if regiao_filtro:
        query = query.filter(TabelaRede.regiao == regiao_filtro.upper())
    if produto_filtro:
        query = query.filter(TabelaRede.cod_produto.ilike(f'%{produto_filtro}%'))

    registros = query.order_by(
        TabelaRede.rede,
        TabelaRede.regiao,
        TabelaRede.cod_produto
    ).paginate(page=page, per_page=per_page, error_out=False)

    # Lista de redes e regiões para filtros
    redes = db.session.query(TabelaRede.rede).distinct().all()
    regioes = db.session.query(TabelaRede.regiao).distinct().all()

    return render_template(
        'pedidos/leitura/tabela_precos.html',
        registros=registros,
        redes=[r[0] for r in redes],
        regioes=[r[0] for r in regioes],
        rede_filtro=rede_filtro,
        regiao_filtro=regiao_filtro,
        produto_filtro=produto_filtro
    )


@bp.route('/tabela-precos/criar', methods=['GET', 'POST'])
@login_required
def tabela_precos_criar():
    """Cria novo registro de preço"""
    if request.method == 'POST':
        try:
            rede = request.form.get('rede', '').upper()
            regiao = request.form.get('regiao', '').upper()
            cod_produto = request.form.get('cod_produto', '').strip()
            preco = request.form.get('preco', '0').replace(',', '.')

            if not all([rede, regiao, cod_produto, preco]):
                flash('Todos os campos são obrigatórios', 'danger')
                return redirect(url_for('leitura_pedidos.tabela_precos_criar'))

            # Verifica se já existe
            existente = TabelaRede.query.filter_by(
                rede=rede, regiao=regiao, cod_produto=cod_produto
            ).first()

            if existente:
                flash('Já existe um registro para esta combinação Rede/Região/Produto', 'warning')
                return redirect(url_for('leitura_pedidos.tabela_precos_criar'))

            registro = TabelaRede(
                rede=rede,
                regiao=regiao,
                cod_produto=cod_produto,
                preco=float(preco),
                criado_por=current_user.username if hasattr(current_user, 'username') else str(current_user.id),
                ativo=True
            )
            db.session.add(registro)
            db.session.commit()

            flash(f'Preço cadastrado com sucesso: {rede}/{regiao}/{cod_produto} = R$ {preco}', 'success')
            return redirect(url_for('leitura_pedidos.tabela_precos'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar: {str(e)}', 'danger')

    # Lista de regiões existentes para sugestão
    regioes = db.session.query(RegiaoTabelaRede.regiao).distinct().all()

    return render_template(
        'pedidos/leitura/tabela_precos_form.html',
        registro=None,
        regioes_existentes=[r[0] for r in regioes]
    )


@bp.route('/tabela-precos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def tabela_precos_editar(id):
    """Edita registro de preço"""
    registro = TabelaRede.query.get_or_404(id)

    if request.method == 'POST':
        try:
            registro.rede = request.form.get('rede', '').upper()
            registro.regiao = request.form.get('regiao', '').upper()
            registro.cod_produto = request.form.get('cod_produto', '').strip()
            registro.preco = float(request.form.get('preco', '0').replace(',', '.'))
            registro.ativo = request.form.get('ativo') == 'on'
            registro.atualizado_por = current_user.username if hasattr(current_user, 'username') else str(current_user.id)

            db.session.commit()
            flash('Registro atualizado com sucesso', 'success')
            return redirect(url_for('leitura_pedidos.tabela_precos'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar: {str(e)}', 'danger')

    regioes = db.session.query(RegiaoTabelaRede.regiao).distinct().all()

    return render_template(
        'pedidos/leitura/tabela_precos_form.html',
        registro=registro,
        regioes_existentes=[r[0] for r in regioes]
    )


@bp.route('/tabela-precos/excluir/<int:id>', methods=['POST'])
@login_required
def tabela_precos_excluir(id):
    """Exclui registro de preço"""
    try:
        registro = TabelaRede.query.get_or_404(id)
        db.session.delete(registro)
        db.session.commit()
        flash('Registro excluído com sucesso', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {str(e)}', 'danger')

    return redirect(url_for('leitura_pedidos.tabela_precos'))


@bp.route('/tabela-precos/importar', methods=['POST'])
@login_required
def tabela_precos_importar():
    """
    Importa preços de arquivo Excel (XLSX)

    Formato esperado (colunas):
    rede | regiao | cod_produto | preco
    ATACADAO | SUDESTE | 35642 | 199.48
    """
    import pandas as pd

    if 'file' not in request.files:
        flash('Nenhum arquivo enviado', 'danger')
        return redirect(url_for('leitura_pedidos.tabela_precos'))

    file = request.files['file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('leitura_pedidos.tabela_precos'))

    if not file.filename.endswith(('.xlsx', '.xls')):
        flash('Arquivo deve ser Excel (.xlsx ou .xls)', 'danger')
        return redirect(url_for('leitura_pedidos.tabela_precos'))

    try:
        # Lê o arquivo Excel
        df = pd.read_excel(file, engine='openpyxl')

        # Normaliza nomes das colunas (remove espaços, lowercase)
        df.columns = [col.strip().lower() for col in df.columns]

        criados = 0
        atualizados = 0
        erros = []

        for idx, row in df.iterrows():
            try:
                rede = str(row.get('rede', '')).upper().strip()
                regiao = str(row.get('regiao', '')).upper().strip()
                cod_produto = str(row.get('cod_produto', '')).strip()

                # Trata o preço
                preco_raw = row.get('preco', 0)
                if pd.isna(preco_raw):
                    preco = 0.0
                elif isinstance(preco_raw, str):
                    preco = float(preco_raw.replace(',', '.'))
                else:
                    preco = float(preco_raw)

                if not all([rede, regiao, cod_produto]) or rede == 'NAN':
                    continue

                existente = TabelaRede.query.filter_by(
                    rede=rede, regiao=regiao, cod_produto=cod_produto
                ).first()

                if existente:
                    existente.preco = preco
                    existente.atualizado_por = current_user.username if hasattr(current_user, 'username') else str(current_user.id)
                    atualizados += 1
                else:
                    novo = TabelaRede(
                        rede=rede,
                        regiao=regiao,
                        cod_produto=cod_produto,
                        preco=preco,
                        criado_por=current_user.username if hasattr(current_user, 'username') else str(current_user.id),
                        ativo=True
                    )
                    db.session.add(novo)
                    criados += 1

            except Exception as e:
                erros.append(f"Erro na linha {idx + 2}: {str(e)}")

        db.session.commit()
        flash(f'Importação concluída: {criados} criados, {atualizados} atualizados', 'success')

        if erros:
            flash(f'Erros: {len(erros)} linhas com problema', 'warning')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao importar: {str(e)}', 'danger')

    return redirect(url_for('leitura_pedidos.tabela_precos'))


# ============================================================================
# CRUD - Regiões por UF
# ============================================================================

@bp.route('/regioes')
@login_required
def regioes():
    """Lista mapeamento UF → Região por rede"""
    page = request.args.get('page', 1, type=int)
    rede_filtro = request.args.get('rede', '')

    query = RegiaoTabelaRede.query

    if rede_filtro:
        query = query.filter(RegiaoTabelaRede.rede == rede_filtro.upper())

    registros = query.order_by(
        RegiaoTabelaRede.rede,
        RegiaoTabelaRede.uf
    ).paginate(page=page, per_page=100, error_out=False)

    # Lista de redes para filtro
    redes = db.session.query(RegiaoTabelaRede.rede).distinct().all()

    return render_template(
        'pedidos/leitura/regioes.html',
        registros=registros,
        redes=[r[0] for r in redes],
        rede_filtro=rede_filtro
    )


@bp.route('/regioes/criar', methods=['GET', 'POST'])
@login_required
def regioes_criar():
    """Cria novo mapeamento UF → Região"""
    if request.method == 'POST':
        try:
            rede = request.form.get('rede', '').upper()
            uf = request.form.get('uf', '').upper()
            regiao = request.form.get('regiao', '').upper()

            if not all([rede, uf, regiao]):
                flash('Todos os campos são obrigatórios', 'danger')
                return redirect(url_for('leitura_pedidos.regioes_criar'))

            # Verifica se já existe
            existente = RegiaoTabelaRede.query.filter_by(rede=rede, uf=uf).first()
            if existente:
                flash('Já existe um mapeamento para esta Rede/UF', 'warning')
                return redirect(url_for('leitura_pedidos.regioes_criar'))

            registro = RegiaoTabelaRede(
                rede=rede,
                uf=uf,
                regiao=regiao,
                criado_por=current_user.username if hasattr(current_user, 'username') else str(current_user.id),
                ativo=True
            )
            db.session.add(registro)
            db.session.commit()

            flash(f'Mapeamento criado: {rede}/{uf} → {regiao}', 'success')
            return redirect(url_for('leitura_pedidos.regioes'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar: {str(e)}', 'danger')

    return render_template('pedidos/leitura/regioes_form.html', registro=None)


@bp.route('/regioes/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def regioes_editar(id):
    """Edita mapeamento UF → Região"""
    registro = RegiaoTabelaRede.query.get_or_404(id)

    if request.method == 'POST':
        try:
            registro.rede = request.form.get('rede', '').upper()
            registro.uf = request.form.get('uf', '').upper()
            registro.regiao = request.form.get('regiao', '').upper()
            registro.ativo = request.form.get('ativo') == 'on'

            db.session.commit()
            flash('Mapeamento atualizado com sucesso', 'success')
            return redirect(url_for('leitura_pedidos.regioes'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar: {str(e)}', 'danger')

    return render_template('pedidos/leitura/regioes_form.html', registro=registro)


@bp.route('/regioes/excluir/<int:id>', methods=['POST'])
@login_required
def regioes_excluir(id):
    """Exclui mapeamento UF → Região"""
    try:
        registro = RegiaoTabelaRede.query.get_or_404(id)
        db.session.delete(registro)
        db.session.commit()
        flash('Mapeamento excluído com sucesso', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir: {str(e)}', 'danger')

    return redirect(url_for('leitura_pedidos.regioes'))


@bp.route('/regioes/importar', methods=['POST'])
@login_required
def regioes_importar():
    """
    Importa mapeamento UF → Região de arquivo Excel (XLSX)

    Formato esperado (colunas):
    rede | uf | regiao
    ATACADAO | SP | SAO PAULO
    ATACADAO | RJ | SUDESTE/SUL
    """
    import pandas as pd

    if 'file' not in request.files:
        flash('Nenhum arquivo enviado', 'danger')
        return redirect(url_for('leitura_pedidos.regioes'))

    file = request.files['file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('leitura_pedidos.regioes'))

    if not file.filename.endswith(('.xlsx', '.xls')):
        flash('Arquivo deve ser Excel (.xlsx ou .xls)', 'danger')
        return redirect(url_for('leitura_pedidos.regioes'))

    try:
        # Lê o arquivo Excel
        df = pd.read_excel(file, engine='openpyxl')

        # Normaliza nomes das colunas (remove espaços, lowercase)
        df.columns = [col.strip().lower() for col in df.columns]

        criados = 0
        atualizados = 0
        erros = []

        for idx, row in df.iterrows():
            try:
                rede = str(row.get('rede', '')).upper().strip()
                uf = str(row.get('uf', '')).upper().strip()
                regiao = str(row.get('regiao', '')).upper().strip()

                if not all([rede, uf, regiao]) or rede == 'NAN':
                    continue

                existente = RegiaoTabelaRede.query.filter_by(rede=rede, uf=uf).first()

                if existente:
                    existente.regiao = regiao
                    atualizados += 1
                else:
                    novo = RegiaoTabelaRede(
                        rede=rede,
                        uf=uf,
                        regiao=regiao,
                        criado_por=current_user.username if hasattr(current_user, 'username') else str(current_user.id),
                        ativo=True
                    )
                    db.session.add(novo)
                    criados += 1

            except Exception as e:
                erros.append(f"Erro na linha {idx + 2}: {str(e)}")

        db.session.commit()
        flash(f'Importação concluída: {criados} criados, {atualizados} atualizados', 'success')

        if erros:
            flash(f'Erros: {len(erros)} linhas com problema', 'warning')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao importar: {str(e)}', 'danger')

    return redirect(url_for('leitura_pedidos.regioes'))
