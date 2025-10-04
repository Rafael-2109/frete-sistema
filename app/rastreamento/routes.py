"""
🚚 ROTAS DO SISTEMA DE RASTREAMENTO GPS
Endpoints para transportadores e monitoramento interno
"""

from flask import render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.rastreamento import rastreamento_bp
from app.rastreamento.models import RastreamentoEmbarque, PingGPS, LogRastreamento, ConfiguracaoRastreamento
from app.rastreamento.services.gps_service import GPSService
from app.rastreamento.services.qrcode_service import QRCodeService
from app.embarques.models import Embarque
from app.monitoramento.models import EntregaMonitorada
from app import db, csrf
from datetime import datetime, timedelta
import json
from app.utils.timezone import agora_brasil


# ========================================
# ROTAS PÚBLICAS (SEM LOGIN) - TRANSPORTADOR
# ========================================

@rastreamento_bp.route('/aceite/<token>', methods=['GET'])
def aceite_lgpd(token):
    """
    Tela de aceite LGPD - Primeira tela que o transportador vê
    Acesso via QR Code escaneado
    """
    # Buscar rastreamento pelo token
    rastreamento = RastreamentoEmbarque.query.filter_by(token_acesso=token).first()

    if not rastreamento:
        return render_template('rastreamento/erro.html',
                             mensagem="QR Code inválido ou expirado."), 404

    # Verificar se já aceitou
    if rastreamento.aceite_lgpd:
        return redirect(url_for('rastreamento.rastrear', token=token))

    # Verificar se expirou
    if rastreamento.token_expiracao and agora_brasil() > rastreamento.token_expiracao:
        rastreamento.status = 'EXPIRADO'
        db.session.commit()
        return render_template('rastreamento/erro.html',
                             mensagem="Este link de rastreamento expirou."), 410

    # Buscar dados do embarque para exibir
    embarque = rastreamento.embarque
    config = ConfiguracaoRastreamento.get_config()

    return render_template('rastreamento/aceite_lgpd.html',
                          rastreamento=rastreamento,
                          embarque=embarque,
                          config=config,
                          versao_termo=config.versao_termo_lgpd)


@rastreamento_bp.route('/aceite/<token>', methods=['POST'])
@csrf.exempt
def processar_aceite_lgpd(token):
    """
    Processa o aceite do termo LGPD
    ⚠️ CSRF desabilitado: Rota pública para transportadores externos via QR Code
    Segurança garantida pelo token único de acesso
    """
    rastreamento = RastreamentoEmbarque.query.filter_by(token_acesso=token).first()

    if not rastreamento:
        return jsonify({'success': False, 'message': 'Token inválido'}), 404

    # Verificar se já aceitou
    if rastreamento.aceite_lgpd:
        return jsonify({'success': True, 'redirect': url_for('rastreamento.rastrear', token=token)})

    try:
        # Coletar dados do aceite
        rastreamento.aceite_lgpd = True
        rastreamento.aceite_lgpd_em = agora_brasil()
        rastreamento.aceite_lgpd_ip = request.remote_addr
        rastreamento.aceite_lgpd_user_agent = request.headers.get('User-Agent', '')[:500]
        rastreamento.status = 'ATIVO'
        rastreamento.rastreamento_iniciado_em = agora_brasil()

        # Registrar log
        rastreamento.registrar_log(
            evento='ACEITE_LGPD',
            detalhes=json.dumps({
                'ip': rastreamento.aceite_lgpd_ip,
                'user_agent': rastreamento.aceite_lgpd_user_agent[:100]
            })
        )

        db.session.commit()

        current_app.logger.info(f"Aceite LGPD registrado para embarque #{rastreamento.embarque_id}")

        return jsonify({
            'success': True,
            'message': 'Termo aceito com sucesso!',
            'redirect': url_for('rastreamento.rastrear', token=token)
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao processar aceite LGPD: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro ao processar aceite: {str(e)}'}), 500


@rastreamento_bp.route('/rastrear/<token>', methods=['GET'])
def rastrear(token):
    """
    Tela principal de rastreamento - Envia pings GPS a cada 2 minutos
    """
    rastreamento = RastreamentoEmbarque.query.filter_by(token_acesso=token).first()

    if not rastreamento:
        return render_template('rastreamento/erro.html',
                             mensagem="Link inválido."), 404

    # Verificar se aceitou LGPD
    if not rastreamento.aceite_lgpd:
        return redirect(url_for('rastreamento.aceite_lgpd', token=token))

    # Verificar status
    if rastreamento.status in ['CANCELADO', 'EXPIRADO']:
        return render_template('rastreamento/erro.html',
                             mensagem="Rastreamento não está mais ativo."), 410

    embarque = rastreamento.embarque
    config = ConfiguracaoRastreamento.get_config()

    # Obter coordenadas do destino
    coord_destino = GPSService.obter_coordenadas_embarque(embarque)

    # Pegar último ping para exibir última posição
    ultimo_ping = rastreamento.pings.first()

    return render_template('rastreamento/rastreamento_ativo.html',
                          rastreamento=rastreamento,
                          embarque=embarque,
                          config=config,
                          coord_destino=coord_destino,
                          ultimo_ping=ultimo_ping,
                          intervalo_ping=config.intervalo_ping_segundos)


@rastreamento_bp.route('/api/ping/<token>', methods=['POST'])
@csrf.exempt
def receber_ping_gps(token):
    """
    API para receber pings GPS do dispositivo
    Chamada a cada 2 minutos pelo JavaScript
    ⚠️ CSRF desabilitado: API pública para transportadores externos
    """
    rastreamento = RastreamentoEmbarque.query.filter_by(token_acesso=token).first()

    if not rastreamento:
        return jsonify({'success': False, 'message': 'Token inválido'}), 404

    if not rastreamento.aceite_lgpd or rastreamento.status != 'ATIVO':
        return jsonify({'success': False, 'message': 'Rastreamento não está ativo'}), 403

    try:
        # Extrair dados do ping
        data = request.get_json()

        latitude = data.get('latitude')
        longitude = data.get('longitude')
        precisao = data.get('precisao')
        altitude = data.get('altitude')
        velocidade = data.get('velocidade')
        direcao = data.get('direcao')
        bateria_nivel = data.get('bateria_nivel')
        bateria_carregando = data.get('bateria_carregando', False)
        timestamp_dispositivo = data.get('timestamp')

        # Validar coordenadas
        if not GPSService.validar_coordenadas(latitude, longitude):
            return jsonify({'success': False, 'message': 'Coordenadas inválidas'}), 400

        # Obter coordenadas do destino
        coord_destino = GPSService.obter_coordenadas_embarque(rastreamento.embarque)
        coord_atual = (latitude, longitude)

        # Calcular distância até o destino
        distancia_destino = None
        if coord_destino:
            distancia_destino = GPSService.calcular_distancia(coord_atual, coord_destino, 'metros')

        # Criar registro de ping
        ping = PingGPS(
            rastreamento_id=rastreamento.id,
            latitude=latitude,
            longitude=longitude,
            precisao=precisao,
            altitude=altitude,
            velocidade=velocidade,
            direcao=direcao,
            distancia_destino=distancia_destino,
            bateria_nivel=bateria_nivel,
            bateria_carregando=bateria_carregando,
            timestamp_dispositivo=datetime.fromisoformat(timestamp_dispositivo) if timestamp_dispositivo else None
        )
        db.session.add(ping)

        # Atualizar rastreamento
        rastreamento.ultimo_ping_em = agora_brasil()

        # ✅ NOVO: Detectar proximidade de TODAS entregas pendentes
        from app.rastreamento.services.entrega_rastreada_service import EntregaRastreadaService

        entregas_proximas = EntregaRastreadaService.detectar_entrega_proxima(
            rastreamento.id,
            latitude,
            longitude
        )

        # Manter lógica antiga para compatibilidade (distância do primeiro destino)
        config = ConfiguracaoRastreamento.get_config()
        chegou_proximo = len(entregas_proximas) > 0

        if distancia_destino and distancia_destino <= config.distancia_chegada_metros:
            if rastreamento.status != 'CHEGOU_DESTINO':
                rastreamento.status = 'CHEGOU_DESTINO'
                rastreamento.chegou_destino_em = agora_brasil()
                rastreamento.distancia_minima_atingida = distancia_destino

                # Registrar log
                rastreamento.registrar_log(
                    evento='CHEGADA_DESTINO',
                    detalhes=json.dumps({
                        'distancia_metros': distancia_destino,
                        'latitude': latitude,
                        'longitude': longitude,
                        'entregas_proximas': len(entregas_proximas)
                    })
                )

                current_app.logger.info(
                    f"Embarque #{rastreamento.embarque_id} chegou próximo de {len(entregas_proximas)} entrega(s)"
                )

            # Atualizar distância mínima se for menor
            if rastreamento.distancia_minima_atingida is None or distancia_destino < rastreamento.distancia_minima_atingida:
                rastreamento.distancia_minima_atingida = distancia_destino

        db.session.commit()

        # ✅ NOVO: Preparar lista de entregas próximas para o frontend
        entregas_proximas_json = [
            {
                'id': ep['entrega'].id,
                'descricao': ep['entrega'].descricao_completa,
                'descricao_com_endereco': ep['entrega'].descricao_com_endereco,
                'cliente': ep['entrega'].cliente,
                'cidade': ep['entrega'].cidade,
                'uf': ep['entrega'].uf,
                'numero_nf': ep['entrega'].numero_nf,
                'distancia': ep['distancia'],
                'distancia_formatada': GPSService.formatar_distancia(ep['distancia'])
            }
            for ep in entregas_proximas
        ]

        # ✅ NOVO: Obter estatísticas das entregas
        stats = EntregaRastreadaService.obter_estatisticas_entregas(rastreamento.id)

        return jsonify({
            'success': True,
            'message': 'Ping recebido com sucesso',
            'data': {
                'distancia_destino': distancia_destino,
                'distancia_formatada': GPSService.formatar_distancia(distancia_destino),
                'chegou_proximo': chegou_proximo,
                'status': rastreamento.status,
                'total_pings': rastreamento.pings.count(),
                # ✅ NOVO: Dados das entregas individuais
                'entregas_proximas': entregas_proximas_json,
                'total_entregas': stats['total'],
                'entregas_pendentes': stats['pendentes'],
                'entregas_entregues': stats['entregues'],
                'pode_finalizar': chegou_proximo  # Libera botão de confirmar entrega
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao processar ping GPS: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500


@rastreamento_bp.route('/upload_canhoto/<token>', methods=['GET'])
def tela_upload_canhoto(token):
    """
    Tela para upload do canhoto de entrega
    Exibida quando transportador clica em "Entreguei o Pedido"
    """
    rastreamento = RastreamentoEmbarque.query.filter_by(token_acesso=token).first()

    if not rastreamento:
        return render_template('rastreamento/erro.html',
                             mensagem="Link inválido."), 404

    if not rastreamento.aceite_lgpd:
        return redirect(url_for('rastreamento.aceite_lgpd', token=token))

    embarque = rastreamento.embarque

    return render_template('rastreamento/upload_canhoto.html',
                          rastreamento=rastreamento,
                          embarque=embarque,
                          token=token)


@rastreamento_bp.route('/api/upload_canhoto/<token>', methods=['POST'])
@csrf.exempt
def processar_upload_canhoto(token):
    """
    API para processar upload do canhoto de entrega
    ⚠️ CSRF desabilitado: API pública para transportadores externos

    REGRA DE NEGÓCIO:
    - Exige seleção de entrega_id (qual NF está sendo entregue)
    - Salva canhoto individual por entrega
    - Atualiza EntregaRastreada + EntregaMonitorada
    - Finaliza rastreamento apenas quando TODAS entregas concluídas
    """
    rastreamento = RastreamentoEmbarque.query.filter_by(token_acesso=token).first()

    if not rastreamento:
        return jsonify({'success': False, 'message': 'Token inválido'}), 404

    # ✅ NOVO: Verificar qual entrega está sendo comprovada
    entrega_id = request.form.get('entrega_id')

    if not entrega_id:
        return jsonify({
            'success': False,
            'message': 'Selecione a entrega que está comprovando'
        }), 400

    # ✅ NOVO: Buscar entrega rastreada
    from app.rastreamento.models import EntregaRastreada
    entrega = EntregaRastreada.query.get(entrega_id)

    if not entrega or entrega.rastreamento_id != rastreamento.id:
        return jsonify({'success': False, 'message': 'Entrega inválida'}), 404

    if entrega.status == 'ENTREGUE':
        return jsonify({'success': False, 'message': 'Esta entrega já foi confirmada'}), 400

    if 'canhoto' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'}), 400

    file = request.files['canhoto']
    if not file or not file.filename:
        return jsonify({'success': False, 'message': 'Arquivo inválido'}), 400

    # Validar extensão
    extensao = file.filename.split('.')[-1].lower()
    if extensao not in ['jpg', 'jpeg', 'png', 'pdf']:
        return jsonify({'success': False, 'message': 'Apenas JPG, PNG ou PDF'}), 400

    try:
        # Obter coordenadas do upload
        data = request.form
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        # ✅ Salvar arquivo usando MESMO sistema do monitoramento
        from app.utils.file_storage import get_file_storage
        storage = get_file_storage()
        file_path = storage.save_file(
            file=file,
            folder='canhotos_rastreamento',  # Mesma pasta do monitoramento
            allowed_extensions=['jpg', 'jpeg', 'png', 'pdf']
        )

        if not file_path:
            return jsonify({'success': False, 'message': 'Erro ao salvar arquivo'}), 500

        # ✅ Calcular distância do cliente no momento da entrega
        distancia_entrega = None
        if latitude and longitude and GPSService.validar_coordenadas(latitude, longitude):
            if entrega.tem_coordenadas:
                distancia_entrega = GPSService.calcular_distancia(
                    (float(latitude), float(longitude)),
                    (entrega.destino_latitude, entrega.destino_longitude),
                    'metros'
                )

        # ✅ Atualizar APENAS esta entrega
        entrega.canhoto_arquivo = file_path
        entrega.canhoto_latitude = float(latitude) if latitude and GPSService.validar_coordenadas(latitude, longitude) else None
        entrega.canhoto_longitude = float(longitude) if longitude and GPSService.validar_coordenadas(latitude, longitude) else None
        entrega.entregue_em = agora_brasil()
        entrega.entregue_distancia_metros = distancia_entrega
        entrega.status = 'ENTREGUE'

        # Registrar log
        rastreamento.registrar_log(
            evento='UPLOAD_CANHOTO',
            detalhes=json.dumps({
                'entrega_id': entrega.id,
                'nf': entrega.numero_nf,
                'pedido': entrega.pedido,
                'cliente': entrega.cliente,
                'arquivo': file_path,
                'distancia_metros': distancia_entrega
            })
        )

        # ✅ Atualizar EntregaMonitorada correspondente (se existir)
        if entrega.item.separacao_lote_id:
            entrega_mon = EntregaMonitorada.query.filter_by(
                separacao_lote_id=entrega.item.separacao_lote_id
            ).first()

            if entrega_mon:
                entrega_mon.canhoto_arquivo = file_path
                entrega_mon.entregue = True
                entrega_mon.data_hora_entrega_realizada = agora_brasil()
                current_app.logger.info(
                    f"✅ EntregaMonitorada atualizada: NF {entrega_mon.numero_nf}"
                )

        # ✅ Verificar se TODAS entregas foram concluídas
        from app.rastreamento.services.entrega_rastreada_service import EntregaRastreadaService

        todas_concluidas = EntregaRastreadaService.verificar_todas_entregas_concluidas(
            rastreamento.id
        )

        if todas_concluidas:
            rastreamento.status = 'ENTREGUE'
            rastreamento.rastreamento_finalizado_em = agora_brasil()
            current_app.logger.info(
                f"✅ TODAS entregas concluídas - Rastreamento finalizado para embarque #{rastreamento.embarque_id}"
            )

        # Contar entregas restantes
        entregas_pendentes = rastreamento.entregas.filter(
            EntregaRastreada.status.in_(['PENDENTE', 'EM_ROTA', 'PROXIMO'])
        ).count()

        db.session.commit()

        current_app.logger.info(
            f"✅ Canhoto recebido: {entrega.descricao_completa} | "
            f"Distância: {distancia_entrega:.0f}m | "
            f"Restantes: {entregas_pendentes}"
        )

        return jsonify({
            'success': True,
            'message': f'Entrega de {entrega.cliente} confirmada!' if entregas_pendentes > 0
                      else 'Todas as entregas foram concluídas!',
            'entregas_restantes': entregas_pendentes,
            'todas_concluidas': todas_concluidas,
            'redirect': url_for('rastreamento.rastrear', token=token) if entregas_pendentes > 0
                       else url_for('rastreamento.confirmacao_entrega', token=token)
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao processar upload de canhoto: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500


@rastreamento_bp.route('/confirmacao/<token>', methods=['GET'])
def confirmacao_entrega(token):
    """
    Tela de confirmação após envio do canhoto
    """
    rastreamento = RastreamentoEmbarque.query.filter_by(token_acesso=token).first()

    if not rastreamento:
        return render_template('rastreamento/erro.html',
                             mensagem="Link inválido."), 404

    embarque = rastreamento.embarque

    return render_template('rastreamento/confirmacao.html',
                          rastreamento=rastreamento,
                          embarque=embarque)


# ========================================
# ROTAS INTERNAS (COM LOGIN) - MONITORAMENTO
# ========================================

@rastreamento_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard_rastreamento():
    """
    Dashboard de monitoramento com mapa de todos os rastreamentos ativos
    """
    # Buscar rastreamentos ativos
    rastreamentos_ativos = RastreamentoEmbarque.query.filter(
        RastreamentoEmbarque.status.in_(['ATIVO', 'CHEGOU_DESTINO'])
    ).all()

    # Coordenadas do CD (origem)
    from app.carteira.services.mapa_service import MapaService
    mapa_service = MapaService()
    origem_cd = {
        'lat': mapa_service.coordenadas_cd['lat'],
        'lng': mapa_service.coordenadas_cd['lng'],
        'nome': mapa_service.nome_cd,
        'endereco': mapa_service.endereco_cd
    }

    # Preparar dados para o mapa
    dados_mapa = []
    for rastr in rastreamentos_ativos:
        ultimo_ping = rastr.pings.first()
        if not ultimo_ping:
            continue

        embarque = rastr.embarque

        # Coletar NFs únicas do embarque
        nfs = set()
        for item in embarque.itens:
            if item.nota_fiscal and item.status == 'ativo':
                nfs.add(item.nota_fiscal)

        # Buscar destinos das entregas
        destinos = []
        from app.rastreamento.models import EntregaRastreada
        entregas = rastr.entregas.filter(
            EntregaRastreada.status.in_(['PENDENTE', 'EM_ROTA', 'PROXIMO'])
        ).all()

        for entrega in entregas:
            if entrega.tem_coordenadas:
                destinos.append({
                    'lat': entrega.destino_latitude,
                    'lng': entrega.destino_longitude,
                    'cliente': entrega.cliente,
                    'cidade': entrega.cidade,
                    'uf': entrega.uf,
                    'numero_nf': entrega.numero_nf,
                    'pedido': entrega.pedido,
                    'status': entrega.status
                })

        # Determinar status legível
        status_legivel = _mapear_status_rastreamento(rastr)

        dados_mapa.append({
            'rastreamento_id': rastr.id,
            'embarque_id': rastr.embarque_id,
            'embarque_numero': embarque.numero if embarque else 'N/A',
            'transportadora': embarque.transportadora.nome if embarque.transportadora else 'Não definida',
            'nfs': list(nfs),
            'status': rastr.status,
            'status_legivel': status_legivel,
            'ultimo_ping': rastr.ultimo_ping_em.strftime('%d/%m/%Y %H:%M') if rastr.ultimo_ping_em else 'N/A',
            'bateria': ultimo_ping.bateria_nivel,
            'motorista': {
                'lat': ultimo_ping.latitude,
                'lng': ultimo_ping.longitude,
                'distancia_destino': ultimo_ping.distancia_destino
            },
            'destinos': destinos
        })

    config = ConfiguracaoRastreamento.get_config()

    return render_template('rastreamento/dashboard.html',
                          rastreamentos=rastreamentos_ativos,
                          dados_mapa=dados_mapa,
                          origem_cd=origem_cd,
                          config=config)


def _mapear_status_rastreamento(rastreamento):
    """
    Mapeia status técnico para status legível
    """
    mapeamento = {
        'AGUARDANDO_ACEITE': 'Aguardando',
        'ATIVO': 'Em rota',
        'CHEGOU_DESTINO': 'Em rota',  # Ainda está em rota, só chegou próximo
        'ENTREGUE': 'Finalizada',
        'CANCELADO': 'Finalizada',
        'EXPIRADO': 'Finalizada'
    }
    return mapeamento.get(rastreamento.status, rastreamento.status)


@rastreamento_bp.route('/detalhes/<int:embarque_id>', methods=['GET'])
@login_required
def detalhes_rastreamento(embarque_id):
    """
    Detalhes completos de um rastreamento específico
    """
    rastreamento = RastreamentoEmbarque.query.filter_by(embarque_id=embarque_id).first_or_404()

    # Buscar todos os pings (últimos 100)
    pings = rastreamento.pings.limit(100).all()

    # Buscar logs
    logs = rastreamento.logs.limit(50).all()

    # Preparar histórico de rota
    historico_rota = []
    for ping in reversed(pings):  # Ordem cronológica
        historico_rota.append({
            'latitude': ping.latitude,
            'longitude': ping.longitude,
            'timestamp': ping.criado_em.strftime('%d/%m/%Y %H:%M:%S'),
            'distancia_destino': ping.distancia_destino,
            'velocidade': ping.velocidade
        })

    return render_template('rastreamento/detalhes.html',
                          rastreamento=rastreamento,
                          pings=pings,
                          logs=logs,
                          historico_rota=historico_rota)


@rastreamento_bp.route('/api/status/<int:embarque_id>', methods=['GET'])
@login_required
def api_status_rastreamento(embarque_id):
    """
    API para obter status atual do rastreamento (para atualização em tempo real)
    """
    rastreamento = RastreamentoEmbarque.query.filter_by(embarque_id=embarque_id).first_or_404()

    ultimo_ping = rastreamento.pings.first()

    return jsonify({
        'success': True,
        'data': {
            'status': rastreamento.status,
            'ultimo_ping_em': rastreamento.ultimo_ping_em.isoformat() if rastreamento.ultimo_ping_em else None,
            'tempo_sem_ping': rastreamento.tempo_sem_ping,
            'distancia_minima': rastreamento.distancia_minima_atingida,
            'distancia_atual': ultimo_ping.distancia_destino if ultimo_ping else None,
            'latitude': ultimo_ping.latitude if ultimo_ping else None,
            'longitude': ultimo_ping.longitude if ultimo_ping else None,
            'bateria': ultimo_ping.bateria_nivel if ultimo_ping else None,
            'total_pings': rastreamento.pings.count()
        }
    })


@rastreamento_bp.route('/api/encerrar/<int:rastreamento_id>', methods=['POST'])
@login_required
def encerrar_rastreamento(rastreamento_id):
    """
    Encerra um rastreamento GPS ativo
    Desconecta o motorista e finaliza a coleta de dados
    """
    try:
        rastreamento = RastreamentoEmbarque.query.get_or_404(rastreamento_id)

        # Verificar se já está encerrado
        if rastreamento.status in ['CANCELADO', 'ENTREGUE', 'EXPIRADO']:
            return jsonify({
                'success': False,
                'message': f'Rastreamento já está {rastreamento.status}'
            }), 400

        # Atualizar status
        rastreamento.status = 'CANCELADO'
        rastreamento.rastreamento_finalizado_em = agora_brasil()

        # Registrar log
        rastreamento.registrar_log(
            evento='ENCERRAMENTO_MANUAL',
            detalhes=json.dumps({
                'usuario': current_user.nome if current_user.is_authenticated else 'Sistema',
                'motivo': 'Encerramento manual pelo dashboard'
            })
        )

        db.session.commit()

        current_app.logger.info(
            f"✅ Rastreamento #{rastreamento_id} encerrado manualmente por {current_user.nome}"
        )

        return jsonify({
            'success': True,
            'message': 'Rastreamento encerrado com sucesso',
            'data': {
                'status': rastreamento.status,
                'finalizado_em': rastreamento.rastreamento_finalizado_em.isoformat()
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao encerrar rastreamento: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao encerrar rastreamento: {str(e)}'
        }), 500
