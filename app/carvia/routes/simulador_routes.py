"""
Rotas do Simulador 3D de Carga de Motos

Dois modos:
- Livre: usuario seleciona veiculo + N modelos com quantidades
- Embarque: carrega motos reais das NFs do embarque

APIs JSON fornecem dados para o bin-packing client-side (Three.js).
"""

import logging
from collections import defaultdict

from flask import render_template, jsonify
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

    @bp.route('/api/simulador-carga/embarque/<int:embarque_id>')
    @login_required
    def api_simulador_embarque(embarque_id):
        """Retorna dados de um embarque para simulacao"""
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado'}), 403

        from app.embarques.models import Embarque
        embarque = Embarque.query.get_or_404(embarque_id)

        return jsonify(_resolver_dados_embarque(embarque))


def _resolver_dados_embarque(embarque):
    """Resolve veiculo e motos de um embarque para o simulador.

    1. Veiculo: embarque.modalidade → Veiculo.nome
    2. Motos: EmbarqueItem.nota_fiscal → CarviaNf → CarviaNfVeiculo.modelo
       → match contra CarviaModeloMoto.regex_pattern
    """
    from app import db
    from app.veiculos.models import Veiculo
    from app.carvia.models.config_moto import CarviaModeloMoto
    from app.carvia.models.documentos import CarviaNf, CarviaNfVeiculo
    from app.embarques.models import EmbarqueItem

    # 1. Resolver veiculo
    veiculo_data = None
    if embarque.modalidade:
        veiculo = Veiculo.query.filter(
            db.func.upper(Veiculo.nome) == embarque.modalidade.upper()
        ).first()
        if veiculo and veiculo.tem_dimensoes_bau():
            veiculo_data = {
                'nome': veiculo.nome,
                'peso_maximo': veiculo.peso_maximo,
                'comprimento_bau': veiculo.comprimento_bau,
                'largura_bau': veiculo.largura_bau,
                'altura_bau': veiculo.altura_bau,
            }

    # 2. Resolver motos via NFs do embarque
    itens = EmbarqueItem.query.filter_by(
        embarque_id=embarque.id, status='ativo'
    ).all()

    # Coletar NFs unicas do embarque
    nfs_numeros = set()
    for item in itens:
        if item.nota_fiscal and item.nota_fiscal.strip():
            nfs_numeros.add(item.nota_fiscal.strip())

    # Buscar veiculos (chassis) das NFs CarVia
    modelos_ativos = CarviaModeloMoto.query.filter_by(ativo=True).all()
    contagem_modelos = defaultdict(int)  # {modelo_id: quantidade}
    items_sem_modelo = 0
    peso_total = 0.0

    if nfs_numeros:
        # Buscar CarviaNfs pelo numero
        carvia_nfs = CarviaNf.query.filter(
            CarviaNf.numero_nf.in_(list(nfs_numeros))
        ).all()

        nf_ids = [nf.id for nf in carvia_nfs]
        if nf_ids:
            veiculos_nf = CarviaNfVeiculo.query.filter(
                CarviaNfVeiculo.nf_id.in_(nf_ids)
            ).all()

            for veiculo_nf in veiculos_nf:
                modelo_match = _match_modelo_veiculo(
                    veiculo_nf.modelo, modelos_ativos
                )
                if modelo_match:
                    contagem_modelos[modelo_match.id] += 1
                    if modelo_match.peso_medio:
                        peso_total += float(modelo_match.peso_medio)
                else:
                    items_sem_modelo += 1

    # Montar lista de motos com dimensoes
    modelos_dict = {m.id: m for m in modelos_ativos}
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

    return {
        'embarque_id': embarque.id,
        'embarque_numero': embarque.numero,
        'veiculo': veiculo_data,
        'motos': motos,
        'peso_total': round(peso_total, 2),
        'items_sem_modelo': items_sem_modelo,
        'erro': 'veiculo_sem_dimensoes' if not veiculo_data else None,
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
