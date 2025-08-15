"""
Serviço de integração com Google Maps API
Autor: Sistema Frete
Data: 2025-08-14
"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import requests
from flask import current_app
from sqlalchemy import and_, or_, func
from app import db
from app.carteira.models import CarteiraPrincipal
from app.producao.models import CadastroPalletizacao
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.veiculos.models import Veiculo
import logging

logger = logging.getLogger(__name__)

class MapaService:
    """Serviço para integração com Google Maps API e visualização geográfica de pedidos"""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_MAPS_API_KEY', '')
        self.geocoding_cache = {}  # Cache em memória para geocodificação
        self.base_geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"
        self.base_directions_url = "https://maps.googleapis.com/maps/api/directions/json"
        self.base_distance_matrix_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        
        # Endereço do CD - Nacom Goya em Santana de Parnaíba
        self.nome_cd = "Nacom Goya Ind E Comércio De Alimentos LTDA"
        self.endereco_cd = "R. Victório Marchezine, 61 - Parque dos Eucaliptos (Fazendinha), Santana de Parnaíba - SP, 06530-581, Brazil"
        self.coordenadas_cd = {
            'lat': -23.409447293705245,  # Coordenadas exatas fornecidas
            'lng': -46.89113812682363
        }
        
    def obter_pedidos_para_mapa(self, pedido_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Obtém dados dos pedidos selecionados para exibição no mapa
        
        Args:
            pedido_ids: Lista de IDs dos pedidos selecionados
            
        Returns:
            Lista de dicionários com dados dos pedidos formatados para o mapa
        """
        try:
            # Buscar pedidos da carteira com JOIN para CadastroPalletizacao
            pedidos_query = db.session.query(
                CarteiraPrincipal.num_pedido,
                CarteiraPrincipal.cnpj_cpf,
                CarteiraPrincipal.raz_social_red,
                CarteiraPrincipal.municipio,
                CarteiraPrincipal.estado,
                CarteiraPrincipal.expedicao,
                CarteiraPrincipal.agendamento,
                CarteiraPrincipal.protocolo,
                CarteiraPrincipal.observ_ped_1,
                # Endereço de entrega
                CarteiraPrincipal.cnpj_endereco_ent,
                CarteiraPrincipal.empresa_endereco_ent,
                CarteiraPrincipal.cep_endereco_ent,
                CarteiraPrincipal.nome_cidade,
                CarteiraPrincipal.cod_uf,
                CarteiraPrincipal.bairro_endereco_ent,
                CarteiraPrincipal.rua_endereco_ent,
                CarteiraPrincipal.endereco_ent,
                CarteiraPrincipal.telefone_endereco_ent,
                # Totais usando CadastroPalletizacao para peso e pallet corretos
                func.coalesce(func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido), 0).label('valor_total'),
                func.coalesce(func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CadastroPalletizacao.peso_bruto), 0).label('peso_total'),
                func.coalesce(func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido / CadastroPalletizacao.palletizacao), 0).label('pallet_total'),
                func.count(CarteiraPrincipal.cod_produto).label('total_itens')
            ).outerjoin(
                CadastroPalletizacao,
                CarteiraPrincipal.cod_produto == CadastroPalletizacao.cod_produto
            ).filter(
                CarteiraPrincipal.num_pedido.in_(pedido_ids)
            ).group_by(
                CarteiraPrincipal.num_pedido,
                CarteiraPrincipal.cnpj_cpf,
                CarteiraPrincipal.raz_social_red,
                CarteiraPrincipal.municipio,
                CarteiraPrincipal.estado,
                CarteiraPrincipal.expedicao,
                CarteiraPrincipal.agendamento,
                CarteiraPrincipal.protocolo,
                CarteiraPrincipal.observ_ped_1,
                CarteiraPrincipal.cnpj_endereco_ent,
                CarteiraPrincipal.empresa_endereco_ent,
                CarteiraPrincipal.cep_endereco_ent,
                CarteiraPrincipal.nome_cidade,
                CarteiraPrincipal.cod_uf,
                CarteiraPrincipal.bairro_endereco_ent,
                CarteiraPrincipal.rua_endereco_ent,
                CarteiraPrincipal.endereco_ent,
                CarteiraPrincipal.telefone_endereco_ent
            ).all()
            
            pedidos_mapa = []
            
            for pedido in pedidos_query:
                # Montar endereço completo
                endereco_completo = self._montar_endereco_completo(pedido)
                
                # Obter coordenadas (geocodificação)
                lat, lng = self.geocodificar_endereco(endereco_completo)
                
                if lat and lng:
                    pedido_info = {
                        'num_pedido': pedido.num_pedido,
                        'cliente': {
                            'cnpj': pedido.cnpj_cpf,
                            'nome': pedido.raz_social_red or pedido.empresa_endereco_ent,
                            'telefone': pedido.telefone_endereco_ent
                        },
                        'endereco': {
                            'completo': endereco_completo,
                            'rua': pedido.rua_endereco_ent,
                            'numero': pedido.endereco_ent,
                            'bairro': pedido.bairro_endereco_ent,
                            'cidade': pedido.nome_cidade or pedido.municipio,
                            'uf': pedido.cod_uf or pedido.estado,
                            'cep': pedido.cep_endereco_ent
                        },
                        'coordenadas': {
                            'lat': lat,
                            'lng': lng
                        },
                        'valores': {
                            'total': float(pedido.valor_total or 0),
                            'peso': float(pedido.peso_total or 0),
                            'pallet': float(pedido.pallet_total or 0),
                            'itens': pedido.total_itens
                        },
                        'datas': {
                            'expedicao': pedido.expedicao.strftime('%d/%m/%Y') if pedido.expedicao else None,
                            'agendamento': pedido.agendamento.strftime('%d/%m/%Y') if pedido.agendamento else None,
                            'protocolo': pedido.protocolo
                        },
                        'observacoes': pedido.observ_ped_1,
                        'status': self._determinar_status_pedido(pedido)
                    }
                    pedidos_mapa.append(pedido_info)
                else:
                    logger.warning(f"Não foi possível geocodificar o endereço do pedido {pedido.num_pedido}")
                    
            return pedidos_mapa
            
        except Exception as e:
            logger.error(f"Erro ao obter pedidos para mapa: {str(e)}")
            return []
            
    def _montar_endereco_completo(self, pedido) -> str:
        """Monta o endereço completo para geocodificação"""
        partes = []
        
        if pedido.rua_endereco_ent:
            partes.append(pedido.rua_endereco_ent)
        if pedido.endereco_ent:
            partes.append(f"nº {pedido.endereco_ent}")
        if pedido.bairro_endereco_ent:
            partes.append(pedido.bairro_endereco_ent)
            
        cidade = pedido.nome_cidade or pedido.municipio
        if cidade:
            partes.append(cidade)
            
        uf = pedido.cod_uf or pedido.estado
        if uf:
            partes.append(uf)
            
        if pedido.cep_endereco_ent:
            partes.append(f"CEP {pedido.cep_endereco_ent}")
            
        partes.append("Brasil")
        
        return ", ".join(filter(None, partes))
        
    def _determinar_status_pedido(self, pedido) -> str:
        """Determina o status do pedido para visualização"""
        if pedido.agendamento and pedido.protocolo:
            return "agendado"
        elif pedido.expedicao:
            if pedido.expedicao <= datetime.now().date():
                return "atrasado"
            elif pedido.expedicao <= datetime.now().date() + timedelta(days=3):
                return "urgente"
            else:
                return "normal"
        return "pendente"
        
    def geocodificar_endereco(self, endereco: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Geocodifica um endereço usando Google Maps API
        
        Args:
            endereco: Endereço completo para geocodificar
            
        Returns:
            Tupla com latitude e longitude, ou (None, None) se falhar
        """
        try:
            # Verificar cache
            cache_key = hashlib.md5(endereco.encode()).hexdigest()
            if cache_key in self.geocoding_cache:
                return self.geocoding_cache[cache_key]
                
            # Fazer requisição para API
            params = {
                'address': endereco,
                'key': self.api_key,
                'region': 'br',
                'language': 'pt-BR'
            }
            
            response = requests.get(self.base_geocoding_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data['status'] == 'OK' and data['results']:
                    location = data['results'][0]['geometry']['location']
                    lat = location['lat']
                    lng = location['lng']
                    
                    # Salvar no cache
                    self.geocoding_cache[cache_key] = (lat, lng)
                    
                    return lat, lng
                    
            return None, None
            
        except Exception as e:
            logger.error(f"Erro ao geocodificar endereço: {str(e)}")
            return None, None
            
    def calcular_rota_otimizada(self, pedido_ids: List[str], origem: Optional[str] = None) -> Dict[str, Any]:
        """
        Calcula a rota otimizada para entrega dos pedidos
        
        Args:
            pedido_ids: Lista de IDs dos pedidos
            origem: Endereço de origem (padrão: CD Nacom Goya)
            
        Returns:
            Dicionário com a rota otimizada e estatísticas
        """
        try:
            # Obter dados dos pedidos
            pedidos = self.obter_pedidos_para_mapa(pedido_ids)
            
            if not pedidos:
                return {'erro': 'Nenhum pedido encontrado'}
                
            # Usar CD Nacom Goya como origem padrão
            if not origem:
                origem = self.endereco_cd
                
            # Preparar waypoints
            waypoints = []
            for pedido in pedidos:
                waypoints.append({
                    'location': f"{pedido['coordenadas']['lat']},{pedido['coordenadas']['lng']}",
                    'pedido': pedido['num_pedido']
                })
                
            # Otimizar rota usando Google Directions API
            # Se tiver apenas 1 pedido, destino é ele mesmo
            # Se tiver mais, otimizar e terminar no último
            if len(waypoints) == 1:
                destination = waypoints[0]['location']
                waypoints_param = None
            else:
                # Usar o último waypoint como destino (não voltar ao CD)
                destination = waypoints[-1]['location']
                waypoints_param = 'optimize:true|' + '|'.join([w['location'] for w in waypoints[:-1]])
            
            params = {
                'origin': origem,
                'destination': destination,  # Terminar na última entrega
                'key': self.api_key,
                'language': 'pt-BR',
                'mode': 'driving',
                'units': 'metric',
                'avoid': 'ferries'  # Evitar balsas
            }
            
            if waypoints_param:
                params['waypoints'] = waypoints_param
            
            response = requests.get(self.base_directions_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data['status'] == 'OK' and data['routes']:
                    route = data['routes'][0]
                    
                    # Processar ordem otimizada
                    ordem_otimizada = []
                    if 'waypoint_order' in route:
                        for idx in route['waypoint_order']:
                            ordem_otimizada.append(waypoints[idx]['pedido'])
                            
                    # Extrair informações da rota
                    total_distance = sum(leg['distance']['value'] for leg in route['legs'])
                    total_duration = sum(leg['duration']['value'] for leg in route['legs'])
                    
                    # Calcular peso total e selecionar veículo
                    peso_total = sum(p['valores']['peso'] for p in pedidos)
                    veiculo_selecionado = self._selecionar_veiculo_adequado(peso_total)
                    
                    # Calcular pedágio estimado
                    pedagio_estimado = self._calcular_pedagio_estimado(
                        total_distance / 1000,
                        veiculo_selecionado
                    )
                    
                    return {
                        'sucesso': True,
                        'rota': {
                            'ordem_pedidos': ordem_otimizada,
                            'distancia_total_km': total_distance / 1000,
                            'tempo_total_minutos': total_duration / 60,
                            'tempo_formatado': self._formatar_tempo(total_duration),
                            'polyline': route['overview_polyline']['points'],
                            'bounds': route['bounds'],
                            'legs': [
                                {
                                    'distancia': leg['distance']['text'],
                                    'duracao': leg['duration']['text'],
                                    'endereco_inicio': leg['start_address'],
                                    'endereco_fim': leg['end_address']
                                }
                                for leg in route['legs']
                            ]
                        },
                        'estatisticas': {
                            'total_pedidos': len(pedidos),
                            'valor_total': sum(p['valores']['total'] for p in pedidos),
                            'peso_total': peso_total,
                            'pallet_total': sum(p['valores']['pallet'] for p in pedidos),
                            'custo_estimado_km': (total_distance / 1000) * 2.5  # R$ 2.50 por km (configurável)
                        },
                        'veiculo': {
                            'nome': veiculo_selecionado.nome if veiculo_selecionado else 'Não definido',
                            'peso_maximo': veiculo_selecionado.peso_maximo if veiculo_selecionado else 0,
                            'tipo': veiculo_selecionado.tipo_veiculo if veiculo_selecionado else 'Não definido',
                            'eixos': veiculo_selecionado.qtd_eixos if veiculo_selecionado else 2,
                            'multiplicador_pedagio': veiculo_selecionado.multiplicador_pedagio if veiculo_selecionado else 1.0
                        },
                        'pedagio': pedagio_estimado
                    }
                    
            return {'erro': 'Não foi possível calcular a rota'}
            
        except Exception as e:
            logger.error(f"Erro ao calcular rota otimizada: {str(e)}")
            return {'erro': str(e)}
            
    def _formatar_tempo(self, segundos: int) -> str:
        """Formata tempo em segundos para formato legível"""
        horas = segundos // 3600
        minutos = (segundos % 3600) // 60
        
        if horas > 0:
            return f"{horas}h {minutos}min"
        return f"{minutos}min"
    
    def _selecionar_veiculo_adequado(self, peso_total: float) -> Optional[Veiculo]:
        """
        Seleciona o menor veículo capaz de transportar o peso total
        
        Args:
            peso_total: Peso total em kg
            
        Returns:
            Veículo selecionado ou None
        """
        try:
            # Buscar veículos ordenados por peso máximo (menor primeiro)
            veiculos = Veiculo.query.filter(
                Veiculo.peso_maximo >= peso_total
            ).order_by(
                Veiculo.peso_maximo.asc()
            ).first()
            
            if not veiculos:
                # Se nenhum veículo comporta, pegar o maior disponível
                veiculos = Veiculo.query.order_by(
                    Veiculo.peso_maximo.desc()
                ).first()
                
            return veiculos
            
        except Exception as e:
            logger.error(f"Erro ao selecionar veículo: {str(e)}")
            return None
    
    def _calcular_pedagio_estimado(self, distancia_km: float, veiculo: Optional[Veiculo]) -> Dict[str, Any]:
        """
        Calcula estimativa de pedágio baseado na distância e tipo de veículo
        
        Args:
            distancia_km: Distância total em km
            veiculo: Veículo selecionado
            
        Returns:
            Dicionário com estimativas de pedágio
        """
        try:
            # Estimativas baseadas em médias do Brasil
            # Praças a cada 40-50km em rodovias pedagiadas
            # Valor médio por praça para carro: R$ 5-15
            
            # Estimar número de praças (conservador)
            # Considerando que nem toda a rota é pedagiada (aprox 60% em SP)
            percentual_pedagiado = 0.6
            distancia_pedagiada = distancia_km * percentual_pedagiado
            
            # Uma praça a cada 45km em média
            num_pracas_estimado = max(1, int(distancia_pedagiada / 45))
            
            # Valor base por praça (média SP)
            valor_base_praca = 8.50  # Valor médio para carro em SP
            
            # Aplicar multiplicador do veículo
            multiplicador = veiculo.multiplicador_pedagio if veiculo else 1.0
            valor_por_praca = valor_base_praca * multiplicador
            
            # Calcular total
            valor_total = num_pracas_estimado * valor_por_praca
            
            return {
                'estimado': True,
                'valor_total': round(valor_total, 2),
                'num_pracas_estimado': num_pracas_estimado,
                'valor_medio_praca': round(valor_por_praca, 2),
                'valor_base_carro': valor_base_praca,
                'multiplicador_veiculo': multiplicador,
                'distancia_pedagiada_km': round(distancia_pedagiada, 1),
                'observacao': f'Estimativa para {num_pracas_estimado} praça(s) de pedágio'
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular pedágio: {str(e)}")
            return {
                'estimado': True,
                'valor_total': 0,
                'erro': str(e)
            }
        
    def analisar_densidade_regional(self, pedido_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analisa a densidade de pedidos por região
        
        Args:
            pedido_ids: Lista opcional de IDs de pedidos (None = todos)
            
        Returns:
            Dicionário com análise de densidade por região
        """
        try:
            # Query base com JOIN para CadastroPalletizacao
            query = db.session.query(
                CarteiraPrincipal.cod_uf,
                CarteiraPrincipal.nome_cidade,
                func.count(func.distinct(CarteiraPrincipal.num_pedido)).label('total_pedidos'),
                func.coalesce(func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido), 0).label('valor_total'),
                func.coalesce(func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CadastroPalletizacao.peso_bruto), 0).label('peso_total'),
                func.coalesce(func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido / CadastroPalletizacao.palletizacao), 0).label('pallet_total')
            ).outerjoin(
                CadastroPalletizacao,
                CarteiraPrincipal.cod_produto == CadastroPalletizacao.cod_produto
            )
            
            if pedido_ids:
                query = query.filter(CarteiraPrincipal.num_pedido.in_(pedido_ids))
                
            # Agrupar por região
            resultado = query.group_by(
                CarteiraPrincipal.cod_uf,
                CarteiraPrincipal.nome_cidade
            ).order_by(
                func.count(func.distinct(CarteiraPrincipal.num_pedido)).desc()
            ).all()
            
            # Processar resultados
            densidade = {
                'por_estado': {},
                'por_cidade': [],
                'resumo': {
                    'total_estados': 0,
                    'total_cidades': 0,
                    'total_pedidos': 0,
                    'valor_total': 0,
                    'peso_total': 0,
                    'pallet_total': 0
                }
            }
            
            for item in resultado:
                uf = item.cod_uf or 'ND'
                cidade = item.nome_cidade or 'Não definida'
                
                # Agregar por estado
                if uf not in densidade['por_estado']:
                    densidade['por_estado'][uf] = {
                        'total_pedidos': 0,
                        'valor_total': 0,
                        'peso_total': 0,
                        'pallet_total': 0,
                        'cidades': []
                    }
                    
                densidade['por_estado'][uf]['total_pedidos'] += item.total_pedidos
                densidade['por_estado'][uf]['valor_total'] += float(item.valor_total or 0)
                densidade['por_estado'][uf]['peso_total'] += float(item.peso_total or 0)
                densidade['por_estado'][uf]['pallet_total'] += float(item.pallet_total or 0)
                densidade['por_estado'][uf]['cidades'].append(cidade)
                
                # Adicionar cidade
                densidade['por_cidade'].append({
                    'cidade': cidade,
                    'uf': uf,
                    'total_pedidos': item.total_pedidos,
                    'valor_total': float(item.valor_total or 0),
                    'peso_total': float(item.peso_total or 0),
                    'pallet_total': float(item.pallet_total or 0)
                })
                
                # Atualizar resumo
                densidade['resumo']['total_pedidos'] += item.total_pedidos
                densidade['resumo']['valor_total'] += float(item.valor_total or 0)
                densidade['resumo']['peso_total'] += float(item.peso_total or 0)
                densidade['resumo']['pallet_total'] += float(item.pallet_total or 0)
                
            densidade['resumo']['total_estados'] = len(densidade['por_estado'])
            densidade['resumo']['total_cidades'] = len(densidade['por_cidade'])
            
            # Adicionar análises
            densidade['analises'] = self._gerar_analises_densidade(densidade)
            
            return densidade
            
        except Exception as e:
            logger.error(f"Erro ao analisar densidade regional: {str(e)}")
            return {}
            
    def _gerar_analises_densidade(self, densidade: Dict[str, Any]) -> Dict[str, Any]:
        """Gera análises e insights sobre a densidade regional"""
        analises = {
            'concentracao': [],
            'oportunidades': [],
            'sugestoes': []
        }
        
        # Análise de concentração
        if densidade['por_estado']:
            estados_ordenados = sorted(
                densidade['por_estado'].items(),
                key=lambda x: x[1]['total_pedidos'],
                reverse=True
            )
            
            # Top 3 estados
            top_estados = estados_ordenados[:3]
            for uf, dados in top_estados:
                percentual = (dados['total_pedidos'] / densidade['resumo']['total_pedidos']) * 100
                analises['concentracao'].append({
                    'uf': uf,
                    'percentual': round(percentual, 1),
                    'pedidos': dados['total_pedidos']
                })
                
        # Identificar oportunidades
        if densidade['por_cidade']:
            # Cidades com alta demanda
            cidades_alta_demanda = [
                c for c in densidade['por_cidade']
                if c['total_pedidos'] >= 5
            ]
            
            if cidades_alta_demanda:
                analises['oportunidades'].append({
                    'tipo': 'consolidacao',
                    'descricao': f"Consolidar cargas para {len(cidades_alta_demanda)} cidades com alta demanda",
                    'cidades': [c['cidade'] for c in cidades_alta_demanda[:5]]
                })
                
        # Sugestões de otimização
        if densidade['resumo']['total_pedidos'] > 10:
            analises['sugestoes'].append({
                'tipo': 'agrupamento',
                'descricao': 'Considere agrupar pedidos por região para reduzir custos de frete'
            })
            
        if densidade['resumo']['pallet_total'] > 20:
            analises['sugestoes'].append({
                'tipo': 'carga_fechada',
                'descricao': 'Volume suficiente para considerar carga fechada'
            })
            
        return analises
        
    def calcular_matriz_distancias(self, pedido_ids: List[str]) -> Dict[str, Any]:
        """
        Calcula matriz de distâncias entre todos os pedidos
        
        Args:
            pedido_ids: Lista de IDs dos pedidos
            
        Returns:
            Matriz de distâncias e tempos entre os pedidos
        """
        try:
            # Obter dados dos pedidos
            pedidos = self.obter_pedidos_para_mapa(pedido_ids)
            
            if len(pedidos) < 2:
                return {'erro': 'Necessário pelo menos 2 pedidos para calcular matriz'}
                
            # Limitar a 10 pedidos por vez (limite da API)
            if len(pedidos) > 10:
                pedidos = pedidos[:10]
                
            # Preparar origens e destinos
            locations = []
            for pedido in pedidos:
                locations.append(f"{pedido['coordenadas']['lat']},{pedido['coordenadas']['lng']}")
                
            # Chamar Distance Matrix API
            params = {
                'origins': '|'.join(locations),
                'destinations': '|'.join(locations),
                'key': self.api_key,
                'language': 'pt-BR',
                'mode': 'driving',
                'units': 'metric'
            }
            
            response = requests.get(self.base_distance_matrix_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data['status'] == 'OK':
                    # Processar matriz
                    matriz = {
                        'pedidos': [p['num_pedido'] for p in pedidos],
                        'distancias': [],
                        'tempos': [],
                        'resumo': {
                            'distancia_media_km': 0,
                            'tempo_medio_min': 0,
                            'pares_proximos': [],
                            'pares_distantes': []
                        }
                    }
                    
                    total_distancia = 0
                    total_tempo = 0
                    pares = []
                    
                    for i, row in enumerate(data['rows']):
                        dist_row = []
                        tempo_row = []
                        
                        for j, element in enumerate(row['elements']):
                            if element['status'] == 'OK':
                                distancia = element['distance']['value'] / 1000  # km
                                tempo = element['duration']['value'] / 60  # minutos
                                
                                dist_row.append(round(distancia, 1))
                                tempo_row.append(round(tempo, 0))
                                
                                if i != j:
                                    total_distancia += distancia
                                    total_tempo += tempo
                                    
                                    pares.append({
                                        'origem': pedidos[i]['num_pedido'],
                                        'destino': pedidos[j]['num_pedido'],
                                        'distancia': distancia,
                                        'tempo': tempo
                                    })
                            else:
                                dist_row.append(None)
                                tempo_row.append(None)
                                
                        matriz['distancias'].append(dist_row)
                        matriz['tempos'].append(tempo_row)
                        
                    # Calcular médias
                    if pares:
                        matriz['resumo']['distancia_media_km'] = round(total_distancia / len(pares), 1)
                        matriz['resumo']['tempo_medio_min'] = round(total_tempo / len(pares), 0)
                        
                        # Identificar pares próximos e distantes
                        pares_ordenados = sorted(pares, key=lambda x: x['distancia'])
                        matriz['resumo']['pares_proximos'] = pares_ordenados[:3]
                        matriz['resumo']['pares_distantes'] = pares_ordenados[-3:]
                        
                    return matriz
                    
            return {'erro': 'Não foi possível calcular matriz de distâncias'}
            
        except Exception as e:
            logger.error(f"Erro ao calcular matriz de distâncias: {str(e)}")
            return {'erro': str(e)}