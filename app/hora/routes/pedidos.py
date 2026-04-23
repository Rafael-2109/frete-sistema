"""Rotas de pedidos HORA→Motochefe."""
from __future__ import annotations

import base64
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from app.hora.decorators import require_hora_perm

from app.hora.models import HoraLoja, HoraPedido, HoraNfEntrada
from app.hora.routes import hora_bp
from app.hora.services import matching_service, pedido_service
from app.hora.services.auth_helper import lojas_permitidas_ids, usuario_tem_acesso_a_loja
from app.hora.services.parsers import (
    CNPJ_MATRIZ_HORA,
    cnpj_matriz_presente,
    parse_pedido_xlsx,
    resolver_loja_por_apelido,
    PedidoParseError,
)


@hora_bp.route('/pedidos')
@require_hora_perm('pedidos', 'ver')
def pedidos_lista():
    status = request.args.get('status') or None
    pedidos = pedido_service.listar_pedidos(
        status=status,
        limit=200,
        lojas_permitidas_ids=lojas_permitidas_ids(),
    )
    # Bulk load para evitar N+1 (uma query agregada em vez de N por pedido).
    pedido_ids = [p.id for p in pedidos]
    fat_batch = matching_service.chassis_faturados_por_pedido_batch(pedido_ids)
    resumos = {
        p.id: matching_service.resumo_faturamento_pedido(p, fat_batch)
        for p in pedidos
    }
    return render_template(
        'hora/pedidos_lista.html',
        pedidos=pedidos,
        filtro_status=status,
        resumos=resumos,
    )


@hora_bp.route('/pedidos/<int:pedido_id>')
@require_hora_perm('pedidos', 'ver')
def pedidos_detalhe(pedido_id: int):
    pedido = HoraPedido.query.get_or_404(pedido_id)
    # Autorização por loja_destino
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        flash('Acesso negado: pedido de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.pedidos_lista'))
    nfs_vinculadas = HoraNfEntrada.query.filter_by(pedido_id=pedido.id).all()
    chassis_pedido = {i.numero_chassi for i in pedido.itens}
    chassis_faturados = {
        item.numero_chassi
        for nf in nfs_vinculadas
        for item in nf.itens
    }
    chassis_nao_faturados = sorted(chassis_pedido - chassis_faturados)
    chassis_extra_em_nf = sorted(chassis_faturados - chassis_pedido)

    # Vinculo por chassi: {chassi: {'nf': ..., 'nf_item': ...}}
    vinculos = matching_service.vinculos_por_chassi_pedido(pedido.id)

    return render_template(
        'hora/pedido_detalhe.html',
        pedido=pedido,
        nfs_vinculadas=nfs_vinculadas,
        chassis_nao_faturados=chassis_nao_faturados,
        chassis_extra_em_nf=chassis_extra_em_nf,
        vinculos_por_chassi=vinculos,
    )


@hora_bp.route('/pedidos/novo', methods=['GET', 'POST'])
@require_hora_perm('pedidos', 'criar')
def pedidos_novo():
    """Formulário simples manual (para P3a). Import Excel virá em P3b."""
    if request.method == 'POST':
        try:
            numero_pedido = request.form['numero_pedido'].strip()
            cnpj_destino = request.form['cnpj_destino'].strip()
            data_pedido_str = request.form['data_pedido']
            data_pedido = datetime.strptime(data_pedido_str, '%Y-%m-%d').date()

            # Lê itens dinâmicos: chassis[], precos[]
            chassis = request.form.getlist('chassis[]')
            modelos = request.form.getlist('modelos[]')
            cores = request.form.getlist('cores[]')
            precos = request.form.getlist('precos[]')

            if not chassis:
                raise ValueError('Pedido precisa de pelo menos um item')

            itens = []
            for i, chassi in enumerate(chassis):
                chassi = chassi.strip()
                if not chassi:
                    continue
                try:
                    preco = Decimal(precos[i].replace(',', '.'))
                except (InvalidOperation, IndexError, ValueError):
                    raise ValueError(f'Preço inválido para item {i+1}')
                itens.append({
                    'numero_chassi': chassi,
                    'modelo': (modelos[i] if i < len(modelos) else '').strip() or None,
                    'cor': (cores[i] if i < len(cores) else '').strip() or None,
                    'preco_compra_esperado': preco,
                })

            pedido = pedido_service.criar_pedido(
                numero_pedido=numero_pedido,
                cnpj_destino=cnpj_destino,
                data_pedido=data_pedido,
                itens=itens,
                criado_por=current_user.nome if hasattr(current_user, 'nome') else None,
            )
            flash(f'Pedido {pedido.numero_pedido} criado com {len(itens)} item(ns).', 'success')
            return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido.id))
        except (ValueError, KeyError) as exc:
            flash(f'Erro ao criar pedido: {exc}', 'danger')

    return render_template('hora/pedido_novo.html', hoje=date.today().isoformat())


# ----------------------------- Importação XLSX -----------------------------

def _serializar_extracao(pedido_extraido) -> str:
    """Serializa PedidoExtraido em JSON + base64 para round-trip no form."""
    payload = {
        'numero_pedido': pedido_extraido.numero_pedido,
        'cnpj_destino': pedido_extraido.cnpj_destino,
        'cnpjs_candidatos': pedido_extraido.cnpjs_candidatos,
        'apelido_detectado': pedido_extraido.apelido_detectado,
        'data_pedido': pedido_extraido.data_pedido.isoformat() if pedido_extraido.data_pedido else None,
        'cliente_nome': pedido_extraido.cliente_nome,
        'cidade': pedido_extraido.cidade,
        'uf': pedido_extraido.uf,
        'header_row': pedido_extraido.header_row,
        'avisos': pedido_extraido.avisos,
        'itens': [
            {
                'numero_chassi': i.numero_chassi,
                'modelo': i.modelo,
                'cor': i.cor,
                'preco_compra_esperado': str(i.preco_compra_esperado) if i.preco_compra_esperado is not None else None,
                'linha_origem': i.linha_origem,
                'aviso': i.aviso,
            }
            for i in pedido_extraido.itens
        ],
    }
    return base64.b64encode(json.dumps(payload).encode('utf-8')).decode('ascii')


def _deserializar_extracao(token: str):
    """Reconstroi PedidoExtraido a partir do JSON+base64."""
    from app.hora.services.parsers import PedidoExtraido, ItemPedidoExtraido

    payload = json.loads(base64.b64decode(token).decode('utf-8'))
    itens = [
        ItemPedidoExtraido(
            numero_chassi=d['numero_chassi'],
            modelo=d['modelo'],
            cor=d['cor'],
            preco_compra_esperado=Decimal(d['preco_compra_esperado']) if d['preco_compra_esperado'] else None,
            linha_origem=d['linha_origem'],
            aviso=d.get('aviso'),
        )
        for d in payload['itens']
    ]
    return PedidoExtraido(
        numero_pedido=payload['numero_pedido'],
        cnpj_destino=payload['cnpj_destino'],
        cnpjs_candidatos=payload.get('cnpjs_candidatos', []),
        apelido_detectado=payload.get('apelido_detectado'),
        data_pedido=date.fromisoformat(payload['data_pedido']) if payload['data_pedido'] else None,
        cliente_nome=payload['cliente_nome'],
        cidade=payload['cidade'],
        uf=payload['uf'],
        header_row=payload['header_row'],
        avisos=payload['avisos'],
        itens=itens,
    )


@hora_bp.route('/pedidos/importar-xlsx', methods=['GET', 'POST'])
@require_hora_perm('pedidos', 'criar')
def pedidos_importar_xlsx():
    """Upload de XLSX → parseia → mostra preview com resolução de loja."""
    if request.method == 'GET':
        return render_template('hora/pedido_importar.html')

    arquivo = request.files.get('xlsx')
    if not arquivo or not arquivo.filename:
        flash('Selecione um arquivo XLSX.', 'danger')
        return render_template('hora/pedido_importar.html')

    try:
        conteudo = arquivo.read()
        extracao = parse_pedido_xlsx(conteudo, nome_arquivo=arquivo.filename)
    except PedidoParseError as exc:
        flash(f'Erro ao parsear: {exc}', 'danger')
        return render_template('hora/pedido_importar.html')

    # Triagem: o CNPJ da matriz HORA (Tatuapé) precisa aparecer no cabeçalho do
    # XLSX. Se não aparece, o arquivo provavelmente não é pedido HORA — evita
    # que um pedido de outro cliente seja importado por engano.
    if not cnpj_matriz_presente(extracao.cnpjs_candidatos):
        cnpjs_encontrados = (
            ', '.join(extracao.cnpjs_candidatos)
            if extracao.cnpjs_candidatos else 'nenhum'
        )
        flash(
            f'Arquivo não parece ser pedido HORA. O CNPJ da matriz '
            f'({CNPJ_MATRIZ_HORA}) não foi encontrado no cabeçalho do XLSX. '
            f'CNPJs encontrados: {cnpjs_encontrados}.',
            'danger',
        )
        return render_template('hora/pedido_importar.html')

    # Todas as NFs/pedidos HORA usam mesmo CNPJ (matriz). Resolução correta = via apelido.
    loja_sugerida_id, msg_lookup = resolver_loja_por_apelido(extracao.apelido_detectado)

    lojas_ativas = HoraLoja.query.filter_by(ativa=True).order_by(HoraLoja.nome).all()

    token = _serializar_extracao(extracao)
    return render_template(
        'hora/pedido_importar_preview.html',
        extracao=extracao,
        token=token,
        nome_arquivo=arquivo.filename,
        loja_sugerida_id=loja_sugerida_id,
        msg_lookup=msg_lookup,
        lojas_ativas=lojas_ativas,
    )


@hora_bp.route('/pedidos/importar-xlsx/confirmar', methods=['POST'])
@require_hora_perm('pedidos', 'criar')
def pedidos_importar_xlsx_confirmar():
    """Confirma a importação: cria HoraPedido a partir da extração preservada."""
    token = request.form.get('token')
    loja_destino_id_str = (request.form.get('loja_destino_id') or '').strip()

    if not token:
        flash('Token de extração ausente.', 'danger')
        return redirect(url_for('hora.pedidos_importar_xlsx'))
    if not loja_destino_id_str.isdigit():
        flash('Selecione a loja de destino.', 'danger')
        return redirect(url_for('hora.pedidos_importar_xlsx'))

    try:
        extracao = _deserializar_extracao(token)

        pedido = pedido_service.criar_pedido_a_partir_de_extracao(
            pedido_extraido=extracao,
            loja_destino_id=int(loja_destino_id_str),
            criado_por=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        flash(
            f'Pedido {pedido.numero_pedido} criado com {len(pedido.itens)} item(ns) '
            f'para {pedido.loja_destino.rotulo_display}.',
            'success',
        )
        return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido.id))
    except ValueError as exc:
        flash(f'Erro ao criar pedido: {exc}', 'danger')
        return redirect(url_for('hora.pedidos_importar_xlsx'))


# ========================================================================
# Wizard: completar chassis pendentes
# ========================================================================

@hora_bp.route('/pedidos/<int:pedido_id>/completar-chassis', methods=['GET'])
@require_hora_perm('pedidos', 'editar')
def pedidos_completar_chassis(pedido_id: int):
    """Tela-wizard: pareia item_pedido (chassi=NULL) com nf_item da mesma loja."""
    pedido = HoraPedido.query.get_or_404(pedido_id)
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        flash('Acesso negado: pedido de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.pedidos_lista'))

    if not pedido.loja_destino_id:
        flash(
            'Pedido sem loja definida. Defina a loja antes de completar chassis.',
            'warning',
        )
        return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido.id))

    pendentes = [i for i in pedido.itens if not i.numero_chassi]
    if not pendentes:
        flash('Pedido nao tem itens pendentes.', 'info')
        return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido.id))

    try:
        disponiveis = matching_service.chassis_nf_disponiveis_para_pedido(pedido.id)
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
        return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido.id))

    return render_template(
        'hora/pedido_completar_chassis.html',
        pedido=pedido,
        itens_pendentes=pendentes,
        chassis_disponiveis=disponiveis,
    )


@hora_bp.route('/pedidos/<int:pedido_id>/completar-chassis', methods=['POST'])
@require_hora_perm('pedidos', 'editar')
def pedidos_completar_chassis_aplicar(pedido_id: int):
    """Recebe pares pedido_item_id + nf_item_id e aplica em transacao."""
    pedido = HoraPedido.query.get_or_404(pedido_id)
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        flash('Acesso negado: pedido de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.pedidos_lista'))

    pedido_item_ids = request.form.getlist('pedido_item_id[]')
    nf_item_ids = request.form.getlist('nf_item_id[]')

    if len(pedido_item_ids) != len(nf_item_ids):
        flash('Quantidade de pares invalida.', 'danger')
        return redirect(url_for('hora.pedidos_completar_chassis', pedido_id=pedido.id))

    pares = []
    for pi, ni in zip(pedido_item_ids, nf_item_ids):
        pi_s = (pi or '').strip()
        ni_s = (ni or '').strip()
        if not pi_s or not ni_s:
            continue
        if not pi_s.isdigit() or not ni_s.isdigit():
            flash(f'Par invalido: {pi}, {ni}', 'danger')
            return redirect(url_for('hora.pedidos_completar_chassis', pedido_id=pedido.id))
        pares.append({'pedido_item_id': int(pi_s), 'nf_item_id': int(ni_s)})

    if not pares:
        flash('Nenhum par selecionado.', 'warning')
        return redirect(url_for('hora.pedidos_completar_chassis', pedido_id=pedido.id))

    try:
        res = matching_service.aplicar_pares_completar_chassis(
            pedido_id=pedido.id,
            pares=pares,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        flash(f'{res["total"]} chassi(s) preenchido(s).', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')

    return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido.id))


# ========================================================================
# Edicao manual de item (excecao da excecao)
# ========================================================================

@hora_bp.route(
    '/pedidos/<int:pedido_id>/itens/<int:item_id>/editar',
    methods=['POST'],
)
@require_hora_perm('pedidos', 'editar')
def pedidos_editar_item(pedido_id: int, item_id: int):
    pedido = HoraPedido.query.get_or_404(pedido_id)
    is_ajax = request.is_json or request.headers.get('Accept') == 'application/json'
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        if is_ajax:
            return jsonify({'ok': False, 'erro': 'acesso negado'}), 403
        flash('Acesso negado: pedido de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.pedidos_lista'))

    numero_chassi = (request.form.get('numero_chassi') or '').strip() or None
    modelo_nome = (request.form.get('modelo_nome') or '').strip() or None
    cor = (request.form.get('cor') or '').strip() or None
    try:
        res = matching_service.editar_pedido_item_manual(
            pedido_id=pedido.id,
            pedido_item_id=item_id,
            numero_chassi=numero_chassi,
            modelo_nome=modelo_nome,
            cor=cor,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        if is_ajax:
            return jsonify(res)
        flash('Item atualizado.', 'success')
    except ValueError as exc:
        if is_ajax:
            return jsonify({'ok': False, 'erro': str(exc)}), 400
        flash(f'Erro: {exc}', 'danger')

    return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido.id))
