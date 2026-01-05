"""
Rotas de Ocorrencias de Devolucao
=================================

Dashboard e gerenciamento de ocorrencias para Comercial e Logistica.

Criado em: 30/12/2024
"""
from flask import (
    Blueprint, request, jsonify, render_template
)
from flask_login import login_required, current_user
from app import db
from app.devolucao.models import (
    NFDevolucao, NFDevolucaoLinha, OcorrenciaDevolucao,
    FreteDevolucao, AnexoOcorrencia, DescarteDevolucao,
    NFDevolucaoNFReferenciada
)
from app.monitoramento.models import EntregaMonitorada
from app.utils.timezone import agora_brasil
from sqlalchemy import or_, func
from datetime import datetime, timedelta

# Blueprint
ocorrencia_bp = Blueprint('devolucao_ocorrencia', __name__, url_prefix='/ocorrencias')


# =============================================================================
# Dashboard de Ocorrencias
# =============================================================================

@ocorrencia_bp.route('/')
@login_required
def index():
    """
    Dashboard principal de ocorrencias

    Filtros via query params:
    - status: ABERTA, EM_ANALISE, RESOLVIDA
    - destino: RETORNO, DESCARTE, INDEFINIDO
    - categoria: QUALIDADE, COMERCIAL, LOGISTICA
    - responsavel: NACOM, TRANSPORTADORA, CLIENTE
    - busca: texto livre (numero_ocorrencia, numero_nfd, cliente)
    - data_inicio, data_fim: periodo
    """
    # Filtros
    status = request.args.get('status', '')
    destino = request.args.get('destino', '')
    categoria = request.args.get('categoria', '')
    responsavel = request.args.get('responsavel', '')
    busca = request.args.get('busca', '').strip()
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')

    # Query base
    query = db.session.query(OcorrenciaDevolucao).join(
        NFDevolucao, OcorrenciaDevolucao.nf_devolucao_id == NFDevolucao.id
    ).outerjoin(
        EntregaMonitorada, NFDevolucao.entrega_monitorada_id == EntregaMonitorada.id
    ).filter(
        OcorrenciaDevolucao.ativo == True
    )

    # Aplicar filtros
    if status:
        query = query.filter(OcorrenciaDevolucao.status == status)

    if destino:
        query = query.filter(OcorrenciaDevolucao.destino == destino)

    if categoria:
        query = query.filter(OcorrenciaDevolucao.categoria == categoria)

    if responsavel:
        query = query.filter(OcorrenciaDevolucao.responsavel == responsavel)

    if busca:
        busca_like = f'%{busca}%'
        query = query.filter(or_(
            OcorrenciaDevolucao.numero_ocorrencia.ilike(busca_like),
            NFDevolucao.numero_nfd.ilike(busca_like),
            NFDevolucao.nome_emitente.ilike(busca_like),
            EntregaMonitorada.cliente.ilike(busca_like)
        ))

    if data_inicio:
        try:
            dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(OcorrenciaDevolucao.data_abertura >= dt_inicio)
        except ValueError:
            pass

    if data_fim:
        try:
            dt_fim = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(OcorrenciaDevolucao.data_abertura < dt_fim)
        except ValueError:
            pass

    # Ordenar por mais recente
    query = query.order_by(OcorrenciaDevolucao.data_abertura.desc())

    # Paginacao
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    ocorrencias = pagination.items

    # Estatisticas
    stats = {
        'total': OcorrenciaDevolucao.query.filter_by(ativo=True).count(),
        'abertas': OcorrenciaDevolucao.query.filter_by(ativo=True, status='ABERTA').count(),
        'em_analise': OcorrenciaDevolucao.query.filter_by(ativo=True, status='EM_ANALISE').count(),
        'resolvidas': OcorrenciaDevolucao.query.filter_by(ativo=True, status='RESOLVIDA').count(),
    }

    return render_template(
        'devolucao/ocorrencias/index.html',
        ocorrencias=ocorrencias,
        pagination=pagination,
        stats=stats,
        filtros={
            'status': status,
            'destino': destino,
            'categoria': categoria,
            'responsavel': responsavel,
            'busca': busca,
            'data_inicio': data_inicio,
            'data_fim': data_fim
        },
        opcoes_status=OcorrenciaDevolucao.STATUS_OCORRENCIA,
        opcoes_destino=OcorrenciaDevolucao.DESTINOS,
        opcoes_categoria=OcorrenciaDevolucao.CATEGORIAS,
        opcoes_responsavel=OcorrenciaDevolucao.RESPONSAVEIS
    )


@ocorrencia_bp.route('/<int:ocorrencia_id>')
@login_required
def detalhe(ocorrencia_id):
    """
    Detalhe de uma ocorrencia com secoes Logistica e Comercial
    """
    ocorrencia = OcorrenciaDevolucao.query.get_or_404(ocorrencia_id)
    nfd = ocorrencia.nf_devolucao
    entrega = nfd.entrega_monitorada if nfd else None

    # Linhas da NFD (se importada do Odoo)
    linhas = NFDevolucaoLinha.query.filter_by(
        nf_devolucao_id=nfd.id
    ).all() if nfd else []

    # NFs de venda referenciadas (pode ser N NFs)
    nfs_referenciadas = []
    if nfd:
        refs = NFDevolucaoNFReferenciada.query.filter_by(
            nf_devolucao_id=nfd.id
        ).all()

        for ref in refs:
            # Buscar entrega monitorada vinculada ou por numero da NF
            entrega_ref = None
            if ref.entrega_monitorada_id:
                entrega_ref = EntregaMonitorada.query.get(ref.entrega_monitorada_id)
            elif ref.numero_nf:
                # Buscar por numero da NF
                entrega_ref = EntregaMonitorada.query.filter_by(
                    numero_nf=ref.numero_nf
                ).first()

            nfs_referenciadas.append({
                'id': ref.id,
                'numero_nf': ref.numero_nf,
                'serie_nf': ref.serie_nf,
                'chave_nf': ref.chave_nf,
                'origem': ref.origem,
                'entrega_id': entrega_ref.id if entrega_ref else None,
                'cliente': entrega_ref.cliente if entrega_ref else None
            })

    # Fretes de retorno
    fretes = FreteDevolucao.query.filter_by(
        ocorrencia_devolucao_id=ocorrencia_id,
        ativo=True
    ).order_by(FreteDevolucao.data_cotacao.desc()).all()

    # Descartes autorizados
    descartes = DescarteDevolucao.query.filter_by(
        ocorrencia_devolucao_id=ocorrencia_id,
        ativo=True
    ).order_by(DescarteDevolucao.data_autorizacao.desc()).all()

    # Anexos
    anexos = AnexoOcorrencia.query.filter_by(
        ocorrencia_devolucao_id=ocorrencia_id,
        ativo=True
    ).order_by(AnexoOcorrencia.criado_em.desc()).all()

    return render_template(
        'devolucao/ocorrencias/detalhe.html',
        ocorrencia=ocorrencia,
        nfd=nfd,
        entrega=entrega,
        linhas=linhas,
        nfs_referenciadas=nfs_referenciadas,
        fretes=fretes,
        descartes=descartes,
        anexos=anexos,
        opcoes_status=OcorrenciaDevolucao.STATUS_OCORRENCIA,
        opcoes_destino=OcorrenciaDevolucao.DESTINOS,
        opcoes_localizacao=OcorrenciaDevolucao.LOCALIZACOES,
        opcoes_categoria=OcorrenciaDevolucao.CATEGORIAS,
        opcoes_subcategoria=OcorrenciaDevolucao.SUBCATEGORIAS,
        opcoes_responsavel=OcorrenciaDevolucao.RESPONSAVEIS,
        opcoes_origem=OcorrenciaDevolucao.ORIGENS,
        opcoes_momento_devolucao=OcorrenciaDevolucao.MOMENTOS_DEVOLUCAO
    )


# =============================================================================
# API Endpoints
# =============================================================================

@ocorrencia_bp.route('/api/<int:ocorrencia_id>/logistica', methods=['PUT'])
@login_required
def api_atualizar_logistica(ocorrencia_id):
    """
    Atualiza secao Logistica da ocorrencia

    Body JSON:
    {
        "destino": "RETORNO",
        "localizacao_atual": "EM_TRANSITO",
        "transportadora_retorno_id": 123,
        "data_previsao_retorno": "2024-12-31",
        "observacoes_logistica": "..."
    }
    """
    try:
        ocorrencia = OcorrenciaDevolucao.query.get(ocorrencia_id)
        if not ocorrencia:
            return jsonify({'sucesso': False, 'erro': 'Ocorrencia nao encontrada'}), 404

        data = request.get_json()

        # Atualizar campos de logistica
        if 'destino' in data:
            ocorrencia.destino = data['destino']

        if 'localizacao_atual' in data:
            ocorrencia.localizacao_atual = data['localizacao_atual']

        if 'transportadora_retorno_id' in data:
            ocorrencia.transportadora_retorno_id = data['transportadora_retorno_id']
            # Buscar nome da transportadora
            if data['transportadora_retorno_id']:
                from app.transportadoras.models import Transportadora
                transp = Transportadora.query.get(data['transportadora_retorno_id'])
                if transp:
                    ocorrencia.transportadora_retorno_nome = transp.razao_social

        if 'data_previsao_retorno' in data and data['data_previsao_retorno']:
            try:
                ocorrencia.data_previsao_retorno = datetime.strptime(
                    data['data_previsao_retorno'], '%Y-%m-%d'
                ).date()
            except ValueError:
                pass

        if 'data_chegada_cd' in data and data['data_chegada_cd']:
            try:
                ocorrencia.data_chegada_cd = datetime.strptime(
                    data['data_chegada_cd'], '%Y-%m-%dT%H:%M'
                )
            except ValueError:
                pass

        if 'recebido_por' in data:
            ocorrencia.recebido_por = data['recebido_por']

        if 'observacoes_logistica' in data:
            ocorrencia.observacoes_logistica = data['observacoes_logistica']

        # Auditoria
        ocorrencia.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else current_user.username
        ocorrencia.atualizado_em = agora_brasil()

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': 'Dados de logistica atualizados!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@ocorrencia_bp.route('/api/<int:ocorrencia_id>/comercial', methods=['PUT'])
@login_required
def api_atualizar_comercial(ocorrencia_id):
    """
    Atualiza secao Comercial da ocorrencia

    Body JSON:
    {
        "categoria": "QUALIDADE",
        "subcategoria": "AVARIA_TRANSPORTE",
        "descricao_comercial": "...",
        "responsavel": "TRANSPORTADORA",
        "status": "EM_ANALISE",
        "origem": "TRANSPORTE",
        "autorizado_por": "Joao",
        "desfecho": "..."
    }
    """
    try:
        ocorrencia = OcorrenciaDevolucao.query.get(ocorrencia_id)
        if not ocorrencia:
            return jsonify({'sucesso': False, 'erro': 'Ocorrencia nao encontrada'}), 404

        data = request.get_json()

        # Atualizar campos comerciais
        if 'categoria' in data:
            ocorrencia.categoria = data['categoria']

        if 'subcategoria' in data:
            ocorrencia.subcategoria = data['subcategoria']

        if 'descricao_comercial' in data:
            ocorrencia.descricao_comercial = data['descricao_comercial']

        if 'responsavel' in data:
            ocorrencia.responsavel = data['responsavel']

        if 'status' in data:
            status_anterior = ocorrencia.status
            ocorrencia.status = data['status']

            # Marcar data de resolucao se mudou para RESOLVIDA
            if data['status'] == 'RESOLVIDA' and status_anterior != 'RESOLVIDA':
                ocorrencia.data_resolucao = agora_brasil()
                ocorrencia.resolvido_por = current_user.nome if hasattr(current_user, 'nome') else current_user.username

            # Marcar data de acao comercial se mudou para EM_ANALISE
            if data['status'] == 'EM_ANALISE' and status_anterior == 'ABERTA':
                ocorrencia.data_acao_comercial = agora_brasil()

        if 'origem' in data:
            ocorrencia.origem = data['origem']

        if 'momento_devolucao' in data:
            ocorrencia.momento_devolucao = data['momento_devolucao']

        if 'autorizado_por' in data:
            ocorrencia.autorizado_por = data['autorizado_por']

        if 'desfecho' in data:
            ocorrencia.desfecho = data['desfecho']

        # Auditoria
        ocorrencia.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else current_user.username
        ocorrencia.atualizado_em = agora_brasil()

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': 'Dados comerciais atualizados!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@ocorrencia_bp.route('/api/<int:ocorrencia_id>', methods=['GET'])
@login_required
def api_obter_ocorrencia(ocorrencia_id):
    """
    Obtem dados de uma ocorrencia
    """
    try:
        ocorrencia = OcorrenciaDevolucao.query.get(ocorrencia_id)
        if not ocorrencia:
            return jsonify({'sucesso': False, 'erro': 'Ocorrencia nao encontrada'}), 404

        return jsonify({
            'sucesso': True,
            'ocorrencia': ocorrencia.to_dict()
        })

    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@ocorrencia_bp.route('/api/stats', methods=['GET'])
@login_required
def api_stats():
    """
    Retorna estatisticas das ocorrencias
    """
    try:
        # Por status
        stats_status = db.session.query(
            OcorrenciaDevolucao.status,
            func.count(OcorrenciaDevolucao.id)
        ).filter(
            OcorrenciaDevolucao.ativo == True
        ).group_by(OcorrenciaDevolucao.status).all()

        # Por categoria
        stats_categoria = db.session.query(
            OcorrenciaDevolucao.categoria,
            func.count(OcorrenciaDevolucao.id)
        ).filter(
            OcorrenciaDevolucao.ativo == True,
            OcorrenciaDevolucao.categoria.isnot(None)
        ).group_by(OcorrenciaDevolucao.categoria).all()

        # Por responsavel
        stats_responsavel = db.session.query(
            OcorrenciaDevolucao.responsavel,
            func.count(OcorrenciaDevolucao.id)
        ).filter(
            OcorrenciaDevolucao.ativo == True,
            OcorrenciaDevolucao.responsavel.isnot(None)
        ).group_by(OcorrenciaDevolucao.responsavel).all()

        return jsonify({
            'sucesso': True,
            'por_status': {s: c for s, c in stats_status},
            'por_categoria': {c: n for c, n in stats_categoria if c},
            'por_responsavel': {r: n for r, n in stats_responsavel if r}
        })

    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# Anexos da Ocorrencia
# =============================================================================

@ocorrencia_bp.route('/api/<int:ocorrencia_id>/anexos', methods=['POST'])
@login_required
def api_upload_anexo(ocorrencia_id):
    """
    Upload de anexo para ocorrencia

    Form-data:
    - arquivo: Arquivo a ser enviado
    - tipo: EMAIL, FOTO, DOCUMENTO (opcional, default: DOCUMENTO)
    - descricao: Descricao do anexo (opcional)
    """
    from flask import current_app
    from app.utils.file_storage import FileStorage
    from werkzeug.utils import secure_filename

    try:
        ocorrencia = OcorrenciaDevolucao.query.get(ocorrencia_id)
        if not ocorrencia:
            return jsonify({'sucesso': False, 'erro': 'Ocorrencia nao encontrada'}), 404

        # Verificar arquivo
        if 'arquivo' not in request.files:
            return jsonify({'sucesso': False, 'erro': 'Nenhum arquivo enviado'}), 400

        arquivo = request.files['arquivo']
        if not arquivo.filename:
            return jsonify({'sucesso': False, 'erro': 'Arquivo vazio'}), 400

        # Dados do formulario
        tipo = request.form.get('tipo', 'DOCUMENTO').upper()
        descricao = request.form.get('descricao', '').strip()

        # Validar tipo
        tipos_validos = ['EMAIL', 'FOTO', 'DOCUMENTO', 'PLANILHA', 'OUTROS']
        if tipo not in tipos_validos:
            tipo = 'OUTROS'

        # Extensoes permitidas por tipo
        extensoes_por_tipo = {
            'EMAIL': ['msg', 'eml'],
            'FOTO': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
            'DOCUMENTO': ['pdf', 'doc', 'docx', 'txt'],
            'PLANILHA': ['xls', 'xlsx', 'csv'],
            'OUTROS': ['pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'csv', 'jpg', 'jpeg', 'png', 'gif', 'msg', 'eml', 'zip']
        }

        # Salvar arquivo
        storage = FileStorage()
        folder = f"devolucoes/ocorrencias/{ocorrencia_id}"

        try:
            caminho = storage.save_file(
                arquivo,
                folder,
                allowed_extensions=extensoes_por_tipo.get(tipo, extensoes_por_tipo['OUTROS'])
            )
        except ValueError as e:
            return jsonify({'sucesso': False, 'erro': str(e)}), 400

        if not caminho:
            return jsonify({'sucesso': False, 'erro': 'Erro ao salvar arquivo'}), 500

        # Criar registro do anexo
        nome_seguro = secure_filename(arquivo.filename)
        anexo = AnexoOcorrencia(
            ocorrencia_devolucao_id=ocorrencia_id,
            tipo=tipo,
            nome_original=arquivo.filename,
            nome_arquivo=nome_seguro,
            caminho_s3=caminho,
            tamanho_bytes=arquivo.content_length or 0,
            content_type=arquivo.content_type,
            descricao=descricao or None,
            criado_por=current_user.nome if hasattr(current_user, 'nome') else current_user.username
        )

        db.session.add(anexo)
        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': 'Anexo enviado com sucesso!',
            'anexo': {
                'id': anexo.id,
                'nome': anexo.nome_original,
                'tipo': anexo.tipo,
                'tamanho_kb': anexo.tamanho_kb
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao fazer upload de anexo: {str(e)}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@ocorrencia_bp.route('/api/<int:ocorrencia_id>/anexos/<int:anexo_id>/download')
@login_required
def api_download_anexo(ocorrencia_id, anexo_id):
    """
    Download de anexo
    """
    from flask import current_app, redirect, send_file
    from app.utils.file_storage import FileStorage
    import os

    try:
        anexo = AnexoOcorrencia.query.filter_by(
            id=anexo_id,
            ocorrencia_devolucao_id=ocorrencia_id,
            ativo=True
        ).first()

        if not anexo:
            return jsonify({'sucesso': False, 'erro': 'Anexo nao encontrado'}), 404

        storage = FileStorage()

        if storage.use_s3:
            # Gerar URL assinada do S3
            url = storage.get_file_url(anexo.caminho_s3)
            if url:
                return redirect(url)
            else:
                return jsonify({'sucesso': False, 'erro': 'Erro ao gerar URL de download'}), 500
        else:
            # Arquivo local
            file_path = os.path.join(current_app.root_path, 'static', anexo.caminho_s3)
            if os.path.exists(file_path):
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=anexo.nome_original,
                    mimetype=anexo.content_type or 'application/octet-stream'
                )
            else:
                return jsonify({'sucesso': False, 'erro': 'Arquivo nao encontrado'}), 404

    except Exception as e:
        current_app.logger.error(f"Erro ao baixar anexo {anexo_id}: {str(e)}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@ocorrencia_bp.route('/api/<int:ocorrencia_id>/anexos/<int:anexo_id>', methods=['DELETE'])
@login_required
def api_excluir_anexo(ocorrencia_id, anexo_id):
    """
    Exclui anexo (soft delete)
    """
    from flask import current_app

    try:
        anexo = AnexoOcorrencia.query.filter_by(
            id=anexo_id,
            ocorrencia_devolucao_id=ocorrencia_id,
            ativo=True
        ).first()

        if not anexo:
            return jsonify({'sucesso': False, 'erro': 'Anexo nao encontrado'}), 404

        # Soft delete
        anexo.ativo = False
        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': f'Anexo {anexo.nome_original} excluido!'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao excluir anexo {anexo_id}: {str(e)}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@ocorrencia_bp.route('/api/<int:ocorrencia_id>/anexos', methods=['GET'])
@login_required
def api_listar_anexos(ocorrencia_id):
    """
    Lista anexos de uma ocorrencia
    """
    try:
        anexos = AnexoOcorrencia.query.filter_by(
            ocorrencia_devolucao_id=ocorrencia_id,
            ativo=True
        ).order_by(AnexoOcorrencia.criado_em.desc()).all()

        return jsonify({
            'sucesso': True,
            'anexos': [a.to_dict() for a in anexos]
        })

    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# Download de XML e PDF da NFD
# =============================================================================

@ocorrencia_bp.route('/nfd/<int:nfd_id>/xml')
@login_required
def download_xml(nfd_id):
    """
    Download do XML da NFD
    """
    from flask import current_app, redirect, send_file, Response
    from app.utils.file_storage import FileStorage
    import base64
    import os

    try:
        nfd = NFDevolucao.query.get(nfd_id)
        if not nfd:
            return jsonify({'sucesso': False, 'erro': 'NFD nao encontrada'}), 404

        # Se tem path do S3, baixar de la
        if nfd.nfd_xml_path:
            storage = FileStorage()

            if storage.use_s3:
                url = storage.get_file_url(nfd.nfd_xml_path)
                if url:
                    return redirect(url)
            else:
                file_path = os.path.join(current_app.root_path, 'static', nfd.nfd_xml_path)
                if os.path.exists(file_path):
                    return send_file(
                        file_path,
                        as_attachment=True,
                        download_name=nfd.nfd_xml_nome_arquivo or f'NFD_{nfd.numero_nfd}.xml',
                        mimetype='application/xml'
                    )

        # Se tem conteudo base64 (dados do Odoo ainda nao salvos em arquivo)
        if hasattr(nfd, 'xml_base64') and nfd.xml_base64:
            try:
                xml_content = base64.b64decode(nfd.xml_base64)
                return Response(
                    xml_content,
                    mimetype='application/xml',
                    headers={
                        'Content-Disposition': f'attachment; filename=NFD_{nfd.numero_nfd}.xml'
                    }
                )
            except Exception:
                pass

        return jsonify({'sucesso': False, 'erro': 'XML nao disponivel'}), 404

    except Exception as e:
        current_app.logger.error(f"Erro ao baixar XML da NFD {nfd_id}: {str(e)}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@ocorrencia_bp.route('/nfd/<int:nfd_id>/pdf')
@login_required
def download_pdf(nfd_id):
    """
    Download do PDF (DANFE) da NFD
    """
    from flask import current_app, redirect, send_file, Response
    from app.utils.file_storage import FileStorage
    import base64
    import os

    try:
        nfd = NFDevolucao.query.get(nfd_id)
        if not nfd:
            return jsonify({'sucesso': False, 'erro': 'NFD nao encontrada'}), 404

        # Se tem path do S3, baixar de la
        if nfd.nfd_pdf_path:
            storage = FileStorage()

            if storage.use_s3:
                url = storage.get_file_url(nfd.nfd_pdf_path)
                if url:
                    return redirect(url)
            else:
                file_path = os.path.join(current_app.root_path, 'static', nfd.nfd_pdf_path)
                if os.path.exists(file_path):
                    return send_file(
                        file_path,
                        as_attachment=True,
                        download_name=nfd.nfd_pdf_nome_arquivo or f'NFD_{nfd.numero_nfd}.pdf',
                        mimetype='application/pdf'
                    )

        # Se tem conteudo base64 (dados do Odoo ainda nao salvos em arquivo)
        if hasattr(nfd, 'pdf_base64') and nfd.pdf_base64:
            try:
                pdf_content = base64.b64decode(nfd.pdf_base64)
                return Response(
                    pdf_content,
                    mimetype='application/pdf',
                    headers={
                        'Content-Disposition': f'attachment; filename=NFD_{nfd.numero_nfd}.pdf'
                    }
                )
            except Exception:
                pass

        return jsonify({'sucesso': False, 'erro': 'PDF nao disponivel'}), 404

    except Exception as e:
        current_app.logger.error(f"Erro ao baixar PDF da NFD {nfd_id}: {str(e)}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# Registrar blueprint
# =============================================================================

def init_app(app):
    """Registra o blueprint no aplicativo Flask"""
    from app.devolucao import devolucao_bp
    devolucao_bp.register_blueprint(ocorrencia_bp)
