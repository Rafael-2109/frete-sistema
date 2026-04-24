"""Rotas de Estoque HORA: KPIs, listagem chassi-a-chassi, rastreamento de moto."""
from __future__ import annotations

from flask import flash, jsonify, redirect, render_template, request, url_for

from app import db
from app.hora.decorators import require_hora_perm
from app.hora.models import HoraLoja, HoraModelo, HoraMoto
from app.hora.routes import hora_bp
from app.hora.services import estoque_service
from app.hora.services.auth_helper import (
    lojas_permitidas_ids,
    usuario_tem_acesso_a_loja,
)


def _int_arg(nome: str):
    v = (request.args.get(nome) or '').strip()
    return int(v) if v.isdigit() else None


@hora_bp.route('/estoque')
@require_hora_perm('estoque', 'ver')
def estoque_lista():
    permitidas = lojas_permitidas_ids()

    loja_id = _int_arg('loja_id')
    modelo_id = _int_arg('modelo_id')
    cor = (request.args.get('cor') or '').strip() or None
    chassi = (request.args.get('chassi') or '').strip() or None
    pedido_id = _int_arg('pedido_id')
    nf_entrada_id = _int_arg('nf_entrada_id')
    venda_id = _int_arg('venda_id')

    if loja_id and not usuario_tem_acesso_a_loja(loja_id):
        flash('Acesso negado a essa loja.', 'danger')
        return redirect(url_for('hora.estoque_lista'))

    incluir_avariadas = request.args.get('incluir_avariadas', '1') == '1'
    incluir_faltando_peca = request.args.get('incluir_faltando_peca', '1') == '1'
    incluir_fora_estoque = request.args.get('incluir_fora_estoque', '0') == '1'

    # Filtros por documento forcam `incluir_fora_estoque=True` para permitir
    # ver vendidas ao filtrar por venda, NF entrada cujo chassi ja saiu, etc.
    if pedido_id or nf_entrada_id or venda_id or chassi:
        incluir_fora_estoque = True

    motos = estoque_service.listar_estoque(
        loja_id=loja_id,
        modelo_id=modelo_id,
        cor=cor,
        incluir_avariadas=incluir_avariadas,
        incluir_faltando_peca=incluir_faltando_peca,
        incluir_fora_estoque=incluir_fora_estoque,
        lojas_permitidas_ids=permitidas,
        pedido_id=pedido_id,
        nf_entrada_id=nf_entrada_id,
        venda_id=venda_id,
        chassi=chassi,
    )
    kpis_loja = estoque_service.kpis_estoque_por_loja(
        lojas_permitidas_ids=permitidas,
    )
    kpis_modelo = estoque_service.kpis_estoque_por_modelo(
        loja_id=loja_id,
        lojas_permitidas_ids=permitidas,
    )

    lojas_q = HoraLoja.query.filter_by(ativa=True)
    if permitidas is not None:
        if not permitidas:
            lojas = []
        else:
            lojas_q = lojas_q.filter(HoraLoja.id.in_(permitidas))
            lojas = lojas_q.order_by(HoraLoja.nome).all()
    else:
        lojas = lojas_q.order_by(HoraLoja.nome).all()

    opcoes = estoque_service.opcoes_filtro_estoque(lojas_permitidas_ids=permitidas)
    opcoes_docs = estoque_service.opcoes_documentos_filtro(
        lojas_permitidas_ids=permitidas,
    )

    # Para preencher input quando vier filtrado por modelo_id, precisamos do nome.
    modelo_selecionado_nome = None
    if modelo_id:
        m = HoraModelo.query.get(modelo_id)
        if m:
            modelo_selecionado_nome = m.nome_modelo

    return render_template(
        'hora/estoque_lista.html',
        motos=motos,
        kpis_loja=kpis_loja,
        kpis_modelo=kpis_modelo,
        lojas=lojas,
        modelos=opcoes['modelos'],
        cores=opcoes['cores'],
        pedidos_filtro=opcoes_docs['pedidos'],
        nfs_entrada_filtro=opcoes_docs['nfs_entrada'],
        vendas_filtro=opcoes_docs['vendas'],
        filtro_loja_id=loja_id,
        filtro_modelo_id=modelo_id,
        filtro_modelo_nome=modelo_selecionado_nome,
        filtro_cor=cor,
        filtro_chassi=chassi,
        filtro_pedido_id=pedido_id,
        filtro_nf_entrada_id=nf_entrada_id,
        filtro_venda_id=venda_id,
        incluir_avariadas=incluir_avariadas,
        incluir_faltando_peca=incluir_faltando_peca,
        incluir_fora_estoque=incluir_fora_estoque,
    )


# ------------------------------------------------------------------
# Autocomplete endpoints (JSON) — usados pelos inputs da tela de estoque.
# ------------------------------------------------------------------

@hora_bp.route('/estoque/autocomplete/chassi')
@require_hora_perm('estoque', 'ver')
def estoque_autocomplete_chassi():
    q = request.args.get('q') or ''
    return jsonify(estoque_service.autocomplete_chassi(
        q=q,
        lojas_permitidas_ids=lojas_permitidas_ids(),
        limit=20,
    ))


@hora_bp.route('/estoque/autocomplete/modelo')
@require_hora_perm('estoque', 'ver')
def estoque_autocomplete_modelo():
    q = request.args.get('q') or ''
    return jsonify(estoque_service.autocomplete_modelo(
        q=q,
        lojas_permitidas_ids=lojas_permitidas_ids(),
        limit=20,
    ))


@hora_bp.route('/estoque/autocomplete/cor')
@require_hora_perm('estoque', 'ver')
def estoque_autocomplete_cor():
    q = request.args.get('q') or ''
    return jsonify(estoque_service.autocomplete_cor(
        q=q,
        lojas_permitidas_ids=lojas_permitidas_ids(),
        limit=20,
    ))


@hora_bp.route('/estoque/chassi/<numero_chassi>')
@require_hora_perm('estoque', 'ver')
def estoque_chassi_detalhe(numero_chassi: str):
    from app.hora.models import HoraMotoEvento

    chassi = numero_chassi.strip().upper()
    moto = HoraMoto.query.get_or_404(chassi)

    rastreio = estoque_service.rastreamento_completo(chassi)

    # Autorizacao: usuario deve ter acesso a ALGUMA loja pela qual este chassi
    # ja passou. Admin (lojas_permitidas_ids() is None) sempre passa.
    permitidas = lojas_permitidas_ids()
    if permitidas is not None:
        if not permitidas:
            flash('Sem acesso a nenhuma loja.', 'danger')
            return redirect(url_for('hora.estoque_lista'))
        tem_vinculo = (
            db.session.query(HoraMotoEvento.id)
            .filter(
                HoraMotoEvento.numero_chassi == chassi,
                HoraMotoEvento.loja_id.in_(permitidas),
            )
            .first()
        )
        if not tem_vinculo:
            flash('Acesso negado a esse chassi.', 'danger')
            return redirect(url_for('hora.estoque_lista'))

    return render_template(
        'hora/estoque_chassi_detalhe.html',
        moto=moto,
        rastreio=rastreio,
    )
