"""
Rotas de Pedidos CarVia — CRUD vinculado a cotacao
"""

import logging
from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)


def register_pedido_routes(bp):

    @bp.route('/pedidos-carvia')
    @login_required
    def listar_pedidos_carvia():
        """Lista pedidos CarVia

        Filtra pedidos cujas cotacoes estao em status "em edicao" ou finalizados:
        - Esconde: RASCUNHO, PENDENTE_ADMIN, RECUSADO, CANCELADO
        - Exibe: ENVIADO, APROVADO
        Cotacao ainda em edicao gera pedidos apenas internamente (visiveis na tela
        de detalhe da cotacao, mas NAO na listagem publica de pedidos).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaPedido, CarviaCotacao
        from collections import Counter

        status = request.args.get('status')
        cotacao_id = request.args.get('cotacao_id', type=int)

        # Filtro por status de COTACAO pai: apenas ENVIADO e APROVADO
        # aparecem na listagem publica de pedidos (cotacoes em edicao
        # ou finalizadas sem sucesso permanecem invisiveis aqui).
        query = CarviaPedido.query.join(
            CarviaCotacao, CarviaPedido.cotacao_id == CarviaCotacao.id
        ).filter(
            CarviaCotacao.status.in_(['ENVIADO', 'APROVADO'])
        )
        if cotacao_id:
            query = query.filter(CarviaPedido.cotacao_id == cotacao_id)

        todos = query.order_by(CarviaPedido.criado_em.desc()).all()

        # Contadores por status_calculado (property, nao coluna DB)
        contadores = Counter(p.status_calculado for p in todos)

        # Filtrar por status_calculado (nao pela coluna DB)
        if status:
            pedidos = [p for p in todos if p.status_calculado == status]
        else:
            pedidos = todos

        # Pre-build NFs, embarque, peso/valor/qtd, emitente/destino por pedido
        from app.carvia.models import CarviaNf, CarviaPedidoItem
        from app.embarques.models import EmbarqueItem, Embarque
        from sqlalchemy import func as sqlfunc

        nfs_por_pedido = {}
        embarques_por_pedido = {}
        peso_por_pedido = {}  # float kg
        valor_por_pedido = {}  # float R$
        qtd_por_pedido = {}    # int (soma CarviaPedidoItem.quantidade)
        emitente_por_pedido = {}    # cotacao.endereco_origem
        destino_por_pedido = {}     # cotacao.endereco_destino

        ped_ids = [p.id for p in pedidos]

        # Batch: somar quantidade e valor dos CarviaPedidoItem por pedido
        if ped_ids:
            rows = db.session.query(
                CarviaPedidoItem.pedido_id,
                sqlfunc.coalesce(sqlfunc.sum(CarviaPedidoItem.quantidade), 0),
                sqlfunc.coalesce(sqlfunc.sum(CarviaPedidoItem.valor_total), 0),
            ).filter(
                CarviaPedidoItem.pedido_id.in_(ped_ids)
            ).group_by(CarviaPedidoItem.pedido_id).all()
            for pid, qtd, valor in rows:
                qtd_por_pedido[pid] = int(qtd or 0)
                valor_por_pedido[pid] = float(valor or 0)

        # NF Triangular: pegar numeros_nf que sao transferencia efetiva
        # para filtra-los da listagem de pedidos
        try:
            from app.carvia.services.documentos.nf_transferencia_service import (
                CarviaNfTransferenciaService as _NFTS3,
            )
            nums_transf_efetivas = _NFTS3.get_nums_transferencia_efetiva()
        except Exception:
            nums_transf_efetivas = set()

        for ped in pedidos:
            itens = ped.itens.all()
            nf_nums = sorted({
                i.numero_nf for i in itens
                if i.numero_nf and i.numero_nf not in nums_transf_efetivas
            })
            nfs_por_pedido[ped.id] = nf_nums

            # Peso: somar peso_bruto das CarviaNfs vinculadas; se nenhuma, fallback 0
            if nf_nums:
                peso_por_pedido[ped.id] = float(
                    db.session.query(
                        sqlfunc.coalesce(sqlfunc.sum(CarviaNf.peso_bruto), 0)
                    ).filter(
                        CarviaNf.numero_nf.in_(nf_nums)
                    ).scalar() or 0
                )
            else:
                peso_por_pedido[ped.id] = 0.0

            # Embarque: primeiro CARVIA-NF-{nf_id} ativo dessas NFs
            for nf_num in nf_nums:
                nf_obj = CarviaNf.query.filter_by(numero_nf=str(nf_num)).first()
                if nf_obj:
                    em = EmbarqueItem.query.filter_by(
                        separacao_lote_id=f'CARVIA-NF-{nf_obj.id}',
                        status='ativo',
                    ).first()
                    if em:
                        embarques_por_pedido[ped.id] = db.session.get(
                            Embarque, em.embarque_id
                        )
                        break

            # Emitente/Destinatario: cotacao.endereco_origem/destino
            cot = ped.cotacao
            if cot:
                emitente_por_pedido[ped.id] = cot.endereco_origem
                destino_por_pedido[ped.id] = cot.endereco_destino

        return render_template(
            'carvia/pedidos/listar.html',
            pedidos=pedidos,
            status_filtro=status,
            contadores=dict(contadores),
            nfs_por_pedido=nfs_por_pedido,
            embarques_por_pedido=embarques_por_pedido,
            peso_por_pedido=peso_por_pedido,
            valor_por_pedido=valor_por_pedido,
            qtd_por_pedido=qtd_por_pedido,
            emitente_por_pedido=emitente_por_pedido,
            destino_por_pedido=destino_por_pedido,
        )

    @bp.route('/pedidos-carvia/<int:pedido_id>')
    @login_required
    def detalhe_pedido_carvia(pedido_id):
        """Detalhe do pedido com itens"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaPedido

        pedido = db.session.get(CarviaPedido, pedido_id)
        if not pedido:
            flash('Pedido nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_pedidos_carvia'))

        itens = pedido.itens.all()

        return render_template(
            'carvia/pedidos/detalhe.html',
            pedido=pedido,
            itens=itens,
        )

    @bp.route('/api/cotacoes/<int:cotacao_id>/pedidos', methods=['POST'])
    @login_required
    def api_criar_pedido(cotacao_id):
        """Cria pedido vinculado a cotacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaCotacao, CarviaPedido
        from app.utils.timezone import agora_utc_naive

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return jsonify({'erro': 'Cotacao nao encontrada.'}), 404
        if cotacao.status == 'CANCELADO':
            return jsonify({'erro': 'Cotacao cancelada nao permite criar pedidos.'}), 400

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        filial = (data.get('filial') or '').upper()
        if filial not in ('SP', 'RJ'):
            return jsonify({'erro': 'Filial deve ser SP ou RJ.'}), 400

        tipo_sep = 'ESTOQUE' if filial == 'SP' else 'CROSSDOCK'

        try:
            pedido = CarviaPedido(
                numero_pedido=CarviaPedido.gerar_numero_pedido(cotacao_id),
                cotacao_id=cotacao_id,
                filial=filial,
                tipo_separacao=tipo_sep,
                observacoes=data.get('observacoes'),
                criado_por=current_user.email,
                criado_em=agora_utc_naive(),
                atualizado_em=agora_utc_naive(),
            )
            db.session.add(pedido)
            db.session.flush()

            # Adicionar itens: se fornecidos no JSON, usar. Senao, copiar motos da cotacao.
            from app.carvia.models import CarviaPedidoItem
            itens_data = data.get('itens', [])
            if itens_data:
                for item_data in itens_data:
                    item = CarviaPedidoItem(
                        pedido_id=pedido.id,
                        modelo_moto_id=item_data.get('modelo_moto_id'),
                        descricao=item_data.get('descricao'),
                        cor=item_data.get('cor'),
                        quantidade=int(item_data.get('quantidade', 1)),
                        valor_unitario=item_data.get('valor_unitario'),
                        valor_total=item_data.get('valor_total'),
                    )
                    db.session.add(item)
            elif cotacao.tipo_material == 'MOTO':
                # Auto-copiar motos da cotacao como itens do pedido
                # valor_unitario = valor do PRODUTO (nao do frete)
                motos = cotacao.motos.all()
                for moto in motos:
                    modelo = moto.modelo_moto
                    # Usar valor do produto da moto (preenchido na cotacao)
                    vlr_unit = float(moto.valor_unitario) if moto.valor_unitario else None
                    vlr_total = float(moto.valor_total) if moto.valor_total else None

                    item = CarviaPedidoItem(
                        pedido_id=pedido.id,
                        modelo_moto_id=moto.modelo_moto_id,
                        descricao=modelo.nome if modelo else 'Moto',
                        cor=None,
                        quantidade=moto.quantidade,
                        valor_unitario=vlr_unit,
                        valor_total=vlr_total,
                    )
                    db.session.add(item)

            db.session.commit()
            return jsonify({
                'sucesso': True,
                'id': pedido.id,
                'numero_pedido': pedido.numero_pedido,
                'mensagem': f'Pedido {pedido.numero_pedido} criado.',
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao criar pedido: %s", e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/pedidos-carvia/<int:pedido_id>/nf', methods=['PUT'])
    @login_required
    def api_anexar_nf_pedido(pedido_id):
        """Anexa numero de NF ao pedido CarVia e expande provisorio no embarque.

        Body JSON: { "numero_nf": "123456" }

        Fluxo:
        1. Preenche CarviaPedidoItem.numero_nf para todos itens do pedido
        2. Se cotacao esta em embarque → cria EmbarqueItem real (expansao)
        3. Se TODOS pedidos da cotacao tem NF → remove provisorio
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaPedido, CarviaPedidoItem

        pedido = db.session.get(CarviaPedido, pedido_id)
        if not pedido:
            return jsonify({'erro': 'Pedido nao encontrado.'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Dados JSON invalidos.'}), 400

        numero_nf = (data.get('numero_nf') or '').strip()
        if not numero_nf:
            return jsonify({'erro': 'numero_nf e obrigatorio.'}), 400

        try:
            # 1. Preencher numero_nf nos itens do pedido
            itens = CarviaPedidoItem.query.filter_by(pedido_id=pedido_id).all()
            for item in itens:
                item.numero_nf = numero_nf

            db.session.flush()

            # 2. Expandir provisorio no embarque (se cotacao esta em algum)
            resultado_expansao = None
            try:
                from app.carvia.services.documentos.embarque_carvia_service import EmbarqueCarViaService
                resultado_expansao = EmbarqueCarViaService.expandir_provisorio(
                    carvia_cotacao_id=pedido.cotacao_id,
                    pedido_id=pedido_id,
                    numero_nf=numero_nf,
                )
            except Exception as e:
                logger.warning(
                    "Erro ao expandir provisorio (nao-bloqueante): %s", e
                )

            # 3. Limpar alerta saida-sem-nf se todos os itens da cotacao agora tem NF
            try:
                from app.carvia.models import CarviaCotacao as _CC
                cot = db.session.get(_CC, pedido.cotacao_id)
                if cot and cot.alerta_saida_sem_nf:
                    from app.embarques.models import EmbarqueItem as _EI
                    still_pending = _EI.query.filter(
                        _EI.carvia_cotacao_id == pedido.cotacao_id,
                        _EI.status == 'ativo',
                        db.or_(
                            _EI.provisorio == True,
                            _EI.nota_fiscal.is_(None),
                            _EI.nota_fiscal == '',
                        )
                    ).count()
                    if still_pending == 0:
                        cot.alerta_saida_sem_nf = False
                        cot.alerta_saida_sem_nf_em = None
                        cot.alerta_saida_embarque_id = None
            except Exception as e:
                logger.warning("Erro ao limpar alerta saida-sem-nf: %s", e)

            db.session.commit()

            resposta = {
                'sucesso': True,
                'mensagem': f'NF {numero_nf} anexada ao pedido {pedido.numero_pedido}.',
                'itens_atualizados': len(itens),
                'status_pedido': pedido.status_calculado,
            }
            if resultado_expansao:
                resposta['embarque'] = resultado_expansao

            return jsonify(resposta)

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao anexar NF ao pedido %s: %s", pedido_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== FILIAL EDITAVEL ====================

    @bp.route('/api/pedidos-carvia/<int:pedido_id>/filial', methods=['PATCH'])
    @login_required
    def api_editar_filial_pedido(pedido_id):
        """Edita filial (SP/RJ) de um pedido CarVia."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaPedido

        pedido = db.session.get(CarviaPedido, pedido_id)
        if not pedido:
            return jsonify({'erro': 'Pedido nao encontrado.'}), 404
        if pedido.status_calculado == 'EMBARCADO':
            return jsonify({'erro': 'Pedido EMBARCADO nao pode ter filial alterada.'}), 400

        data = request.get_json()
        nova_filial = (data.get('filial') or '').upper()
        if nova_filial not in ('SP', 'RJ'):
            return jsonify({'erro': 'Filial deve ser SP ou RJ.'}), 400

        pedido.filial = nova_filial
        pedido.tipo_separacao = 'ESTOQUE' if nova_filial == 'SP' else 'CROSSDOCK'
        db.session.commit()
        return jsonify({'sucesso': True, 'filial': nova_filial, 'tipo_separacao': pedido.tipo_separacao})

    # ==================== DESANEXAR NF ====================

    @bp.route('/api/pedidos-carvia/<int:pedido_id>/desanexar-nf', methods=['POST'])
    @login_required
    def api_desanexar_nf_pedido(pedido_id):
        """Desanexa NF do pedido (limpa numero_nf, reverte status para ABERTO).

        Remove EmbarqueItem CARVIA-NF-* vinculado e devolve saldo ao provisorio.
        O pedido NAO e excluido — apenas volta ao estado ABERTO.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaPedido, CarviaNf
        from app.embarques.models import EmbarqueItem

        pedido = db.session.get(CarviaPedido, pedido_id)
        if not pedido:
            return jsonify({'erro': 'Pedido nao encontrado.'}), 404

        # Desanexo em pedido EMBARCADO: permitido se nenhum CarviaFrete da NF
        # estiver CONFERIDO/FATURADO ou vinculado a fatura cliente.
        # Busca em 2 caminhos: via CarviaOperacao (normal) e via CarviaFrete.numeros_nfs
        # (fallback para fretes sem operacao_id — backfill ou legado).
        aviso_frete = None
        if pedido.status_calculado == 'EMBARCADO':
            nfs_para_check = [i.numero_nf for i in pedido.itens.all() if i.numero_nf]
            if nfs_para_check:
                from app.carvia.models import (
                    CarviaFrete, CarviaOperacao, CarviaOperacaoNf,
                )
                status_bloqueante = db.or_(
                    CarviaFrete.status == 'CONFERIDO',
                    CarviaFrete.status == 'FATURADO',
                    CarviaFrete.status_conferencia == 'APROVADO',
                    CarviaFrete.fatura_cliente_id.isnot(None),
                )

                # Caminho 1: via CarviaOperacao → CarviaOperacaoNf → CarviaNf
                frete_bloqueante = db.session.query(CarviaFrete).join(
                    CarviaOperacao, CarviaFrete.operacao_id == CarviaOperacao.id
                ).join(
                    CarviaOperacaoNf,
                    CarviaOperacaoNf.operacao_id == CarviaOperacao.id
                ).join(
                    CarviaNf, CarviaOperacaoNf.nf_id == CarviaNf.id
                ).filter(
                    CarviaNf.numero_nf.in_(nfs_para_check),
                    status_bloqueante,
                ).first()

                # Caminho 2 (fallback): CarviaFrete sem operacao_id via numeros_nfs CSV
                if not frete_bloqueante:
                    conds_csv = [
                        CarviaFrete.numeros_nfs.ilike(f'%{nf}%')
                        for nf in nfs_para_check
                    ]
                    if conds_csv:
                        frete_bloqueante = db.session.query(CarviaFrete).filter(
                            CarviaFrete.operacao_id.is_(None),
                            db.or_(*conds_csv),
                            status_bloqueante,
                        ).first()

                if frete_bloqueante:
                    return jsonify({
                        'erro': (
                            f'NF possui CarviaFrete #{frete_bloqueante.id} '
                            f'conferido/faturado. Desfaca a conferencia '
                            f'financeira antes de desanexar.'
                        )
                    }), 400
                aviso_frete = (
                    'Embarque ja saiu da portaria. CTe/frete precisa ser '
                    'ajustado manualmente no modulo CarVia.'
                )

        try:
            cotacao_id = pedido.cotacao_id

            # 1. Coletar NFs dos itens do pedido
            nfs_do_pedido = [i.numero_nf for i in pedido.itens.all() if i.numero_nf]
            if not nfs_do_pedido:
                return jsonify({'erro': 'Pedido nao possui NF vinculada.'}), 400

            nf_ids = []
            for nf_num in set(nfs_do_pedido):
                nf_obj = CarviaNf.query.filter_by(numero_nf=str(nf_num)).first()
                if nf_obj:
                    nf_ids.append(nf_obj.id)

            # 2. Remover EmbarqueItems CARVIA-NF-* e somar saldo
            peso_devolver = 0
            valor_devolver = 0
            vol_devolver = 0
            embarque_id_ref = None

            for nf_id in nf_ids:
                lote_nf = f'CARVIA-NF-{nf_id}'
                ei = EmbarqueItem.query.filter_by(
                    separacao_lote_id=lote_nf, status='ativo',
                ).first()
                if ei:
                    peso_devolver += float(ei.peso or 0)
                    valor_devolver += float(ei.valor or 0)
                    vol_devolver += int(ei.volumes or 0)
                    embarque_id_ref = ei.embarque_id
                    db.session.delete(ei)

            # 3. Devolver saldo ao provisorio
            if embarque_id_ref and cotacao_id:
                provisorio = EmbarqueItem.query.filter_by(
                    carvia_cotacao_id=cotacao_id,
                    provisorio=True,
                    status='ativo',
                ).first()

                if provisorio:
                    provisorio.volumes = (provisorio.volumes or 0) + vol_devolver
                    provisorio.peso = (provisorio.peso or 0) + peso_devolver
                    provisorio.valor = (provisorio.valor or 0) + valor_devolver
                elif peso_devolver > 0 or vol_devolver > 0:
                    from app.carvia.models import CarviaCotacao
                    cotacao = db.session.get(CarviaCotacao, cotacao_id)
                    dest = cotacao.endereco_destino if cotacao else None
                    novo_prov = EmbarqueItem(
                        embarque_id=embarque_id_ref,
                        separacao_lote_id=f'CARVIA-COT-{cotacao_id}',
                        cnpj_cliente=dest.cnpj if dest else '',
                        cliente=cotacao.cliente.nome_comercial if cotacao and cotacao.cliente else '',
                        pedido=cotacao.numero_cotacao if cotacao else '',
                        peso=peso_devolver,
                        valor=valor_devolver,
                        pallets=0,
                        uf_destino=dest.fisico_uf if dest else '',
                        cidade_destino=dest.fisico_cidade if dest else '',
                        volumes=vol_devolver,
                        provisorio=True,
                        carvia_cotacao_id=cotacao_id,
                    )
                    db.session.add(novo_prov)

            # 4. Limpar numero_nf dos itens
            for item in pedido.itens.all():
                item.numero_nf = None

            db.session.commit()
            logger.info(
                "NF desanexada do pedido %s (cotacao %s). NFs: %s",
                pedido.numero_pedido, cotacao_id, nfs_do_pedido,
            )
            resposta = {
                'sucesso': True,
                'mensagem': f'NF desanexada. Pedido {pedido.numero_pedido} voltou para ABERTO.',
            }
            if aviso_frete:
                resposta['aviso'] = aviso_frete
            return jsonify(resposta)

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao desanexar NF do pedido %s: %s", pedido_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    # ==================== EXCLUIR PEDIDO ====================

    @bp.route('/api/pedidos-carvia/<int:pedido_id>', methods=['DELETE'])
    @login_required
    def api_excluir_pedido(pedido_id):
        """Exclui pedido CarVia, seus itens e EmbarqueItem vinculado."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        from app.carvia.models import CarviaPedido, CarviaPedidoItem
        from app.embarques.models import EmbarqueItem

        pedido = db.session.get(CarviaPedido, pedido_id)
        if not pedido:
            return jsonify({'erro': 'Pedido nao encontrado.'}), 404

        # Permitir excluir pedido EMBARCADO apenas se nenhum CarviaFrete
        # da NF esta CONFERIDO/FATURADO / vinculado a fatura cliente.
        # Busca em 2 caminhos (idem api_desanexar_nf_pedido): via CarviaOperacao
        # e via CarviaFrete.numeros_nfs CSV (fallback para fretes sem operacao_id).
        aviso_frete = None
        if pedido.status_calculado == 'EMBARCADO':
            from app.carvia.models import CarviaNf as _CN
            nfs_para_check = [i.numero_nf for i in pedido.itens.all() if i.numero_nf]
            if nfs_para_check:
                from app.carvia.models import (
                    CarviaFrete, CarviaOperacao, CarviaOperacaoNf,
                )
                status_bloqueante = db.or_(
                    CarviaFrete.status == 'CONFERIDO',
                    CarviaFrete.status == 'FATURADO',
                    CarviaFrete.status_conferencia == 'APROVADO',
                    CarviaFrete.fatura_cliente_id.isnot(None),
                )

                frete_bloqueante = db.session.query(CarviaFrete).join(
                    CarviaOperacao, CarviaFrete.operacao_id == CarviaOperacao.id
                ).join(
                    CarviaOperacaoNf,
                    CarviaOperacaoNf.operacao_id == CarviaOperacao.id
                ).join(
                    _CN, CarviaOperacaoNf.nf_id == _CN.id
                ).filter(
                    _CN.numero_nf.in_(nfs_para_check),
                    status_bloqueante,
                ).first()

                if not frete_bloqueante:
                    conds_csv = [
                        CarviaFrete.numeros_nfs.ilike(f'%{nf}%')
                        for nf in nfs_para_check
                    ]
                    if conds_csv:
                        frete_bloqueante = db.session.query(CarviaFrete).filter(
                            CarviaFrete.operacao_id.is_(None),
                            db.or_(*conds_csv),
                            status_bloqueante,
                        ).first()

                if frete_bloqueante:
                    return jsonify({
                        'erro': (
                            f'Pedido tem NF com CarviaFrete #{frete_bloqueante.id} '
                            f'conferido/faturado. Desfaca a conferencia '
                            f'financeira antes de excluir o pedido.'
                        )
                    }), 400
                aviso_frete = (
                    'Embarque ja saiu da portaria. CTe/frete precisa ser '
                    'ajustado manualmente no modulo CarVia.'
                )

        try:
            numero = pedido.numero_pedido
            cotacao_id = pedido.cotacao_id

            # 1. Coletar EmbarqueItems de NFs do pedido (CARVIA-NF-*)
            # e o EmbarqueItem do pedido antigo (CARVIA-PED-*)
            nfs_do_pedido = [i.numero_nf for i in pedido.itens.all() if i.numero_nf]
            from app.carvia.models import CarviaNf
            nf_ids = []
            for nf_num in set(nfs_do_pedido):
                nf_obj = CarviaNf.query.filter_by(numero_nf=str(nf_num)).first()
                if nf_obj:
                    nf_ids.append(nf_obj.id)

            # Somar peso/valor/volumes dos EmbarqueItems que serao removidos
            peso_devolver = 0
            valor_devolver = 0
            vol_devolver = 0
            embarque_id_ref = None

            # Helper: delete EntregaRastreada vinculada ANTES do EmbarqueItem.
            # EntregaRastreada.embarque_item_id e NOT NULL sem ondelete=CASCADE,
            # entao autoflush tentaria SET NULL e violaria constraint.
            # Sentry PYTHON-FLASK-JC rastreava esse erro.
            from app.rastreamento.models import EntregaRastreada

            def _delete_embarque_item_com_rastreio(ei_obj):
                EntregaRastreada.query.filter_by(
                    embarque_item_id=ei_obj.id
                ).delete(synchronize_session='fetch')
                db.session.delete(ei_obj)

            for nf_id in nf_ids:
                lote_nf = f'CARVIA-NF-{nf_id}'
                ei = EmbarqueItem.query.filter_by(
                    separacao_lote_id=lote_nf, status='ativo',
                ).first()
                if ei:
                    peso_devolver += float(ei.peso or 0)
                    valor_devolver += float(ei.valor or 0)
                    vol_devolver += int(ei.volumes or 0)
                    embarque_id_ref = ei.embarque_id
                    _delete_embarque_item_com_rastreio(ei)

            # Remover EmbarqueItem antigo (CARVIA-PED-*)
            lote_ped = f'CARVIA-PED-{pedido_id}'
            ei_ped = EmbarqueItem.query.filter_by(
                separacao_lote_id=lote_ped, status='ativo',
            ).first()
            if ei_ped:
                peso_devolver += float(ei_ped.peso or 0)
                valor_devolver += float(ei_ped.valor or 0)
                vol_devolver += int(ei_ped.volumes or 0)
                embarque_id_ref = ei_ped.embarque_id
                _delete_embarque_item_com_rastreio(ei_ped)

            # 2. Devolver saldo ao provisorio
            if embarque_id_ref and cotacao_id:
                provisorio = EmbarqueItem.query.filter_by(
                    carvia_cotacao_id=cotacao_id,
                    provisorio=True,
                    status='ativo',
                ).first()

                if provisorio:
                    provisorio.volumes = (provisorio.volumes or 0) + vol_devolver
                    provisorio.peso = (provisorio.peso or 0) + peso_devolver
                    provisorio.valor = (provisorio.valor or 0) + valor_devolver
                    logger.info(
                        "Provisorio restaurado: +%d vol, +%.1f kg, +%.2f R$ (cotacao %s)",
                        vol_devolver, peso_devolver, valor_devolver, cotacao_id,
                    )
                elif peso_devolver > 0 or vol_devolver > 0:
                    # Recriar provisorio com saldo devolvido
                    from app.carvia.models import CarviaCotacao
                    cotacao = db.session.get(CarviaCotacao, cotacao_id)
                    dest = cotacao.endereco_destino if cotacao else None
                    novo_prov = EmbarqueItem(
                        embarque_id=embarque_id_ref,
                        separacao_lote_id=f'CARVIA-COT-{cotacao_id}',
                        cnpj_cliente=dest.cnpj if dest else '',
                        cliente=cotacao.cliente.nome_comercial if cotacao and cotacao.cliente else '',
                        pedido=cotacao.numero_cotacao if cotacao else '',
                        peso=peso_devolver,
                        valor=valor_devolver,
                        pallets=0,
                        uf_destino=dest.fisico_uf if dest else '',
                        cidade_destino=dest.fisico_cidade if dest else '',
                        volumes=vol_devolver,
                        provisorio=True,
                        carvia_cotacao_id=cotacao_id,
                    )
                    db.session.add(novo_prov)
                    logger.info(
                        "Provisorio RECRIADO: vol=%d, peso=%.1f, valor=%.2f (cotacao %s, embarque %s)",
                        vol_devolver, peso_devolver, valor_devolver, cotacao_id, embarque_id_ref,
                    )

            # 3. Remover itens do pedido
            CarviaPedidoItem.query.filter_by(
                pedido_id=pedido_id
            ).delete(synchronize_session='fetch')

            # 4. Remover pedido
            db.session.delete(pedido)
            db.session.commit()

            logger.info("Pedido %s excluido com restauracao (cotacao %s)", numero, cotacao_id)
            resposta = {
                'sucesso': True,
                'mensagem': f'Pedido {numero} excluido. Saldo restaurado.',
            }
            if aviso_frete:
                resposta['aviso'] = aviso_frete
            return jsonify(resposta)

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao excluir pedido %s: %s", pedido_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500
