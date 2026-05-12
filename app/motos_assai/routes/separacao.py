from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import (
    get_separacao_ativa, saldo_pendente_por_modelo,
    registrar_chassi, desfazer_chassi, finalizar_separacao, cancelar_separacao,
    listar_pares_separaveis,
    SeparacaoConflictError, SeparacaoValidationError,
    # Realocacao de saldo (Tasks #11/#12/#13)
    analisar_finalizacao, finalizar_separacao_com_decisao,
    SeparacaoSaldoPendenteError,
    FINALIZAR_MODO_AUTO, FINALIZAR_MODO_VOLTAR_SALDO,
    FINALIZAR_MODO_MANTER_PLANEJADO, FINALIZAR_MODO_REALOCAR,
)
from app.motos_assai.models import (
    AssaiSeparacao, AssaiSeparacaoItem, AssaiPedidoVenda, AssaiLoja,
    AssaiSeparacaoSaldoModelo, AssaiModelo,
    SEPARACAO_STATUS_EM_SEPARACAO,
)


@motos_assai_bp.route('/separacao')
@login_required
@require_motos_assai
def separacao_lista():
    seps = (
        AssaiSeparacao.query
        .order_by(AssaiSeparacao.iniciada_em.desc())
        .limit(250).all()
    )
    return render_template('motos_assai/separacao/lista.html', separacoes=seps)


@motos_assai_bp.route('/separacao/nova')
@login_required
@require_motos_assai
def separacao_nova():
    """Tela com pares (pedido, loja) com saldo pendente para iniciar separacao.

    Cada par tem botao "Iniciar separacao" que abre a tela operacional
    (/pedidos/<pid>/separar/<lid>) - se ja houver separacao ativa, abre ela.
    """
    pares = listar_pares_separaveis()
    return render_template('motos_assai/separacao/nova.html', pares=pares)


@motos_assai_bp.route('/pedidos/<int:pedido_id>/separar/<int:loja_id>')
@login_required
@require_motos_assai
def separacao_tela(pedido_id, loja_id):
    """Tela de escaneio.

    Aceita `?sep_id=N` para selecionar uma separacao especifica (necessario
    quando ha N separacoes EM_SEPARACAO simultaneas — fluxo de 2+ veiculos).

    Sem `?sep_id`: busca a EM_SEPARACAO mais antiga do par. Se NAO houver
    nenhuma, redireciona para pedidos_detalhe com flash orientativo —
    operador deve criar via checkbox+qtd (criar_separacao_com_saldos).

    HIST 2026-05-12 (item 3 corretivo): antes esta rota chamava
    `get_ou_criar_separacao` que CRIAVA sep implicitamente quando nao havia
    nenhuma ativa. Cada navegacao gerava registro fantasma no banco. Bug
    confirmado em prod (pedido 21439695/L loja 112 com Sep 1 CANCELADA +
    Sep 2 EM_SEPARACAO vazia).
    """
    pedido = AssaiPedidoVenda.query.get_or_404(pedido_id)
    loja = AssaiLoja.query.get_or_404(loja_id)

    sep_id_param = request.args.get('sep_id', type=int)
    if sep_id_param:
        sep = AssaiSeparacao.query.filter_by(
            id=sep_id_param, pedido_id=pedido_id, loja_id=loja_id,
        ).first_or_404()
    else:
        sep = get_separacao_ativa(pedido_id, loja_id)
        if not sep:
            flash(
                f'Nenhuma separacao ativa para pedido {pedido.numero} loja '
                f'{loja.numero}. Crie via "Criar separacao com itens selecionados" '
                'no detalhe do pedido (checkbox + qtd a separar).',
                'info',
            )
            return redirect(url_for('motos_assai.pedidos_detalhe', pedido_id=pedido_id))

    saldos = saldo_pendente_por_modelo(pedido_id, loja_id)
    items = AssaiSeparacaoItem.query.filter_by(separacao_id=sep.id).all()

    # Plano planejado por modelo para ESTA separacao (AssaiSeparacaoSaldoModelo)
    planejado_rows = (
        AssaiSeparacaoSaldoModelo.query
        .filter_by(separacao_id=sep.id)
        .all()
    )
    planejado_por_modelo = {p.modelo_id: int(p.qtd_planejada) for p in planejado_rows}

    return render_template(
        'motos_assai/separacao/tela.html',
        pedido=pedido, loja=loja, separacao=sep,
        saldos=saldos, items=items,
        planejado_por_modelo=planejado_por_modelo,
    )


@motos_assai_bp.route('/separacao/registrar-chassi', methods=['POST'])
@login_required
@require_motos_assai
def separacao_registrar_chassi():
    data = request.get_json(silent=True) or {}
    # separacao_id e opcional — quando UI passa, alvo explicito (Plano 5 — N seps simultaneas).
    sep_id = data.get('separacao_id')
    try:
        result = registrar_chassi(
            pedido_id=int(data['pedido_id']),
            loja_id=int(data['loja_id']),
            chassi=data['chassi'],
            registrada_por_id=current_user.id,
            separacao_id=int(sep_id) if sep_id else None,
        )
    except SeparacaoConflictError as e:
        return jsonify({'ok': False, 'erro': str(e), 'retry': True}), 409
    except SeparacaoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400

    saldos = saldo_pendente_por_modelo(int(data['pedido_id']), int(data['loja_id']))
    return jsonify({'ok': True, **result, 'saldos': [
        {**s, 'valor_unitario': float(s['valor_unitario'])} for s in saldos
    ]})


@motos_assai_bp.route('/separacao/desfazer/<int:item_id>', methods=['POST'])
@login_required
@require_motos_assai
def separacao_desfazer(item_id):
    try:
        result = desfazer_chassi(item_id, current_user.id)
    except SeparacaoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    return jsonify({'ok': True, **result})


@motos_assai_bp.route('/separacao/<int:separacao_id>/finalizar', methods=['POST'])
@login_required
@require_motos_assai
def separacao_finalizar(separacao_id):
    """Finaliza separacao. Suporta saldo planejado nao-separado.

    Body JSON (opcional):
        {
            modo?: 'auto' | 'voltar_saldo' | 'manter_planejado' | 'realocar',
            alocacoes?: [{sep_destino_id: int|null, modelo_id: int, qtd: int}, ...],
        }

    Modos:
        - 'auto' (default): se sem saldo, finaliza direto. Se ha saldo,
          retorna 409 com plano para UI decidir (Caso A / Caso B).
        - 'voltar_saldo' (Caso A op1): qtd_planejada reduz para qtd_escaneada.
          Saldo volta a saldo_pendente_por_modelo() para nova separacao.
        - 'manter_planejado' (Caso A op2): qtd_planejada mantida; sep fica
          FECHADA com divergencia. NF Q.P.A. ajusta posteriormente.
        - 'realocar' (Caso B): usa `alocacoes` para distribuir saldo entre
          outras seps EM_SEPARACAO e/ou voltar ao pedido (sep_destino_id=null).
    """
    data = request.get_json(silent=True) or {}
    modo = data.get('modo', FINALIZAR_MODO_AUTO)
    alocacoes = data.get('alocacoes')
    saldo_version = data.get('saldo_version')  # H3 TOCTOU

    try:
        sep = finalizar_separacao_com_decisao(
            separacao_id, current_user.id,
            modo=modo, alocacoes=alocacoes,
            saldo_version=saldo_version,
        )
    except SeparacaoSaldoPendenteError as e:
        # Saldo nao-separado existe e modo='auto', OU saldo_version mismatch (TOCTOU).
        # UI precisa re-renderizar modal com plano atualizado.
        plano = e.plano
        outras = [
            {
                'id': o['id'],
                'iniciada_em': o['iniciada_em'].strftime('%d/%m %H:%M') if o['iniciada_em'] else None,
                'qtd_escaneada_total': o['qtd_escaneada_total'],
            }
            for o in plano['outras_seps']
        ]
        return jsonify({
            'ok': False,
            'requer_decisao': True,
            'cenario': plano['cenario'],
            'sep_id': plano['sep_id'],
            'saldo': plano['saldo'],
            'saldo_version': plano.get('saldo_version'),
            'modelos_info': plano['modelos_info'],
            'outras_seps': outras,
            'erro': str(e),
        }), 409
    except SeparacaoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400

    return jsonify({'ok': True, 'status': sep.status})


@motos_assai_bp.route('/separacao/<int:separacao_id>/analisar-finalizacao')
@login_required
@require_motos_assai
def separacao_analisar_finalizacao(separacao_id):
    """Retorna o cenario de finalizacao (read-only) para a UI montar modal.

    Response:
        {
            cenario: 'sem_saldo' | 'caso_a' | 'caso_b',
            sep_id: int,
            saldo: {modelo_id: qtd},
            modelos_info: [{modelo_id, codigo, nome, qtd_nao_separada}],
            outras_seps: [{id, iniciada_em, qtd_escaneada_total}],
        }
    """
    try:
        plano = analisar_finalizacao(separacao_id)
    except SeparacaoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400

    outras = [
        {
            'id': o['id'],
            'iniciada_em': o['iniciada_em'].strftime('%d/%m %H:%M') if o['iniciada_em'] else None,
            'qtd_escaneada_total': o['qtd_escaneada_total'],
        }
        for o in plano['outras_seps']
    ]
    return jsonify({
        'ok': True,
        'cenario': plano['cenario'],
        'sep_id': plano['sep_id'],
        'saldo': plano['saldo'],
        'saldo_version': plano.get('saldo_version'),
        'modelos_info': plano['modelos_info'],
        'outras_seps': outras,
    })


@motos_assai_bp.route('/separacao/<int:separacao_id>/cancelar', methods=['POST'])
@login_required
@require_motos_assai
def separacao_cancelar(separacao_id):
    data = request.get_json(silent=True) or {}
    try:
        sep = cancelar_separacao(separacao_id, data.get('motivo', ''), current_user.id)
    except SeparacaoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    return jsonify({'ok': True, 'status': sep.status})
