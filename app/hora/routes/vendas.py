"""Rotas de Pedido de Venda (HORA -> consumidor final).

Inclui: upload DANFE legado, criacao manual via TagPlus, listagem, detalhe,
edicao de header e itens, transicoes (confirmar, cancelar), definicao de loja,
resolucao de divergencias.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.hora.decorators import require_hora_perm
from app.hora.models import (
    HoraLoja,
    HoraVenda,
    HoraVendaDivergencia,
    VENDA_STATUS_COTACAO,
)
from app.hora.models.tagplus import HoraTagPlusFormaPagamentoMap
from app.hora.routes import hora_bp
from app.hora.services import venda_service
from app.hora.services.auth_helper import (
    lojas_permitidas_ids,
    usuario_tem_acesso_a_loja,
)
from app.hora.services.parsers.danfe_adapter import DanfeParseError


def _lojas_ativas_permitidas():
    permitidas = lojas_permitidas_ids()
    q = HoraLoja.query.filter_by(ativa=True)
    if permitidas is not None:
        if not permitidas:
            return []
        q = q.filter(HoraLoja.id.in_(permitidas))
    return q.order_by(HoraLoja.nome).all()


def _operador_atual() -> str:
    return getattr(current_user, 'nome', None) or 'desconhecido'


# ------------------------------------------------------------------------
# Listagem
# ------------------------------------------------------------------------

@hora_bp.route('/vendas')
@require_hora_perm('vendas', 'ver')
def vendas_lista():
    try:
        page = int(request.args.get('page', 1))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = int(request.args.get('per_page', 50))
    except (TypeError, ValueError):
        per_page = 50

    status_filtro = (request.args.get('status') or '').strip().upper() or None
    if status_filtro and status_filtro not in (
        'COTACAO', 'CONFIRMADO', 'FATURADO', 'CANCELADO',
    ):
        status_filtro = None

    pagination = venda_service.paginar_vendas(
        page=page, per_page=per_page,
        lojas_permitidas_ids=lojas_permitidas_ids(),
        status=status_filtro,
    )
    return render_template(
        'hora/vendas_lista.html',
        pagination=pagination,
        vendas=(pagination.items if pagination else []),
        status_filtro=status_filtro,
        per_page=per_page,
    )


# ------------------------------------------------------------------------
# Upload DANFE -> cria venda
# ------------------------------------------------------------------------

@hora_bp.route('/vendas/upload', methods=['GET', 'POST'])
@require_hora_perm('vendas', 'criar')
def vendas_upload():
    """Upload DANFE PDF emitido pela loja HORA — aceita 1 ou N arquivos
    (BACKFILL em lote). Parseia via adapter e cria HoraVenda + itens +
    eventos VENDIDA + divergencias para cada PDF.

    Nao pede loja nem cliente — tudo vem da NF. Operador preenche vendedor e
    forma_pagamento depois na tela de detalhe.
    """
    if request.method == 'POST':
        # Aceita campo `pdf` (legacy 1 arquivo) e `pdfs` (multiplo).
        arquivos = request.files.getlist('pdfs') or []
        if not arquivos:
            unico = request.files.get('pdf')
            if unico and unico.filename:
                arquivos = [unico]

        arquivos = [a for a in arquivos if a and a.filename]
        if not arquivos:
            flash('Selecione ao menos 1 arquivo PDF.', 'danger')
            return render_template('hora/venda_upload.html', resultados=[])

        resultados = []
        operador = _operador_atual()
        for arq in arquivos:
            entry = {
                'arquivo': arq.filename,
                'status': None,         # 'sucesso' | 'duplicado' | 'erro'
                'venda_id': None,
                'numero_nf': None,
                'qtd_chassis': 0,
                'qtd_divergencias': 0,
                'mensagem': '',
            }
            try:
                pdf_bytes = arq.read()
                venda = venda_service.importar_nf_saida_pdf(
                    pdf_bytes=pdf_bytes,
                    nome_arquivo_origem=arq.filename,
                    criado_por=operador,
                )
                entry.update({
                    'status': 'sucesso',
                    'venda_id': venda.id,
                    'numero_nf': venda.nf_saida_numero,
                    'qtd_chassis': len(venda.itens),
                    'qtd_divergencias': len(venda.divergencias_abertas),
                    'mensagem': (
                        f'NF {venda.nf_saida_numero} importada — '
                        f'{len(venda.itens)} chassi(s) para {venda.nome_cliente}.'
                    ),
                })
            except venda_service.NfSaidaJaImportada as exc:
                entry['status'] = 'duplicado'
                entry['mensagem'] = str(exc)
            except (ValueError, DanfeParseError) as exc:
                entry['status'] = 'erro'
                entry['mensagem'] = f'Erro ao importar: {exc}'
            except Exception as exc:  # pragma: no cover
                entry['status'] = 'erro'
                entry['mensagem'] = f'Erro inesperado: {exc}'
            resultados.append(entry)

        # Resumo flash + tela de resultados.
        n_ok = sum(1 for r in resultados if r['status'] == 'sucesso')
        n_dup = sum(1 for r in resultados if r['status'] == 'duplicado')
        n_err = sum(1 for r in resultados if r['status'] == 'erro')
        n_div = sum(r['qtd_divergencias'] for r in resultados)
        if len(resultados) == 1 and n_ok == 1 and n_div == 0:
            # Caso 1-arquivo bem sucedido: mantem comportamento legado
            # (redireciona pro detalhe).
            return redirect(url_for(
                'hora.vendas_detalhe', venda_id=resultados[0]['venda_id'],
            ))
        flash(
            f'Backfill: {n_ok} ok · {n_dup} duplicado(s) · {n_err} erro(s) '
            f'· {n_div} divergencia(s) total.',
            'warning' if (n_err or n_dup or n_div) else 'success',
        )
        return render_template('hora/venda_upload.html', resultados=resultados)

    return render_template('hora/venda_upload.html', resultados=[])


# ------------------------------------------------------------------------
# Detalhe
# ------------------------------------------------------------------------

@hora_bp.route('/vendas/<int:venda_id>')
@require_hora_perm('vendas', 'ver')
def vendas_detalhe(venda_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    if venda.loja_id and not usuario_tem_acesso_a_loja(venda.loja_id):
        flash('Acesso negado: venda de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.vendas_lista'))
    # Venda sem loja (loja_id=NULL) so e acessivel para admin (lojas_permitidas_ids=None).
    if not venda.loja_id and lojas_permitidas_ids() is not None:
        flash(
            'Esta venda ainda nao tem loja definida — apenas administradores podem abrir.',
            'warning',
        )
        return redirect(url_for('hora.vendas_lista'))

    # Sempre popular lojas_ativas — operador pode trocar loja em vendas
    # backfilladas que caem na matriz por causa do CNPJ emitente (regra
    # fiscal: NFe HORA sai sempre com CNPJ da matriz). Filtrado por escopo.
    lojas_ativas = _lojas_ativas_permitidas()

    # Formas de pagamento dinamicas: mapeamentos cadastrados em
    # HoraTagPlusFormaPagamentoMap (mesma fonte usada no formulario de pedido
    # de venda manual). 'NAO_INFORMADO' eh sentinela (default da coluna) e
    # sempre aparece como primeira opcao.
    formas_pagamento = (
        HoraTagPlusFormaPagamentoMap.query
        .order_by(HoraTagPlusFormaPagamentoMap.forma_pagamento_hora)
        .all()
    )

    return render_template(
        'hora/venda_detalhe.html',
        venda=venda,
        lojas_ativas=lojas_ativas,
        formas_pagamento=formas_pagamento,
    )


# ------------------------------------------------------------------------
# Download PDF
# ------------------------------------------------------------------------

@hora_bp.route('/vendas/<int:venda_id>/download-pdf')
@require_hora_perm('vendas', 'ver')
def vendas_download_pdf(venda_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    if venda.loja_id and not usuario_tem_acesso_a_loja(venda.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.vendas_lista'))
    if not venda.arquivo_pdf_s3_key:
        flash('PDF desta venda nao esta armazenado.', 'warning')
        return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))

    from app.utils.file_storage import FileStorage
    url = FileStorage().get_file_url(venda.arquivo_pdf_s3_key)
    if not url:
        flash('Falha ao gerar URL do PDF.', 'danger')
        return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))
    return redirect(url)


# ------------------------------------------------------------------------
# Editar (vendedor, forma_pagamento, contato, observacoes)
# ------------------------------------------------------------------------

@hora_bp.route('/vendas/<int:venda_id>/editar', methods=['POST'])
@require_hora_perm('vendas', 'editar')
def vendas_editar(venda_id: int):
    """Edita campos do header. Conjunto de campos permitidos varia por status:
    - COTACAO: tudo (incluindo cliente/endereco)
    - CONFIRMADO: contato/endereco/operacionais
    - FATURADO: so observacoes
    - CANCELADO: nada
    """
    venda = HoraVenda.query.get_or_404(venda_id)
    if venda.loja_id and not usuario_tem_acesso_a_loja(venda.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.vendas_lista'))
    if not venda.loja_id and lojas_permitidas_ids() is not None:
        flash('Pedido sem loja definida — apenas admin edita.', 'warning')
        return redirect(url_for('hora.vendas_lista'))

    try:
        venda_service.editar_venda(
            venda_id=venda.id,
            vendedor=request.form.get('vendedor'),
            forma_pagamento=request.form.get('forma_pagamento'),
            telefone_cliente=request.form.get('telefone_cliente'),
            email_cliente=request.form.get('email_cliente'),
            observacoes=request.form.get('observacoes'),
            nome_cliente=request.form.get('nome_cliente'),
            cpf_cliente=request.form.get('cpf_cliente'),
            cep=request.form.get('cep'),
            endereco_logradouro=request.form.get('endereco_logradouro'),
            endereco_numero=request.form.get('endereco_numero'),
            endereco_complemento=request.form.get('endereco_complemento'),
            endereco_bairro=request.form.get('endereco_bairro'),
            endereco_cidade=request.form.get('endereco_cidade'),
            endereco_uf=request.form.get('endereco_uf'),
            modalidade_frete=request.form.get('modalidade_frete'),
            numero_parcelas=request.form.get('numero_parcelas'),
            intervalo_parcelas_dias=request.form.get('intervalo_parcelas_dias'),
            usuario=_operador_atual(),
        )
        flash('Pedido atualizado.', 'success')
    except (ValueError, venda_service.TransicaoInvalidaError) as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))


# ------------------------------------------------------------------------
# Confirmar pedido (COTACAO -> CONFIRMADO)
# ------------------------------------------------------------------------

@hora_bp.route('/vendas/<int:venda_id>/confirmar', methods=['POST'])
@require_hora_perm('vendas', 'aprovar')
def vendas_confirmar(venda_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    if venda.loja_id and not usuario_tem_acesso_a_loja(venda.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.vendas_lista'))
    if not venda.loja_id and lojas_permitidas_ids() is not None:
        flash('Pedido sem loja definida — apenas admin confirma.', 'warning')
        return redirect(url_for('hora.vendas_lista'))

    try:
        venda_service.confirmar_venda(
            venda_id=venda.id, usuario=_operador_atual(),
        )
        flash(
            f'Pedido #{venda.id} confirmado. Pronto para emissao de NFe.',
            'success',
        )
    except (ValueError, venda_service.TransicaoInvalidaError) as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))


# ------------------------------------------------------------------------
# Voltar para cotacao (CONFIRMADO -> COTACAO, para reabrir edicao)
# ------------------------------------------------------------------------

@hora_bp.route('/vendas/<int:venda_id>/voltar-cotacao', methods=['POST'])
@require_hora_perm('vendas', 'editar')
def vendas_voltar_cotacao(venda_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    if venda.loja_id and not usuario_tem_acesso_a_loja(venda.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.vendas_lista'))
    try:
        venda_service.voltar_para_cotacao(
            venda_id=venda.id, usuario=_operador_atual(),
        )
        flash(
            f'Pedido #{venda.id} voltou para COTACAO. Edite e confirme novamente.',
            'success',
        )
    except (ValueError, venda_service.TransicaoInvalidaError) as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))


# ------------------------------------------------------------------------
# Edicao de itens (apenas em COTACAO)
# ------------------------------------------------------------------------

def _parse_decimal_form(valor_raw: str) -> Decimal:
    valor_raw = (valor_raw or '').strip()
    try:
        return (
            Decimal(valor_raw.replace('.', '').replace(',', '.'))
            if ',' in valor_raw else Decimal(valor_raw)
        )
    except (InvalidOperation, ValueError):
        raise ValueError(f'Valor invalido: {valor_raw!r}')


@hora_bp.route('/vendas/<int:venda_id>/itens/adicionar', methods=['POST'])
@require_hora_perm('vendas', 'editar')
def vendas_item_adicionar(venda_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    if venda.loja_id and not usuario_tem_acesso_a_loja(venda.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.vendas_lista'))
    if venda.status != VENDA_STATUS_COTACAO:
        flash('Itens so podem ser adicionados em pedidos COTACAO.', 'warning')
        return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))

    chassi = (request.form.get('numero_chassi') or '').strip()
    valor_raw = request.form.get('valor_final', '')
    try:
        valor = _parse_decimal_form(valor_raw)
        venda_service.adicionar_item_pedido(
            venda_id=venda.id,
            numero_chassi=chassi,
            valor_final=valor,
            usuario=_operador_atual(),
        )
        flash(f'Item adicionado ao pedido #{venda.id}.', 'success')
    except (ValueError, venda_service.ChassiIndisponivelError,
            venda_service.TransicaoInvalidaError) as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))


@hora_bp.route('/vendas/<int:venda_id>/itens/<int:item_id>/remover', methods=['POST'])
@require_hora_perm('vendas', 'editar')
def vendas_item_remover(venda_id: int, item_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    if venda.loja_id and not usuario_tem_acesso_a_loja(venda.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.vendas_lista'))
    try:
        venda_service.remover_item_pedido(
            venda_id=venda.id, item_id=item_id,
            usuario=_operador_atual(),
        )
        flash('Item removido.', 'success')
    except (ValueError, venda_service.TransicaoInvalidaError) as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))


@hora_bp.route('/vendas/<int:venda_id>/itens/<int:item_id>/editar', methods=['POST'])
@require_hora_perm('vendas', 'editar')
def vendas_item_editar(venda_id: int, item_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    if venda.loja_id and not usuario_tem_acesso_a_loja(venda.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.vendas_lista'))

    novo_chassi = (request.form.get('novo_chassi') or '').strip() or None
    valor_raw = (request.form.get('valor_final') or '').strip()
    novo_valor = None
    if valor_raw:
        try:
            novo_valor = _parse_decimal_form(valor_raw)
        except ValueError as exc:
            flash(f'Erro: {exc}', 'danger')
            return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))

    try:
        venda_service.editar_item_pedido(
            venda_id=venda.id, item_id=item_id,
            novo_chassi=novo_chassi, novo_valor=novo_valor,
            usuario=_operador_atual(),
        )
        flash('Item atualizado.', 'success')
    except (ValueError, venda_service.ChassiIndisponivelError,
            venda_service.TransicaoInvalidaError) as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))


# ------------------------------------------------------------------------
# Definir loja (resolve CNPJ_DESCONHECIDO)
# ------------------------------------------------------------------------

@hora_bp.route('/vendas/<int:venda_id>/definir-loja', methods=['POST'])
@require_hora_perm('vendas', 'editar')
def vendas_definir_loja(venda_id: int):
    """Define ou TROCA a loja do pedido.

    - Vendas sem loja (CNPJ_DESCONHECIDO): apenas admin pode definir.
    - Vendas com loja: usuario com permissao `vendas/editar` na loja
      atual pode trocar (caso tipico do backfill TagPlus, onde todas
      caem na matriz por causa do CNPJ emitente).
    """
    venda = HoraVenda.query.get_or_404(venda_id)

    if venda.loja_id is None:
        # Apenas admin abre venda com loja=NULL — coerente com vendas_detalhe.
        if lojas_permitidas_ids() is not None:
            flash('Apenas administradores podem definir loja de venda sem loja.', 'danger')
            return redirect(url_for('hora.vendas_lista'))
    else:
        # Trocar loja: usuario precisa ter acesso a loja atual.
        if not usuario_tem_acesso_a_loja(venda.loja_id):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('hora.vendas_lista'))

    loja_str = (request.form.get('loja_id') or '').strip()
    if not loja_str.isdigit():
        flash('Selecione a loja.', 'danger')
        return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))

    nova_loja_id = int(loja_str)
    # Usuario nao-admin nao pode mover venda para loja fora do seu escopo.
    permitidas = lojas_permitidas_ids()
    if permitidas is not None and nova_loja_id not in permitidas:
        flash(
            'Voce nao tem permissao na loja destino — peca para um administrador.',
            'danger',
        )
        return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))

    try:
        venda_atualizada = venda_service.definir_loja_venda(
            venda_id=venda.id,
            loja_id=nova_loja_id,
            usuario=_operador_atual(),
        )
        if venda.loja_id is None and venda_atualizada.loja_id == nova_loja_id:
            flash('Loja definida e divergencia CNPJ_DESCONHECIDO resolvida.', 'success')
        else:
            flash('Loja do pedido atualizada.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))


# ------------------------------------------------------------------------
# Cancelar venda
# ------------------------------------------------------------------------

@hora_bp.route('/vendas/<int:venda_id>/cancelar', methods=['POST'])
@require_hora_perm('vendas', 'apagar')
def vendas_cancelar(venda_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    if venda.loja_id and not usuario_tem_acesso_a_loja(venda.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.vendas_lista'))
    if not venda.loja_id and lojas_permitidas_ids() is not None:
        flash('Venda sem loja definida — apenas admin cancela.', 'warning')
        return redirect(url_for('hora.vendas_lista'))

    motivo = (request.form.get('motivo') or '').strip()
    try:
        venda_service.cancelar_venda(
            venda_id=venda.id,
            motivo=motivo,
            usuario=_operador_atual(),
        )
        flash(
            f'Pedido #{venda.id} cancelado. Chassis devolvidos ao estoque.',
            'success',
        )
    except (ValueError, venda_service.TransicaoInvalidaError) as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))


# ------------------------------------------------------------------------
# Resolver divergencia (marca como tratada)
# ------------------------------------------------------------------------

@hora_bp.route(
    '/vendas/<int:venda_id>/divergencias/<int:div_id>/resolver',
    methods=['POST'],
)
@require_hora_perm('vendas', 'editar')
def vendas_resolver_divergencia(venda_id: int, div_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    is_ajax = request.is_json or request.headers.get('Accept') == 'application/json'

    if venda.loja_id and not usuario_tem_acesso_a_loja(venda.loja_id):
        if is_ajax:
            return jsonify({'ok': False, 'erro': 'acesso negado'}), 403
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.vendas_lista'))

    # Venda sem loja (loja_id=NULL) so resolve por admin — mesma regra das
    # outras rotas desta venda (vendas_detalhe/editar/cancelar).
    if not venda.loja_id and lojas_permitidas_ids() is not None:
        if is_ajax:
            return jsonify({'ok': False, 'erro': 'venda sem loja — apenas admin'}), 403
        flash('Venda sem loja definida — apenas admin resolve divergencias.', 'warning')
        return redirect(url_for('hora.vendas_lista'))

    div = HoraVendaDivergencia.query.get_or_404(div_id)
    if div.venda_id != venda.id:
        flash('Divergencia nao pertence a essa venda.', 'danger')
        return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))

    try:
        venda_service.resolver_divergencia(
            divergencia_id=div_id,
            usuario=_operador_atual(),
        )
        flash('Divergencia marcada como resolvida.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))
