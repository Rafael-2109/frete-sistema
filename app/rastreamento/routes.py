"""
🚚 ROTAS DO SISTEMA DE RASTREAMENTO GPS
Endpoints para transportadores e monitoramento interno
"""

from flask import render_template, request, jsonify, redirect, url_for, current_app
from flask_login import login_required, current_user
from app.rastreamento import rastreamento_bp
from app.rastreamento.models import RastreamentoEmbarque, PingGPS, ConfiguracaoRastreamento
from app.rastreamento.services.gps_service import GPSService
from app.monitoramento.models import EntregaMonitorada
from app import db, csrf
from datetime import datetime
import json
from app.utils.timezone import agora_utc_naive


# ========================================
# ROTAS PÚBLICAS (SEM LOGIN) - TRANSPORTADOR
# ========================================

@rastreamento_bp.route('/app', methods=['GET'])
@rastreamento_bp.route('/app/inicio', methods=['GET'])
def app_inicio():
    """
    🚚 Tela inicial do app para motoristas (SEM LOGIN)

    Esta é a primeira tela que o motorista vê ao abrir o app.
    Apresenta botão para escanear QR Code e iniciar rastreamento.

    Acesso: Público (sem autenticação)
    Uso: Aplicativo mobile de rastreamento
    """
    return render_template('rastreamento/app_inicio.html')


@rastreamento_bp.route('/scanner', methods=['GET'])
def scanner_qrcode():
    """
    📷 Scanner de QR Code via câmera web (SEM LOGIN)

    Página com leitor de QR Code usando biblioteca html5-qrcode.
    Usado como fallback quando não é app nativo ou para testes em navegador.

    Acesso: Público (sem autenticação)
    Uso: Navegadores web e fallback do app mobile
    """
    return render_template('rastreamento/scanner_qrcode.html')


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
    if rastreamento.token_expiracao and agora_utc_naive() > rastreamento.token_expiracao:
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
        rastreamento.aceite_lgpd_em = agora_utc_naive()
        rastreamento.aceite_lgpd_ip = request.remote_addr
        rastreamento.aceite_lgpd_user_agent = request.headers.get('User-Agent', '')[:500]
        rastreamento.status = 'ATIVO'
        rastreamento.rastreamento_iniciado_em = agora_utc_naive()

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
        rastreamento.ultimo_ping_em = agora_utc_naive()

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
                rastreamento.chegou_destino_em = agora_utc_naive()
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
    entrega = db.session.get(EntregaRastreada,entrega_id) if entrega_id else None

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
    if extensao not in ['jpg', 'jpeg', 'jfif', 'png', 'pdf']:
        return jsonify({'success': False, 'message': 'Apenas JPG, JFIF, PNG ou PDF'}), 400

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
            allowed_extensions=['jpg', 'jpeg', 'jfif', 'png', 'pdf']
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
        entrega.entregue_em = agora_utc_naive()
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
            entrega_mon = db.session.query(EntregaMonitorada).filter_by(
                separacao_lote_id=entrega.item.separacao_lote_id
            ).first()

            if entrega_mon:
                entrega_mon.canhoto_arquivo = file_path
                entrega_mon.entregue = True
                entrega_mon.data_hora_entrega_realizada = agora_utc_naive()
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
            rastreamento.rastreamento_finalizado_em = agora_utc_naive()
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
            'message': f'Entrega de {entrega.cliente} confirmada!' if entregas_pendentes > 0 else 'Todas as entregas foram concluídas!',
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
            'transportadora': embarque.transportadora.razao_social if embarque.transportadora else 'Não definida',
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
        rastreamento.rastreamento_finalizado_em = agora_utc_naive()

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


# ========================================
# NOVOS ENDPOINTS PARA APP MOBILE
# ========================================

@rastreamento_bp.route('/api/iniciar', methods=['POST'])
@csrf.exempt
def api_iniciar_rastreamento():
    """
    🚚 API para iniciar rastreamento via QR Code ou embarque_id

    Chamado pelo app mobile ao escanear QR Code.
    Cria ou retorna rastreamento existente para o embarque.

    Body JSON:
    - embarque_id (int): ID do embarque OU
    - token (str): Token de acesso (se já escaneado antes)

    Retorna:
    - token: Token de acesso para rastreamento
    - embarque_id: ID do embarque
    - status: Status atual do rastreamento
    - entregas: Lista de NFs/clientes a entregar
    - requer_aceite_lgpd: Se precisa aceitar LGPD primeiro
    """
    try:
        data = request.get_json()

        embarque_id = data.get('embarque_id')
        token = data.get('token')

        if not embarque_id and not token:
            return jsonify({
                'success': False,
                'message': 'embarque_id ou token é obrigatório'
            }), 400

        # Buscar rastreamento existente
        rastreamento = None

        if token:
            rastreamento = RastreamentoEmbarque.query.filter_by(token_acesso=token).first()
        elif embarque_id:
            rastreamento = RastreamentoEmbarque.query.filter_by(embarque_id=embarque_id).first()

        # Se não existe, criar novo
        if not rastreamento:
            if not embarque_id:
                return jsonify({
                    'success': False,
                    'message': 'embarque_id é obrigatório para criar novo rastreamento'
                }), 400

            from app.embarques.models import Embarque
            embarque = db.session.get(Embarque, embarque_id)

            if not embarque:
                return jsonify({
                    'success': False,
                    'message': f'Embarque #{embarque_id} não encontrado'
                }), 404

            # Criar rastreamento
            rastreamento = RastreamentoEmbarque(
                embarque_id=embarque_id,
                criado_por='App Mobile'
            )
            db.session.add(rastreamento)
            db.session.flush()

            # Criar entregas rastreadas
            from app.rastreamento.services.entrega_rastreada_service import EntregaRastreadaService
            EntregaRastreadaService.criar_entregas_para_embarque(
                rastreamento.id,
                embarque_id
            )

            rastreamento.registrar_log(
                evento='CRIACAO_RASTREAMENTO',
                detalhes=json.dumps({'origem': 'app_mobile', 'embarque_id': embarque_id})
            )

            db.session.commit()
            current_app.logger.info(f"✅ Novo rastreamento criado para embarque #{embarque_id}")

        # Buscar entregas pendentes
        from app.rastreamento.models import EntregaRastreada
        entregas = rastreamento.entregas.filter(
            EntregaRastreada.status.in_(['PENDENTE', 'EM_ROTA', 'PROXIMO'])
        ).all()

        entregas_json = [
            {
                'id': e.id,
                'numero_nf': e.numero_nf,
                'pedido': e.pedido,
                'cliente': e.cliente,
                'cidade': e.cidade,
                'uf': e.uf,
                'endereco': e.endereco_completo,
                'status': e.status,
                'latitude': e.destino_latitude,
                'longitude': e.destino_longitude,
                'geocodificado': e.tem_coordenadas
            }
            for e in entregas
        ]

        return jsonify({
            'success': True,
            'data': {
                'token': rastreamento.token_acesso,
                'embarque_id': rastreamento.embarque_id,
                'embarque_numero': rastreamento.embarque.numero if rastreamento.embarque else None,
                'status': rastreamento.status,
                'requer_aceite_lgpd': not rastreamento.aceite_lgpd,
                'url_aceite': url_for('rastreamento.aceite_lgpd', token=rastreamento.token_acesso, _external=True),
                'entregas': entregas_json,
                'total_entregas': len(entregas_json)
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao iniciar rastreamento: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao iniciar rastreamento: {str(e)}'
        }), 500


@rastreamento_bp.route('/api/verificar-proximidade/<token>', methods=['GET'])
@csrf.exempt
def api_verificar_proximidade(token):
    """
    📍 API para verificar proximidade do motorista a todas entregas

    Calcula distância para cada entrega pendente e retorna lista ordenada.
    Atualiza status para PROXIMO quando <200m.

    Query params:
    - latitude (float): Latitude atual
    - longitude (float): Longitude atual

    Retorna:
    - entregas_proximas: Lista de entregas <200m
    - todas_entregas: Lista completa com distâncias
    """
    try:
        rastreamento = RastreamentoEmbarque.query.filter_by(token_acesso=token).first()

        if not rastreamento:
            return jsonify({'success': False, 'message': 'Token inválido'}), 404

        if not rastreamento.aceite_lgpd:
            return jsonify({'success': False, 'message': 'Aceite LGPD pendente'}), 403

        latitude = request.args.get('latitude', type=float)
        longitude = request.args.get('longitude', type=float)

        if not latitude or not longitude:
            return jsonify({
                'success': False,
                'message': 'latitude e longitude são obrigatórios'
            }), 400

        # Validar coordenadas
        if not GPSService.validar_coordenadas(latitude, longitude):
            return jsonify({
                'success': False,
                'message': 'Coordenadas inválidas'
            }), 400

        from app.rastreamento.services.entrega_rastreada_service import EntregaRastreadaService
        from app.rastreamento.models import EntregaRastreada

        # Detectar entregas próximas
        entregas_proximas = EntregaRastreadaService.detectar_entrega_proxima(
            rastreamento.id,
            latitude,
            longitude
        )

        # Buscar todas entregas pendentes com distância
        entregas_pendentes = rastreamento.entregas.filter(
            EntregaRastreada.status.in_(['PENDENTE', 'EM_ROTA', 'PROXIMO'])
        ).all()

        todas_entregas = []
        for entrega in entregas_pendentes:
            distancia = None
            if entrega.tem_coordenadas:
                distancia = GPSService.calcular_distancia(
                    (latitude, longitude),
                    (entrega.destino_latitude, entrega.destino_longitude),
                    'metros'
                )

            todas_entregas.append({
                'id': entrega.id,
                'numero_nf': entrega.numero_nf,
                'pedido': entrega.pedido,
                'cliente': entrega.cliente,
                'cidade': entrega.cidade,
                'uf': entrega.uf,
                'status': entrega.status,
                'distancia_metros': distancia,
                'distancia_formatada': GPSService.formatar_distancia(distancia) if distancia else 'N/A',
                'proximo': distancia and distancia <= 200
            })

        # Ordenar por distância
        todas_entregas.sort(key=lambda x: x['distancia_metros'] or 999999)

        db.session.commit()

        return jsonify({
            'success': True,
            'data': {
                'posicao_atual': {'latitude': latitude, 'longitude': longitude},
                'entregas_proximas': [
                    {
                        'id': ep['entrega'].id,
                        'numero_nf': ep['entrega'].numero_nf,
                        'cliente': ep['entrega'].cliente,
                        'distancia_metros': ep['distancia'],
                        'distancia_formatada': GPSService.formatar_distancia(ep['distancia'])
                    }
                    for ep in entregas_proximas
                ],
                'todas_entregas': todas_entregas,
                'total_proximas': len(entregas_proximas),
                'total_pendentes': len(todas_entregas)
            }
        })

    except Exception as e:
        current_app.logger.error(f"Erro ao verificar proximidade: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro: {str(e)}'
        }), 500


@rastreamento_bp.route('/api/comentario', methods=['POST'])
@csrf.exempt
def api_enviar_comentario():
    """
    💬 API para motorista enviar comentário ao monitoramento

    Usado quando motorista clica em "Contactar Monitoramento".
    Registra comentário e pode notificar operação.

    Body JSON:
    - token (str): Token de acesso
    - entrega_id (int, opcional): ID da entrega específica
    - mensagem (str): Texto do comentário
    - tipo (str, opcional): 'dificuldade', 'informacao', 'urgente'

    Retorna:
    - success: True/False
    - comentario_id: ID do comentário criado
    """
    try:
        data = request.get_json()

        token = data.get('token')
        entrega_id = data.get('entrega_id')
        mensagem = data.get('mensagem')
        tipo = data.get('tipo', 'informacao')

        if not token or not mensagem:
            return jsonify({
                'success': False,
                'message': 'token e mensagem são obrigatórios'
            }), 400

        rastreamento = RastreamentoEmbarque.query.filter_by(token_acesso=token).first()

        if not rastreamento:
            return jsonify({'success': False, 'message': 'Token inválido'}), 404

        # Registrar log com comentário
        log = rastreamento.registrar_log(
            evento='COMENTARIO_MOTORISTA',
            detalhes=json.dumps({
                'mensagem': mensagem,
                'tipo': tipo,
                'entrega_id': entrega_id,
                'timestamp': agora_utc_naive().isoformat()
            })
        )

        # Se for entrega específica, atualizar entrega também
        if entrega_id:
            from app.rastreamento.models import EntregaRastreada
            entrega = db.session.get(EntregaRastreada, entrega_id)
            if entrega and entrega.rastreamento_id == rastreamento.id:
                # Pode adicionar campo de observação se necessário
                pass

        # TODO: Integrar com Odoo para gravar no chatter da NF
        # Será implementado na fase de integração Odoo

        db.session.commit()

        current_app.logger.info(
            f"💬 Comentário recebido - Embarque #{rastreamento.embarque_id}: {mensagem[:50]}..."
        )

        return jsonify({
            'success': True,
            'message': 'Comentário enviado com sucesso',
            'data': {
                'comentario_id': log.id,
                'timestamp': log.criado_em.isoformat()
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao enviar comentário: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro: {str(e)}'
        }), 500


@rastreamento_bp.route('/api/ativos', methods=['GET'])
@login_required
def api_rastreamentos_ativos():
    """
    📊 API para listar todos rastreamentos ativos

    Usado pelo dashboard de monitoramento.
    Inclui posição atual, entregas pendentes, tempo no cliente.

    Retorna:
    - rastreamentos: Lista de rastreamentos ativos com detalhes
    """
    try:
        rastreamentos = RastreamentoEmbarque.query.filter(
            RastreamentoEmbarque.status.in_(['ATIVO', 'CHEGOU_DESTINO'])
        ).all()

        from app.rastreamento.models import EntregaRastreada

        resultado = []
        for rastr in rastreamentos:
            ultimo_ping = rastr.pings.first()
            embarque = rastr.embarque

            # Calcular tempo no cliente (se chegou próximo)
            tempo_no_cliente = None
            if rastr.chegou_destino_em:
                delta = agora_utc_naive() - rastr.chegou_destino_em
                tempo_no_cliente = int(delta.total_seconds() / 60)  # Em minutos

            # Buscar entregas pendentes
            entregas_pendentes = rastr.entregas.filter(
                EntregaRastreada.status.in_(['PENDENTE', 'EM_ROTA', 'PROXIMO'])
            ).all()

            entregas_proximas = rastr.entregas.filter_by(status='PROXIMO').all()

            # Coletar NFs únicas
            nfs = set()
            for item in embarque.itens:
                if item.nota_fiscal and item.status == 'ativo':
                    nfs.add(item.nota_fiscal)

            resultado.append({
                'rastreamento_id': rastr.id,
                'embarque_id': rastr.embarque_id,
                'embarque_numero': embarque.numero if embarque else None,
                'transportadora': embarque.transportadora.razao_social if embarque and embarque.transportadora else 'Não definida',
                'status': rastr.status,
                'nfs': list(nfs),
                'posicao': {
                    'latitude': ultimo_ping.latitude if ultimo_ping else None,
                    'longitude': ultimo_ping.longitude if ultimo_ping else None,
                    'distancia_destino': ultimo_ping.distancia_destino if ultimo_ping else None,
                    'bateria': ultimo_ping.bateria_nivel if ultimo_ping else None
                },
                'ultimo_ping': rastr.ultimo_ping_em.isoformat() if rastr.ultimo_ping_em else None,
                'tempo_sem_ping': rastr.tempo_sem_ping,
                'tempo_no_cliente_minutos': tempo_no_cliente,
                'com_dificuldade': tempo_no_cliente and tempo_no_cliente > 40,
                'entregas': {
                    'total': rastr.entregas.count(),
                    'pendentes': len(entregas_pendentes),
                    'proximas': len(entregas_proximas),
                    'entregues': rastr.entregas.filter_by(status='ENTREGUE').count()
                },
                'clientes_pendentes': [
                    {'cliente': e.cliente, 'cidade': e.cidade, 'uf': e.uf, 'numero_nf': e.numero_nf}
                    for e in entregas_pendentes[:5]  # Limitar a 5
                ]
            })

        return jsonify({
            'success': True,
            'data': {
                'rastreamentos': resultado,
                'total': len(resultado),
                'com_dificuldade': sum(1 for r in resultado if r['com_dificuldade'])
            }
        })

    except Exception as e:
        current_app.logger.error(f"Erro ao listar rastreamentos ativos: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro: {str(e)}'
        }), 500


@rastreamento_bp.route('/api/dificuldades', methods=['GET'])
@login_required
def api_entregas_com_dificuldade():
    """
    ⚠️ API para listar entregas com dificuldade (>40min no cliente)

    Filtro: tempo_no_cliente > 40 minutos e status != ENTREGUE

    Retorna:
    - entregas_dificuldade: Lista de entregas com >40min no cliente
    """
    try:
        from app.rastreamento.models import EntregaRastreada

        rastreamentos = RastreamentoEmbarque.query.filter(
            RastreamentoEmbarque.status.in_(['ATIVO', 'CHEGOU_DESTINO']),
            RastreamentoEmbarque.chegou_destino_em.isnot(None)
        ).all()

        entregas_dificuldade = []
        agora = agora_utc_naive()

        for rastr in rastreamentos:
            # Calcular tempo no cliente
            delta = agora - rastr.chegou_destino_em
            tempo_minutos = int(delta.total_seconds() / 60)

            if tempo_minutos > 40:
                # Buscar entregas próximas (status PROXIMO)
                entregas_proximas = rastr.entregas.filter_by(status='PROXIMO').all()

                embarque = rastr.embarque
                ultimo_ping = rastr.pings.first()

                for entrega in entregas_proximas:
                    entregas_dificuldade.append({
                        'rastreamento_id': rastr.id,
                        'embarque_id': rastr.embarque_id,
                        'embarque_numero': embarque.numero if embarque else None,
                        'transportadora': embarque.transportadora.razao_social if embarque and embarque.transportadora else 'N/A',
                        'entrega_id': entrega.id,
                        'numero_nf': entrega.numero_nf,
                        'cliente': entrega.cliente,
                        'cidade': entrega.cidade,
                        'uf': entrega.uf,
                        'tempo_no_cliente_minutos': tempo_minutos,
                        'chegou_em': rastr.chegou_destino_em.isoformat(),
                        'posicao': {
                            'latitude': ultimo_ping.latitude if ultimo_ping else None,
                            'longitude': ultimo_ping.longitude if ultimo_ping else None
                        },
                        'bateria': ultimo_ping.bateria_nivel if ultimo_ping else None,
                        'ultimo_ping': rastr.ultimo_ping_em.isoformat() if rastr.ultimo_ping_em else None
                    })

        # Ordenar por tempo (maior primeiro)
        entregas_dificuldade.sort(key=lambda x: x['tempo_no_cliente_minutos'], reverse=True)

        return jsonify({
            'success': True,
            'data': {
                'entregas_dificuldade': entregas_dificuldade,
                'total': len(entregas_dificuldade)
            }
        })

    except Exception as e:
        current_app.logger.error(f"Erro ao listar entregas com dificuldade: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro: {str(e)}'
        }), 500


@rastreamento_bp.route('/api/finalizar-entrega', methods=['POST'])
@csrf.exempt
def api_finalizar_entrega():
    """
    ✅ API completa para finalizar entrega com questionário

    Fluxo do questionário:
    1. NFs entregues? (SIM/NÃO)
    2. Houve devolução? (NFD)
    3. Houve pagamento descarga? (DespesaExtra)
    4. Houve devolução pallet?

    Body JSON:
    - token (str): Token de acesso
    - entrega_id (int): ID da entrega sendo finalizada
    - entregue (bool): Se foi entregue com sucesso
    - motivo_nao_entrega (str, opcional): Motivo se não entregue
    - canhoto_base64 (str, opcional): Foto do canhoto em base64
    - latitude (float, opcional): Latitude no momento da entrega
    - longitude (float, opcional): Longitude no momento da entrega

    Dados opcionais do questionário:
    - devolucao: {
        houve: bool,
        numero_nfd: str (manual ou código de barras),
        motivo: str
      }
    - pagamento_descarga: {
        houve: bool,
        valor: float,
        comprovante_base64: str (foto)
      }
    - pallet: {
        devolveu: bool,
        quantidade_devolvida: int,
        vale_pallet: bool,
        vale_pallet_base64: str (foto),
        canhoto_nf_pallet: bool
      }

    Retorna:
    - success: True/False
    - entregas_restantes: Número de entregas pendentes
    - todas_concluidas: Se todas entregas foram finalizadas
    """
    try:
        data = request.get_json()

        token = data.get('token')
        entrega_id = data.get('entrega_id')
        entregue = data.get('entregue', True)
        motivo_nao_entrega = data.get('motivo_nao_entrega')
        canhoto_base64 = data.get('canhoto_base64')
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        # Dados do questionário
        devolucao_data = data.get('devolucao', {})
        pagamento_descarga_data = data.get('pagamento_descarga', {})
        pallet_data = data.get('pallet', {})

        if not token or not entrega_id:
            return jsonify({
                'success': False,
                'message': 'token e entrega_id são obrigatórios'
            }), 400

        rastreamento = RastreamentoEmbarque.query.filter_by(token_acesso=token).first()
        if not rastreamento:
            return jsonify({'success': False, 'message': 'Token inválido'}), 404

        from app.rastreamento.models import EntregaRastreada
        entrega = db.session.get(EntregaRastreada, entrega_id)

        if not entrega or entrega.rastreamento_id != rastreamento.id:
            return jsonify({'success': False, 'message': 'Entrega não encontrada'}), 404

        if entrega.status == 'ENTREGUE':
            return jsonify({
                'success': False,
                'message': 'Esta entrega já foi finalizada'
            }), 400

        # Calcular distância do cliente
        distancia_entrega = None
        if latitude and longitude and entrega.tem_coordenadas:
            if GPSService.validar_coordenadas(latitude, longitude):
                distancia_entrega = GPSService.calcular_distancia(
                    (float(latitude), float(longitude)),
                    (entrega.destino_latitude, entrega.destino_longitude),
                    'metros'
                )

        # Salvar canhoto se fornecido em base64
        canhoto_path = None
        if canhoto_base64 and entregue:
            import base64
            from app.utils.file_storage import get_file_storage
            storage = get_file_storage()

            # Decodificar base64
            try:
                # Remover prefixo data:image/xxx;base64, se existir
                if ',' in canhoto_base64:
                    canhoto_base64 = canhoto_base64.split(',')[1]

                img_data = base64.b64decode(canhoto_base64)
                filename = f"canhoto_{entrega_id}_{int(agora_utc_naive().timestamp())}.jpg"

                # Salvar usando o storage
                from io import BytesIO
                from werkzeug.datastructures import FileStorage
                file_obj = FileStorage(
                    stream=BytesIO(img_data),
                    filename=filename,
                    content_type='image/jpeg'
                )
                canhoto_path = storage.save_file(
                    file=file_obj,
                    folder='canhotos_rastreamento',
                    allowed_extensions=['jpg', 'jpeg', 'png']
                )
            except Exception as e:
                current_app.logger.error(f"Erro ao salvar canhoto base64: {str(e)}")

        # Atualizar entrega
        entrega.entregue_em = agora_utc_naive()
        entrega.entregue_distancia_metros = distancia_entrega
        entrega.canhoto_latitude = float(latitude) if latitude else None
        entrega.canhoto_longitude = float(longitude) if longitude else None

        if entregue:
            entrega.status = 'ENTREGUE'
            if canhoto_path:
                entrega.canhoto_arquivo = canhoto_path
        else:
            entrega.status = 'NAO_ENTREGUE'

        # Processar devolução (NFD) - Usando serviço de integração Odoo
        from app.rastreamento.services.odoo_integration_service import OdooRastreamentoIntegrationService

        nfd_criada = None
        if devolucao_data.get('houve'):
            numero_nfd = devolucao_data.get('numero_nfd')
            motivo_devolucao = devolucao_data.get('motivo', 'Informado pelo motorista')

            if numero_nfd:
                # Criar registro na tabela nf_devolucao
                resultado_nfd = OdooRastreamentoIntegrationService.criar_nfd_devolucao(
                    numero_nfd=numero_nfd,
                    entrega_id=entrega_id,
                    motivo=motivo_devolucao
                )
                if resultado_nfd.get('success'):
                    nfd_criada = numero_nfd
                    current_app.logger.info(
                        f"📦 NFD {numero_nfd} criada/vinculada - Entrega #{entrega_id}"
                    )

        # Processar pagamento de descarga (DespesaExtra) - Usando serviço de integração
        despesa_criada = None
        if pagamento_descarga_data.get('houve'):
            valor_descarga = pagamento_descarga_data.get('valor', 0)
            comprovante_base64 = pagamento_descarga_data.get('comprovante_base64')

            # Salvar comprovante se fornecido
            comprovante_path = None
            if comprovante_base64:
                try:
                    import base64
                    from app.utils.file_storage import get_file_storage
                    from io import BytesIO
                    from werkzeug.datastructures import FileStorage as WZFileStorage

                    storage = get_file_storage()
                    if ',' in comprovante_base64:
                        comprovante_base64 = comprovante_base64.split(',')[1]
                    img_data = base64.b64decode(comprovante_base64)
                    filename = f"comprovante_descarga_{entrega_id}_{int(agora_utc_naive().timestamp())}.jpg"
                    file_obj = WZFileStorage(
                        stream=BytesIO(img_data),
                        filename=filename,
                        content_type='image/jpeg'
                    )
                    comprovante_path = storage.save_file(
                        file=file_obj,
                        folder='comprovantes_descarga',
                        allowed_extensions=['jpg', 'jpeg', 'png']
                    )
                except Exception as e:
                    current_app.logger.error(f"Erro ao salvar comprovante descarga: {str(e)}")

            if valor_descarga > 0:
                # Criar DespesaExtra vinculada ao frete
                resultado_despesa = OdooRastreamentoIntegrationService.criar_despesa_descarga(
                    entrega_id=entrega_id,
                    valor=valor_descarga,
                    comprovante_path=comprovante_path
                )
                if resultado_despesa.get('success'):
                    despesa_criada = {
                        'tipo': 'DESCARGA',
                        'valor': valor_descarga,
                        'despesa_id': resultado_despesa.get('despesa_id')
                    }
                    current_app.logger.info(
                        f"💰 DespesaExtra criada: R$ {valor_descarga:.2f} - Entrega #{entrega_id}"
                    )
                else:
                    despesa_criada = {
                        'tipo': 'DESCARGA',
                        'valor': valor_descarga,
                        'erro': resultado_despesa.get('error', 'Frete não encontrado')
                    }

        # Processar devolução de pallet - Usando serviço de integração
        pallet_info = None
        if pallet_data:
            devolveu = pallet_data.get('devolveu', False)
            qtd_devolvida = pallet_data.get('quantidade_devolvida', 0)
            vale_pallet = pallet_data.get('vale_pallet', False)

            if devolveu or vale_pallet:
                # Registrar info de pallet no embarque
                OdooRastreamentoIntegrationService.registrar_pallet_info(
                    embarque_id=rastreamento.embarque_id,
                    pallet_data=pallet_data
                )
                pallet_info = {
                    'devolveu': devolveu,
                    'quantidade': qtd_devolvida,
                    'vale_pallet': vale_pallet
                }
                current_app.logger.info(
                    f"📦 Pallet - Devolveu: {qtd_devolvida} | Vale: {vale_pallet} - Entrega #{entrega_id}"
                )

        # Registrar log completo
        rastreamento.registrar_log(
            evento='FINALIZACAO_ENTREGA',
            detalhes=json.dumps({
                'entrega_id': entrega_id,
                'entregue': entregue,
                'motivo_nao_entrega': motivo_nao_entrega,
                'distancia_metros': distancia_entrega,
                'canhoto_path': canhoto_path,
                'nfd_informada': nfd_criada,
                'despesa_descarga': despesa_criada,
                'pallet_info': pallet_info
            })
        )

        # Atualizar EntregaMonitorada se existir
        if entrega.item and entrega.item.separacao_lote_id:
            entrega_mon = db.session.query(EntregaMonitorada).filter_by(
                separacao_lote_id=entrega.item.separacao_lote_id
            ).first()

            if entrega_mon:
                entrega_mon.entregue = entregue
                entrega_mon.data_hora_entrega_realizada = agora_utc_naive()
                if canhoto_path:
                    entrega_mon.canhoto_arquivo = canhoto_path
                if nfd_criada:
                    entrega_mon.teve_devolucao = True

        # Verificar se todas entregas foram concluídas
        from app.rastreamento.services.entrega_rastreada_service import EntregaRastreadaService

        entregas_pendentes = rastreamento.entregas.filter(
            EntregaRastreada.status.in_(['PENDENTE', 'EM_ROTA', 'PROXIMO'])
        ).count()

        todas_concluidas = entregas_pendentes == 0

        if todas_concluidas:
            rastreamento.status = 'ENTREGUE'
            rastreamento.rastreamento_finalizado_em = agora_utc_naive()

        db.session.commit()

        current_app.logger.info(
            f"✅ Entrega finalizada: {entrega.descricao_completa} | "
            f"Entregue: {entregue} | Restantes: {entregas_pendentes}"
        )

        return jsonify({
            'success': True,
            'message': 'Entrega finalizada com sucesso!' if entregue else 'Entrega registrada como não realizada',
            'data': {
                'entrega_id': entrega_id,
                'status': entrega.status,
                'entregas_restantes': entregas_pendentes,
                'todas_concluidas': todas_concluidas,
                'nfd_registrada': nfd_criada,
                'despesa_registrada': despesa_criada is not None,
                'pallet_info': pallet_info,
                'redirect': url_for('rastreamento.rastrear', token=token) if not todas_concluidas
                           else url_for('rastreamento.confirmacao_entrega', token=token)
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao finalizar entrega: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro: {str(e)}'
        }), 500


@rastreamento_bp.route('/questionario/<token>/<int:entrega_id>', methods=['GET'])
@csrf.exempt
def tela_questionario_entrega(token, entrega_id):
    """
    📋 Tela do questionário de finalização de entrega (SEM LOGIN)

    Apresenta formulário mobile-friendly para o motorista informar:
    - Se entregou ou não (com canhoto ou motivo)
    - Devolução com número da NFD
    - Pagamento de descarga (valor + comprovante)
    - Retorno de pallets (quantidade + vale pallet)

    Args:
        token: Token de acesso do rastreamento
        entrega_id: ID da EntregaRastreada

    Acesso: Público (via token único do QR Code)
    """
    from app.rastreamento.models import EntregaRastreada

    # Validar rastreamento pelo token
    rastreamento = RastreamentoEmbarque.query.filter_by(token_acesso=token).first()
    if not rastreamento:
        return render_template('rastreamento/erro.html',
                              mensagem="Token inválido ou expirado."), 404

    # Validar se rastreamento está ativo
    if rastreamento.status not in ['ATIVO', 'CHEGOU_DESTINO']:
        return render_template('rastreamento/erro.html',
                              mensagem="Este rastreamento não está mais ativo."), 410

    # Buscar entrega
    entrega = db.session.get(EntregaRastreada, entrega_id)
    if not entrega:
        return render_template('rastreamento/erro.html',
                              mensagem="Entrega não encontrada."), 404

    # Validar se entrega pertence ao rastreamento
    if entrega.rastreamento_id != rastreamento.id:
        return render_template('rastreamento/erro.html',
                              mensagem="Entrega não pertence a este rastreamento."), 403

    # Verificar se já foi finalizada
    if entrega.status in ['ENTREGUE', 'NAO_ENTREGUE']:
        return render_template('rastreamento/erro.html',
                              mensagem=f"Esta entrega já foi finalizada como: {entrega.status}"), 400

    # Buscar configurações
    config = ConfiguracaoRastreamento.get_config()

    # Dados do embarque para contexto
    embarque = rastreamento.embarque

    return render_template('rastreamento/questionario_entrega.html',
                          rastreamento=rastreamento,
                          entrega=entrega,
                          embarque=embarque,
                          config=config,
                          token=token)


@rastreamento_bp.route('/monitoramento', methods=['GET'])
@login_required
def tela_monitoramento():
    """
    🖥️ Tela de monitoramento em tempo real

    Mapa com motoristas rastreados + lista de entregas com dificuldade
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

    # Contar entregas com dificuldade (>40min)
    agora = agora_utc_naive()
    entregas_dificuldade = 0

    for rastr in rastreamentos_ativos:
        if rastr.chegou_destino_em:
            delta = agora - rastr.chegou_destino_em
            if delta.total_seconds() > 40 * 60:  # >40 minutos
                entregas_dificuldade += rastr.entregas.filter_by(status='PROXIMO').count()

    config = ConfiguracaoRastreamento.get_config()

    return render_template('rastreamento/monitoramento.html',
                          rastreamentos=rastreamentos_ativos,
                          origem_cd=origem_cd,
                          config=config,
                          entregas_dificuldade=entregas_dificuldade)
