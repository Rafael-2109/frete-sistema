"""
📍 SERVIÇO DE CÁLCULOS GPS
Cálculo de distâncias, proximidade e geocoding com Google Maps API
"""

from haversine import haversine, Unit
from flask import current_app
import os
import hashlib
import requests
import cachetools


class GPSService:
    """Serviço para cálculos geográficos e GPS"""

    # Configuração do Google Maps API
    _api_key = None
    _geocoding_cache = cachetools.TTLCache(maxsize=500, ttl=3600)
    _base_geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"

    @classmethod
    def _get_api_key(cls):
        """Obtém API key do Google Maps (lazy loading)"""
        if cls._api_key is None:
            cls._api_key = os.getenv('GOOGLE_MAPS_API_KEY', '')
            if not cls._api_key:
                current_app.logger.warning("⚠️ GOOGLE_MAPS_API_KEY não configurada")
        return cls._api_key

    @staticmethod
    def calcular_distancia(coord1, coord2, unidade='metros'):
        """
        Calcula a distância entre duas coordenadas GPS usando fórmula de Haversine

        Args:
            coord1 (tuple): (latitude, longitude) do ponto 1
            coord2 (tuple): (latitude, longitude) do ponto 2
            unidade (str): 'metros', 'km', 'milhas' (padrão: metros)

        Returns:
            float: Distância na unidade especificada
        """
        try:
            # Validar coordenadas
            if not coord1 or not coord2:
                return None
            if len(coord1) != 2 or len(coord2) != 2:
                return None

            # Calcular distância
            if unidade == 'metros':
                distancia = haversine(coord1, coord2, unit=Unit.METERS)
            elif unidade == 'km':
                distancia = haversine(coord1, coord2, unit=Unit.KILOMETERS)
            elif unidade == 'milhas':
                distancia = haversine(coord1, coord2, unit=Unit.MILES)
            else:
                distancia = haversine(coord1, coord2, unit=Unit.METERS)

            return round(distancia, 2)

        except Exception as e:
            current_app.logger.error(f"Erro ao calcular distância: {str(e)}")
            return None

    @staticmethod
    def esta_proximo(coord_atual, coord_destino, raio_metros=200):
        """
        Verifica se a coordenada atual está próxima do destino

        Args:
            coord_atual (tuple): (latitude, longitude) posição atual
            coord_destino (tuple): (latitude, longitude) destino
            raio_metros (float): Raio de proximidade em metros (padrão: 200)

        Returns:
            bool: True se está dentro do raio, False caso contrário
        """
        try:
            distancia = GPSService.calcular_distancia(coord_atual, coord_destino, 'metros')
            if distancia is None:
                return False

            return distancia <= raio_metros

        except Exception as e:
            current_app.logger.error(f"Erro ao verificar proximidade: {str(e)}")
            return False

    @classmethod
    def geocode_endereco(cls, endereco, timeout=10):
        """
        Converte endereço em coordenadas GPS usando Google Maps Geocoding API

        Args:
            endereco (str): Endereço completo
            timeout (int): Timeout em segundos (padrão: 10)

        Returns:
            tuple: (latitude, longitude) ou None se falhar
        """
        try:
            # Verificar cache primeiro
            cache_key = hashlib.md5(endereco.encode()).hexdigest()
            if cache_key in cls._geocoding_cache:
                current_app.logger.debug(f"📍 Geocoding (cache): {endereco[:50]}...")
                return cls._geocoding_cache[cache_key]

            # Obter API key
            api_key = cls._get_api_key()
            if not api_key:
                current_app.logger.error("❌ Google Maps API key não configurada")
                return None

            # Fazer requisição para Google Maps API
            params = {
                'address': endereco,
                'key': api_key,
                'region': 'br',
                'language': 'pt-BR'
            }

            response = requests.get(cls._base_geocoding_url, params=params, timeout=timeout)

            if response.status_code == 200:
                data = response.json()

                if data['status'] == 'OK' and data['results']:
                    location = data['results'][0]['geometry']['location']
                    lat = location['lat']
                    lng = location['lng']

                    # Salvar no cache
                    cls._geocoding_cache[cache_key] = (lat, lng)

                    current_app.logger.info(f"✅ Geocoding sucesso: {endereco[:50]}... → ({lat:.6f}, {lng:.6f})")
                    return (lat, lng)
                elif data['status'] == 'ZERO_RESULTS':
                    current_app.logger.warning(f"⚠️ Nenhum resultado para: {endereco[:50]}...")
                    return None
                elif data['status'] == 'OVER_QUERY_LIMIT':
                    current_app.logger.error("❌ Limite de requisições da API excedido")
                    return None
                else:
                    current_app.logger.warning(f"⚠️ Google Maps API retornou: {data['status']}")
                    return None

            current_app.logger.error(f"❌ Erro HTTP {response.status_code} ao geocodificar")
            return None

        except requests.exceptions.Timeout:
            current_app.logger.error(f"❌ Timeout ao geocodificar: {endereco[:50]}...")
            return None
        except Exception as e:
            current_app.logger.error(f"❌ Erro inesperado no geocoding: {str(e)}")
            return None

    @classmethod
    def reverse_geocode(cls, latitude, longitude, timeout=10):
        """
        Converte coordenadas GPS em endereço usando Google Maps Reverse Geocoding API

        Args:
            latitude (float): Latitude
            longitude (float): Longitude
            timeout (int): Timeout em segundos (padrão: 10)

        Returns:
            str: Endereço formatado ou None
        """
        try:
            # Obter API key
            api_key = cls._get_api_key()
            if not api_key:
                current_app.logger.error("❌ Google Maps API key não configurada")
                return None

            # Fazer requisição para Google Maps API
            params = {
                'latlng': f"{latitude},{longitude}",
                'key': api_key,
                'language': 'pt-BR'
            }

            response = requests.get(cls._base_geocoding_url, params=params, timeout=timeout)

            if response.status_code == 200:
                data = response.json()

                if data['status'] == 'OK' and data['results']:
                    endereco = data['results'][0]['formatted_address']
                    current_app.logger.info(f"✅ Reverse geocoding: ({latitude:.6f}, {longitude:.6f}) → {endereco[:50]}...")
                    return endereco

            return None

        except requests.exceptions.Timeout:
            current_app.logger.error(f"❌ Timeout no reverse geocoding")
            return None
        except Exception as e:
            current_app.logger.error(f"❌ Erro no reverse geocoding: {str(e)}")
            return None

    @staticmethod
    def obter_coordenadas_embarque(embarque):
        """
        Obtém coordenadas GPS do destino de um embarque
        USANDO ENDEREÇO COMPLETO da CarteiraPrincipal (mesma fonte do mapa_service.py)

        Args:
            embarque: Objeto Embarque

        Returns:
            tuple: (latitude, longitude) ou None se não conseguir geocode
        """
        try:
            # Verifica se há itens no embarque
            if not embarque.itens or len(embarque.itens) == 0:
                return None

            item = embarque.itens[0]

            # 🔄 BUSCAR DADOS COMPLETOS DA CARTEIRA (mesma fonte do mapa_service.py)
            from app.carteira.models import CarteiraPrincipal

            # Buscar pedido original na CarteiraPrincipal
            pedido_carteira = CarteiraPrincipal.query.filter_by(
                num_pedido=item.pedido
            ).first()

            if pedido_carteira:
                # ✅ MONTAR ENDEREÇO COMPLETO (igual ao mapa_service.py)
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

                endereco_busca = ", ".join(filter(None, partes))

                current_app.logger.info(f"📍 Geocoding endereço completo: {endereco_busca}")
            else:
                # Fallback: usar apenas cidade + UF (método antigo)
                endereco_busca = f"{item.cidade_destino}, {item.uf_destino}, Brasil"
                current_app.logger.warning(f"⚠️ Pedido não encontrado na carteira, usando fallback: {endereco_busca}")

            # Faz geocoding
            coordenadas = GPSService.geocode_endereco(endereco_busca)

            if coordenadas:
                current_app.logger.info(f"✅ Geocoding sucesso para embarque #{embarque.numero}: {coordenadas}")
            else:
                current_app.logger.warning(f"❌ Não foi possível geocodificar: {endereco_busca}")

            return coordenadas

        except Exception as e:
            current_app.logger.error(f"Erro ao obter coordenadas do embarque: {str(e)}")
            return None

    @staticmethod
    def validar_coordenadas(latitude, longitude):
        """
        Valida se as coordenadas estão em formato válido

        Args:
            latitude (float): Latitude (-90 a 90)
            longitude (float): Longitude (-180 a 180)

        Returns:
            bool: True se válidas, False caso contrário
        """
        try:
            lat = float(latitude)
            lon = float(longitude)

            # Validar ranges
            if lat < -90 or lat > 90:
                return False
            if lon < -180 or lon > 180:
                return False

            return True

        except (ValueError, TypeError):
            return False

    @staticmethod
    def formatar_distancia(metros):
        """
        Formata distância em metros para exibição amigável

        Args:
            metros (float): Distância em metros

        Returns:
            str: Distância formatada (ex: "1,5 km" ou "350 m")
        """
        if metros is None:
            return "N/A"

        if metros >= 1000:
            km = metros / 1000
            return f"{km:.1f} km"
        else:
            return f"{int(metros)} m"

    @staticmethod
    def calcular_velocidade_kmh(coord1, coord2, tempo_segundos):
        """
        Calcula velocidade média entre dois pontos

        Args:
            coord1 (tuple): (lat, lon) ponto inicial
            coord2 (tuple): (lat, lon) ponto final
            tempo_segundos (int): Tempo decorrido em segundos

        Returns:
            float: Velocidade em km/h ou None
        """
        try:
            if tempo_segundos <= 0:
                return None

            distancia_km = GPSService.calcular_distancia(coord1, coord2, 'km')
            if distancia_km is None:
                return None

            tempo_horas = tempo_segundos / 3600
            velocidade = distancia_km / tempo_horas

            return round(velocidade, 2)

        except Exception as e:
            current_app.logger.error(f"Erro ao calcular velocidade: {str(e)}")
            return None
