"""
Service para comparar solicitações de agendamento com planilha modelo
Etapa 2 do processo semi-automatizado Sendas
"""

from app import db
from app.portal.sendas.models_planilha import PlanilhaModeloSendas
from app.portal.sendas.models import FilialDeParaSendas, ProdutoDeParaSendas
from app.portal.sendas.utils_protocolo import gerar_protocolo_sendas
from app.portal.models_fila_sendas import FilaAgendamentoSendas
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ComparacaoSendasService:
    """
    Service para comparar solicitações com disponibilidade na planilha modelo
    """

    def __init__(self):
        self.filiais_cache = {}
        self.produtos_cache = {}


    def comparar_multiplas_solicitacoes(self, solicitacoes):
        """
        Compara múltiplas solicitações - SEMPRE usado para todos os fluxos

        Args:
            solicitacoes: Lista de dicts com cnpj, pedido_cliente, cod_produto, quantidade, data_agendamento

        Returns:
            dict: Resultado agrupado por CNPJ com comparações de todos os produtos
        """
        resultados_por_cnpj = {}

        # Agrupar solicitações por CNPJ para processar juntas
        solicitacoes_por_cnpj = {}
        for solicitacao in solicitacoes:
            cnpj = solicitacao['cnpj']
            if cnpj not in solicitacoes_por_cnpj:
                solicitacoes_por_cnpj[cnpj] = []
            solicitacoes_por_cnpj[cnpj].append(solicitacao)

        # Processar cada CNPJ
        for cnpj, itens_cnpj in solicitacoes_por_cnpj.items():
            logger.info(f"Comparando {len(itens_cnpj)} itens para CNPJ {cnpj}")

            # Obter o primeiro pedido_cliente para ajudar no fallback (todos são do mesmo CNPJ = mesma filial)
            primeiro_pedido = itens_cnpj[0].get('pedido_cliente') if itens_cnpj else None

            # 1. Converter CNPJ para filial Sendas (com fallback usando primeiro pedido)
            unidade_destino_sendas = self._converter_cnpj_para_filial(cnpj, primeiro_pedido)
            if not unidade_destino_sendas:
                resultados_por_cnpj[cnpj] = {
                    'cnpj': cnpj,
                    'sucesso': False,
                    'erro': f'CNPJ {cnpj} não encontrado no DE-PARA de filiais',
                    'itens': []
                }
                continue

            # 2. Processar cada item do CNPJ
            itens_resultado = []
            pedidos_encontrados = set()
            produtos_nao_encontrados = []

            for item in itens_cnpj:
                pedido_cliente = item.get('pedido_cliente')
                cod_produto = item.get('cod_produto')
                quantidade = item.get('quantidade', 0)
                data_agendamento = item.get('data_agendamento')

                # Converter produto para código Sendas
                codigo_produto_sendas = self._converter_produto_para_sendas(cod_produto)
                if not codigo_produto_sendas:
                    logger.warning(f"Produto {cod_produto} não no DE-PARA, usando código original")
                    codigo_produto_sendas = cod_produto

                # Buscar disponibilidade
                disponibilidades = self._buscar_disponibilidade(
                    unidade_destino_sendas,
                    pedido_cliente,
                    codigo_produto_sendas
                )

                if disponibilidades:
                    # Encontrou o item
                    pedidos_encontrados.add(pedido_cliente)
                    total_disponivel = sum(d.saldo_disponivel for d in disponibilidades)

                    for disp in disponibilidades:
                        nosso_produto = ProdutoDeParaSendas.obter_nosso_codigo(disp.codigo_produto_cliente)
                        itens_resultado.append({
                            'solicitado': {
                                'pedido_cliente': pedido_cliente,
                                'cod_produto': cod_produto,
                                'quantidade': float(quantidade),
                                'data_agendamento': data_agendamento,
                                'num_pedido': item.get('num_pedido')  # ✅ ADICIONADO: num_pedido
                            },
                            'encontrado': {
                                'codigo_pedido_sendas': disp.codigo_pedido_cliente,
                                'codigo_produto_sendas': disp.codigo_produto_cliente,
                                'codigo_produto_nosso': nosso_produto or disp.codigo_produto_cliente,
                                'descricao': disp.descricao_item,
                                'saldo_disponivel': float(disp.saldo_disponivel),
                                'unidade_medida': disp.unidade_medida,
                                'quantidade_suficiente': float(disp.saldo_disponivel) >= quantidade
                            },
                            'tipo_match': 'exato',
                            'pode_agendar': True  # Sendas aceita divergências
                        })
                else:
                    # Não encontrou - adicionar mesmo assim (Sendas aceita divergências)
                    produtos_nao_encontrados.append(cod_produto)
                    itens_resultado.append({
                        'solicitado': {
                            'pedido_cliente': pedido_cliente,
                            'cod_produto': cod_produto,
                            'quantidade': float(quantidade),
                            'data_agendamento': data_agendamento,
                            'num_pedido': item.get('num_pedido')  # ✅ ADICIONADO: num_pedido
                        },
                        'encontrado': None,
                        'tipo_match': 'nao_encontrado',
                        'pode_agendar': True,  # Sendas aceita mesmo sem encontrar
                        'observacao': 'Produto não encontrado na planilha, mas Sendas aceita divergências'
                    })

            # 3. Verificar se TODOS os itens têm match
            todos_tem_match = all(item['tipo_match'] == 'exato' for item in itens_resultado)

            # 4. Se ALGUM item NÃO tem match, buscar TUDO da filial
            alternativas_filial = None
            if not todos_tem_match:
                logger.info(f"Nem todos os itens têm match, buscando TODA a filial {unidade_destino_sendas}")
                alternativas = self._buscar_alternativas_filial(unidade_destino_sendas)

                if alternativas:
                    pedidos_filial = {}

                    # Criar mapa de matches para identificação rápida
                    matches_map = {}
                    for item in itens_resultado:
                        if item['tipo_match'] == 'exato' and item['encontrado']:
                            key = f"{item['encontrado']['codigo_pedido_sendas']}_{item['encontrado']['codigo_produto_sendas']}"
                            matches_map[key] = {
                                'quantidade_solicitada': item['solicitado']['quantidade'],
                                'cod_produto_original': item['solicitado']['cod_produto']
                            }

                    # Processar TODOS os produtos da filial
                    for alt in alternativas:
                        pedido_cod = alt.codigo_pedido_cliente.split('-')[0] if '-' in alt.codigo_pedido_cliente else alt.codigo_pedido_cliente
                        if pedido_cod not in pedidos_filial:
                            pedidos_filial[pedido_cod] = []

                        nosso_produto = ProdutoDeParaSendas.obter_nosso_codigo(alt.codigo_produto_cliente)

                        # Verificar se este item é um match
                        key_check = f"{alt.codigo_pedido_cliente}_{alt.codigo_produto_cliente}"
                        eh_match = key_check in matches_map

                        pedidos_filial[pedido_cod].append({
                            'codigo_pedido_sendas': alt.codigo_pedido_cliente,
                            'codigo_produto_sendas': alt.codigo_produto_cliente,
                            'codigo_produto_nosso': nosso_produto or alt.codigo_produto_cliente,
                            'descricao': alt.descricao_item,
                            'saldo_disponivel': float(alt.saldo_disponivel),
                            'unidade_medida': alt.unidade_medida,
                            'eh_match': eh_match,
                            'quantidade_pre_preenchida': matches_map[key_check]['quantidade_solicitada'] if eh_match else 0,
                            'cod_produto_solicitado': matches_map[key_check]['cod_produto_original'] if eh_match else None
                        })

                    alternativas_filial = {
                        'total_pedidos': len(pedidos_filial),
                        'pedidos': pedidos_filial,
                        'mostrar_tudo': True,  # Flag indicando que deve mostrar TUDO
                        'sugestao': 'Nem todos os itens foram encontrados. Mostrando TODOS os produtos disponíveis nesta filial.'
                    }

            # Montar resultado final para este CNPJ
            resultados_por_cnpj[cnpj] = {
                'cnpj': cnpj,
                'unidade_destino_sendas': unidade_destino_sendas,
                'sucesso': True,  # Sempre sucesso pois Sendas aceita divergências
                'data_agendamento': itens_cnpj[0].get('data_agendamento'),
                'total_itens': len(itens_resultado),
                'itens_encontrados': len([i for i in itens_resultado if i['tipo_match'] == 'exato']),
                'itens_nao_encontrados': len(produtos_nao_encontrados),
                'itens': itens_resultado,
                'alternativas_filial': alternativas_filial,
                'pode_agendar_todos': True,  # Sendas sempre permite agendamento
                'todos_tem_match_100': todos_tem_match  # Flag para auto-confirmação: True se TODOS os itens têm match exato
            }

        return resultados_por_cnpj

    def _converter_cnpj_para_filial(self, cnpj, pedido_cliente=None):
        """Converte CNPJ para código de filial usando DE-PARA com fallback por números"""
        logger.info(f"🔍 _converter_cnpj_para_filial: CNPJ={cnpj}, pedido_cliente={pedido_cliente}")

        if cnpj in self.filiais_cache:
            logger.info(f"   ✅ CNPJ encontrado no cache: {self.filiais_cache[cnpj]}")
            return self.filiais_cache[cnpj]

        # Primeiro tentar buscar qual filial está na planilha para este pedido
        filial_planilha = None
        if pedido_cliente:
            logger.info(f"   🔍 Buscando filial na planilha para pedido_cliente: {pedido_cliente}")
            # Buscar qualquer item deste pedido na planilha para obter o nome da filial
            item_planilha = PlanilhaModeloSendas.query.filter(
                PlanilhaModeloSendas.codigo_pedido_cliente.like(f"{pedido_cliente}-%")
            ).first()

            if item_planilha:
                filial_planilha = item_planilha.unidade_destino
                logger.info(f"   ✅ Filial encontrada na planilha para pedido {pedido_cliente}: {filial_planilha}")
            else:
                logger.warning(f"   ⚠️ Nenhum item encontrado na planilha para pedido_cliente: {pedido_cliente}")
        else:
            logger.warning(f"   ⚠️ pedido_cliente é None - tentando buscar filial apenas pelo CNPJ")

        # Usar o método com fallback passando a filial da planilha
        logger.info(f"   🔄 Chamando FilialDeParaSendas.cnpj_to_filial(cnpj={cnpj}, filial_planilha={filial_planilha})")
        filial = FilialDeParaSendas.cnpj_to_filial(cnpj, filial_planilha)

        if filial:
            logger.info(f"   ✅ Filial encontrada: {filial}")
            self.filiais_cache[cnpj] = filial
        else:
            logger.error(f"   ❌ FALHA: Filial NÃO encontrada para CNPJ {cnpj}")
            logger.error(f"      - pedido_cliente fornecido: {pedido_cliente}")
            logger.error(f"      - filial_planilha encontrada: {filial_planilha}")
            logger.error(f"      - Verifique se o CNPJ está cadastrado em FilialDeParaSendas")
            logger.error(f"      - Verifique se a planilha modelo foi importada corretamente")

        return filial

    def _converter_produto_para_sendas(self, cod_produto):
        """Converte nosso código para código Sendas usando DE-PARA"""
        if cod_produto in self.produtos_cache:
            return self.produtos_cache[cod_produto]

        codigo_sendas = ProdutoDeParaSendas.obter_codigo_sendas(cod_produto)
        if codigo_sendas:
            self.produtos_cache[cod_produto] = codigo_sendas
        return codigo_sendas

    def _buscar_disponibilidade(self, unidade_destino, pedido_cliente, codigo_produto):
        """
        Busca disponibilidade na planilha modelo

        Prioridade:
        1. Filial + Pedido + Produto (match exato)
        2. Filial + Pedido (todos produtos do pedido)
        3. Filial (todos produtos da filial)

        Inclui fallback para pedido_cliente com caracteres não numéricos (ex: /L)
        """
        import re

        query = PlanilhaModeloSendas.query

        # Sempre filtrar por unidade destino
        query = query.filter_by(unidade_destino=unidade_destino)

        # Se tem pedido, filtrar por pedido (formato "pedido-filial")
        if pedido_cliente:
            # Primeiro tentar com o valor completo
            query_original = query.filter(
                PlanilhaModeloSendas.codigo_pedido_cliente.like(f"{pedido_cliente}-%")
            )

            # Se tem produto, filtrar por produto
            if codigo_produto:
                query_original = query_original.filter_by(codigo_produto_cliente=str(codigo_produto))

            # Filtrar apenas com saldo disponível
            query_original = query_original.filter(PlanilhaModeloSendas.saldo_disponivel > 0)

            resultados = query_original.all()

            # Se encontrou com o valor original, retornar
            if resultados:
                logger.debug(f"Encontrado com pedido_cliente original: {pedido_cliente}")
                return resultados

            # FALLBACK: Se não encontrou e o pedido tem caracteres não numéricos
            # Extrair apenas os números e tentar novamente
            numeros_apenas = re.sub(r'[^0-9]', '', pedido_cliente)

            if numeros_apenas and numeros_apenas != pedido_cliente:
                logger.info(f"Tentando fallback: pedido_cliente '{pedido_cliente}' → números apenas '{numeros_apenas}'")

                query_fallback = PlanilhaModeloSendas.query
                query_fallback = query_fallback.filter_by(unidade_destino=unidade_destino)
                query_fallback = query_fallback.filter(
                    PlanilhaModeloSendas.codigo_pedido_cliente.like(f"{numeros_apenas}-%")
                )

                # Se tem produto, filtrar por produto
                if codigo_produto:
                    query_fallback = query_fallback.filter_by(codigo_produto_cliente=str(codigo_produto))

                # Filtrar apenas com saldo disponível
                query_fallback = query_fallback.filter(PlanilhaModeloSendas.saldo_disponivel > 0)

                resultados_fallback = query_fallback.all()

                if resultados_fallback:
                    logger.info(f"✅ Fallback bem-sucedido: encontrados {len(resultados_fallback)} itens com pedido '{numeros_apenas}'")
                    return resultados_fallback
                else:
                    logger.info(f"⚠️ Fallback não encontrou resultados para pedido '{numeros_apenas}'")

            # Se chegou aqui, não encontrou nem com original nem com fallback
            return []

        # Se não tem pedido_cliente, continuar com a lógica normal
        # Se tem produto, filtrar por produto
        if codigo_produto:
            query = query.filter_by(codigo_produto_cliente=str(codigo_produto))

        # Filtrar apenas com saldo disponível
        query = query.filter(PlanilhaModeloSendas.saldo_disponivel > 0)

        return query.all()

    def _buscar_alternativas_filial(self, unidade_destino):
        """Busca todos os itens disponíveis da filial (quando não encontra pedido específico)"""
        return PlanilhaModeloSendas.query.filter_by(
            unidade_destino=unidade_destino
        ).filter(
            PlanilhaModeloSendas.saldo_disponivel > 0
        ).all()

    def _analisar_disponibilidade(self, disponibilidades, cnpj, pedido_cliente, cod_produto,
                                  quantidade_solicitada, data_agendamento, unidade_destino_sendas,
                                  codigo_produto_sendas):
        """
        Analisa disponibilidades encontradas e monta resposta estruturada
        """
        solicitacao = self._criar_dict_solicitacao(
            cnpj, pedido_cliente, cod_produto, quantidade_solicitada, data_agendamento
        )

        # Caso 1: Encontrou exatamente o que foi solicitado
        if disponibilidades:
            # Verificar se tem quantidade suficiente
            total_disponivel = sum(d.saldo_disponivel for d in disponibilidades)

            itens_disponiveis = []
            for disp in disponibilidades:
                # Converter de volta para nosso padrão
                nosso_produto = ProdutoDeParaSendas.obter_nosso_codigo(disp.codigo_produto_cliente)

                itens_disponiveis.append({
                    'codigo_pedido_sendas': disp.codigo_pedido_cliente,
                    'codigo_produto_sendas': disp.codigo_produto_cliente,
                    'codigo_produto_nosso': nosso_produto or disp.codigo_produto_cliente,
                    'descricao': disp.descricao_item,
                    'saldo_disponivel': float(disp.saldo_disponivel),
                    'unidade_medida': disp.unidade_medida,
                    'pode_agendar': float(disp.saldo_disponivel) >= quantidade_solicitada
                })

            return {
                'sucesso': True,
                'tipo_match': 'exato',
                'solicitacao': solicitacao,
                'disponibilidades': itens_disponiveis,
                'total_disponivel': float(total_disponivel),
                'quantidade_suficiente': total_disponivel >= quantidade_solicitada,
                'unidade_destino_sendas': unidade_destino_sendas,
                'sugestao': None
            }

        # Caso 2: Não encontrou o pedido, mas encontrou a filial
        alternativas = self._buscar_alternativas_filial(unidade_destino_sendas)
        if alternativas:
            # Agrupar por pedido
            pedidos_filial = {}
            for alt in alternativas:
                pedido_cod = alt.codigo_pedido_cliente.split('-')[0] if '-' in alt.codigo_pedido_cliente else alt.codigo_pedido_cliente

                if pedido_cod not in pedidos_filial:
                    pedidos_filial[pedido_cod] = []

                nosso_produto = ProdutoDeParaSendas.obter_nosso_codigo(alt.codigo_produto_cliente)
                pedidos_filial[pedido_cod].append({
                    'codigo_pedido_sendas': alt.codigo_pedido_cliente,
                    'codigo_produto_sendas': alt.codigo_produto_cliente,
                    'codigo_produto_nosso': nosso_produto or alt.codigo_produto_cliente,
                    'descricao': alt.descricao_item,
                    'saldo_disponivel': float(alt.saldo_disponivel),
                    'unidade_medida': alt.unidade_medida
                })

            return {
                'sucesso': True,
                'tipo_match': 'filial_apenas',
                'solicitacao': solicitacao,
                'disponibilidades': [],
                'pedidos_alternativos': pedidos_filial,
                'total_itens_filial': len(alternativas),
                'unidade_destino_sendas': unidade_destino_sendas,
                'sugestao': f'Pedido {pedido_cliente} não encontrado, mas há {len(pedidos_filial)} outros pedidos disponíveis nesta filial. Deseja agendar algum deles?'
            }

        # Caso 3: Não encontrou nada
        return {
            'sucesso': False,
            'tipo_match': 'nenhum',
            'solicitacao': solicitacao,
            'disponibilidades': [],
            'erro': f'Nenhuma disponibilidade encontrada para a filial {unidade_destino_sendas}',
            'unidade_destino_sendas': unidade_destino_sendas
        }

    def _criar_dict_solicitacao(self, cnpj, pedido_cliente, cod_produto, quantidade, data_agendamento):
        """Cria dicionário com dados da solicitação"""
        return {
            'cnpj': cnpj,
            'pedido_cliente': pedido_cliente,
            'cod_produto': cod_produto,
            'quantidade_solicitada': float(quantidade) if quantidade else 0,
            'data_agendamento': data_agendamento
        }

    def _buscar_cnpj_backend(self, num_pedido):
        """
        Busca o CNPJ correto do backend usando o num_pedido

        Args:
            num_pedido: Número do pedido

        Returns:
            str: CNPJ encontrado ou None
        """
        if not num_pedido:
            return None

        try:
            # Primeiro tentar na Separacao
            from app.separacao.models import Separacao
            separacao = Separacao.query.filter_by(num_pedido=num_pedido).first()
            if separacao and separacao.cnpj_cpf:
                logger.debug(f"CNPJ encontrado na Separacao para pedido {num_pedido}: {separacao.cnpj_cpf}")
                return separacao.cnpj_cpf

            # Se não encontrar, tentar na CarteiraPrincipal
            from app.carteira.models import CarteiraPrincipal
            carteira = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).first()
            if carteira and carteira.cnpj_cpf:
                logger.debug(f"CNPJ encontrado na CarteiraPrincipal para pedido {num_pedido}: {carteira.cnpj_cpf}")
                return carteira.cnpj_cpf

            logger.warning(f"CNPJ não encontrado no backend para pedido {num_pedido}")
            return None

        except Exception as e:
            logger.error(f"Erro ao buscar CNPJ no backend para pedido {num_pedido}: {e}")
            return None

    def gravar_fila_agendamento(self, itens_confirmados, tipo_origem, documento_origem, protocolo_existente=None):
        """
        Grava os itens confirmados em FilaAgendamentoSendas com protocolo correto por fluxo

        Args:
            itens_confirmados: Lista de itens que o usuário confirmou para agendar
            tipo_origem: 'lote', 'separacao' ou 'nf'
            documento_origem: Identificador da origem (separacao_lote_id, numero_nf, etc)
            protocolo_existente: Protocolo já gerado anteriormente (evita gerar novo)

        Returns:
            dict: Resultado com protocolos gerados conforme regras:
                  - Fluxo 1 (lote): 1 protocolo por CNPJ
                  - Fluxo 2 (separacao): 1 protocolo por separacao_lote_id
                  - Fluxo 3 (nf): 1 protocolo por NF
        """
        protocolos_gerados = {}
        protocolo_unico = None

        try:
            # Determinar estratégia de protocolo baseado no fluxo
            if tipo_origem == 'lote':
                # FLUXO 1: 1 protocolo por CNPJ
                protocolos_por_cnpj = {}

                for item in itens_confirmados:
                    # ✅ BUSCAR CNPJ DO BACKEND pelo num_pedido
                    cnpj_backend = self._buscar_cnpj_backend(item.get('num_pedido'))
                    cnpj = cnpj_backend if cnpj_backend else item['cnpj']  # Usar backend ou fallback para frontend

                    # ✅ CRÍTICO: Usar protocolo existente se fornecido, senão gerar novo
                    if cnpj not in protocolos_por_cnpj:
                        if protocolo_existente:
                            protocolos_por_cnpj[cnpj] = protocolo_existente
                            logger.info(f"✅ Usando protocolo existente para CNPJ {cnpj}: {protocolo_existente}")
                        else:
                            protocolos_por_cnpj[cnpj] = gerar_protocolo_sendas(
                                cnpj,
                                item['data_agendamento']
                            )
                            logger.info(f"⚠️ Gerando NOVO protocolo para CNPJ {cnpj}: {protocolos_por_cnpj[cnpj]}")

                    protocolo = protocolos_por_cnpj[cnpj]

                    # Adicionar na fila com o protocolo do CNPJ
                    FilaAgendamentoSendas.adicionar(
                        tipo_origem=tipo_origem,
                        documento_origem=cnpj,  # Usar CNPJ como origem para lote
                        cnpj=cnpj,
                        num_pedido=item.get('num_pedido'),
                        cod_produto=item['cod_produto'],
                        quantidade=item['quantidade'],
                        data_expedicao=item.get('data_expedicao'),
                        data_agendamento=item['data_agendamento'],
                        pedido_cliente=item.get('pedido_cliente'),
                        nome_produto=item.get('nome_produto'),
                        protocolo=protocolo
                    )

                protocolos_gerados = protocolos_por_cnpj

            elif tipo_origem == 'separacao':
                # FLUXO 2: 1 protocolo por separacao_lote_id (todos os itens do lote compartilham)
                if itens_confirmados:
                    primeiro_item = itens_confirmados[0]
                    # ✅ BUSCAR CNPJ DO BACKEND pelo num_pedido
                    cnpj_backend = self._buscar_cnpj_backend(primeiro_item.get('num_pedido'))
                    cnpj = cnpj_backend if cnpj_backend else primeiro_item['cnpj']

                    protocolo_unico = gerar_protocolo_sendas(
                        cnpj,
                        primeiro_item['data_agendamento']
                    )

                    for item in itens_confirmados:
                        # ✅ BUSCAR CNPJ DO BACKEND para cada item
                        cnpj_item = self._buscar_cnpj_backend(item.get('num_pedido'))
                        if not cnpj_item:
                            cnpj_item = item['cnpj']  # Fallback para frontend

                        FilaAgendamentoSendas.adicionar(
                            tipo_origem=tipo_origem,
                            documento_origem=documento_origem,  # separacao_lote_id
                            cnpj=cnpj_item,
                            num_pedido=item.get('num_pedido'),
                            cod_produto=item['cod_produto'],
                            quantidade=item['quantidade'],
                            data_expedicao=item.get('data_expedicao'),
                            data_agendamento=item['data_agendamento'],
                            pedido_cliente=item.get('pedido_cliente'),
                            nome_produto=item.get('nome_produto'),
                            protocolo=protocolo_unico  # Mesmo protocolo para todo o lote
                        )

                    # Para separação, retornar protocolo único com chave do lote
                    protocolos_gerados[documento_origem] = protocolo_unico

            elif tipo_origem == 'nf':
                # FLUXO 3: 1 protocolo por NF (todos os produtos da NF compartilham)
                if itens_confirmados:
                    primeiro_item = itens_confirmados[0]
                    # ✅ BUSCAR CNPJ DO BACKEND pelo num_pedido ou número da NF
                    cnpj_backend = self._buscar_cnpj_backend(primeiro_item.get('num_pedido'))
                    cnpj = cnpj_backend if cnpj_backend else primeiro_item['cnpj']

                    protocolo_unico = gerar_protocolo_sendas(
                        cnpj,
                        primeiro_item['data_agendamento']
                    )

                    for item in itens_confirmados:
                        # ✅ BUSCAR CNPJ DO BACKEND para cada item
                        cnpj_item = self._buscar_cnpj_backend(item.get('num_pedido'))
                        if not cnpj_item:
                            cnpj_item = item['cnpj']  # Fallback para frontend

                        FilaAgendamentoSendas.adicionar(
                            tipo_origem=tipo_origem,
                            documento_origem=documento_origem,  # numero_nf
                            cnpj=cnpj_item,
                            num_pedido=item.get('num_pedido'),
                            cod_produto=item['cod_produto'],
                            quantidade=item['quantidade'],
                            data_expedicao=item.get('data_expedicao'),
                            data_agendamento=item['data_agendamento'],
                            pedido_cliente=item.get('pedido_cliente'),
                            nome_produto=item.get('nome_produto'),
                            protocolo=protocolo_unico  # Mesmo protocolo para toda NF
                        )

                    # Para NF, retornar protocolo único com chave da NF
                    protocolos_gerados[documento_origem] = protocolo_unico

            else:
                raise ValueError(f"Tipo de origem inválido: {tipo_origem}")

            return {
                'sucesso': True,
                'protocolos': protocolos_gerados,
                'total_itens': len(itens_confirmados),
                'tipo_origem': tipo_origem,
                'documento_origem': documento_origem
            }

        except Exception as e:
            logger.error(f"Erro ao gravar fila agendamento: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }