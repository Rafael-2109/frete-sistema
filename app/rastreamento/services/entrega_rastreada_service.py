"""
🎯 SERVIÇO DE ENTREGAS RASTREADAS
Gerencia entregas individuais dentro de um embarque
Autor: Sistema de Rastreamento Nacom
Data: 2025-10-03
"""

from app import db
from app.rastreamento.models import EntregaRastreada, RastreamentoEmbarque
from app.rastreamento.services.gps_service import GPSService
from app.embarques.models import Embarque, EmbarqueItem
from app.carteira.models import CarteiraPrincipal
from datetime import datetime
from app.utils.timezone import agora_utc_naive
from flask import current_app


class EntregaRastreadaService:
    """Serviço para gerenciar entregas rastreadas individuais"""

    @staticmethod
    def criar_entregas_para_embarque(rastreamento_id, embarque_id):
        """
        Cria EntregaRastreada para cada item do embarque
        Geocodifica endereços automaticamente

        Args:
            rastreamento_id (int): ID do RastreamentoEmbarque
            embarque_id (int): ID do Embarque

        Returns:
            list: Lista de EntregaRastreada criadas
        """
        embarque = db.session.get(Embarque,embarque_id) if embarque_id else None
        if not embarque or not embarque.itens:
            current_app.logger.warning(f"Embarque {embarque_id} não tem itens para criar entregas rastreadas")
            return []

        # Pre-check FK: valida que cada item.id ainda existe na DB.
        # Evita ForeignKeyViolation em entregas_rastreadas.embarque_item_id
        # quando o relationship retorna objetos stale (Sentry PYTHON-FLASK-VP).
        item_ids_em_memoria = [item.id for item in embarque.itens_ativos]
        ids_validos_db = set()
        if item_ids_em_memoria:
            ids_validos_db = {
                row[0] for row in db.session.query(EmbarqueItem.id).filter(
                    EmbarqueItem.id.in_(item_ids_em_memoria)
                ).all()
            }

        entregas_criadas = []

        for idx, item in enumerate(embarque.itens_ativos, start=1):
            if item.id not in ids_validos_db:
                current_app.logger.warning(
                    f"EmbarqueItem {item.id} (pedido {item.pedido}) nao existe mais "
                    f"na DB — pulando entrega rastreada (provavelmente cancelado/deletado "
                    f"antes deste commit). Embarque {embarque_id}."
                )
                continue
            # Buscar dados completos da carteira
            pedido_carteira = db.session.query(CarteiraPrincipal).filter_by(
                num_pedido=item.pedido
            ).first()

            # Montar endereço completo e geocodificar
            endereco_completo, lat, lon = EntregaRastreadaService._obter_endereco_e_coordenadas(
                item, pedido_carteira
            )

            # Criar entrega rastreada
            entrega = EntregaRastreada(
                rastreamento_id=rastreamento_id,
                embarque_item_id=item.id,
                numero_nf=item.nota_fiscal,
                pedido=item.pedido,
                cnpj_cliente=item.cnpj_cliente or '',
                cliente=item.cliente,
                endereco_completo=endereco_completo,
                cidade=item.cidade_destino,
                uf=item.uf_destino,
                destino_latitude=lat,
                destino_longitude=lon,
                geocodificado_em=agora_utc_naive() if lat else None,
                ordem_entrega=idx if embarque.tipo_carga == 'DIRETA' else None,
                status='PENDENTE'
            )

            db.session.add(entrega)
            entregas_criadas.append(entrega)

            current_app.logger.info(
                f"✅ Entrega rastreada criada: {entrega.descricao_completa} | "
                f"Coords: {'✅ ' + str(lat)[:8] + ',' + str(lon)[:8] if lat else '❌ Não geocodificado'}"
            )

        db.session.flush()
        return entregas_criadas

    @staticmethod
    def _obter_endereco_e_coordenadas(item, pedido_carteira):
        """
        Obtém endereço completo e geocodifica

        Args:
            item: EmbarqueItem
            pedido_carteira: CarteiraPrincipal ou None

        Returns:
            tuple: (endereco_completo, latitude, longitude)
        """
        if pedido_carteira:
            # Montar endereço completo da CarteiraPrincipal
            partes = []

            if pedido_carteira.rua_endereco_ent:
                partes.append(pedido_carteira.rua_endereco_ent)
            if pedido_carteira.endereco_ent:
                partes.append(f"nº {pedido_carteira.endereco_ent}")
            if pedido_carteira.bairro_endereco_ent:
                partes.append(pedido_carteira.bairro_endereco_ent)

            cidade = pedido_carteira.nome_cidade or item.cidade_destino
            if cidade:
                partes.append(cidade)

            uf = pedido_carteira.cod_uf or item.uf_destino
            if uf:
                partes.append(uf)

            if pedido_carteira.cep_endereco_ent:
                partes.append(f"CEP {pedido_carteira.cep_endereco_ent}")

            partes.append("Brasil")

            endereco = ", ".join(filter(None, partes))
        else:
            # Fallback: usar apenas cidade + UF
            endereco = f"{item.cidade_destino}, {item.uf_destino}, Brasil"
            current_app.logger.warning(
                f"⚠️ Pedido {item.pedido} não encontrado na CarteiraPrincipal, usando fallback"
            )

        # Geocodificar
        try:
            coords = GPSService.geocode_endereco(endereco, timeout=10)
            lat = coords[0] if coords else None
            lon = coords[1] if coords else None

            if not coords:
                current_app.logger.warning(f"❌ Geocoding falhou para: {endereco}")

        except Exception as e:
            current_app.logger.error(f"❌ Erro ao geocodificar {endereco}: {str(e)}")
            lat = None
            lon = None

        return endereco, lat, lon

    @staticmethod
    def detectar_entrega_proxima(rastreamento_id, latitude_atual, longitude_atual):
        """
        Detecta qual(is) entrega(s) o motorista está próximo (<200m)

        REGRA DE NEGÓCIO:
        - Considera apenas entregas com status='PENDENTE'
        - Calcula distância para todas entregas pendentes
        - Marca como 'PROXIMO' as que estiverem <200m
        - Retorna lista ordenada por distância

        Args:
            rastreamento_id (int): ID do RastreamentoEmbarque
            latitude_atual (float): Latitude atual do motorista
            longitude_atual (float): Longitude atual do motorista

        Returns:
            list: Lista de dicts com {'entrega': EntregaRastreada, 'distancia': float}
        """
        rastreamento = db.session.get(RastreamentoEmbarque,rastreamento_id) if rastreamento_id else None
        if not rastreamento:
            return []

        entregas_proximas = []

        # Buscar entregas pendentes
        entregas_pendentes = rastreamento.entregas.filter(
            EntregaRastreada.status.in_(['PENDENTE', 'EM_ROTA'])
        ).all()

        for entrega in entregas_pendentes:
            if not entrega.tem_coordenadas:
                current_app.logger.debug(
                    f"⚠️ Entrega {entrega.id} não tem coordenadas, pulando detecção de proximidade"
                )
                continue

            # Calcular distância
            distancia = GPSService.calcular_distancia(
                (latitude_atual, longitude_atual),
                (entrega.destino_latitude, entrega.destino_longitude),
                'metros'
            )

            if distancia is None:
                continue

            # Se está próximo (<200m)
            if distancia <= 200:
                entregas_proximas.append({
                    'entrega': entrega,
                    'distancia': distancia
                })

                # Atualizar status para PROXIMO (apenas se ainda PENDENTE)
                if entrega.status == 'PENDENTE':
                    entrega.status = 'PROXIMO'
                    current_app.logger.info(
                        f"📍 Motorista chegou próximo de {entrega.descricao_completa} ({distancia:.0f}m)"
                    )

        # Ordenar por distância (mais próximo primeiro)
        entregas_proximas.sort(key=lambda x: x['distancia'])

        return entregas_proximas

    @staticmethod
    def obter_entregas_pendentes(rastreamento_id):
        """
        Retorna todas entregas pendentes de um rastreamento
        Útil para quando motorista está longe de todos destinos

        Args:
            rastreamento_id (int): ID do RastreamentoEmbarque

        Returns:
            list: Lista de EntregaRastreada pendentes
        """
        rastreamento = db.session.get(RastreamentoEmbarque,rastreamento_id) if rastreamento_id else None
        if not rastreamento:
            return []

        return rastreamento.entregas.filter(
            EntregaRastreada.status.in_(['PENDENTE', 'EM_ROTA', 'PROXIMO'])
        ).order_by(EntregaRastreada.ordem_entrega.asc().nullsfirst()).all()

    @staticmethod
    def verificar_todas_entregas_concluidas(rastreamento_id):
        """
        Verifica se todas entregas de um rastreamento foram concluídas

        Args:
            rastreamento_id (int): ID do RastreamentoEmbarque

        Returns:
            bool: True se todas concluídas, False caso contrário
        """
        rastreamento = db.session.get(RastreamentoEmbarque,rastreamento_id) if rastreamento_id else None
        if not rastreamento:
            return False

        entregas_pendentes = rastreamento.entregas.filter(
            EntregaRastreada.status.in_(['PENDENTE', 'EM_ROTA', 'PROXIMO'])
        ).count()

        return entregas_pendentes == 0

    @staticmethod
    def obter_estatisticas_entregas(rastreamento_id):
        """
        Retorna estatísticas das entregas de um rastreamento

        Args:
            rastreamento_id (int): ID do RastreamentoEmbarque

        Returns:
            dict: Estatísticas {total, entregues, pendentes, proximas}
        """
        rastreamento = db.session.get(RastreamentoEmbarque,rastreamento_id) if rastreamento_id else None
        if not rastreamento:
            return {'total': 0, 'entregues': 0, 'pendentes': 0, 'proximas': 0}

        total = rastreamento.entregas.count()
        entregues = rastreamento.entregas.filter_by(status='ENTREGUE').count()
        proximas = rastreamento.entregas.filter_by(status='PROXIMO').count()
        pendentes = rastreamento.entregas.filter(
            EntregaRastreada.status.in_(['PENDENTE', 'EM_ROTA'])
        ).count()

        return {
            'total': total,
            'entregues': entregues,
            'pendentes': pendentes,
            'proximas': proximas
        }
