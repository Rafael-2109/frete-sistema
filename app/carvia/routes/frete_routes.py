"""
Rotas de Fretes CarVia — Listagem, detalhe, edicao e vinculacao de CTe/Fatura

CarviaFrete e o eixo central: agrupa EmbarqueItems por (cnpj_emitente, cnpj_destino).
Tem 2 lados:
  - CUSTO (subcontrato): tabela Nacom, gera CarviaSubcontrato → Fatura Transportadora
  - VENDA (operacao):    tabela CarVia, gera CarviaOperacao → Fatura Cliente
"""

import logging
from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user

from app import db
from app.carvia.models import (
    CarviaFrete, CarviaOperacao, CarviaSubcontrato,
    CarviaFaturaCliente, CarviaFaturaTransportadora, CarviaNf,
)

logger = logging.getLogger(__name__)


def register_frete_routes(bp):

    # ------------------------------------------------------------------
    # Listar
    # ------------------------------------------------------------------

    @bp.route('/fretes')  # type: ignore
    @login_required
    def listar_fretes_carvia():  # type: ignore
        """Lista CarviaFretes com filtros e paginacao."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        page = request.args.get('page', 1, type=int)
        per_page = 50

        # Filtros
        filtro_id = request.args.get('id', '', type=str).strip()
        filtro_embarque = request.args.get('embarque', '', type=str).strip()
        filtro_emitente = request.args.get('emitente', '', type=str).strip()
        filtro_destino = request.args.get('destino', '', type=str).strip()
        filtro_nf = request.args.get('nf', '', type=str).strip()
        filtro_status = request.args.get('status', '', type=str).strip()
        filtro_transportadora = request.args.get('transportadora', '', type=str).strip()
        filtro_data_de = request.args.get('data_de', '', type=str).strip()
        filtro_data_ate = request.args.get('data_ate', '', type=str).strip()

        query = CarviaFrete.query

        if filtro_id:
            try:
                query = query.filter(CarviaFrete.id == int(filtro_id))
            except ValueError:
                pass
        if filtro_embarque:
            from app.embarques.models import Embarque
            query = query.join(Embarque).filter(Embarque.numero.ilike(f'%{filtro_embarque}%'))
        if filtro_emitente:
            query = query.filter(
                db.or_(
                    CarviaFrete.cnpj_emitente.ilike(f'%{filtro_emitente}%'),
                    CarviaFrete.nome_emitente.ilike(f'%{filtro_emitente}%'),
                )
            )
        if filtro_destino:
            query = query.filter(
                db.or_(
                    CarviaFrete.cnpj_destino.ilike(f'%{filtro_destino}%'),
                    CarviaFrete.nome_destino.ilike(f'%{filtro_destino}%'),
                )
            )
        if filtro_nf:
            query = query.filter(CarviaFrete.numeros_nfs.ilike(f'%{filtro_nf}%'))
        if filtro_status:
            query = query.filter(CarviaFrete.status == filtro_status)
        if filtro_transportadora:
            from app.transportadoras.models import Transportadora
            query = query.join(Transportadora).filter(
                Transportadora.razao_social.ilike(f'%{filtro_transportadora}%')
            )
        if filtro_data_de:
            from datetime import datetime as dt_mod
            query = query.filter(CarviaFrete.criado_em >= dt_mod.strptime(filtro_data_de, '%Y-%m-%d'))
        if filtro_data_ate:
            from datetime import datetime as dt_mod
            dt_ate = dt_mod.strptime(filtro_data_ate, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(CarviaFrete.criado_em <= dt_ate)

        paginacao = query.order_by(CarviaFrete.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return render_template(
            'carvia/fretes/listar.html',
            fretes=paginacao.items,
            paginacao=paginacao,
            filtro_id=filtro_id,
            filtro_embarque=filtro_embarque,
            filtro_emitente=filtro_emitente,
            filtro_destino=filtro_destino,
            filtro_nf=filtro_nf,
            filtro_status=filtro_status,
            filtro_transportadora=filtro_transportadora,
            filtro_data_de=filtro_data_de,
            filtro_data_ate=filtro_data_ate,
        )

    # ------------------------------------------------------------------
    # Detalhe
    # ------------------------------------------------------------------

    @bp.route('/fretes/<int:id>')  # type: ignore
    @login_required
    def detalhe_frete_carvia(id):  # type: ignore
        """Detalhe de um CarviaFrete com paineis CUSTO e VENDA."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        frete = CarviaFrete.query.get_or_404(id)

        # Carregar entidades vinculadas
        operacao = frete.operacao if frete.operacao_id else None
        subcontrato = frete.subcontrato if frete.subcontrato_id else None
        fatura_cliente = frete.fatura_cliente_rel if frete.fatura_cliente_id else None
        fatura_transportadora = frete.fatura_transportadora_rel if frete.fatura_transportadora_id else None

        return render_template(
            'carvia/fretes/detalhe.html',
            frete=frete,
            operacao=operacao,
            subcontrato=subcontrato,
            fatura_cliente=fatura_cliente,
            fatura_transportadora=fatura_transportadora,
        )

    # ------------------------------------------------------------------
    # Editar
    # ------------------------------------------------------------------

    @bp.route('/fretes/<int:id>/editar', methods=['GET', 'POST'])  # type: ignore
    @login_required
    def editar_frete_carvia(id):  # type: ignore
        """Editar valores do CarviaFrete.

        Campos CUSTO (valor_cte, valor_considerado, valor_pago) so sao
        editaveis se frete tem fatura_transportadora vinculada.
        Campos VENDA (valor_venda) e observacoes sao sempre editaveis.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        frete = CarviaFrete.query.get_or_404(id)
        custo_editavel = bool(frete.fatura_transportadora_id)

        if request.method == 'POST':
            try:
                # Campos CUSTO — so processar se tem fatura transportadora
                if custo_editavel:
                    valor_cte = request.form.get('valor_cte', '').strip().replace('.', '').replace(',', '.')
                    valor_considerado = request.form.get('valor_considerado', '').strip().replace('.', '').replace(',', '.')
                    valor_pago = request.form.get('valor_pago', '').strip().replace('.', '').replace(',', '.')

                    if valor_cte:
                        frete.valor_cte = float(valor_cte)
                    if valor_considerado:
                        frete.valor_considerado = float(valor_considerado)
                    if valor_pago:
                        frete.valor_pago = float(valor_pago)

                    # Sincronizar CarviaFrete → CarviaSubcontrato
                    if frete.subcontrato_id:
                        sub = CarviaSubcontrato.query.get(frete.subcontrato_id)
                        if sub:
                            if valor_cte and frete.valor_cte:
                                sub.cte_valor = frete.valor_cte
                                sub.valor_acertado = frete.valor_cte
                            if valor_considerado and frete.valor_considerado:
                                sub.valor_considerado = frete.valor_considerado

                # Campos VENDA — sempre processar
                valor_venda = request.form.get('valor_venda', '').strip().replace('.', '').replace(',', '.')
                observacoes = request.form.get('observacoes', '').strip()

                if valor_venda:
                    frete.valor_venda = float(valor_venda)
                if observacoes:
                    frete.observacoes = observacoes

                db.session.commit()
                flash('Frete atualizado com sucesso!', 'success')
                return redirect(url_for('carvia.detalhe_frete_carvia', id=frete.id))

            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao atualizar frete: {e}', 'danger')

        # Sugestoes de CTe Subcontrato (busca por NFs do frete)
        sugestoes_sub = []
        if frete.numeros_nfs:
            nfs_lista = [nf.strip() for nf in frete.numeros_nfs.split(',') if nf.strip()]
            for nf_num in nfs_lista:
                carvia_nf = CarviaNf.query.filter_by(numero_nf=nf_num, status='ATIVA').first()
                if carvia_nf:
                    from app.carvia.models import CarviaOperacaoNf
                    junctions = CarviaOperacaoNf.query.filter_by(nf_id=carvia_nf.id).all()
                    for j in junctions:
                        subs = CarviaSubcontrato.query.filter_by(
                            operacao_id=j.operacao_id,
                        ).filter(CarviaSubcontrato.id != frete.subcontrato_id).all()
                        sugestoes_sub.extend(subs)

        return render_template(
            'carvia/fretes/editar.html',
            frete=frete,
            custo_editavel=custo_editavel,
            sugestoes_sub=list({s.id: s for s in sugestoes_sub}.values()),
        )

    # ------------------------------------------------------------------
    # Lancar CTe (busca por NF)
    # ------------------------------------------------------------------

    @bp.route('/fretes/lancar-cte', methods=['GET'])  # type: ignore
    @login_required
    def lancar_cte_carvia():  # type: ignore
        """Busca CarviaFrete por NF para vincular CTe (CUSTO ou VENDA).

        Tabs: CUSTO (Subcontrato+Fatura) | VENDA (Operacao).
        Param ?tipo=venda controla tab ativa.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        # Faturas transportadora disponiveis (nao conferidas)
        faturas = CarviaFaturaTransportadora.query.filter(
            CarviaFaturaTransportadora.status_conferencia != 'CONFERIDO'
        ).order_by(
            CarviaFaturaTransportadora.id.desc()
        ).limit(50).all()

        fatura_id = request.args.get('fatura_id', type=int)
        numero_nf = request.args.get('nf', '').strip()
        tipo = request.args.get('tipo', 'custo').strip()
        fretes_encontrados = []

        if numero_nf:
            # Busca CarviaFretes que contem essa NF
            fretes_encontrados = CarviaFrete.query.filter(
                CarviaFrete.numeros_nfs.ilike(f'%{numero_nf}%')
            ).order_by(CarviaFrete.id.desc()).all()

        return render_template(
            'carvia/fretes/lancar_cte.html',
            faturas=faturas,
            fatura_id=fatura_id,
            numero_nf=numero_nf,
            tipo=tipo,
            fretes_encontrados=fretes_encontrados,
        )

    # ------------------------------------------------------------------
    # Processar CTe Subcontrato (vincula Frete+Sub a Fatura)
    # Espelho de fretes/routes.py processar_cte_frete_existente
    # ------------------------------------------------------------------

    @bp.route('/fretes/processar-cte-subcontrato', methods=['POST'])  # type: ignore
    @login_required
    def processar_cte_subcontrato():  # type: ignore
        """CRIA CarviaSubcontrato e vincula a CarviaFrete + CarviaFaturaTransportadora.

        Fluxo identico ao Nacom (processar_cte_frete_existente):
        Fatura criada sem vinculos → CTe criado dentro da Fatura vinculando fretes.
        Cadeia: FaturaTransportadora ← CarviaSubcontrato ← CarviaFrete
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        frete_id = request.form.get('frete_id', type=int)
        fatura_id = request.form.get('fatura_id', type=int)

        if not frete_id:
            flash('ID do frete nao informado.', 'danger')
            return redirect(url_for('carvia.lancar_cte_carvia'))

        if not fatura_id:
            flash('Selecione uma fatura transportadora.', 'danger')
            return redirect(url_for('carvia.lancar_cte_carvia'))

        try:
            frete = CarviaFrete.query.get_or_404(frete_id)
            fatura = CarviaFaturaTransportadora.query.get_or_404(fatura_id)

            # Validar que frete nao esta ja vinculado a outra fatura
            if frete.fatura_transportadora_id and frete.fatura_transportadora_id != fatura_id:
                fatura_atual = CarviaFaturaTransportadora.query.get(frete.fatura_transportadora_id)
                flash(
                    f'Frete #{frete.id} ja esta vinculado a fatura '
                    f'{fatura_atual.numero_fatura if fatura_atual else frete.fatura_transportadora_id}. '
                    f'Desanexe primeiro.',
                    'warning',
                )
                return redirect(url_for('carvia.lancar_cte_carvia', fatura_id=fatura_id))

            # Validar transportadora match
            if frete.transportadora_id != fatura.transportadora_id:
                from app.transportadoras.models import Transportadora
                transp_frete = Transportadora.query.get(frete.transportadora_id)
                transp_fatura = Transportadora.query.get(fatura.transportadora_id)

                if transp_frete and hasattr(transp_frete, 'pertence_mesmo_grupo') and transp_frete.pertence_mesmo_grupo(fatura.transportadora_id):
                    flash(
                        'Transportadoras diferentes mas do mesmo grupo. Vinculacao permitida.',
                        'info',
                    )
                else:
                    nome_frete = transp_frete.razao_social if transp_frete else str(frete.transportadora_id)
                    nome_fatura = transp_fatura.razao_social if transp_fatura else str(fatura.transportadora_id)
                    flash(
                        f'Transportadora da fatura ({nome_fatura}) e diferente da transportadora do frete ({nome_frete}).',
                        'danger',
                    )
                    return redirect(url_for('carvia.lancar_cte_carvia', fatura_id=fatura_id))

            # Validar que fatura nao esta conferida
            if fatura.status_conferencia == 'CONFERIDO':
                flash('Fatura ja conferida. Nao e possivel vincular novos CTes.', 'danger')
                return redirect(url_for('carvia.lancar_cte_carvia', fatura_id=fatura_id))

            # === CRIAR CarviaSubcontrato (se nao existe) ===
            from app.utils.timezone import agora_utc_naive
            from decimal import Decimal

            if frete.subcontrato_id:
                # Subcontrato ja existe (criado anteriormente) — reusar
                sub = CarviaSubcontrato.query.get(frete.subcontrato_id)
                if not sub:
                    flash('Subcontrato vinculado nao encontrado.', 'danger')
                    return redirect(url_for('carvia.lancar_cte_carvia', fatura_id=fatura_id))
            else:
                # CRIAR novo CarviaSubcontrato
                sub = CarviaSubcontrato(
                    operacao_id=frete.operacao_id,  # pode ser NULL
                    transportadora_id=frete.transportadora_id,
                    cte_numero=CarviaSubcontrato.gerar_numero_sub(),
                    valor_cotado=Decimal(str(frete.valor_cotado)) if frete.valor_cotado else None,
                    fatura_transportadora_id=fatura.id,
                    status='FATURADO',
                    criado_por=current_user.email,
                    criado_em=agora_utc_naive(),
                    observacoes=f'Criado via Lancar CTe — frete #{frete.id}',
                )
                db.session.add(sub)
                db.session.flush()  # sub.id disponivel

                # Vincular subcontrato ao frete
                frete.subcontrato_id = sub.id

            # === VINCULAR ===
            # 1. Subcontrato → Fatura (se ainda nao vinculado)
            if not sub.fatura_transportadora_id:
                sub.fatura_transportadora_id = fatura.id
                sub.status = 'FATURADO'

            # 2. CarviaFrete → Fatura
            frete.fatura_transportadora_id = fatura.id

            # 3. Auto-preencher valor_cte com valor do subcontrato
            if sub.valor_final and not frete.valor_cte:
                frete.valor_cte = float(sub.valor_final)

            db.session.flush()

            # 4. Gerar itens de detalhe da fatura
            from app.carvia.services.linking_service import LinkingService
            linker = LinkingService()
            linker.criar_itens_fatura_transportadora_incremental(fatura.id, [sub.id])

            db.session.commit()

            flash(
                f'CTe {sub.cte_numero} vinculado a fatura {fatura.numero_fatura}. '
                f'Preencha os dados do CTe.',
                'success',
            )
            return redirect(url_for('carvia.editar_frete_carvia', id=frete.id))

        except Exception as e:
            db.session.rollback()
            logger.exception(f'Erro ao processar CTe subcontrato: {e}')
            flash(f'Erro ao processar CTe: {e}', 'danger')
            return redirect(url_for('carvia.lancar_cte_carvia', fatura_id=fatura_id))

    # ------------------------------------------------------------------
    # Processar CTe Operacao (cria CarviaOperacao e vincula ao Frete)
    # Lado VENDA — espelho do processar_cte_subcontrato (lado CUSTO)
    # ------------------------------------------------------------------

    @bp.route('/fretes/processar-cte-operacao', methods=['POST'])  # type: ignore
    @login_required
    def processar_cte_operacao():  # type: ignore
        """CRIA CarviaOperacao e vincula ao CarviaFrete (lado VENDA).

        Diferente do CUSTO, nao requer fatura — R12 diz que CTe e criado
        antes da fatura no lado VENDA. Campos derivados do frete.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        frete_id = request.form.get('frete_id', type=int)

        if not frete_id:
            flash('ID do frete nao informado.', 'danger')
            return redirect(url_for('carvia.lancar_cte_carvia', tipo='venda'))

        try:
            frete = CarviaFrete.query.get_or_404(frete_id)

            # Validar que frete nao tem operacao ja vinculada
            if frete.operacao_id:
                op_existente = CarviaOperacao.query.get(frete.operacao_id)
                flash(
                    f'Frete #{frete.id} ja possui CTe CarVia vinculado '
                    f'({op_existente.cte_numero if op_existente else frete.operacao_id}).',
                    'warning',
                )
                return redirect(url_for('carvia.detalhe_frete_carvia', id=frete.id))

            # === CRIAR CarviaOperacao ===
            from app.utils.timezone import agora_utc_naive
            from decimal import Decimal

            op = CarviaOperacao(
                cnpj_cliente=frete.cnpj_destino,
                nome_cliente=frete.nome_destino,
                uf_destino=frete.uf_destino,
                cidade_destino=frete.cidade_destino,
                cte_numero=CarviaOperacao.gerar_numero_cte(),
                cte_valor=Decimal(str(frete.valor_venda)) if frete.valor_venda else None,
                tipo_entrada='MANUAL_SEM_CTE',
                status='RASCUNHO',
                peso_bruto=frete.peso_total if frete.peso_total else None,
                valor_mercadoria=frete.valor_total_nfs if frete.valor_total_nfs else None,
                criado_por=current_user.email,
                criado_em=agora_utc_naive(),
                observacoes=f'Criado via Lancar CTe CarVia — frete #{frete.id}',
            )
            db.session.add(op)
            db.session.flush()  # op.id disponivel

            # Vincular operacao ao frete
            frete.operacao_id = op.id

            # Auto-preencher valor_venda se nao preenchido
            if op.cte_valor and not frete.valor_venda:
                frete.valor_venda = float(op.cte_valor)

            # Criar junctions CarviaOperacaoNf para NFs do frete
            if frete.numeros_nfs:
                from app.carvia.models import CarviaOperacaoNf
                nfs_lista = [nf.strip() for nf in frete.numeros_nfs.split(',') if nf.strip()]
                for nf_num in nfs_lista:
                    carvia_nf = CarviaNf.query.filter_by(
                        numero_nf=nf_num, status='ATIVA'
                    ).first()
                    if carvia_nf:
                        existe = CarviaOperacaoNf.query.filter_by(
                            operacao_id=op.id, nf_id=carvia_nf.id
                        ).first()
                        if not existe:
                            junction = CarviaOperacaoNf(
                                operacao_id=op.id, nf_id=carvia_nf.id
                            )
                            db.session.add(junction)

            db.session.commit()

            flash(
                f'CTe CarVia {op.cte_numero} criado e vinculado ao frete #{frete.id}.',
                'success',
            )
            return redirect(url_for('carvia.detalhe_frete_carvia', id=frete.id))

        except Exception as e:
            db.session.rollback()
            logger.exception(f'Erro ao processar CTe operacao: {e}')
            flash(f'Erro ao processar CTe CarVia: {e}', 'danger')
            return redirect(url_for('carvia.lancar_cte_carvia', tipo='venda'))

    # ------------------------------------------------------------------
    # Vincular CTe Subcontrato ao frete
    # ------------------------------------------------------------------

    @bp.route('/fretes/<int:id>/vincular-subcontrato', methods=['POST'])  # type: ignore
    @login_required
    def vincular_subcontrato_frete(id):  # type: ignore
        """Vincula um CarviaSubcontrato ao CarviaFrete."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        frete = CarviaFrete.query.get_or_404(id)
        subcontrato_id = request.form.get('subcontrato_id', type=int)

        if not subcontrato_id:
            flash('Subcontrato nao informado.', 'danger')
            return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

        sub = CarviaSubcontrato.query.get_or_404(subcontrato_id)
        frete.subcontrato_id = sub.id

        # Atualizar valor_cte com o valor do subcontrato
        if sub.valor_final:
            frete.valor_cte = float(sub.valor_final)

        db.session.commit()
        flash(f'CTe Subcontrato {sub.cte_numero} vinculado ao frete.', 'success')
        return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

    # ------------------------------------------------------------------
    # Vincular CTe CarVia (Operacao) ao frete
    # ------------------------------------------------------------------

    @bp.route('/fretes/<int:id>/vincular-operacao', methods=['POST'])  # type: ignore
    @login_required
    def vincular_operacao_frete(id):  # type: ignore
        """Vincula uma CarviaOperacao ao CarviaFrete."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        frete = CarviaFrete.query.get_or_404(id)
        operacao_id = request.form.get('operacao_id', type=int)

        if not operacao_id:
            flash('Operacao nao informada.', 'danger')
            return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

        op = CarviaOperacao.query.get_or_404(operacao_id)
        frete.operacao_id = op.id

        # Atualizar valor_venda com o valor do CTe CarVia
        if op.cte_valor:
            frete.valor_venda = float(op.cte_valor)

        db.session.commit()
        flash(f'CTe CarVia {op.cte_numero} vinculado ao frete.', 'success')
        return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

    # ------------------------------------------------------------------
    # Desvincular CTe Subcontrato do frete (fluxo reverso CUSTO)
    # ------------------------------------------------------------------

    @bp.route('/fretes/<int:id>/desvincular-subcontrato', methods=['POST'])  # type: ignore
    @login_required
    def desvincular_subcontrato_frete(id):  # type: ignore
        """Desvincula CarviaSubcontrato + FaturaTransportadora do CarviaFrete."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        frete = CarviaFrete.query.get_or_404(id)

        if not frete.subcontrato_id:
            flash('Frete nao possui CTe Subcontrato vinculado.', 'warning')
            return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

        # Guard: fatura conferida bloqueia
        if frete.fatura_transportadora_id:
            fat = CarviaFaturaTransportadora.query.get(frete.fatura_transportadora_id)
            if fat and fat.status_conferencia == 'CONFERIDO':
                flash('Nao e possivel desvincular — fatura transportadora ja conferida.', 'danger')
                return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

        try:
            sub = CarviaSubcontrato.query.get(frete.subcontrato_id)

            # Limpar FKs no frete
            frete.subcontrato_id = None
            frete.fatura_transportadora_id = None
            frete.valor_cte = None
            frete.valor_considerado = None
            frete.valor_pago = None

            # Reverter status do subcontrato
            if sub:
                sub.fatura_transportadora_id = None
                sub.status = 'PENDENTE'

            db.session.commit()
            logger.info(
                'CTe Subcontrato desvinculado do frete #%d por %s',
                id, current_user.email,
            )
            flash('CTe Subcontrato desvinculado com sucesso.', 'success')

        except Exception as e:
            db.session.rollback()
            logger.exception(f'Erro ao desvincular subcontrato do frete #{id}: {e}')
            flash(f'Erro ao desvincular: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

    # ------------------------------------------------------------------
    # Desvincular CTe CarVia (Operacao) do frete (fluxo reverso VENDA)
    # ------------------------------------------------------------------

    @bp.route('/fretes/<int:id>/desvincular-operacao', methods=['POST'])  # type: ignore
    @login_required
    def desvincular_operacao_frete(id):  # type: ignore
        """Desvincula CarviaOperacao do CarviaFrete."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        frete = CarviaFrete.query.get_or_404(id)

        if not frete.operacao_id:
            flash('Frete nao possui CTe CarVia vinculado.', 'warning')
            return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

        # Guard: fatura cliente impede
        if frete.fatura_cliente_id:
            flash('Nao e possivel desvincular — frete vinculado a fatura cliente.', 'danger')
            return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

        try:
            frete.operacao_id = None

            db.session.commit()
            logger.info(
                'CTe CarVia desvinculado do frete #%d por %s',
                id, current_user.email,
            )
            flash('CTe CarVia desvinculado com sucesso.', 'success')

        except Exception as e:
            db.session.rollback()
            logger.exception(f'Erro ao desvincular operacao do frete #{id}: {e}')
            flash(f'Erro ao desvincular: {e}', 'danger')

        return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

    # ------------------------------------------------------------------
    # Cancelar frete
    # ------------------------------------------------------------------

    @bp.route('/fretes/<int:id>/cancelar', methods=['POST'])  # type: ignore
    @login_required
    def cancelar_frete_carvia(id):  # type: ignore
        """Cancela um CarviaFrete."""
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        frete = CarviaFrete.query.get_or_404(id)

        if frete.fatura_cliente_id or frete.fatura_transportadora_id:
            flash('Nao e possivel cancelar frete vinculado a fatura.', 'danger')
            return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

        frete.status = 'CANCELADO'
        db.session.commit()
        flash('Frete cancelado.', 'warning')
        return redirect(url_for('carvia.detalhe_frete_carvia', id=id))

    # ------------------------------------------------------------------
    # API: Buscar CTes por NF (AJAX)
    # ------------------------------------------------------------------

    @bp.route('/api/fretes/buscar-ctes', methods=['POST'])  # type: ignore
    @login_required
    def api_buscar_ctes_frete():  # type: ignore
        """Busca CTes Subcontrato/CarVia por numero NF (AJAX)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json() or {}
        numero_nf = data.get('numero_nf', '').strip()
        tipo = data.get('tipo', 'subcontrato')  # subcontrato | operacao

        if not numero_nf:
            return jsonify({'resultados': []})

        # Busca CarviaNf pela NF
        carvia_nf = CarviaNf.query.filter_by(numero_nf=numero_nf, status='ATIVA').first()
        if not carvia_nf:
            return jsonify({'resultados': [], 'mensagem': f'NF {numero_nf} nao encontrada'})

        resultados = []
        from app.carvia.models import CarviaOperacaoNf

        # Busca operacoes vinculadas a esta NF
        junctions = CarviaOperacaoNf.query.filter_by(nf_id=carvia_nf.id).all()

        for j in junctions:
            if tipo == 'subcontrato':
                subs = CarviaSubcontrato.query.filter_by(operacao_id=j.operacao_id).all()
                for sub in subs:
                    resultados.append({
                        'id': sub.id,
                        'tipo': 'subcontrato',
                        'cte_numero': sub.cte_numero,
                        'transportadora': sub.transportadora.razao_social if sub.transportadora else '',
                        'valor': float(sub.valor_final) if sub.valor_final else 0,
                        'status': sub.status,
                    })
            else:
                op = CarviaOperacao.query.get(j.operacao_id)
                if op:
                    resultados.append({
                        'id': op.id,
                        'tipo': 'operacao',
                        'cte_numero': op.cte_numero,
                        'cliente': op.nome_cliente or '',
                        'valor': float(op.cte_valor) if op.cte_valor else 0,
                        'status': op.status,
                    })

        return jsonify({'resultados': resultados})
