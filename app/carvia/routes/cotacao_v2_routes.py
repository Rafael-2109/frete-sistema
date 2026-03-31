"""
Rotas de Cotacao Comercial CarVia — Fluxo proativo
"""

import logging
from datetime import datetime
from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)


def register_cotacao_v2_routes(bp):

    # ==================== LISTAR ====================

    @bp.route('/cotacoes') # type: ignore
    @login_required
    def listar_cotacoes_v2(): # type: ignore
        """Lista cotacoes comerciais"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

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
                from app.carvia.services.nfe_xml_parser import NFeXMLParser
                parser = NFeXMLParser(conteudo)
                if not parser.is_valid():
                    return jsonify({'erro': 'XML invalido.'}), 400
                if not parser.is_nfe():
                    return jsonify({'erro': 'XML nao e NF-e (modelo 55).'}), 400
                dados = parser.get_todas_informacoes()
            else:
                from app.carvia.services.danfe_pdf_parser import DanfePDFParser
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

        from app.carvia.services.cliente_service import CarviaClienteService
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
                from app.carvia.services.nfe_xml_parser import NFeXMLParser
                parser = NFeXMLParser(conteudo)
                if not parser.is_valid() or not parser.is_nfe():
                    return jsonify({'erro': 'XML invalido ou nao e NF-e.'}), 400
                dados = parser.get_todas_informacoes()
            else:
                from app.carvia.services.danfe_pdf_parser import DanfePDFParser
                parser = DanfePDFParser(pdf_bytes=conteudo)
                if not parser.is_valid():
                    return jsonify({'erro': 'PDF invalido.'}), 400
                dados = parser.get_todas_informacoes()

            cnpj_emitente = dados.get('cnpj_emitente') or ''
            cnpj_dest = dados.get('cnpj_destinatario') or ''
            import re as _re
            cnpj_emit_limpo = _re.sub(r'\D', '', cnpj_emitente)
            cnpj_dest_limpo = _re.sub(r'\D', '', cnpj_dest)

            # 2. Verificar cliente existente (por CNPJ emitente nos enderecos)
            cliente_id = None
            cliente_nome = None
            enderecos_existentes = CarviaClienteService.buscar_enderecos_por_cnpj(
                cnpj_emit_limpo
            ) if cnpj_emit_limpo else []
            for end in enderecos_existentes:
                if end.cliente_id and end.cliente:
                    cliente_id = end.cliente_id
                    cliente_nome = end.cliente.nome_comercial
                    break

            # Tambem checar pelo CNPJ destino
            if not cliente_id and cnpj_dest_limpo:
                enderecos_dest = CarviaClienteService.buscar_enderecos_por_cnpj(
                    cnpj_dest_limpo
                )
                for end in enderecos_dest:
                    if end.cliente_id and end.cliente:
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
                    from app.carvia.services.moto_recognition_service import MotoRecognitionService
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
        from app.carvia.services.cliente_service import CarviaClienteService

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
            ).first()

            if existing_pedido and existing_pedido.cotacao:
                aviso_cotacao_existente = True
                cotacao_existente_info = {
                    'cotacao_id': existing_pedido.cotacao.id,
                    'numero_cotacao': existing_pedido.cotacao.numero_cotacao,
                    'status': existing_pedido.cotacao.status,
                }

            # 2. Buscar cliente existente por CNPJ emitente
            cliente_id = None
            cliente_nome = None
            enderecos_existentes = CarviaClienteService.buscar_enderecos_por_cnpj(
                cnpj_emit_limpo
            )
            for end in enderecos_existentes:
                if end.cliente_id and end.cliente:
                    cliente_id = end.cliente_id
                    cliente_nome = end.cliente.nome_comercial
                    break

            # Tambem checar pelo CNPJ destino
            if not cliente_id and cnpj_dest_limpo:
                enderecos_dest = CarviaClienteService.buscar_enderecos_por_cnpj(
                    cnpj_dest_limpo
                )
                for end in enderecos_dest:
                    if end.cliente_id and end.cliente:
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
                ).first()
                if orig_global:
                    endereco_origem_id = orig_global.id

            # Buscar destino do cliente
            if cliente_id and cnpj_dest_limpo:
                dest = CarviaClienteEndereco.query.filter_by(
                    cliente_id=cliente_id, cnpj=cnpj_dest_limpo, tipo='DESTINO'
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
                    from app.carvia.services.moto_recognition_service import MotoRecognitionService
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

            return jsonify({
                'sucesso': True,
                'nf_id': nf.id,
                'aviso_cotacao_existente': aviso_cotacao_existente,
                'cotacao_existente_info': cotacao_existente_info,
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

        from app.carvia.services.cliente_service import CarviaClienteService

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        nome = (data.get('nome_comercial') or '').strip()
        if not nome:
            return jsonify({'erro': 'Nome comercial obrigatorio.'}), 400

        try:
            # Guard: verificar se cliente ja existe pelo CNPJ do emitente
            cliente_existente = None
            orig_data = data.get('origem', {})
            cnpj_orig = orig_data.get('cnpj', '')
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
                # 1. Criar cliente
                cliente, erro = CarviaClienteService.criar_cliente(
                    nome_comercial=nome,
                    criado_por=current_user.email,
                )
                if erro:
                    return jsonify({'erro': erro}), 400

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
                    principal=True,
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

        from app.carvia.services.cliente_service import CarviaClienteService

        def _ctx_criar():
            """Contexto compartilhado GET + erro POST."""
            from app.carvia.models import CarviaModeloMoto
            import json as json_lib
            modelos_raw = CarviaModeloMoto.query.filter_by(ativo=True).order_by(
                CarviaModeloMoto.nome.asc()
            ).all()
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
            }

        if request.method == 'GET':
            nf_id_param = request.args.get('nf_id', type=int)
            return render_template(
                'carvia/cotacoes/criar.html',
                nf_id_param=nf_id_param,
                **_ctx_criar(),
            )

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

        # Preservar nf_id para re-render em caso de erro
        nf_id_param = request.form.get('nf_id_existente', type=int)

        try:
            # Parse datas
            data_exp = request.form.get('data_expedicao')
            data_ag = request.form.get('data_agenda')

            cotacao, erro = CotacaoV2Service.criar_cotacao(
                cliente_id=int(request.form.get('cliente_id', 0)),
                endereco_origem_id=int(request.form.get('endereco_origem_id', 0)),
                endereco_destino_id=int(request.form.get('endereco_destino_id', 0)),
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
            )

            if erro:
                flash(erro, 'danger')
                return render_template(
                    'carvia/cotacoes/criar.html',
                    nf_id_param=nf_id_param,
                    **_ctx_criar(),
                )

            # tipo_carga
            tipo_carga = request.form.get('tipo_carga', 'FRACIONADA')
            if tipo_carga in ('DIRETA', 'FRACIONADA'):
                cotacao.tipo_carga = tipo_carga

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

            # Auto-cotar apos criacao
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

                        pedido.status = 'FATURADO'
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
        from app.carvia.models import CarviaNf
        veiculos_por_nf = {}
        for ped in pedidos:
            for item in ped.itens.all():
                if item.numero_nf and item.numero_nf not in veiculos_por_nf:
                    nf_obj = CarviaNf.query.filter_by(
                        numero_nf=str(item.numero_nf)
                    ).order_by(CarviaNf.id.desc()).first()
                    if nf_obj:
                        veiculos_por_nf[item.numero_nf] = nf_obj.veiculos.all()

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
        from app.carvia.services.cliente_service import CarviaClienteService
        clientes = CarviaClienteService.listar_clientes(apenas_ativos=True)

        # Limite desconto para UI
        from app.carvia.services.config_service import CarviaConfigService
        limite_desconto = CarviaConfigService.limite_desconto_percentual()

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

        try:
            # Campos de referencia
            if 'cliente_id' in data and data['cliente_id']:
                cotacao.cliente_id = int(data['cliente_id'])
            if 'endereco_origem_id' in data and data['endereco_origem_id']:
                cotacao.endereco_origem_id = int(data['endereco_origem_id'])
            if 'endereco_destino_id' in data and data['endereco_destino_id']:
                cotacao.endereco_destino_id = int(data['endereco_destino_id'])
            if 'tipo_material' in data and data['tipo_material'] in ('CARGA_GERAL', 'MOTO'):
                cotacao.tipo_material = data['tipo_material']

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

        try:
            # --- Atualizar campos header ---
            if data.get('cliente_id'):
                cotacao.cliente_id = int(data['cliente_id'])
            if data.get('endereco_origem_id'):
                cotacao.endereco_origem_id = int(data['endereco_origem_id'])
            if data.get('endereco_destino_id'):
                cotacao.endereco_destino_id = int(data['endereco_destino_id'])
            if data.get('tipo_material') in ('CARGA_GERAL', 'MOTO'):
                cotacao.tipo_material = data['tipo_material']
            if data.get('tipo_carga') in ('DIRETA', 'FRACIONADA'):
                cotacao.tipo_carga = data['tipo_carga']

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

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

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

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

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

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

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

    # ==================== API: STATUS ====================

    @bp.route('/api/cotacoes/<int:cotacao_id>/enviar', methods=['POST']) # type: ignore
    @login_required
    def api_enviar_cotacao(cotacao_id): # type: ignore
        """Marca como ENVIADO"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

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

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

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

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

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

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

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

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

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

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

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

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

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

        from app.carvia.services.cotacao_v2_service import CotacaoV2Service

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

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return jsonify({'erro': 'Cotacao nao encontrada.'}), 404
        if cotacao.status != 'APROVADO':
            return jsonify({'erro': f'Cotacao em status {cotacao.status}, esperado APROVADO.'}), 400

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
                from app.carvia.services.nfe_xml_parser import NFeXMLParser
                parser = NFeXMLParser(conteudo)
                if not parser.is_valid():
                    return jsonify({'erro': 'XML invalido.'}), 400
                if not parser.is_nfe():
                    return jsonify({'erro': 'XML nao e NF-e (modelo 55). Pode ser CTe.'}), 400
                dados = parser.get_todas_informacoes()
            else:
                from app.carvia.services.danfe_pdf_parser import DanfePDFParser
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

            # 6. Atualizar status do pedido
            if pedido.status == 'ABERTO':
                pedido.status = 'FATURADO'

            db.session.flush()

            # 7. Expandir provisorio no embarque (nao-bloqueante)
            resultado_expansao = None
            try:
                from app.carvia.services.embarque_carvia_service import EmbarqueCarViaService
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
            CarviaClienteEndereco.principal.desc()
        ).all()

        def _serializar(e):
            doc = e.cnpj or 'PROVISORIO'
            prov = ' [PROVISORIO]' if e.provisorio else ''
            return {
                'id': e.id,
                'cnpj': e.cnpj,
                'razao_social': e.razao_social,
                'tipo': e.tipo,
                'principal': e.principal,
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

        from app.carvia.services.cliente_service import CarviaClienteService

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

    # ==================== API: EDITAR ENDERECO INLINE ====================

    @bp.route('/api/cotacoes/enderecos/<int:endereco_id>', methods=['PATCH']) # type: ignore
    @login_required
    def api_editar_endereco_cotacao(endereco_id): # type: ignore
        """Edita campos fisico_* de um endereco — acessivel da tela de cotacao."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.cliente_service import CarviaClienteService

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados obrigatorios.'}), 400

        ok, erro = CarviaClienteService.atualizar_endereco(endereco_id, data)
        if not ok:
            return jsonify({'erro': erro}), 400
        db.session.commit()
        return jsonify({'sucesso': True})

    # ==================== API: DESTINO PROVISORIO ====================

    @bp.route('/api/cotacoes/destino-provisorio', methods=['POST']) # type: ignore
    @login_required
    def api_criar_destino_provisorio(): # type: ignore
        """Cria destino provisorio sem CNPJ para cotacao de frete."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.services.cliente_service import CarviaClienteService

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
