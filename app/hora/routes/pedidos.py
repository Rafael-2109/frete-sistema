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
    # Lojas para o modal de exportacao (filtradas pelo escopo do usuario).
    escopo = lojas_permitidas_ids()
    lojas_q = HoraLoja.query.filter_by(ativa=True)
    if escopo is not None:
        lojas_q = lojas_q.filter(HoraLoja.id.in_(escopo)) if escopo else lojas_q.filter(False)
    lojas_ativas = lojas_q.order_by(HoraLoja.nome).all()

    return render_template(
        'hora/pedidos_lista.html',
        pedidos=pedidos,
        filtro_status=status,
        resumos=resumos,
        lojas_ativas=lojas_ativas,
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
    # Filtra None: itens de pedido pre-NF (chassi pendente) tem numero_chassi=None
    # e quebram sorted() ao misturar com strings.
    chassis_pedido = {i.numero_chassi for i in pedido.itens if i.numero_chassi}
    chassis_faturados = {
        item.numero_chassi
        for nf in nfs_vinculadas
        for item in nf.itens
        if item.numero_chassi
    }
    chassis_nao_faturados = sorted(chassis_pedido - chassis_faturados)
    chassis_extra_em_nf = sorted(chassis_faturados - chassis_pedido)

    # Vinculo por chassi: {chassi: {'nf': ..., 'nf_item': ...}}
    vinculos = matching_service.vinculos_por_chassi_pedido(pedido.id)

    # Lojas ativas para o modal de editar header.
    lojas_ativas = HoraLoja.query.filter_by(ativa=True).order_by(HoraLoja.nome).all()

    # Set de chassis ja faturados em NF deste pedido — usado para desabilitar
    # o botao "excluir item" e proteger o usuario do erro 400 do backend.
    chassis_faturados_set = set(vinculos.keys()) if vinculos else set()

    pode_excluir_pedido = len(nfs_vinculadas) == 0

    return render_template(
        'hora/pedido_detalhe.html',
        pedido=pedido,
        nfs_vinculadas=nfs_vinculadas,
        chassis_nao_faturados=chassis_nao_faturados,
        chassis_extra_em_nf=chassis_extra_em_nf,
        vinculos_por_chassi=vinculos,
        lojas_ativas=lojas_ativas,
        chassis_faturados_set=chassis_faturados_set,
        pode_excluir_pedido=pode_excluir_pedido,
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

# Limites de upload em batch.
# - MAX_XLSX_BYTES: 1 MB por arquivo individual (XLSX HORA típico = 15-20 KB;
#   1 MB já cobre o caso 50x do normal e evita arquivo errado estourar o batch).
# - MAX_BATCH_FILES: 1000 arquivos por upload (operacional para grandes lotes).
# - MAX_BATCH_BYTES: 50 MB combinado de XLSX bruto (com 20 KB médio = 2500 arquivos
#   teóricos; cap em 1000 unidades). Token base64 fica em ~67 MB.
# - MAX_CONTENT_LENGTH ajustado para 128 MB no boot do app HORA (cobre token
#   base64 + overhead do POST). Default global era 32 MB.
MAX_XLSX_BYTES = 1 * 1024 * 1024
MAX_BATCH_FILES = 1000
MAX_BATCH_BYTES = 50 * 1024 * 1024


def _serializar_extracao_dict(
    pedido_extraido,
    xlsx_bytes: bytes | None = None,
    xlsx_nome_original: str | None = None,
) -> dict:
    """Converte um PedidoExtraido + bytes do XLSX em dict serializável."""
    return {
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
        'xlsx_bytes_b64': (
            base64.b64encode(xlsx_bytes).decode('ascii') if xlsx_bytes else None
        ),
        'xlsx_nome_original': xlsx_nome_original,
    }


def _deserializar_extracao_dict(d: dict):
    """Reconstroi (PedidoExtraido, xlsx_bytes|None, xlsx_nome|None) a partir do dict."""
    from app.hora.services.parsers import PedidoExtraido, ItemPedidoExtraido

    itens = [
        ItemPedidoExtraido(
            numero_chassi=i['numero_chassi'],
            modelo=i['modelo'],
            cor=i['cor'],
            preco_compra_esperado=Decimal(i['preco_compra_esperado']) if i['preco_compra_esperado'] else None,
            linha_origem=i['linha_origem'],
            aviso=i.get('aviso'),
        )
        for i in d['itens']
    ]
    extraido = PedidoExtraido(
        numero_pedido=d['numero_pedido'],
        cnpj_destino=d['cnpj_destino'],
        cnpjs_candidatos=d.get('cnpjs_candidatos', []),
        apelido_detectado=d.get('apelido_detectado'),
        data_pedido=date.fromisoformat(d['data_pedido']) if d['data_pedido'] else None,
        cliente_nome=d['cliente_nome'],
        cidade=d['cidade'],
        uf=d['uf'],
        header_row=d['header_row'],
        avisos=d['avisos'],
        itens=itens,
    )
    xlsx_b64 = d.get('xlsx_bytes_b64')
    xlsx_bytes = base64.b64decode(xlsx_b64) if xlsx_b64 else None
    xlsx_nome = d.get('xlsx_nome_original')
    return extraido, xlsx_bytes, xlsx_nome


def _serializar_extracoes(extracoes_dicts: list[dict]) -> str:
    """Serializa lista de extracoes (cada item = dict do _serializar_extracao_dict)."""
    payload = {'pedidos': extracoes_dicts}
    return base64.b64encode(json.dumps(payload).encode('utf-8')).decode('ascii')


def _deserializar_extracoes(token: str) -> list[dict]:
    """Retorna a lista bruta de dicts de extracoes do token."""
    payload = json.loads(base64.b64decode(token).decode('utf-8'))
    return payload.get('pedidos', [])


@hora_bp.route('/pedidos/importar-xlsx', methods=['GET', 'POST'])
@require_hora_perm('pedidos', 'criar')
def pedidos_importar_xlsx():
    """Upload de N XLSX → parseia cada um → mostra preview consolidado."""
    if request.method == 'GET':
        return render_template('hora/pedido_importar.html')

    arquivos = [a for a in request.files.getlist('xlsx') if a and a.filename]
    if not arquivos:
        flash('Selecione pelo menos um arquivo XLSX.', 'danger')
        return render_template('hora/pedido_importar.html')

    if len(arquivos) > MAX_BATCH_FILES:
        flash(
            f'Muitos arquivos ({len(arquivos)}; max {MAX_BATCH_FILES}). '
            f'Divida em uploads menores.',
            'danger',
        )
        return render_template('hora/pedido_importar.html')

    # 1ª passada: ler bytes e validar limite combinado.
    arquivos_bytes: list[tuple[str, bytes]] = []
    total_bytes = 0
    for arq in arquivos:
        conteudo = arq.read()
        if len(conteudo) > MAX_XLSX_BYTES:
            flash(
                f'Arquivo "{arq.filename}" muito grande ({len(conteudo) // 1024} KB; '
                f'max {MAX_XLSX_BYTES // 1024} KB).',
                'danger',
            )
            return render_template('hora/pedido_importar.html')
        total_bytes += len(conteudo)
        arquivos_bytes.append((arq.filename, conteudo))

    if total_bytes > MAX_BATCH_BYTES:
        flash(
            f'Tamanho combinado excedido ({total_bytes // 1024} KB; '
            f'max {MAX_BATCH_BYTES // 1024} KB). Divida em uploads menores.',
            'danger',
        )
        return render_template('hora/pedido_importar.html')

    lojas_ativas = HoraLoja.query.filter_by(ativa=True).order_by(HoraLoja.nome).all()

    # 2ª passada: parsear cada arquivo. Sucesso/falha individual: erros não
    # bloqueiam outros arquivos válidos.
    cards = []  # cada card vai para o template de preview
    extracoes_para_token: list[dict] = []
    numeros_vistos: dict[str, int] = {}  # detecta duplicatas dentro do batch

    for filename, conteudo in arquivos_bytes:
        card = {
            'nome_arquivo': filename,
            'tamanho_kb': len(conteudo) // 1024,
            'parse_ok': False,
            'cnpj_matriz_ok': False,
            'extracao': None,
            'loja_sugerida_id': None,
            'msg_lookup': None,
            'erro': None,
            'aviso_duplicado_batch': False,
            'token_index': None,  # index na lista do token (None se descartado)
        }

        try:
            extracao = parse_pedido_xlsx(conteudo, nome_arquivo=filename)
        except PedidoParseError as exc:
            card['erro'] = f'Erro ao parsear: {exc}'
            cards.append(card)
            continue

        card['parse_ok'] = True
        card['extracao'] = extracao

        # Triagem: CNPJ matriz HORA presente no cabeçalho?
        if not cnpj_matriz_presente(extracao.cnpjs_candidatos):
            cnpjs_encontrados = (
                ', '.join(extracao.cnpjs_candidatos)
                if extracao.cnpjs_candidatos else 'nenhum'
            )
            card['erro'] = (
                f'CNPJ da matriz ({CNPJ_MATRIZ_HORA}) não está no cabeçalho. '
                f'CNPJs encontrados: {cnpjs_encontrados}.'
            )
            cards.append(card)
            continue
        card['cnpj_matriz_ok'] = True

        # Resolução de loja por apelido (mesma lógica do upload single).
        loja_sugerida_id, msg_lookup = resolver_loja_por_apelido(extracao.apelido_detectado)
        card['loja_sugerida_id'] = loja_sugerida_id
        card['msg_lookup'] = msg_lookup

        # Detecta duplicado dentro do mesmo batch.
        numero = extracao.numero_pedido
        if numero in numeros_vistos:
            card['aviso_duplicado_batch'] = True

        # Adiciona ao token (mesmo se duplicado — usuário decide se inclui).
        card['token_index'] = len(extracoes_para_token)
        extracoes_para_token.append(
            _serializar_extracao_dict(
                extracao, xlsx_bytes=conteudo, xlsx_nome_original=filename,
            )
        )
        numeros_vistos[numero] = numeros_vistos.get(numero, 0) + 1

        cards.append(card)

    # Separa elegíveis (entram no batch) de descartados (XLSX que não é HORA
    # ou falhou no parse). Descartados vão para uma lista simplificada — o
    # caso típico é subir 1000 XLSX e ter 900 de outros clientes.
    cards_elegiveis = [c for c in cards if c['token_index'] is not None]
    cards_descartados = [c for c in cards if c['token_index'] is None]

    if not cards_elegiveis:
        flash(
            'Nenhum arquivo elegível para importação. Veja os erros e tente novamente.',
            'danger',
        )
        return render_template('hora/pedido_importar.html')

    token = _serializar_extracoes(extracoes_para_token)
    return render_template(
        'hora/pedido_importar_preview.html',
        cards_elegiveis=cards_elegiveis,
        cards_descartados=cards_descartados,
        token=token,
        lojas_ativas=lojas_ativas,
        total_arquivos=len(cards),
        total_elegiveis=len(cards_elegiveis),
        numeros_vistos=numeros_vistos,
    )


@hora_bp.route('/pedidos/importar-xlsx/confirmar', methods=['POST'])
@require_hora_perm('pedidos', 'criar')
def pedidos_importar_xlsx_confirmar():
    """Confirma a importação em batch: cria N HoraPedido a partir do token.

    Cada pedido tem sua própria transação — falha em um não bloqueia os outros.
    """
    token = request.form.get('token')
    if not token:
        flash('Token de extração ausente.', 'danger')
        return redirect(url_for('hora.pedidos_importar_xlsx'))

    try:
        extracoes_dicts = _deserializar_extracoes(token)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        flash(f'Token inválido: {exc}', 'danger')
        return redirect(url_for('hora.pedidos_importar_xlsx'))

    # IDs dos pedidos a criar (checkbox marcado) e loja por pedido.
    incluir_indices_raw = request.form.getlist('incluir_idx[]')
    incluir_indices = {int(i) for i in incluir_indices_raw if i.isdigit()}

    if not incluir_indices:
        flash('Nenhum pedido selecionado para importação.', 'warning')
        return redirect(url_for('hora.pedidos_importar_xlsx'))

    sucessos: list[str] = []
    erros: list[str] = []
    primeiro_pedido_id = None

    for idx, d in enumerate(extracoes_dicts):
        if idx not in incluir_indices:
            continue

        loja_str = (request.form.get(f'loja_destino_id_{idx}') or '').strip()
        nome_arq = d.get('xlsx_nome_original') or f'arquivo_{idx + 1}'
        numero = d.get('numero_pedido') or f'(sem número, idx {idx})'

        if not loja_str.isdigit():
            erros.append(f'{nome_arq}: loja destino não selecionada.')
            continue

        try:
            extracao, xlsx_bytes, xlsx_nome = _deserializar_extracao_dict(d)

            # Persiste XLSX original no storage. Falha não aborta a criação.
            arquivo_origem_s3_key = None
            if xlsx_bytes:
                try:
                    import io as _io
                    buf = _io.BytesIO(xlsx_bytes)
                    buf.name = xlsx_nome or f'pedido_{extracao.numero_pedido}.xlsx'
                    from app.utils.file_storage import FileStorage
                    arquivo_origem_s3_key = FileStorage().save_file(
                        buf, folder='hora/pedidos',
                        filename=f'{extracao.numero_pedido}.xlsx',
                        allowed_extensions=['xlsx', 'xls'],
                    )
                except Exception as exc:
                    from flask import current_app as _app
                    _app.logger.warning(
                        f'hora: falha ao persistir XLSX do pedido '
                        f'{extracao.numero_pedido}: {exc}'
                    )

            pedido = pedido_service.criar_pedido_a_partir_de_extracao(
                pedido_extraido=extracao,
                loja_destino_id=int(loja_str),
                arquivo_origem_s3_key=arquivo_origem_s3_key,
                criado_por=current_user.nome if hasattr(current_user, 'nome') else None,
            )
            sucessos.append(
                f'{pedido.numero_pedido} ({len(pedido.itens)} itens, {pedido.loja_destino.rotulo_display})'
            )
            if primeiro_pedido_id is None:
                primeiro_pedido_id = pedido.id
        except ValueError as exc:
            erros.append(f'{nome_arq} (pedido {numero}): {exc}')
        except Exception as exc:  # noqa: BLE001 — mostra ao usuário ao invés de 500
            from flask import current_app as _app
            _app.logger.exception(
                f'hora: erro inesperado ao criar pedido a partir de {nome_arq}'
            )
            erros.append(f'{nome_arq} (pedido {numero}): erro inesperado — {exc}')

    if sucessos:
        flash(
            f'{len(sucessos)} pedido(s) criado(s): ' + ' · '.join(sucessos),
            'success',
        )
    if erros:
        flash(
            f'{len(erros)} pedido(s) com erro: ' + ' · '.join(erros),
            'danger' if not sucessos else 'warning',
        )

    # Redireciona: se único sucesso, vai pra ele; se vários, vai pra lista.
    if len(sucessos) == 1 and primeiro_pedido_id:
        return redirect(url_for('hora.pedidos_detalhe', pedido_id=primeiro_pedido_id))
    return redirect(url_for('hora.pedidos_lista'))


# ========================================================================
# Download XLSX de origem
# ========================================================================

@hora_bp.route('/pedidos/<int:pedido_id>/download-xlsx')
@require_hora_perm('pedidos', 'ver')
def pedidos_download_xlsx(pedido_id: int):
    """Redireciona para URL (S3 presigned ou local) do XLSX original do pedido."""
    pedido = HoraPedido.query.get_or_404(pedido_id)
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        flash('Acesso negado: pedido de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.pedidos_lista'))
    if not pedido.arquivo_origem_s3_key:
        flash(
            'XLSX deste pedido nao esta armazenado (pedido manual ou import anterior a esta feature).',
            'warning',
        )
        return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido.id))

    from app.utils.file_storage import FileStorage
    url = FileStorage().get_file_url(pedido.arquivo_origem_s3_key)
    if not url:
        flash('Falha ao gerar URL do XLSX.', 'danger')
        return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido.id))
    return redirect(url)


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
# Exportacao Excel: pedidos com itens + vinculo NF
# ========================================================================

@hora_bp.route('/pedidos/exportar')
@require_hora_perm('pedidos', 'ver')
def pedidos_exportar():
    """Exporta pedidos para XLSX. Filtros: data_inicio, data_fim, loja_id."""
    from datetime import timedelta
    from flask import send_file
    import io as _io

    data_ini_str = (request.args.get('data_inicio') or '').strip()
    data_fim_str = (request.args.get('data_fim') or '').strip()
    loja_str = (request.args.get('loja_id') or '').strip()

    # Default: ultimos 30 dias.
    try:
        data_inicio = datetime.strptime(data_ini_str, '%Y-%m-%d').date() if data_ini_str else (date.today() - timedelta(days=30))
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date() if data_fim_str else date.today()
    except ValueError:
        flash('Data invalida (use formato YYYY-MM-DD).', 'danger')
        return redirect(url_for('hora.pedidos_lista'))

    # Restringe ao escopo de lojas do usuario.
    escopo = lojas_permitidas_ids()
    if loja_str.isdigit():
        loja_id = int(loja_str)
        if escopo is not None and loja_id not in escopo:
            flash('Acesso negado: loja fora do seu escopo.', 'danger')
            return redirect(url_for('hora.pedidos_lista'))
        lojas_filtro = [loja_id]
    else:
        lojas_filtro = list(escopo) if escopo is not None else None

    xlsx_bytes = pedido_service.exportar_pedidos_excel(
        data_inicio=data_inicio,
        data_fim=data_fim,
        lojas_ids=lojas_filtro,
    )

    filename = f'pedidos_hora_{data_inicio.isoformat()}_a_{data_fim.isoformat()}.xlsx'
    return send_file(
        _io.BytesIO(xlsx_bytes),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename,
    )


# ========================================================================
# CRUD do header e itens (apenas pedidos sem NF vinculada)
# ========================================================================

@hora_bp.route('/pedidos/<int:pedido_id>/excluir', methods=['POST'])
@require_hora_perm('pedidos', 'apagar')
def pedidos_excluir(pedido_id: int):
    """Exclui pedido (e itens via cascade). Bloqueado se ha NF vinculada."""
    pedido = HoraPedido.query.get_or_404(pedido_id)
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        flash('Acesso negado: pedido de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.pedidos_lista'))

    try:
        numero = pedido_service.excluir_pedido(
            pedido_id,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        flash(f'Pedido {numero} excluido.', 'success')
        return redirect(url_for('hora.pedidos_lista'))
    except ValueError as exc:
        flash(f'Erro ao excluir: {exc}', 'danger')
        return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido_id))


@hora_bp.route('/pedidos/<int:pedido_id>/editar', methods=['POST'])
@require_hora_perm('pedidos', 'editar')
def pedidos_editar_header(pedido_id: int):
    """Edita header do pedido: data, loja_destino, observacoes."""
    pedido = HoraPedido.query.get_or_404(pedido_id)
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        flash('Acesso negado: pedido de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.pedidos_lista'))

    data_str = (request.form.get('data_pedido') or '').strip()
    loja_str = (request.form.get('loja_destino_id') or '').strip()
    observacoes = request.form.get('observacoes', '').strip()

    try:
        data_pedido = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else None
        loja_destino_id = int(loja_str) if loja_str.isdigit() else None

        pedido_service.editar_pedido_header(
            pedido_id=pedido_id,
            data_pedido=data_pedido,
            loja_destino_id=loja_destino_id,
            observacoes=observacoes,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        flash('Pedido atualizado.', 'success')
    except (ValueError, KeyError) as exc:
        flash(f'Erro ao editar: {exc}', 'danger')

    return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido_id))


@hora_bp.route('/pedidos/<int:pedido_id>/itens/novo', methods=['POST'])
@require_hora_perm('pedidos', 'editar')
def pedidos_adicionar_item(pedido_id: int):
    """Adiciona novo item (chassi/moto) a pedido existente."""
    pedido = HoraPedido.query.get_or_404(pedido_id)
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        flash('Acesso negado: pedido de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.pedidos_lista'))

    numero_chassi = (request.form.get('numero_chassi') or '').strip() or None
    modelo_nome = (request.form.get('modelo_nome') or '').strip() or None
    cor = (request.form.get('cor') or '').strip() or None
    preco_str = (request.form.get('preco_compra_esperado') or '').strip().replace(',', '.')

    try:
        if not preco_str:
            raise ValueError('Preco obrigatorio')
        preco = Decimal(preco_str)
        pedido_service.adicionar_item_pedido(
            pedido_id=pedido_id,
            numero_chassi=numero_chassi,
            modelo_nome=modelo_nome,
            cor=cor,
            preco_compra_esperado=preco,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        flash('Item adicionado.', 'success')
    except (ValueError, InvalidOperation) as exc:
        flash(f'Erro ao adicionar item: {exc}', 'danger')

    return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido_id))


@hora_bp.route('/pedidos/<int:pedido_id>/itens/<int:item_id>/excluir', methods=['POST'])
@require_hora_perm('pedidos', 'editar')
def pedidos_excluir_item(pedido_id: int, item_id: int):
    """Remove item do pedido. Bloqueado se chassi ja foi faturado em NF."""
    pedido = HoraPedido.query.get_or_404(pedido_id)
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        flash('Acesso negado: pedido de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.pedidos_lista'))

    try:
        pedido_service.excluir_item_pedido(
            pedido_id=pedido_id,
            item_id=item_id,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        flash('Item removido.', 'success')
    except ValueError as exc:
        flash(f'Erro ao remover item: {exc}', 'danger')

    return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido_id))


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
