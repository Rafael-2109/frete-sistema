"""
Rotas do Simulador 3D de Carga de Motos

Dois modos:
- Livre: usuario seleciona veiculo + N modelos com quantidades
- Embarque: carrega motos reais das NFs do embarque

APIs JSON fornecem dados para o bin-packing client-side (Three.js).
"""

import logging
from collections import defaultdict

from flask import render_template, jsonify, request
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)


def register_simulador_routes(bp):
    """Registra rotas do simulador 3D de carga"""

    # --- Paginas HTML ---

    @bp.route('/simulador-carga')
    @login_required
    def simulador_carga():
        """Pagina do simulador livre — usuario escolhe veiculo + motos"""
        if not getattr(current_user, 'sistema_carvia', False):
            from flask import abort
            abort(403)
        return render_template('carvia/simulador/simulador_livre.html')

    @bp.route('/embarques/<int:embarque_id>/simulador-carga')
    @login_required
    def simulador_carga_embarque(embarque_id):
        """Pagina do simulador com dados reais do embarque"""
        if not getattr(current_user, 'sistema_carvia', False):
            from flask import abort
            abort(403)

        import json
        from app.embarques.models import Embarque

        embarque = Embarque.query.get_or_404(embarque_id)
        dados_embarque = _resolver_dados_embarque(embarque)

        return render_template(
            'carvia/simulador/simulador_embarque.html',
            embarque=embarque,
            dados_json=json.dumps(dados_embarque, ensure_ascii=False),
        )

    @bp.route('/simulador-carga/rota')
    @login_required
    def simulador_carga_rota():
        """Simulador livre PRE-PREENCHIDO com as motos dos lotes de uma rota do mapa.

        Params:
          - lotes[]=...   separacao_lote_id (CarVia = 'CARVIA-NF-{nf_id}')
          - rota_id=...   RotaSalva (usa seus lotes + veiculo_id se nao vierem)
          - veiculo_id=.. override do bau

        Modo livre editavel: as linhas vem preenchidas mas o usuario pode ajustar.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            from flask import abort
            abort(403)

        import json

        lotes = request.args.getlist('lotes[]')
        rota_id = request.args.get('rota_id')
        veiculo_id = request.args.get('veiculo_id')

        if rota_id:
            from app.carteira.models import RotaSalva
            rota = RotaSalva.query.get(rota_id)
            if rota:
                if rota.lotes and not lotes:
                    lotes = list(rota.lotes)
                if not veiculo_id and rota.veiculo_id:
                    veiculo_id = rota.veiculo_id

        prefill = _resolver_prefill_rota(lotes, veiculo_id)
        return render_template(
            'carvia/simulador/simulador_livre.html',
            prefill_json=json.dumps(prefill, ensure_ascii=False),
        )

    # --- APIs JSON ---

    @bp.route('/api/simulador-carga/catalogo')
    @login_required
    def api_simulador_catalogo():
        """Retorna veiculos com dimensoes + modelos moto ativos"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.veiculos.models import Veiculo
        from app.carvia.models.config_moto import CarviaModeloMoto

        veiculos = Veiculo.query.order_by(Veiculo.peso_maximo.asc()).all()
        modelos = CarviaModeloMoto.query.filter_by(ativo=True).order_by(
            CarviaModeloMoto.nome
        ).all()

        return jsonify({
            'veiculos': [
                {
                    'id': v.id,
                    'nome': v.nome,
                    'peso_maximo': v.peso_maximo,
                    'comprimento_bau': v.comprimento_bau,
                    'largura_bau': v.largura_bau,
                    'altura_bau': v.altura_bau,
                    'tem_dimensoes_bau': v.tem_dimensoes_bau(),
                }
                for v in veiculos
            ],
            'modelos_moto': [
                {
                    'id': m.id,
                    'nome': m.nome,
                    'comprimento': float(m.comprimento),
                    'largura': float(m.largura),
                    'altura': float(m.altura),
                    'peso_medio': float(m.peso_medio) if m.peso_medio else None,
                }
                for m in modelos
            ],
        })

    @bp.route('/api/simulador-carga/pallets-por-separacao')
    @login_required
    def api_simulador_pallets_por_separacao():
        """Monta os pallets PBR de conservas Nacom de uma Separacao (Camada 1).

        Params: lote (obrigatorio), modo (A-D), separado (0/1), overbooking (0-0.5).
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.carteira.services.palletizacao_service import montar_pallets_da_separacao

        lote = request.args.get('lote', type=str)
        if not lote:
            return jsonify({'erro': 'parametro lote obrigatorio'}), 400
        modo = request.args.get('modo', 'A', type=str)
        separado = request.args.get('separado', '0') in ('1', 'true', 'True')
        try:
            overbooking = float(request.args.get('overbooking', 0) or 0)
        except (TypeError, ValueError):
            overbooking = 0.0

        out = montar_pallets_da_separacao(
            lote, modo=modo, separado_por_pallet=separado, overbooking_pct=overbooking)
        return jsonify(out)

    @bp.route('/api/simulador-carga/embarque/<int:embarque_id>')
    @login_required
    def api_simulador_embarque(embarque_id):
        """Retorna dados de um embarque para simulacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.embarques.models import Embarque
        embarque = Embarque.query.get_or_404(embarque_id)

        return jsonify(_resolver_dados_embarque(embarque))

    @bp.route('/api/simulador-carga/nfs-pendentes')
    @login_required
    def api_simulador_nfs_pendentes():
        """NFs CarVia ainda nao entregues — alimentam o seletor do simulador livre."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.monitoramento.models import EntregaMonitorada

        entregas = EntregaMonitorada.query.filter_by(
            entregue=False, origem='CARVIA'
        ).order_by(EntregaMonitorada.data_faturamento.desc()).limit(500).all()

        return jsonify({
            'nfs': [
                {
                    'numero_nf': e.numero_nf,
                    'cliente': e.cliente,
                    'municipio': e.municipio,
                    'uf': e.uf,
                    'data': e.data_faturamento.strftime('%d/%m/%Y') if e.data_faturamento else None,
                }
                for e in entregas
            ]
        })

    @bp.route('/api/simulador-carga/motos-por-nf')
    @login_required
    def api_simulador_motos_por_nf():
        """Resolve as motos de uma ou mais NFs (CSV em ?nfs=12345,67890)."""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        raw = request.args.get('nfs', '')
        numeros = [n.strip() for n in raw.split(',') if n.strip()]
        motos, peso_total, items_sem_modelo = _resolver_motos_de_nfs(numeros_nf=numeros)
        return jsonify({
            'motos': motos,
            'peso_total': peso_total,
            'items_sem_modelo': items_sem_modelo,
        })

    @bp.route('/api/simulador-carga/veiculo/<int:veiculo_id>/dimensoes', methods=['POST'])
    @login_required
    def api_simulador_salvar_dimensoes(veiculo_id):
        """Persiste as dimensoes do bau editadas no simulador no cadastro do Veiculo.

        O override de dimensoes do simulador e' so client-side; este endpoint grava
        comprimento/largura/altura_bau (cm) no `Veiculo` para reuso em proximas cargas.
        """
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app import db
        from app.veiculos.models import Veiculo

        veiculo = Veiculo.query.get_or_404(veiculo_id)
        data = request.get_json(silent=True) or {}

        def _positivo(valor):
            try:
                num = float(valor)
            except (TypeError, ValueError):
                return None
            return num if num > 0 else None

        comp = _positivo(data.get('comprimento_bau'))
        larg = _positivo(data.get('largura_bau'))
        alt = _positivo(data.get('altura_bau'))
        if not (comp and larg and alt):
            return jsonify({
                'erro': 'Dimensões inválidas — informe comprimento, largura e altura (> 0).'
            }), 400

        veiculo.comprimento_bau = comp
        veiculo.largura_bau = larg
        veiculo.altura_bau = alt
        db.session.commit()

        return jsonify({
            'sucesso': True,
            'veiculo': {
                'id': veiculo.id,
                'nome': veiculo.nome,
                'peso_maximo': veiculo.peso_maximo,
                'comprimento_bau': veiculo.comprimento_bau,
                'largura_bau': veiculo.largura_bau,
                'altura_bau': veiculo.altura_bau,
                'tem_dimensoes_bau': veiculo.tem_dimensoes_bau(),
            },
        })


def _resolver_dados_embarque(embarque):
    """Resolve veiculo e motos de um embarque para o simulador.

    1. Veiculo: embarque.modalidade → Veiculo.nome
    2. Motos: EmbarqueItem.nota_fiscal → CarviaNf → CarviaNfVeiculo.modelo
       → match contra CarviaModeloMoto.regex_pattern
    """
    from app.embarques.models import EmbarqueItem

    veiculo_data = _veiculo_data_por_nome(embarque.modalidade)

    itens = EmbarqueItem.query.filter_by(
        embarque_id=embarque.id, status='ativo'
    ).all()
    nfs_numeros = {
        item.nota_fiscal.strip()
        for item in itens
        if item.nota_fiscal and item.nota_fiscal.strip()
    }

    motos, peso_total, items_sem_modelo = _resolver_motos_de_nfs(numeros_nf=nfs_numeros)

    # Conservas Nacom: monta os pallets dos lotes Nacom (LOTE_*) do mesmo embarque.
    from app.carteira.services.palletizacao_service import montar_pallets_da_separacao
    lotes_nacom = {
        it.separacao_lote_id for it in itens
        if (it.separacao_lote_id or '').startswith('LOTE_')
    }
    pallets = []
    for lote in lotes_nacom:
        pallets.extend(montar_pallets_da_separacao(lote)['pallets'])

    return {
        'embarque_id': embarque.id,
        'embarque_numero': embarque.numero,
        'veiculo': veiculo_data,
        'motos': motos,
        'pallets': pallets,
        'peso_total': peso_total,
        'items_sem_modelo': items_sem_modelo,
        'erro': 'veiculo_sem_dimensoes' if not veiculo_data else None,
    }


def _resolver_prefill_rota(lotes, veiculo_id=None):
    """Resolve veiculo + motos para pre-preencher o simulador a partir dos
    lotes de uma rota do mapa.

    Formatos de lote suportados (o mapa monta CarVia via cotacao/pedido,
    NAO via NF — ver app/carteira/services/mapa_service.py):
      - 'CARVIA-NF-{nf_id}'  -> id de CarviaNf direto
      - 'CARVIA-PED-{ped_id}' -> CarviaPedido -> itens (numero_nf / modelo)
      - 'CARVIA-{cot_id}'    -> CarviaCotacao -> pedidos -> itens
      - separacao_lote_id NACOM -> NF via Separacao.numero_nf

    Pedidos CarVia faturados resolvem as motos REAIS pelas NFs
    (CarviaPedidoItem.numero_nf -> CarviaNfVeiculo / chassi). Itens ainda
    sem NF caem no fallback direto (modelo_moto_id + quantidade) para o
    simulador abrir preenchido mesmo antes do faturamento.
    """
    nf_ids = set()
    numeros_nf = set()
    pedido_ids = set()
    cotacao_ids = set()
    lotes_nacom = []

    for lote in lotes or []:
        texto = str(lote)
        if texto.startswith('CARVIA-NF-'):
            try:
                nf_ids.add(int(texto.rsplit('-', 1)[1]))
            except (ValueError, IndexError):
                pass
        elif texto.startswith('CARVIA-PED-'):
            try:
                pedido_ids.add(int(texto.rsplit('-', 1)[1]))
            except (ValueError, IndexError):
                pass
        elif texto.startswith('CARVIA-'):
            try:
                cotacao_ids.add(int(texto.rsplit('-', 1)[1]))
            except (ValueError, IndexError):
                pass
        else:
            lotes_nacom.append(texto)

    # Pedidos/cotacoes CarVia -> itens (numero_nf faturado OU modelo direto)
    itens_diretos = []  # [(modelo_moto_id, quantidade)] de itens ainda sem NF
    if pedido_ids or cotacao_ids:
        from app.carvia.models.cotacao import CarviaPedido, CarviaPedidoItem

        ped_ids = set(pedido_ids)
        if cotacao_ids:
            rows = CarviaPedido.query.filter(
                CarviaPedido.cotacao_id.in_(list(cotacao_ids))
            ).with_entities(CarviaPedido.id).all()
            ped_ids.update(r[0] for r in rows)

        if ped_ids:
            itens = CarviaPedidoItem.query.filter(
                CarviaPedidoItem.pedido_id.in_(list(ped_ids))
            ).all()
            for it in itens:
                if it.numero_nf and str(it.numero_nf).strip():
                    numeros_nf.add(str(it.numero_nf).strip())
                elif it.modelo_moto_id:
                    itens_diretos.append((it.modelo_moto_id, it.quantidade or 0))

    if lotes_nacom:
        from app.separacao.models import Separacao
        rows = Separacao.query.filter(
            Separacao.separacao_lote_id.in_(lotes_nacom),
            Separacao.numero_nf.isnot(None),
        ).with_entities(Separacao.numero_nf).all()
        numeros_nf.update(r[0] for r in rows if r[0])

    motos, peso_total, items_sem_modelo = _resolver_motos_de_nfs(
        numeros_nf=numeros_nf, nf_ids=nf_ids, itens_diretos=itens_diretos
    )
    return {
        'veiculo': _veiculo_data_por_id(veiculo_id),
        'motos': motos,
        'peso_total': peso_total,
        'items_sem_modelo': items_sem_modelo,
    }


def _resolver_motos_de_nfs(numeros_nf=None, nf_ids=None, itens_diretos=None):
    """Resolve a contagem de motos por modelo a partir de numeros de NF e/ou
    ids de CarviaNf. Devolve (lista_motos, peso_total, items_sem_modelo).

    Por NF, a fonte das motos e (nesta ordem, sem dupla contagem):
      1. `carvia_nf_veiculos` (1 chassi por linha, match textual do modelo) —
         contagem exata; preserva NFs que ja tem chassis.
      2. `carvia_nf_itens.modelo_moto_id` + `quantidade` — fonte do peso cubado
         (MotoRecognitionService). SO para NFs SEM chassi (PDF_DANFE: tem o item
         com modelo, sem chassis). Itens sem modelo sao ignorados.

    Helper unico compartilhado por embarque (numeros_nf), simulador livre
    (NF nao entregue) e rota do mapa (nf_ids diretos + numeros_nf NACOM).

    `itens_diretos` = [(modelo_moto_id, quantidade)] de itens de pedido CarVia
    ainda sem NF (fallback pre-faturamento) — somados a contagem por modelo.
    """
    from app.carvia.models.config_moto import CarviaModeloMoto
    from app.carvia.models.documentos import CarviaNf, CarviaNfItem, CarviaNfVeiculo

    modelos_ativos = CarviaModeloMoto.query.filter_by(ativo=True).all()
    modelos_dict = {m.id: m for m in modelos_ativos}
    contagem_modelos = defaultdict(int)  # {modelo_id: quantidade}
    items_sem_modelo = 0
    peso_total = 0.0

    ids = set(nf_ids or [])
    numeros = {str(n).strip() for n in (numeros_nf or []) if n and str(n).strip()}
    if numeros:
        carvia_nfs = CarviaNf.query.filter(
            CarviaNf.numero_nf.in_(list(numeros))
        ).all()
        ids.update(nf.id for nf in carvia_nfs)

    if ids:
        ids_list = list(ids)
        # FONTE PRIMARIA: chassis (carvia_nf_veiculos) — 1 linha por moto fisica,
        # contagem exata. Preserva o comportamento das NFs que ja tem chassis.
        veiculos_nf = CarviaNfVeiculo.query.filter(
            CarviaNfVeiculo.nf_id.in_(ids_list)
        ).all()
        nfs_com_chassi = set()
        for veiculo_nf in veiculos_nf:
            nfs_com_chassi.add(veiculo_nf.nf_id)
            modelo_match = _match_modelo_veiculo(veiculo_nf.modelo, modelos_ativos)
            if modelo_match:
                contagem_modelos[modelo_match.id] += 1
                if modelo_match.peso_medio:
                    peso_total += float(modelo_match.peso_medio)
            else:
                items_sem_modelo += 1

        # FONTE ALTERNATIVA: carvia_nf_itens (modelo_moto_id + quantidade) — mesma
        # fonte do peso cubado (MotoRecognitionService). SO p/ NFs SEM chassi (a
        # maioria, importadas por PDF_DANFE: tem o item com modelo, sem chassis).
        # Itens sem modelo sao ignorados (consistente com calcular_peso_cubado_nf).
        itens_nf = CarviaNfItem.query.filter(
            CarviaNfItem.nf_id.in_(ids_list),
            CarviaNfItem.modelo_moto_id.isnot(None),
        ).all()
        for it in itens_nf:
            if it.nf_id in nfs_com_chassi:
                continue  # ja contada (exata) pelos chassis
            qtd = int(round(float(it.quantidade or 0)))
            if qtd <= 0:
                continue
            m = modelos_dict.get(it.modelo_moto_id)
            if m:
                contagem_modelos[m.id] += qtd
                if m.peso_medio:
                    peso_total += float(m.peso_medio) * qtd
            else:
                items_sem_modelo += qtd  # modelo inativo

    # Fallback: itens de pedido CarVia sem NF (modelo_moto_id + quantidade)
    for modelo_id, qtd in (itens_diretos or []):
        qtd = int(qtd or 0)
        if qtd <= 0:
            continue
        m = modelos_dict.get(modelo_id)
        if m:
            contagem_modelos[m.id] += qtd
            if m.peso_medio:
                peso_total += float(m.peso_medio) * qtd
        else:
            items_sem_modelo += qtd

    motos = []
    for modelo_id, qtd in contagem_modelos.items():
        m = modelos_dict[modelo_id]
        motos.append({
            'modelo_id': m.id,
            'modelo_nome': m.nome,
            'quantidade': qtd,
            'comprimento': float(m.comprimento),
            'largura': float(m.largura),
            'altura': float(m.altura),
            'peso_medio': float(m.peso_medio) if m.peso_medio else None,
        })

    return motos, round(peso_total, 2), items_sem_modelo


def _veiculo_data_por_nome(nome_modalidade):
    """Resolve dados do bau de um veiculo pelo nome (embarque.modalidade)."""
    from app import db
    from app.veiculos.models import Veiculo

    if not nome_modalidade:
        return None
    veiculo = Veiculo.query.filter(
        db.func.upper(Veiculo.nome) == nome_modalidade.upper()
    ).first()
    return _veiculo_data(veiculo)


def _veiculo_data_por_id(veiculo_id):
    """Resolve dados do bau de um veiculo pelo id (RotaSalva.veiculo_id ou query)."""
    from app.veiculos.models import Veiculo

    if not veiculo_id:
        return None
    try:
        veiculo_id = int(veiculo_id)
    except (ValueError, TypeError):
        return None
    return _veiculo_data(Veiculo.query.get(veiculo_id))


def _veiculo_data(veiculo):
    """Serializa o bau de um Veiculo (ou None se sem dimensoes cadastradas)."""
    if not veiculo or not veiculo.tem_dimensoes_bau():
        return None
    return {
        'id': veiculo.id,
        'nome': veiculo.nome,
        'peso_maximo': veiculo.peso_maximo,
        'comprimento_bau': veiculo.comprimento_bau,
        'largura_bau': veiculo.largura_bau,
        'altura_bau': veiculo.altura_bau,
    }


def _match_modelo_veiculo(texto_modelo, modelos_ativos):
    """Tenta matchear texto de modelo de veiculo com CarviaModeloMoto.

    Usa regex_pattern e nome exato, similar ao MotoRecognitionService.
    """
    import re

    if not texto_modelo:
        return None

    texto_upper = texto_modelo.upper().strip()

    for modelo in modelos_ativos:
        # Match por regex_pattern customizado
        if modelo.regex_pattern:
            try:
                if re.search(modelo.regex_pattern, texto_upper, re.IGNORECASE):
                    return modelo
            except re.error:
                pass

        # Match por nome com word boundary
        nome_escaped = re.escape(modelo.nome.upper())
        if re.search(
            r'(?<![A-Za-z])' + nome_escaped + r'(?![A-Za-z])', texto_upper
        ):
            return modelo

    return None
