"""
Rotas para Títulos A Pagar - MotoChefe
Gerencia pagamento de Movimentação e Montagem
"""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from decimal import Decimal

from app import db
from app.motochefe.routes import motochefe_bp
from app.motochefe.routes.cadastros import requer_motochefe
from app.motochefe.models.financeiro import TituloAPagar
from app.motochefe.models.cadastro import EmpresaVendaMoto
from app.motochefe.services.titulo_a_pagar_service import pagar_titulo_a_pagar, listar_titulos_a_pagar


@motochefe_bp.route('/titulos-a-pagar')
@login_required
@requer_motochefe
def listar_titulos_a_pagar_route():
    """Lista títulos a pagar com filtros e paginação"""
    status_filtro = request.args.get('status')
    tipo_filtro = request.args.get('tipo')
    page = request.args.get('page', 1, type=int)
    per_page = 100

    # Buscar títulos
    titulos = listar_titulos_a_pagar(
        status=status_filtro,
        tipo=tipo_filtro
    )

    # Agrupar por status (para totalizadores)
    pendentes = [t for t in titulos if t.status == 'PENDENTE']
    abertos = [t for t in titulos if t.status == 'ABERTO']
    parciais = [t for t in titulos if t.status == 'PARCIAL']
    pagos = [t for t in titulos if t.status == 'PAGO']

    # Totais
    total_pendente = sum((t.valor_saldo for t in pendentes), Decimal("0"))
    total_aberto = sum((t.valor_saldo for t in abertos), Decimal("0"))
    total_parcial = sum((t.valor_saldo for t in parciais), Decimal("0"))

    # Paginação manual da lista consolidada
    total_items = len(titulos)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    titulos_paginados = titulos[start_idx:end_idx]

    # Criar objeto paginacao manual
    class PaginacaoManual:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page if per_page > 0 else 0
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None

    paginacao = PaginacaoManual(titulos_paginados, page, per_page, total_items)

    # Empresas para pagamento
    empresas = EmpresaVendaMoto.query.filter_by(ativo=True).order_by(EmpresaVendaMoto.empresa).all()

    return render_template('motochefe/titulos_a_pagar/listar.html',
                         titulos=paginacao.items,
                         paginacao=paginacao,
                         total_pendente=total_pendente,
                         total_aberto=total_aberto,
                         total_parcial=total_parcial,
                         empresas=empresas,
                         status_filtro=status_filtro,
                         tipo_filtro=tipo_filtro)


@motochefe_bp.route('/titulos-a-pagar/<int:id>/detalhes')
@login_required
@requer_motochefe
def detalhes_titulo_a_pagar(id):
    """Exibe detalhes de título a pagar"""
    titulo = TituloAPagar.query.get_or_404(id)

    return render_template('motochefe/titulos_a_pagar/detalhes.html',
                         titulo=titulo)


@motochefe_bp.route('/titulos-a-pagar/<int:id>/pagar', methods=['POST'])
@login_required
@requer_motochefe
def pagar_titulo_a_pagar_route(id):
    """Paga título a pagar"""
    titulo = TituloAPagar.query.get_or_404(id)

    try:
        # Dados do form
        empresa_pagadora_id = request.form.get('empresa_pagadora_id')
        valor_pago = request.form.get('valor_pago')

        if not empresa_pagadora_id or not valor_pago:
            flash('Empresa e valor são obrigatórios', 'danger')
            return redirect(url_for('motochefe.listar_titulos_a_pagar_route'))

        empresa = EmpresaVendaMoto.query.get_or_404(empresa_pagadora_id)
        valor = Decimal(valor_pago)

        # Executar pagamento
        resultado = pagar_titulo_a_pagar(
            titulo,
            valor,
            empresa,
            current_user.nome
        )

        db.session.commit()

        if resultado['saldo_restante'] <= 0:
            flash(f'Título #{titulo.id} pago totalmente!', 'success')
        else:
            flash(f'Pagamento parcial efetuado. Saldo restante: R$ {resultado["saldo_restante"]}', 'info')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao pagar título: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_titulos_a_pagar_route'))


@motochefe_bp.route('/titulos-a-pagar/pagar-lote', methods=['POST'])
@login_required
@requer_motochefe
def pagar_lote_titulos_a_pagar():
    """Paga múltiplos títulos em lote"""
    try:
        import json
        empresa_pagadora_id = request.form.get('empresa_pagadora_id')
        itens_json = request.form.get('itens_pagamento')

        if not empresa_pagadora_id or not itens_json:
            flash('Selecione empresa e títulos', 'warning')
            return redirect(url_for('motochefe.listar_titulos_a_pagar_route'))

        empresa = EmpresaVendaMoto.query.get_or_404(empresa_pagadora_id)
        itens = json.loads(itens_json)

        contador = 0
        total_pago = Decimal('0')

        for item in itens:
            titulo_id = int(item['id'])
            valor = Decimal(item['valor'])

            titulo = TituloAPagar.query.get(titulo_id)
            if titulo and titulo.pode_pagar:
                pagar_titulo_a_pagar(
                    titulo,
                    valor,
                    empresa,
                    current_user.nome
                )
                contador += 1
                total_pago += valor

        db.session.commit()

        flash(f'{contador} títulos pagos com sucesso! Total: R$ {total_pago}', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao processar pagamentos: {str(e)}', 'danger')

    return redirect(url_for('motochefe.listar_titulos_a_pagar_route'))


@motochefe_bp.route('/titulos-a-pagar/api/validar-saldo')
@login_required
@requer_motochefe
def api_validar_saldo_titulo():
    """API: Valida se empresa tem saldo para pagar título"""
    from app.motochefe.services.empresa_service import validar_saldo

    empresa_id = request.args.get('empresa_id', type=int)
    valor = request.args.get('valor', type=float)

    if not empresa_id or not valor:
        return jsonify({'erro': 'Parâmetros inválidos'}), 400

    valido, mensagem = validar_saldo(empresa_id, Decimal(str(valor)))

    return jsonify({
        'valido': valido,
        'mensagem': mensagem
    })
