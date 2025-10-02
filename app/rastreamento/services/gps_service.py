"""
📍 SERVIÇO DE CÁLCULOS GPS
Cálculo de distâncias, proximidade e geocoding
"""

from haversine import haversine, Unit
from geopy.geocoders import Nominatim
from geopy.exc import GeopyError
from flask import current_app
import time


class GPSService:
    """Serviço para cálculos geográficos e GPS"""

    # Configuração do geocoder
    geocoder = Nominatim(user_agent="sistema_frete_nacom/1.0")

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

    @staticmethod
    def geocode_endereco(endereco, timeout=5):
        """
        Converte endereço em coordenadas GPS (geocoding)

        Args:
            endereco (str): Endereço completo
            timeout (int): Timeout em segundos (padrão: 5)

        Returns:
            tuple: (latitude, longitude) ou None se falhar
        """
        try:
            location = GPSService.geocoder.geocode(endereco, timeout=timeout)
            if location:
                return (location.latitude, location.longitude)
            return None

        except GeopyError as e:
            current_app.logger.error(f"Erro de geocoding: {str(e)}")
            return None
        except Exception as e:
            current_app.logger.error(f"Erro inesperado no geocoding: {str(e)}")
            return None

    @staticmethod
    def reverse_geocode(latitude, longitude, timeout=5):
        """
        Converte coordenadas GPS em endereço (reverse geocoding)

        Args:
            latitude (float): Latitude
            longitude (float): Longitude
            timeout (int): Timeout em segundos

        Returns:
            str: Endereço formatado ou None
        """
        try:
            location = GPSService.geocoder.reverse(f"{latitude}, {longitude}", timeout=timeout)
            if location:
                return location.address
            return None

        except GeopyError as e:
            current_app.logger.error(f"Erro de reverse geocoding: {str(e)}")
            return None
        except Exception as e:
            current_app.logger.error(f"Erro inesperado no reverse geocoding: {str(e)}")
            return None

    @staticmethod
    def obter_coordenadas_embarque(embarque):
        """
        Obtém coordenadas GPS do destino de um embarque

        Args:
            embarque: Objeto Embarque

        Returns:
            tuple: (latitude, longitude) ou None se não conseguir geocode
        """
        try:
            # Verifica se há itens no embarque
            if not embarque.itens or len(embarque.itens) == 0:
                return None

            # Pega o primeiro item para obter cidade/UF de destino
            item = embarque.itens[0]
            endereco_busca = f"{item.cidade_destino}, {item.uf_destino}, Brasil"

            # Faz geocoding
            coordenadas = GPSService.geocode_endereco(endereco_busca)

            if coordenadas:
                current_app.logger.info(f"Geocoding sucesso para embarque #{embarque.numero}: {coordenadas}")
            else:
                current_app.logger.warning(f"Não foi possível geocodificar: {endereco_busca}")

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
