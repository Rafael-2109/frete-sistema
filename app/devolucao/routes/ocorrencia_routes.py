"""
Rotas de Ocorrencias de Devolucao
=================================

Dashboard e gerenciamento de ocorrencias para Comercial e Logistica.

Criado em: 30/12/2024
"""
import os
from flask import (
    Blueprint, request, jsonify, render_template, send_file, redirect
)
from flask_login import login_required, current_user
from app import db
from app.devolucao.models import (
    NFDevolucao, NFDevolucaoLinha, OcorrenciaDevolucao,
    FreteDevolucao, AnexoOcorrencia, DescarteDevolucao,
    NFDevolucaoNFReferenciada,
    OcorrenciaCategoria, OcorrenciaSubcategoria,
    OcorrenciaResponsavel, OcorrenciaOrigem, OcorrenciaAutorizadoPor,
    OcorrenciaDevolucaoCategoria, OcorrenciaDevolucaoSubcategoria,
    PermissaoCadastroDevolucao
)
from app.monitoramento.models import EntregaMonitorada
from app.carteira.models import CarteiraPrincipal
from app.faturamento.models import FaturamentoProduto
from app.utils.timezone import agora_utc_naive
from sqlalchemy import or_, func
from datetime import datetime, date, timedelta

# Blueprint
ocorrencia_bp = Blueprint('devolucao_ocorrencia', __name__, url_prefix='/ocorrencias')

# CNPJs a excluir da listagem (La Famiglia e Nacom Goya - empresas internas)
CNPJS_EXCLUIDOS = ['18467441', '61724241']


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
    cnpj = request.args.get('cnpj', '').strip()
    transportadora = request.args.get('transportadora', '').strip()
    transportadora_retorno = request.args.get('transportadora_retorno', '').strip()
    data_retorno = request.args.get('data_retorno', '')

    # Query base - busca ocorrências com data de entrega do monitoramento
    query = db.session.query(
        OcorrenciaDevolucao,
        EntregaMonitorada.data_hora_entrega_realizada.label('data_entrega_monitoramento')
    ).join(
        NFDevolucao, OcorrenciaDevolucao.nf_devolucao_id == NFDevolucao.id
    ).outerjoin(
        EntregaMonitorada, EntregaMonitorada.numero_nf == NFDevolucao.numero_nf_venda
    ).filter(
        OcorrenciaDevolucao.ativo == True
    )

    # Excluir CNPJs de empresas internas (La Famiglia e Nacom Goya)
    for cnpj_prefixo in CNPJS_EXCLUIDOS:
        query = query.filter(
            db.or_(
                NFDevolucao.cnpj_emitente.is_(None),
                ~NFDevolucao.cnpj_emitente.like(f'{cnpj_prefixo}%')
            )
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

    # Filtro por CNPJ do emitente (cliente)
    if cnpj:
        # Remove caracteres nao numericos
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        if cnpj_limpo:
            query = query.filter(NFDevolucao.cnpj_emitente.like(f'%{cnpj_limpo}%'))

    # Filtro por transportadora (via EntregaMonitorada das NFs referenciadas)
    if transportadora:
        # Buscar ocorrencias que tenham NF referenciada com essa transportadora
        subquery_nfs_ref = db.session.query(
            NFDevolucaoNFReferenciada.nf_devolucao_id
        ).join(
            EntregaMonitorada, EntregaMonitorada.numero_nf == NFDevolucaoNFReferenciada.numero_nf
        ).filter(
            EntregaMonitorada.transportadora.ilike(f'%{transportadora}%')
        ).distinct()

        query = query.filter(NFDevolucao.id.in_(subquery_nfs_ref))

    # Filtro por transportadora de frete retorno
    if transportadora_retorno:
        subquery_frete_retorno = db.session.query(
            FreteDevolucao.ocorrencia_devolucao_id
        ).filter(
            FreteDevolucao.ativo == True,
            FreteDevolucao.transportadora_nome.ilike(f'%{transportadora_retorno}%')
        ).distinct()

        query = query.filter(OcorrenciaDevolucao.id.in_(subquery_frete_retorno))

    # Filtro por data prevista de retorno
    if data_retorno:
        try:
            dt_retorno = datetime.strptime(data_retorno, '%Y-%m-%d').date()
            subquery_data_retorno = db.session.query(
                FreteDevolucao.ocorrencia_devolucao_id
            ).filter(
                FreteDevolucao.ativo == True,
                FreteDevolucao.data_coleta_prevista == dt_retorno
            ).distinct()

            query = query.filter(OcorrenciaDevolucao.id.in_(subquery_data_retorno))
        except ValueError:
            pass

    # Ordenar pela data de emissao da NFD (data da devolucao)
    query = query.order_by(NFDevolucao.data_emissao.desc().nullslast())

    # Paginacao
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 150, type=int)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Processar tuplas e adicionar dados de NFs referenciadas
    ocorrencias = []
    for item in pagination.items:
        oc, data_entrega = item
        oc.data_entrega_monitoramento = data_entrega

        if oc.nf_devolucao:
            # Buscar NFs referenciadas
            nfs_ref = NFDevolucaoNFReferenciada.query.filter_by(
                nf_devolucao_id=oc.nf_devolucao.id
            ).all()

            # Buscar dados de entrega para cada NF
            dados_entregas = []
            for ref in nfs_ref:
                entrega = EntregaMonitorada.query.filter_by(
                    numero_nf=ref.numero_nf
                ).first()
                dados_entregas.append({
                    'numero_nf': ref.numero_nf,
                    'transportadora': entrega.transportadora if entrega else None,
                    'data_entrega': entrega.data_hora_entrega_realizada if entrega else None
                })

            oc.nfs_referenciadas = nfs_ref
            oc.dados_entregas = dados_entregas
        else:
            oc.nfs_referenciadas = []
            oc.dados_entregas = []

        # Buscar Frete Retorno (último frete ativo)
        frete_retorno = FreteDevolucao.query.filter_by(
            ocorrencia_devolucao_id=oc.id,
            ativo=True
        ).order_by(FreteDevolucao.data_cotacao.desc()).first()

        # Buscar Descarte (se houver)
        descarte = DescarteDevolucao.query.filter_by(
            ocorrencia_devolucao_id=oc.id,
            ativo=True
        ).first()

        # Calcular % descartado (valor_mercadoria / valor_total NFD)
        valor_nfd = float(oc.nf_devolucao.valor_total) if oc.nf_devolucao and oc.nf_devolucao.valor_total else 0
        valor_descarte = float(descarte.valor_mercadoria) if descarte and descarte.valor_mercadoria else 0
        percentual_descarte = (valor_descarte / valor_nfd * 100) if valor_nfd > 0 and valor_descarte > 0 else None

        # Atribuir ao objeto
        oc.frete_retorno = frete_retorno
        oc.descarte = descarte
        oc.percentual_descarte = percentual_descarte

        ocorrencias.append(oc)

    # =====================================================================
    # Enriquecer com raz_social_red (Bloco 1)
    # =====================================================================
    cnpjs_prefixo = set()
    for oc in ocorrencias:
        if oc.nf_devolucao and oc.nf_devolucao.cnpj_emitente:
            cnpjs_prefixo.add(oc.nf_devolucao.cnpj_emitente[:8])

    raz_social_map = {}
    if cnpjs_prefixo:
        for prefixo in cnpjs_prefixo:
            cp = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.cnpj_cpf.like(f'{prefixo}%')
            ).first()
            if cp and cp.raz_social_red:
                raz_social_map[prefixo] = cp.raz_social_red

    for oc in ocorrencias:
        prefixo = oc.nf_devolucao.cnpj_emitente[:8] if oc.nf_devolucao and oc.nf_devolucao.cnpj_emitente else None
        oc.raz_social_red = raz_social_map.get(prefixo) if prefixo else None

    # =====================================================================
    # Enriquecer com Vendedor/Equipe (Bloco 6)
    # =====================================================================
    nfs_para_busca = set()
    cnpjs_para_busca = set()
    for oc in ocorrencias:
        if oc.nfs_referenciadas:
            nfs_para_busca.update(ref.numero_nf for ref in oc.nfs_referenciadas if ref.numero_nf)
        if oc.nf_devolucao and oc.nf_devolucao.cnpj_emitente:
            cnpjs_para_busca.add(oc.nf_devolucao.cnpj_emitente)

    vendedor_por_nf = {}
    if nfs_para_busca:
        fat_results = db.session.query(
            FaturamentoProduto.numero_nf,
            FaturamentoProduto.vendedor,
            FaturamentoProduto.equipe_vendas
        ).filter(
            FaturamentoProduto.numero_nf.in_(nfs_para_busca)
        ).distinct(
            FaturamentoProduto.numero_nf
        ).order_by(
            FaturamentoProduto.numero_nf,
            FaturamentoProduto.data_fatura.desc()
        ).all()
        for r in fat_results:
            vendedor_por_nf[r.numero_nf] = {'vendedor': r.vendedor, 'equipe': r.equipe_vendas}

    vendedor_por_cnpj = {}
    if cnpjs_para_busca:
        fat_cnpj = db.session.query(
            FaturamentoProduto.cnpj_cliente,
            FaturamentoProduto.vendedor,
            FaturamentoProduto.equipe_vendas
        ).filter(
            FaturamentoProduto.cnpj_cliente.in_(cnpjs_para_busca)
        ).distinct(
            FaturamentoProduto.cnpj_cliente
        ).order_by(
            FaturamentoProduto.cnpj_cliente,
            FaturamentoProduto.data_fatura.desc()
        ).all()
        for r in fat_cnpj:
            vendedor_por_cnpj[r.cnpj_cliente] = {'vendedor': r.vendedor, 'equipe': r.equipe_vendas}

    for oc in ocorrencias:
        info = None
        if oc.nfs_referenciadas:
            for ref in oc.nfs_referenciadas:
                if ref.numero_nf in vendedor_por_nf:
                    info = vendedor_por_nf[ref.numero_nf]
                    break
        if not info and oc.nf_devolucao and oc.nf_devolucao.cnpj_emitente:
            info = vendedor_por_cnpj.get(oc.nf_devolucao.cnpj_emitente)
        oc.vendedor_info = info or {}

    # Estatisticas
    stats = {
        'total': OcorrenciaDevolucao.query.filter_by(ativo=True).count(),
        'abertas': OcorrenciaDevolucao.query.filter_by(ativo=True, status='ABERTA').count(),
        'em_analise': OcorrenciaDevolucao.query.filter_by(ativo=True, status='EM_ANALISE').count(),
        'resolvidas': OcorrenciaDevolucao.query.filter_by(ativo=True, status='RESOLVIDA').count(),
    }

    # Buscar transportadoras unicas para o filtro (entrega)
    transportadoras_query = db.session.query(
        EntregaMonitorada.transportadora
    ).join(
        NFDevolucaoNFReferenciada, NFDevolucaoNFReferenciada.numero_nf == EntregaMonitorada.numero_nf
    ).filter(
        EntregaMonitorada.transportadora.isnot(None),
        EntregaMonitorada.transportadora != ''
    ).distinct().order_by(EntregaMonitorada.transportadora).all()

    lista_transportadoras = [t[0] for t in transportadoras_query if t[0]]

    # Buscar transportadoras unicas de frete retorno para o filtro
    transportadoras_retorno_query = db.session.query(
        FreteDevolucao.transportadora_nome
    ).filter(
        FreteDevolucao.ativo == True,
        FreteDevolucao.transportadora_nome.isnot(None),
        FreteDevolucao.transportadora_nome != ''
    ).distinct().order_by(FreteDevolucao.transportadora_nome).all()

    lista_transportadoras_retorno = [t[0] for t in transportadoras_retorno_query if t[0]]

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
            'data_fim': data_fim,
            'cnpj': cnpj,
            'transportadora': transportadora,
            'transportadora_retorno': transportadora_retorno,
            'data_retorno': data_retorno
        },
        opcoes_status=OcorrenciaDevolucao.STATUS_OCORRENCIA,
        opcoes_destino=OcorrenciaDevolucao.DESTINOS,
        opcoes_categoria=OcorrenciaCategoria.query.filter_by(ativo=True).order_by(OcorrenciaCategoria.descricao).all(),
        opcoes_responsavel=OcorrenciaResponsavel.query.filter_by(ativo=True).order_by(OcorrenciaResponsavel.descricao).all(),
        lista_transportadoras=lista_transportadoras,
        lista_transportadoras_retorno=lista_transportadoras_retorno
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

    # Extrair motivo automaticamente se não foi extraído pela IA ainda
    # Verifica se tem info_complementar e se confianca_motivo é None (não foi processado pela IA)
    if nfd and nfd.info_complementar and nfd.confianca_motivo is None:
        try:
            from app.devolucao.services import get_ai_resolver
            ai_service = get_ai_resolver()
            # O método correto é extrair_observacao() que analisa texto e extrai motivo
            resultado = ai_service.extrair_observacao(nfd.info_complementar)
            if resultado and resultado.descricao_motivo:
                nfd.descricao_motivo = resultado.descricao_motivo
                nfd.confianca_motivo = resultado.confianca
                if resultado.motivo_sugerido:
                    nfd.motivo = resultado.motivo_sugerido
                db.session.commit()
        except Exception as e:
            # Log silencioso - não interrompe a página
            import logging
            logging.getLogger(__name__).warning(f"Erro ao extrair motivo automaticamente: {e}")

    # Linhas da NFD (se importada do Odoo)
    linhas = NFDevolucaoLinha.query.filter_by(
        nf_devolucao_id=nfd.id
    ).all() if nfd else []

    # Para NFs revertidas (tipo_documento='NF'), buscar produtos de FaturamentoProduto
    # Esses produtos já são NOSSOS códigos, não precisam de resolução
    produtos_faturamento = []
    if nfd and nfd.tipo_documento == 'NF' and nfd.numero_nf_venda:
        produtos_faturamento = FaturamentoProduto.query.filter_by(
            numero_nf=str(nfd.numero_nf_venda)
        ).all()

    # NFs de venda referenciadas (pode ser N NFs)
    nfs_referenciadas = []
    transportadoras_set = set()  # Para coletar transportadoras únicas
    if nfd:
        refs = NFDevolucaoNFReferenciada.query.filter_by(
            nf_devolucao_id=nfd.id
        ).all()

        for ref in refs:
            # Buscar entrega monitorada vinculada ou por numero da NF
            entrega_ref = None
            if ref.entrega_monitorada_id:
                entrega_ref = db.session.get(EntregaMonitorada,ref.entrega_monitorada_id) if ref.entrega_monitorada_id else None
            elif ref.numero_nf:
                # Buscar por numero da NF
                entrega_ref = EntregaMonitorada.query.filter_by(
                    numero_nf=ref.numero_nf
                ).first()

            # Coletar transportadora
            if entrega_ref and entrega_ref.transportadora:
                transportadoras_set.add(entrega_ref.transportadora)

            nfs_referenciadas.append({
                'id': ref.id,
                'numero_nf': ref.numero_nf,
                'serie_nf': ref.serie_nf,
                'chave_nf': ref.chave_nf,
                'origem': ref.origem,
                'entrega_id': entrega_ref.id if entrega_ref else None,
                'cliente': entrega_ref.cliente if entrega_ref else None,
                'transportadora': entrega_ref.transportadora if entrega_ref else None,
                'data_entrega': entrega_ref.data_hora_entrega_realizada if entrega_ref else None
            })

    # Lista de transportadoras únicas
    transportadoras = list(transportadoras_set)

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

    # =====================================================================
    # Enriquecer com raz_social_red (Bloco 1)
    # =====================================================================
    raz_social_red = None
    if nfd and nfd.cnpj_emitente:
        prefixo = nfd.cnpj_emitente[:8]
        cp = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.cnpj_cpf.like(f'{prefixo}%')
        ).first()
        if cp and cp.raz_social_red:
            raz_social_red = cp.raz_social_red

    # =====================================================================
    # Enriquecer com Vendedor/Equipe (Bloco 7)
    # =====================================================================
    vendedor_info = {}
    # Tentar por NFs referenciadas
    if nfs_referenciadas:
        for nf_ref in nfs_referenciadas:
            if nf_ref.get('numero_nf'):
                fat = FaturamentoProduto.query.filter_by(
                    numero_nf=nf_ref['numero_nf']
                ).first()
                if fat and fat.vendedor:
                    vendedor_info = {'vendedor': fat.vendedor, 'equipe': fat.equipe_vendas}
                    break
    # Fallback por CNPJ
    if not vendedor_info and nfd and nfd.cnpj_emitente:
        fat = FaturamentoProduto.query.filter_by(
            cnpj_cliente=nfd.cnpj_emitente
        ).order_by(FaturamentoProduto.data_fatura.desc()).first()
        if fat and fat.vendedor:
            vendedor_info = {'vendedor': fat.vendedor, 'equipe': fat.equipe_vendas}

    return render_template(
        'devolucao/ocorrencias/detalhe.html',
        ocorrencia=ocorrencia,
        nfd=nfd,
        entrega=entrega,
        linhas=linhas,
        produtos_faturamento=produtos_faturamento,  # Produtos de NF revertida
        nfs_referenciadas=nfs_referenciadas,
        transportadoras=transportadoras,
        fretes=fretes,
        descartes=descartes,
        anexos=anexos,
        raz_social_red=raz_social_red,
        vendedor_info=vendedor_info,
        opcoes_status=OcorrenciaDevolucao.STATUS_OCORRENCIA,
        opcoes_destino=OcorrenciaDevolucao.DESTINOS,
        opcoes_localizacao=OcorrenciaDevolucao.LOCALIZACOES,
        opcoes_categoria=OcorrenciaCategoria.query.filter_by(ativo=True).order_by(OcorrenciaCategoria.descricao).all(),
        opcoes_subcategoria=OcorrenciaSubcategoria.query.filter_by(ativo=True).order_by(OcorrenciaSubcategoria.descricao).all(),
        opcoes_responsavel=OcorrenciaResponsavel.query.filter_by(ativo=True).order_by(OcorrenciaResponsavel.descricao).all(),
        opcoes_origem=OcorrenciaOrigem.query.filter_by(ativo=True).order_by(OcorrenciaOrigem.descricao).all(),
        opcoes_autorizado=OcorrenciaAutorizadoPor.query.filter_by(ativo=True).order_by(OcorrenciaAutorizadoPor.descricao).all(),
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
        ocorrencia = db.session.get(OcorrenciaDevolucao,ocorrencia_id) if ocorrencia_id else None
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
                transp = db.session.get(Transportadora,data['transportadora_retorno_id']) if data['transportadora_retorno_id'] else None
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
        ocorrencia.atualizado_em = agora_utc_naive()

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

    Body JSON (novo formato com IDs normalizados):
    {
        "categoria_ids": [1, 3],
        "subcategoria_ids": [2, 5],
        "responsavel_id": 4,
        "origem_id": 2,
        "autorizado_por_id": 1,
        "descricao_comercial": "...",
        "status": "EM_ANALISE",
        "momento_devolucao": "ATO_ENTREGA",
        "desfecho": "..."
    }
    """
    try:
        ocorrencia = db.session.get(OcorrenciaDevolucao, ocorrencia_id) if ocorrencia_id else None
        if not ocorrencia:
            return jsonify({'sucesso': False, 'erro': 'Ocorrencia nao encontrada'}), 404

        data = request.get_json()

        # =====================================================================
        # Categorias (N:M via junction table)
        # =====================================================================
        if 'categoria_ids' in data:
            cat_ids = [int(cid) for cid in data['categoria_ids'] if cid]

            # Delete existing
            OcorrenciaDevolucaoCategoria.query.filter_by(
                ocorrencia_devolucao_id=ocorrencia_id
            ).delete()

            # Insert new
            for cid in cat_ids:
                db.session.add(OcorrenciaDevolucaoCategoria(
                    ocorrencia_devolucao_id=ocorrencia_id,
                    categoria_id=cid
                ))

            # Sync com coluna varchar cache (primeira categoria para filtros)
            if cat_ids:
                primeira_cat = db.session.get(OcorrenciaCategoria, cat_ids[0])
                ocorrencia.categoria = primeira_cat.codigo if primeira_cat else None
            else:
                ocorrencia.categoria = None

        # =====================================================================
        # Subcategorias (N:M via junction table)
        # =====================================================================
        if 'subcategoria_ids' in data:
            sub_ids = [int(sid) for sid in data['subcategoria_ids'] if sid]

            # Delete existing
            OcorrenciaDevolucaoSubcategoria.query.filter_by(
                ocorrencia_devolucao_id=ocorrencia_id
            ).delete()

            # Insert new
            for sid in sub_ids:
                db.session.add(OcorrenciaDevolucaoSubcategoria(
                    ocorrencia_devolucao_id=ocorrencia_id,
                    subcategoria_id=sid
                ))

            # Sync com coluna varchar cache
            if sub_ids:
                primeira_sub = db.session.get(OcorrenciaSubcategoria, sub_ids[0])
                ocorrencia.subcategoria = primeira_sub.codigo if primeira_sub else None
            else:
                ocorrencia.subcategoria = None

        # =====================================================================
        # Responsavel (FK direto)
        # =====================================================================
        if 'responsavel_id' in data:
            rid = data['responsavel_id']
            ocorrencia.responsavel_id = int(rid) if rid else None

            # Sync com coluna varchar cache
            if rid:
                resp_ref = db.session.get(OcorrenciaResponsavel, int(rid))
                ocorrencia.responsavel = resp_ref.codigo if resp_ref else None
            else:
                ocorrencia.responsavel = None

        # =====================================================================
        # Origem (FK direto)
        # =====================================================================
        if 'origem_id' in data:
            oid = data['origem_id']
            ocorrencia.origem_id = int(oid) if oid else None

            # Sync com coluna varchar cache
            if oid:
                orig_ref = db.session.get(OcorrenciaOrigem, int(oid))
                ocorrencia.origem = orig_ref.codigo if orig_ref else None
            else:
                ocorrencia.origem = None

        # =====================================================================
        # Autorizado Por (FK direto)
        # =====================================================================
        if 'autorizado_por_id' in data:
            aid = data['autorizado_por_id']
            ocorrencia.autorizado_por_id = int(aid) if aid else None

            # Sync com coluna varchar cache
            if aid:
                aut_ref = db.session.get(OcorrenciaAutorizadoPor, int(aid))
                ocorrencia.autorizado_por = aut_ref.descricao if aut_ref else None
            else:
                ocorrencia.autorizado_por = None

        # =====================================================================
        # Campos texto simples (mantidos como antes)
        # =====================================================================
        if 'descricao_comercial' in data:
            ocorrencia.descricao_comercial = data['descricao_comercial']

        if 'status' in data:
            status_anterior = ocorrencia.status
            ocorrencia.status = data['status']

            # Marcar data de resolucao se mudou para RESOLVIDA
            # Usar data_entrada da NFD (data real de entrada no Odoo) quando disponivel
            if data['status'] == 'RESOLVIDA' and status_anterior != 'RESOLVIDA':
                nfd = ocorrencia.nf_devolucao
                if nfd and nfd.data_entrada:
                    # Converter date para datetime naive se necessario
                    if isinstance(nfd.data_entrada, date) and not isinstance(nfd.data_entrada, datetime):
                        ocorrencia.data_resolucao = datetime.combine(nfd.data_entrada, datetime.min.time())
                    else:
                        ocorrencia.data_resolucao = nfd.data_entrada
                else:
                    ocorrencia.data_resolucao = agora_utc_naive()  # fallback
                ocorrencia.resolvido_por = current_user.nome if hasattr(current_user, 'nome') else current_user.username

            # Marcar data de acao comercial se mudou para EM_ANALISE
            if data['status'] == 'EM_ANALISE' and status_anterior == 'ABERTA':
                ocorrencia.data_acao_comercial = agora_utc_naive()

        if 'momento_devolucao' in data:
            ocorrencia.momento_devolucao = data['momento_devolucao']

        if 'desfecho' in data:
            ocorrencia.desfecho = data['desfecho']

        # Auditoria
        ocorrencia.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else current_user.username
        ocorrencia.atualizado_em = agora_utc_naive()

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
        ocorrencia = db.session.get(OcorrenciaDevolucao,ocorrencia_id) if ocorrencia_id else None
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
    Upload de anexo(s) para ocorrencia — suporta multiplos arquivos

    Form-data:
    - arquivo: Arquivo(s) a ser(em) enviado(s) (aceita multiple)
    - tipo: EMAIL, FOTO, DOCUMENTO (opcional, auto-detectado se nao informado)
    - descricao: Descricao do anexo (opcional)
    """
    from flask import current_app
    from app.utils.file_storage import FileStorage
    from werkzeug.utils import secure_filename

    # Mapa de extensao → tipo para auto-deteccao
    EXTENSAO_TIPO_MAP = {
        'pdf': 'DOCUMENTO', 'doc': 'DOCUMENTO', 'docx': 'DOCUMENTO', 'txt': 'DOCUMENTO',
        'msg': 'EMAIL', 'eml': 'EMAIL',
        'jpg': 'FOTO', 'jpeg': 'FOTO', 'png': 'FOTO', 'gif': 'FOTO', 'webp': 'FOTO', 'jfif': 'FOTO',
        'xlsx': 'PLANILHA', 'xls': 'PLANILHA', 'csv': 'PLANILHA',
    }

    try:
        ocorrencia = db.session.get(OcorrenciaDevolucao, ocorrencia_id) if ocorrencia_id else None
        if not ocorrencia:
            return jsonify({'sucesso': False, 'erro': 'Ocorrencia nao encontrada'}), 404

        # Suportar multiplos arquivos via getlist
        arquivos = request.files.getlist('arquivo')
        if not arquivos or not arquivos[0].filename:
            return jsonify({'sucesso': False, 'erro': 'Nenhum arquivo enviado'}), 400

        descricao = request.form.get('descricao', '').strip()
        tipo_form = request.form.get('tipo', '').upper().strip()

        # Validar tipo se informado
        tipos_validos = ['EMAIL', 'FOTO', 'DOCUMENTO', 'PLANILHA', 'OUTROS']

        # Extensoes permitidas (union de todos os tipos)
        todas_extensoes = ['pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'csv',
                           'jpg', 'jpeg', 'jfif', 'png', 'gif', 'webp',
                           'msg', 'eml', 'zip']

        storage = FileStorage()
        folder = f"devolucoes/ocorrencias/{ocorrencia_id}"

        anexos_criados = []
        erros = []

        for arquivo in arquivos:
            if not arquivo.filename:
                continue

            try:
                # Auto-detectar tipo pela extensao
                ext = arquivo.filename.rsplit('.', 1)[-1].lower() if '.' in arquivo.filename else ''
                if tipo_form and tipo_form in tipos_validos:
                    tipo = tipo_form
                else:
                    tipo = EXTENSAO_TIPO_MAP.get(ext, 'OUTROS')

                caminho = storage.save_file(
                    arquivo,
                    folder,
                    allowed_extensions=todas_extensoes
                )

                if not caminho:
                    erros.append(f'{arquivo.filename}: Erro ao salvar')
                    continue

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
                anexos_criados.append({
                    'nome': arquivo.filename,
                    'tipo': tipo
                })

            except ValueError as e:
                erros.append(f'{arquivo.filename}: {str(e)}')

        db.session.commit()

        total = len(anexos_criados)
        mensagem = f'{total} anexo{"s" if total != 1 else ""} enviado{"s" if total != 1 else ""} com sucesso!'
        if erros:
            mensagem += f' ({len(erros)} erro{"s" if len(erros) != 1 else ""})'

        return jsonify({
            'sucesso': True,
            'mensagem': mensagem,
            'anexos': anexos_criados,
            'erros': erros
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
            # Gerar URL assinada do S3 com download forçado
            url = storage.get_download_url(anexo.caminho_s3, anexo.nome_original)
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


@ocorrencia_bp.route('/api/<int:ocorrencia_id>/anexos/download-all')
@login_required
def api_download_all_anexos(ocorrencia_id):
    """
    Baixa todos os anexos de uma ocorrencia como ZIP
    """
    from flask import current_app
    from app.utils.file_storage import FileStorage
    import io
    import zipfile

    try:
        ocorrencia = db.session.get(OcorrenciaDevolucao, ocorrencia_id)
        if not ocorrencia:
            return jsonify({'sucesso': False, 'erro': 'Ocorrencia nao encontrada'}), 404

        anexos = AnexoOcorrencia.query.filter_by(
            ocorrencia_devolucao_id=ocorrencia_id,
            ativo=True
        ).all()

        if not anexos:
            return jsonify({'sucesso': False, 'erro': 'Nenhum anexo encontrado'}), 404

        storage = FileStorage()
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            nomes_usados = {}
            for anexo in anexos:
                try:
                    file_bytes = storage.download_file(anexo.caminho_s3)
                    if file_bytes:
                        # Evitar nomes duplicados
                        nome = anexo.nome_original or anexo.nome_arquivo
                        if nome in nomes_usados:
                            nomes_usados[nome] += 1
                            base, ext = os.path.splitext(nome)
                            nome = f"{base}_{nomes_usados[nome]}{ext}"
                        else:
                            nomes_usados[nome] = 0
                        zf.writestr(nome, file_bytes)
                except Exception as e:
                    current_app.logger.warning(f"Erro ao baixar anexo {anexo.id}: {e}")

        zip_buffer.seek(0)
        numero_oc = ocorrencia.numero_ocorrencia or f'OC_{ocorrencia_id}'

        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{numero_oc}_anexos.zip'
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao baixar todos os anexos: {str(e)}")
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
        nfd = db.session.get(NFDevolucao,nfd_id) if nfd_id else None
        if not nfd:
            return jsonify({'sucesso': False, 'erro': 'NFD nao encontrada'}), 404

        # Se tem path do S3, baixar de la
        if nfd.nfd_xml_path:
            storage = FileStorage()

            if storage.use_s3:
                filename = nfd.nfd_xml_nome_arquivo or f'NFD_{nfd.numero_nfd}.xml'
                url = storage.get_download_url(nfd.nfd_xml_path, filename)
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
        nfd = db.session.get(NFDevolucao,nfd_id) if nfd_id else None
        if not nfd:
            return jsonify({'sucesso': False, 'erro': 'NFD nao encontrada'}), 404

        # Se tem path do S3, baixar de la
        if nfd.nfd_pdf_path:
            storage = FileStorage()

            if storage.use_s3:
                filename = nfd.nfd_pdf_nome_arquivo or f'NFD_{nfd.numero_nfd}.pdf'
                url = storage.get_download_url(nfd.nfd_pdf_path, filename)
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
# API Comparar Produtos NFD com NFs de Venda
# =============================================================================

@ocorrencia_bp.route('/api/<int:ocorrencia_id>/comparar-nf-venda')
@login_required
def api_comparar_nf_venda(ocorrencia_id):
    """
    Compara produtos da NFD com os produtos das NFs de venda referenciadas.

    Retorna:
    - produtos: Lista com qtd_vendida, qtd_devolvida, preco_venda, preco_devolvido
    - nfs_nao_encontradas: NFs referenciadas que não estão no sistema
    """
    try:
        from app.faturamento.models import FaturamentoProduto

        ocorrencia = db.session.get(OcorrenciaDevolucao,ocorrencia_id) if ocorrencia_id else None
        if not ocorrencia:
            return jsonify({'sucesso': False, 'erro': 'Ocorrencia nao encontrada'}), 404
        nfd = ocorrencia.nf_devolucao

        if not nfd:
            return jsonify({'sucesso': False, 'erro': 'NFD não encontrada'})

        # Buscar NFs de venda referenciadas
        nfs_ref = NFDevolucaoNFReferenciada.query.filter_by(
            nf_devolucao_id=nfd.id
        ).all()

        if not nfs_ref:
            return jsonify({
                'sucesso': True,
                'produtos': [],
                'nfs_nao_encontradas': [],
                'mensagem': 'Nenhuma NF de venda referenciada'
            })

        # Coletar números das NFs
        numeros_nf_ref = [ref.numero_nf for ref in nfs_ref if ref.numero_nf]

        # Buscar produtos nas NFs de venda (FaturamentoProduto)
        produtos_venda = {}
        nfs_encontradas = set()
        nfs_nao_encontradas = []

        for num_nf in numeros_nf_ref:
            # Buscar na tabela de faturamento
            produtos_nf = FaturamentoProduto.query.filter_by(
                numero_nf=str(num_nf)
            ).all()

            if produtos_nf:
                nfs_encontradas.add(num_nf)
                for prod in produtos_nf:
                    codigo = prod.cod_produto
                    if codigo not in produtos_venda:
                        produtos_venda[codigo] = {
                            'codigo': codigo,
                            'descricao': prod.nome_produto,
                            'qtd_vendida': 0,
                            'preco_venda': float(prod.preco_produto_faturado) if prod.preco_produto_faturado else 0
                        }
                    produtos_venda[codigo]['qtd_vendida'] += float(prod.qtd_produto_faturado or 0)
            else:
                if num_nf not in nfs_encontradas:
                    nfs_nao_encontradas.append(str(num_nf))

        # Buscar produtos devolvidos (linhas da NFD)
        from app.devolucao.models import NFDevolucaoLinha
        linhas_nfd = NFDevolucaoLinha.query.filter_by(
            nf_devolucao_id=nfd.id
        ).all()

        # Mapear produtos devolvidos
        produtos_devolvidos = {}
        for linha in linhas_nfd:
            # Usar codigo interno se resolvido, senão codigo do cliente
            codigo = linha.codigo_produto_interno or linha.codigo_produto_cliente
            if not codigo:
                continue

            if codigo not in produtos_devolvidos:
                produtos_devolvidos[codigo] = {
                    'codigo': codigo,
                    'descricao': linha.descricao_produto_interno or linha.descricao_produto_cliente,
                    'qtd_devolvida': 0,
                    'preco_devolvido': 0
                }

            # Usar quantidade convertida se disponível
            qtd = float(linha.quantidade_convertida or linha.quantidade or 0)
            produtos_devolvidos[codigo]['qtd_devolvida'] += qtd

            # Calcular preço devolvido (valor unitário convertido)
            if linha.valor_unitario and linha.qtd_por_caixa:
                preco_conv = float(linha.valor_unitario) * float(linha.qtd_por_caixa)
                produtos_devolvidos[codigo]['preco_devolvido'] = preco_conv
            elif linha.valor_unitario:
                produtos_devolvidos[codigo]['preco_devolvido'] = float(linha.valor_unitario)

        # Combinar vendas e devoluções
        todos_codigos = set(produtos_venda.keys()) | set(produtos_devolvidos.keys())
        resultado = []

        for codigo in todos_codigos:
            venda = produtos_venda.get(codigo, {})
            devol = produtos_devolvidos.get(codigo, {})

            resultado.append({
                'codigo': codigo,
                'descricao': venda.get('descricao') or devol.get('descricao', '-'),
                'qtd_vendida': venda.get('qtd_vendida', 0),
                'qtd_devolvida': devol.get('qtd_devolvida', 0),
                'preco_venda': venda.get('preco_venda', 0),
                'preco_devolvido': devol.get('preco_devolvido', 0)
            })

        # Ordenar por código
        resultado.sort(key=lambda x: x['codigo'])

        return jsonify({
            'sucesso': True,
            'produtos': resultado,
            'nfs_nao_encontradas': list(set(nfs_nao_encontradas)),
            'total_nfs_ref': len(numeros_nf_ref),
            'total_nfs_encontradas': len(nfs_encontradas)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =============================================================================
# Registrar blueprint
# =============================================================================

def init_app(app):
    """Registra o blueprint no aplicativo Flask"""
    from app.devolucao import devolucao_bp
    devolucao_bp.register_blueprint(ocorrencia_bp)
