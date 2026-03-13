"""
Rotas de Sessao de Cotacao CarVia
==================================

CRUD sessoes de cotacao + endpoints AJAX para cotar e selecionar opcoes.
Ferramenta comercial para cotar frete subcontratado antes de fechar negocio.

Fluxo: RASCUNHO → ENVIADO → APROVADO / CONTRA_PROPOSTA
       CANCELADO (de qualquer estado exceto APROVADO)
"""

import logging
from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.carvia.models import CarviaSessaoCotacao, CarviaSessaoDemanda
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

# UFs brasileiras para selects
UFS_BRASIL = [
    'AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
    'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN',
    'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO',
]


def register_sessao_cotacao_routes(bp):

    # =====================================================================
    # LISTAR SESSOES
    # =====================================================================
    @bp.route('/sessoes-cotacao')
    @login_required
    def listar_sessoes_cotacao():
        """Lista paginada de sessoes de cotacao com filtros"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        sort = request.args.get('sort', 'criado_em')
        direction = request.args.get('direction', 'desc')

        # Subquery: contar demandas por sessao
        subq_demandas = db.session.query(
            CarviaSessaoDemanda.sessao_id,
            func.count(CarviaSessaoDemanda.id).label('qtd_demandas'),
            func.coalesce(
                func.sum(CarviaSessaoDemanda.valor_frete_calculado), 0
            ).label('total_frete')
        ).group_by(CarviaSessaoDemanda.sessao_id).subquery()

        query = db.session.query(
            CarviaSessaoCotacao,
            subq_demandas.c.qtd_demandas,
            subq_demandas.c.total_frete,
        ).outerjoin(
            subq_demandas,
            CarviaSessaoCotacao.id == subq_demandas.c.sessao_id
        )

        if status_filtro:
            query = query.filter(CarviaSessaoCotacao.status == status_filtro)

        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaSessaoCotacao.nome_sessao.ilike(busca_like),
                    CarviaSessaoCotacao.numero_sessao.ilike(busca_like),
                )
            )

        # Ordenacao
        sort_map = {
            'numero_sessao': CarviaSessaoCotacao.numero_sessao,
            'nome_sessao': CarviaSessaoCotacao.nome_sessao,
            'status': CarviaSessaoCotacao.status,
            'criado_em': CarviaSessaoCotacao.criado_em,
        }
        sort_col = sort_map.get(sort, CarviaSessaoCotacao.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return render_template(
            'carvia/sessoes_cotacao/listar.html',
            sessoes=pagination.items,
            pagination=pagination,
            status_filtro=status_filtro,
            busca=busca,
            sort=sort,
            direction=direction,
        )

    # =====================================================================
    # NOVA SESSAO
    # =====================================================================
    @bp.route('/sessoes-cotacao/nova', methods=['GET', 'POST'])
    @login_required
    def nova_sessao_cotacao():
        """Criar sessao + primeira demanda"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        if request.method == 'POST':
            nome_sessao = request.form.get('nome_sessao', '').strip()
            observacoes = request.form.get('observacoes', '').strip() or None

            if not nome_sessao:
                flash('Nome da sessao e obrigatorio.', 'danger')
                return redirect(url_for('carvia.nova_sessao_cotacao'))

            # Validar primeira demanda
            origem_empresa = request.form.get('origem_empresa', '').strip()
            origem_uf = request.form.get('origem_uf', '').strip().upper()
            origem_cidade = request.form.get('origem_cidade', '').strip()
            destino_empresa = request.form.get('destino_empresa', '').strip()
            destino_uf = request.form.get('destino_uf', '').strip().upper()
            destino_cidade = request.form.get('destino_cidade', '').strip()
            peso_str = request.form.get('peso', '').strip()
            valor_str = request.form.get('valor_mercadoria', '').strip()

            erros = []
            if not origem_empresa:
                erros.append('Empresa origem e obrigatoria')
            if not origem_uf or len(origem_uf) != 2:
                erros.append('UF origem invalida')
            if not origem_cidade:
                erros.append('Cidade origem e obrigatoria')
            if not destino_empresa:
                erros.append('Empresa destino e obrigatoria')
            if not destino_uf or len(destino_uf) != 2:
                erros.append('UF destino invalida')
            if not destino_cidade:
                erros.append('Cidade destino e obrigatoria')

            peso = 0
            try:
                peso = float(peso_str.replace(',', '.'))
                if peso <= 0:
                    erros.append('Peso deve ser maior que zero')
            except (ValueError, TypeError):
                erros.append('Peso invalido')

            valor_mercadoria = 0
            try:
                valor_mercadoria = float(valor_str.replace(',', '.'))
                if valor_mercadoria <= 0:
                    erros.append('Valor da mercadoria deve ser maior que zero')
            except (ValueError, TypeError):
                erros.append('Valor da mercadoria invalido')

            if erros:
                for e in erros:
                    flash(e, 'danger')
                return redirect(url_for('carvia.nova_sessao_cotacao'))

            # Campos opcionais de contato do cliente
            cliente_nome = request.form.get('cliente_nome', '').strip() or None
            cliente_email = request.form.get('cliente_email', '').strip() or None
            cliente_telefone = request.form.get('cliente_telefone', '').strip() or None
            cliente_responsavel = request.form.get('cliente_responsavel', '').strip() or None

            try:
                numero = CarviaSessaoCotacao.gerar_numero_sessao()

                sessao = CarviaSessaoCotacao(
                    numero_sessao=numero,
                    nome_sessao=nome_sessao,
                    observacoes=observacoes,
                    criado_por=current_user.email,
                    cliente_nome=cliente_nome,
                    cliente_email=cliente_email,
                    cliente_telefone=cliente_telefone,
                    cliente_responsavel=cliente_responsavel,
                )
                db.session.add(sessao)
                db.session.flush()  # pegar sessao.id

                # Campos opcionais
                tipo_carga = request.form.get('tipo_carga', '').strip() or None
                volume_str = request.form.get('volume', '').strip()
                volume = int(volume_str) if volume_str else None
                data_coleta = request.form.get('data_coleta') or None
                data_entrega = request.form.get('data_entrega_prevista') or None
                data_agendamento = request.form.get('data_agendamento') or None

                demanda = CarviaSessaoDemanda(
                    sessao_id=sessao.id,
                    ordem=1,
                    origem_empresa=origem_empresa,
                    origem_uf=origem_uf,
                    origem_cidade=origem_cidade,
                    destino_empresa=destino_empresa,
                    destino_uf=destino_uf,
                    destino_cidade=destino_cidade,
                    tipo_carga=tipo_carga,
                    peso=peso,
                    valor_mercadoria=valor_mercadoria,
                    volume=volume,
                    data_coleta=data_coleta,
                    data_entrega_prevista=data_entrega,
                    data_agendamento=data_agendamento,
                )
                db.session.add(demanda)
                db.session.commit()

                flash(f'Sessao {numero} criada com sucesso!', 'success')
                return redirect(url_for(
                    'carvia.detalhe_sessao_cotacao', id=sessao.id
                ))

            except Exception as e:
                db.session.rollback()
                logger.error("Erro ao criar sessao cotacao: %s", e)
                flash(f'Erro ao criar sessao: {e}', 'danger')
                return redirect(url_for('carvia.nova_sessao_cotacao'))

        # Prefill via query params (vindo do botao Cotar em NF/CTe)
        prefill = {}
        if request.args.get('prefill'):
            prefill = {
                'peso': request.args.get('peso', ''),
                'valor_mercadoria': request.args.get('valor_mercadoria', ''),
                'uf_destino': request.args.get('uf_destino', ''),
                'cidade_destino': request.args.get('cidade_destino', ''),
                'uf_origem': request.args.get('uf_origem', ''),
                'cliente_nome': request.args.get('cliente_nome', ''),
                'transportadora_id': request.args.get('transportadora_id', ''),
                'transportadora_nome': request.args.get('transportadora_nome', ''),
                'valor_frete': request.args.get('valor_frete', ''),
            }

        return render_template(
            'carvia/sessoes_cotacao/nova.html',
            ufs=UFS_BRASIL,
            prefill=prefill,
        )

    # =====================================================================
    # DETALHE SESSAO
    # =====================================================================
    @bp.route('/sessoes-cotacao/<int:id>')
    @login_required
    def detalhe_sessao_cotacao(id):
        """Detalhe com demandas, opcoes de frete e acoes"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        sessao = db.session.get(CarviaSessaoCotacao, id)
        if not sessao:
            flash('Sessao nao encontrada.', 'danger')
            return redirect(url_for('carvia.listar_sessoes_cotacao'))

        demandas = CarviaSessaoDemanda.query.filter_by(
            sessao_id=sessao.id
        ).order_by(CarviaSessaoDemanda.ordem).all()

        return render_template(
            'carvia/sessoes_cotacao/detalhe.html',
            sessao=sessao,
            demandas=demandas,
            ufs=UFS_BRASIL,
        )

    # =====================================================================
    # ADICIONAR DEMANDA
    # =====================================================================
    @bp.route('/sessoes-cotacao/<int:id>/adicionar-demanda', methods=['POST'])
    @login_required
    def adicionar_demanda(id):
        """Adicionar nova demanda a sessao RASCUNHO"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        sessao = db.session.get(CarviaSessaoCotacao, id)
        if not sessao:
            flash('Sessao nao encontrada.', 'danger')
            return redirect(url_for('carvia.listar_sessoes_cotacao'))

        if sessao.status != 'RASCUNHO':
            flash('Sessao nao esta em rascunho.', 'warning')
            return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))

        # Validar campos
        origem_empresa = request.form.get('origem_empresa', '').strip()
        origem_uf = request.form.get('origem_uf', '').strip().upper()
        origem_cidade = request.form.get('origem_cidade', '').strip()
        destino_empresa = request.form.get('destino_empresa', '').strip()
        destino_uf = request.form.get('destino_uf', '').strip().upper()
        destino_cidade = request.form.get('destino_cidade', '').strip()
        peso_str = request.form.get('peso', '').strip()
        valor_str = request.form.get('valor_mercadoria', '').strip()

        erros = []
        if not all([origem_empresa, origem_uf, origem_cidade,
                    destino_empresa, destino_uf, destino_cidade]):
            erros.append('Todos os campos de origem e destino sao obrigatorios')

        peso = 0
        try:
            peso = float(peso_str.replace(',', '.'))
            if peso <= 0:
                erros.append('Peso deve ser maior que zero')
        except (ValueError, TypeError):
            erros.append('Peso invalido')

        valor_mercadoria = 0
        try:
            valor_mercadoria = float(valor_str.replace(',', '.'))
            if valor_mercadoria <= 0:
                erros.append('Valor da mercadoria deve ser maior que zero')
        except (ValueError, TypeError):
            erros.append('Valor da mercadoria invalido')

        if erros:
            for e in erros:
                flash(e, 'danger')
            return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))

        try:
            # Calcular proxima ordem
            max_ordem = db.session.query(
                func.coalesce(func.max(CarviaSessaoDemanda.ordem), 0)
            ).filter(
                CarviaSessaoDemanda.sessao_id == sessao.id
            ).scalar()

            tipo_carga = request.form.get('tipo_carga', '').strip() or None
            volume_str = request.form.get('volume', '').strip()
            volume = int(volume_str) if volume_str else None
            data_coleta = request.form.get('data_coleta') or None
            data_entrega = request.form.get('data_entrega_prevista') or None
            data_agendamento = request.form.get('data_agendamento') or None

            demanda = CarviaSessaoDemanda(
                sessao_id=sessao.id,
                ordem=max_ordem + 1,
                origem_empresa=origem_empresa,
                origem_uf=origem_uf,
                origem_cidade=origem_cidade,
                destino_empresa=destino_empresa,
                destino_uf=destino_uf,
                destino_cidade=destino_cidade,
                tipo_carga=tipo_carga,
                peso=peso,
                valor_mercadoria=valor_mercadoria,
                volume=volume,
                data_coleta=data_coleta,
                data_entrega_prevista=data_entrega,
                data_agendamento=data_agendamento,
            )
            db.session.add(demanda)
            sessao.atualizado_em = agora_utc_naive()
            db.session.commit()

            flash('Demanda adicionada com sucesso!', 'success')

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao adicionar demanda: %s", e)
            flash(f'Erro ao adicionar demanda: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))

    # =====================================================================
    # REMOVER DEMANDA
    # =====================================================================
    @bp.route('/sessoes-cotacao/<int:id>/remover-demanda/<int:did>', methods=['POST'])
    @login_required
    def remover_demanda(id, did):
        """Remover demanda de sessao RASCUNHO"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        sessao = db.session.get(CarviaSessaoCotacao, id)
        if not sessao:
            flash('Sessao nao encontrada.', 'danger')
            return redirect(url_for('carvia.listar_sessoes_cotacao'))

        if sessao.status != 'RASCUNHO':
            flash('Sessao nao esta em rascunho.', 'warning')
            return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))

        demanda = db.session.get(CarviaSessaoDemanda, did)
        if not demanda or demanda.sessao_id != sessao.id:
            flash('Demanda nao encontrada.', 'danger')
            return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))

        # Verificar se nao e a ultima demanda
        count = CarviaSessaoDemanda.query.filter_by(sessao_id=sessao.id).count()
        if count <= 1:
            flash('Nao e possivel remover a unica demanda da sessao.', 'warning')
            return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))

        try:
            db.session.delete(demanda)
            sessao.atualizado_em = agora_utc_naive()
            db.session.commit()
            flash('Demanda removida.', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao remover demanda: %s", e)
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))

    # =====================================================================
    # ENVIAR SESSAO (RASCUNHO → ENVIADO)
    # =====================================================================
    @bp.route('/sessoes-cotacao/<int:id>/enviar', methods=['POST'])
    @login_required
    def enviar_sessao_cotacao(id):
        """Enviar sessao — todas demandas devem ter frete selecionado"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        sessao = db.session.get(CarviaSessaoCotacao, id)
        if not sessao:
            flash('Sessao nao encontrada.', 'danger')
            return redirect(url_for('carvia.listar_sessoes_cotacao'))

        if sessao.status != 'RASCUNHO':
            flash('Sessao nao esta em rascunho.', 'warning')
            return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))

        # Validar: todas demandas com frete
        demandas = CarviaSessaoDemanda.query.filter_by(sessao_id=sessao.id).all()
        if not demandas:
            flash('Sessao sem demandas.', 'danger')
            return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))

        sem_frete = [d for d in demandas if d.valor_frete_calculado is None]
        if sem_frete:
            flash(
                f'{len(sem_frete)} demanda(s) sem frete selecionado. '
                f'Cote e selecione antes de enviar.',
                'warning'
            )
            return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))

        try:
            sessao.status = 'ENVIADO'
            sessao.enviado_em = agora_utc_naive()
            sessao.enviado_por = current_user.email
            sessao.atualizado_em = agora_utc_naive()
            db.session.commit()
            flash('Sessao enviada com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao enviar sessao: %s", e)
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))

    # =====================================================================
    # REGISTRAR RESPOSTA (ENVIADO → APROVADO ou CONTRA_PROPOSTA)
    # =====================================================================
    @bp.route('/sessoes-cotacao/<int:id>/resposta', methods=['POST'])
    @login_required
    def registrar_resposta_sessao(id):
        """Registrar resposta do cliente"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        sessao = db.session.get(CarviaSessaoCotacao, id)
        if not sessao:
            flash('Sessao nao encontrada.', 'danger')
            return redirect(url_for('carvia.listar_sessoes_cotacao'))

        if sessao.status != 'ENVIADO':
            flash('Sessao nao esta no status ENVIADO.', 'warning')
            return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))

        tipo_resposta = request.form.get('tipo_resposta', '')
        obs = request.form.get('resposta_cliente_obs', '').strip() or None

        if tipo_resposta == 'APROVADO':
            sessao.status = 'APROVADO'
        elif tipo_resposta == 'CONTRA_PROPOSTA':
            valor_str = request.form.get('valor_contra_proposta', '').strip()
            if not valor_str:
                flash('Valor da contra proposta e obrigatorio.', 'danger')
                return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))
            try:
                valor = float(valor_str.replace(',', '.'))
                if valor <= 0:
                    raise ValueError("Valor deve ser positivo")
                sessao.valor_contra_proposta = valor
            except (ValueError, TypeError):
                flash('Valor da contra proposta invalido.', 'danger')
                return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))
            sessao.status = 'CONTRA_PROPOSTA'
        else:
            flash('Tipo de resposta invalido.', 'danger')
            return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))

        try:
            sessao.resposta_cliente_obs = obs
            sessao.respondido_em = agora_utc_naive()
            sessao.respondido_por = current_user.email
            sessao.atualizado_em = agora_utc_naive()
            db.session.commit()
            flash(f'Resposta registrada: {sessao.status}', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao registrar resposta: %s", e)
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))

    # =====================================================================
    # CANCELAR SESSAO
    # =====================================================================
    @bp.route('/sessoes-cotacao/<int:id>/cancelar', methods=['POST'])
    @login_required
    def cancelar_sessao_cotacao(id):
        """Cancelar sessao (de qualquer estado exceto APROVADO)"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        sessao = db.session.get(CarviaSessaoCotacao, id)
        if not sessao:
            flash('Sessao nao encontrada.', 'danger')
            return redirect(url_for('carvia.listar_sessoes_cotacao'))

        if sessao.status == 'APROVADO':
            flash('Nao e possivel cancelar sessao aprovada.', 'warning')
            return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))

        if sessao.status == 'CANCELADO':
            flash('Sessao ja esta cancelada.', 'info')
            return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))

        try:
            sessao.status = 'CANCELADO'
            sessao.atualizado_em = agora_utc_naive()
            db.session.commit()
            flash('Sessao cancelada.', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao cancelar sessao: %s", e)
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_sessao_cotacao', id=id))

    # =====================================================================
    # API: COTAR DEMANDA (AJAX)
    # =====================================================================
    @bp.route('/api/sessao-cotacao/<int:id>/cotar-demanda/<int:did>', methods=['POST'])
    @login_required
    def api_cotar_demanda(id, did):
        """Retorna todas as opcoes de frete para uma demanda"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        sessao = db.session.get(CarviaSessaoCotacao, id)
        if not sessao:
            return jsonify({'erro': 'Sessao nao encontrada'}), 404

        if sessao.status != 'RASCUNHO':
            return jsonify({'erro': 'Sessao nao esta em rascunho'}), 400

        demanda = db.session.get(CarviaSessaoDemanda, did)
        if not demanda or demanda.sessao_id != sessao.id:
            return jsonify({'erro': 'Demanda nao encontrada'}), 404

        try:
            from app.carvia.services.cotacao_service import CotacaoService
            service = CotacaoService()

            opcoes = service.cotar_todas_opcoes(
                peso=float(demanda.peso),
                valor_mercadoria=float(demanda.valor_mercadoria),
                uf_destino=demanda.destino_uf,
                cidade_destino=demanda.destino_cidade,
                uf_origem=demanda.origem_uf,
            )

            return jsonify({
                'sucesso': True,
                'demanda_id': demanda.id,
                'opcoes': opcoes,
                'total_opcoes': len(opcoes),
            })

        except Exception as e:
            logger.error("Erro ao cotar demanda %s: %s", did, e)
            return jsonify({'erro': str(e)}), 500

    # =====================================================================
    # API: SELECIONAR OPCAO (AJAX)
    # =====================================================================
    @bp.route('/api/sessao-cotacao/<int:id>/selecionar-opcao/<int:did>', methods=['POST'])
    @login_required
    def api_selecionar_opcao(id, did):
        """Grava opcao de frete selecionada na demanda"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        sessao = db.session.get(CarviaSessaoCotacao, id)
        if not sessao:
            return jsonify({'erro': 'Sessao nao encontrada'}), 404

        if sessao.status != 'RASCUNHO':
            return jsonify({'erro': 'Sessao nao esta em rascunho'}), 400

        demanda = db.session.get(CarviaSessaoDemanda, did)
        if not demanda or demanda.sessao_id != sessao.id:
            return jsonify({'erro': 'Demanda nao encontrada'}), 404

        data = request.get_json(silent=True) or {}
        transportadora_id = data.get('transportadora_id')
        tabela_frete_id = data.get('tabela_frete_id')
        valor_frete = data.get('valor_frete')
        detalhes = data.get('detalhes', {})
        manual = data.get('manual', False)
        valor_proposto = data.get('valor_proposto')

        # Cotacao manual: tabela_frete_id pode ser None
        if not transportadora_id or not valor_frete:
            return jsonify({'erro': 'Dados incompletos'}), 400

        if not manual and not tabela_frete_id:
            return jsonify({'erro': 'Dados incompletos'}), 400

        try:
            demanda.transportadora_id = int(transportadora_id)
            demanda.tabela_frete_id = int(tabela_frete_id) if tabela_frete_id else None
            demanda.valor_frete_calculado = float(valor_frete)
            demanda.detalhes_calculo = (
                {'tipo': 'MANUAL', 'observacao': data.get('observacao', '')}
                if manual else detalhes
            )

            # Gravar valor proposto se informado
            if valor_proposto is not None:
                demanda.valor_proposto = float(valor_proposto)

            sessao.atualizado_em = agora_utc_naive()
            db.session.commit()

            # Buscar nome da transportadora para resposta
            from app.transportadoras.models import Transportadora
            transp = db.session.get(Transportadora, demanda.transportadora_id)

            return jsonify({
                'sucesso': True,
                'demanda_id': demanda.id,
                'transportadora_nome': transp.razao_social if transp else '?',
                'valor_frete': float(demanda.valor_frete_calculado),
            })

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao selecionar opcao: %s", e)
            return jsonify({'erro': str(e)}), 500

    # =====================================================================
    # API: ATUALIZAR VALOR PROPOSTO / CONTRA PROPOSTA POR DEMANDA (AJAX)
    # =====================================================================
    @bp.route('/api/sessao-cotacao/<int:id>/demanda/<int:did>/valores', methods=['POST'])
    @login_required
    def api_atualizar_valores_demanda(id, did):
        """Grava valor_proposto e/ou valor_contra_proposta por demanda"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        sessao = db.session.get(CarviaSessaoCotacao, id)
        if not sessao:
            return jsonify({'erro': 'Sessao nao encontrada'}), 404

        demanda = db.session.get(CarviaSessaoDemanda, did)
        if not demanda or demanda.sessao_id != sessao.id:
            return jsonify({'erro': 'Demanda nao encontrada'}), 404

        data = request.get_json(silent=True) or {}

        try:
            if 'valor_proposto' in data:
                val = data['valor_proposto']
                demanda.valor_proposto = float(val) if val else None

            if 'valor_contra_proposta' in data:
                val = data['valor_contra_proposta']
                demanda.valor_contra_proposta = float(val) if val else None

            sessao.atualizado_em = agora_utc_naive()
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'demanda_id': demanda.id,
                'valor_proposto': float(demanda.valor_proposto) if demanda.valor_proposto else None,
                'valor_contra_proposta': float(demanda.valor_contra_proposta) if demanda.valor_contra_proposta else None,
            })

        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao atualizar valores demanda: %s", e)
            return jsonify({'erro': str(e)}), 500
