"""
Rotas de Cotacao Comercial CarVia — Fluxo proativo
"""

import logging
from datetime import datetime
from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)

# Tolerancia para comparacao de totais (arredondamento Numeric/float)
_TOL_KG = 0.01
_TOL_VAL = 0.01


def _agregar_totais_nfs_cotacao(cotacao_id):
    """Agrega peso_bruto / valor_total / quantidade_volumes das NFs ja vinculadas
    a CarviaPedidoItem desta cotacao.

    Tambem calcula peso cubado agregado das NFs via
    `EmbarqueCarViaService.calcular_cubado_por_modelos` (para MOTO) — para
    CARGA_GERAL o cubado agregado retorna 0 (NFs de CARGA_GERAL nao tem
    cubado proprio; usar peso_bruto como proxy na validacao).

    Returns:
        dict com:
          - peso_bruto: float (kg)
          - peso_cubado: float (kg) — 0 para CARGA_GERAL
          - valor_total: float (R$)
          - quantidade_volumes: int
          - nfs_vinculadas: set[str] — numeros de NF ja vinculadas (para skip
            de re-anexacao)
    """
    from app.carvia.models import (
        CarviaNf, CarviaNfVeiculo, CarviaPedido, CarviaPedidoItem,
    )
    from app.carvia.services.documentos.embarque_carvia_service import (
        EmbarqueCarViaService,
    )

    nfs_vinculadas_nums = {
        n for (n,) in db.session.query(
            CarviaPedidoItem.numero_nf
        ).join(
            CarviaPedido, CarviaPedidoItem.pedido_id == CarviaPedido.id
        ).filter(
            CarviaPedido.cotacao_id == cotacao_id,
            CarviaPedidoItem.numero_nf.isnot(None),
            CarviaPedidoItem.numero_nf != '',
        ).distinct().all()
    }

    if not nfs_vinculadas_nums:
        return {
            'peso_bruto': 0.0,
            'peso_cubado': 0.0,
            'valor_total': 0.0,
            'quantidade_volumes': 0,
            'nfs_vinculadas': set(),
        }

    # Agregados diretos das CarviaNfs
    nfs_rows = CarviaNf.query.filter(
        CarviaNf.numero_nf.in_(list(nfs_vinculadas_nums))
    ).all()
    peso_bruto = sum(float(n.peso_bruto or 0) for n in nfs_rows)
    valor_total = sum(float(n.valor_total or 0) for n in nfs_rows)
    volumes = sum(int(n.quantidade_volumes or 0) for n in nfs_rows)

    # Cubado agregado: somar modelos de CarviaNfVeiculo das NFs vinculadas
    modelos = [
        v.modelo for v in CarviaNfVeiculo.query.filter(
            CarviaNfVeiculo.nf_id.in_([n.id for n in nfs_rows])
        ).all()
    ]
    peso_cubado = EmbarqueCarViaService.calcular_cubado_por_modelos(
        cotacao_id, modelos
    ) if modelos else 0.0

    return {
        'peso_bruto': peso_bruto,
        'peso_cubado': peso_cubado,
        'valor_total': valor_total,
        'quantidade_volumes': volumes,
        'nfs_vinculadas': nfs_vinculadas_nums,
    }


def register_cotacao_v2_routes(bp):

    # ==================== LISTAR ====================

    @bp.route('/cotacoes') # type: ignore
    @login_required
    def listar_cotacoes_v2(): # type: ignore
        """Lista cotacoes comerciais"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service

        status = request.args.get('status')
        cliente_id = request.args.get('cliente_id', type=int)
        alerta = request.args.get('alerta')

        cotacoes = CotacaoV2Service.listar_cotacoes(
            status=status,
            cliente_id=cliente_id,
            alerta=alerta,
        )

        # Contadores por status
        from app.carvia.models import CarviaCotacao
        from sqlalchemy import func
        contadores = dict(
            db.session.query(
                CarviaCotacao.status,
                func.count(CarviaCotacao.id)
            ).group_by(CarviaCotacao.status).all()
        )

        # Contador de cotacoes com alerta ativo
        contadores_alerta = CarviaCotacao.query.filter_by(
            alerta_saida_sem_nf=True
        ).count()

        return render_template(
            'carvia/cotacoes/listar.html',
            cotacoes=cotacoes,
            status_filtro=status,
            cliente_id_filtro=cliente_id,
            alerta_filtro=alerta,
            contadores=contadores,
            contadores_alerta=contadores_alerta,
        )

    # ==================== PARSEAR NF PARA PRE-PREENCHIMENTO ====================

    @bp.route('/api/cotacoes/parsear-nf', methods=['POST']) # type: ignore
    @login_required
    def api_parsear_nf(): # type: ignore
        """Parseia PDF/XML de NF e retorna dados para pre-preencher cotacao.

        Nao salva nada no banco — apenas extrai e retorna os dados.
        A NF sera criada apenas quando a cotacao for salva.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        arquivo = request.files.get('arquivo')
        if not arquivo or not arquivo.filename:
            return jsonify({'erro': 'Arquivo (PDF ou XML) obrigatorio.'}), 400

        nome_arquivo = arquivo.filename
        ext = nome_arquivo.lower().rsplit('.', 1)[-1] if '.' in nome_arquivo else ''
        if ext not in ('xml', 'pdf'):
            return jsonify({'erro': f'Extensao .{ext} nao suportada. Use PDF ou XML.'}), 400

        try:
            conteudo = arquivo.read()

            if ext == 'xml':
                from app.carvia.services.parsers.nfe_xml_parser import NFeXMLParser
                parser = NFeXMLParser(conteudo)
                if not parser.is_valid():
                    return jsonify({'erro': 'XML invalido.'}), 400
                if not parser.is_nfe():
                    return jsonify({'erro': 'XML nao e NF-e (modelo 55).'}), 400
                dados = parser.get_todas_informacoes()
            else:
                from app.carvia.services.parsers.danfe_pdf_parser import DanfePDFParser
                parser = DanfePDFParser(pdf_bytes=conteudo)
                if not parser.is_valid():
                    return jsonify({'erro': 'PDF invalido ou sem texto extraivel.'}), 400
                dados = parser.get_todas_informacoes()

            # Retornar dados para o JS preencher o form
            return jsonify({
                'sucesso': True,
                'nf': {
                    'numero_nf': dados.get('numero_nf'),
                    'chave_acesso': dados.get('chave_acesso_nf'),
                    'data_emissao': str(dados.get('data_emissao') or ''),
                    'cnpj_emitente': dados.get('cnpj_emitente'),
                    'nome_emitente': dados.get('nome_emitente'),
                    'cnpj_destinatario': dados.get('cnpj_destinatario'),
                    'nome_destinatario': dados.get('nome_destinatario'),
                    'uf_destinatario': dados.get('uf_destinatario'),
                    'cidade_destinatario': dados.get('cidade_destinatario'),
                    'valor_total': dados.get('valor_total'),
                    'peso_bruto': dados.get('peso_bruto'),
                    'quantidade_volumes': dados.get('quantidade_volumes'),
                    'tipo_fonte': dados.get('tipo_fonte'),
                    'arquivo_nome': nome_arquivo,
                },
                'itens': [
                    {
                        'codigo': it.get('codigo_produto'),
                        'descricao': it.get('descricao'),
                        'ncm': it.get('ncm'),
                        'unidade': it.get('unidade'),
                        'quantidade': it.get('quantidade'),
                        'valor_unitario': it.get('valor_unitario'),
                        'valor_total': it.get('valor_total_item'),
                    }
                    for it in dados.get('itens', [])
                ],
                'veiculos': [
                    {
                        'chassi': v.get('chassi'),
                        'cor': v.get('cor'),
                        'modelo': v.get('modelo'),
                        'numero_motor': v.get('numero_motor'),
                        'ano_modelo': v.get('ano_modelo'),
                    }
                    for v in dados.get('veiculos', [])
                ],
            })

        except Exception as e:
            logger.error("Erro ao parsear NF: %s", e)
            return jsonify({'erro': f'Erro ao parsear: {e}'}), 500

    # ==================== SETUP NF: PARSEAR + VERIFICAR CLIENTE/ENDERECOS ====================

    @bp.route('/api/cotacoes/setup-nf', methods=['POST']) # type: ignore
    @login_required
    def api_setup_nf(): # type: ignore
        """Parseia NF + verifica/cria cliente e enderecos.

        Form multipart: arquivo=<file>, nome_cliente=<str>(opcional),
          origem_fisico_json=<json>(opcional), destino_fisico_json=<json>(opcional)

        Fluxo:
        1. Parseia PDF/XML da NF
        2. Identifica CNPJ emitente (origem) e destinatario (destino)
        3. Busca cliente existente ou cria novo
        4. Busca/cria enderecos ORIGEM e DESTINO
        5. Retorna tudo para pre-preencher a cotacao
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.clientes.cliente_service import CarviaClienteService
        from app.carvia.models import CarviaClienteEndereco

        arquivo = request.files.get('arquivo')
        if not arquivo or not arquivo.filename:
            return jsonify({'erro': 'Arquivo (PDF ou XML) obrigatorio.'}), 400

        nome_arquivo = arquivo.filename
        ext = nome_arquivo.lower().rsplit('.', 1)[-1] if '.' in nome_arquivo else ''
        if ext not in ('xml', 'pdf'):
            return jsonify({'erro': f'Extensao .{ext} nao suportada.'}), 400

        try:
            conteudo = arquivo.read()

            # 1. Parsear
            if ext == 'xml':
                from app.carvia.services.parsers.nfe_xml_parser import NFeXMLParser
                parser = NFeXMLParser(conteudo)
                if not parser.is_valid() or not parser.is_nfe():
                    return jsonify({'erro': 'XML invalido ou nao e NF-e.'}), 400
                dados = parser.get_todas_informacoes()
            else:
                from app.carvia.services.parsers.danfe_pdf_parser import DanfePDFParser
                parser = DanfePDFParser(pdf_bytes=conteudo)
                if not parser.is_valid():
                    return jsonify({'erro': 'PDF invalido.'}), 400
                dados = parser.get_todas_informacoes()

            cnpj_emitente = dados.get('cnpj_emitente') or ''
            cnpj_dest = dados.get('cnpj_destinatario') or ''
            import re as _re
            cnpj_emit_limpo = _re.sub(r'\D', '', cnpj_emitente)
            cnpj_dest_limpo = _re.sub(r'\D', '', cnpj_dest)

            # 1b. Verificar cotacao existente para esta NF (mesma logica de api_setup_nf_existente)
            aviso_cotacao_existente = False
            cotacao_existente_info = None
            numero_nf_parsed = dados.get('numero_nf') or ''
            if numero_nf_parsed and cnpj_emit_limpo:
                from app.carvia.models import (
                    CarviaCotacao as _CotCheck, CarviaPedido as _PedCheck,
                    CarviaPedidoItem as _PedItemCheck,
                )
                _dup_ped = db.session.query(_PedCheck).join(
                    _PedItemCheck, _PedItemCheck.pedido_id == _PedCheck.id
                ).join(
                    _CotCheck, _PedCheck.cotacao_id == _CotCheck.id
                ).join(
                    CarviaClienteEndereco,
                    _CotCheck.endereco_origem_id == CarviaClienteEndereco.id,
                ).filter(
                    _PedItemCheck.numero_nf == str(numero_nf_parsed),
                    CarviaClienteEndereco.cnpj == cnpj_emit_limpo,
                    _CotCheck.status != 'CANCELADO',
                ).first()
                if _dup_ped and _dup_ped.cotacao:
                    aviso_cotacao_existente = True
                    cotacao_existente_info = {
                        'cotacao_id': _dup_ped.cotacao.id,
                        'numero_cotacao': _dup_ped.cotacao.numero_cotacao,
                        'status': _dup_ped.cotacao.status,
                    }

            # 2. Verificar cliente existente: PRIMEIRO pelo CNPJ destinatario
            #    (endereco tipo=DESTINO), depois pelo CNPJ emitente (endereco
            #    tipo=ORIGEM). Filtrar por tipo evita falso-match quando o mesmo
            #    CNPJ aparece em enderecos de papeis diferentes.
            cliente_id = None
            cliente_nome = None
            if cnpj_dest_limpo:
                enderecos_dest = CarviaClienteEndereco.query.filter(
                    CarviaClienteEndereco.cnpj == cnpj_dest_limpo,
                    CarviaClienteEndereco.tipo == 'DESTINO',
                    CarviaClienteEndereco.cliente_id.isnot(None),
                ).all()
                for end in enderecos_dest:
                    if end.cliente:
                        cliente_id = end.cliente_id
                        cliente_nome = end.cliente.nome_comercial
                        break

            if not cliente_id and cnpj_emit_limpo:
                enderecos_orig = CarviaClienteEndereco.query.filter(
                    CarviaClienteEndereco.cnpj == cnpj_emit_limpo,
                    CarviaClienteEndereco.tipo == 'ORIGEM',
                    CarviaClienteEndereco.cliente_id.isnot(None),
                ).all()
                for end in enderecos_orig:
                    if end.cliente:
                        cliente_id = end.cliente_id
                        cliente_nome = end.cliente.nome_comercial
                        break

            # 3. Verificar enderecos ORIGEM e DESTINO
            endereco_origem_id = None
            endereco_destino_id = None
            if cliente_id:
                if cnpj_dest_limpo:
                    dest = CarviaClienteEndereco.query.filter_by(
                        cliente_id=cliente_id, cnpj=cnpj_dest_limpo, tipo='DESTINO'
                    ).first()
                    if dest:
                        endereco_destino_id = dest.id

            # Buscar origem global (origens sao sempre compartilhadas, cliente_id=NULL)
            if cnpj_emit_limpo:
                orig_global = CarviaClienteEndereco.query.filter(
                    CarviaClienteEndereco.cnpj == cnpj_emit_limpo,
                    CarviaClienteEndereco.tipo == 'ORIGEM',
                    CarviaClienteEndereco.cliente_id.is_(None),
                ).first()
                if orig_global:
                    endereco_origem_id = orig_global.id

            # 4. Detectar tipo material (MOTO se NCM comeca com 8711)
            itens = dados.get('itens', [])
            eh_moto = any(
                (it.get('ncm') or '').startswith('8711')
                for it in itens
            )

            # 5. Consultar Receita para CNPJs (se sao CNPJ, nao CPF)
            receita_emitente = None
            receita_emitente_erro = None
            receita_dest = None
            receita_dest_erro = None
            if len(cnpj_emit_limpo) == 14:
                try:
                    receita_emitente, erro = CarviaClienteService.buscar_cnpj_receita(
                        cnpj_emit_limpo
                    )
                    if erro:
                        receita_emitente_erro = erro
                        logger.warning("ReceitaWS emitente %s: %s", cnpj_emit_limpo, erro)
                except Exception as e:
                    receita_emitente_erro = f'Erro ao consultar Receita: {e}'
                    logger.warning("ReceitaWS emitente %s exception: %s", cnpj_emit_limpo, e)
            elif cnpj_emit_limpo:
                receita_emitente_erro = 'CPF detectado (Receita so consulta CNPJ)'

            if len(cnpj_dest_limpo) == 14:
                try:
                    receita_dest, erro = CarviaClienteService.buscar_cnpj_receita(
                        cnpj_dest_limpo
                    )
                    if erro:
                        receita_dest_erro = erro
                        logger.warning("ReceitaWS dest %s: %s", cnpj_dest_limpo, erro)
                except Exception as e:
                    receita_dest_erro = f'Erro ao consultar Receita: {e}'
                    logger.warning("ReceitaWS dest %s exception: %s", cnpj_dest_limpo, e)
            elif cnpj_dest_limpo:
                receita_dest_erro = 'CPF detectado (Receita so consulta CNPJ)'

            # 6. Reconhecimento automatico de motos nos itens da NF
            motos_reconhecidas = []
            if eh_moto:
                try:
                    from app.carvia.services.pricing.moto_recognition_service import MotoRecognitionService
                    from app.carvia.models import CarviaModeloMoto
                    modelos_db = CarviaModeloMoto.query.filter_by(ativo=True).all()
                    modelos_by_nome = {m.nome: m for m in modelos_db}
                    for it in itens:
                        nome_match = MotoRecognitionService._match_descricao(
                            it.get('descricao', ''), modelos_db, it.get('codigo_produto')
                        )
                        modelo = modelos_by_nome.get(nome_match) if nome_match else None
                        motos_reconhecidas.append({
                            'descricao': it.get('descricao'),
                            'modelo_moto_id': modelo.id if modelo else None,
                            'modelo_nome': modelo.nome if modelo else None,
                            'quantidade': it.get('quantidade', 1),
                            'valor_unitario': it.get('valor_unitario'),
                            'valor_total': it.get('valor_total_item'),
                            'match': nome_match,
                        })
                except Exception as e:
                    logger.warning("Erro no reconhecimento de motos: %s", e)

            return jsonify({
                'sucesso': True,
                'nf': {
                    'numero_nf': dados.get('numero_nf'),
                    'chave_acesso': dados.get('chave_acesso_nf'),
                    'data_emissao': str(dados.get('data_emissao') or ''),
                    'cnpj_emitente': cnpj_emit_limpo,
                    'nome_emitente': dados.get('nome_emitente'),
                    'uf_emitente': dados.get('uf_emitente'),
                    'cidade_emitente': dados.get('cidade_emitente'),
                    'cnpj_destinatario': cnpj_dest_limpo,
                    'nome_destinatario': dados.get('nome_destinatario'),
                    'uf_destinatario': dados.get('uf_destinatario'),
                    'cidade_destinatario': dados.get('cidade_destinatario'),
                    'valor_total': dados.get('valor_total'),
                    'peso_bruto': dados.get('peso_bruto'),
                    'quantidade_volumes': dados.get('quantidade_volumes'),
                    'tipo_fonte': dados.get('tipo_fonte'),
                    'arquivo_nome': nome_arquivo,
                },
                'itens': [
                    {
                        'codigo': it.get('codigo_produto'),
                        'descricao': it.get('descricao'),
                        'ncm': it.get('ncm'),
                        'unidade': it.get('unidade'),
                        'quantidade': it.get('quantidade'),
                        'valor_unitario': it.get('valor_unitario'),
                        'valor_total': it.get('valor_total_item'),
                    }
                    for it in itens
                ],
                'veiculos': [
                    {
                        'chassi': v.get('chassi'),
                        'cor': v.get('cor'),
                        'modelo': v.get('modelo'),
                        'numero_motor': v.get('numero_motor'),
                        'ano_modelo': v.get('ano_modelo'),
                    }
                    for v in dados.get('veiculos', [])
                ],
                'tipo_material': 'MOTO' if eh_moto else 'CARGA_GERAL',
                'cliente': {
                    'id': cliente_id,
                    'nome': cliente_nome,
                    'existe': cliente_id is not None,
                },
                'enderecos': {
                    'origem_id': endereco_origem_id,
                    'origem_existe': endereco_origem_id is not None,
                    'destino_id': endereco_destino_id,
                    'destino_existe': endereco_destino_id is not None,
                },
                'receita_emitente': receita_emitente,
                'receita_emitente_erro': receita_emitente_erro,
                'receita_destinatario': receita_dest,
                'receita_destinatario_erro': receita_dest_erro,
                'motos_reconhecidas': motos_reconhecidas,
                'aviso_cotacao_existente': aviso_cotacao_existente,
                'cotacao_existente_info': cotacao_existente_info,
            })

        except Exception as e:
            logger.error("Erro no setup-nf: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== SETUP NF EXISTENTE (A PARTIR DO BANCO) ====================

    @bp.route('/api/cotacoes/setup-nf-existente/<int:nf_id>') # type: ignore
    @login_required
    def api_setup_nf_existente(nf_id): # type: ignore
        """Carrega NF ja importada do banco e retorna dados para pre-preencher cotacao.

        Mesma estrutura de retorno que api_setup_nf, mas sem parsear arquivo —
        usa dados ja existentes no banco. Permite reusar o wizard JS do criar.html.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        import re as _re
        from app.carvia.models import (
            CarviaNf, CarviaPedido, CarviaPedidoItem,
            CarviaClienteEndereco,
        )
        from app.carvia.services.clientes.cliente_service import CarviaClienteService

        nf = db.session.get(CarviaNf, nf_id)
        if not nf:
            return jsonify({'erro': 'NF nao encontrada.'}), 404

        if nf.status == 'CANCELADA':
            return jsonify({'erro': 'NF cancelada nao pode gerar cotacao.'}), 400

        cnpj_emit_limpo = _re.sub(r'\D', '', nf.cnpj_emitente or '')
        cnpj_dest_limpo = _re.sub(r'\D', '', nf.cnpj_destinatario or '')

        if not cnpj_emit_limpo:
            return jsonify({'erro': 'NF sem CNPJ emitente — nao e possivel identificar o cliente.'}), 400

        try:
            # 1. Verificar cotacao existente via pedido
            #    Escopo: mesmo numero_nf E cotacao cujo endereco_origem tem o mesmo CNPJ
            aviso_cotacao_existente = False
            cotacao_existente_info = None

            from app.carvia.models import CarviaCotacao
            existing_pedido = db.session.query(CarviaPedido).join(
                CarviaPedidoItem, CarviaPedidoItem.pedido_id == CarviaPedido.id
            ).join(
                CarviaCotacao, CarviaPedido.cotacao_id == CarviaCotacao.id
            ).join(
                CarviaClienteEndereco,
                CarviaCotacao.endereco_origem_id == CarviaClienteEndereco.id,
            ).filter(
                CarviaPedidoItem.numero_nf == str(nf.numero_nf),
                CarviaClienteEndereco.cnpj == cnpj_emit_limpo,
                CarviaCotacao.status != 'CANCELADO',
            ).first()

            if existing_pedido and existing_pedido.cotacao:
                aviso_cotacao_existente = True
                cotacao_existente_info = {
                    'cotacao_id': existing_pedido.cotacao.id,
                    'numero_cotacao': existing_pedido.cotacao.numero_cotacao,
                    'status': existing_pedido.cotacao.status,
                }

            # 2. Buscar cliente existente: PRIMEIRO pelo CNPJ destinatario
            #    (endereco tipo=DESTINO), depois pelo CNPJ emitente (endereco
            #    tipo=ORIGEM). Mesma regra do api_setup_nf.
            cliente_id = None
            cliente_nome = None
            if cnpj_dest_limpo:
                enderecos_dest = CarviaClienteEndereco.query.filter(
                    CarviaClienteEndereco.cnpj == cnpj_dest_limpo,
                    CarviaClienteEndereco.tipo == 'DESTINO',
                    CarviaClienteEndereco.cliente_id.isnot(None),
                    CarviaClienteEndereco.ativo == True,
                ).all()
                for end in enderecos_dest:
                    if end.cliente:
                        cliente_id = end.cliente_id
                        cliente_nome = end.cliente.nome_comercial
                        break

            if not cliente_id and cnpj_emit_limpo:
                enderecos_orig = CarviaClienteEndereco.query.filter(
                    CarviaClienteEndereco.cnpj == cnpj_emit_limpo,
                    CarviaClienteEndereco.tipo == 'ORIGEM',
                    CarviaClienteEndereco.cliente_id.isnot(None),
                    CarviaClienteEndereco.ativo == True,
                ).all()
                for end in enderecos_orig:
                    if end.cliente:
                        cliente_id = end.cliente_id
                        cliente_nome = end.cliente.nome_comercial
                        break

            # 3. Verificar enderecos ORIGEM e DESTINO
            endereco_origem_id = None
            endereco_destino_id = None

            # Buscar origem global (origens sao sempre compartilhadas, cliente_id=NULL)
            if cnpj_emit_limpo:
                orig_global = CarviaClienteEndereco.query.filter(
                    CarviaClienteEndereco.cnpj == cnpj_emit_limpo,
                    CarviaClienteEndereco.tipo == 'ORIGEM',
                    CarviaClienteEndereco.cliente_id.is_(None),
                    CarviaClienteEndereco.ativo == True,
                ).first()
                if orig_global:
                    endereco_origem_id = orig_global.id

            # Buscar destino do cliente
            if cliente_id and cnpj_dest_limpo:
                dest = CarviaClienteEndereco.query.filter_by(
                    cliente_id=cliente_id, cnpj=cnpj_dest_limpo,
                    tipo='DESTINO', ativo=True
                ).first()
                if dest:
                    endereco_destino_id = dest.id

            # 4. Detectar tipo material (MOTO se NCM comeca com 8711)
            itens_db = nf.itens.all()
            eh_moto = any(
                (it.ncm or '').startswith('8711')
                for it in itens_db
            )

            # 5. Reconhecimento automatico de motos
            motos_reconhecidas = []
            if eh_moto:
                try:
                    from app.carvia.services.pricing.moto_recognition_service import MotoRecognitionService
                    from app.carvia.models import CarviaModeloMoto
                    modelos_db = CarviaModeloMoto.query.filter_by(ativo=True).all()
                    modelos_by_nome = {m.nome: m for m in modelos_db}
                    for it in itens_db:
                        nome_match = MotoRecognitionService._match_descricao(
                            it.descricao or '', modelos_db, it.codigo_produto
                        )
                        modelo = modelos_by_nome.get(nome_match) if nome_match else None
                        motos_reconhecidas.append({
                            'descricao': it.descricao,
                            'modelo_moto_id': modelo.id if modelo else None,
                            'modelo_nome': modelo.nome if modelo else None,
                            'quantidade': float(it.quantidade or 1),
                            'valor_unitario': float(it.valor_unitario) if it.valor_unitario else None,
                            'valor_total': float(it.valor_total_item) if it.valor_total_item else None,
                            'match': nome_match,
                        })
                except Exception as e:
                    logger.warning("Erro no reconhecimento de motos (NF existente): %s", e)

            # 6. Consultar Receita para CNPJs (se sao CNPJ, nao CPF)
            receita_emitente = None
            receita_emitente_erro = None
            receita_dest = None
            receita_dest_erro = None
            if len(cnpj_emit_limpo) == 14:
                try:
                    receita_emitente, erro = CarviaClienteService.buscar_cnpj_receita(
                        cnpj_emit_limpo
                    )
                    if erro:
                        receita_emitente_erro = erro
                        logger.warning("ReceitaWS emitente %s: %s", cnpj_emit_limpo, erro)
                except Exception as e:
                    receita_emitente_erro = f'Erro ao consultar Receita: {e}'
                    logger.warning("ReceitaWS emitente %s exception: %s", cnpj_emit_limpo, e)
            elif cnpj_emit_limpo:
                receita_emitente_erro = 'CPF detectado (Receita so consulta CNPJ)'

            if len(cnpj_dest_limpo) == 14:
                try:
                    receita_dest, erro = CarviaClienteService.buscar_cnpj_receita(
                        cnpj_dest_limpo
                    )
                    if erro:
                        receita_dest_erro = erro
                        logger.warning("ReceitaWS dest %s: %s", cnpj_dest_limpo, erro)
                except Exception as e:
                    receita_dest_erro = f'Erro ao consultar Receita: {e}'
                    logger.warning("ReceitaWS dest %s exception: %s", cnpj_dest_limpo, e)
            elif cnpj_dest_limpo:
                receita_dest_erro = 'CPF detectado (Receita so consulta CNPJ)'

            # 7. Serializar veiculos
            veiculos_db = nf.veiculos.all()

            # 8. Info CTe CarVia (para criacao tardia)
            operacoes_nf = nf.operacoes.all()
            cte_valor_total = sum(float(op.cte_valor or 0) for op in operacoes_nf)
            cte_info = {
                'tem_cte': bool(operacoes_nf),
                'cte_valor_total': round(cte_valor_total, 2),
                'qtd_ctes': len(operacoes_nf),
            }

            return jsonify({
                'sucesso': True,
                'nf_id': nf.id,
                'aviso_cotacao_existente': aviso_cotacao_existente,
                'cotacao_existente_info': cotacao_existente_info,
                'cte_info': cte_info,
                'nf': {
                    'numero_nf': nf.numero_nf,
                    'chave_acesso': nf.chave_acesso_nf,
                    'data_emissao': str(nf.data_emissao or ''),
                    'cnpj_emitente': cnpj_emit_limpo,
                    'nome_emitente': nf.nome_emitente,
                    'uf_emitente': nf.uf_emitente,
                    'cidade_emitente': nf.cidade_emitente,
                    'cnpj_destinatario': cnpj_dest_limpo,
                    'nome_destinatario': nf.nome_destinatario,
                    'uf_destinatario': nf.uf_destinatario,
                    'cidade_destinatario': nf.cidade_destinatario,
                    'valor_total': float(nf.valor_total) if nf.valor_total is not None else None,
                    'peso_bruto': float(nf.peso_bruto) if nf.peso_bruto is not None else None,
                    'quantidade_volumes': nf.quantidade_volumes,
                    'tipo_fonte': nf.tipo_fonte,
                    'arquivo_nome': nf.arquivo_nome_original,
                },
                'itens': [
                    {
                        'codigo': it.codigo_produto,
                        'descricao': it.descricao,
                        'ncm': it.ncm,
                        'unidade': it.unidade,
                        'quantidade': float(it.quantidade) if it.quantidade else None,
                        'valor_unitario': float(it.valor_unitario) if it.valor_unitario else None,
                        'valor_total': float(it.valor_total_item) if it.valor_total_item else None,
                    }
                    for it in itens_db
                ],
                'veiculos': [
                    {
                        'chassi': v.chassi,
                        'cor': v.cor,
                        'modelo': v.modelo,
                        'numero_motor': v.numero_motor,
                        'ano_modelo': v.ano,
                    }
                    for v in veiculos_db
                ],
                'tipo_material': 'MOTO' if eh_moto else 'CARGA_GERAL',
                'cliente': {
                    'id': cliente_id,
                    'nome': cliente_nome,
                    'existe': cliente_id is not None,
                },
                'enderecos': {
                    'origem_id': endereco_origem_id,
                    'origem_existe': endereco_origem_id is not None,
                    'destino_id': endereco_destino_id,
                    'destino_existe': endereco_destino_id is not None,
                },
                'receita_emitente': receita_emitente,
                'receita_emitente_erro': receita_emitente_erro,
                'receita_destinatario': receita_dest,
                'receita_destinatario_erro': receita_dest_erro,
                'motos_reconhecidas': motos_reconhecidas,
            })

        except Exception as e:
            logger.error("Erro no setup-nf-existente (nf_id=%s): %s", nf_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== CRIAR CLIENTE+ENDERECOS RAPIDO ====================

    @bp.route('/api/cotacoes/criar-cliente-rapido', methods=['POST']) # type: ignore
    @login_required
    def api_criar_cliente_rapido(): # type: ignore
        """Cria cliente + endereco origem + endereco destino em uma unica chamada.

        Body JSON:
        {
          "nome_comercial": "...",
          "origem": { "cnpj": "...", "razao_social": "...", "fisico": {...} },
          "destino": { "cnpj": "...", "razao_social": "...", "fisico": {...} }
        }
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.clientes.cliente_service import CarviaClienteService

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        nome = (data.get('nome_comercial') or '').strip()
        if not nome:
            return jsonify({'erro': 'Nome comercial obrigatorio.'}), 400

        try:
            # Modo 1: cliente existente selecionado pelo usuario no wizard
            cliente_id_existente = data.get('cliente_id_existente')
            if cliente_id_existente:
                from app.carvia.models import CarviaCliente
                cliente = db.session.get(CarviaCliente, cliente_id_existente)
                if not cliente:
                    return jsonify({'erro': f'Cliente ID {cliente_id_existente} nao encontrado.'}), 404
                logger.info(
                    "api_criar_cliente_rapido: usando cliente existente selecionado (id=%s, nome=%s).",
                    cliente.id, cliente.nome_comercial,
                )
            else:
                # Guard: verificar se cliente ja existe pelo CNPJ do emitente
                cliente_existente = None
                orig_data_guard = data.get('origem', {})
                cnpj_orig = orig_data_guard.get('cnpj', '')
                if cnpj_orig:
                    import re as _re
                    cnpj_limpo = _re.sub(r'\D', '', cnpj_orig)
                    enderecos_existentes = CarviaClienteService.buscar_enderecos_por_cnpj(cnpj_limpo)
                    for end in enderecos_existentes:
                        if end.cliente_id:
                            from app.carvia.models import CarviaCliente
                            cliente_existente = db.session.get(CarviaCliente, end.cliente_id)
                            break

                if cliente_existente:
                    # Ajuste 1: retornar cliente existente sem criar novo ou sobrescrever nome
                    cliente = cliente_existente
                    logger.info(
                        "api_criar_cliente_rapido: cliente ja existe (id=%s, nome=%s), nao criando novo.",
                        cliente.id, cliente.nome_comercial,
                    )
                else:
                    # Criar cliente novo
                    cliente, erro = CarviaClienteService.criar_cliente(
                        nome_comercial=nome,
                        criado_por=current_user.email,
                    )
                    if erro:
                        return jsonify({'erro': erro}), 400

            orig_data = data.get('origem', {})

            resultado = {
                'cliente_id': cliente.id,
                'nome_comercial': cliente.nome_comercial,
            }

            # 2. Criar/reutilizar endereco ORIGEM (global — compartilhado)
            if orig_data.get('cnpj'):
                fisico = orig_data.get('fisico', {})
                # Origens sao globais (Ajuste 2)
                endereco, erro_end = CarviaClienteService.adicionar_origem_global(
                    cnpj=orig_data['cnpj'],
                    criado_por=current_user.email,
                    razao_social=orig_data.get('razao_social'),
                    dados_receita=orig_data.get('receita', {}),
                    dados_fisico=fisico if fisico else None,
                )
                if endereco:
                    resultado['endereco_origem_id'] = endereco.id
                elif erro_end:
                    logger.warning("Erro endereco origem global: %s", erro_end)

            # 3. Criar endereco DESTINO (por cliente)
            dest_data = data.get('destino', {})
            if dest_data.get('provisorio'):
                # Ajuste 5: destino provisorio sem CNPJ
                fisico = dest_data.get('fisico', {})
                endereco, erro_end = CarviaClienteService.adicionar_destino_provisorio(
                    cliente_id=cliente.id,
                    criado_por=current_user.email,
                    razao_social=dest_data.get('razao_social'),
                    dados_fisico=fisico if fisico else None,
                )
                if endereco:
                    resultado['endereco_destino_id'] = endereco.id
                elif erro_end:
                    logger.warning("Erro endereco destino provisorio: %s", erro_end)
            elif dest_data.get('cnpj'):
                fisico = dest_data.get('fisico', {})
                endereco, erro_end = CarviaClienteService.adicionar_endereco(
                    cliente_id=cliente.id,
                    cnpj=dest_data['cnpj'],
                    tipo='DESTINO',
                    criado_por=current_user.email,
                    razao_social=dest_data.get('razao_social'),
                    dados_receita=dest_data.get('receita', {}),
                    dados_fisico=fisico if fisico else None,
                )
                if endereco:
                    resultado['endereco_destino_id'] = endereco.id
                elif erro_end:
                    logger.warning("Erro endereco destino: %s", erro_end)

            db.session.commit()

            return jsonify({'sucesso': True, **resultado})

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar cliente rapido: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== CRIAR ====================

    @bp.route('/cotacoes/nova', methods=['GET', 'POST']) # type: ignore
    @login_required
    def criar_cotacao_v2(): # type: ignore
        """Cria nova cotacao comercial"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.clientes.cliente_service import CarviaClienteService

        def _ctx_criar():
            """Contexto compartilhado GET + erro POST."""
            from app.carvia.models import CarviaModeloMoto
            import json as json_lib
            modelos_raw = CarviaModeloMoto.query.filter_by(ativo=True).order_by(
                CarviaModeloMoto.nome.asc()
            ).all()
            from app.veiculos.models import Veiculo
            veiculos_direta = Veiculo.query.order_by(Veiculo.peso_maximo.asc()).all()
            return {
                'clientes': CarviaClienteService.listar_clientes(apenas_ativos=True),
                'modelos_moto_json': json_lib.dumps([{
                    'id': m.id,
                    'nome': m.nome,
                    'peso_cubado': round(
                        float(m.comprimento) * float(m.largura) * float(m.altura)
                        * max(float(m.cubagem_minima or 300), 300) / 1_000_000, 3
                    ) if m.comprimento and m.largura and m.altura else None,
                } for m in modelos_raw]),
                'veiculos_direta': veiculos_direta,
            }

        if request.method == 'GET':
            nf_id_param = request.args.get('nf_id', type=int)
            criacao_tardia_param = bool(request.args.get('criacao_tardia', type=int, default=0))
            return render_template(
                'carvia/cotacoes/criar.html',
                nf_id_param=nf_id_param,
                criacao_tardia=criacao_tardia_param,
                **_ctx_criar(),
            )

        from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service

        # Preservar nf_id para re-render em caso de erro
        nf_id_param = request.form.get('nf_id_existente', type=int)

        try:
            # Parse datas
            data_exp = request.form.get('data_expedicao')
            data_ag = request.form.get('data_agenda')

            # Resolver endereco_destino_id (com fallback para destino manual)
            endereco_destino_id = int(request.form.get('endereco_destino_id', 0))
            if endereco_destino_id == 0:
                # Fallback server-side: criar provisorio a partir de campos manuais
                man_cidade = (request.form.get('man_dest_cidade') or '').strip()
                man_uf = (request.form.get('man_dest_uf') or '').strip().upper()
                if man_cidade and man_uf:
                    cliente_id_form = int(request.form.get('cliente_id', 0))
                    endereco_prov, erro_prov = CarviaClienteService.adicionar_destino_provisorio(
                        cliente_id=cliente_id_form,
                        criado_por=current_user.email,
                        razao_social=(request.form.get('man_dest_razao') or '').strip() or None,
                        dados_fisico={
                            'cidade': man_cidade,
                            'uf': man_uf,
                            'cep': (request.form.get('man_dest_cep') or '').strip() or None,
                            'logradouro': (request.form.get('man_dest_logradouro') or '').strip() or None,
                            'numero': (request.form.get('man_dest_numero') or '').strip() or None,
                            'bairro': (request.form.get('man_dest_bairro') or '').strip() or None,
                        }
                    )
                    if erro_prov:
                        flash(erro_prov, 'danger')
                        return render_template(
                            'carvia/cotacoes/criar.html',
                            nf_id_param=nf_id_param,
                            **_ctx_criar(),
                        )
                    endereco_destino_id = endereco_prov.id
                else:
                    flash('Selecione um destino ou preencha Cidade e UF manualmente.', 'danger')
                    return render_template(
                        'carvia/cotacoes/criar.html',
                        nf_id_param=nf_id_param,
                        **_ctx_criar(),
                    )

            # Guard: verificar NF duplicada antes de criar cotacao
            nf_dados_guard = request.form.get('nf_dados_json', '').strip()
            if nf_dados_guard:
                try:
                    import json as _json_guard
                    _parsed_guard = _json_guard.loads(nf_dados_guard)
                    _nfs_guard = _parsed_guard if isinstance(_parsed_guard, list) else [_parsed_guard]
                except Exception:
                    _nfs_guard = []

                for _nf_g in _nfs_guard:
                    _nf_db_id_g = _nf_g.get('nf_db_id') or _nf_g.get('nf_id')
                    _nf_info_g = _nf_g.get('nf', {})
                    _numero_nf_g = _nf_info_g.get('numero_nf') or ''
                    _cnpj_emit_g = (_nf_info_g.get('cnpj_emitente') or '').replace('.', '').replace('/', '').replace('-', '')

                    if _nf_db_id_g:
                        from app.carvia.models import CarviaNf as _NfGuard
                        _nf_obj_g = db.session.get(_NfGuard, int(_nf_db_id_g))
                        if _nf_obj_g:
                            _numero_nf_g = str(_nf_obj_g.numero_nf)
                            _cnpj_emit_g = (_nf_obj_g.cnpj_emitente or '').replace('.', '').replace('/', '').replace('-', '')

                    if _numero_nf_g and _cnpj_emit_g:
                        from app.carvia.models import (
                            CarviaCotacao as _CotGuard, CarviaPedido as _PedGuard,
                            CarviaPedidoItem as _PedItemGuard, CarviaClienteEndereco as _EndGuard,
                        )
                        _dup = db.session.query(_PedGuard).join(
                            _PedItemGuard, _PedItemGuard.pedido_id == _PedGuard.id
                        ).join(
                            _CotGuard, _PedGuard.cotacao_id == _CotGuard.id
                        ).join(
                            _EndGuard, _CotGuard.endereco_origem_id == _EndGuard.id,
                        ).filter(
                            _PedItemGuard.numero_nf == _numero_nf_g,
                            _EndGuard.cnpj == _cnpj_emit_g,
                            _CotGuard.status != 'CANCELADO',
                        ).first()

                        if _dup and _dup.cotacao:
                            flash(
                                f'NF {_numero_nf_g} ja possui cotacao '
                                f'{_dup.cotacao.numero_cotacao} ({_dup.cotacao.status}). '
                                f'Acesse a cotacao existente.',
                                'danger',
                            )
                            return render_template(
                                'carvia/cotacoes/criar.html',
                                nf_id_param=nf_id_param,
                                **_ctx_criar(),
                            )

            cotacao, erro = CotacaoV2Service.criar_cotacao(
                cliente_id=int(request.form.get('cliente_id', 0)),
                endereco_origem_id=int(request.form.get('endereco_origem_id', 0)),
                endereco_destino_id=endereco_destino_id,
                tipo_material=request.form.get('tipo_material', 'CARGA_GERAL'),
                criado_por=current_user.email,
                peso=request.form.get('peso', type=float),
                valor_mercadoria=request.form.get('valor_mercadoria', type=float),
                volumes=request.form.get('volumes', type=int),
                dimensao_c=request.form.get('dimensao_c', type=float),
                dimensao_l=request.form.get('dimensao_l', type=float),
                dimensao_a=request.form.get('dimensao_a', type=float),
                data_expedicao=datetime.strptime(data_exp, '%Y-%m-%d').date() if data_exp else None,
                data_agenda=datetime.strptime(data_ag, '%Y-%m-%d').date() if data_ag else None,
                observacoes=request.form.get('observacoes'),
                # Condicao de pagamento e responsavel do frete
                condicao_pagamento=request.form.get('condicao_pagamento') or None,
                prazo_dias=request.form.get('prazo_dias', type=int),
                responsavel_frete=request.form.get('responsavel_frete') or None,
                percentual_remetente=request.form.get('percentual_remetente', type=float),
                percentual_destinatario=request.form.get('percentual_destinatario', type=float),
            )

            if erro:
                flash(erro, 'danger')
                return render_template(
                    'carvia/cotacoes/criar.html',
                    nf_id_param=nf_id_param,
                    **_ctx_criar(),
                )

            # Criacao tardia: pricing do CTe existente
            is_criacao_tardia = request.form.get('criacao_tardia') == '1'

            # tipo_carga + veiculo (DIRETA only)
            # Criacao tardia: tipo_carga nasce vazio (forcar preenchimento)
            tipo_carga_raw = request.form.get('tipo_carga', '')
            if not is_criacao_tardia:
                tipo_carga = tipo_carga_raw or 'FRACIONADA'
            else:
                tipo_carga = tipo_carga_raw if tipo_carga_raw in ('DIRETA', 'FRACIONADA') else None
            if tipo_carga in ('DIRETA', 'FRACIONADA'):
                cotacao.tipo_carga = tipo_carga
            veiculo_id_form = request.form.get('veiculo_id', type=int)
            if veiculo_id_form and tipo_carga == 'DIRETA':
                cotacao.veiculo_id = veiculo_id_form

            # Adicionar motos (se tipo MOTO)
            if cotacao.tipo_material == 'MOTO':
                import json as json_lib
                motos_raw = request.form.get('motos_json', '[]')
                try:
                    motos_data = json_lib.loads(motos_raw)
                except Exception:
                    motos_data = []

                for moto in motos_data:
                    _, moto_erro = CotacaoV2Service.adicionar_moto(
                        cotacao_id=cotacao.id,
                        modelo_moto_id=int(moto.get('modelo_moto_id', 0)),
                        quantidade=int(moto.get('quantidade', 0)),
                        valor_unitario=float(moto['valor_unitario']) if moto.get('valor_unitario') else None,
                    )
                    if moto_erro:
                        logger.warning("Erro ao adicionar moto na cotacao %s: %s", cotacao.id, moto_erro)

            db.session.flush()

            if is_criacao_tardia and nf_id_param:
                # Criacao tardia: pricing do CTe existente (backend determina valor)
                from decimal import Decimal as _Decimal
                from app.carvia.models import CarviaNf as _CarviaNf
                nf_tardia = db.session.get(_CarviaNf, nf_id_param) if nf_id_param else None
                if nf_tardia:
                    ops_nf = nf_tardia.operacoes.all()
                    cte_valor = sum(_Decimal(str(op.cte_valor or 0)) for op in ops_nf)
                    if cte_valor > 0:
                        cotacao.criacao_tardia = True
                        cotacao.valor_tabela = cte_valor
                        cotacao.valor_descontado = cte_valor
                        cotacao.valor_final_aprovado = cte_valor
                        cotacao.percentual_desconto = _Decimal('0')
                        cotacao.dentro_tabela = True
                        logger.info(
                            "Cotacao %s criada como tardia (CTe valor=%s, NF=%s)",
                            cotacao.id, cte_valor, nf_id_param,
                        )
                    else:
                        logger.warning(
                            "Criacao tardia sem CTe valor para NF %s, prosseguindo sem pricing",
                            nf_id_param,
                        )
            else:
                # Auto-cotar apos criacao (fluxo normal)
                try:
                    CotacaoV2Service.calcular_preco(cotacao.id)
                except Exception as e_price:
                    logger.warning("Auto-cotacao falhou para %s: %s", cotacao.id, e_price)

            # Criar 1 pedido por NF — suporta array de NFs (multi-NF)
            nf_dados_raw = request.form.get('nf_dados_json', '').strip()
            nfs_list = []

            if nf_dados_raw:
                try:
                    import json as json_lib
                    parsed = json_lib.loads(nf_dados_raw)
                    # Suportar array (multi-NF) ou objeto unico (legado)
                    if isinstance(parsed, list):
                        nfs_list = parsed
                    elif isinstance(parsed, dict):
                        nfs_list = [parsed]
                except Exception:
                    nfs_list = []

            if nfs_list:
                from app.carvia.models import (
                    CarviaNf, CarviaNfItem, CarviaNfVeiculo,
                    CarviaPedido, CarviaPedidoItem,
                )
                from app.utils.timezone import agora_utc_naive as _agora

                origem = cotacao.endereco_origem
                filial = 'RJ' if origem and origem.fisico_uf == 'RJ' else 'SP'
                tipo_sep = 'ESTOQUE' if filial == 'SP' else 'CROSSDOCK'

                for nf_entry in nfs_list:
                    try:
                        nf_db_id = nf_entry.get('nf_db_id') or nf_entry.get('nf_id')
                        nf_info = nf_entry.get('nf', {})
                        nf_itens = nf_entry.get('itens', [])
                        nf_veiculos = nf_entry.get('veiculos', [])

                        # Resolver ou criar CarviaNf
                        nf_obj = None
                        if nf_db_id:
                            # PATH A: NF ja existe no banco
                            nf_obj = db.session.get(CarviaNf, int(nf_db_id))
                            if nf_obj and nf_obj.status == 'CANCELADA':
                                logger.warning("NF %s cancelada, pulando", nf_db_id)
                                continue
                            if not nf_obj:
                                logger.warning("NF %s nao encontrada, pulando", nf_db_id)
                                continue
                            # Usar itens reais do banco se disponiveis
                            itens_db = nf_obj.itens.all()
                            veiculos_db = nf_obj.veiculos.all()
                        else:
                            # PATH B: NF nova via JSON (upload)
                            data_emissao = nf_info.get('data_emissao')
                            if data_emissao and isinstance(data_emissao, str) and data_emissao != '':
                                try:
                                    data_emissao = datetime.strptime(data_emissao[:10], '%Y-%m-%d').date()
                                except (ValueError, TypeError):
                                    data_emissao = None
                            else:
                                data_emissao = None

                            chave = nf_info.get('chave_acesso')
                            if chave:
                                nf_obj = CarviaNf.query.filter_by(chave_acesso_nf=chave).first()

                            if not nf_obj:
                                nf_obj = CarviaNf(
                                    numero_nf=nf_info.get('numero_nf') or '0',
                                    serie_nf=nf_info.get('serie_nf'),
                                    chave_acesso_nf=chave,
                                    data_emissao=data_emissao,
                                    cnpj_emitente=nf_info.get('cnpj_emitente') or 'DESCONHECIDO',
                                    nome_emitente=nf_info.get('nome_emitente'),
                                    uf_emitente=nf_info.get('uf_emitente'),
                                    cidade_emitente=nf_info.get('cidade_emitente'),
                                    cnpj_destinatario=nf_info.get('cnpj_destinatario'),
                                    nome_destinatario=nf_info.get('nome_destinatario'),
                                    uf_destinatario=nf_info.get('uf_destinatario'),
                                    cidade_destinatario=nf_info.get('cidade_destinatario'),
                                    valor_total=nf_info.get('valor_total'),
                                    peso_bruto=nf_info.get('peso_bruto'),
                                    quantidade_volumes=nf_info.get('quantidade_volumes'),
                                    tipo_fonte=nf_info.get('tipo_fonte', 'MANUAL'),
                                    arquivo_nome_original=nf_info.get('arquivo_nome'),
                                    criado_por=current_user.email,
                                    criado_em=_agora(),
                                )
                                db.session.add(nf_obj)
                                db.session.flush()

                                for it in nf_itens:
                                    db.session.add(CarviaNfItem(
                                        nf_id=nf_obj.id,
                                        codigo_produto=it.get('codigo'),
                                        descricao=it.get('descricao'),
                                        ncm=it.get('ncm'),
                                        unidade=it.get('unidade'),
                                        quantidade=it.get('quantidade'),
                                        valor_unitario=it.get('valor_unitario'),
                                        valor_total_item=it.get('valor_total'),
                                    ))

                            # Criar veiculos — dedup por chassi
                            for v_idx, v in enumerate(nf_veiculos):
                                chassi = (v.get('chassi') or '').strip()
                                if chassi:
                                    existente = CarviaNfVeiculo.query.filter_by(chassi=chassi).first()
                                    if not existente:
                                        item_ref = nf_itens[min(v_idx, len(nf_itens) - 1)] if nf_itens else {}
                                        db.session.add(CarviaNfVeiculo(
                                            nf_id=nf_obj.id,
                                            chassi=chassi,
                                            modelo=v.get('modelo') or item_ref.get('descricao'),
                                            cor=v.get('cor'),
                                            valor=(
                                                v.get('valor')
                                                or item_ref.get('valor_unitario')
                                                or item_ref.get('valor_total')
                                            ),
                                            ano=v.get('ano_modelo'),
                                            numero_motor=v.get('numero_motor'),
                                        ))

                            itens_db = None
                            veiculos_db = None

                        # Criar pedido para esta NF
                        numero_nf = nf_obj.numero_nf or '0'

                        pedido = CarviaPedido(
                            numero_pedido=CarviaPedido.gerar_numero_pedido(cotacao.id),
                            cotacao_id=cotacao.id,
                            filial=filial,
                            tipo_separacao=tipo_sep,
                            criado_por=current_user.email,
                            criado_em=_agora(),
                            atualizado_em=_agora(),
                        )
                        db.session.add(pedido)
                        db.session.flush()

                        # Criar itens — preferir dados do banco (PATH A), senao JSON (PATH B)
                        if itens_db:
                            vlist = veiculos_db or []
                            for idx, it in enumerate(itens_db):
                                veiculo = vlist[idx] if idx < len(vlist) else None
                                cor = veiculo.cor if veiculo else None
                                db.session.add(CarviaPedidoItem(
                                    pedido_id=pedido.id,
                                    descricao=it.descricao or 'Produto',
                                    cor=cor,
                                    quantidade=int(it.quantidade or 1),
                                    valor_unitario=float(it.valor_unitario) if it.valor_unitario is not None else None,
                                    valor_total=float(it.valor_total_item) if it.valor_total_item is not None else None,
                                    numero_nf=numero_nf,
                                ))
                        elif nf_itens:
                            for idx, it in enumerate(nf_itens):
                                veiculo = nf_veiculos[idx] if idx < len(nf_veiculos) else None
                                cor = veiculo.get('cor') if veiculo else None
                                db.session.add(CarviaPedidoItem(
                                    pedido_id=pedido.id,
                                    descricao=it.get('descricao') or 'Produto',
                                    cor=cor,
                                    quantidade=int(it.get('quantidade') or 1),
                                    valor_unitario=it.get('valor_unitario'),
                                    valor_total=it.get('valor_total'),
                                    numero_nf=numero_nf,
                                ))
                        else:
                            # Fallback: NF sem itens detalhados
                            db.session.add(CarviaPedidoItem(
                                pedido_id=pedido.id,
                                descricao=nf_obj.nome_emitente or 'Produto',
                                quantidade=1,
                                valor_total=float(nf_obj.valor_total) if nf_obj.valor_total is not None else None,
                                numero_nf=numero_nf,
                            ))

                        logger.info(
                            "Pedido %s criado (NF %s) na cotacao %s",
                            pedido.numero_pedido, numero_nf, cotacao.numero_cotacao,
                        )

                    except Exception as e_nf:
                        logger.warning("Erro ao criar pedido para NF na cotacao %s: %s", cotacao.id, e_nf)

            db.session.commit()
            n_pedidos = len(nfs_list)
            msg_pedidos = f' com {n_pedidos} pedido(s)' if n_pedidos else ''
            flash(f'Cotacao {cotacao.numero_cotacao} criada{msg_pedidos}.', 'success')
            return redirect(url_for('carvia.detalhe_cotacao_v2', cotacao_id=cotacao.id))

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar cotacao: %s", e)
            flash(f'Erro: {e}', 'danger')
            return render_template(
                'carvia/cotacoes/criar.html',
                nf_id_param=nf_id_param,
                **_ctx_criar(),
            )

    # ==================== DETALHE ====================

    @bp.route('/cotacoes/<int:cotacao_id>') # type: ignore
    @login_required
    def detalhe_cotacao_v2(cotacao_id): # type: ignore
        """Detalhe da cotacao com motos, pricing e acoes"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaCotacao
        import json as json_lib

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            flash('Cotacao nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_cotacoes_v2'))

        motos_raw = cotacao.motos.all() if cotacao.tipo_material == 'MOTO' else []
        pedidos = cotacao.pedidos.all()

        # Mapeamento numero_nf -> [CarviaNfVeiculo] para accordion de veiculos
        # + detectar se alguma NF ja possui CTe (para ocultar emissao CTe SSW)
        from app.carvia.models import CarviaNf
        veiculos_por_nf = {}
        tem_cte_existente = bool(cotacao.criacao_tardia)
        for ped in pedidos:
            for item in ped.itens.all():
                if item.numero_nf and item.numero_nf not in veiculos_por_nf:
                    nf_obj = CarviaNf.query.filter_by(
                        numero_nf=str(item.numero_nf)
                    ).order_by(CarviaNf.id.desc()).first()
                    if nf_obj:
                        veiculos_por_nf[item.numero_nf] = nf_obj.veiculos.all()
                        # Verificar se NF ja tem CTe vinculado
                        if not tem_cte_existente and nf_obj.operacoes.count() > 0:
                            tem_cte_existente = True

        # Serializar motos para JS (evita tojson em SQLAlchemy objects)
        motos_list_json = json_lib.dumps([{
            'modelo_moto_id': m.modelo_moto_id,
            'modelo_nome': m.modelo_moto.nome if m.modelo_moto else '',
            'categoria_nome': m.categoria_moto.nome if m.categoria_moto else '',
            'quantidade': m.quantidade,
            'valor_unitario': float(m.valor_unitario) if m.valor_unitario else None,
            'valor_total': float(m.valor_total) if m.valor_total else None,
            'peso_cubado_unitario': float(m.peso_cubado_unitario) if m.peso_cubado_unitario else None,
            'peso_cubado_total': float(m.peso_cubado_total) if m.peso_cubado_total else None,
        } for m in motos_raw])

        # Modelos de moto para tabela inline
        from app.carvia.models import CarviaModeloMoto
        import json as json_lib
        modelos_raw = CarviaModeloMoto.query.filter_by(ativo=True).order_by(
            CarviaModeloMoto.nome.asc()
        ).all()
        modelos_moto_json = json_lib.dumps([{
            'id': m.id,
            'nome': m.nome,
            'peso_cubado': round(
                float(m.comprimento) * float(m.largura) * float(m.altura)
                * max(float(m.cubagem_minima or 300), 300) / 1_000_000, 3
            ) if m.comprimento and m.largura and m.altura else None,
        } for m in modelos_raw])

        # Clientes e enderecos para edicao
        from app.carvia.services.clientes.cliente_service import CarviaClienteService
        clientes = CarviaClienteService.listar_clientes(apenas_ativos=True)

        # Limite desconto + toggle exigir aprovacao admin (global)
        from app.carvia.services.pricing.config_service import CarviaConfigService
        limite_desconto = CarviaConfigService.limite_desconto_percentual()
        exigir_aprovacao_admin = CarviaConfigService.exigir_aprovacao_admin()

        # Veiculos para dropdown DIRETA
        from app.veiculos.models import Veiculo
        veiculos_direta = Veiculo.query.order_by(Veiculo.peso_maximo.asc()).all()

        # Pre-vinculos extrato <-> cotacao (feature frete pre-pago)
        from app.carvia.models import CarviaPreVinculoExtratoCotacao
        previnculos = CarviaPreVinculoExtratoCotacao.query.filter_by(
            cotacao_id=cotacao_id,
        ).order_by(
            CarviaPreVinculoExtratoCotacao.criado_em.desc()
        ).all()

        return render_template(
            'carvia/cotacoes/detalhe.html',
            cotacao=cotacao,
            motos=motos_raw,
            motos_list_json=motos_list_json,
            pedidos=pedidos,
            veiculos_por_nf=veiculos_por_nf,
            clientes=clientes,
            modelos_moto_json=modelos_moto_json,
            limite_desconto=limite_desconto,
            exigir_aprovacao_admin=exigir_aprovacao_admin,
            veiculos_direta=veiculos_direta,
            tem_cte_existente=tem_cte_existente,
            previnculos=previnculos,
        )

    # ==================== API: ATUALIZAR COTACAO ====================

    @bp.route('/api/cotacoes/<int:cotacao_id>', methods=['PUT']) # type: ignore
    @login_required
    def api_atualizar_cotacao(cotacao_id): # type: ignore
        """Atualiza dados da cotacao (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaCotacao

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return jsonify({'erro': 'Cotacao nao encontrada.'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        # Guard: cotacao APROVADO — bloquear edicao (exceto criacao tardia parcial)
        if cotacao.status == 'APROVADO' and not cotacao.criacao_tardia:
            return jsonify({'erro': 'Cotacao aprovada nao pode ser editada. Reabra primeiro.'}), 400
        if cotacao.status == 'CANCELADO':
            return jsonify({'erro': 'Cotacao cancelada nao pode ser editada.'}), 400

        try:
            # Campos de referencia
            if 'cliente_id' in data and data['cliente_id']:
                cotacao.cliente_id = int(data['cliente_id'])
            if 'endereco_origem_id' in data and data['endereco_origem_id']:
                cotacao.endereco_origem_id = int(data['endereco_origem_id'])
            if 'endereco_destino_id' in data and data['endereco_destino_id']:
                novo_destino = int(data['endereco_destino_id'])
                if novo_destino != cotacao.endereco_destino_id:
                    cotacao.endereco_destino_id = novo_destino
                    # Limpar override de entrega e pricing (destino mudou)
                    for c in ('entrega_uf', 'entrega_cidade', 'entrega_logradouro',
                              'entrega_numero', 'entrega_bairro', 'entrega_cep',
                              'entrega_complemento'):
                        setattr(cotacao, c, None)
                    cotacao.valor_tabela = None
                    cotacao.valor_descontado = None
                    cotacao.valor_final_aprovado = None
                    cotacao.tabela_carvia_id = None
                    cotacao.dentro_tabela = None
                    cotacao.detalhes_calculo = None
                    cotacao.percentual_desconto = None
                    cotacao.cotacao_manual = False
                    cotacao.valor_manual = None
            if 'tipo_material' in data and data['tipo_material'] in ('CARGA_GERAL', 'MOTO'):
                cotacao.tipo_material = data['tipo_material']

            # Tipo carga + veiculo
            if 'tipo_carga' in data:
                new_tc = (data['tipo_carga'] or '').upper()
                if new_tc in ('DIRETA', 'FRACIONADA') and new_tc != cotacao.tipo_carga:
                    cotacao.tipo_carga = new_tc
                    # Limpar veiculo se saiu de DIRETA
                    if new_tc != 'DIRETA':
                        cotacao.veiculo_id = None
                    # Limpar pricing (tipo_carga mudou)
                    cotacao.valor_tabela = None
                    cotacao.valor_descontado = None
                    cotacao.valor_final_aprovado = None
                    cotacao.tabela_carvia_id = None
                    cotacao.dentro_tabela = None
                    cotacao.detalhes_calculo = None
                    cotacao.percentual_desconto = None
                    cotacao.cotacao_manual = False
                    cotacao.valor_manual = None

            if 'veiculo_id' in data:
                novo_vid = int(data['veiculo_id']) if data['veiculo_id'] else None
                if novo_vid != cotacao.veiculo_id:
                    cotacao.veiculo_id = novo_vid
                    # Reset pricing (veiculo mudou → preco diferente)
                    cotacao.valor_tabela = None
                    cotacao.valor_descontado = None
                    cotacao.valor_final_aprovado = None
                    cotacao.tabela_carvia_id = None
                    cotacao.dentro_tabela = None
                    cotacao.detalhes_calculo = None
                    cotacao.percentual_desconto = None

            # Campos numericos
            for campo in ('peso', 'valor_mercadoria', 'volumes',
                          'dimensao_c', 'dimensao_l', 'dimensao_a'):
                if campo in data:
                    setattr(cotacao, campo, data[campo])

            # Peso cubado automatico
            if cotacao.dimensao_c and cotacao.dimensao_l and cotacao.dimensao_a:
                cotacao.peso_cubado = (
                    float(cotacao.dimensao_c) * float(cotacao.dimensao_l)
                    * float(cotacao.dimensao_a) * 300
                )

            # Datas
            if 'data_expedicao' in data:
                cotacao.data_expedicao = (
                    datetime.strptime(data['data_expedicao'], '%Y-%m-%d').date()
                    if data['data_expedicao'] else None
                )
            if 'data_agenda' in data:
                cotacao.data_agenda = (
                    datetime.strptime(data['data_agenda'], '%Y-%m-%d').date()
                    if data['data_agenda'] else None
                )

            if 'observacoes' in data:
                cotacao.observacoes = data['observacoes'] or None

            # Condicao de pagamento e responsavel do frete
            if 'condicao_pagamento' in data:
                cotacao.condicao_pagamento = data['condicao_pagamento'] or None
            if 'prazo_dias' in data:
                cotacao.prazo_dias = int(data['prazo_dias']) if data['prazo_dias'] else None
            if 'responsavel_frete' in data:
                cotacao.responsavel_frete = data['responsavel_frete'] or None
            if 'percentual_remetente' in data:
                cotacao.percentual_remetente = float(data['percentual_remetente']) if data['percentual_remetente'] is not None else None
            if 'percentual_destinatario' in data:
                cotacao.percentual_destinatario = float(data['percentual_destinatario']) if data['percentual_destinatario'] is not None else None

            # Endereco de entrega (override por cotacao)
            endereco_mudou = False
            for campo in ('entrega_uf', 'entrega_cidade', 'entrega_logradouro',
                          'entrega_numero', 'entrega_bairro', 'entrega_cep',
                          'entrega_complemento'):
                if campo in data:
                    novo = data[campo] or None
                    if campo in ('entrega_uf', 'entrega_cidade'):
                        atual = getattr(cotacao, campo, None)
                        if novo != atual:
                            endereco_mudou = True
                    setattr(cotacao, campo, novo)

            # Zerar pricing quando UF ou cidade mudam (obriga recalculo)
            if endereco_mudou:
                cotacao.valor_tabela = None
                cotacao.valor_descontado = None
                cotacao.valor_final_aprovado = None
                cotacao.tabela_carvia_id = None
                cotacao.dentro_tabela = None
                cotacao.detalhes_calculo = None
                cotacao.percentual_desconto = None
                cotacao.cotacao_manual = False
                cotacao.valor_manual = None

            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Cotacao atualizada.'})

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao atualizar cotacao #%s: %s", cotacao_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== API: SALVAR COMPLETO ====================

    @bp.route('/api/cotacoes/<int:cotacao_id>/salvar-completo', methods=['PUT']) # type: ignore
    @login_required
    def api_salvar_cotacao_completo(cotacao_id): # type: ignore
        """Salva dados + motos de uma vez"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaCotacao, CarviaCotacaoMoto, CarviaModeloMoto

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return jsonify({'erro': 'Cotacao nao encontrada.'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        # Guard: cotacao APROVADO — bloquear edicao (exceto criacao tardia)
        if cotacao.status == 'APROVADO':
            if not cotacao.criacao_tardia:
                return jsonify({'erro': 'Cotacao aprovada nao pode ser editada. Reabra primeiro.'}), 400
            # Criacao tardia APROVADO: filtrar apenas campos permitidos
            campos_permitidos = {
                'endereco_origem_id', 'endereco_destino_id', 'tipo_carga',
                'entrega_uf', 'entrega_cidade', 'entrega_logradouro',
                'entrega_numero', 'entrega_bairro', 'entrega_cep', 'entrega_complemento',
            }
            data = {k: v for k, v in data.items() if k in campos_permitidos}

        # Guard: cotacao CANCELADO — bloquear edicao
        if cotacao.status == 'CANCELADO':
            return jsonify({'erro': 'Cotacao cancelada nao pode ser editada.'}), 400

        try:
            # --- Atualizar campos header ---
            if data.get('cliente_id'):
                cotacao.cliente_id = int(data['cliente_id'])
            if data.get('endereco_origem_id'):
                cotacao.endereco_origem_id = int(data['endereco_origem_id'])
            if data.get('endereco_destino_id'):
                novo_destino = int(data['endereco_destino_id'])
                if novo_destino != cotacao.endereco_destino_id:
                    cotacao.endereco_destino_id = novo_destino
                    for c in ('entrega_uf', 'entrega_cidade', 'entrega_logradouro',
                              'entrega_numero', 'entrega_bairro', 'entrega_cep',
                              'entrega_complemento'):
                        setattr(cotacao, c, None)
                    cotacao.valor_tabela = None
                    cotacao.valor_descontado = None
                    cotacao.valor_final_aprovado = None
                    cotacao.tabela_carvia_id = None
                    cotacao.dentro_tabela = None
                    cotacao.detalhes_calculo = None
                    cotacao.percentual_desconto = None
            if data.get('tipo_material') in ('CARGA_GERAL', 'MOTO'):
                cotacao.tipo_material = data['tipo_material']
            if data.get('tipo_carga') in ('DIRETA', 'FRACIONADA'):
                new_tc = data['tipo_carga']
                if new_tc != cotacao.tipo_carga:
                    # Limpar veiculo se saiu de DIRETA
                    if new_tc != 'DIRETA':
                        cotacao.veiculo_id = None
                cotacao.tipo_carga = new_tc

            if 'veiculo_id' in data:
                cotacao.veiculo_id = int(data['veiculo_id']) if data['veiculo_id'] else None

            for campo in ('peso', 'valor_mercadoria', 'volumes',
                          'dimensao_c', 'dimensao_l', 'dimensao_a'):
                if campo in data:
                    setattr(cotacao, campo, data[campo])

            if cotacao.dimensao_c and cotacao.dimensao_l and cotacao.dimensao_a:
                cotacao.peso_cubado = (
                    float(cotacao.dimensao_c) * float(cotacao.dimensao_l)
                    * float(cotacao.dimensao_a) * 300
                )

            if 'data_expedicao' in data:
                cotacao.data_expedicao = (
                    datetime.strptime(data['data_expedicao'], '%Y-%m-%d').date()
                    if data['data_expedicao'] else None
                )
            if 'data_agenda' in data:
                cotacao.data_agenda = (
                    datetime.strptime(data['data_agenda'], '%Y-%m-%d').date()
                    if data['data_agenda'] else None
                )
            if 'observacoes' in data:
                cotacao.observacoes = data['observacoes'] or None

            # Condicao de pagamento e responsavel do frete
            if 'condicao_pagamento' in data:
                cotacao.condicao_pagamento = data['condicao_pagamento'] or None
            if 'prazo_dias' in data:
                cotacao.prazo_dias = int(data['prazo_dias']) if data['prazo_dias'] else None
            if 'responsavel_frete' in data:
                cotacao.responsavel_frete = data['responsavel_frete'] or None
            if 'percentual_remetente' in data:
                cotacao.percentual_remetente = float(data['percentual_remetente']) if data['percentual_remetente'] is not None else None
            if 'percentual_destinatario' in data:
                cotacao.percentual_destinatario = float(data['percentual_destinatario']) if data['percentual_destinatario'] is not None else None

            # Endereco de entrega (override por cotacao)
            endereco_mudou = False
            for campo in ('entrega_uf', 'entrega_cidade', 'entrega_logradouro',
                          'entrega_numero', 'entrega_bairro', 'entrega_cep',
                          'entrega_complemento'):
                if campo in data:
                    novo = data[campo] or None
                    if campo in ('entrega_uf', 'entrega_cidade'):
                        atual = getattr(cotacao, campo, None)
                        if novo != atual:
                            endereco_mudou = True
                    setattr(cotacao, campo, novo)

            # Zerar pricing quando UF ou cidade mudam (obriga recalculo)
            if endereco_mudou:
                cotacao.valor_tabela = None
                cotacao.valor_descontado = None
                cotacao.valor_final_aprovado = None
                cotacao.tabela_carvia_id = None
                cotacao.dentro_tabela = None
                cotacao.detalhes_calculo = None
                cotacao.percentual_desconto = None
                cotacao.cotacao_manual = False
                cotacao.valor_manual = None

            # --- Sync motos (se tipo=MOTO) ---
            if cotacao.tipo_material == 'MOTO' and 'motos' in data:
                # Deletar existentes
                CarviaCotacaoMoto.query.filter_by(cotacao_id=cotacao.id).delete()
                db.session.flush()

                # Recriar
                from decimal import Decimal
                soma_valor = 0
                for moto_data in data['motos']:
                    modelo_id = moto_data.get('modelo_moto_id')
                    qtd = moto_data.get('quantidade', 0)
                    vlr_unit = moto_data.get('valor_unitario')

                    if not modelo_id or not qtd:
                        continue

                    modelo = db.session.get(CarviaModeloMoto, int(modelo_id))
                    if not modelo:
                        continue

                    # Calcular peso cubado (mesma logica do service)
                    peso_unit = 0
                    if modelo.comprimento and modelo.largura and modelo.altura:
                        m3 = float(modelo.comprimento) * float(modelo.largura) * float(modelo.altura)
                        cubagem = max(float(modelo.cubagem_minima or 300), 300)
                        peso_unit = m3 * cubagem / 1_000_000

                    vlr_total = float(vlr_unit or 0) * int(qtd)
                    soma_valor += vlr_total

                    item = CarviaCotacaoMoto(
                        cotacao_id=cotacao.id,
                        modelo_moto_id=int(modelo_id),
                        categoria_moto_id=modelo.categoria_moto_id,
                        quantidade=int(qtd),
                        peso_cubado_unitario=Decimal(str(round(peso_unit, 3))),
                        peso_cubado_total=Decimal(str(round(peso_unit * int(qtd), 3))),
                        valor_unitario=Decimal(str(vlr_unit)) if vlr_unit else None,
                        valor_total=Decimal(str(vlr_total)) if vlr_total else None,
                    )
                    db.session.add(item)

                if soma_valor > 0:
                    cotacao.valor_mercadoria = Decimal(str(soma_valor))

            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Cotacao salva.'})

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao salvar cotacao completa #%s: %s", cotacao_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== API: MOTOS ====================

    @bp.route('/api/cotacoes/<int:cotacao_id>/motos', methods=['POST']) # type: ignore
    @login_required
    def api_adicionar_moto_cotacao(cotacao_id): # type: ignore
        """Adiciona moto a cotacao (JSON API)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        try:
            item, erro = CotacaoV2Service.adicionar_moto(
                cotacao_id=cotacao_id,
                modelo_moto_id=int(data.get('modelo_moto_id', 0)),
                quantidade=int(data.get('quantidade', 0)),
                valor_unitario=float(data['valor_unitario']) if data.get('valor_unitario') else None,
            )
            if erro:
                return jsonify({'erro': erro}), 400

            db.session.commit()
            return jsonify({
                'sucesso': True,
                'id': item.id,
                'mensagem': 'Moto adicionada.',
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao adicionar moto: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cotacao-motos/<int:item_id>', methods=['DELETE']) # type: ignore
    @login_required
    def api_remover_moto_cotacao(item_id): # type: ignore
        """Remove moto da cotacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaCotacaoMoto

        item = db.session.get(CarviaCotacaoMoto, item_id)
        if not item:
            return jsonify({'erro': 'Item nao encontrado.'}), 404

        if item.cotacao.status != 'RASCUNHO':
            return jsonify({'erro': 'Cotacao nao esta em RASCUNHO.'}), 400

        try:
            db.session.delete(item)
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Moto removida.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== API: PRICING ====================

    @bp.route('/api/cotacoes/<int:cotacao_id>/calcular-preco', methods=['POST']) # type: ignore
    @login_required
    def api_calcular_preco(cotacao_id): # type: ignore
        """Calcula preco da cotacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service

        try:
            resultado, erro = CotacaoV2Service.calcular_preco(cotacao_id)
            if erro:
                return jsonify({'erro': erro}), 400

            db.session.commit()
            return jsonify({'sucesso': True, **resultado})

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao calcular preco: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cotacoes/<int:cotacao_id>/desconto', methods=['POST']) # type: ignore
    @login_required
    def api_aplicar_desconto(cotacao_id): # type: ignore
        """Aplica desconto na cotacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        try:
            sucesso, erro = CotacaoV2Service.aplicar_desconto(
                cotacao_id=cotacao_id,
                percentual_desconto=float(data.get('percentual_desconto', 0)),
                usuario=current_user.email,
            )
            if not sucesso:
                return jsonify({'erro': erro}), 400

            db.session.commit()

            from app.carvia.models import CarviaCotacao
            cotacao = db.session.get(CarviaCotacao, cotacao_id)
            return jsonify({
                'sucesso': True,
                'status': cotacao.status,
                'valor_descontado': float(cotacao.valor_descontado or 0),
                'valor_final_aprovado': float(cotacao.valor_final_aprovado or 0),
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== API: COTACAO MANUAL ====================

    @bp.route('/api/cotacoes/<int:cotacao_id>/valor-manual', methods=['POST']) # type: ignore
    @login_required
    def api_valor_manual(cotacao_id): # type: ignore
        """Define valor manual para cotacao (sem lookup de tabela)"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        try:
            sucesso, erro = CotacaoV2Service.definir_valor_manual(
                cotacao_id=cotacao_id,
                valor=float(data.get('valor', 0)),
                usuario=current_user.email,
            )
            if not sucesso:
                return jsonify({'erro': erro}), 400

            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Valor manual definido. Aguardando aprovacao.'})

        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== API: SUGESTAO DE VEICULO ====================

    @bp.route('/api/cotacoes/sugerir-veiculo', methods=['POST']) # type: ignore
    @login_required
    def api_sugerir_veiculo(): # type: ignore
        """Sugere veiculo por peso para carga direta"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service

        data = request.get_json()
        peso = float(data.get('peso', 0)) if data else 0

        veiculo_id = CotacaoV2Service.sugerir_veiculo(peso)
        return jsonify({'veiculo_id': veiculo_id})

    # ==================== API: STATUS ====================

    @bp.route('/api/cotacoes/<int:cotacao_id>/enviar', methods=['POST']) # type: ignore
    @login_required
    def api_enviar_cotacao(cotacao_id): # type: ignore
        """Marca como ENVIADO"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service

        try:
            sucesso, erro = CotacaoV2Service.marcar_enviado(
                cotacao_id, current_user.email)
            if not sucesso:
                return jsonify({'erro': erro}), 400
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Cotacao enviada.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cotacoes/<int:cotacao_id>/aprovar-cliente', methods=['POST']) # type: ignore
    @login_required
    def api_aprovar_cliente(cotacao_id): # type: ignore
        """Registra aprovacao do cliente"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service

        try:
            sucesso, erro = CotacaoV2Service.registrar_aprovacao_cliente(
                cotacao_id, current_user.email)
            if not sucesso:
                return jsonify({'erro': erro}), 400
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Cotacao aprovada pelo cliente.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cotacoes/<int:cotacao_id>/recusar-cliente', methods=['POST']) # type: ignore
    @login_required
    def api_recusar_cliente(cotacao_id): # type: ignore
        """Registra recusa do cliente"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service

        try:
            sucesso, erro = CotacaoV2Service.registrar_recusa_cliente(cotacao_id)
            if not sucesso:
                return jsonify({'erro': erro}), 400
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Cotacao recusada.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cotacoes/<int:cotacao_id>/contra-proposta', methods=['POST']) # type: ignore
    @login_required
    def api_contra_proposta(cotacao_id): # type: ignore
        """Registra contra-proposta do cliente"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        try:
            sucesso, erro = CotacaoV2Service.registrar_contra_proposta(
                cotacao_id, float(data.get('novo_valor', 0)))
            if not sucesso:
                return jsonify({'erro': erro}), 400
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Contra-proposta registrada.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cotacoes/<int:cotacao_id>/cancelar', methods=['POST']) # type: ignore
    @login_required
    def api_cancelar_cotacao(cotacao_id): # type: ignore
        """Cancela cotacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service

        try:
            sucesso, erro = CotacaoV2Service.cancelar(cotacao_id)
            if not sucesso:
                return jsonify({'erro': erro}), 400
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Cotacao cancelada.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cotacoes/<int:cotacao_id>/reabrir', methods=['POST']) # type: ignore
    @login_required
    def api_reabrir_cotacao(cotacao_id): # type: ignore
        """Reabre cotacao aprovada — volta para RASCUNHO"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service

        try:
            sucesso, erro = CotacaoV2Service.reabrir(
                cotacao_id, current_user.email)
            if not sucesso:
                return jsonify({'erro': erro}), 400
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Cotacao reaberta.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cotacoes/<int:cotacao_id>/admin-aprovar', methods=['POST']) # type: ignore
    @login_required
    def api_admin_aprovar_cotacao(cotacao_id): # type: ignore
        """Admin aprova cotacao pendente"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403
        if not getattr(current_user, 'perfil', '') == 'administrador':
            return jsonify({'erro': 'Apenas administradores.'}), 403

        from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service

        try:
            sucesso, erro = CotacaoV2Service.admin_aprovar(
                cotacao_id, current_user.email)
            if not sucesso:
                return jsonify({'erro': erro}), 400
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Desconto aprovado pelo admin.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/cotacoes/<int:cotacao_id>/admin-rejeitar', methods=['POST']) # type: ignore
    @login_required
    def api_admin_rejeitar_cotacao(cotacao_id): # type: ignore
        """Admin rejeita cotacao pendente"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403
        if not getattr(current_user, 'perfil', '') == 'administrador':
            return jsonify({'erro': 'Apenas administradores.'}), 403

        from app.carvia.services.pricing.cotacao_v2_service import CotacaoV2Service

        try:
            sucesso, erro = CotacaoV2Service.admin_rejeitar(cotacao_id)
            if not sucesso:
                return jsonify({'erro': erro}), 400
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Desconto rejeitado.'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== API: ANEXAR NF NA COTACAO ====================

    @bp.route('/api/cotacoes/<int:cotacao_id>/nf', methods=['POST']) # type: ignore
    @login_required
    def api_anexar_nf_cotacao(cotacao_id): # type: ignore
        """Anexa NF na cotacao via upload de arquivo (PDF DANFE ou XML NF-e).

        Form multipart: origem_id=<int>, arquivo=<file>
        (backward compat: filial=SP|RJ tambem aceito)

        Parseia o arquivo, cria CarviaNf + itens, cria/reutiliza pedido,
        vincula e expande provisorio no embarque.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import (
            CarviaCotacao, CarviaClienteEndereco, CarviaNf, CarviaNfItem,
            CarviaNfVeiculo, CarviaPedido, CarviaPedidoItem,
        )
        from app.utils.timezone import agora_utc_naive

        # SELECT FOR UPDATE: serializa anexacoes concorrentes na mesma cotacao
        # (evita race condition onde 2 requests leem agg base identico e ambas
        # passam pelo teto de peso/valor em APROVADA).
        cotacao = CarviaCotacao.query.filter_by(
            id=cotacao_id
        ).with_for_update().first()
        if not cotacao:
            return jsonify({'erro': 'Cotacao nao encontrada.'}), 404
        # Status permitidos: qualquer um editavel + APROVADO (com validacao de teto adiante)
        _STATUS_ANEXAR_NF = {'RASCUNHO', 'PENDENTE_ADMIN', 'ENVIADO', 'APROVADO', 'RECUSADO'}
        if cotacao.status not in _STATUS_ANEXAR_NF:
            return jsonify({
                'erro': f'Cotacao em status {cotacao.status} nao permite anexar NF.'
            }), 400

        # Determinar filial: novo fluxo (origem_id) ou legado (filial direta)
        origem_id = request.form.get('origem_id', type=int)
        if origem_id:
            origem = db.session.get(CarviaClienteEndereco, origem_id)
            if not origem or origem.tipo != 'ORIGEM':
                return jsonify({'erro': 'Origem invalida.'}), 400
            filial = 'RJ' if origem.fisico_uf == 'RJ' else 'SP'
        else:
            # Backward compat: filial direta
            filial = (request.form.get('filial') or '').upper()
            if filial not in ('SP', 'RJ'):
                return jsonify({'erro': 'Filial ou origem_id obrigatorio.'}), 400

        arquivo = request.files.get('arquivo')
        if not arquivo or not arquivo.filename:
            return jsonify({'erro': 'Arquivo (PDF ou XML) obrigatorio.'}), 400

        nome_arquivo = arquivo.filename
        ext = nome_arquivo.lower().rsplit('.', 1)[-1] if '.' in nome_arquivo else ''
        if ext not in ('xml', 'pdf'):
            return jsonify({'erro': f'Extensao .{ext} nao suportada. Use PDF ou XML.'}), 400

        try:
            conteudo = arquivo.read()

            # 1. Parsear arquivo
            if ext == 'xml':
                from app.carvia.services.parsers.nfe_xml_parser import NFeXMLParser
                parser = NFeXMLParser(conteudo)
                if not parser.is_valid():
                    return jsonify({'erro': 'XML invalido.'}), 400
                if not parser.is_nfe():
                    return jsonify({'erro': 'XML nao e NF-e (modelo 55). Pode ser CTe.'}), 400
                dados = parser.get_todas_informacoes()
            else:
                from app.carvia.services.parsers.danfe_pdf_parser import DanfePDFParser
                parser = DanfePDFParser(pdf_bytes=conteudo)
                if not parser.is_valid():
                    return jsonify({'erro': 'PDF invalido ou sem texto extraivel.'}), 400
                dados = parser.get_todas_informacoes()

            numero_nf = dados.get('numero_nf') or '0'
            data_emissao = dados.get('data_emissao')
            if data_emissao and hasattr(data_emissao, 'date'):
                data_emissao = data_emissao.date()

            # 2. Verificar duplicata — reutilizar NF existente se ja importada
            chave = dados.get('chave_acesso_nf')
            nf_reutilizada = False
            nf = None

            if chave:
                nf = CarviaNf.query.filter_by(chave_acesso_nf=chave).first()
                if nf:
                    nf_reutilizada = True
                    numero_nf = nf.numero_nf or numero_nf

            # 2.5. Validar/Recalcular limites da cotacao
            # - APROVADO: bloqueia se soma(NFs + nova NF) excede peso, peso_cubado ou valor
            # - Nao-APROVADO: recalcula cotacao.peso / peso_cubado / valor_mercadoria /
            #   volumes (apenas aumenta, nunca diminui). Pricing nao e redisparado.
            from app.carvia.services.documentos.embarque_carvia_service import (
                EmbarqueCarViaService,
            )

            peso_nova = float(
                (nf.peso_bruto if nf else dados.get('peso_bruto')) or 0
            )
            valor_nova = float(
                (nf.valor_total if nf else dados.get('valor_total')) or 0
            )
            volumes_nova = int(
                (nf.quantidade_volumes if nf else dados.get('quantidade_volumes')) or 0
            )

            # Cubado da NF nova: MOTO soma por modelos, CARGA_GERAL usa peso_bruto
            if cotacao.tipo_material == 'MOTO':
                if nf:
                    modelos_nf = [v.modelo for v in nf.veiculos.all()]
                else:
                    modelos_nf = [v.get('modelo') for v in dados.get('veiculos', [])]
                cubado_nova = EmbarqueCarViaService.calcular_cubado_por_modelos(
                    cotacao_id, modelos_nf
                )
            else:
                cubado_nova = peso_nova  # CARGA_GERAL: proxy conservador

            agg = _agregar_totais_nfs_cotacao(cotacao_id)
            eh_reanexacao = str(numero_nf) in agg['nfs_vinculadas']

            if not eh_reanexacao:
                soma_peso = agg['peso_bruto'] + peso_nova
                soma_cubado = agg['peso_cubado'] + cubado_nova
                soma_valor = agg['valor_total'] + valor_nova
                soma_volumes = agg['quantidade_volumes'] + volumes_nova

                # Teto cubado: MOTO -> peso_total_motos (property); CARGA_GERAL -> peso_cubado
                if cotacao.tipo_material == 'MOTO':
                    teto_peso_cubado = float(cotacao.peso_total_motos or 0)
                else:
                    teto_peso_cubado = float(cotacao.peso_cubado or 0)
                teto_peso = float(cotacao.peso or 0)
                teto_valor = float(cotacao.valor_mercadoria or 0)

                if cotacao.status == 'APROVADO':
                    excessos = []
                    if teto_peso > 0 and soma_peso > teto_peso + _TOL_KG:
                        excessos.append(
                            f"peso {soma_peso:.2f}/{teto_peso:.2f} kg"
                        )
                    if teto_peso_cubado > 0 and soma_cubado > teto_peso_cubado + _TOL_KG:
                        excessos.append(
                            f"peso cubado {soma_cubado:.2f}/{teto_peso_cubado:.2f} kg"
                        )
                    if teto_valor > 0 and soma_valor > teto_valor + _TOL_VAL:
                        excessos.append(
                            f"valor R$ {soma_valor:.2f}/{teto_valor:.2f}"
                        )
                    if excessos:
                        db.session.rollback()
                        return jsonify({
                            'erro': (
                                f'NF excede limites da cotacao aprovada: '
                                f'{"; ".join(excessos)}. Cancele a cotacao '
                                f'ou reabra-a (status != APROVADO) para recalcular.'
                            )
                        }), 400
                else:
                    # Nao-APROVADO: recalcular totais da cotacao (apenas aumenta)
                    if soma_peso > teto_peso + _TOL_KG:
                        cotacao.peso = soma_peso
                    if cotacao.tipo_material != 'MOTO':
                        # CARGA_GERAL: atualiza peso_cubado quando excedido
                        if soma_cubado > float(cotacao.peso_cubado or 0) + _TOL_KG:
                            cotacao.peso_cubado = soma_cubado
                    # MOTO: peso_total_motos e property derivada de CarviaCotacaoMoto
                    if soma_valor > teto_valor + _TOL_VAL:
                        cotacao.valor_mercadoria = soma_valor
                    cotacao.volumes = soma_volumes
                    # valor_tabela / valor_final_aprovado permanecem congelados;
                    # usuario reprecifica manualmente se desejar.

            # 3. Criar CarviaNf + itens (se nao reutilizada)
            if not nf:
                nf = CarviaNf(
                    numero_nf=numero_nf,
                    serie_nf=dados.get('serie_nf'),
                    chave_acesso_nf=chave,
                    data_emissao=data_emissao,
                    cnpj_emitente=dados.get('cnpj_emitente') or 'DESCONHECIDO',
                    nome_emitente=dados.get('nome_emitente'),
                    uf_emitente=dados.get('uf_emitente'),
                    cidade_emitente=dados.get('cidade_emitente'),
                    cnpj_destinatario=dados.get('cnpj_destinatario'),
                    nome_destinatario=dados.get('nome_destinatario'),
                    uf_destinatario=dados.get('uf_destinatario'),
                    cidade_destinatario=dados.get('cidade_destinatario'),
                    valor_total=dados.get('valor_total'),
                    peso_bruto=dados.get('peso_bruto'),
                    peso_liquido=dados.get('peso_liquido'),
                    quantidade_volumes=dados.get('quantidade_volumes'),
                    tipo_fonte=dados.get('tipo_fonte', 'MANUAL'),
                    arquivo_nome_original=nome_arquivo,
                    criado_por=current_user.email,
                    criado_em=agora_utc_naive(),
                )
                db.session.add(nf)
                db.session.flush()

                for item_data in dados.get('itens', []):
                    db.session.add(CarviaNfItem(
                        nf_id=nf.id,
                        codigo_produto=item_data.get('codigo_produto'),
                        descricao=item_data.get('descricao'),
                        ncm=item_data.get('ncm'),
                        cfop=item_data.get('cfop'),
                        unidade=item_data.get('unidade'),
                        quantidade=item_data.get('quantidade'),
                        valor_unitario=item_data.get('valor_unitario'),
                        valor_total_item=item_data.get('valor_total_item'),
                    ))

                # Criar veiculos (motos: chassi, cor, modelo)
                # Enriquecer com dados do item da NF (valor/modelo que LLM nao extrai)
                itens_nf_ref = dados.get('itens', [])
                for v_idx, veiculo in enumerate(dados.get('veiculos', [])):
                    chassi = (veiculo.get('chassi') or '').strip()
                    if chassi:
                        existente = CarviaNfVeiculo.query.filter_by(chassi=chassi).first()
                        if not existente:
                            # B2 fix: more vehicles than NF items → fall back to last item (same NF line, multiple chassis)
                            item_nf_ref = itens_nf_ref[min(v_idx, len(itens_nf_ref) - 1)] if itens_nf_ref else {}
                            db.session.add(CarviaNfVeiculo(
                                nf_id=nf.id,
                                chassi=chassi,
                                modelo=veiculo.get('modelo') or item_nf_ref.get('descricao'),
                                cor=veiculo.get('cor'),
                                valor=veiculo.get('valor') or item_nf_ref.get('valor_unitario') or item_nf_ref.get('valor_total_item'),
                                ano=veiculo.get('ano_modelo'),
                                numero_motor=veiculo.get('numero_motor'),
                            ))

            # 4. Buscar pedido existente com esta NF (dedup) ou criar novo
            # B3 fix: lookup by NF number, not just filial — avoids merging different NFs into same pedido
            pedido = CarviaPedido.query.filter_by(
                cotacao_id=cotacao_id,
            ).filter(CarviaPedido.status != 'CANCELADO').join(
                CarviaPedidoItem
            ).filter(CarviaPedidoItem.numero_nf == numero_nf).first()

            pedido_criado = False
            if not pedido:
                tipo_sep = 'ESTOQUE' if filial == 'SP' else 'CROSSDOCK'
                pedido = CarviaPedido(
                    numero_pedido=CarviaPedido.gerar_numero_pedido(cotacao_id),
                    cotacao_id=cotacao_id,
                    filial=filial,
                    tipo_separacao=tipo_sep,
                    criado_por=current_user.email,
                    criado_em=agora_utc_naive(),
                    atualizado_em=agora_utc_naive(),
                )
                db.session.add(pedido)
                db.session.flush()
                pedido_criado = True

            # 5. Criar PedidoItem por produto da NF (com dados reais)
            itens_nf = dados.get('itens', [])
            veiculos = dados.get('veiculos', [])
            if itens_nf:
                for idx, item_nf in enumerate(itens_nf):
                    # Associar veiculo por posicao (1 item = 1 moto tipicamente)
                    veiculo = veiculos[idx] if idx < len(veiculos) else None
                    cor = veiculo.get('cor') if veiculo else None
                    desc = item_nf.get('descricao') or 'Produto'

                    pedido_item = CarviaPedidoItem(
                        pedido_id=pedido.id,
                        descricao=desc,
                        cor=cor,
                        quantidade=int(item_nf.get('quantidade') or 1),
                        valor_unitario=item_nf.get('valor_unitario'),
                        valor_total=item_nf.get('valor_total_item'),
                        numero_nf=numero_nf,
                    )
                    db.session.add(pedido_item)
            else:
                # Fallback: NF sem itens detalhados (PDF com extracao parcial)
                pedido_item = CarviaPedidoItem(
                    pedido_id=pedido.id,
                    descricao=dados.get('nome_emitente') or 'Produto',
                    quantidade=1,
                    valor_total=dados.get('valor_total'),
                    numero_nf=numero_nf,
                )
                db.session.add(pedido_item)

            db.session.flush()

            # 7. Expandir provisorio no embarque (nao-bloqueante)
            resultado_expansao = None
            try:
                from app.carvia.services.documentos.embarque_carvia_service import EmbarqueCarViaService
                resultado_expansao = EmbarqueCarViaService.expandir_provisorio(
                    carvia_cotacao_id=cotacao_id,
                    pedido_id=pedido.id,
                    numero_nf=numero_nf,
                )
                logger.info(
                    "expandir_provisorio resultado=%s (cotacao=%s, pedido=%s, nf=%s)",
                    resultado_expansao, cotacao_id, pedido.id, numero_nf,
                )
            except Exception:
                logger.exception(
                    "ERRO expandir_provisorio cotacao=%s pedido=%s nf=%s",
                    cotacao_id, pedido.id, numero_nf,
                )

            db.session.commit()

            msg_nf = 'reutilizada' if nf_reutilizada else 'importada'
            return jsonify({
                'sucesso': True,
                'mensagem': (
                    f'NF {numero_nf} {msg_nf} ({len(dados.get("itens", []))} itens, '
                    f'R$ {dados.get("valor_total") or 0:.2f}). '
                    f'Pedido: {pedido.numero_pedido} ({filial}).'
                ),
                'nf_id': nf.id,
                'pedido_id': pedido.id,
                'numero_pedido': pedido.numero_pedido,
                'pedido_criado': pedido_criado,
                'nf_reutilizada': nf_reutilizada,
            })

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao anexar NF na cotacao %s: %s", cotacao_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== API: NFs SEM COTACAO ====================

    @bp.route('/api/nfs-sem-cotacao') # type: ignore
    @login_required
    def api_listar_nfs_sem_cotacao(): # type: ignore
        """Lista CarviaNfs sem vinculo a CarviaPedidoItem (ATIVA + status != CANCELADA).

        Query params opcionais:
          - cnpj_emitente: filtro exato
          - cnpj_destinatario: filtro exato
          - limit: default 100
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaNf, CarviaPedidoItem

        limit = request.args.get('limit', default=100, type=int)
        cnpj_emit = (request.args.get('cnpj_emitente') or '').strip()
        cnpj_dest = (request.args.get('cnpj_destinatario') or '').strip()

        # Subquery: numeros de NF ja vinculados a qualquer CarviaPedidoItem
        subq_vinculadas = db.session.query(
            CarviaPedidoItem.numero_nf
        ).filter(
            CarviaPedidoItem.numero_nf.isnot(None),
            CarviaPedidoItem.numero_nf != '',
        ).distinct().subquery()

        q = CarviaNf.query.filter(
            CarviaNf.status == 'ATIVA',
            CarviaNf.numero_nf.notin_(db.session.query(subq_vinculadas)),
        )
        if cnpj_emit:
            q = q.filter(CarviaNf.cnpj_emitente == cnpj_emit)
        if cnpj_dest:
            q = q.filter(CarviaNf.cnpj_destinatario == cnpj_dest)

        nfs = q.order_by(CarviaNf.data_emissao.desc().nullslast(),
                         CarviaNf.id.desc()).limit(limit).all()

        return jsonify({
            'nfs': [{
                'id': n.id,
                'numero_nf': n.numero_nf,
                'chave_acesso_nf': n.chave_acesso_nf,
                'cnpj_emitente': n.cnpj_emitente,
                'nome_emitente': n.nome_emitente,
                'cnpj_destinatario': n.cnpj_destinatario,
                'nome_destinatario': n.nome_destinatario,
                'uf_emitente': n.uf_emitente,
                'uf_destinatario': n.uf_destinatario,
                'peso_bruto': float(n.peso_bruto) if n.peso_bruto else None,
                'valor_total': float(n.valor_total) if n.valor_total else None,
                'quantidade_volumes': n.quantidade_volumes,
                'data_emissao': n.data_emissao.isoformat() if n.data_emissao else None,
            } for n in nfs],
            'total': len(nfs),
        })

    @bp.route('/api/nfs-sem-cotacao/count-similares') # type: ignore
    @login_required
    def api_count_nfs_similares(): # type: ignore
        """Conta CarviaNfs sem cotacao com mesmo (cnpj_emitente, cnpj_destinatario).

        Query params:
          - cnpj_emitente (obrigatorio)
          - cnpj_destinatario (obrigatorio)
          - exclude_nf_id: ID de NF a excluir da contagem (ja selecionada)
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaNf, CarviaPedidoItem

        cnpj_emit = (request.args.get('cnpj_emitente') or '').strip()
        cnpj_dest = (request.args.get('cnpj_destinatario') or '').strip()
        exclude_id = request.args.get('exclude_nf_id', type=int)

        if not cnpj_emit or not cnpj_dest:
            return jsonify({'erro': 'cnpj_emitente e cnpj_destinatario obrigatorios.'}), 400

        subq_vinculadas = db.session.query(
            CarviaPedidoItem.numero_nf
        ).filter(
            CarviaPedidoItem.numero_nf.isnot(None),
            CarviaPedidoItem.numero_nf != '',
        ).distinct().subquery()

        q = CarviaNf.query.filter(
            CarviaNf.status == 'ATIVA',
            CarviaNf.cnpj_emitente == cnpj_emit,
            CarviaNf.cnpj_destinatario == cnpj_dest,
            CarviaNf.numero_nf.notin_(db.session.query(subq_vinculadas)),
        )
        if exclude_id:
            q = q.filter(CarviaNf.id != exclude_id)

        return jsonify({
            'count': q.count(),
            'cnpj_emitente': cnpj_emit,
            'cnpj_destinatario': cnpj_dest,
        })

    # ==================== API: ENDERECOS DO CLIENTE ====================

    @bp.route('/api/cotacoes/enderecos-cliente/<int:cliente_id>') # type: ignore
    @login_required
    def api_enderecos_cliente_cotacao(cliente_id): # type: ignore
        """Lista enderecos para dropdown na cotacao.

        Retorna:
        - Origens GLOBAIS (cliente_id IS NULL, tipo=ORIGEM) — compartilhadas
        - Destinos do CLIENTE (cliente_id=cliente_id, tipo=DESTINO)
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaClienteEndereco
        from sqlalchemy import or_

        enderecos = CarviaClienteEndereco.query.filter(
            CarviaClienteEndereco.ativo == True,
            or_(
                # Origens globais (compartilhadas)
                db.and_(
                    CarviaClienteEndereco.tipo == 'ORIGEM',
                    CarviaClienteEndereco.cliente_id.is_(None),
                ),
                # Destinos do cliente
                db.and_(
                    CarviaClienteEndereco.tipo == 'DESTINO',
                    CarviaClienteEndereco.cliente_id == cliente_id,
                ),
            )
        ).order_by(
            CarviaClienteEndereco.tipo,
        ).all()

        def _serializar(e):
            doc = e.cnpj or 'PROVISORIO'
            prov = ' [PROVISORIO]' if e.provisorio else ''
            return {
                'id': e.id,
                'cnpj': e.cnpj,
                'razao_social': e.razao_social,
                'tipo': e.tipo,
                'provisorio': e.provisorio,
                'fisico_uf': e.fisico_uf,
                'fisico_cidade': e.fisico_cidade,
                'fisico_logradouro': e.fisico_logradouro,
                'fisico_numero': e.fisico_numero,
                'fisico_bairro': e.fisico_bairro,
                'fisico_cep': e.fisico_cep,
                'fisico_complemento': e.fisico_complemento,
                'label': f'{doc} - {e.razao_social or "Sem razao"} ({e.fisico_cidade}/{e.fisico_uf}) [{e.tipo}]{prov}',
            }

        return jsonify({
            'enderecos': [_serializar(e) for e in enderecos]
        })

    # ==================== API: ORIGENS GLOBAIS ====================

    @bp.route('/api/cotacoes/origens-globais') # type: ignore
    @login_required
    def api_listar_origens_globais(): # type: ignore
        """Lista origens globais para selecao no modal Importar NF."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.clientes.cliente_service import CarviaClienteService

        origens = CarviaClienteService.listar_origens_globais()
        return jsonify({
            'origens': [
                {
                    'id': o.id,
                    'cnpj': o.cnpj,
                    'razao_social': o.razao_social,
                    'cidade': o.fisico_cidade,
                    'uf': o.fisico_uf,
                    'label': f'{o.cnpj} - {o.razao_social or "Sem razao"} ({o.fisico_cidade}/{o.fisico_uf})',
                }
                for o in origens
            ]
        })

    # ==================== API: BUSCAR CLIENTES (autocomplete wizard) ====================

    @bp.route('/api/cotacoes/buscar-clientes') # type: ignore
    @login_required
    def api_buscar_clientes_cotacao(): # type: ignore
        """Lista clientes ativos (wizard step 1).

        Query params:
            busca: texto para filtrar por nome (ilike) — opcional
        Retorna lista de {id, nome_comercial} (max 500 resultados —
        cabe a base inteira de clientes ativos da CarVia; o <select>
        nativo ordena alfabeticamente para localizacao visual).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaCliente

        busca = request.args.get('busca', '').strip()
        query = CarviaCliente.query.filter_by(ativo=True)
        if busca:
            query = query.filter(CarviaCliente.nome_comercial.ilike(f'%{busca}%'))

        clientes = query.order_by(CarviaCliente.nome_comercial).limit(500).all()
        return jsonify({
            'clientes': [
                {'id': c.id, 'nome_comercial': c.nome_comercial}
                for c in clientes
            ]
        })

    # ==================== API: EDITAR ENDERECO INLINE ====================

    @bp.route('/api/cotacoes/enderecos/<int:endereco_id>', methods=['PATCH']) # type: ignore
    @login_required
    def api_editar_endereco_cotacao(endereco_id): # type: ignore
        """Edita campos fisico_* de um endereco — acessivel da tela de cotacao.

        Guard: bloqueia se endereco pertence a cotacao APROVADA/CANCELADA (sem criacao_tardia).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        # Guard: verificar se endereco esta vinculado a cotacao bloqueada
        from app.carvia.models import CarviaClienteEndereco, CarviaCotacao
        endereco = db.session.get(CarviaClienteEndereco, endereco_id)
        if not endereco:
            return jsonify({'erro': 'Endereco nao encontrado.'}), 404

        cotacao_bloqueada = CarviaCotacao.query.filter(
            db.or_(
                CarviaCotacao.endereco_origem_id == endereco_id,
                CarviaCotacao.endereco_destino_id == endereco_id,
            ),
            CarviaCotacao.status.in_(['APROVADO', 'CANCELADO']),
            CarviaCotacao.criacao_tardia.is_(False),
        ).first()
        if cotacao_bloqueada:
            return jsonify({
                'erro': f'Endereco vinculado a cotacao {cotacao_bloqueada.numero_cotacao} '
                        f'({cotacao_bloqueada.status}). Reabra a cotacao para editar.',
            }), 400

        from app.carvia.services.clientes.cliente_service import CarviaClienteService

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados obrigatorios.'}), 400

        ok, erro, contexto = CarviaClienteService.atualizar_endereco(endereco_id, data)
        if not ok:
            resp = {'erro': erro}
            if contexto:
                resp.update(contexto)
            status = 409 if contexto and contexto.get('acao_sugerida') == 'mesclar' else 400
            return jsonify(resp), status
        db.session.commit()
        return jsonify({'sucesso': True})

    # ==================== API: DESTINO PROVISORIO ====================

    @bp.route('/api/cotacoes/destino-provisorio', methods=['POST']) # type: ignore
    @login_required
    def api_criar_destino_provisorio(): # type: ignore
        """Cria destino provisorio sem CNPJ para cotacao de frete."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.clientes.cliente_service import CarviaClienteService

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados obrigatorios.'}), 400

        cliente_id = data.get('cliente_id')
        if not cliente_id:
            return jsonify({'erro': 'cliente_id obrigatorio.'}), 400

        endereco, erro = CarviaClienteService.adicionar_destino_provisorio(
            cliente_id=cliente_id,
            criado_por=current_user.email,
            razao_social=data.get('razao_social'),
            dados_fisico=data.get('fisico'),
        )
        if erro:
            return jsonify({'erro': erro}), 400

        db.session.commit()
        return jsonify({
            'sucesso': True,
            'endereco_id': endereco.id,
            'label': f'PROVISORIO - {endereco.razao_social or "Sem razao"} ({endereco.fisico_cidade}/{endereco.fisico_uf}) [DESTINO] [PROVISORIO]',
        })

    # ==================================================================
    # Emissao CTe SSW a partir da Cotacao
    # ==================================================================

    @bp.route('/api/cotacoes/<int:cotacao_id>/preview-emissao-cte', methods=['GET']) # type: ignore
    @login_required
    def api_preview_emissao_cte(cotacao_id): # type: ignore
        """Preview dos dados que serao usados para emissao de CTe.

        Valida premissas (APROVADO, NFs completas) e retorna
        resumo dos dados para confirmacao do usuario.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carvia.models import (
            CarviaCotacao, CarviaPedido, CarviaPedidoItem,
            CarviaNf, CarviaCotacaoMoto, CarviaEmissaoCte,
        )
        import random

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return jsonify({'erro': 'Cotacao nao encontrada'}), 404

        # --- Premissa 1: status APROVADO ---
        if cotacao.status != 'APROVADO':
            return jsonify({
                'erro': f'Cotacao deve estar APROVADA para emitir CTe (status atual: {cotacao.status})',
                'bloqueio': 'STATUS',
            }), 400

        # --- Premissa 2: todos os pedidos devem ter NF ---
        pedidos = CarviaPedido.query.filter(
            CarviaPedido.cotacao_id == cotacao_id,
            CarviaPedido.status != 'CANCELADO',
        ).all()

        if not pedidos:
            return jsonify({
                'erro': 'Cotacao nao possui pedidos. Crie pedidos e anexe NFs antes de emitir CTe.',
                'bloqueio': 'SEM_PEDIDOS',
            }), 400

        itens_sem_nf = []
        nf_numeros = set()
        for ped in pedidos:
            for item in ped.itens.all():
                if not item.numero_nf:
                    itens_sem_nf.append({
                        'pedido': ped.numero_pedido,
                        'descricao': item.descricao,
                        'quantidade': item.quantidade,
                    })
                else:
                    nf_numeros.add(item.numero_nf)

        if itens_sem_nf:
            return jsonify({
                'erro': f'{len(itens_sem_nf)} item(ns) sem NF vinculada. Anexe NFs a todos os itens antes de emitir.',
                'bloqueio': 'NF_INCOMPLETA',
                'itens_sem_nf': itens_sem_nf,
            }), 400

        # --- Buscar NFs com chave de acesso ---
        nfs_para_emitir = []
        nfs_sem_chave = []
        for nf_num in sorted(nf_numeros):
            nf = CarviaNf.query.filter_by(numero_nf=str(nf_num)).first()
            if not nf:
                nfs_sem_chave.append(nf_num)
                continue
            if not nf.chave_acesso_nf or len(nf.chave_acesso_nf) != 44:
                nfs_sem_chave.append(nf_num)
                continue

            # Verificar se ja existe emissao em andamento
            em_andamento = CarviaEmissaoCte.query.filter(
                CarviaEmissaoCte.nf_id == nf.id,
                CarviaEmissaoCte.status.in_(['PENDENTE', 'EM_PROCESSAMENTO']),
            ).first()

            nfs_para_emitir.append({
                'nf_id': nf.id,
                'numero_nf': nf.numero_nf,
                'chave_acesso': nf.chave_acesso_nf,
                'valor_total': float(nf.valor_total) if nf.valor_total else None,
                'peso_bruto': float(nf.peso_bruto) if nf.peso_bruto else None,
                'em_andamento': em_andamento.id if em_andamento else None,
            })

        if nfs_sem_chave:
            return jsonify({
                'erro': f'NF(s) sem chave de acesso valida: {", ".join(nfs_sem_chave)}. Importe o XML da NF primeiro.',
                'bloqueio': 'SEM_CHAVE',
                'nfs_sem_chave': nfs_sem_chave,
            }), 400

        # --- Montar dados de medidas (motos) ---
        medidas = []
        motos = CarviaCotacaoMoto.query.filter_by(cotacao_id=cotacao_id).all()
        for moto in motos:
            modelo = moto.modelo_moto
            medidas.append({
                'modelo_id': moto.modelo_moto_id,
                'modelo_nome': modelo.nome if modelo else '?',
                'comp_cm': float(modelo.comprimento) if modelo else 0,
                'larg_cm': float(modelo.largura) if modelo else 0,
                'alt_cm': float(modelo.altura) if modelo else 0,
                'qtd': moto.quantidade,
            })

        # --- CNPJ tomador (destinatario) ---
        dest = cotacao.endereco_destino
        cnpj_tomador = dest.cnpj if dest else None

        # --- Placa ---
        placa = 'ARMAZEM' if cotacao.tipo_carga == 'FRACIONADA' else ''

        # --- Gerar captcha (3 numeros aleatorios) ---
        captcha = str(random.randint(100, 999))

        return jsonify({
            'sucesso': True,
            'cotacao': {
                'id': cotacao.id,
                'numero': cotacao.numero_cotacao,
                'cliente': cotacao.cliente.nome_comercial if cotacao.cliente else '?',
                'destino': f'{dest.fisico_cidade}/{dest.fisico_uf}' if dest else '?',
                'valor_frete': float(cotacao.valor_final_aprovado) if cotacao.valor_final_aprovado else None,
                'tipo_carga': cotacao.tipo_carga,
                'tipo_material': cotacao.tipo_material,
            },
            'nfs': nfs_para_emitir,
            'medidas': medidas,
            'placa': placa,
            'cnpj_tomador': cnpj_tomador,
            'captcha': captcha,
        })

    @bp.route('/api/cotacoes/<int:cotacao_id>/emitir-cte', methods=['POST']) # type: ignore
    @login_required
    def api_emitir_cte_cotacao(cotacao_id): # type: ignore
        """Dispara emissao de CTe SSW para todas NFs da cotacao.

        Body JSON:
            captcha_resposta: str  — deve bater com captcha gerado
            captcha_esperado: str  — captcha original (validado server-side)
            incluir_fatura: bool   — se True, gera fatura 437 alem do CTe
            data_vencimento: str   — YYYY-MM-DD (obrigatorio se incluir_fatura)
            placa: str             — default ARMAZEM

        Returns 202:
            {emissoes: [{nf_id, emissao_id, status}]}
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Body JSON obrigatorio'}), 400

        # --- Validar captcha ---
        captcha_resp = str(data.get('captcha_resposta', '')).strip()
        captcha_esperado = str(data.get('captcha_esperado', '')).strip()
        if not captcha_resp or captcha_resp != captcha_esperado:
            return jsonify({'erro': 'Codigo de confirmacao incorreto'}), 400

        incluir_fatura = data.get('incluir_fatura', False)

        # --- Parsear data_vencimento ---
        data_vencimento = None
        if incluir_fatura:
            if not data.get('data_vencimento'):
                return jsonify({'erro': 'data_vencimento obrigatoria para emissao com fatura'}), 400
            try:
                from datetime import datetime
                data_vencimento = datetime.strptime(
                    data['data_vencimento'], '%Y-%m-%d'
                ).date()
            except ValueError:
                return jsonify({'erro': 'data_vencimento invalida (YYYY-MM-DD)'}), 400

        from app.carvia.models import (
            CarviaCotacao, CarviaPedido, CarviaNf, CarviaCotacaoMoto,
        )

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao or cotacao.status != 'APROVADO':
            return jsonify({'erro': 'Cotacao nao encontrada ou nao APROVADA'}), 400

        # --- Coletar NFs unicas dos pedidos ---
        pedidos = CarviaPedido.query.filter(
            CarviaPedido.cotacao_id == cotacao_id,
            CarviaPedido.status != 'CANCELADO',
        ).all()

        nf_numeros = set()
        for ped in pedidos:
            for item in ped.itens.all():
                if item.numero_nf:
                    nf_numeros.add(item.numero_nf)

        if not nf_numeros:
            return jsonify({'erro': 'Nenhuma NF encontrada nos pedidos'}), 400

        # --- Resolver NF IDs ---
        nf_ids = []
        for nf_num in sorted(nf_numeros):
            nf = CarviaNf.query.filter_by(numero_nf=str(nf_num)).first()
            if nf and nf.chave_acesso_nf and len(nf.chave_acesso_nf) == 44:
                nf_ids.append(nf.id)

        if not nf_ids:
            return jsonify({'erro': 'Nenhuma NF com chave de acesso valida'}), 400

        # --- Montar medidas ---
        medidas = []
        motos = CarviaCotacaoMoto.query.filter_by(cotacao_id=cotacao_id).all()
        for moto in motos:
            if moto.modelo_moto_id and moto.quantidade:
                medidas.append({
                    'modelo_id': moto.modelo_moto_id,
                    'qtd': moto.quantidade,
                })

        # --- CNPJ tomador ---
        dest = cotacao.endereco_destino
        cnpj_tomador = dest.cnpj if (dest and incluir_fatura) else None

        placa = data.get('placa', 'ARMAZEM')
        frete_valor = float(cotacao.valor_final_aprovado) if cotacao.valor_final_aprovado else 0

        if frete_valor <= 0:
            return jsonify({'erro': 'Cotacao sem valor de frete aprovado'}), 400

        # --- Disparar emissao via SswEmissaoService ---
        try:
            from app.carvia.services.documentos.ssw_emissao_service import SswEmissaoService
            resultados = SswEmissaoService.preparar_emissao_lote(
                nf_ids=nf_ids,
                placa=placa,
                cnpj_tomador=cnpj_tomador,
                frete_valor=frete_valor,
                data_vencimento=data_vencimento,
                medidas_motos=medidas if medidas else None,
                usuario=current_user.email,
            )
            return jsonify({
                'sucesso': True,
                'emissoes': resultados,
                'cotacao_id': cotacao_id,
                'incluir_fatura': incluir_fatura,
            }), 202

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao emitir CTe cotacao {cotacao_id}: {e}")
            return jsonify({'erro': str(e)}), 500
