"""
Rotas de Custo de Entrega CarVia — CRUD completo + AJAX anexos
"""

import logging
import os
from datetime import date, datetime

from flask import (
    render_template, request, flash, redirect, url_for, jsonify,
)
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app import db
from app.carvia.models import (
    CarviaCustoEntrega, CarviaCustoEntregaAnexo, CarviaOperacao,
    CarviaCteComplementar, CarviaEmissaoCteComplementar,
)

logger = logging.getLogger(__name__)

TIPOS_CUSTO = [
    'DIARIA', 'REENTREGA', 'ARMAZENAGEM', 'DEVOLUCAO', 'AVARIA',
    'PEDAGIO_EXTRA', 'TAXA_DESCARGA', 'OUTROS',
]
STATUS_CUSTO = ['PENDENTE', 'PAGO', 'CANCELADO']
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx', 'msg', 'eml'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Mapeamento tipo_custo → motivo SSW opcao 222
# D=descarga, E=estadia, R=reembolso, C=complementar geral
TIPO_CUSTO_MOTIVO_SSW = {
    'TAXA_DESCARGA': 'D',
    'DIARIA': 'E',
    'REENTREGA': 'R',
    'DEVOLUCAO': 'R',
    'ARMAZENAGEM': 'R',
    'AVARIA': 'C',
    'PEDAGIO_EXTRA': 'C',
    'OUTROS': 'C',
}

# PIS/COFINS fixo 9.25% — divisor para grossing up
PISCOFINS_DIVISOR = 0.9075


def _allowed_file(filename):
    """Verifica se extensao do arquivo e permitida."""
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def register_custo_entrega_routes(bp):

    @bp.route('/custos-entrega') # type: ignore
    @login_required
    def listar_custos_entrega(): # type: ignore
        """Lista custos de entrega com filtros"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        page = request.args.get('page', 1, type=int)
        operacao_filtro = request.args.get('operacao', '', type=str)
        tipo_filtro = request.args.get('tipo', '')
        status_filtro = request.args.get('status', '')
        busca = request.args.get('busca', '')
        sort = request.args.get('sort', 'criado_em')
        direction = request.args.get('direction', 'desc')

        query = db.session.query(CarviaCustoEntrega).outerjoin(
            CarviaOperacao,
            CarviaCustoEntrega.operacao_id == CarviaOperacao.id,
        )

        if operacao_filtro:
            query = query.filter(CarviaCustoEntrega.operacao_id == int(operacao_filtro))
        if tipo_filtro:
            query = query.filter(CarviaCustoEntrega.tipo_custo == tipo_filtro)
        if status_filtro:
            query = query.filter(CarviaCustoEntrega.status == status_filtro)
        if busca:
            busca_like = f'%{busca}%'
            query = query.filter(
                db.or_(
                    CarviaCustoEntrega.numero_custo.ilike(busca_like),
                    CarviaCustoEntrega.descricao.ilike(busca_like),
                    CarviaCustoEntrega.fornecedor_nome.ilike(busca_like),
                    CarviaCustoEntrega.observacoes.ilike(busca_like),
                    CarviaOperacao.nome_cliente.ilike(busca_like),
                    CarviaOperacao.cnpj_cliente.ilike(busca_like),
                    CarviaOperacao.cte_numero.ilike(busca_like),
                    CarviaOperacao.ctrc_numero.ilike(busca_like),
                    CarviaOperacao.cidade_destino.ilike(busca_like),
                )
            )

        # Ordenacao dinamica
        sortable_columns = {
            'numero_custo': CarviaCustoEntrega.numero_custo,
            'tipo_custo': CarviaCustoEntrega.tipo_custo,
            'valor': CarviaCustoEntrega.valor,
            'data_custo': CarviaCustoEntrega.data_custo,
            'data_vencimento': CarviaCustoEntrega.data_vencimento,
            'status': CarviaCustoEntrega.status,
            'criado_em': CarviaCustoEntrega.criado_em,
        }
        sort_col = sortable_columns.get(sort, CarviaCustoEntrega.criado_em)
        if direction == 'asc':
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        paginacao = query.paginate(page=page, per_page=25, error_out=False)

        today = date.today()

        return render_template(
            'carvia/custos_entrega/listar.html',
            custos_entrega=paginacao.items,
            paginacao=paginacao,
            operacao_filtro=operacao_filtro,
            tipo_filtro=tipo_filtro,
            status_filtro=status_filtro,
            busca=busca,
            sort=sort,
            direction=direction,
            tipos_custo=TIPOS_CUSTO,
            today=today,
        )

    @bp.route('/custos-entrega/criar', methods=['GET', 'POST']) # type: ignore
    @login_required
    def criar_custo_entrega(): # type: ignore
        """Cria novo custo de entrega"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        if request.method == 'POST':
            operacao_id_str = request.form.get('operacao_id', '').strip()
            cte_complementar_id_str = request.form.get('cte_complementar_id', '').strip()
            tipo_custo = request.form.get('tipo_custo', '').strip()
            descricao = request.form.get('descricao', '').strip()
            valor_str = request.form.get('valor', '').strip()
            data_custo_str = request.form.get('data_custo', '').strip()
            data_vencimento_str = request.form.get('data_vencimento', '').strip()
            fornecedor_nome = request.form.get('fornecedor_nome', '').strip()
            fornecedor_cnpj = request.form.get('fornecedor_cnpj', '').strip()
            observacoes = request.form.get('observacoes', '').strip()

            # Validacoes
            if not operacao_id_str or not tipo_custo or not valor_str or not data_custo_str:
                flash(
                    'Operacao, tipo, valor e data do custo sao obrigatorios.',
                    'warning',
                )
                return redirect(url_for('carvia.criar_custo_entrega'))

            if tipo_custo not in TIPOS_CUSTO:
                flash('Tipo de custo invalido.', 'warning')
                return redirect(url_for('carvia.criar_custo_entrega'))

            try:
                operacao_id = int(operacao_id_str)
                operacao = db.session.get(CarviaOperacao, operacao_id)
                if not operacao:
                    flash('Operacao nao encontrada.', 'warning')
                    return redirect(url_for('carvia.criar_custo_entrega'))

                valor = float(valor_str.replace(',', '.'))
                if valor <= 0:
                    flash('Valor deve ser maior que zero.', 'warning')
                    return redirect(url_for('carvia.criar_custo_entrega'))

                data_custo = date.fromisoformat(data_custo_str)
                data_vencimento = (
                    date.fromisoformat(data_vencimento_str)
                    if data_vencimento_str else None
                )

                cte_complementar_id = (
                    int(cte_complementar_id_str) if cte_complementar_id_str else None
                )

                numero_custo = CarviaCustoEntrega.gerar_numero_custo()

                custo = CarviaCustoEntrega(
                    numero_custo=numero_custo,
                    operacao_id=operacao_id,
                    cte_complementar_id=cte_complementar_id,
                    tipo_custo=tipo_custo,
                    descricao=descricao or None,
                    valor=valor,
                    data_custo=data_custo,
                    data_vencimento=data_vencimento,
                    fornecedor_nome=fornecedor_nome or None,
                    fornecedor_cnpj=fornecedor_cnpj or None,
                    status='PENDENTE',
                    observacoes=observacoes or None,
                    criado_por=current_user.email,
                )
                db.session.add(custo)
                db.session.flush()

                # Vincular ao CarviaFrete pela operacao_id
                if custo.operacao_id:
                    from app.carvia.models import CarviaFrete
                    frete = CarviaFrete.query.filter_by(
                        operacao_id=custo.operacao_id
                    ).first()
                    if frete:
                        custo.frete_id = frete.id

                db.session.commit()

                flash(
                    f'Custo de entrega {custo.numero_custo} criado com sucesso.',
                    'success',
                )
                return redirect(url_for(
                    'carvia.detalhe_custo_entrega', custo_id=custo.id
                ))

            except ValueError as ve:
                flash(f'Dados invalidos: {ve}', 'warning')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao criar custo de entrega: {e}")
                flash(f'Erro: {e}', 'danger')

        # GET: buscar operacoes e CTes complementares para o form
        operacoes = db.session.query(CarviaOperacao).filter(
            CarviaOperacao.status != 'CANCELADO'
        ).order_by(CarviaOperacao.criado_em.desc()).all()

        ctes_complementares = db.session.query(CarviaCteComplementar).filter(
            CarviaCteComplementar.status != 'CANCELADO'
        ).order_by(CarviaCteComplementar.criado_em.desc()).all()

        return render_template(
            'carvia/custos_entrega/criar.html',
            tipos_custo=TIPOS_CUSTO,
            operacoes=operacoes,
            ctes_complementares=ctes_complementares,
        )

    @bp.route('/custos-entrega/<int:custo_id>') # type: ignore
    @login_required
    def detalhe_custo_entrega(custo_id): # type: ignore
        """Detalhe de um custo de entrega com anexos"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        custo = db.session.get(CarviaCustoEntrega, custo_id)
        if not custo:
            flash('Custo de entrega nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_custos_entrega'))

        # Anexos ativos
        anexos = db.session.query(CarviaCustoEntregaAnexo).filter(
            CarviaCustoEntregaAnexo.custo_entrega_id == custo_id,
            CarviaCustoEntregaAnexo.ativo.is_(True),
        ).order_by(CarviaCustoEntregaAnexo.criado_em.desc()).all()

        # Cross-links: operacao, subcontratos, faturas, ctes complementares
        operacao = db.session.get(CarviaOperacao, custo.operacao_id)

        from app.carvia.models import (
            CarviaSubcontrato, CarviaFaturaCliente,
            CarviaFaturaTransportadora, CarviaOperacaoNf, CarviaNf,
        )

        subcontratos = []
        fatura_cliente = None
        faturas_transportadora = []
        nfs = []
        ctes_complementares = []

        if operacao:
            subcontratos = CarviaSubcontrato.query.filter(
                CarviaSubcontrato.operacao_id == operacao.id
            ).order_by(CarviaSubcontrato.criado_em.desc()).all()

            if operacao.fatura_cliente_id:
                fatura_cliente = db.session.get(
                    CarviaFaturaCliente, operacao.fatura_cliente_id
                )

            # Faturas transportadora via subcontratos
            fat_transp_ids = {
                s.fatura_transportadora_id for s in subcontratos
                if s.fatura_transportadora_id
            }
            if fat_transp_ids:
                faturas_transportadora = CarviaFaturaTransportadora.query.filter(
                    CarviaFaturaTransportadora.id.in_(fat_transp_ids)
                ).all()

            # NFs via junction
            nf_ids = db.session.query(CarviaOperacaoNf.nf_id).filter(
                CarviaOperacaoNf.operacao_id == operacao.id
            ).all()
            nf_id_list = [r[0] for r in nf_ids]
            if nf_id_list:
                nfs = CarviaNf.query.filter(CarviaNf.id.in_(nf_id_list)).all()

            # Outros CTes complementares da mesma operacao
            ctes_complementares = CarviaCteComplementar.query.filter(
                CarviaCteComplementar.operacao_id == operacao.id,
                CarviaCteComplementar.id != (custo.cte_complementar_id or 0),
            ).order_by(CarviaCteComplementar.criado_em.desc()).all()

        # Emissao CTe Comp em andamento (para mostrar progresso)
        emissao_comp = CarviaEmissaoCteComplementar.query.filter(
            CarviaEmissaoCteComplementar.custo_entrega_id == custo_id,
        ).order_by(CarviaEmissaoCteComplementar.criado_em.desc()).first()

        return render_template(
            'carvia/custos_entrega/detalhe.html',
            custo=custo,
            anexos=anexos,
            operacao=operacao,
            subcontratos=subcontratos,
            fatura_cliente=fatura_cliente,
            faturas_transportadora=faturas_transportadora,
            nfs=nfs,
            ctes_complementares=ctes_complementares,
            emissao_comp=emissao_comp,
        )

    @bp.route('/custos-entrega/<int:custo_id>/editar', methods=['GET', 'POST']) # type: ignore
    @login_required
    def editar_custo_entrega(custo_id): # type: ignore
        """Edita um custo de entrega existente"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        custo = db.session.get(CarviaCustoEntrega, custo_id)
        if not custo:
            flash('Custo de entrega nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_custos_entrega'))

        if custo.status == 'CANCELADO':
            flash('Nao e possivel editar custo cancelado.', 'warning')
            return redirect(url_for(
                'carvia.detalhe_custo_entrega', custo_id=custo_id
            ))

        if custo.status == 'PAGO':
            flash(
                'Custo de entrega pago nao pode ser editado. '
                'Cancele e crie um novo se necessario.',
                'warning',
            )
            return redirect(url_for(
                'carvia.detalhe_custo_entrega', custo_id=custo_id
            ))

        if request.method == 'POST':
            cte_complementar_id_str = request.form.get('cte_complementar_id', '').strip()
            tipo_custo = request.form.get('tipo_custo', '').strip()
            descricao = request.form.get('descricao', '').strip()
            valor_str = request.form.get('valor', '').strip()
            data_custo_str = request.form.get('data_custo', '').strip()
            data_vencimento_str = request.form.get('data_vencimento', '').strip()
            fornecedor_nome = request.form.get('fornecedor_nome', '').strip()
            fornecedor_cnpj = request.form.get('fornecedor_cnpj', '').strip()
            observacoes = request.form.get('observacoes', '').strip()

            if not tipo_custo or not valor_str or not data_custo_str:
                flash('Tipo, valor e data do custo sao obrigatorios.', 'warning')
                return redirect(url_for(
                    'carvia.editar_custo_entrega', custo_id=custo_id
                ))

            if tipo_custo not in TIPOS_CUSTO:
                flash('Tipo de custo invalido.', 'warning')
                return redirect(url_for(
                    'carvia.editar_custo_entrega', custo_id=custo_id
                ))

            try:
                valor = float(valor_str.replace(',', '.'))
                if valor <= 0:
                    flash('Valor deve ser maior que zero.', 'warning')
                    return redirect(url_for(
                        'carvia.editar_custo_entrega', custo_id=custo_id
                    ))

                custo.cte_complementar_id = (
                    int(cte_complementar_id_str) if cte_complementar_id_str else None
                )
                custo.tipo_custo = tipo_custo
                custo.descricao = descricao or None
                custo.valor = valor
                custo.data_custo = date.fromisoformat(data_custo_str)
                custo.data_vencimento = (
                    date.fromisoformat(data_vencimento_str)
                    if data_vencimento_str else None
                )
                custo.fornecedor_nome = fornecedor_nome or None
                custo.fornecedor_cnpj = fornecedor_cnpj or None
                custo.observacoes = observacoes or None

                db.session.commit()
                flash('Custo de entrega atualizado com sucesso.', 'success')
                return redirect(url_for(
                    'carvia.detalhe_custo_entrega', custo_id=custo_id
                ))

            except ValueError as ve:
                flash(f'Dados invalidos: {ve}', 'warning')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao editar custo de entrega {custo_id}: {e}")
                flash(f'Erro: {e}', 'danger')

        # GET: buscar CTes complementares para o seletor
        ctes_complementares = db.session.query(CarviaCteComplementar).filter(
            CarviaCteComplementar.operacao_id == custo.operacao_id,
            CarviaCteComplementar.status != 'CANCELADO',
        ).order_by(CarviaCteComplementar.criado_em.desc()).all()

        return render_template(
            'carvia/custos_entrega/editar.html',
            custo=custo,
            tipos_custo=TIPOS_CUSTO,
            ctes_complementares=ctes_complementares,
        )

    @bp.route('/custos-entrega/<int:custo_id>/status', methods=['POST']) # type: ignore
    @login_required
    def atualizar_status_custo_entrega(custo_id): # type: ignore
        """Atualiza status de um custo de entrega"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        custo = db.session.get(CarviaCustoEntrega, custo_id)
        if not custo:
            flash('Custo de entrega nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_custos_entrega'))

        novo_status = request.form.get('status')
        if novo_status not in STATUS_CUSTO:
            flash('Status invalido.', 'warning')
            return redirect(url_for(
                'carvia.detalhe_custo_entrega', custo_id=custo_id
            ))

        try:
            # Se revertendo de PAGO para outro status, remover movimentacao financeira
            if custo.status == 'PAGO' and novo_status != 'PAGO':
                from app.carvia.routes.fluxo_caixa_routes import _remover_movimentacao
                _remover_movimentacao('custo_entrega', custo_id)
                custo.pago_por = None
                custo.pago_em = None
                logger.info(
                    f"Custo entrega #{custo_id}: movimentacao removida ao reverter "
                    f"PAGO -> {novo_status} por {current_user.email}"
                )

            custo.status = novo_status

            # Ao marcar como PAGO: registrar pago_em/pago_por e criar movimentacao
            if novo_status == 'PAGO':
                data_pagamento_str = request.form.get('data_pagamento', '').strip()
                if not data_pagamento_str:
                    flash(
                        'Data de pagamento e obrigatoria para marcar como PAGO.',
                        'warning',
                    )
                    return redirect(url_for(
                        'carvia.detalhe_custo_entrega', custo_id=custo_id
                    ))
                try:
                    data_pagamento = date.fromisoformat(data_pagamento_str)
                except ValueError:
                    flash('Data de pagamento invalida.', 'warning')
                    return redirect(url_for(
                        'carvia.detalhe_custo_entrega', custo_id=custo_id
                    ))

                custo.pago_em = datetime.combine(data_pagamento, datetime.min.time())
                custo.pago_por = current_user.email

                # Criar movimentacao financeira na conta
                from app.carvia.routes.fluxo_caixa_routes import (
                    _criar_movimentacao, _gerar_descricao,
                )
                descricao = _gerar_descricao('custo_entrega', custo)
                _criar_movimentacao(
                    'custo_entrega', custo_id,
                    float(custo.valor or 0), descricao, current_user.email,
                )

            db.session.commit()
            flash(f'Status atualizado para {novo_status}.', 'success')
        except IntegrityError:
            db.session.rollback()
            logger.warning(f"Movimentacao duplicada custo entrega #{custo_id}")
            flash('Este lancamento ja foi processado.', 'warning')
        except Exception as e:
            db.session.rollback()
            logger.error(
                f"Erro ao atualizar status custo entrega {custo_id}: {e}"
            )
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for(
            'carvia.detalhe_custo_entrega', custo_id=custo_id
        ))

    # ========================================================================
    # AJAX — Anexos
    # ========================================================================

    @bp.route('/api/custo-entrega/<int:custo_id>/upload-anexo', methods=['POST']) # type: ignore
    @login_required
    def upload_anexo_custo_entrega(custo_id): # type: ignore
        """Upload de anexo comprovatorio (multipart) via AJAX"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        custo = db.session.get(CarviaCustoEntrega, custo_id)
        if not custo:
            return jsonify({'erro': 'Custo de entrega nao encontrado.'}), 404

        if 'arquivo' not in request.files:
            return jsonify({'erro': 'Nenhum arquivo enviado.'}), 400

        file = request.files['arquivo']
        if not file or not file.filename:
            return jsonify({'erro': 'Arquivo invalido.'}), 400

        if not _allowed_file(file.filename):
            return jsonify({
                'erro': f'Extensao nao permitida. Aceitas: {", ".join(sorted(ALLOWED_EXTENSIONS))}'
            }), 400

        # Verificar tamanho
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > MAX_FILE_SIZE:
            return jsonify({
                'erro': f'Arquivo excede o limite de {MAX_FILE_SIZE // (1024 * 1024)}MB.'
            }), 400

        try:
            from app.utils.file_storage import get_file_storage
            storage = get_file_storage()

            caminho = storage.save_file(
                file, folder='carvia/custos-entrega/anexos'
            )

            descricao = request.form.get('descricao', '').strip()

            # Se for email (.msg/.eml), extrair metadados
            email_metadata = {}
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            if ext in ('msg', 'eml'):
                try:
                    from app.utils.email_handler import EmailHandler
                    email_handler = EmailHandler()
                    file.seek(0)
                    if ext == 'msg':
                        email_metadata = email_handler.processar_email_msg(file) or {}
                    else:
                        email_metadata = email_handler.processar_email_eml(file) or {}
                except Exception as e_email:
                    logger.warning(
                        f"Nao foi possivel extrair metadados do email: {e_email}"
                    )

            preview = email_metadata.get('conteudo_preview', '')
            anexo = CarviaCustoEntregaAnexo(
                custo_entrega_id=custo_id,
                nome_original=file.filename,
                nome_arquivo=os.path.basename(caminho),
                caminho_s3=caminho,
                tamanho_bytes=size,
                content_type=file.content_type,
                descricao=descricao or None,
                criado_por=current_user.email,
                email_remetente=email_metadata.get('remetente') or None,
                email_assunto=email_metadata.get('assunto') or None,
                email_data_envio=email_metadata.get('data_envio'),
                email_conteudo_preview=preview[:500] if preview else None,
            )
            db.session.add(anexo)
            db.session.commit()

            return jsonify({
                'sucesso': True,
                'anexo': {
                    'id': anexo.id,
                    'nome_original': anexo.nome_original,
                    'tamanho_bytes': anexo.tamanho_bytes,
                    'criado_em': anexo.criado_em.isoformat() if anexo.criado_em else None,
                },
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao fazer upload de anexo para custo {custo_id}: {e}")
            return jsonify({'erro': f'Erro ao salvar arquivo: {e}'}), 500

    @bp.route('/api/custo-entrega/anexo/<int:anexo_id>/excluir', methods=['POST']) # type: ignore
    @login_required
    def excluir_anexo_custo_entrega(anexo_id): # type: ignore
        """Soft-delete de anexo (ativo=False) via AJAX"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403

        anexo = db.session.get(CarviaCustoEntregaAnexo, anexo_id)
        if not anexo:
            return jsonify({'erro': 'Anexo nao encontrado.'}), 404

        try:
            anexo.ativo = False
            db.session.commit()
            return jsonify({'sucesso': True})
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao excluir anexo {anexo_id}: {e}")
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/custo-entrega/anexo/<int:anexo_id>/download') # type: ignore
    @login_required
    def download_anexo_custo_entrega(anexo_id): # type: ignore
        """Redirect para URL presigned S3 do anexo"""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        anexo = db.session.get(CarviaCustoEntregaAnexo, anexo_id)
        if not anexo or not anexo.ativo:
            flash('Anexo nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_custos_entrega'))

        try:
            from app.utils.file_storage import get_file_storage
            storage = get_file_storage()

            url = storage.get_download_url(
                anexo.caminho_s3, anexo.nome_original
            ) or storage.get_file_url(anexo.caminho_s3)

            if url:
                return redirect(url)

            flash('Nao foi possivel gerar URL de download.', 'warning')
        except Exception as e:
            logger.error(f"Erro ao gerar URL download anexo {anexo_id}: {e}")
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for(
            'carvia.detalhe_custo_entrega', custo_id=anexo.custo_entrega_id
        ))

    # ── CTe Complementar: trigger de emissao via SSW opcao 222 ──

    @bp.route('/custos-entrega/<int:custo_id>/gerar-cte-complementar', methods=['POST'])  # type: ignore
    @login_required
    def gerar_cte_complementar(custo_id):  # type: ignore
        """Calcula valor com impostos, cria CTe Complementar e enfileira emissao SSW."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        custo = db.session.get(CarviaCustoEntrega, custo_id)
        if not custo:
            flash('Custo de entrega nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_custos_entrega'))

        # Guards
        if custo.cte_complementar_id:
            flash('Este custo ja possui CTe Complementar vinculado.', 'warning')
            return redirect(url_for('carvia.detalhe_custo_entrega', custo_id=custo_id))

        if custo.status == 'CANCELADO':
            flash('Custo cancelado nao pode gerar CTe Complementar.', 'warning')
            return redirect(url_for('carvia.detalhe_custo_entrega', custo_id=custo_id))

        # Verificar emissao em andamento
        emissao_ativa = CarviaEmissaoCteComplementar.query.filter(
            CarviaEmissaoCteComplementar.custo_entrega_id == custo_id,
            CarviaEmissaoCteComplementar.status.in_(['PENDENTE', 'EM_PROCESSAMENTO']),
        ).first()
        if emissao_ativa:
            flash('Ja existe emissao em andamento para este custo.', 'warning')
            return redirect(url_for('carvia.detalhe_custo_entrega', custo_id=custo_id))

        operacao = db.session.get(CarviaOperacao, custo.operacao_id)
        if not operacao or not operacao.ctrc_numero:
            flash(
                'Operacao nao possui CTRC. Importe o CTe XML primeiro.',
                'danger'
            )
            return redirect(url_for('carvia.detalhe_custo_entrega', custo_id=custo_id))

        # Resolver ICMS — do campo persistido ou re-parse do XML
        icms = float(operacao.icms_aliquota or 0)
        if icms == 0 and operacao.cte_xml_path:
            try:
                from app.utils.file_storage import get_file_storage
                from app.carvia.services.parsers.cte_xml_parser_carvia import (
                    CTeXMLParserCarvia,
                )
                storage = get_file_storage()
                xml_bytes = storage.get_file_content(operacao.cte_xml_path)
                if xml_bytes:
                    xml_str = xml_bytes.decode('utf-8', errors='replace')
                    parser = CTeXMLParserCarvia(xml_str)
                    impostos = parser.get_impostos()
                    icms = float(impostos.get('aliquota_icms') or 0)
                    if icms > 0:
                        operacao.icms_aliquota = icms  # Persistir para futuro
            except Exception as e:
                logger.warning("Falha ao resolver ICMS do XML op=%s: %s", operacao.id, e)

        if icms == 0:
            flash(
                'ICMS nao encontrado para esta operacao. '
                'Verifique se o XML do CTe foi importado.',
                'danger'
            )
            return redirect(url_for('carvia.detalhe_custo_entrega', custo_id=custo_id))

        # Calcular valor CTe Complementar: valor / 0.9075 / (1 - icms/100)
        valor_base = float(custo.valor)
        icms_divisor = 1 - (icms / 100)
        if icms_divisor <= 0:
            flash('Aliquota ICMS invalida.', 'danger')
            return redirect(url_for('carvia.detalhe_custo_entrega', custo_id=custo_id))

        valor_cte = round(valor_base / PISCOFINS_DIVISOR / icms_divisor, 2)
        motivo_ssw = TIPO_CUSTO_MOTIVO_SSW.get(custo.tipo_custo, 'C')

        try:
            # Criar CTe Complementar (RASCUNHO)
            cte_comp = CarviaCteComplementar(
                numero_comp=CarviaCteComplementar.gerar_numero_comp(),
                operacao_id=operacao.id,
                cte_valor=valor_cte,
                cnpj_cliente=operacao.cnpj_cliente,
                nome_cliente=operacao.nome_cliente,
                status='RASCUNHO',
                observacoes=(
                    f'Gerado automaticamente de {custo.numero_custo} '
                    f'({custo.tipo_custo}). '
                    f'Base={valor_base:.2f}, PIS/COFINS=9.25%, ICMS={icms}%'
                ),
                criado_por=current_user.email,
            )
            db.session.add(cte_comp)
            db.session.flush()

            # Vincular custo ao CTe Complementar
            custo.cte_complementar_id = cte_comp.id

            # Criar emissao (tracking)
            emissao = CarviaEmissaoCteComplementar(
                custo_entrega_id=custo.id,
                cte_complementar_id=cte_comp.id,
                operacao_id=operacao.id,
                ctrc_pai=operacao.ctrc_numero,
                motivo_ssw=motivo_ssw,
                filial_ssw='CAR',
                valor_calculado=valor_cte,
                icms_aliquota_usada=icms,
                status='PENDENTE',
                criado_por=current_user.email,
            )
            db.session.add(emissao)
            db.session.flush()

            # Enfileirar job RQ
            from app.portal.workers import enqueue_job
            from app.carvia.workers.ssw_cte_complementar_jobs import (
                emitir_cte_complementar_job,
            )

            job = enqueue_job(
                emitir_cte_complementar_job,
                emissao.id,
                queue_name='high',
                timeout='10m',
            )
            emissao.job_id = job.id
            db.session.commit()

            logger.info(
                "CTe Complementar %s criado para custo %s (valor=%s, icms=%s%%, motivo=%s)",
                cte_comp.numero_comp, custo.numero_custo,
                valor_cte, icms, motivo_ssw
            )
            flash(
                f'CTe Complementar {cte_comp.numero_comp} criado — '
                f'valor {valor_cte:.2f} (base {valor_base:.2f} + PIS/COFINS 9.25% + ICMS {icms}%). '
                f'Emissao SSW em andamento...',
                'success'
            )

        except IntegrityError as e:
            db.session.rollback()
            logger.error("IntegrityError ao gerar CTe Complementar: %s", e)
            flash('Erro de integridade ao criar CTe Complementar.', 'danger')
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao gerar CTe Complementar custo=%s: %s", custo_id, e)
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_custo_entrega', custo_id=custo_id))

    @bp.route('/api/custos-entrega/emissao-comp/<int:emissao_comp_id>/status')  # type: ignore
    @login_required
    def status_emissao_cte_complementar(emissao_comp_id):  # type: ignore
        """API de polling: retorna status da emissao CTe Complementar."""
        emissao = db.session.get(CarviaEmissaoCteComplementar, emissao_comp_id)
        if not emissao:
            return jsonify({'erro': 'Emissao nao encontrada'}), 404

        return jsonify({
            'status': emissao.status,
            'etapa': emissao.etapa,
            'erro': emissao.erro_ssw,
            'cte_complementar_id': emissao.cte_complementar_id,
        })
