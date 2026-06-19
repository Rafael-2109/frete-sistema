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
    MIME_TYPES_ACEITOS,
    cnpj_matriz_presente,
    parse_pedido_imagem,
    parse_pedido_xlsx,
    resolver_loja_por_apelido,
    PedidoParseError,
)


@hora_bp.route('/pedidos')
@require_hora_perm('pedidos', 'ver')
def pedidos_lista():
    status = (request.args.get('status') or '').strip() or None
    numero_pedido = (request.args.get('numero_pedido') or '').strip() or None
    loja_id_str = (request.args.get('loja_id') or '').strip()
    loja_id = int(loja_id_str) if loja_id_str.isdigit() else None
    data_ini_str = (request.args.get('data_inicio') or '').strip()
    data_fim_str = (request.args.get('data_fim') or '').strip()

    try:
        data_inicio = datetime.strptime(data_ini_str, '%Y-%m-%d').date() if data_ini_str else None
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date() if data_fim_str else None
    except ValueError:
        flash('Data invalida (use formato YYYY-MM-DD).', 'warning')
        data_inicio = None
        data_fim = None

    if loja_id and not usuario_tem_acesso_a_loja(loja_id):
        flash('Acesso negado a essa loja.', 'danger')
        return redirect(url_for('hora.pedidos_lista'))

    pedidos = pedido_service.listar_pedidos(
        status=status,
        limit=200,
        lojas_permitidas_ids=lojas_permitidas_ids(),
        numero_pedido=numero_pedido,
        loja_id=loja_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
    # Bulk load para evitar N+1 (uma query agregada em vez de N por pedido).
    pedido_ids = [p.id for p in pedidos]
    fat_batch = matching_service.chassis_faturados_por_pedido_batch(pedido_ids)
    resumos = {
        p.id: matching_service.resumo_faturamento_pedido(p, fat_batch)
        for p in pedidos
    }
    # Comparativo de valores (match/sem-match por chassi) — 1 query agregada.
    comparativos_valores = matching_service.comparativos_valores_pedidos_batch(pedidos)
    # Deteccao de chassi duplicado entre pedidos ATIVOS (1 query agregada).
    # {pedido_id: count_chassis_duplicados} — pedidos sem duplicidade sao
    # omitidos. Pedidos CANCELADO nao aparecem (regra: nao alerta cancelado).
    duplicidades_chassi = pedido_service.chassis_duplicados_em_outros_pedidos_batch(pedido_ids)
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
        filtro_numero_pedido=numero_pedido,
        filtro_loja_id=loja_id,
        filtro_data_inicio=data_ini_str,
        filtro_data_fim=data_fim_str,
        resumos=resumos,
        comparativos_valores=comparativos_valores,
        duplicidades_chassi=duplicidades_chassi,
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

    # Comparativo de valores (match/sem-match por chassi).
    comparativo_valores = matching_service.comparativo_valores_pedido(pedido)

    # Pedidos candidatos para mover item (mesma loja, qualquer status exceto
    # CANCELADO, excluindo o pedido atual). FATURADO entra porque o caso
    # comum e absorver chassi extra de NF (NF=11 motos, pedido=10 fechados).
    pedidos_candidatos_movimento = []
    if pedido.loja_destino_id:
        pedidos_candidatos_movimento = (
            HoraPedido.query
            .filter(HoraPedido.loja_destino_id == pedido.loja_destino_id)
            .filter(HoraPedido.status != 'CANCELADO')
            .filter(HoraPedido.id != pedido.id)
            .order_by(HoraPedido.data_pedido.desc(), HoraPedido.id.desc())
            .limit(100)
            .all()
        )

    # Deteccao de chassi duplicado em outros pedidos ATIVOS.
    # Mapa {chassi: [{pedido_id, numero_pedido, status, item_id}]} usado pelo
    # template para alerta visual. Vazio se pedido base esta CANCELADO ou nao
    # ha duplicidades.
    duplicidades_chassi = pedido_service.chassis_duplicados_em_outros_pedidos(pedido.id)

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
        comparativo_valores=comparativo_valores,
        pedidos_candidatos_movimento=pedidos_candidatos_movimento,
        duplicidades_chassi=duplicidades_chassi,
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
                origem='XLSX',
            )
            sucessos.append(
                f'{pedido.numero_pedido} ({len(pedido.itens)} itens, {pedido.loja_destino.rotulo_display})'
            )
            if primeiro_pedido_id is None:
                primeiro_pedido_id = pedido.id
        except ValueError as exc:
            # Isola a transacao por pedido: criar_pedido faz flush do header
            # antes dos itens; sem rollback, o header de um pedido que falhou
            # vazaria no commit do proximo pedido do batch (header orfao sem
            # itens — o bug dos pedidos 119/124/125/126).
            from app import db as _db
            _db.session.rollback()
            erros.append(f'{nome_arq} (pedido {numero}): {exc}')
        except Exception as exc:  # noqa: BLE001 — mostra ao usuário ao invés de 500
            from app import db as _db
            _db.session.rollback()
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
# Importacao via IMAGEM (OCR Sonnet 4.6)
# ========================================================================

# Limites para imagens. Imagens sao maiores que XLSX em bytes mas o LLM
# tambem cobra tokens proporcional ao numero de imagens, entao limite de
# 50 por batch evita custo de uma imagem ruim multiplicado.
MAX_IMAGEM_BYTES = 5 * 1024 * 1024
MAX_BATCH_IMAGENS = 50
MAX_BATCH_BYTES_IMAGENS = 100 * 1024 * 1024


def _serializar_extracao_dict_imagem(
    pedido_extraido,
    imagem_bytes: bytes | None = None,
    imagem_nome_original: str | None = None,
    imagem_mime_type: str = 'image/jpeg',
) -> dict:
    """Serializa PedidoExtraido + bytes da imagem para o token de preview.

    Espelha _serializar_extracao_dict (XLSX) mas guarda imagem em vez de XLSX.
    """
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
        'metodo_extracao': pedido_extraido.metodo_extracao,
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
        'imagem_bytes_b64': (
            base64.b64encode(imagem_bytes).decode('ascii') if imagem_bytes else None
        ),
        'imagem_nome_original': imagem_nome_original,
        'imagem_mime_type': imagem_mime_type,
    }


def _deserializar_extracao_dict_imagem(d: dict):
    """Reconstroi (PedidoExtraido, imagem_bytes, imagem_nome, mime) do dict."""
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
        header_row=d.get('header_row'),
        avisos=d['avisos'],
        itens=itens,
        metodo_extracao=d.get('metodo_extracao', 'IMAGEM_LLM_SONNET_4_6'),
    )
    img_b64 = d.get('imagem_bytes_b64')
    img_bytes = base64.b64decode(img_b64) if img_b64 else None
    img_nome = d.get('imagem_nome_original')
    mime = d.get('imagem_mime_type', 'image/jpeg')
    return extraido, img_bytes, img_nome, mime


@hora_bp.route('/pedidos/importar-imagem', methods=['GET', 'POST'])
@require_hora_perm('pedidos', 'criar')
def pedidos_importar_imagem():
    """Upload de N imagens → parseia cada uma via Claude Sonnet 4.6 → preview.

    Espelho de pedidos_importar_xlsx mas com imagens (JPG/PNG/WEBP). Usa o
    mesmo template de preview parametrizado (tipo_origem='IMAGEM').
    """
    import os

    if request.method == 'GET':
        # Pre-checa se ANTHROPIC_API_KEY esta configurado — se nao, mostra
        # aviso ao operador antes que ele faca upload (evita perder tempo).
        sem_api_key = not os.environ.get('ANTHROPIC_API_KEY')
        return render_template(
            'hora/pedido_importar_imagem.html', sem_api_key=sem_api_key,
        )

    if not os.environ.get('ANTHROPIC_API_KEY'):
        flash(
            'ANTHROPIC_API_KEY nao configurado no servidor — parser de imagem '
            'desabilitado. Configure a variavel ou use o import via XLSX.',
            'danger',
        )
        return render_template('hora/pedido_importar_imagem.html', sem_api_key=True)

    arquivos = [a for a in request.files.getlist('imagens') if a and a.filename]
    if not arquivos:
        flash('Selecione pelo menos uma imagem (JPG/PNG/WEBP).', 'danger')
        return render_template('hora/pedido_importar_imagem.html')

    if len(arquivos) > MAX_BATCH_IMAGENS:
        flash(
            f'Muitas imagens ({len(arquivos)}; max {MAX_BATCH_IMAGENS}). '
            f'Divida em uploads menores.',
            'danger',
        )
        return render_template('hora/pedido_importar_imagem.html')

    # 1ª passada: validar bytes + MIME.
    arquivos_bytes: list[tuple[str, bytes, str]] = []  # (nome, bytes, mime)
    total_bytes = 0
    for arq in arquivos:
        # Detecta MIME a partir do content_type (browser) ou extensao
        mime = (arq.mimetype or '').lower().split(';')[0].strip()
        if mime not in MIME_TYPES_ACEITOS:
            # Tentativa de fallback via extensao
            ext = (arq.filename or '').lower().rsplit('.', 1)[-1] if arq.filename and '.' in arq.filename else ''
            mime_por_ext = {
                'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                'png': 'image/png', 'webp': 'image/webp',
            }.get(ext)
            if mime_por_ext:
                mime = mime_por_ext
            else:
                flash(
                    f'Arquivo "{arq.filename}" tem MIME nao suportado: '
                    f'{arq.mimetype or "(desconhecido)"}. Aceito: JPG, PNG, WEBP.',
                    'danger',
                )
                return render_template('hora/pedido_importar_imagem.html')

        conteudo = arq.read()
        if len(conteudo) > MAX_IMAGEM_BYTES:
            flash(
                f'Imagem "{arq.filename}" muito grande ({len(conteudo) // 1024} KB; '
                f'max {MAX_IMAGEM_BYTES // 1024} KB).',
                'danger',
            )
            return render_template('hora/pedido_importar_imagem.html')
        total_bytes += len(conteudo)
        arquivos_bytes.append((arq.filename, conteudo, mime))

    if total_bytes > MAX_BATCH_BYTES_IMAGENS:
        flash(
            f'Tamanho combinado excedido ({total_bytes // (1024*1024)} MB; '
            f'max {MAX_BATCH_BYTES_IMAGENS // (1024*1024)} MB).',
            'danger',
        )
        return render_template('hora/pedido_importar_imagem.html')

    lojas_ativas = HoraLoja.query.filter_by(ativa=True).order_by(HoraLoja.nome).all()

    # 2ª passada: chama LLM para cada imagem. Falha individual nao bloqueia outras.
    cards = []
    extracoes_para_token: list[dict] = []
    numeros_vistos: dict[str, int] = {}

    for filename, conteudo, mime in arquivos_bytes:
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
            'token_index': None,
        }

        try:
            extracao = parse_pedido_imagem(conteudo, nome_arquivo=filename, mime_type=mime)
        except PedidoParseError as exc:
            card['erro'] = f'Erro na extracao OCR: {exc}'
            cards.append(card)
            continue
        except Exception as exc:  # noqa: BLE001 — qualquer falha LLM
            from flask import current_app as _app
            _app.logger.exception(
                'hora: erro inesperado parseando imagem %s', filename,
            )
            card['erro'] = f'Erro inesperado: {exc}'
            cards.append(card)
            continue

        card['parse_ok'] = True
        card['extracao'] = extracao

        # Triagem CNPJ matriz
        if not cnpj_matriz_presente(extracao.cnpjs_candidatos):
            cnpjs_encontrados = (
                ', '.join(extracao.cnpjs_candidatos)
                if extracao.cnpjs_candidatos else 'nenhum'
            )
            card['erro'] = (
                f'CNPJ da matriz HORA ({CNPJ_MATRIZ_HORA}) nao encontrado na imagem. '
                f'CNPJs detectados: {cnpjs_encontrados}.'
            )
            cards.append(card)
            continue
        card['cnpj_matriz_ok'] = True

        # Resolucao de loja
        loja_sugerida_id, msg_lookup = resolver_loja_por_apelido(extracao.apelido_detectado)
        card['loja_sugerida_id'] = loja_sugerida_id
        card['msg_lookup'] = msg_lookup

        # Duplicado no batch
        numero = extracao.numero_pedido
        if numero in numeros_vistos:
            card['aviso_duplicado_batch'] = True

        card['token_index'] = len(extracoes_para_token)
        extracoes_para_token.append(
            _serializar_extracao_dict_imagem(
                extracao,
                imagem_bytes=conteudo,
                imagem_nome_original=filename,
                imagem_mime_type=mime,
            )
        )
        numeros_vistos[numero] = numeros_vistos.get(numero, 0) + 1

        cards.append(card)

    cards_elegiveis = [c for c in cards if c['token_index'] is not None]
    cards_descartados = [c for c in cards if c['token_index'] is None]

    if not cards_elegiveis:
        flash(
            'Nenhuma imagem elegivel para importacao. Veja os erros e tente novamente.',
            'danger',
        )
        return render_template('hora/pedido_importar_imagem.html')

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
        # Parametros que diferenciam o template do XLSX:
        tipo_origem='IMAGEM',
        url_voltar=url_for('hora.pedidos_importar_imagem'),
        url_confirmar=url_for('hora.pedidos_importar_imagem_confirmar'),
    )


@hora_bp.route('/pedidos/importar-imagem/confirmar', methods=['POST'])
@require_hora_perm('pedidos', 'criar')
def pedidos_importar_imagem_confirmar():
    """Confirma criacao em batch de pedidos a partir de imagens.

    Para cada pedido selecionado:
      1. Faz upload da imagem original ao S3 (sincrono).
      2. Cria HoraPedido com origem='IMAGEM' + arquivo_origem_s3_key=imagem.
      3. Enfileira job RQ para gerar XLSX equivalente em background.
    """
    token = request.form.get('token')
    if not token:
        flash('Token ausente.', 'danger')
        return redirect(url_for('hora.pedidos_importar_imagem'))

    try:
        extracoes_dicts = _deserializar_extracoes(token)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        flash(f'Token invalido: {exc}', 'danger')
        return redirect(url_for('hora.pedidos_importar_imagem'))

    incluir_indices_raw = request.form.getlist('incluir_idx[]')
    incluir_indices = {int(i) for i in incluir_indices_raw if i.isdigit()}

    if not incluir_indices:
        flash('Nenhum pedido selecionado.', 'warning')
        return redirect(url_for('hora.pedidos_importar_imagem'))

    sucessos: list[str] = []
    erros: list[str] = []
    primeiro_pedido_id = None
    jobs_xlsx_enfileirados = 0
    falhas_enfileirar_xlsx = 0

    from flask import current_app as _app
    from app.utils.file_storage import FileStorage

    for idx, d in enumerate(extracoes_dicts):
        if idx not in incluir_indices:
            continue

        loja_str = (request.form.get(f'loja_destino_id_{idx}') or '').strip()
        nome_arq = d.get('imagem_nome_original') or f'imagem_{idx + 1}'
        numero = d.get('numero_pedido') or f'(idx {idx})'

        if not loja_str.isdigit():
            erros.append(f'{nome_arq}: loja destino nao selecionada.')
            continue

        try:
            extracao, img_bytes, img_nome, img_mime = _deserializar_extracao_dict_imagem(d)

            # Upload da imagem original ao S3 (sincrono — falha cria pedido sem imagem).
            arquivo_origem_s3_key = None
            if img_bytes:
                try:
                    import io as _io
                    buf = _io.BytesIO(img_bytes)
                    ext_imagem = {
                        'image/jpeg': 'jpg',
                        'image/png': 'png',
                        'image/webp': 'webp',
                    }.get(img_mime, 'jpg')
                    nome_persist = f'{extracao.numero_pedido}.{ext_imagem}'
                    buf.name = nome_persist
                    arquivo_origem_s3_key = FileStorage().save_file(
                        buf,
                        folder='hora/pedidos/imagem-import',
                        filename=nome_persist,
                        allowed_extensions=['jpg', 'jpeg', 'png', 'webp'],
                    )
                except Exception as exc:
                    _app.logger.warning(
                        'hora: falha ao persistir imagem do pedido %s: %s',
                        extracao.numero_pedido, exc,
                    )

            pedido = pedido_service.criar_pedido_a_partir_de_extracao(
                pedido_extraido=extracao,
                loja_destino_id=int(loja_str),
                arquivo_origem_s3_key=arquivo_origem_s3_key,
                criado_por=current_user.nome if hasattr(current_user, 'nome') else None,
                origem='IMAGEM',
            )
            sucessos.append(
                f'{pedido.numero_pedido} ({len(pedido.itens)} itens, '
                f'{pedido.loja_destino.rotulo_display})'
            )
            if primeiro_pedido_id is None:
                primeiro_pedido_id = pedido.id

            # Enfileira job para gerar XLSX equivalente em background.
            try:
                from app.hora.workers.pedido_imagem_worker import (
                    enfileirar_gerar_xlsx_para_pedido_imagem,
                )
                enfileirar_gerar_xlsx_para_pedido_imagem(pedido.id)
                jobs_xlsx_enfileirados += 1
            except Exception as exc:  # noqa: BLE001
                _app.logger.warning(
                    'hora: falha ao enfileirar job XLSX para pedido %s: %s',
                    pedido.id, exc,
                )
                falhas_enfileirar_xlsx += 1

        except ValueError as exc:
            # Mesmo isolamento por-pedido do import XLSX: sem rollback, o header
            # flushado de um pedido que falhou vazaria no commit do proximo.
            from app import db as _db
            _db.session.rollback()
            erros.append(f'{nome_arq} (pedido {numero}): {exc}')
        except Exception as exc:  # noqa: BLE001
            from app import db as _db
            _db.session.rollback()
            _app.logger.exception(
                'hora: erro inesperado ao criar pedido a partir da imagem %s', nome_arq,
            )
            erros.append(f'{nome_arq} (pedido {numero}): erro inesperado — {exc}')

    if sucessos:
        flash(
            f'{len(sucessos)} pedido(s) criado(s) via imagem: ' + ' · '.join(sucessos),
            'success',
        )
        if jobs_xlsx_enfileirados:
            flash(
                f'{jobs_xlsx_enfileirados} job(s) enfileirado(s) para gerar XLSX equivalente '
                f'em background. Aguarde alguns segundos e atualize a tela do pedido.',
                'info',
            )
        if falhas_enfileirar_xlsx:
            flash(
                f'{falhas_enfileirar_xlsx} job(s) falharam ao enfileirar — '
                f'pedido(s) criado(s) mas XLSX equivalente nao sera gerado automaticamente. '
                f'Verifique se REDIS_URL esta configurado.',
                'warning',
            )
    if erros:
        flash(
            f'{len(erros)} pedido(s) com erro: ' + ' · '.join(erros),
            'danger' if not sucessos else 'warning',
        )

    if len(sucessos) == 1 and primeiro_pedido_id:
        return redirect(url_for('hora.pedidos_detalhe', pedido_id=primeiro_pedido_id))
    return redirect(url_for('hora.pedidos_lista'))


# ========================================================================
# Download XLSX/imagem de origem
# ========================================================================

@hora_bp.route('/pedidos/<int:pedido_id>/download-xlsx')
@require_hora_perm('pedidos', 'ver')
def pedidos_download_xlsx(pedido_id: int):
    """Redireciona para URL (S3 presigned ou local) do arquivo original do pedido.

    Para origem='XLSX': retorna o XLSX original que o operador subiu.
    Para origem='IMAGEM': retorna a IMAGEM original que o operador subiu
                          (apesar do nome legacy da rota — kept para compat URLs).
    Se quiser o XLSX equivalente gerado em background para origem='IMAGEM',
    use a rota /pedidos/<id>/download-xlsx-equivalente.
    """
    pedido = HoraPedido.query.get_or_404(pedido_id)
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        flash('Acesso negado: pedido de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.pedidos_lista'))
    if not pedido.arquivo_origem_s3_key:
        flash(
            'Arquivo deste pedido nao esta armazenado (pedido manual ou import anterior a esta feature).',
            'warning',
        )
        return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido.id))

    from app.utils.file_storage import FileStorage
    url = FileStorage().get_file_url(pedido.arquivo_origem_s3_key)
    if not url:
        flash('Falha ao gerar URL do arquivo.', 'danger')
        return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido.id))
    return redirect(url)


@hora_bp.route('/pedidos/<int:pedido_id>/download-xlsx-equivalente')
@require_hora_perm('pedidos', 'ver')
def pedidos_download_xlsx_equivalente(pedido_id: int):
    """Para origem='IMAGEM': baixa o XLSX equivalente gerado em background.

    Se o job ainda nao terminou, mostra mensagem para tentar de novo.
    """
    pedido = HoraPedido.query.get_or_404(pedido_id)
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        flash('Acesso negado: pedido de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.pedidos_lista'))
    if pedido.origem != 'IMAGEM':
        flash(
            'Pedido nao foi criado via imagem — XLSX equivalente nao se aplica. '
            'Para baixar o XLSX original, use o botao "Baixar arquivo original".',
            'info',
        )
        return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido.id))
    if not pedido.xlsx_origem_s3_key:
        flash(
            'XLSX equivalente ainda esta sendo gerado em background. '
            'Atualize a tela em alguns segundos.',
            'info',
        )
        return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido.id))

    from app.utils.file_storage import FileStorage
    url = FileStorage().get_file_url(pedido.xlsx_origem_s3_key)
    if not url:
        flash('Falha ao gerar URL do XLSX equivalente.', 'danger')
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


# ========================================================================
# Mover item entre pedidos (1 moto = 1 chassi pode mudar de pedido)
# ========================================================================

@hora_bp.route(
    '/pedidos/<int:pedido_id>/itens/<int:item_id>/mover',
    methods=['POST'],
)
@require_hora_perm('pedidos', 'editar')
def pedidos_mover_item(pedido_id: int, item_id: int):
    """Move 1 item (moto/chassi) de um pedido para outro.

    Apos mover, tenta vincular automaticamente NFs orfas que contem o chassi
    com o pedido destino (facilita o vinculo Pedido x NF).

    Form/JSON:
      - pedido_destino_id (obrigatorio)
      - tentar_vincular_nfs (opcional, default True)
    """
    pedido = HoraPedido.query.get_or_404(pedido_id)
    is_ajax = (
        request.is_json
        or request.headers.get('Accept') == 'application/json'
    )

    # Acesso a loja origem
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        if is_ajax:
            return jsonify({'ok': False, 'erro': 'acesso negado'}), 403
        flash('Acesso negado: pedido de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.pedidos_lista'))

    # Le payload (suporta JSON e form)
    payload = request.get_json(silent=True) or request.form
    destino_str = str(payload.get('pedido_destino_id') or '').strip()
    if not destino_str.isdigit():
        if is_ajax:
            return jsonify({'ok': False, 'erro': 'pedido_destino_id invalido'}), 400
        flash('Pedido destino invalido.', 'danger')
        return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido.id))

    pedido_destino_id = int(destino_str)
    tentar_vincular_nfs = str(
        payload.get('tentar_vincular_nfs', '1')
    ).lower() not in ('0', 'false', 'no', '')

    pedido_destino = HoraPedido.query.get(pedido_destino_id)
    if not pedido_destino:
        if is_ajax:
            return jsonify({'ok': False, 'erro': 'pedido destino nao encontrado'}), 404
        flash(f'Pedido destino {pedido_destino_id} nao encontrado.', 'danger')
        return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido.id))

    # Acesso a loja destino (regra de matching: mesma loja, mas validamos
    # autorizacao de qualquer forma — usuario precisa ter acesso a ambas)
    if pedido_destino.loja_destino_id and not usuario_tem_acesso_a_loja(
        pedido_destino.loja_destino_id
    ):
        if is_ajax:
            return jsonify({'ok': False, 'erro': 'acesso negado ao pedido destino'}), 403
        flash('Acesso negado: pedido destino de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido.id))

    try:
        res = pedido_service.mover_item_para_outro_pedido(
            pedido_origem_id=pedido.id,
            item_id=item_id,
            pedido_destino_id=pedido_destino_id,
            tentar_vincular_nfs=tentar_vincular_nfs,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
    except ValueError as exc:
        if is_ajax:
            return jsonify({'ok': False, 'erro': str(exc)}), 400
        flash(f'Erro ao mover item: {exc}', 'danger')
        return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido.id))

    if is_ajax:
        # Enriquece com URLs uteis pro front-end
        res['pedido_destino_url'] = url_for(
            'hora.pedidos_detalhe', pedido_id=pedido_destino_id,
        )
        return jsonify(res)

    # Modo nao-AJAX: monta flash com resumo e redireciona ao destino
    n_auto = len(res.get('nfs_auto_vinculadas') or [])
    n_outras = len(res.get('nfs_candidatas_outras') or [])
    msg = (
        f'Item movido para o pedido {pedido_destino.numero_pedido}.'
    )
    if n_auto:
        nf_nums = ', '.join(
            n['numero_nf'] for n in res['nfs_auto_vinculadas']
        )
        msg += f' {n_auto} NF(s) vinculada(s) automaticamente: {nf_nums}.'
    if n_outras:
        msg += (
            f' {n_outras} NF(s) com este chassi precisam de revisao manual '
            f'(ja vinculadas a outros pedidos ou outra loja).'
        )
    flash(msg, 'success')
    return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido_destino_id))


# ========================================================================
# Itens de PECA (compra de pecas - XOR moto/peca em hora_pedido_item)
# ========================================================================

@hora_bp.route('/pedidos/<int:pedido_id>/itens-peca/novo', methods=['POST'])
@require_hora_perm('pedidos', 'editar')
def pedido_adicionar_item_peca(pedido_id: int):
    """Adiciona item peca em pedido de compra (HoraPedido)."""
    pedido = HoraPedido.query.get_or_404(pedido_id)
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        flash('Acesso negado: pedido de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.pedidos_lista'))

    try:
        peca_id_str = (request.form.get('peca_id') or '').strip()
        if not peca_id_str.isdigit():
            raise ValueError('Selecione uma peca')
        peca_id = int(peca_id_str)
        qtd_str = (request.form.get('qtd_pedida') or '').strip().replace(',', '.')
        preco_str = (request.form.get('preco_compra_esperado') or '').strip().replace(',', '.')
        if not qtd_str or not preco_str:
            raise ValueError('Quantidade e preco obrigatorios')
        pedido_service.adicionar_item_peca_pedido(
            pedido_id=pedido_id,
            peca_id=peca_id,
            qtd_pedida=Decimal(qtd_str),
            preco_compra_esperado=Decimal(preco_str),
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        flash('Peca adicionada ao pedido.', 'success')
    except (ValueError, InvalidOperation) as exc:
        flash(f'Erro ao adicionar peca: {exc}', 'danger')

    return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido_id))


@hora_bp.route('/pedidos/<int:pedido_id>/itens-peca/<int:item_id>/remover', methods=['POST'])
@require_hora_perm('pedidos', 'editar')
def pedido_remover_item_peca(pedido_id: int, item_id: int):
    """Remove item peca de pedido em status ABERTO."""
    pedido = HoraPedido.query.get_or_404(pedido_id)
    if pedido.loja_destino_id and not usuario_tem_acesso_a_loja(pedido.loja_destino_id):
        flash('Acesso negado: pedido de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.pedidos_lista'))

    try:
        pedido_service.remover_item_peca_pedido(
            pedido_id=pedido_id,
            item_id=item_id,
            operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        flash('Peca removida do pedido.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')

    return redirect(url_for('hora.pedidos_detalhe', pedido_id=pedido_id))
