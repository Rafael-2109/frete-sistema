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
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

TIPOS_CUSTO = [
    'DIARIA', 'REENTREGA', 'ARMAZENAGEM', 'DEVOLUCAO', 'AVARIA',
    'PEDAGIO_EXTRA', 'TAXA_DESCARGA', 'OUTROS',
]
STATUS_CUSTO = ['PENDENTE', 'VINCULADO_FT', 'PAGO', 'CANCELADO']

# C3 (2026-04-19): politicas centralizadas em upload_policies.py
from app.carvia.utils.upload_policies import (  # noqa: E402
    ALLOWED_EXT_ANEXO as ALLOWED_EXTENSIONS,
    MAX_BYTES_ANEXO as MAX_FILE_SIZE,
)

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
    """Verifica se extensao do arquivo e permitida (C3: reusa helper central)."""
    from app.carvia.utils.upload_policies import is_extensao_permitida
    return is_extensao_permitida(filename, ALLOWED_EXTENSIONS)


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

    # Rota /custos-entrega/criar REMOVIDA (2026-04-15).
    # Fluxo unificado em /carvia/despesas-extras/nova — suporta venda e compra.
    # Deriva operacao_id automaticamente via CarviaFrete.operacao_id.

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

        # Se vinculado a FT, checa pode_editar() da fatura (bloqueia se CONFERIDA/PAGA).
        # Permite edicao se FT esta em PENDENTE/EM_CONFERENCIA (fatura em construcao).
        # Padrao espelhado de DespesaExtra ↔ FaturaFrete no Nacom.
        if custo.fatura_transportadora_id:
            from app.carvia.models import CarviaFaturaTransportadora
            ft = db.session.get(CarviaFaturaTransportadora, custo.fatura_transportadora_id)
            if ft:
                pode, razao = ft.pode_editar()
                if not pode:
                    flash(
                        f'Custo vinculado a Fatura Transportadora #{ft.numero_fatura}: {razao} '
                        f'Desvincule o custo (se possivel) ou reabra a conferencia da fatura antes de editar.',
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
        # W10 Nivel 2 (Sprint 4): apenas PENDENTE e CANCELADO aqui.
        # Para PAGO, usar endpoint JSON /custos-entrega/<id>/pagar.
        if novo_status not in ('PENDENTE', 'CANCELADO'):
            flash(
                'Status invalido. Para marcar como PAGO, use o botao "Pagar".',
                'warning',
            )
            return redirect(url_for(
                'carvia.detalhe_custo_entrega', custo_id=custo_id
            ))

        # Invariante: CE em VINCULADO_FT nao pode ter status alterado por esta
        # rota. Tem que desvincular da FT primeiro (via rota dedicada) —
        # caso contrario ficaria com FK preenchida e status inconsistente.
        if custo.status == 'VINCULADO_FT':
            flash(
                f'Custo esta VINCULADO_FT (fatura #{custo.fatura_transportadora_id}). '
                f'Desvincule da fatura antes de alterar o status.',
                'warning',
            )
            return redirect(url_for(
                'carvia.detalhe_custo_entrega', custo_id=custo_id
            ))

        # A5+NC1 combinados — ORDEM CRITICA para UX correta:
        #
        # Quando usuario pede CANCELADO, verificamos PRIMEIRO o vinculo com
        # Fatura Transportadora, porque se o CE esta vinculado a FT o
        # cancelamento e impossivel mesmo apos desfazer o pagamento. A unica
        # via para cancelar e desvincular o CE da FT primeiro.
        #
        # Entao: FT-coverage (terminal blocker) ANTES de NC1 (2-step flow).
        if novo_status == 'CANCELADO' and custo.fatura_transportadora_id:
            flash(
                f'Custo esta vinculado a Fatura Transportadora '
                f'#{custo.fatura_transportadora_id}. Nao pode ser cancelado '
                f'diretamente — desvincule da fatura primeiro.',
                'danger',
            )
            return redirect(url_for(
                'carvia.detalhe_custo_entrega', custo_id=custo_id
            ))

        # NC1: bloquear transicao PAGO -> CANCELADO direta (apos FT check).
        # R4 exige que CANCELADO venha de PENDENTE — desfazer pagamento
        # primeiro, cancelar depois (2 acoes explicitas).
        if custo.status == 'PAGO' and novo_status == 'CANCELADO':
            flash(
                'Nao e possivel cancelar custo PAGO diretamente. '
                'Desfaca o pagamento primeiro (isso reverte para PENDENTE), '
                'depois cancele.',
                'warning',
            )
            return redirect(url_for(
                'carvia.detalhe_custo_entrega', custo_id=custo_id
            ))

        try:
            # Se revertendo de PAGO, usar service de desfazer
            if custo.status == 'PAGO':
                from app.carvia.services.financeiro.carvia_pagamento_service import (
                    CarviaPagamentoService, PagamentoError,
                )
                try:
                    CarviaPagamentoService.desfazer_pagamento(
                        'custo_entrega', custo_id, current_user.email
                    )
                except PagamentoError as e:
                    db.session.rollback()
                    flash(str(e), 'danger')
                    return redirect(url_for(
                        'carvia.detalhe_custo_entrega', custo_id=custo_id
                    ))
                # Compat historico (ContaMovimentacao legada) e feito
                # INTERNAMENTE por CarviaPagamentoService.desfazer_pagamento.

            custo.status = novo_status
            db.session.commit()
            flash(f'Status atualizado para {novo_status}.', 'success')

        except Exception as e:
            db.session.rollback()
            logger.exception(
                f"Erro ao atualizar status custo entrega {custo_id}: {e}"
            )
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for(
            'carvia.detalhe_custo_entrega', custo_id=custo_id
        ))

    @bp.route('/custos-entrega/<int:custo_id>/pagar', methods=['POST']) # type: ignore
    @login_required
    def pagar_custo_entrega(custo_id): # type: ignore
        """Paga custo de entrega via CarviaPagamentoService (JSON)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        custo = db.session.get(CarviaCustoEntrega, custo_id)
        if not custo:
            return jsonify({'erro': 'Custo de entrega nao encontrado'}), 404

        # Integridade CE-FT: CE vinculado a FT nao pode ser pago diretamente
        if custo.fatura_transportadora_id:
            return jsonify({
                'erro': (
                    f'Custo esta vinculado a Fatura Transportadora '
                    f'#{custo.fatura_transportadora_id}. Sera pago '
                    f'automaticamente quando a fatura for paga.'
                ),
            }), 400

        data = request.get_json() or {}
        data_pagamento_str = data.get('data_pagamento', '')
        extrato_linha_id = data.get('extrato_linha_id')
        conta_origem = data.get('conta_origem')
        descricao_pagamento = data.get('descricao_pagamento')

        if not data_pagamento_str:
            return jsonify({'erro': 'data_pagamento e obrigatoria'}), 400
        try:
            data_pagamento = date.fromisoformat(data_pagamento_str)
        except ValueError:
            return jsonify({'erro': 'Data de pagamento invalida'}), 400

        from app.carvia.services.financeiro.carvia_pagamento_service import (
            CarviaPagamentoService,
            DocumentoJaPagoError,
            DocumentoCanceladoError,
            DocumentoNaoEncontradoError,
            JaConciliadoError,
            ParametroInvalidoError,
            PagamentoError,
        )

        try:
            if extrato_linha_id:
                resultado = CarviaPagamentoService.pagar_com_conciliacao(
                    tipo_doc='custo_entrega',
                    doc_id=custo_id,
                    data_pagamento=data_pagamento,
                    extrato_linha_id=extrato_linha_id,
                    usuario=current_user.email,
                )
            else:
                resultado = CarviaPagamentoService.pagar_manual(
                    tipo_doc='custo_entrega',
                    doc_id=custo_id,
                    data_pagamento=data_pagamento,
                    conta_origem=conta_origem,
                    descricao_pagamento=descricao_pagamento,
                    usuario=current_user.email,
                )
            db.session.commit()
            return jsonify({
                'sucesso': True,
                'novo_status': resultado['novo_status'],
                'pago_em': custo.pago_em.isoformat() if custo.pago_em else None,
                'pago_por': custo.pago_por,
                'extrato_linha_id': resultado.get('extrato_linha_id'),
                'modo': resultado.get('modo'),
            })

        except DocumentoNaoEncontradoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 404
        except DocumentoJaPagoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 409
        except DocumentoCanceladoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except JaConciliadoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except ParametroInvalidoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except PagamentoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Erro ao pagar custo entrega #{custo_id}: {e}")
            return jsonify({'erro': str(e)}), 500

    @bp.route('/custos-entrega/<int:custo_id>/desfazer-pagamento', methods=['POST']) # type: ignore
    @login_required
    def desfazer_pagamento_custo_entrega(custo_id): # type: ignore
        """Desfaz pagamento de custo de entrega (JSON).

        Bloqueado se CE esta vinculado a FT: nesse caso o pagamento vem da
        propagacao automatica da FT — nao ha pagamento manual para desfazer.
        Usuario deve desvincular o CE da FT primeiro.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        custo = db.session.get(CarviaCustoEntrega, custo_id)
        if not custo:
            return jsonify({'erro': 'Custo de entrega nao encontrado'}), 404

        # Simetrico ao guard de pagar_custo_entrega: CE vinculado a FT tem
        # pagamento automatico, nao manual.
        if custo.fatura_transportadora_id:
            return jsonify({
                'erro': (
                    f'Custo esta vinculado a Fatura Transportadora '
                    f'#{custo.fatura_transportadora_id}. Pagamento e '
                    f'automatico via FT — nao ha desfazer manual. '
                    f'Desvincule da fatura primeiro.'
                ),
            }), 400

        from app.carvia.services.financeiro.carvia_pagamento_service import (
            CarviaPagamentoService,
            DocumentoNaoEncontradoError,
            PagamentoError,
        )

        try:
            resultado = CarviaPagamentoService.desfazer_pagamento(
                'custo_entrega', custo_id, current_user.email
            )
            # Compat historico (ContaMovimentacao legada) e feito
            # INTERNAMENTE por CarviaPagamentoService.desfazer_pagamento.
            db.session.commit()
            return jsonify({
                'sucesso': True,
                'novo_status': resultado['novo_status'],
            })
        except DocumentoNaoEncontradoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 404
        except PagamentoError as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Erro desfazer custo entrega #{custo_id}: {e}")
            return jsonify({'erro': str(e)}), 500

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

    def _executar_gerar_cte_complementar(custo, user_email):
        """Executa a logica tecnica de emissao de CTe Complementar SSW 222.

        Extraida da rota gerar_cte_complementar para ser reutilizavel pelo
        fluxo da tela "Nova Despesa Extra" quando o usuario clica em
        "Emitir CTe Compl. SSW" apos criar o custo.

        Validacoes cobertas:
            - operacao_id preenchido
            - cte_complementar_id nao preenchido
            - status != CANCELADO
            - sem emissao ativa para o mesmo custo
            - operacao existe e possui ctrc_numero
            - ICMS resolvel via campo ou re-parse do XML
            - calculo de valor com grossing up (PIS/COFINS + ICMS)

        Args:
            custo: CarviaCustoEntrega ja persistido em sessao.
            user_email: email do usuario (auditoria).

        Returns:
            tuple(sucesso: bool, mensagem: str, emissao_id: int | None)
        """
        # Guards de estado
        if custo.cte_complementar_id:
            return (False, 'Este custo ja possui CTe Complementar vinculado.', None)
        if custo.status == 'CANCELADO':
            return (False, 'Custo cancelado nao pode gerar CTe Complementar.', None)
        if not custo.operacao_id:
            return (
                False,
                'Este custo nao possui CTe CarVia vinculado (frete sem operacao de venda).',
                None,
            )

        # Verificar emissao em andamento
        emissao_ativa = CarviaEmissaoCteComplementar.query.filter(
            CarviaEmissaoCteComplementar.custo_entrega_id == custo.id,
            CarviaEmissaoCteComplementar.status.in_(['PENDENTE', 'EM_PROCESSAMENTO']),
        ).first()
        if emissao_ativa:
            return (False, 'Ja existe emissao em andamento para este custo.', None)

        operacao = db.session.get(CarviaOperacao, custo.operacao_id)
        if not operacao or not operacao.ctrc_numero:
            return (
                False,
                'Operacao nao possui CTRC. Importe o CTe XML primeiro.',
                None,
            )

        # Resolver ICMS — do campo persistido ou re-parse do XML
        icms = float(operacao.icms_aliquota or 0)
        if icms == 0 and operacao.cte_xml_path:
            try:
                from app.utils.file_storage import get_file_storage
                from app.carvia.services.parsers.cte_xml_parser_carvia import (
                    CTeXMLParserCarvia,
                )
                storage = get_file_storage()
                xml_bytes = storage.download_file(operacao.cte_xml_path)
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
            return (
                False,
                'ICMS nao encontrado para esta operacao. Verifique se o XML do CTe foi importado.',
                None,
            )

        # Calcular valor CTe Complementar: valor / 0.9075 / (1 - icms/100)
        valor_base = float(custo.valor)
        icms_divisor = 1 - (icms / 100)
        if icms_divisor <= 0:
            return (False, 'Aliquota ICMS invalida.', None)

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
                criado_por=user_email,
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
                criado_por=user_email,
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
            return (
                True,
                (
                    f'CTe Complementar {cte_comp.numero_comp} criado — '
                    f'valor {valor_cte:.2f} (base {valor_base:.2f} + PIS/COFINS 9.25% + ICMS {icms}%). '
                    f'Emissao SSW em andamento...'
                ),
                emissao.id,
            )

        except IntegrityError as e:
            db.session.rollback()
            logger.error("IntegrityError ao gerar CTe Complementar: %s", e)
            return (False, 'Erro de integridade ao criar CTe Complementar.', None)
        except Exception as e:
            db.session.rollback()
            logger.error("Erro ao gerar CTe Complementar custo=%s: %s", custo.id, e)
            return (False, f'Erro: {e}', None)

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

        sucesso, mensagem, _emissao_id = _executar_gerar_cte_complementar(
            custo, current_user.email,
        )
        if sucesso:
            flash(mensagem, 'success')
        else:
            # Mensagem ja traz contexto do erro; classificar como warning/danger
            # pela natureza do erro nao e relevante aqui (o helper ja loga).
            flash(mensagem, 'warning')

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

    @bp.route(
        '/api/custos-entrega/emissao-comp/<int:emissao_comp_id>/retry',
        methods=['POST'],
    )  # type: ignore
    @login_required
    def retry_emissao_cte_complementar(emissao_comp_id):  # type: ignore
        """Re-enfileira emissao de CTe Complementar que ficou em ERRO.

        Casos de uso: credenciais ausentes no env, timeout SSW, erro de rede,
        worker down durante o processamento. Reseta status e job_id e chama
        enqueue_job novamente reutilizando o mesmo cte_comp (RASCUNHO).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        emissao = db.session.get(
            CarviaEmissaoCteComplementar, emissao_comp_id
        )
        if not emissao:
            flash('Emissao nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_custos_entrega'))

        if emissao.status != 'ERRO':
            flash(
                f'Emissao nao esta em ERRO (status={emissao.status}). '
                f'Nao pode re-tentar.',
                'warning',
            )
            return redirect(url_for(
                'carvia.detalhe_custo_entrega',
                custo_id=emissao.custo_entrega_id,
            ))

        # Guardar: cte_comp deve estar em RASCUNHO (senao ja emitiu)
        cte_comp = db.session.get(
            CarviaCteComplementar, emissao.cte_complementar_id
        )
        if cte_comp and cte_comp.status != 'RASCUNHO':
            flash(
                f'CTe Complementar ja esta em {cte_comp.status}, '
                f'nao pode re-tentar.',
                'warning',
            )
            return redirect(url_for(
                'carvia.detalhe_custo_entrega',
                custo_id=emissao.custo_entrega_id,
            ))

        try:
            # Reset da emissao
            emissao.status = 'PENDENTE'
            emissao.etapa = None
            emissao.erro_ssw = None
            emissao.atualizado_em = agora_utc_naive()
            db.session.flush()

            # Re-enfileirar job
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
                "EmissaoCteComp %s re-enfileirada (job_id=%s) por %s",
                emissao.id, job.id, current_user.email,
            )
            flash(
                'Emissao re-enfileirada. Aguarde 1-2 minutos para o worker '
                'processar.',
                'success',
            )
        except Exception as e:
            db.session.rollback()
            logger.error(
                "Erro ao re-enfileirar emissao %s: %s", emissao_comp_id, e
            )
            flash(f'Erro ao re-enfileirar: {e}', 'danger')

        return redirect(url_for(
            'carvia.detalhe_custo_entrega',
            custo_id=emissao.custo_entrega_id,
        ))

    # ===================================================================
    # Gerenciar CEs por status de vinculacao a Fatura Transportadora
    # (espelho de gerenciar_despesas_extras do Nacom)
    # ===================================================================

    @bp.route('/custos-entrega/gerenciar') # type: ignore
    @login_required
    def gerenciar_custos_entrega(): # type: ignore
        """Lista CEs agrupados por status de vinculacao a FT.

        Abas:
        - Sem Fatura: fatura_transportadora_id IS NULL, status != CANCELADO
        - Com Fatura: fatura_transportadora_id IS NOT NULL
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        aba = request.args.get('aba', 'sem_fatura')
        filtro_tipo = request.args.get('tipo_custo', '').strip()
        busca = request.args.get('busca', '').strip()

        def _aplicar_filtros(query):
            """Aplica filtros tipo/busca sobre query base (espelho Nacom /despesas/gerenciar)."""
            if filtro_tipo:
                query = query.filter(CarviaCustoEntrega.tipo_custo == filtro_tipo)
            if busca:
                like = f'%{busca}%'
                query = query.filter(
                    db.or_(
                        CarviaCustoEntrega.numero_custo.ilike(like),
                        CarviaCustoEntrega.descricao.ilike(like),
                    )
                )
            return query.order_by(CarviaCustoEntrega.criado_em.desc())

        # Eager loading para evitar N+1 no template que acessa
        # ce.operacao.cte_numero e ce.fatura_transportadora.numero_fatura
        base_query = CarviaCustoEntrega.query.options(
            db.joinedload(CarviaCustoEntrega.operacao),
            db.joinedload(CarviaCustoEntrega.fatura_transportadora),
        )

        query_sem = _aplicar_filtros(
            base_query.filter(
                CarviaCustoEntrega.fatura_transportadora_id.is_(None),
                CarviaCustoEntrega.status != 'CANCELADO',
            )
        )
        query_com = _aplicar_filtros(
            base_query.filter(
                CarviaCustoEntrega.fatura_transportadora_id.isnot(None),
            )
        )

        ces_sem_fatura = query_sem.all()
        ces_com_fatura = query_com.all()

        total_sem = sum(float(ce.valor or 0) for ce in ces_sem_fatura)
        total_com = sum(float(ce.valor or 0) for ce in ces_com_fatura)

        return render_template(
            'carvia/custos_entrega/gerenciar.html',
            ces_sem_fatura=ces_sem_fatura,
            ces_com_fatura=ces_com_fatura,
            total_sem=total_sem,
            total_com=total_com,
            aba=aba,
            filtro_tipo=filtro_tipo,
            busca=busca,
            tipos_custo=TIPOS_CUSTO,
        )

    # ===================================================================
    # Vincular CE a Fatura Transportadora (padrao DespesaExtra.fatura_frete_id)
    # ===================================================================

    @bp.route('/custos-entrega/<int:custo_id>/vincular-fatura', methods=['GET', 'POST']) # type: ignore
    @login_required
    def vincular_fatura_custo_entrega(custo_id): # type: ignore
        """Vincula CE a uma CarviaFaturaTransportadora (tela dedicada).

        GET: renderiza tela com lista de FTs disponiveis da transportadora do frete
        POST: executa vinculacao via CustoEntregaFaturaService
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        custo = db.session.get(CarviaCustoEntrega, custo_id)
        if not custo:
            flash('Custo de entrega nao encontrado.', 'danger')
            return redirect(url_for('carvia.listar_custos_entrega'))

        from app.carvia.services.financeiro.custo_entrega_fatura_service import (
            CustoEntregaFaturaService,
        )

        if request.method == 'POST':
            fatura_id = request.form.get('fatura_transportadora_id', type=int)
            if not fatura_id:
                flash('Selecione uma Fatura Transportadora.', 'warning')
                return redirect(url_for(
                    'carvia.vincular_fatura_custo_entrega', custo_id=custo_id
                ))

            try:
                resultado = CustoEntregaFaturaService.vincular(
                    custo_id, fatura_id, current_user.email
                )
                db.session.commit()
                flash(
                    f'Custo {resultado["ce_numero"]} vinculado a Fatura '
                    f'{resultado["ft_numero"]} com sucesso.',
                    'success',
                )
                return redirect(url_for(
                    'carvia.detalhe_custo_entrega', custo_id=custo_id
                ))
            except ValueError as e:
                db.session.rollback()
                flash(str(e), 'danger')
                return redirect(url_for(
                    'carvia.vincular_fatura_custo_entrega', custo_id=custo_id
                ))
            except Exception as e:
                db.session.rollback()
                logger.exception(f'Erro ao vincular CE #{custo_id} a FT: {e}')
                flash(f'Erro: {e}', 'danger')
                return redirect(url_for(
                    'carvia.vincular_fatura_custo_entrega', custo_id=custo_id
                ))

        # GET
        faturas = CustoEntregaFaturaService.faturas_disponiveis(custo_id)
        return render_template(
            'carvia/custos_entrega/vincular_fatura.html',
            custo=custo,
            faturas_disponiveis=faturas,
        )

    @bp.route('/custos-entrega/<int:custo_id>/desvincular-fatura', methods=['POST']) # type: ignore
    @login_required
    def desvincular_fatura_custo_entrega(custo_id): # type: ignore
        """Remove vinculo CE <-> Fatura Transportadora."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        try:
            from app.carvia.services.financeiro.custo_entrega_fatura_service import (
                CustoEntregaFaturaService,
            )
            resultado = CustoEntregaFaturaService.desvincular(
                custo_id, current_user.email
            )
            db.session.commit()
            return jsonify(resultado)
        except ValueError as e:
            db.session.rollback()
            return jsonify({'sucesso': False, 'erro': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.exception(f'Erro ao desvincular CE #{custo_id}: {e}')
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route('/api/custos-entrega/<int:custo_id>/faturas-transportadora-disponiveis') # type: ignore
    @login_required
    def api_faturas_transportadora_disponiveis(custo_id): # type: ignore
        """Retorna JSON com CarviaFaturaTransportadora disponiveis para vincular este CE."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        try:
            from app.carvia.services.financeiro.custo_entrega_fatura_service import (
                CustoEntregaFaturaService,
            )
            faturas = CustoEntregaFaturaService.faturas_disponiveis(custo_id)
            return jsonify({'faturas': faturas})
        except Exception as e:
            logger.error(
                f'Erro ao buscar FTs disponiveis para CE #{custo_id}: {e}'
            )
            return jsonify({'erro': str(e)}), 500

    # ===================================================================
    # Vincular multiplos CEs a uma FT (reverso — pela tela da FT)
    # ===================================================================

    @bp.route('/api/faturas-transportadora/<int:fatura_id>/custos-entrega-disponiveis') # type: ignore
    @login_required
    def api_custos_entrega_disponiveis_para_ft(fatura_id): # type: ignore
        """Retorna JSON com CarviaCustoEntrega elegiveis para vincular a esta FT.

        Usado pelo modal 'Vincular CE' na tela de detalhe da fatura
        transportadora. Filtra por transportadora da FT (navegacao CE ->
        CarviaFrete -> CarviaSubcontrato -> transportadora_id).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        from app.carvia.models import CarviaFaturaTransportadora

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            return jsonify({'sucesso': False, 'erro': 'Fatura nao encontrada'}), 404

        pode, razao = fatura.pode_editar()
        if not pode:
            return jsonify({'sucesso': False, 'erro': razao}), 400

        try:
            from app.carvia.services.financeiro.custo_entrega_fatura_service import (
                CustoEntregaFaturaService,
            )
            custos = CustoEntregaFaturaService.ces_disponiveis_para_fatura(fatura_id)
            return jsonify({'sucesso': True, 'custos': custos})
        except Exception as e:
            logger.error(
                f'Erro ao buscar CEs disponiveis para FT #{fatura_id}: {e}'
            )
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @bp.route(
        '/faturas-transportadora/<int:fatura_id>/vincular-custos-entrega',
        methods=['POST'],
    ) # type: ignore
    @login_required
    def vincular_custos_entrega_fatura(fatura_id): # type: ignore
        """Vincula uma lista de CEs a uma CarviaFaturaTransportadora.

        Recebe JSON `{custo_ids: [1, 2, 3]}`. Executa vinculacao em loop
        via `CustoEntregaFaturaService.vincular()`. Se qualquer CE falhar,
        faz rollback de toda a transacao e reporta o primeiro erro.
        Espelha o padrao de `anexar_subcontratos_fatura_transportadora`.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403

        from app.carvia.models import CarviaFaturaTransportadora

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            return jsonify({'sucesso': False, 'erro': 'Fatura nao encontrada'}), 404

        pode, razao = fatura.pode_editar()
        if not pode:
            return jsonify({'sucesso': False, 'erro': razao}), 400

        payload = request.get_json(silent=True) or {}
        custo_ids = payload.get('custo_ids') or []
        if not isinstance(custo_ids, list) or not custo_ids:
            return jsonify(
                {'sucesso': False, 'erro': 'Lista de custo_ids obrigatoria'}
            ), 400

        try:
            from app.carvia.services.financeiro.custo_entrega_fatura_service import (
                CustoEntregaFaturaService,
            )
            vinculados = []
            for custo_id in custo_ids:
                try:
                    custo_id_int = int(custo_id)
                except (ValueError, TypeError):
                    db.session.rollback()
                    return jsonify({
                        'sucesso': False,
                        'erro': f'ID invalido: {custo_id}',
                    }), 400

                resultado = CustoEntregaFaturaService.vincular(
                    custo_id_int, fatura_id, current_user.email,
                )
                vinculados.append(resultado['ce_numero'])

            db.session.commit()
            logger.info(
                "FT #%d: %d CEs vinculados por %s (%s)",
                fatura_id, len(vinculados), current_user.email, vinculados,
            )
            return jsonify({
                'sucesso': True,
                'vinculados': vinculados,
                'total': len(vinculados),
            })
        except ValueError as e:
            db.session.rollback()
            return jsonify({'sucesso': False, 'erro': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            logger.exception(
                f'Erro ao vincular CEs a FT #{fatura_id}: {e}'
            )
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    # =====================================================================
    # DESPESAS EXTRAS (xerox DespesaExtra Nacom)
    # =====================================================================
    # Fluxo de COMPRA: cria despesa extra vinculada ao CarviaFrete, similar
    # ao fluxo do modulo fretes (Nacom). 2 fluxos de criacao:
    #   1. Via busca por NF: /carvia/despesas-extras/nova
    #   2. Via botao do frete: /carvia/fretes/<id>/despesas-extras/nova
    # Paridade com app/fretes/routes.py linhas 2832-3175, 4246-4398, 4632-4670.

    def _popular_choices_despesa_form(form, frete):
        """Popula choices dinamicos dos forms CarviaDespesaExtra.

        - tipo_despesa: reusa CarviaCustoEntrega.TIPOS_CUSTO
        - transportadora_id: inclui opcao default "usar do frete"
        - data_custo: default hoje (apenas em GET, nao sobrescreve submit)
        """
        from app.transportadoras.models import Transportadora
        form.tipo_despesa.choices = [(t, t) for t in CarviaCustoEntrega.TIPOS_CUSTO]
        transportadoras_ativas = (
            Transportadora.query
            .order_by(Transportadora.razao_social)
            .all()
        )
        label_default = (
            f'-- Usar transportadora do frete '
            f'({frete.transportadora.razao_social}) --'
        ) if frete and frete.transportadora else '-- Usar transportadora do frete --'
        form.transportadora_id.choices = [('', label_default)] + [
            (str(t.id), t.razao_social) for t in transportadoras_ativas
        ]
        if not form.data_custo.data:
            form.data_custo.data = date.today()

    def _converter_valor_br(valor_str):
        """Converte valor formato brasileiro para float."""
        from app.utils.valores_brasileiros import converter_valor_brasileiro
        return converter_valor_brasileiro(valor_str)

    # -----------------------------------------------------------------
    # Fluxo 1 — Etapa 1: Buscar frete por NF
    # -----------------------------------------------------------------
    @bp.route('/despesas-extras/nova', methods=['GET', 'POST'])  # type: ignore
    @login_required
    def nova_despesa_extra_por_nf_carvia():  # type: ignore
        """Busca CarviaFrete por numero de NF para criar despesa extra.

        Xerox de fretes.nova_despesa_extra_por_nf.

        Suporta `numero_nf` via GET (?numero_nf=X) para integracao com o
        monitoramento (botao "Lancar Custo Extra CarVia" em visualizar_entrega.html).
        Quando GET traz numero_nf, executa a busca automaticamente.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaFrete

        # Aceita numero_nf via POST (form) OU GET (?numero_nf=X do monitoramento)
        numero_nf = (
            request.form.get('numero_nf')
            or request.args.get('numero_nf')
            or ''
        ).strip()

        if numero_nf:
            # Match EXATO em CSV (4 patterns) — evita falso-positivo com contains()
            # Ex: NF '12' nao deve casar com '12345' dentro de '1,12345,999'
            fretes_encontrados = (
                CarviaFrete.query
                .filter(
                    db.or_(
                        CarviaFrete.numeros_nfs == numero_nf,
                        CarviaFrete.numeros_nfs.like(f"{numero_nf},%"),
                        CarviaFrete.numeros_nfs.like(f"%,{numero_nf},%"),
                        CarviaFrete.numeros_nfs.like(f"%,{numero_nf}"),
                    )
                )
                .order_by(CarviaFrete.criado_em.desc())
                .all()
            )

            if not fretes_encontrados:
                flash(
                    f'Nenhum CarviaFrete encontrado para NF {numero_nf}. '
                    f'O frete e gerado automaticamente quando o embarque '
                    f'passa pela portaria.',
                    'warning',
                )
                return render_template('carvia/custos_entrega/nova_por_nf.html')

            # 1 resultado: redireciona direto para o form de criacao
            if len(fretes_encontrados) == 1:
                return redirect(url_for(
                    'carvia.criar_despesa_por_frete_carvia',
                    frete_id=fretes_encontrados[0].id,
                ))

            # Multiplos: usuario escolhe qual frete
            return render_template(
                'carvia/custos_entrega/selecionar_frete.html',
                fretes=fretes_encontrados,
                numero_nf=numero_nf,
            )

        return render_template('carvia/custos_entrega/nova_por_nf.html')

    # -----------------------------------------------------------------
    # Fluxo 1 — Etapa 2: Criar despesa para frete selecionado
    # -----------------------------------------------------------------
    @bp.route(
        '/despesas-extras/criar/<int:frete_id>',
        methods=['GET', 'POST'],
    )  # type: ignore
    @login_required
    def criar_despesa_por_frete_carvia(frete_id):  # type: ignore
        """Criar despesa extra para CarviaFrete selecionado (fluxo unificado).

        Cobre AMBOS os dominios:
        - COMPRA (frete sem operacao de venda): custo fica ligado apenas ao frete.
        - VENDA (frete com CarviaOperacao vinculada): custo herda operacao_id do
          frete e fica elegivel para emissao de CTe Complementar SSW 222.

        A escolha entre apenas criar o custo ou criar + emitir CTe Comp. e feita
        via botoes distintos no template (acao=sem_emissao ou acao=emitir_ssw).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaFrete
        from app.carvia.forms import CarviaDespesaExtraForm

        frete = db.session.get(CarviaFrete, frete_id)
        if not frete:
            flash('Frete CarVia nao encontrado.', 'warning')
            return redirect(url_for('carvia.nova_despesa_extra_por_nf_carvia'))

        form = CarviaDespesaExtraForm()
        _popular_choices_despesa_form(form, frete)

        if form.validate_on_submit():
            try:
                # Mapear beneficiario → transportadora_id / fornecedor_nome / fornecedor_cnpj
                tipo_benef = form.tipo_beneficiario.data
                transportadora_id_final = None
                fornecedor_nome_final = None
                fornecedor_cnpj_final = None
                if tipo_benef == 'TRANSPORTADORA':
                    transportadora_id_final = form.transportadora_id.data or None
                elif tipo_benef == 'DESTINATARIO':
                    fornecedor_nome_final = frete.nome_destino
                    fornecedor_cnpj_final = frete.cnpj_destino
                elif tipo_benef == 'OUTROS':
                    fornecedor_nome_final = (form.beneficiario_nome.data or '').strip() or None

                data_custo_final = form.data_custo.data or date.today()

                custo = CarviaCustoEntrega(
                    numero_custo=CarviaCustoEntrega.gerar_numero_custo(),
                    # Deriva operacao_id do frete (venda quando disponivel)
                    operacao_id=frete.operacao_id,
                    frete_id=frete_id,
                    fatura_transportadora_id=None,
                    transportadora_id=transportadora_id_final,
                    fornecedor_nome=fornecedor_nome_final,
                    fornecedor_cnpj=fornecedor_cnpj_final,
                    tipo_custo=form.tipo_despesa.data,
                    tipo_documento='PENDENTE_DOCUMENTO',
                    numero_documento='PENDENTE_FATURA',
                    valor=_converter_valor_br(form.valor_despesa.data),
                    data_custo=data_custo_final,
                    data_vencimento=data_custo_final,
                    status='PENDENTE',
                    observacoes=form.observacoes.data or None,
                    criado_por=current_user.email,
                )
                db.session.add(custo)
                db.session.flush()

                # Processar anexos (comprovantes/emails)
                _processar_anexos_despesa(custo, form.anexos.data)

                db.session.commit()

                # Detectar acao: emitir CTe Comp. SSW ou so criar
                acao = request.form.get('acao', 'sem_emissao')
                if acao == 'emitir_ssw':
                    sucesso, mensagem, _emissao_id = _executar_gerar_cte_complementar(
                        custo, current_user.email,
                    )
                    if sucesso:
                        flash(
                            f'Despesa extra {custo.numero_custo} criada. {mensagem}',
                            'success',
                        )
                    else:
                        flash(
                            f'Despesa extra {custo.numero_custo} criada, mas nao foi '
                            f'possivel emitir CTe Complementar: {mensagem}',
                            'warning',
                        )
                else:
                    flash(
                        f'Despesa extra {custo.numero_custo} criada com sucesso!',
                        'success',
                    )
                return redirect(url_for(
                    'carvia.detalhe_frete_carvia', id=frete_id
                ))

            except ValueError as ve:
                db.session.rollback()
                flash(f'Dados invalidos: {ve}', 'warning')
            except Exception as e:
                db.session.rollback()
                logger.error(f'Erro ao criar despesa extra: {e}')
                flash(f'Erro ao criar despesa extra: {e}', 'danger')

        return render_template(
            'carvia/custos_entrega/criar_por_frete.html',
            form=form,
            frete=frete,
            today=date.today(),
        )

    # -----------------------------------------------------------------
    # Fluxo 2: Criar despesa diretamente do CarviaFrete (botao)
    # -----------------------------------------------------------------
    @bp.route(
        '/fretes/<int:frete_id>/despesas-extras/nova',
        methods=['GET', 'POST'],
    )  # type: ignore
    @login_required
    def nova_despesa_do_frete_carvia(frete_id):  # type: ignore
        """Criar despesa extra direto do CarviaFrete (fluxo botao).

        Igual ao fluxo /despesas-extras/criar/<frete_id> mas acessado via
        botao na tela do frete. Mesma logica unificada (venda + compra).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import CarviaFrete
        from app.carvia.forms import CarviaDespesaExtraForm

        frete = db.session.get(CarviaFrete, frete_id)
        if not frete:
            flash('Frete CarVia nao encontrado.', 'warning')
            return redirect(url_for('carvia.listar_fretes_carvia'))

        form = CarviaDespesaExtraForm()
        _popular_choices_despesa_form(form, frete)

        if form.validate_on_submit():
            try:
                # Mapear beneficiario → transportadora_id / fornecedor_nome / fornecedor_cnpj
                tipo_benef = form.tipo_beneficiario.data
                transportadora_id_final = None
                fornecedor_nome_final = None
                fornecedor_cnpj_final = None
                if tipo_benef == 'TRANSPORTADORA':
                    transportadora_id_final = form.transportadora_id.data or None
                elif tipo_benef == 'DESTINATARIO':
                    fornecedor_nome_final = frete.nome_destino
                    fornecedor_cnpj_final = frete.cnpj_destino
                elif tipo_benef == 'OUTROS':
                    fornecedor_nome_final = (form.beneficiario_nome.data or '').strip() or None

                data_custo_final = form.data_custo.data or date.today()

                custo = CarviaCustoEntrega(
                    numero_custo=CarviaCustoEntrega.gerar_numero_custo(),
                    operacao_id=frete.operacao_id,
                    frete_id=frete_id,
                    fatura_transportadora_id=None,
                    transportadora_id=transportadora_id_final,
                    fornecedor_nome=fornecedor_nome_final,
                    fornecedor_cnpj=fornecedor_cnpj_final,
                    tipo_custo=form.tipo_despesa.data,
                    tipo_documento='PENDENTE_DOCUMENTO',
                    numero_documento='PENDENTE_FATURA',
                    valor=_converter_valor_br(form.valor_despesa.data),
                    data_custo=data_custo_final,
                    data_vencimento=data_custo_final,
                    status='PENDENTE',
                    observacoes=form.observacoes.data or None,
                    criado_por=current_user.email,
                )
                db.session.add(custo)
                db.session.flush()
                _processar_anexos_despesa(custo, form.anexos.data)
                db.session.commit()

                acao = request.form.get('acao', 'sem_emissao')
                if acao == 'emitir_ssw':
                    sucesso, mensagem, _emissao_id = _executar_gerar_cte_complementar(
                        custo, current_user.email,
                    )
                    if sucesso:
                        flash(
                            f'Despesa extra {custo.numero_custo} criada. {mensagem}',
                            'success',
                        )
                    else:
                        flash(
                            f'Despesa extra {custo.numero_custo} criada, mas nao foi '
                            f'possivel emitir CTe Complementar: {mensagem}',
                            'warning',
                        )
                else:
                    flash(
                        f'Despesa extra {custo.numero_custo} criada com sucesso!',
                        'success',
                    )
                return redirect(url_for(
                    'carvia.detalhe_frete_carvia', id=frete_id
                ))

            except ValueError as ve:
                db.session.rollback()
                flash(f'Dados invalidos: {ve}', 'warning')
            except Exception as e:
                db.session.rollback()
                logger.error(f'Erro ao criar despesa extra: {e}')
                flash(f'Erro ao criar despesa extra: {e}', 'danger')

        return render_template(
            'carvia/custos_entrega/nova_do_frete.html',
            form=form,
            frete=frete,
            today=date.today(),
        )

    # -----------------------------------------------------------------
    # Editar documento (so apos vincular fatura)
    # -----------------------------------------------------------------
    @bp.route(
        '/despesas-extras/<int:custo_id>/editar-documento',
        methods=['GET', 'POST'],
    )  # type: ignore
    @login_required
    def editar_documento_despesa_carvia(custo_id):  # type: ignore
        """Editar tipo_documento e numero_documento apos vincular fatura.

        Xerox de fretes.editar_documento_despesa.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        custo = db.session.get(CarviaCustoEntrega, custo_id)
        if not custo:
            flash('Despesa extra nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_custos_entrega'))

        # Valida que a despesa tem fatura vinculada
        if not custo.fatura_transportadora_id:
            flash(
                'Para preencher o numero do documento, a fatura deve estar '
                'vinculada primeiro!',
                'warning',
            )
            if custo.frete_id:
                return redirect(url_for(
                    'carvia.detalhe_frete_carvia', id=custo.frete_id
                ))
            return redirect(url_for(
                'carvia.detalhe_custo_entrega', custo_id=custo_id
            ))

        if request.method == 'POST':
            numero_documento = (
                request.form.get('numero_documento') or ''
            ).strip()
            tipo_documento = request.form.get('tipo_documento', '').strip()

            if not numero_documento:
                flash('Numero do documento e obrigatorio!', 'warning')
            elif numero_documento == 'PENDENTE_FATURA':
                flash('Este numero nao e permitido!', 'warning')
            else:
                try:
                    custo.numero_documento = numero_documento
                    custo.tipo_documento = tipo_documento
                    db.session.commit()
                    flash('Documento atualizado com sucesso!', 'success')
                    if custo.frete_id:
                        return redirect(url_for(
                            'carvia.detalhe_frete_carvia', id=custo.frete_id
                        ))
                    return redirect(url_for(
                        'carvia.detalhe_custo_entrega', custo_id=custo_id
                    ))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erro ao atualizar documento: {e}', 'danger')

        return render_template(
            'carvia/custos_entrega/editar_documento.html',
            custo=custo,
            fatura=custo.fatura_transportadora,
        )

    # -----------------------------------------------------------------
    # Excluir despesa extra (xerox Nacom)
    # -----------------------------------------------------------------
    @bp.route(
        '/despesas-extras/<int:custo_id>/excluir',
        methods=['POST'],
    )  # type: ignore
    @login_required
    def excluir_despesa_extra_carvia(custo_id):  # type: ignore
        """Excluir despesa extra (bloqueia se PAGO ou fatura conferida).

        Xerox de fretes.excluir_despesa_extra.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        custo = db.session.get(CarviaCustoEntrega, custo_id)
        if not custo:
            flash('Despesa extra nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_custos_entrega'))

        frete_id = custo.frete_id

        # Gates
        if custo.status == 'PAGO':
            flash(
                'Nao e possivel excluir despesa extra com status PAGO!',
                'danger',
            )
            if frete_id:
                return redirect(url_for(
                    'carvia.detalhe_frete_carvia', id=frete_id
                ))
            return redirect(url_for('carvia.listar_custos_entrega'))

        if custo.fatura_transportadora_id and custo.fatura_transportadora:
            if custo.fatura_transportadora.status_conferencia == 'CONFERIDO':
                flash(
                    'Nao e possivel excluir despesa de fatura CONFERIDA!',
                    'danger',
                )
                if frete_id:
                    return redirect(url_for(
                        'carvia.detalhe_frete_carvia', id=frete_id
                    ))
                return redirect(url_for('carvia.listar_custos_entrega'))

        try:
            tipo = custo.tipo_custo
            numero_custo = custo.numero_custo
            valor = float(custo.valor or 0)

            db.session.delete(custo)
            db.session.commit()

            flash(
                f'Despesa extra {numero_custo} excluida com sucesso! '
                f'Tipo: {tipo} | Valor: R$ {valor:.2f}',
                'success',
            )
        except Exception as e:
            db.session.rollback()
            logger.exception(f'Erro ao excluir despesa extra #{custo_id}: {e}')
            flash(f'Erro ao excluir despesa extra: {e}', 'danger')

        if frete_id:
            return redirect(url_for(
                'carvia.detalhe_frete_carvia', id=frete_id
            ))
        return redirect(url_for('carvia.listar_custos_entrega'))

    # -----------------------------------------------------------------
    # Vincular/desvincular CTe Complementar (rastreabilidade da cobranca)
    # -----------------------------------------------------------------
    @bp.route(
        '/despesas-extras/<int:custo_id>/vincular-cte-comp',
        methods=['GET', 'POST'],
    )  # type: ignore
    @login_required
    def vincular_cte_comp_despesa_carvia(custo_id):  # type: ignore
        """Vincular CarviaCteComplementar existente a despesa extra.

        Xerox de fretes.vincular_cte_despesa — rastrea cobranca ao cliente.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        custo = db.session.get(CarviaCustoEntrega, custo_id)
        if not custo:
            flash('Despesa extra nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_custos_entrega'))

        if request.method == 'POST':
            cte_comp_id_str = (
                request.form.get('cte_complementar_id') or ''
            ).strip()
            if not cte_comp_id_str:
                flash('Selecione um CTe Complementar!', 'warning')
                return redirect(url_for(
                    'carvia.vincular_cte_comp_despesa_carvia',
                    custo_id=custo_id,
                ))

            try:
                cte_comp = db.session.get(
                    CarviaCteComplementar, int(cte_comp_id_str)
                )
                if not cte_comp:
                    flash('CTe Complementar nao encontrado.', 'warning')
                else:
                    custo.cte_complementar_id = cte_comp.id
                    db.session.commit()
                    flash(
                        f'CTe Complementar {cte_comp.numero_comp} '
                        f'vinculado com sucesso!',
                        'success',
                    )
                    if custo.frete_id:
                        return redirect(url_for(
                            'carvia.detalhe_frete_carvia', id=custo.frete_id
                        ))
                    return redirect(url_for(
                        'carvia.detalhe_custo_entrega', custo_id=custo_id
                    ))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao vincular CTe Comp.: {e}', 'danger')

        # GET: listar CTes Complementares disponiveis
        # Prioriza CTes da mesma operacao (se existir) e do mesmo frete
        query = CarviaCteComplementar.query.filter(
            CarviaCteComplementar.status != 'CANCELADO',
        )
        if custo.operacao_id:
            query = query.filter(
                CarviaCteComplementar.operacao_id == custo.operacao_id
            )
        ctes_disponiveis = query.order_by(
            CarviaCteComplementar.criado_em.desc()
        ).all()

        return render_template(
            'carvia/custos_entrega/vincular_cte_complementar.html',
            custo=custo,
            ctes_disponiveis=ctes_disponiveis,
        )

    @bp.route(
        '/despesas-extras/<int:custo_id>/desvincular-cte-comp',
        methods=['POST'],
    )  # type: ignore
    @login_required
    def desvincular_cte_comp_despesa_carvia(custo_id):  # type: ignore
        """Desvincula CarviaCteComplementar de uma despesa extra."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        custo = db.session.get(CarviaCustoEntrega, custo_id)
        if not custo:
            flash('Despesa extra nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_custos_entrega'))

        try:
            custo.cte_complementar_id = None
            db.session.commit()
            flash('CTe Complementar desvinculado.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao desvincular CTe Comp.: {e}', 'danger')

        if custo.frete_id:
            return redirect(url_for(
                'carvia.detalhe_frete_carvia', id=custo.frete_id
            ))
        return redirect(url_for(
            'carvia.detalhe_custo_entrega', custo_id=custo_id
        ))

    # -----------------------------------------------------------------
    # Vincular fatura (xerox Nacom — rota paralela a vincular_fatura_custo_entrega)
    # -----------------------------------------------------------------
    @bp.route(
        '/despesas-extras/<int:custo_id>/vincular-fatura',
        methods=['GET', 'POST'],
    )  # type: ignore
    @login_required
    def vincular_despesa_fatura_carvia(custo_id):  # type: ignore
        """Vincular despesa extra a fatura transportadora (xerox Nacom).

        Form POST recebe: fatura_id, tipo_documento_cobranca, valor_cobranca,
        numero_cte_documento. Atualiza CE + chama CustoEntregaFaturaService.

        Xerox de fretes.vincular_despesa_fatura.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.models import (
            CarviaCustoEntrega, CarviaFaturaTransportadora, CarviaFrete,
        )
        from app.carvia.services.financeiro.custo_entrega_fatura_service import (
            CustoEntregaFaturaService,
        )

        custo = db.session.get(CarviaCustoEntrega, custo_id)
        if not custo:
            flash('Despesa extra nao encontrada.', 'warning')
            return redirect(url_for('carvia.listar_custos_entrega'))

        frete = (
            db.session.get(CarviaFrete, custo.frete_id)
            if custo.frete_id else None
        )

        # Faturas disponiveis = nao CONFERIDAS e nao PAGAS
        faturas_disponiveis = CarviaFaturaTransportadora.query.filter(
            CarviaFaturaTransportadora.status_conferencia != 'CONFERIDO',
            CarviaFaturaTransportadora.status_pagamento != 'PAGO',
        ).order_by(CarviaFaturaTransportadora.criado_em.desc()).all()

        if request.method == 'POST':
            fatura_id_str = (request.form.get('fatura_id') or '').strip()
            tipo_documento_cobranca = request.form.get('tipo_documento_cobranca')
            valor_cobranca_str = request.form.get('valor_cobranca')
            numero_cte_documento = (
                request.form.get('numero_cte_documento') or ''
            ).strip()

            if not fatura_id_str:
                flash('Selecione uma fatura!', 'warning')
                return render_template(
                    'carvia/custos_entrega/vincular_despesa_fatura.html',
                    custo=custo,
                    frete=frete,
                    faturas_disponiveis=faturas_disponiveis,
                )

            try:
                fatura = db.session.get(
                    CarviaFaturaTransportadora, int(fatura_id_str)
                )
                if not fatura:
                    flash('Fatura nao encontrada!', 'warning')
                    return render_template(
                        'carvia/custos_entrega/vincular_despesa_fatura.html',
                        custo=custo,
                        frete=frete,
                        faturas_disponiveis=faturas_disponiveis,
                    )

                valor_cobranca_float = (
                    _converter_valor_br(valor_cobranca_str)
                    if valor_cobranca_str else float(custo.valor or 0)
                )

                # Atualiza dados do CE antes de vincular via service
                custo.tipo_documento = tipo_documento_cobranca
                custo.valor = valor_cobranca_float
                custo.numero_documento = (
                    numero_cte_documento if numero_cte_documento
                    else 'PENDENTE_FATURA'
                )
                if fatura.vencimento:
                    custo.data_vencimento = fatura.vencimento

                # Vincula via service (valida regras de integridade)
                CustoEntregaFaturaService.vincular(
                    custo.id, fatura.id, current_user.email,
                )

                db.session.commit()
                flash(
                    f'Despesa extra vinculada a fatura {fatura.numero_fatura}!',
                    'success',
                )

                if custo.frete_id:
                    return redirect(url_for(
                        'carvia.detalhe_frete_carvia', id=custo.frete_id
                    ))
                return redirect(url_for(
                    'carvia.detalhe_custo_entrega', custo_id=custo_id
                ))

            except ValueError as ve:
                db.session.rollback()
                flash(f'{ve}', 'warning')
            except Exception as e:
                db.session.rollback()
                logger.exception(
                    f'Erro ao vincular despesa extra #{custo_id} a fatura: {e}'
                )
                flash(f'Erro ao vincular: {e}', 'danger')

        return render_template(
            'carvia/custos_entrega/vincular_despesa_fatura.html',
            custo=custo,
            frete=frete,
            faturas_disponiveis=faturas_disponiveis,
        )

    # -----------------------------------------------------------------
    # Helper: processar anexos
    # -----------------------------------------------------------------
    def _processar_anexos_despesa(custo, arquivos):
        """Processa upload de anexos (comprovantes/emails) para um CE.

        Reusa sistema existente de CarviaCustoEntregaAnexo + S3.
        Chama `storage.save_file(file, folder=...)` (mesmo padrao do
        `upload_anexo_custo_entrega` linha 752). O storage gera nome
        automatico com timestamp+uuid e retorna o caminho final, que e
        persistido em `CarviaCustoEntregaAnexo.caminho_s3`.
        """
        if not arquivos:
            return

        from app.utils.file_storage import get_file_storage

        storage = get_file_storage()
        for arquivo in arquivos:
            if not arquivo or not arquivo.filename:
                continue
            if not _allowed_file(arquivo.filename):
                continue

            try:
                arquivo.seek(0)
                caminho_s3 = storage.save_file(
                    arquivo,
                    folder=f'carvia/custos-entrega/anexos',
                )
                if not caminho_s3:
                    logger.warning(
                        f'storage.save_file retornou None para {arquivo.filename}'
                    )
                    continue

                # Extrair metadados de email se aplicavel
                email_metadata = {}
                ext = (
                    arquivo.filename.rsplit('.', 1)[1].lower()
                    if '.' in arquivo.filename else ''
                )
                if ext in ('msg', 'eml'):
                    try:
                        from app.utils.email_handler import EmailHandler
                        email_handler = EmailHandler()
                        arquivo.seek(0)
                        if ext == 'msg':
                            email_metadata = (
                                email_handler.processar_email_msg(arquivo) or {}
                            )
                        else:
                            email_metadata = (
                                email_handler.processar_email_eml(arquivo) or {}
                            )
                    except Exception as e_email:
                        logger.warning(
                            f"Nao foi possivel extrair metadados do email: {e_email}"
                        )

                anexo = CarviaCustoEntregaAnexo(
                    custo_entrega_id=custo.id,
                    nome_original=arquivo.filename,
                    nome_arquivo=os.path.basename(caminho_s3),
                    caminho_s3=caminho_s3,
                    content_type=getattr(arquivo, 'content_type', None),
                    criado_por=current_user.email,
                    ativo=True,
                    email_remetente=email_metadata.get('remetente'),
                    email_assunto=email_metadata.get('assunto'),
                    email_data_envio=email_metadata.get('data_envio'),
                    email_conteudo_preview=(email_metadata.get('conteudo_preview') or '')[:500] or None,
                )
                db.session.add(anexo)
            except Exception as e:
                logger.error(
                    f'Erro ao salvar anexo {arquivo.filename} para CE '
                    f'#{custo.id}: {e}'
                )
