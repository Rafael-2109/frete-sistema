"""
Serviço de integração com Google Maps API
Autor: Sistema Frete
Data: 2025-08-14
"""

import os
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import requests
import cachetools
from sqlalchemy import func, or_
from app import db
from app.carteira.models import CarteiraPrincipal
from app.producao.models import CadastroPalletizacao
from app.veiculos.models import Veiculo
from app.separacao.models import Separacao
import logging

logger = logging.getLogger(__name__)

class MapaService:
    """Serviço para integração com Google Maps API e visualização geográfica de pedidos"""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_MAPS_API_KEY', '')
        self.geocoding_cache = cachetools.TTLCache(maxsize=500, ttl=3600)
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
            # NOTA: Campos expedicao, agendamento, protocolo removidos de CarteiraPrincipal
            # Esses dados agora vêm apenas de Separacao
            pedidos_query = db.session.query(
                CarteiraPrincipal.num_pedido,
                CarteiraPrincipal.cnpj_cpf,
                CarteiraPrincipal.raz_social_red,
                CarteiraPrincipal.municipio,
                CarteiraPrincipal.estado,
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
                            'expedicao': None,  # Removido de CarteiraPrincipal - usar Separacao
                            'agendamento': None,  # Removido de CarteiraPrincipal - usar Separacao
                            'protocolo': None  # Removido de CarteiraPrincipal - usar Separacao
                        },
                        'observacoes': pedido.observ_ped_1,
                        'status': 'pendente'  # Simplificado - dados de agendamento agora em Separacao
                    }
                    pedidos_mapa.append(pedido_info)
                else:
                    logger.warning(f"Não foi possível geocodificar o endereço do pedido {pedido.num_pedido}")
                    
            return pedidos_mapa

        except Exception as e:
            logger.error(f"Erro ao obter pedidos para mapa: {str(e)}")
            return []

    def obter_clientes_para_mapa(self, pedido_ids: List[str], lotes: List[str] = None) -> List[Dict[str, Any]]:
        """
        Obtém dados dos clientes (agrupados por CNPJ + endereço) para exibição no mapa.
        Cada cliente pode ter múltiplos pedidos.

        FONTE DE DADOS:
        - NACOM:
          - Valores (valor_saldo, peso, pallet): Separacao (sem filtro sincronizado_nf
            para incluir faturados; mantém qtd_saldo > 0 ou nf_cd=True).
          - Endereço de entrega: CarteiraPrincipal.
        - CarVia: CarviaPedido + CarviaCotacao + CarviaClienteEndereco (endereço destino).
          Valores via SUM(CarviaPedidoItem.valor_total).

        Args:
            pedido_ids: Lista de num_pedido (compat legado).
            lotes: Lista de separacao_lote_id — preferido, distingue CarVia via prefixo.

        Returns:
            Lista de dicionários com dados dos clientes e seus pedidos
        """
        try:
            lotes = lotes or []
            pedido_ids = pedido_ids or []

            # Separar lotes CarVia (prefixo) de lotes/pedidos NACOM
            lotes_carvia = [l for l in lotes if str(l).startswith('CARVIA-')]
            lotes_nacom = [l for l in lotes if not str(l).startswith('CARVIA-')]

            # Para compat: pedido_ids podem ser num_pedido NACOM ou CarVia (PED-*).
            # Detectar CarVia via lookup em CarviaPedido.numero_pedido / CarviaCotacao.numero_cotacao
            pedido_ids_nacom, pedido_ids_carvia_extra = self._classificar_pedido_ids(pedido_ids)

            # Buscar nums NACOM via Separacao por separacao_lote_id (lotes_nacom)
            # ou por num_pedido (pedido_ids_nacom)
            sep_filters = []
            if lotes_nacom:
                sep_filters.append(Separacao.separacao_lote_id.in_(lotes_nacom))
            if pedido_ids_nacom:
                sep_filters.append(Separacao.num_pedido.in_(pedido_ids_nacom))

            separacoes = []
            if sep_filters:
                # SEM filtro sincronizado_nf: faturados continuam tendo endereco/coords
                # qtd_saldo > 0 OU nf_cd=True garante registros relevantes
                separacoes = Separacao.query.filter(
                    or_(*sep_filters),
                    or_(
                        Separacao.qtd_saldo > 0,
                        Separacao.nf_cd == True,
                        Separacao.sincronizado_nf == True,  # Faturados (saldo=0 mas tem endereco)
                    )
                ).all()

            # Processar CarVia em paralelo
            clientes_carvia = self._obter_clientes_carvia(
                lotes_carvia, pedido_ids_carvia_extra
            )

            if not separacoes and not clientes_carvia:
                logger.warning(
                    "Nenhum dado encontrado p/ mapa: lotes=%s, pedidos=%s",
                    lotes, pedido_ids,
                )
                return []

            # Agrupar separações por num_pedido (um pedido pode ter múltiplos itens na separação)
            sep_por_pedido = {}
            for sep in separacoes:
                if sep.num_pedido not in sep_por_pedido:
                    sep_por_pedido[sep.num_pedido] = []
                sep_por_pedido[sep.num_pedido].append(sep)

            # 2. Buscar endereços de entrega de CarteiraPrincipal (Separacao não tem esses campos)
            enderecos_raw = db.session.query(
                CarteiraPrincipal.num_pedido,
                CarteiraPrincipal.cnpj_endereco_ent,
                CarteiraPrincipal.empresa_endereco_ent,
                CarteiraPrincipal.cep_endereco_ent,
                CarteiraPrincipal.nome_cidade,
                CarteiraPrincipal.cod_uf,
                CarteiraPrincipal.bairro_endereco_ent,
                CarteiraPrincipal.rua_endereco_ent,
                CarteiraPrincipal.endereco_ent,
                CarteiraPrincipal.telefone_endereco_ent,
                CarteiraPrincipal.municipio,
                CarteiraPrincipal.estado
            ).filter(
                CarteiraPrincipal.num_pedido.in_(list(sep_por_pedido.keys()))
            ).distinct(
                CarteiraPrincipal.num_pedido
            ).all()

            enderecos_dict = {}
            for e in enderecos_raw:
                enderecos_dict[e.num_pedido] = e

            # 3. Agrupar pedidos por cliente (CNPJ + endereço)
            clientes_dict = {}

            for num_pedido, seps in sep_por_pedido.items():
                # Pegar a primeira separação como referência para dados do pedido
                sep_ref = seps[0]

                # Somar valores de todas as separações deste pedido
                valor_total = sum(float(s.valor_saldo or 0) for s in seps)
                peso_total = sum(float(s.peso or 0) for s in seps)
                pallet_total = sum(float(s.pallet or 0) for s in seps)
                total_itens = len(seps)

                # Dados de agendamento (pegar o primeiro que tiver)
                expedicao = None
                agendamento = None
                agendamento_confirmado = False
                protocolo = None
                separacao_lote_id = None

                for s in seps:
                    if s.expedicao and not expedicao:
                        expedicao = s.expedicao.strftime('%d/%m/%Y')
                    if s.agendamento and not agendamento:
                        agendamento = s.agendamento.strftime('%d/%m/%Y')
                    if s.agendamento_confirmado:
                        agendamento_confirmado = True
                    if s.protocolo and not protocolo:
                        protocolo = s.protocolo
                    if s.separacao_lote_id and not separacao_lote_id:
                        separacao_lote_id = s.separacao_lote_id

                # Obter endereço de entrega de CarteiraPrincipal
                endereco_data = enderecos_dict.get(num_pedido)

                # Dados de endereço: preferir CarteiraPrincipal, fallback para Separacao
                cnpj = sep_ref.cnpj_cpf or ''
                if endereco_data:
                    cep = endereco_data.cep_endereco_ent or ''
                    numero = endereco_data.endereco_ent or ''
                    rua = endereco_data.rua_endereco_ent
                    bairro = endereco_data.bairro_endereco_ent
                    cidade = endereco_data.nome_cidade or endereco_data.municipio or sep_ref.nome_cidade
                    uf = endereco_data.cod_uf or endereco_data.estado or sep_ref.cod_uf
                    empresa = endereco_data.empresa_endereco_ent
                    telefone = endereco_data.telefone_endereco_ent
                else:
                    cep = ''
                    numero = ''
                    rua = None
                    bairro = None
                    cidade = sep_ref.nome_cidade
                    uf = sep_ref.cod_uf
                    empresa = None
                    telefone = None

                # Criar chave única por CNPJ + CEP + número do endereço
                cliente_key = hashlib.md5(f"{cnpj}_{cep}_{numero}".encode()).hexdigest()[:12]

                # Montar endereço completo para geocodificação
                partes_endereco = []
                if rua:
                    partes_endereco.append(rua)
                if numero:
                    partes_endereco.append(f"nº {numero}")
                if bairro:
                    partes_endereco.append(bairro)
                if cidade:
                    partes_endereco.append(cidade)
                if uf:
                    partes_endereco.append(uf)
                if cep:
                    partes_endereco.append(f"CEP {cep}")
                partes_endereco.append("Brasil")
                endereco_completo = ", ".join(filter(None, partes_endereco))

                # Dados do pedido
                pedido_info = {
                    'num_pedido': num_pedido,
                    'valor': valor_total,
                    'peso': peso_total,
                    'pallet': pallet_total,
                    'itens': total_itens,
                    'observacoes': sep_ref.observ_ped_1,
                    'expedicao': expedicao,
                    'agendamento': agendamento,
                    'agendamento_confirmado': agendamento_confirmado,
                    'protocolo': protocolo,
                    'separacao_lote_id': separacao_lote_id
                }

                if cliente_key not in clientes_dict:
                    clientes_dict[cliente_key] = {
                        'cliente_id': cliente_key,
                        'cliente': {
                            'cnpj': cnpj,
                            'nome': sep_ref.raz_social_red or empresa or 'Cliente',
                            'telefone': telefone
                        },
                        'endereco': {
                            'completo': endereco_completo,
                            'rua': rua,
                            'numero': numero,
                            'bairro': bairro,
                            'cidade': cidade,
                            'uf': uf,
                            'cep': cep
                        },
                        'pedidos': [],
                        'totais': {
                            'valor': 0,
                            'peso': 0,
                            'pallet': 0,
                            'itens': 0,
                            'qtd_pedidos': 0
                        },
                        'coordenadas': None  # Será preenchido após geocodificação
                    }

                # Adicionar pedido ao cliente
                clientes_dict[cliente_key]['pedidos'].append(pedido_info)
                clientes_dict[cliente_key]['totais']['valor'] += pedido_info['valor']
                clientes_dict[cliente_key]['totais']['peso'] += pedido_info['peso']
                clientes_dict[cliente_key]['totais']['pallet'] += pedido_info['pallet']
                clientes_dict[cliente_key]['totais']['itens'] += pedido_info['itens']
                clientes_dict[cliente_key]['totais']['qtd_pedidos'] += 1

            # 4. Mesclar CarVia (mesmo CNPJ+endereco = mesmo cliente_key)
            for cv_cliente in clientes_carvia:
                key = cv_cliente['cliente_id']
                if key in clientes_dict:
                    # Append pedidos do CarVia ao cliente existente
                    clientes_dict[key]['pedidos'].extend(cv_cliente['pedidos'])
                    for k in ('valor', 'peso', 'pallet', 'itens', 'qtd_pedidos'):
                        clientes_dict[key]['totais'][k] += cv_cliente['totais'].get(k, 0)
                else:
                    clientes_dict[key] = cv_cliente

            # 5. Geocodificar endereços e montar lista final
            clientes_mapa = []

            for cliente_key, cliente_data in clientes_dict.items():
                endereco = cliente_data['endereco']['completo']
                lat, lng = self.geocodificar_endereco(endereco)

                if lat and lng:
                    cliente_data['coordenadas'] = {'lat': lat, 'lng': lng}

                    # Determinar status visual baseado nos pedidos
                    cliente_data['status'] = self._determinar_status_cliente(cliente_data['pedidos'])

                    clientes_mapa.append(cliente_data)
                else:
                    logger.warning(f"Não foi possível geocodificar endereço do cliente {cliente_data['cliente']['nome']}")

            return clientes_mapa

        except Exception as e:
            logger.error(f"Erro ao obter clientes para mapa: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    # ---------------------------------------------------------------
    # CarVia helpers
    # ---------------------------------------------------------------
    def _classificar_pedido_ids(self, pedido_ids: List[str]) -> Tuple[List[str], List[str]]:
        """Separa pedido_ids legados em (NACOM, CarVia) via lookup nas tabelas CarVia.

        Retorna (nacom_ids, carvia_ids). carvia_ids contem numero_pedido CarVia
        (PED-*) ou numero_cotacao (COT-*) — usado pelo _obter_clientes_carvia.
        """
        if not pedido_ids:
            return [], []
        try:
            from app.carvia.models import CarviaPedido, CarviaCotacao
            cv_peds = {
                r[0] for r in db.session.query(CarviaPedido.numero_pedido).filter(
                    CarviaPedido.numero_pedido.in_(pedido_ids)
                ).all()
            }
            cv_cots = {
                r[0] for r in db.session.query(CarviaCotacao.numero_cotacao).filter(
                    CarviaCotacao.numero_cotacao.in_(pedido_ids)
                ).all()
            }
            carvia_ids = list(cv_peds | cv_cots)
            nacom_ids = [p for p in pedido_ids if p not in cv_peds and p not in cv_cots]
            return nacom_ids, carvia_ids
        except Exception as e:
            logger.warning("Erro classificando pedido_ids CarVia: %s", e)
            return list(pedido_ids), []

    def _obter_clientes_carvia(
        self, lotes_carvia: List[str], numeros_carvia_extra: List[str]
    ) -> List[Dict[str, Any]]:
        """Busca pedidos/cotacoes CarVia e retorna no formato de cliente.

        Aceita:
          - lotes_carvia: 'CARVIA-PED-{ped_id}' ou 'CARVIA-{cot_id}'
          - numeros_carvia_extra: numero_pedido (PED-*) ou numero_cotacao
        """
        if not lotes_carvia and not numeros_carvia_extra:
            return []

        try:
            from app.carvia.models import (
                CarviaPedido, CarviaPedidoItem, CarviaCotacao,
                CarviaClienteEndereco,
            )

            # Resolver IDs de pedidos e cotacoes a partir dos lotes
            ped_ids = set()
            cot_ids = set()
            for lote in lotes_carvia:
                try:
                    s = str(lote)
                    if s.startswith('CARVIA-PED-'):
                        ped_ids.add(int(s.replace('CARVIA-PED-', '')))
                    elif s.startswith('CARVIA-'):
                        cot_ids.add(int(s.replace('CARVIA-', '')))
                except (ValueError, TypeError):
                    pass

            # Resolver numeros extra (compat — quando JS enviou num_pedido)
            if numeros_carvia_extra:
                rows_p = CarviaPedido.query.filter(
                    CarviaPedido.numero_pedido.in_(numeros_carvia_extra)
                ).all()
                for cp in rows_p:
                    ped_ids.add(cp.id)
                rows_c = CarviaCotacao.query.filter(
                    CarviaCotacao.numero_cotacao.in_(numeros_carvia_extra)
                ).all()
                for cc in rows_c:
                    cot_ids.add(cc.id)

            # Buscar pedidos CarVia
            pedidos_cv = []
            if ped_ids:
                pedidos_cv = CarviaPedido.query.filter(
                    CarviaPedido.id.in_(list(ped_ids))
                ).all()

            # Cotacoes alvo: explicit (cot_ids) + as cotacoes dos pedidos
            cot_ids_alvo = set(cot_ids)
            for p in pedidos_cv:
                if p.cotacao_id:
                    cot_ids_alvo.add(p.cotacao_id)

            cotacoes_dict = {}
            if cot_ids_alvo:
                cots = CarviaCotacao.query.filter(
                    CarviaCotacao.id.in_(list(cot_ids_alvo))
                ).all()
                cotacoes_dict = {c.id: c for c in cots}

            # Buscar enderecos destino em batch
            endereco_ids = {
                c.endereco_destino_id for c in cotacoes_dict.values()
                if c.endereco_destino_id
            }
            enderecos_dict = {}
            if endereco_ids:
                rows = CarviaClienteEndereco.query.filter(
                    CarviaClienteEndereco.id.in_(list(endereco_ids))
                ).all()
                enderecos_dict = {e.id: e for e in rows}

            # Buscar valores agregados por pedido (SUM CarviaPedidoItem.valor_total)
            valores_por_ped = {}
            if ped_ids:
                rows = db.session.query(
                    CarviaPedidoItem.pedido_id,
                    func.coalesce(func.sum(CarviaPedidoItem.valor_total), 0).label('valor'),
                    func.count(CarviaPedidoItem.id).label('itens'),
                ).filter(
                    CarviaPedidoItem.pedido_id.in_(list(ped_ids))
                ).group_by(CarviaPedidoItem.pedido_id).all()
                for pid, valor, itens in rows:
                    valores_por_ped[pid] = (float(valor or 0), int(itens or 0))

            # Montar dict de clientes
            clientes_dict = {}

            def _add_to_cliente(end_obj, pedido_info):
                """Adiciona pedido_info ao cliente derivado de end_obj."""
                if not end_obj:
                    return
                cnpj = (end_obj.cnpj or '').strip()
                cep = (end_obj.fisico_cep or '').strip()
                numero = (end_obj.fisico_numero or '').strip()
                key = hashlib.md5(f"{cnpj}_{cep}_{numero}".encode()).hexdigest()[:12]

                if key not in clientes_dict:
                    partes = []
                    if end_obj.fisico_logradouro:
                        partes.append(end_obj.fisico_logradouro)
                    if numero:
                        partes.append(f"nº {numero}")
                    if end_obj.fisico_bairro:
                        partes.append(end_obj.fisico_bairro)
                    if end_obj.fisico_cidade:
                        partes.append(end_obj.fisico_cidade)
                    if end_obj.fisico_uf:
                        partes.append(end_obj.fisico_uf)
                    if cep:
                        partes.append(f"CEP {cep}")
                    partes.append("Brasil")
                    endereco_completo = ", ".join(filter(None, partes))

                    clientes_dict[key] = {
                        'cliente_id': key,
                        'cliente': {
                            'cnpj': cnpj,
                            'nome': end_obj.razao_social or 'Cliente CarVia',
                            'telefone': None,
                        },
                        'endereco': {
                            'completo': endereco_completo,
                            'rua': end_obj.fisico_logradouro,
                            'numero': numero,
                            'bairro': end_obj.fisico_bairro,
                            'cidade': end_obj.fisico_cidade,
                            'uf': end_obj.fisico_uf,
                            'cep': cep,
                        },
                        'pedidos': [],
                        'totais': {
                            'valor': 0, 'peso': 0, 'pallet': 0,
                            'itens': 0, 'qtd_pedidos': 0,
                        },
                        'coordenadas': None,
                    }

                clientes_dict[key]['pedidos'].append(pedido_info)
                clientes_dict[key]['totais']['valor'] += pedido_info['valor']
                clientes_dict[key]['totais']['peso'] += pedido_info['peso']
                clientes_dict[key]['totais']['pallet'] += pedido_info['pallet']
                clientes_dict[key]['totais']['itens'] += pedido_info['itens']
                clientes_dict[key]['totais']['qtd_pedidos'] += 1

            # Adicionar pedidos
            for p in pedidos_cv:
                cot = cotacoes_dict.get(p.cotacao_id)
                if not cot:
                    continue
                end = enderecos_dict.get(cot.endereco_destino_id)
                valor, itens = valores_por_ped.get(p.id, (0.0, 0))
                pedido_info = {
                    'num_pedido': p.numero_pedido,
                    'valor': valor,
                    'peso': 0.0,  # CarVia: peso e proporcional/cubado — calculo distinto
                    'pallet': 0.0,
                    'itens': itens,
                    'observacoes': cot.observacoes if cot else None,
                    'expedicao': cot.data_expedicao.strftime('%d/%m/%Y') if cot and cot.data_expedicao else None,
                    'agendamento': cot.data_agenda.strftime('%d/%m/%Y') if cot and cot.data_agenda else None,
                    'agendamento_confirmado': False,
                    'protocolo': None,
                    'separacao_lote_id': f'CARVIA-PED-{p.id}',
                }
                _add_to_cliente(end, pedido_info)

            # Adicionar cotacoes "soltas" (sem pedido — CARVIA-{cot_id})
            for cot_id in cot_ids:
                cot = cotacoes_dict.get(cot_id)
                if not cot:
                    continue
                # Skip se já adicionada via pedido
                ja_via_pedido = any(p.cotacao_id == cot_id for p in pedidos_cv)
                if ja_via_pedido:
                    continue
                end = enderecos_dict.get(cot.endereco_destino_id)
                pedido_info = {
                    'num_pedido': cot.numero_cotacao,
                    'valor': float(cot.valor_mercadoria or 0),
                    'peso': 0.0,
                    'pallet': 0.0,
                    'itens': 0,
                    'observacoes': cot.observacoes,
                    'expedicao': cot.data_expedicao.strftime('%d/%m/%Y') if cot.data_expedicao else None,
                    'agendamento': cot.data_agenda.strftime('%d/%m/%Y') if cot.data_agenda else None,
                    'agendamento_confirmado': False,
                    'protocolo': None,
                    'separacao_lote_id': f'CARVIA-{cot.id}',
                }
                _add_to_cliente(end, pedido_info)

            return list(clientes_dict.values())

        except Exception as e:
            logger.error("Erro ao obter clientes CarVia: %s", e)
            import traceback
            logger.error(traceback.format_exc())
            return []

    def _determinar_status_cliente(self, pedidos: List[Dict]) -> str:
        """Determina o status visual do cliente baseado nos pedidos"""
        # Se algum pedido tem agendamento confirmado -> verde (agendado)
        # Se algum pedido tem agendamento mas não confirmado -> amarelo (urgente)
        # Senão -> pendente
        for pedido in pedidos:
            if pedido.get('agendamento_confirmado'):
                return 'agendado'
        for pedido in pedidos:
            if pedido.get('agendamento'):
                return 'urgente'
        return 'pendente'

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
        # NOTA: Campos expedicao, agendamento, protocolo foram removidos de CarteiraPrincipal
        # Para status detalhado, seria necessário consultar Separacao
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

    def calcular_rota_clientes(self, clientes: List[Dict[str, Any]], origem: Optional[str] = None) -> Dict[str, Any]:
        """
        Calcula a rota otimizada para entrega aos clientes (agrupados).

        Args:
            clientes: Lista de dicionários de clientes com coordenadas
            origem: Endereço de origem (padrão: CD Nacom Goya)

        Returns:
            Dicionário com a rota otimizada e estatísticas
        """
        try:
            if not clientes:
                return {'erro': 'Nenhum cliente fornecido'}

            # Usar CD Nacom Goya como origem padrão
            if not origem:
                origem = self.endereco_cd

            # Preparar waypoints (um por cliente)
            waypoints = []
            for cliente in clientes:
                if cliente.get('coordenadas'):
                    waypoints.append({
                        'location': f"{cliente['coordenadas']['lat']},{cliente['coordenadas']['lng']}",
                        'cliente_id': cliente['cliente_id']
                    })

            if len(waypoints) == 0:
                return {'erro': 'Nenhum cliente com coordenadas válidas'}

            # Otimizar rota usando Google Directions API
            if len(waypoints) == 1:
                destination = waypoints[0]['location']
                waypoints_param = None
            else:
                # Usar o último waypoint como destino (não voltar ao CD)
                destination = waypoints[-1]['location']
                waypoints_param = 'optimize:true|' + '|'.join([w['location'] for w in waypoints[:-1]])

            params = {
                'origin': origem,
                'destination': destination,
                'key': self.api_key,
                'language': 'pt-BR',
                'mode': 'driving',
                'units': 'metric',
                'avoid': 'ferries'
            }

            if waypoints_param:
                params['waypoints'] = waypoints_param

            response = requests.get(self.base_directions_url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()

                if data['status'] == 'OK' and data['routes']:
                    route = data['routes'][0]

                    # Processar ordem otimizada de clientes
                    ordem_clientes = []
                    if 'waypoint_order' in route:
                        for idx in route['waypoint_order']:
                            ordem_clientes.append(waypoints[idx]['cliente_id'])
                        # Adicionar o último waypoint (que foi usado como destino)
                        ordem_clientes.append(waypoints[-1]['cliente_id'])
                    else:
                        # Se só tem 1 waypoint
                        ordem_clientes = [w['cliente_id'] for w in waypoints]

                    # Extrair informações da rota
                    total_distance = sum(leg['distance']['value'] for leg in route['legs'])
                    total_duration = sum(leg['duration']['value'] for leg in route['legs'])

                    # Calcular totais consolidados
                    peso_total = sum(c['totais']['peso'] for c in clientes)
                    valor_total = sum(c['totais']['valor'] for c in clientes)
                    pallet_total = sum(c['totais']['pallet'] for c in clientes)
                    total_pedidos = sum(c['totais']['qtd_pedidos'] for c in clientes)

                    # Selecionar veículo
                    veiculo_selecionado = self._selecionar_veiculo_adequado(peso_total)

                    # Calcular pedágio estimado
                    pedagio_estimado = self._calcular_pedagio_estimado(
                        total_distance / 1000,
                        veiculo_selecionado
                    )

                    return {
                        'sucesso': True,
                        'rota': {
                            'ordem_clientes': ordem_clientes,
                            'ordem_pedidos': ordem_clientes,  # Mantido para compatibilidade
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
                            'total_clientes': len(clientes),
                            'total_pedidos': total_pedidos,
                            'valor_total': valor_total,
                            'peso_total': peso_total,
                            'pallet_total': pallet_total,
                            'custo_estimado_km': (total_distance / 1000) * 2.5
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
            logger.error(f"Erro ao calcular rota de clientes: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
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