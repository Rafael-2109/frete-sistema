"""
Rotas de Frete e Descarte de Devolucao
======================================

APIs para:
- FreteDevolucao: Cotacao e acompanhamento de frete de retorno
- DescarteDevolucao: Registro e acompanhamento de descartes autorizados

Criado em: 31/12/2024
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from decimal import Decimal
from datetime import datetime

from app import db
from app.devolucao.models import (
    OcorrenciaDevolucao,
    FreteDevolucao,
    DescarteDevolucao,
    NFDevolucao,
    NFDevolucaoLinha,
    NFDevolucaoNFReferenciada
)
from app.devolucao.services.frete_placeholder_service import (
    obter_ou_criar_frete_para_devolucao,
    criar_despesa_devolucao
)
from app.producao.models import CadastroPalletizacao
from app.transportadoras.models import Transportadora
from app.utils.timezone import agora_utc_naive
from app.utils.file_storage import get_file_storage

# Blueprint
frete_bp = Blueprint('devolucao_frete', __name__, url_prefix='/frete')


# =============================================================================
# FRETE DEVOLUCAO - CRUD
# =============================================================================

@frete_bp.route('/api/<int:ocorrencia_id>/fretes', methods=['GET'])
@login_required
def listar_fretes(ocorrencia_id: int):
    """
    Lista fretes de uma ocorrencia

    GET /devolucao/frete/api/{ocorrencia_id}/fretes
    """
    try:
        ocorrencia = db.session.get(OcorrenciaDevolucao, ocorrencia_id)
        if not ocorrencia:
            return jsonify({'sucesso': False, 'erro': 'Ocorrencia nao encontrada'}), 404

        fretes = FreteDevolucao.query.filter_by(
            ocorrencia_devolucao_id=ocorrencia_id,
            ativo=True
        ).order_by(FreteDevolucao.data_cotacao.desc()).all()

        return jsonify({
            'sucesso': True,
            'ocorrencia_id': ocorrencia_id,
            'total': len(fretes),
            'fretes': [f.to_dict() for f in fretes]
        })

    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@frete_bp.route('/api/<int:ocorrencia_id>/fretes', methods=['POST'])
@login_required
def criar_frete(ocorrencia_id: int):
    """
    Cria cotacao de frete de retorno

    POST /devolucao/frete/api/{ocorrencia_id}/fretes
    Body:
    {
        "transportadora_id": 123,
        "transportadora_nome": "Transportadora XYZ",
        "valor_cotado": 150.00,
        "peso_kg": 100.5,
        "uf_origem": "SP",
        "cidade_origem": "Sao Paulo",
        "uf_destino": "SC",
        "cidade_destino": "Blumenau",
        "data_coleta_prevista": "2025-01-05",
        "observacoes": "Coleta pela manha"
    }

    LOGICA DE FRETE PLACEHOLDER:
    1. Verifica se NFD tem NF de venda vinculada (obrigatorio)
    2. Busca Frete existente para a NF de venda
    3. Se nao encontrar, cria Frete placeholder (valor 0)
    4. Cria DespesaExtra do tipo DEVOLUCAO vinculada ao Frete e NFD
    """
    try:
        ocorrencia = db.session.get(OcorrenciaDevolucao, ocorrencia_id)
        if not ocorrencia:
            return jsonify({'sucesso': False, 'erro': 'Ocorrencia nao encontrada'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'sucesso': False, 'erro': 'Dados obrigatorios'}), 400

        # Validacoes basicas
        if not data.get('transportadora_nome'):
            return jsonify({'sucesso': False, 'erro': 'Nome da transportadora obrigatorio'}), 400

        if not data.get('valor_cotado'):
            return jsonify({'sucesso': False, 'erro': 'Valor cotado obrigatorio'}), 400

        # Obter NFD da ocorrencia
        nfd = ocorrencia.nf_devolucao
        if not nfd:
            return jsonify({'sucesso': False, 'erro': 'NFD nao encontrada para esta ocorrencia'}), 400

        # Obter NF de venda (obrigatorio para criar frete de retorno)
        numero_nf_venda = None

        # Primeiro tenta pegar das NFs referenciadas (tabela M:N)
        nfs_ref = NFDevolucaoNFReferenciada.query.filter_by(nf_devolucao_id=nfd.id).first()
        if nfs_ref:
            numero_nf_venda = nfs_ref.numero_nf

        # Se nao encontrar, usa o campo legado numero_nf_venda
        if not numero_nf_venda:
            numero_nf_venda = nfd.numero_nf_venda

        if not numero_nf_venda:
            return jsonify({
                'sucesso': False,
                'erro': 'NFD sem NF de venda vinculada. Vincule a NF de venda antes de criar frete de retorno.'
            }), 400

        # Usuario
        usuario = current_user.username if hasattr(current_user, 'username') else str(current_user.id)

        # Buscar ou criar Frete para a NF de venda
        frete_principal, frete_criado = obter_ou_criar_frete_para_devolucao(
            nfd=nfd,
            numero_nf_venda=numero_nf_venda,
            criado_por=usuario
        )

        # Criar DespesaExtra do tipo DEVOLUCAO
        # ✅ NOVO: Passa transportadora_id para que a despesa apareça no fechamento correto
        valor_despesa = Decimal(str(data['valor_cotado']))
        despesa = criar_despesa_devolucao(
            frete=frete_principal,
            nfd=nfd,
            valor=float(valor_despesa),
            criado_por=usuario,
            transportadora_id=data.get('transportadora_id')  # ✅ Transportadora do frete de retorno
        )

        # Buscar transportadora se ID fornecido
        transportadora = None
        if data.get('transportadora_id'):
            transportadora = db.session.get(Transportadora,data['transportadora_id']) if data['transportadora_id'] else None

        # Criar FreteDevolucao (cotacao de retorno)
        frete_dev = FreteDevolucao(
            ocorrencia_devolucao_id=ocorrencia_id,
            transportadora_id=data.get('transportadora_id'),
            transportadora_nome=data['transportadora_nome'],
            cnpj_transportadora=transportadora.cnpj if transportadora else data.get('cnpj_transportadora'),
            valor_cotado=valor_despesa,
            valor_negociado=Decimal(str(data['valor_negociado'])) if data.get('valor_negociado') else None,
            peso_kg=Decimal(str(data['peso_kg'])) if data.get('peso_kg') else None,
            data_cotacao=agora_utc_naive().date(),
            data_coleta_prevista=datetime.strptime(data['data_coleta_prevista'], '%Y-%m-%d').date() if data.get('data_coleta_prevista') else None,
            data_entrega_prevista=datetime.strptime(data['data_entrega_prevista'], '%Y-%m-%d').date() if data.get('data_entrega_prevista') else None,
            local_coleta=data.get('local_coleta'),
            uf_origem=data.get('uf_origem'),
            cidade_origem=data.get('cidade_origem'),
            uf_destino=data.get('uf_destino'),
            cidade_destino=data.get('cidade_destino'),
            observacoes=data.get('observacoes'),
            status='COTADO',
            criado_por=usuario,
            despesa_extra_id=despesa.id  # Vincular com DespesaExtra
        )

        db.session.add(frete_dev)

        # Atualizar destino da ocorrencia para RETORNO
        if ocorrencia.destino == 'INDEFINIDO':
            ocorrencia.destino = 'RETORNO'
            ocorrencia.transportadora_retorno_id = data.get('transportadora_id')
            ocorrencia.transportadora_retorno_nome = data['transportadora_nome']

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': 'Cotacao de frete criada com sucesso',
            'frete': frete_dev.to_dict(),
            'despesa_extra_id': despesa.id,
            'frete_principal_id': frete_principal.id,
            'frete_placeholder_criado': frete_criado
        })

    except ValueError as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@frete_bp.route('/api/frete/<int:frete_id>', methods=['GET'])
@login_required
def obter_frete(frete_id: int):
    """
    Obtem detalhes de um frete

    GET /devolucao/frete/api/frete/{frete_id}
    """
    try:
        frete = db.session.get(FreteDevolucao, frete_id)
        if not frete:
            return jsonify({'sucesso': False, 'erro': 'Frete nao encontrado'}), 404

        return jsonify({
            'sucesso': True,
            'frete': frete.to_dict()
        })

    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@frete_bp.route('/api/frete/<int:frete_id>', methods=['PUT'])
@login_required
def atualizar_frete(frete_id: int):
    """
    Atualiza dados do frete

    PUT /devolucao/frete/api/frete/{frete_id}
    """
    try:
        frete = db.session.get(FreteDevolucao, frete_id)
        if not frete:
            return jsonify({'sucesso': False, 'erro': 'Frete nao encontrado'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'sucesso': False, 'erro': 'Dados obrigatorios'}), 400

        # Atualizar campos
        if 'transportadora_nome' in data:
            frete.transportadora_nome = data['transportadora_nome']
        if 'valor_cotado' in data:
            frete.valor_cotado = Decimal(str(data['valor_cotado']))
        if 'valor_negociado' in data:
            frete.valor_negociado = Decimal(str(data['valor_negociado'])) if data['valor_negociado'] else None
        if 'peso_kg' in data:
            frete.peso_kg = Decimal(str(data['peso_kg'])) if data['peso_kg'] else None
        if 'data_coleta_prevista' in data and data['data_coleta_prevista']:
            frete.data_coleta_prevista = datetime.strptime(data['data_coleta_prevista'], '%Y-%m-%d').date()
        if 'data_entrega_prevista' in data and data['data_entrega_prevista']:
            frete.data_entrega_prevista = datetime.strptime(data['data_entrega_prevista'], '%Y-%m-%d').date()
        if 'observacoes' in data:
            frete.observacoes = data['observacoes']

        frete.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        frete.atualizado_em = agora_utc_naive()

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': 'Frete atualizado com sucesso',
            'frete': frete.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@frete_bp.route('/api/frete/<int:frete_id>/status', methods=['PUT'])
@login_required
def atualizar_status_frete(frete_id: int):
    """
    Atualiza status do frete

    PUT /devolucao/frete/api/frete/{frete_id}/status
    Body:
    {
        "status": "APROVADO",
        "data_coleta_realizada": "2025-01-05",
        "numero_cte": "123456",
        "chave_cte": "35..."
    }
    """
    try:
        frete = db.session.get(FreteDevolucao, frete_id)
        if not frete:
            return jsonify({'sucesso': False, 'erro': 'Frete nao encontrado'}), 404

        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'sucesso': False, 'erro': 'Status obrigatorio'}), 400

        novo_status = data['status']
        if novo_status not in [s[0] for s in FreteDevolucao.STATUS_CHOICES]:
            return jsonify({'sucesso': False, 'erro': f'Status invalido: {novo_status}'}), 400

        frete.status = novo_status

        # Campos adicionais por status
        if novo_status == 'COLETADO' and data.get('data_coleta_realizada'):
            frete.data_coleta_realizada = datetime.strptime(data['data_coleta_realizada'], '%Y-%m-%d').date()
            # Atualizar localizacao da ocorrencia
            if frete.ocorrencia:
                frete.ocorrencia.localizacao_atual = 'EM_TRANSITO'

        if novo_status == 'ENTREGUE':
            if data.get('data_entrega_realizada'):
                frete.data_entrega_realizada = datetime.strptime(data['data_entrega_realizada'], '%Y-%m-%d').date()
            else:
                frete.data_entrega_realizada = agora_utc_naive().date()
            # Atualizar ocorrencia
            if frete.ocorrencia:
                frete.ocorrencia.localizacao_atual = 'CD'
                frete.ocorrencia.data_chegada_cd = agora_utc_naive()

        if data.get('numero_cte'):
            frete.numero_cte = data['numero_cte']
        if data.get('chave_cte'):
            frete.chave_cte = data['chave_cte']

        frete.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        frete.atualizado_em = agora_utc_naive()

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': f'Status atualizado para {novo_status}',
            'frete': frete.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@frete_bp.route('/api/frete/<int:frete_id>', methods=['DELETE'])
@login_required
def excluir_frete(frete_id: int):
    """
    Exclui (soft delete) um frete

    DELETE /devolucao/frete/api/frete/{frete_id}
    """
    try:
        frete = db.session.get(FreteDevolucao, frete_id)
        if not frete:
            return jsonify({'sucesso': False, 'erro': 'Frete nao encontrado'}), 404

        frete.ativo = False
        frete.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        frete.atualizado_em = agora_utc_naive()

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': 'Frete excluido com sucesso'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# DESCARTE DEVOLUCAO - CRUD
# =============================================================================

@frete_bp.route('/api/<int:ocorrencia_id>/descartes', methods=['GET'])
@login_required
def listar_descartes(ocorrencia_id: int):
    """
    Lista descartes de uma ocorrencia

    GET /devolucao/frete/api/{ocorrencia_id}/descartes
    """
    try:
        ocorrencia = db.session.get(OcorrenciaDevolucao, ocorrencia_id)
        if not ocorrencia:
            return jsonify({'sucesso': False, 'erro': 'Ocorrencia nao encontrada'}), 404

        descartes = DescarteDevolucao.query.filter_by(
            ocorrencia_devolucao_id=ocorrencia_id,
            ativo=True
        ).order_by(DescarteDevolucao.data_autorizacao.desc()).all()

        return jsonify({
            'sucesso': True,
            'ocorrencia_id': ocorrencia_id,
            'total': len(descartes),
            'descartes': [d.to_dict() for d in descartes]
        })

    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@frete_bp.route('/api/<int:ocorrencia_id>/descartes', methods=['POST'])
@login_required
def criar_descarte(ocorrencia_id: int):
    """
    Cria registro de descarte autorizado

    POST /devolucao/frete/api/{ocorrencia_id}/descartes
    Body:
    {
        "empresa_autorizada_nome": "Transportadora XYZ",
        "empresa_autorizada_documento": "00.000.000/0000-00",
        "empresa_autorizada_tipo": "TRANSPORTADOR",
        "motivo_descarte": "CUSTO_ALTO",
        "descricao_motivo": "Frete de retorno R$ 500, valor mercadoria R$ 100",
        "valor_mercadoria": 100.00,
        "observacoes": "Cliente vai descartar e enviar foto"
    }
    """
    try:
        ocorrencia = db.session.get(OcorrenciaDevolucao, ocorrencia_id)
        if not ocorrencia:
            return jsonify({'sucesso': False, 'erro': 'Ocorrencia nao encontrada'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'sucesso': False, 'erro': 'Dados obrigatorios'}), 400

        # Validacoes obrigatorias para compliance
        if not data.get('empresa_autorizada_nome'):
            return jsonify({'sucesso': False, 'erro': 'Nome da empresa autorizada obrigatorio'}), 400

        if not data.get('empresa_autorizada_documento'):
            return jsonify({'sucesso': False, 'erro': 'CNPJ/CPF da empresa autorizada obrigatorio'}), 400

        if not data.get('motivo_descarte'):
            return jsonify({'sucesso': False, 'erro': 'Motivo do descarte obrigatorio'}), 400

        # Gerar numero do termo
        numero_termo = DescarteDevolucao.gerar_numero_termo()

        descarte = DescarteDevolucao(
            ocorrencia_devolucao_id=ocorrencia_id,
            numero_termo=numero_termo,
            autorizado_por=current_user.nome if hasattr(current_user, 'nome') else str(current_user.id),
            # Empresa autorizada (compliance)
            empresa_autorizada_nome=data['empresa_autorizada_nome'],
            empresa_autorizada_documento=data['empresa_autorizada_documento'],
            empresa_autorizada_tipo=data.get('empresa_autorizada_tipo', 'TRANSPORTADOR'),
            # Dados internos
            motivo_descarte=data['motivo_descarte'],
            descricao_motivo=data.get('descricao_motivo'),
            valor_mercadoria=Decimal(str(data['valor_mercadoria'])) if data.get('valor_mercadoria') else None,
            tem_custo=data.get('tem_custo', False),
            valor_descarte=Decimal(str(data['valor_descarte'])) if data.get('valor_descarte') else None,
            fornecedor_descarte=data.get('fornecedor_descarte'),
            observacoes=data.get('observacoes'),
            status='AUTORIZADO',
            criado_por=current_user.username if hasattr(current_user, 'username') else str(current_user.id),
        )

        db.session.add(descarte)

        # Atualizar destino da ocorrencia para DESCARTE
        ocorrencia.destino = 'DESCARTE'

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': f'Descarte autorizado com sucesso. Termo: {numero_termo}',
            'descarte': descarte.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@frete_bp.route('/api/descarte/<int:descarte_id>', methods=['GET'])
@login_required
def obter_descarte(descarte_id: int):
    """
    Obtem detalhes de um descarte

    GET /devolucao/frete/api/descarte/{descarte_id}
    """
    try:
        descarte = db.session.get(DescarteDevolucao, descarte_id)
        if not descarte:
            return jsonify({'sucesso': False, 'erro': 'Descarte nao encontrado'}), 404

        return jsonify({
            'sucesso': True,
            'descarte': descarte.to_dict()
        })

    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@frete_bp.route('/api/descarte/<int:descarte_id>/status', methods=['PUT'])
@login_required
def atualizar_status_descarte(descarte_id: int):
    """
    Atualiza status do descarte

    PUT /devolucao/frete/api/descarte/{descarte_id}/status
    Body:
    {
        "status": "TERMO_ENVIADO",
        "termo_enviado_para": "cliente@email.com"
    }
    """
    try:
        descarte = db.session.get(DescarteDevolucao, descarte_id)
        if not descarte:
            return jsonify({'sucesso': False, 'erro': 'Descarte nao encontrado'}), 404

        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'sucesso': False, 'erro': 'Status obrigatorio'}), 400

        novo_status = data['status']
        if novo_status not in [s[0] for s in DescarteDevolucao.STATUS_CHOICES]:
            return jsonify({'sucesso': False, 'erro': f'Status invalido: {novo_status}'}), 400

        descarte.status = novo_status

        # Campos adicionais por status
        if novo_status == 'TERMO_ENVIADO':
            descarte.termo_enviado_em = agora_utc_naive()
            if data.get('termo_enviado_para'):
                descarte.termo_enviado_para = data['termo_enviado_para']

        if novo_status == 'TERMO_RETORNADO':
            descarte.termo_retornado_em = agora_utc_naive()

        if novo_status == 'DESCARTADO':
            if data.get('data_descarte'):
                descarte.data_descarte = datetime.strptime(data['data_descarte'], '%Y-%m-%d').date()
            else:
                descarte.data_descarte = agora_utc_naive().date()
            # Atualizar localizacao da ocorrencia
            if descarte.ocorrencia:
                descarte.ocorrencia.localizacao_atual = 'DESCARTADO'

        descarte.atualizado_por = current_user.username if hasattr(current_user, 'username') else str(current_user.id)
        descarte.atualizado_em = agora_utc_naive()

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': f'Status atualizado para {novo_status}',
            'descarte': descarte.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@frete_bp.route('/api/descarte/<int:descarte_id>/upload/<tipo>', methods=['POST'])
@login_required
def upload_documento_descarte(descarte_id: int, tipo: str):
    """
    Upload de documento do descarte

    POST /devolucao/frete/api/descarte/{descarte_id}/upload/{tipo}
    tipo: termo | termo_assinado | comprovante

    Form-data:
    - file: arquivo
    """
    try:
        descarte = db.session.get(DescarteDevolucao, descarte_id)
        if not descarte:
            return jsonify({'sucesso': False, 'erro': 'Descarte nao encontrado'}), 404

        if tipo not in ['termo', 'termo_assinado', 'comprovante']:
            return jsonify({'sucesso': False, 'erro': f'Tipo invalido: {tipo}'}), 400

        if 'file' not in request.files:
            return jsonify({'sucesso': False, 'erro': 'Arquivo nao enviado'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'sucesso': False, 'erro': 'Nome do arquivo vazio'}), 400

        # Salvar no S3
        file_storage = get_file_storage()
        folder = f"devolucoes/descartes/{descarte_id}/{tipo}"
        path, nome = file_storage.upload_file(file, folder)

        # Atualizar campos conforme tipo
        if tipo == 'termo':
            descarte.termo_path = path
            descarte.termo_nome_arquivo = nome
        elif tipo == 'termo_assinado':
            descarte.termo_assinado_path = path
            descarte.termo_assinado_nome_arquivo = nome
            descarte.termo_retornado_em = agora_utc_naive()
            if descarte.status == 'TERMO_ENVIADO':
                descarte.status = 'TERMO_RETORNADO'
        elif tipo == 'comprovante':
            descarte.comprovante_path = path
            descarte.comprovante_nome_arquivo = nome
            descarte.data_descarte = agora_utc_naive().date()
            descarte.status = 'DESCARTADO'
            if descarte.ocorrencia:
                descarte.ocorrencia.localizacao_atual = 'DESCARTADO'

        descarte.atualizado_por = current_user.username if hasattr(current_user, 'username') else str(current_user.id)
        descarte.atualizado_em = agora_utc_naive()

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': f'{tipo.replace("_", " ").title()} enviado com sucesso',
            'path': path,
            'nome_arquivo': nome
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@frete_bp.route('/api/descarte/<int:descarte_id>', methods=['DELETE'])
@login_required
def excluir_descarte(descarte_id: int):
    """
    Exclui (soft delete) um descarte

    DELETE /devolucao/frete/api/descarte/{descarte_id}
    """
    try:
        descarte = db.session.get(DescarteDevolucao, descarte_id)
        if not descarte:
            return jsonify({'sucesso': False, 'erro': 'Descarte nao encontrado'}), 404

        descarte.ativo = False
        descarte.atualizado_por = current_user.username if hasattr(current_user, 'username') else str(current_user.id)
        descarte.atualizado_em = agora_utc_naive()

        db.session.commit()

        return jsonify({
            'sucesso': True,
            'mensagem': 'Descarte excluido com sucesso'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# TERMO DE DESCARTE - Download e Impressao
# =============================================================================

@frete_bp.route('/api/descarte/<int:descarte_id>/termo/download', methods=['GET'])
@login_required
def download_termo_descarte(descarte_id: int):
    """
    Gera e baixa o termo de descarte em PDF

    GET /devolucao/frete/api/descarte/{descarte_id}/termo/download

    Requer empresa_autorizada preenchida antes de gerar o termo.
    """
    from flask import render_template, make_response
    from weasyprint import HTML
    from io import BytesIO

    try:
        descarte = db.session.get(DescarteDevolucao, descarte_id)
        if not descarte:
            return jsonify({'sucesso': False, 'erro': 'Descarte nao encontrado'}), 404

        # Validar empresa autorizada (obrigatorio para compliance)
        if not descarte.empresa_autorizada_nome or not descarte.empresa_autorizada_documento:
            return jsonify({
                'sucesso': False,
                'erro': 'Empresa autorizada nao cadastrada. Preencha o nome e CNPJ/CPF antes de gerar o termo.'
            }), 400

        ocorrencia = descarte.ocorrencia
        nfd = ocorrencia.nf_devolucao if ocorrencia else None

        if not nfd:
            return jsonify({'sucesso': False, 'erro': 'NFD nao encontrada'}), 404

        # Buscar linhas da NFD para itens
        linhas = NFDevolucaoLinha.query.filter_by(nf_devolucao_id=nfd.id).all()

        itens = []
        valor_total = Decimal('0')
        for linha in linhas:
            valor_linha = Decimal(str(linha.valor_total or 0))
            valor_total += valor_linha
            itens.append({
                'codigo': linha.codigo_produto_interno or linha.codigo_produto_cliente or '-',
                'descricao': linha.descricao_produto_interno or linha.descricao_produto_cliente or '-',
                'quantidade': float(linha.quantidade or 0),
                'unidade': linha.unidade_medida or 'UN',
                'valor_unitario': float(linha.valor_unitario or 0),
                'valor_total': float(valor_linha)
            })

        # Registrar download
        descarte.termo_salvo_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        descarte.termo_salvo_em = agora_utc_naive()
        db.session.commit()

        # Renderizar HTML
        html_content = render_template(
            'devolucao/termo_descarte.html',
            descarte=descarte,
            nfd=nfd,
            itens=itens,
            valor_total=float(valor_total),
            data_geracao=agora_utc_naive().strftime('%d/%m/%Y %H:%M'),
            usuario_geracao=current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        )

        # Gerar PDF com WeasyPrint
        pdf_buffer = BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        pdf_buffer.seek(0)

        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Termo_Descarte_{descarte.numero_termo}.pdf'

        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@frete_bp.route('/api/descarte/<int:descarte_id>/termo/imprimir', methods=['GET'])
@login_required
def imprimir_termo_descarte(descarte_id: int):
    """
    Abre o termo de descarte para impressao no navegador

    GET /devolucao/frete/api/descarte/{descarte_id}/termo/imprimir

    Requer empresa_autorizada preenchida antes de gerar o termo.
    """
    from flask import render_template

    try:
        descarte = db.session.get(DescarteDevolucao, descarte_id)
        if not descarte:
            return jsonify({'sucesso': False, 'erro': 'Descarte nao encontrado'}), 404

        # Validar empresa autorizada (obrigatorio para compliance)
        if not descarte.empresa_autorizada_nome or not descarte.empresa_autorizada_documento:
            return jsonify({
                'sucesso': False,
                'erro': 'Empresa autorizada nao cadastrada. Preencha o nome e CNPJ/CPF antes de gerar o termo.'
            }), 400

        ocorrencia = descarte.ocorrencia
        nfd = ocorrencia.nf_devolucao if ocorrencia else None

        if not nfd:
            return jsonify({'sucesso': False, 'erro': 'NFD nao encontrada'}), 404

        # Buscar linhas da NFD para itens
        linhas = NFDevolucaoLinha.query.filter_by(nf_devolucao_id=nfd.id).all()

        itens = []
        valor_total = Decimal('0')
        for linha in linhas:
            valor_linha = Decimal(str(linha.valor_total or 0))
            valor_total += valor_linha
            itens.append({
                'codigo': linha.codigo_produto_interno or linha.codigo_produto_cliente or '-',
                'descricao': linha.descricao_produto_interno or linha.descricao_produto_cliente or '-',
                'quantidade': float(linha.quantidade or 0),
                'unidade': linha.unidade_medida or 'UN',
                'valor_unitario': float(linha.valor_unitario or 0),
                'valor_total': float(valor_linha)
            })

        # Registrar impressao
        descarte.termo_impresso_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        descarte.termo_impresso_em = agora_utc_naive()
        db.session.commit()

        return render_template(
            'devolucao/termo_descarte.html',
            descarte=descarte,
            nfd=nfd,
            itens=itens,
            valor_total=float(valor_total),
            data_geracao=agora_utc_naive().strftime('%d/%m/%Y %H:%M'),
            usuario_geracao=current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# HELPERS - Calcular Peso da Devolucao
# =============================================================================

@frete_bp.route('/api/<int:ocorrencia_id>/calcular-peso', methods=['GET'])
@login_required
def calcular_peso_devolucao(ocorrencia_id: int):
    """
    Calcula peso total da devolucao baseado nos produtos.

    GET /devolucao/frete/api/{ocorrencia_id}/calcular-peso

    Para NFD (tipo_documento='NFD'):
        - Usa NFDevolucaoLinha + CadastroPalletizacao

    Para NF Revertida (tipo_documento='NF'):
        - Usa FaturamentoProduto (peso_total já está no registro)

    Retorna:
    - peso_total: soma de (qtd * peso_bruto) de cada linha
    - detalhes: lista com peso por produto
    """
    try:
        ocorrencia = db.session.get(OcorrenciaDevolucao, ocorrencia_id)
        if not ocorrencia:
            return jsonify({'sucesso': False, 'erro': 'Ocorrencia nao encontrada'}), 404

        # Buscar NFD associada
        nfd = NFDevolucao.query.filter_by(
            id=ocorrencia.nf_devolucao_id
        ).first()

        if not nfd:
            return jsonify({
                'sucesso': False,
                'erro': 'NFD nao encontrada para esta ocorrencia'
            }), 404

        peso_total = Decimal('0')
        detalhes = []

        # ========= NF REVERTIDA: Usar FaturamentoProduto =========
        if nfd.tipo_documento == 'NF' and nfd.numero_nf_venda:
            from app.faturamento.models import FaturamentoProduto

            produtos = FaturamentoProduto.query.filter_by(
                numero_nf=str(nfd.numero_nf_venda)
            ).all()

            if not produtos:
                return jsonify({
                    'sucesso': True,
                    'peso_total': 0,
                    'detalhes': [],
                    'mensagem': 'Nenhum produto encontrado para esta NF de Venda'
                })

            for prod in produtos:
                peso_prod = Decimal(str(prod.peso_total or 0))
                peso_total += peso_prod

                detalhes.append({
                    'codigo': prod.cod_produto,
                    'descricao': prod.nome_produto,
                    'quantidade': float(prod.qtd_produto_faturado or 0),
                    'peso_unitario': float(prod.peso_unitario_produto or 0),
                    'peso_total': float(peso_prod),
                    'cadastro_encontrado': True,  # Já é dado do sistema
                    'fonte': 'FaturamentoProduto'
                })

            return jsonify({
                'sucesso': True,
                'peso_total': float(peso_total),
                'detalhes': detalhes,
                'mensagem': f'Peso calculado (NF Venda): {float(peso_total):.3f} kg'
            })

        # ========= NFD: Usar NFDevolucaoLinha + CadastroPalletizacao =========
        linhas = NFDevolucaoLinha.query.filter_by(
            nf_devolucao_id=nfd.id
        ).all()

        if not linhas:
            return jsonify({
                'sucesso': True,
                'peso_total': 0,
                'detalhes': [],
                'mensagem': 'Nenhuma linha de produto na NFD'
            })

        for linha in linhas:
            # Usar codigo interno resolvido ou codigo do cliente
            codigo = linha.codigo_produto_interno or linha.codigo_produto_cliente

            if not codigo:
                continue

            peso_linha = Decimal('0')
            peso_unitario = Decimal('0')
            quantidade_usada = Decimal('0')
            cadastro_encontrado = False

            # PRIORIDADE 1: Usar peso_bruto ja calculado na linha (baseado em quantidade_convertida)
            if linha.peso_bruto:
                peso_linha = Decimal(str(linha.peso_bruto))
                quantidade_usada = Decimal(str(linha.quantidade_convertida or linha.quantidade or 0))
                # Buscar peso unitario do cadastro para exibir
                cadastro = CadastroPalletizacao.query.filter_by(cod_produto=codigo).first()
                if cadastro and cadastro.peso_bruto:
                    peso_unitario = Decimal(str(cadastro.peso_bruto))
                    cadastro_encontrado = True
            else:
                # FALLBACK: Calcular usando quantidade_convertida ou quantidade original
                cadastro = CadastroPalletizacao.query.filter_by(cod_produto=codigo).first()
                if cadastro and cadastro.peso_bruto:
                    peso_unitario = Decimal(str(cadastro.peso_bruto))
                    # Usar quantidade_convertida (caixas) se disponivel
                    quantidade_usada = Decimal(str(linha.quantidade_convertida or linha.quantidade or 0))
                    peso_linha = quantidade_usada * peso_unitario
                    cadastro_encontrado = True

            peso_total += peso_linha

            detalhes.append({
                'codigo': codigo,
                'descricao': linha.descricao_produto_interno or linha.descricao_produto_cliente,
                'quantidade': float(quantidade_usada),
                'peso_unitario': float(peso_unitario),
                'peso_total': float(peso_linha),
                'cadastro_encontrado': cadastro_encontrado
            })

        return jsonify({
            'sucesso': True,
            'peso_total': float(peso_total),
            'detalhes': detalhes,
            'mensagem': f'Peso calculado: {float(peso_total):.3f} kg'
        })

    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# HELPERS - Estimar Frete de Retorno
# =============================================================================

@frete_bp.route('/api/<int:ocorrencia_id>/estimar-retorno', methods=['POST'])
@login_required
def estimar_frete_retorno(ocorrencia_id: int):
    """
    Estima frete de retorno usando tabela da transportadora.

    IMPORTANTE: Todos os produtos devem estar resolvidos antes de estimar.

    POST /devolucao/frete/api/{ocorrencia_id}/estimar-retorno
    Body:
    {
        "transportadora_id": 123,
        "uf_origem": "RJ"
    }

    Retorna:
    - valor_estimado: frete calculado
    - percentual_nf: % do frete em relacao ao valor da NF
    - valor_por_kg: R$/kg da estimativa
    - componentes: breakdown detalhado do calculo (frete_peso, gris, adv, etc)
    """
    from app.tabelas.models import TabelaFrete
    from app.utils.calculadora_frete import CalculadoraFrete

    try:
        ocorrencia = db.session.get(OcorrenciaDevolucao, ocorrencia_id)
        if not ocorrencia:
            return jsonify({'sucesso': False, 'erro': 'Ocorrencia nao encontrada'}), 404

        data = request.get_json()
        transportadora_id = data.get('transportadora_id')
        uf_origem = data.get('uf_origem')

        if not transportadora_id:
            return jsonify({'sucesso': False, 'erro': 'transportadora_id obrigatorio'}), 400

        if not uf_origem:
            return jsonify({'sucesso': False, 'erro': 'uf_origem obrigatorio'}), 400

        # Buscar transportadora
        transportadora = db.session.get(Transportadora, transportadora_id)
        if not transportadora:
            return jsonify({'sucesso': False, 'erro': 'Transportadora nao encontrada'}), 404

        # Buscar NFD associada
        nfd = NFDevolucao.query.filter_by(id=ocorrencia.nf_devolucao_id).first()
        if not nfd:
            return jsonify({'sucesso': False, 'erro': 'NFD nao encontrada'}), 404

        # VALIDACAO: Verificar se todos os produtos estao resolvidos
        linhas_pendentes = NFDevolucaoLinha.query.filter_by(
            nf_devolucao_id=nfd.id,
            produto_resolvido=False
        ).count()

        if linhas_pendentes > 0:
            return jsonify({
                'sucesso': False,
                'erro': f'Existem {linhas_pendentes} produto(s) nao resolvido(s). Resolva todos os produtos antes de estimar o frete.',
                'produtos_pendentes': linhas_pendentes
            }), 400

        # Buscar tabela de frete (origem -> SP)
        tabela = TabelaFrete.query.filter_by(
            transportadora_id=transportadora_id,
            uf_origem=uf_origem,
            uf_destino='SP'
        ).first()

        if not tabela:
            # Tentar buscar tabela inversa (SP -> origem)
            tabela = TabelaFrete.query.filter_by(
                transportadora_id=transportadora_id,
                uf_origem='SP',
                uf_destino=uf_origem
            ).first()

        if not tabela:
            return jsonify({
                'sucesso': False,
                'erro': f'Tabela de frete nao encontrada para {uf_origem} -> SP'
            }), 404

        # Calcular peso total das linhas
        linhas = NFDevolucaoLinha.query.filter_by(nf_devolucao_id=nfd.id).all()
        peso_total = Decimal('0')
        valor_total = Decimal('0')

        for linha in linhas:
            # PRIORIDADE 1: Peso ja calculado e persistido na linha
            if linha.peso_bruto:
                peso_total += Decimal(str(linha.peso_bruto))
            else:
                # PRIORIDADE 2: Calcular usando quantidade_convertida ou quantidade
                codigo = linha.codigo_produto_interno or linha.codigo_produto_cliente
                if codigo:
                    cadastro = CadastroPalletizacao.query.filter_by(cod_produto=codigo).first()
                    if cadastro and cadastro.peso_bruto:
                        # Usar quantidade_convertida (caixas) se disponivel, senao quantidade original
                        quantidade = Decimal(str(linha.quantidade_convertida or linha.quantidade or 0))
                        peso_total += quantidade * Decimal(str(cadastro.peso_bruto))

            if linha.valor_total:
                valor_total += Decimal(str(linha.valor_total))

        if peso_total == 0:
            return jsonify({
                'sucesso': False,
                'erro': 'Peso total zerado. Verifique os produtos.'
            }), 400

        # Montar dados da tabela para calculadora
        tabela_dados = {
            'valor_kg': float(tabela.valor_kg or 0),
            'percentual_valor': float(tabela.percentual_valor or 0),
            'frete_minimo_valor': float(tabela.frete_minimo_valor or 0),
            'frete_minimo_peso': float(tabela.frete_minimo_peso or 0),
            'percentual_gris': float(tabela.percentual_gris or 0),
            'gris_minimo': float(tabela.gris_minimo or 0),
            'percentual_adv': float(tabela.percentual_adv or 0),
            'adv_minimo': float(tabela.adv_minimo or 0),
            'percentual_rca': float(tabela.percentual_rca or 0),
            'pedagio_por_100kg': float(tabela.pedagio_por_100kg or 0),
            'valor_tas': float(tabela.valor_tas or 0),
            'valor_despacho': float(tabela.valor_despacho or 0),
            'valor_cte': float(tabela.valor_cte or 0),
            'icms_incluso': tabela.icms_incluso or False,
            'icms_proprio': float(tabela.icms_proprio) if tabela.icms_proprio else None,
            'icms_destino': 18  # ICMS SP padrao
        }

        # Configuracao da transportadora
        transportadora_config = {
            'aplica_gris_pos_minimo': transportadora.aplica_gris_pos_minimo,
            'aplica_adv_pos_minimo': transportadora.aplica_adv_pos_minimo,
            'aplica_rca_pos_minimo': transportadora.aplica_rca_pos_minimo,
            'aplica_pedagio_pos_minimo': transportadora.aplica_pedagio_pos_minimo,
            'aplica_despacho_pos_minimo': transportadora.aplica_despacho_pos_minimo,
            'aplica_cte_pos_minimo': transportadora.aplica_cte_pos_minimo,
            'aplica_tas_pos_minimo': transportadora.aplica_tas_pos_minimo,
            'pedagio_por_fracao': transportadora.pedagio_por_fracao
        }

        # Calcular frete
        resultado = CalculadoraFrete.calcular_frete_unificado(
            peso=float(peso_total),
            valor_mercadoria=float(valor_total),
            tabela_dados=tabela_dados,
            transportadora_optante=transportadora.optante or False,
            transportadora_config=transportadora_config
        )

        frete_integral = resultado.get('valor_com_icms', 0)
        detalhes = resultado.get('detalhes', {})

        # Calcular metricas usando 100% do frete
        percentual_nf = (frete_integral / float(valor_total) * 100) if valor_total > 0 else 0
        valor_por_kg = (frete_integral / float(peso_total)) if peso_total > 0 else 0

        return jsonify({
            'sucesso': True,
            'valor_estimado': round(frete_integral, 2),
            'peso_kg': round(float(peso_total), 3),
            'valor_nf': round(float(valor_total), 2),
            'percentual_nf': round(percentual_nf, 2),
            'valor_por_kg': round(valor_por_kg, 2),
            'transportadora': transportadora.razao_social,
            'tabela': tabela.nome_tabela,
            'rota': f'{uf_origem} -> SP',
            'componentes': {
                'frete_peso': detalhes.get('frete_base', 0),
                'gris': detalhes.get('gris', 0),
                'adv': detalhes.get('adv', 0),
                'rca': detalhes.get('rca', 0),
                'pedagio': detalhes.get('pedagio', 0),
                'tas': detalhes.get('valor_tas', 0),
                'despacho': detalhes.get('valor_despacho', 0),
                'cte': detalhes.get('valor_cte', 0),
                'subtotal': detalhes.get('frete_liquido_antes_minimo', 0),
                'frete_minimo_aplicado': detalhes.get('frete_minimo_aplicado', False),
                'icms_percentual': resultado.get('icms_aplicado', 0),
                'total': frete_integral
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# HELPERS - Listar Transportadoras
# =============================================================================

@frete_bp.route('/api/transportadoras', methods=['GET'])
@login_required
def listar_transportadoras():
    """
    Lista transportadoras ativas para select

    GET /devolucao/frete/api/transportadoras
    """
    try:
        transportadoras = Transportadora.query.filter_by(
            ativo=True
        ).order_by(Transportadora.razao_social).all()

        return jsonify({
            'sucesso': True,
            'transportadoras': [
                {
                    'id': t.id,
                    'nome': t.razao_social,
                    'cnpj': t.cnpj,
                    'cidade': t.cidade,
                    'uf': t.uf
                }
                for t in transportadoras
            ]
        })

    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# HELPERS - Motivos de Descarte
# =============================================================================

@frete_bp.route('/api/motivos-descarte', methods=['GET'])
@login_required
def listar_motivos_descarte():
    """
    Lista motivos de descarte disponiveis

    GET /devolucao/frete/api/motivos-descarte
    """
    return jsonify({
        'sucesso': True,
        'motivos': [
            {'codigo': m[0], 'descricao': m[1]}
            for m in DescarteDevolucao.MOTIVOS_DESCARTE
        ]
    })


# =============================================================================
# HELPERS - UFs e Cidades
# =============================================================================

@frete_bp.route('/api/ufs', methods=['GET'])
@login_required
def listar_ufs():
    """
    Lista todos os UFs disponiveis (distintos da tabela cidades)

    GET /devolucao/frete/api/ufs
    """
    from app.localidades.models import Cidade
    from sqlalchemy import distinct

    try:
        ufs = db.session.query(distinct(Cidade.uf)).order_by(Cidade.uf).all()

        return jsonify({
            'sucesso': True,
            'ufs': [uf[0] for uf in ufs]
        })

    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@frete_bp.route('/api/cidades/<uf>', methods=['GET'])
@login_required
def listar_cidades_por_uf(uf: str):
    """
    Lista cidades de um UF especifico

    GET /devolucao/frete/api/cidades/{uf}
    """
    from app.localidades.models import Cidade

    try:
        cidades = Cidade.query.filter_by(
            uf=uf.upper()
        ).order_by(Cidade.nome).all()

        return jsonify({
            'sucesso': True,
            'uf': uf.upper(),
            'cidades': [
                {
                    'id': c.id,
                    'nome': c.nome,
                    'codigo_ibge': c.codigo_ibge
                }
                for c in cidades
            ]
        })

    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500
