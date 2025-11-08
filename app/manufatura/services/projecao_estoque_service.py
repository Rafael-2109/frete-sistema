"""
Serviço de Projeção de Estoque de Componentes
============================================

Projeta estoque para 60 dias considerando:
- ENTRADAS: Pedidos de compra + Saldo de requisições
- SAÍDAS: Consumo através de BOM (ListaMateriais) × ProgramacaoProducao

Autor: Sistema de Fretes
Data: 01/11/2025
"""

from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict
from typing import Dict, List, Any
from sqlalchemy import func

from app import db
from app.manufatura.models import (
    PedidoCompras,
    RequisicaoCompras,
    RequisicaoCompraAlocacao,
    ListaMateriais
)
from app.producao.models import ProgramacaoProducao, CadastroPalletizacao
from app.estoque.services.estoque_simples import ServicoEstoqueSimples


class ServicoProjecaoEstoque:
    """
    Serviço para projeção de estoque de componentes
    """

    def __init__(self):
        self.estoque_service = ServicoEstoqueSimples()

        # ✅ CACHE para otimizar performance
        self._cache_programacoes_upstream = {}  # {(cod_produto, data_inicio, data_fim): [(prog, fator), ...]}
        self._cache_eh_intermediario = {}  # {cod_produto: bool}
        self._cache_boms_upstream = {}  # {cod_produto: [ListaMateriais]}

    def _limpar_cache(self):
        """Limpa todos os caches (chamar no início de cada projeção)"""
        self._cache_programacoes_upstream.clear()
        self._cache_eh_intermediario.clear()
        self._cache_boms_upstream.clear()

    def projetar_componentes_60_dias(self) -> Dict[str, Any]:
        """
        Projeta estoque de TODOS os componentes (produto_comprado=True) para 60 dias

        Returns:
            Dict com projeção por produto
        """
        # ✅ Limpar cache no início da projeção
        self._limpar_cache()

        # Buscar apenas produtos comprados
        produtos_comprados = CadastroPalletizacao.query.filter_by(
            produto_comprado=True,
            ativo=True
        ).all()

        projecoes = []

        for produto in produtos_comprados:
            projecao = self.projetar_produto(produto.cod_produto, dias=60)
            if projecao:
                projecoes.append(projecao)

        return {
            'data_projecao': date.today().isoformat(),
            'dias_projetados': 60,
            'total_produtos': len(projecoes),
            'projecoes': projecoes
        }

    def projetar_componentes_consolidado(self) -> Dict[str, Any]:
        """
        Projeta componentes com DADOS CONSOLIDADOS para exibição em tabela

        Retorna estrutura otimizada:
        - Colunas fixas: Estoque, Consumo Carteira, Saldo, Qtd Req, Qtd Ped
        - Timeline D0-D60: projeção diária completa
        """
        # Imports não são necessários aqui, apenas nos métodos auxiliares

        # Buscar produtos comprados
        produtos_comprados = CadastroPalletizacao.query.filter_by(
            produto_comprado=True,
            ativo=True
        ).order_by(CadastroPalletizacao.cod_produto).all()

        componentes = []
        data_inicio = date.today()
        data_fim = data_inicio + timedelta(days=60)

        for produto in produtos_comprados:
            cod_produto = produto.cod_produto

            # Estoque atual
            estoque_atual = self.estoque_service.calcular_estoque_atual(cod_produto)

            # Consumo para Carteira (BOM multinível × Necessidade)
            consumo_carteira = self._calcular_consumo_carteira(cod_produto)

            # Saldo para Carteira
            saldo_carteira = float(estoque_atual) - consumo_carteira

            # ✅ NOVO: Consumo via Programação de Produção (incluindo intermediários)
            consumo_programacao = self._calcular_consumo_programacao(cod_produto)

            # ✅ NOVO: Saldo Programação
            saldo_programacao = float(estoque_atual) - consumo_programacao

            # Qtd em Requisições
            qtd_requisicoes = self._calcular_qtd_requisicoes(cod_produto)

            # Qtd em Pedidos
            qtd_pedidos = self._calcular_qtd_pedidos(cod_produto)

            # Projeção D0-D60 (timeline completa)
            entradas = self._calcular_entradas(cod_produto, data_inicio, data_fim)
            saidas = self._calcular_saidas_por_bom(cod_produto, data_inicio, data_fim)
            timeline = self._gerar_timeline_60_dias(estoque_atual, entradas, saidas)

            componentes.append({
                'cod_produto': cod_produto,
                'nome_produto': produto.nome_produto,
                'estoque_atual': round(float(estoque_atual), 2),
                'consumo_carteira': round(consumo_carteira, 2),
                'saldo_carteira': round(saldo_carteira, 2),
                'consumo_programacao': round(consumo_programacao, 2),  # ✅ NOVO
                'saldo_programacao': round(saldo_programacao, 2),      # ✅ NOVO
                'qtd_requisicoes': round(qtd_requisicoes, 2),
                'qtd_pedidos': round(qtd_pedidos, 2),
                'timeline': timeline,  # Array de 61 posições (D0 a D60)
                # ✅ NOVOS CAMPOS para UI (NÃO incluir linha_producao)
                'tipo_embalagem': produto.tipo_embalagem,
                'tipo_materia_prima': produto.tipo_materia_prima,
                'categoria_produto': produto.categoria_produto
            })

        return {
            'sucesso': True,
            'data_calculo': date.today().isoformat(),
            'total_componentes': len(componentes),
            'componentes': componentes
        }

    def projetar_produto(self, cod_produto: str, dias: int = 60) -> Dict[str, Any]:
        """
        Projeta estoque de um produto específico

        Args:
            cod_produto: Código do produto
            dias: Dias no futuro para projetar

        Returns:
            Dict com projeção diária
        """
        data_inicio = date.today()
        data_fim = data_inicio + timedelta(days=dias)

        # Estoque atual
        estoque_atual = self.estoque_service.calcular_estoque_atual(cod_produto)

        # Entradas: Pedidos + Saldos
        entradas = self._calcular_entradas(cod_produto, data_inicio, data_fim)

        # Saídas: Consumo por BOM
        saidas = self._calcular_saidas_por_bom(cod_produto, data_inicio, data_fim)

        # Projeção dia a dia
        projecao_diaria = self._calcular_projecao_diaria(
            estoque_atual,
            entradas,
            saidas,
            data_inicio,
            data_fim
        )

        # Identificar rupturas
        dias_ruptura = [
            dia for dia in projecao_diaria
            if dia['estoque_final'] < 0
        ]

        # Buscar nome do produto
        produto = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()
        nome_produto = produto.nome_produto if produto else cod_produto

        return {
            'cod_produto': cod_produto,
            'nome_produto': nome_produto,
            'estoque_inicial': float(estoque_atual),
            'total_entradas': sum(e['quantidade'] for e in entradas),
            'total_saidas': sum(s['quantidade'] for s in saidas),
            'estoque_final_projetado': projecao_diaria[-1]['estoque_final'] if projecao_diaria else float(estoque_atual),
            'dias_ruptura': len(dias_ruptura),
            'primeira_ruptura': dias_ruptura[0]['data'] if dias_ruptura else None,
            'projecao_diaria': projecao_diaria,
            'detalhes_entradas': entradas,
            'detalhes_saidas': saidas
        }

    def projetar_requisicao(self, requisicao_id: int) -> Dict[str, Any]:
        """
        Projeta estoque para uma requisição específica: -D7 a +D7 da data_necessidade

        Args:
            requisicao_id: ID da requisição

        Returns:
            Dict com projeção centrada na data_necessidade
        """
        from app.manufatura.models import RequisicaoCompras, RequisicaoCompraAlocacao

        # Buscar requisição
        requisicao = RequisicaoCompras.query.get(requisicao_id)
        if not requisicao:
            return {'sucesso': False, 'erro': 'Requisição não encontrada'}

        if not requisicao.data_necessidade:
            return {'sucesso': False, 'erro': 'Requisição sem data_necessidade'}

        # Calcular janela: -D7 a +D7 da data_necessidade
        data_centro = requisicao.data_necessidade
        data_inicio = data_centro - timedelta(days=7)
        data_fim = data_centro + timedelta(days=7)

        cod_produto = requisicao.cod_produto

        # Estoque atual
        estoque_atual = self.estoque_service.calcular_estoque_atual(cod_produto)

        # Entradas e Saídas
        entradas = self._calcular_entradas(cod_produto, data_inicio, data_fim)
        saidas = self._calcular_saidas_por_bom(cod_produto, data_inicio, data_fim)

        # Projeção diária detalhada
        projecao_diaria = self._calcular_projecao_diaria(
            estoque_atual,
            entradas,
            saidas,
            data_inicio,
            data_fim
        )

        # Buscar pedidos vinculados via alocação
        alocacoes = RequisicaoCompraAlocacao.query.filter_by(
            requisicao_compra_id=requisicao.id
        ).all()

        pedidos_vinculados = []
        for alocacao in alocacoes:
            if alocacao.pedido:
                pedidos_vinculados.append({
                    'num_pedido': alocacao.pedido.num_pedido,
                    'fornecedor': alocacao.pedido.raz_social,
                    'qtd_alocada': float(alocacao.qtd_alocada),
                    'qtd_aberta': float(alocacao.qtd_aberta),
                    'percentual_atendido': alocacao.percentual_alocado(),
                    'status': alocacao.purchase_state,
                    'data_previsao': alocacao.pedido.data_pedido_previsao.isoformat() if alocacao.pedido.data_pedido_previsao else None
                })

        # Buscar produtos que consomem este componente (com programação ativa)
        produtos_consumidores = self._buscar_produtos_consumidores_com_programacao(
            cod_produto,
            data_inicio,
            data_fim
        )

        return {
            'sucesso': True,
            'requisicao': {
                'id': requisicao.id,
                'num_requisicao': requisicao.num_requisicao,
                'cod_produto': requisicao.cod_produto,
                'nome_produto': requisicao.nome_produto,
                'qtd_requisitada': float(requisicao.qtd_produto_requisicao),
                'data_necessidade': requisicao.data_necessidade.isoformat(),
                'status': requisicao.status
            },
            'estoque_atual': float(estoque_atual),
            'data_centro': data_centro.isoformat(),
            'data_inicio': data_inicio.isoformat(),
            'data_fim': data_fim.isoformat(),
            'projecao_diaria': projecao_diaria,
            'pedidos_vinculados': pedidos_vinculados,
            'produtos_consumidores': produtos_consumidores,
            'total_entradas': sum(e['quantidade'] for e in entradas),
            'total_saidas': sum(s['quantidade'] for s in saidas)
        }

    def _calcular_entradas(
        self,
        cod_produto: str,
        data_inicio: date,
        data_fim: date
    ) -> List[Dict]:
        """
        Calcula entradas: Pedidos confirmados + Saldo de requisições
        """
        entradas = []

        # PARTE 1: Pedidos Confirmados (✅ excluindo cancelados)
        pedidos = PedidoCompras.query.filter(
            PedidoCompras.cod_produto == cod_produto,
            PedidoCompras.importado_odoo == True,
            PedidoCompras.data_pedido_previsao.isnot(None),
            PedidoCompras.data_pedido_previsao.between(data_inicio, data_fim),
            PedidoCompras.status_odoo != 'cancel'  # ✅ NÃO considerar cancelados
        ).all()

        for pedido in pedidos:
            entradas.append({
                'data': pedido.data_pedido_previsao,
                'quantidade': float(pedido.qtd_produto_pedido),
                'tipo': 'PEDIDO',
                'origem': pedido.num_pedido,
                'fornecedor': pedido.raz_social
            })

        # PARTE 2: Saldos de Requisições (✅ excluindo rejeitadas/canceladas)
        requisicoes = RequisicaoCompras.query.filter(
            RequisicaoCompras.cod_produto == cod_produto,
            RequisicaoCompras.importado_odoo == True,
            RequisicaoCompras.data_necessidade.isnot(None),
            RequisicaoCompras.data_necessidade.between(data_inicio, data_fim),
            RequisicaoCompras.status.in_(['Aprovada', 'Aguardando Aprovação']),
            RequisicaoCompras.status_requisicao != 'rejected'  # ✅ NÃO considerar rejeitadas
        ).all()

        for requisicao in requisicoes:
            # Calcular saldo não atendido
            qtd_alocada_total = db.session.query(
                func.sum(RequisicaoCompraAlocacao.qtd_alocada)
            ).filter(
                RequisicaoCompraAlocacao.requisicao_compra_id == requisicao.id
            ).scalar() or Decimal('0')

            saldo = requisicao.qtd_produto_requisicao - qtd_alocada_total

            if saldo > 0:
                entradas.append({
                    'data': requisicao.data_necessidade,
                    'quantidade': float(saldo),
                    'tipo': 'SALDO_REQUISICAO',
                    'origem': requisicao.num_requisicao,
                    'fornecedor': None
                })

        return sorted(entradas, key=lambda x: x['data'])

    def _buscar_programacoes_upstream(
        self,
        cod_produto: str,
        data_inicio: date,
        data_fim: date,
        fator_multiplicador: float = 1.0,
        visitados: set = None
    ) -> List[tuple]:
        """
        Busca programações upstream (recursivamente) para produtos intermediários.

        Se cod_produto é intermediário sem programação própria, sobe na hierarquia
        até encontrar produtos com programação.

        Retorna: Lista de tuplas (ProgramacaoProducao, fator_conversao_total)

        ✅ USA CACHE para evitar buscas redundantes
        """
        # ✅ Verificar cache primeiro (somente para fator=1.0, raiz da busca)
        cache_key = (cod_produto, data_inicio, data_fim)
        if fator_multiplicador == 1.0 and cache_key in self._cache_programacoes_upstream:
            # Retornar cópia para não afetar o cache
            return [(prog, fator * fator_multiplicador) for prog, fator in self._cache_programacoes_upstream[cache_key]]

        if visitados is None:
            visitados = set()

        # Evitar loops infinitos
        if cod_produto in visitados:
            return []
        visitados.add(cod_produto)

        resultado = []

        # Primeiro: verificar se este produto TEM programação própria
        programacoes_diretas = ProgramacaoProducao.query.filter(
            ProgramacaoProducao.cod_produto == cod_produto,
            ProgramacaoProducao.data_programacao.between(data_inicio, data_fim)
        ).all()

        if programacoes_diretas:
            # Tem programação direta, retornar
            for prog in programacoes_diretas:
                resultado.append((prog, fator_multiplicador))

            # ✅ Armazenar no cache (somente para fator=1.0)
            if fator_multiplicador == 1.0:
                self._cache_programacoes_upstream[cache_key] = resultado.copy()

            return resultado

        # Segundo: se NÃO tem programação E é intermediário, subir na hierarquia
        if self._eh_produto_intermediario(cod_produto):
            # ✅ Buscar BOMs upstream com cache
            if cod_produto not in self._cache_boms_upstream:
                self._cache_boms_upstream[cod_produto] = ListaMateriais.query.filter(
                    ListaMateriais.cod_produto_componente == cod_produto,
                    ListaMateriais.status == 'ativo'
                ).all()

            boms_upstream = self._cache_boms_upstream[cod_produto]

            for bom in boms_upstream:
                # Fator acumulado: quanto do componente ORIGINAL é necessário
                # por unidade do produto pai
                fator_acumulado = fator_multiplicador * float(bom.qtd_utilizada)

                # Buscar recursivamente upstream
                progs_upstream = self._buscar_programacoes_upstream(
                    bom.cod_produto_produzido,
                    data_inicio,
                    data_fim,
                    fator_acumulado,
                    visitados
                )

                resultado.extend(progs_upstream)

        # ✅ Armazenar no cache (somente para fator=1.0)
        if fator_multiplicador == 1.0:
            self._cache_programacoes_upstream[cache_key] = resultado.copy()

        return resultado

    def _calcular_saidas_por_bom(
        self,
        cod_produto_componente: str,
        data_inicio: date,
        data_fim: date
    ) -> List[Dict]:
        """
        Calcula saídas do componente baseado em:
        - ProgramacaoProducao (produtos finais a produzir)
        - ListaMateriais (quanto de componente cada produto final consome)

        SUPORTA INTERMEDIÁRIOS: Se componente só é usado por intermediários,
        sobe na hierarquia até encontrar programações.
        """
        saidas = []

        # Buscar quais produtos CONSOMEM este componente DIRETAMENTE
        boms = ListaMateriais.query.filter(
            ListaMateriais.cod_produto_componente == cod_produto_componente,
            ListaMateriais.status == 'ativo'
        ).all()

        if not boms:
            return []

        # ✅ NOVA LÓGICA: Buscar programações considerando intermediários
        programacoes_e_fatores = []

        for bom in boms:
            cod_produto_pai = bom.cod_produto_produzido
            qtd_utilizada_base = float(bom.qtd_utilizada)

            # Buscar programações (diretas ou upstream se for intermediário)
            progs = self._buscar_programacoes_upstream(
                cod_produto_pai,
                data_inicio,
                data_fim,
                qtd_utilizada_base
            )

            programacoes_e_fatores.extend(progs)

        # Calcular consumo do componente COM EXPANSÃO DE INTERMEDIÁRIOS
        cache_estoque = {}  # Cache para controlar estoque durante projeção

        # ✅ Função auxiliar para adicionar consumos indiretos RECURSIVAMENTE
        def adicionar_consumos_indiretos(consumos_indiretos, produto_origem, prog):
            """
            Adiciona consumos indiretos às saídas, suportando intermediários aninhados.

            Args:
                consumos_indiretos: Lista de consumos indiretos retornada por _calcular_consumo_recursivo
                produto_origem: Código do produto intermediário que gerou esses consumos
                prog: Objeto ProgramacaoProducao original
            """
            for consumo in consumos_indiretos:
                if consumo['qtd'] > 0:
                    saidas.append({
                        'data': consumo['data'],
                        'quantidade': consumo['qtd'],
                        'tipo': 'CONSUMO_INDIRETO',
                        'produto_produzido': prog.cod_produto,
                        'nome_produto_produzido': prog.nome_produto,
                        'qtd_programada': float(prog.qtd_programada),
                        'via_intermediario': produto_origem,
                        'componente_final': consumo['cod_componente']
                    })

                # Se o componente também tem indiretos (intermediário aninhado), adicionar recursivamente
                if consumo.get('consumos_indiretos'):
                    adicionar_consumos_indiretos(
                        consumo['consumos_indiretos'],
                        consumo['cod_componente'],
                        prog
                    )

        # ✅ NOVA LÓGICA: Processar programações encontradas (diretas ou upstream)
        for prog, fator_conversao in programacoes_e_fatores:
            # fator_conversao já vem acumulado da busca upstream
            # Ex: ACIDO → SALMOURA (0.005) → AZEITONA (2.34) = 0.005 * 2.34 = 0.0117
            qtd_necessaria = prog.qtd_programada * fator_conversao

            if qtd_necessaria > 0:
                # Calcular consumo REAL considerando se é intermediário
                consumo_detalhado = self._calcular_consumo_recursivo(
                    cod_produto_componente,
                    qtd_necessaria,
                    prog.data_programacao,
                    cache_estoque
                )

                # 1. Adicionar consumo direto (do estoque ou total se não for intermediário)
                if consumo_detalhado['consumo_direto'] > 0:
                    saidas.append({
                        'data': prog.data_programacao,
                        'quantidade': consumo_detalhado['consumo_direto'],
                        'tipo': 'CONSUMO_BOM',
                        'produto_produzido': prog.cod_produto,
                        'nome_produto_produzido': prog.nome_produto,
                        'qtd_programada': float(prog.qtd_programada),
                        'qtd_utilizada_unitaria': fator_conversao
                    })

                # 2. ✅ ADICIONAR CONSUMOS INDIRETOS (se houver)
                if consumo_detalhado.get('consumos_indiretos'):
                    adicionar_consumos_indiretos(
                        consumo_detalhado['consumos_indiretos'],
                        cod_produto_componente,
                        prog
                    )

        return sorted(saidas, key=lambda x: x['data'])

    def _eh_produto_intermediario(self, cod_produto: str) -> bool:
        """
        Verifica se produto é intermediário:
        - produto_produzido=True E
        - Consome componentes (tem BOM) E
        - É usado como componente em outros produtos

        ✅ USA CACHE para evitar queries redundantes
        """
        # Verificar cache primeiro
        if cod_produto in self._cache_eh_intermediario:
            return self._cache_eh_intermediario[cod_produto]

        # Calcular e armazenar no cache
        produto = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()

        if not produto or not produto.produto_produzido:
            self._cache_eh_intermediario[cod_produto] = False
            return False

        # Verifica se consome componentes
        tem_bom = ListaMateriais.query.filter_by(
            cod_produto_produzido=cod_produto,
            status='ativo'
        ).first() is not None

        # Verifica se é usado como componente
        eh_usado = ListaMateriais.query.filter_by(
            cod_produto_componente=cod_produto,
            status='ativo'
        ).first() is not None

        resultado = tem_bom and eh_usado
        self._cache_eh_intermediario[cod_produto] = resultado
        return resultado

    def _calcular_consumo_recursivo(
        self,
        cod_produto: str,
        qtd_necessaria: float,
        data_consumo: date,
        cache_estoque: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Calcula consumo REAL considerando produtos intermediários.

        Lógica RECURSIVA:
        1. Se NÃO é intermediário → consumo_direto = qtd_necessaria
        2. Se É intermediário:
           a. Consumir estoque até zero
           b. Se faltou → expandir BOM recursivamente

        Retorna:
        {
            'consumo_direto': float,  # Quanto consome deste produto (nunca > estoque)
            'consumos_indiretos': []  # Consumos dos componentes (se expandiu BOM)
        }
        """
        # Se não é intermediário, consome normalmente
        if not self._eh_produto_intermediario(cod_produto):
            return {
                'consumo_direto': qtd_necessaria,
                'consumos_indiretos': []
            }

        # É intermediário → verificar estoque
        if cod_produto not in cache_estoque:
            cache_estoque[cod_produto] = float(self.estoque_service.calcular_estoque_atual(cod_produto))

        estoque_disponivel = cache_estoque[cod_produto]

        # Caso 1: Tem estoque suficiente
        if estoque_disponivel >= qtd_necessaria:
            cache_estoque[cod_produto] -= qtd_necessaria
            return {
                'consumo_direto': qtd_necessaria,
                'consumos_indiretos': []
            }

        # Caso 2: Estoque insuficiente → consome estoque + expande BOM
        qtd_do_estoque = estoque_disponivel
        qtd_faltante = qtd_necessaria - estoque_disponivel

        # Zera estoque
        cache_estoque[cod_produto] = 0

        # ✅ EXPANDIR BOM DOS COMPONENTES (RECURSIVO)
        bom_componentes = ListaMateriais.query.filter_by(
            cod_produto_produzido=cod_produto,
            status='ativo'
        ).all()

        consumos_indiretos = []
        for bom in bom_componentes:
            qtd_componente_necessaria = qtd_faltante * float(bom.qtd_utilizada)

            # Recursivo: calcular consumo do componente
            consumo_componente = self._calcular_consumo_recursivo(
                bom.cod_produto_componente,
                qtd_componente_necessaria,
                data_consumo,
                cache_estoque
            )

            # ✅ INCLUIR consumos indiretos aninhados para suportar intermediários de intermediários
            consumos_indiretos.append({
                'cod_componente': bom.cod_produto_componente,
                'qtd': consumo_componente['consumo_direto'],
                'data': data_consumo,
                'consumos_indiretos': consumo_componente.get('consumos_indiretos', [])
            })

        return {
            'consumo_direto': qtd_do_estoque,  # Só consome do estoque (nunca negativo)
            'consumos_indiretos': consumos_indiretos
        }

    def _calcular_projecao_diaria(
        self,
        estoque_inicial: Decimal,
        entradas: List[Dict],
        saidas: List[Dict],
        data_inicio: date,
        data_fim: date
    ) -> List[Dict]:
        """
        Calcula projeção dia a dia
        """
        # Agrupar entradas por data
        entradas_por_data = defaultdict(float)
        for entrada in entradas:
            entradas_por_data[entrada['data']] += entrada['quantidade']

        # Agrupar saídas por data
        saidas_por_data = defaultdict(float)
        for saida in saidas:
            saidas_por_data[saida['data']] += saida['quantidade']

        # Calcular projeção dia a dia
        projecao = []
        estoque_atual = float(estoque_inicial)
        data_atual = data_inicio

        while data_atual <= data_fim:
            entrada_dia = entradas_por_data.get(data_atual, 0)
            saida_dia = saidas_por_data.get(data_atual, 0)

            estoque_final = estoque_atual + entrada_dia - saida_dia

            # ✅ MUDOU: Adicionar TODOS os dias (não apenas com movimento)
            projecao.append({
                'data': data_atual.isoformat(),
                'estoque_inicial': round(estoque_atual, 2),
                'entradas': round(entrada_dia, 2),
                'saidas': round(saida_dia, 2),
                'estoque_final': round(estoque_final, 2),
                'ruptura': estoque_final < 0
            })

            estoque_atual = estoque_final
            data_atual += timedelta(days=1)

        return projecao

    def _calcular_consumo_carteira(self, cod_produto_componente: str) -> float:
        """
        Calcula consumo necessário para atender CarteiraPrincipal

        Lógica:
        1. Verifica quais produtos PA (acabados) consomem este componente
        2. Para cada PA, calcula necessidade de produção (Saldo Carteira - Estoque PA)
        3. Multiplica pela estrutura (BOM) para obter consumo do componente
        4. Considera intermediários recursivamente
        """
        from app.carteira.models import CarteiraPrincipal  # ✅ Import correto conforme CLAUDE.md

        consumo_total = 0.0

        # Buscar quais produtos CONSOMEM este componente
        boms = ListaMateriais.query.filter(
            ListaMateriais.cod_produto_componente == cod_produto_componente,
            ListaMateriais.status == 'ativo'
        ).all()

        if not boms:
            return 0.0

        # Para cada produto que usa este componente
        for bom in boms:
            cod_produto_pai = bom.cod_produto_produzido
            qtd_utilizada = float(bom.qtd_utilizada)

            # Calcular necessidade de produção do produto PAI
            # Saldo Carteira
            saldo_carteira = db.session.query(
                func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido)
            ).filter(
                CarteiraPrincipal.cod_produto == cod_produto_pai
            ).scalar() or 0.0

            # Estoque do PA
            estoque_pa = self.estoque_service.calcular_estoque_atual(cod_produto_pai)

            # Necessidade = Saldo Carteira - Estoque (só se negativo)
            necessidade = float(saldo_carteira) - float(estoque_pa)

            if necessidade > 0:
                # Consumo = Necessidade × Qtd Utilizada
                consumo_total += necessidade * qtd_utilizada

        return consumo_total

    def _calcular_consumo_programacao(self, cod_produto_componente: str) -> float:
        """
        Calcula consumo TOTAL através da Programação de Produção

        Considera:
        - Programações diretas de produtos que consomem este componente
        - Programações indiretas via intermediários (SALMOURA, etc.)
        - Estrutura completa da BOM em cascata

        DIFERENTE de _calcular_consumo_carteira que usa Saldo Carteira
        """
        data_inicio = date.today()
        data_fim = date.today() + timedelta(days=365)  # 1 ano à frente

        consumo_total = 0.0
        cache_estoque = {}  # Cache temporário para este cálculo

        # Buscar quais produtos CONSOMEM este componente DIRETAMENTE
        boms = ListaMateriais.query.filter(
            ListaMateriais.cod_produto_componente == cod_produto_componente,
            ListaMateriais.status == 'ativo'
        ).all()

        if not boms:
            return 0.0

        # Para cada produto que consome (pode ser intermediário ou final)
        for bom in boms:
            cod_produto_pai = bom.cod_produto_produzido
            qtd_utilizada_base = float(bom.qtd_utilizada)

            # ✅ Buscar programações (diretas ou upstream se for intermediário)
            programacoes_e_fatores = self._buscar_programacoes_upstream(
                cod_produto_pai,
                data_inicio,
                data_fim,
                qtd_utilizada_base
            )

            # Somar consumo de todas as programações encontradas
            for prog, fator_conversao in programacoes_e_fatores:
                qtd_necessaria = prog.qtd_programada * fator_conversao
                consumo_total += qtd_necessaria

        return consumo_total

    def _calcular_qtd_requisicoes(self, cod_produto: str) -> float:
        """
        Calcula quantidade total em requisições ativas (não rejeitadas)
        """
        qtd = db.session.query(
            func.sum(RequisicaoCompras.qtd_produto_requisicao)
        ).filter(
            RequisicaoCompras.cod_produto == cod_produto,
            RequisicaoCompras.importado_odoo == True,
            RequisicaoCompras.status_requisicao != 'rejected'  # Não canceladas
        ).scalar()

        return float(qtd) if qtd else 0.0

    def _calcular_qtd_pedidos(self, cod_produto: str) -> float:
        """
        Calcula quantidade total em pedidos ativos (não cancelados)
        """
        qtd = db.session.query(
            func.sum(PedidoCompras.qtd_produto_pedido)
        ).filter(
            PedidoCompras.cod_produto == cod_produto,
            PedidoCompras.importado_odoo == True,
            PedidoCompras.status_odoo != 'cancel'  # Não cancelados
        ).scalar()

        return float(qtd) if qtd else 0.0

    def _gerar_timeline_60_dias(
        self,
        estoque_inicial: Decimal,
        entradas: List[Dict],
        saidas: List[Dict]
    ) -> List[float]:
        """
        Gera array de 61 posições com projeção D0 a D60

        Retorna apenas estoque final de cada dia (simplificado para tabela)
        """
        # Agrupar por data
        entradas_por_data = defaultdict(float)
        for e in entradas:
            entradas_por_data[e['data']] += e['quantidade']

        saidas_por_data = defaultdict(float)
        for s in saidas:
            saidas_por_data[s['data']] += s['quantidade']

        # Calcular dia a dia
        timeline = []
        estoque_atual = float(estoque_inicial)
        data_atual = date.today()

        for i in range(61):  # D0 a D60
            entrada_dia = entradas_por_data.get(data_atual, 0)
            saida_dia = saidas_por_data.get(data_atual, 0)

            estoque_atual = estoque_atual + entrada_dia - saida_dia
            timeline.append(round(estoque_atual, 2))

            data_atual += timedelta(days=1)

        return timeline

    def _buscar_produtos_consumidores_com_programacao(
        self,
        cod_produto_componente: str,
        data_inicio: date,
        data_fim: date
    ) -> List[Dict]:
        """
        Busca produtos que consomem este componente E têm programação ativa no período

        Retorna lista com:
        - Produtos finais programados
        - Produtos intermediários expandidos (caminho completo na hierarquia)
        - Quantidade programada e consumo previsto

        Args:
            cod_produto_componente: Código do componente
            data_inicio: Data início do período
            data_fim: Data fim do período

        Returns:
            Lista de dicts com produtos consumidores e suas programações
        """
        from app.producao.models import ProgramacaoProducao

        resultados = []

        # Buscar quais produtos CONSOMEM este componente
        boms = ListaMateriais.query.filter(
            ListaMateriais.cod_produto_componente == cod_produto_componente,
            ListaMateriais.status == 'ativo'
        ).all()

        if not boms:
            return []

        # Para cada produto que consome
        for bom in boms:
            cod_produto_pai = bom.cod_produto_produzido
            qtd_utilizada_base = float(bom.qtd_utilizada)

            # Buscar programações (diretas ou upstream se for intermediário)
            programacoes_e_fatores = self._buscar_programacoes_upstream(
                cod_produto_pai,
                data_inicio,
                data_fim,
                qtd_utilizada_base
            )

            # Se encontrou programações, processar
            for prog, fator_conversao in programacoes_e_fatores:
                qtd_consumo = prog.qtd_programada * fator_conversao

                # Verificar se é intermediário (para expandir caminho)
                eh_intermediario = self._eh_produto_intermediario(cod_produto_pai)

                # Buscar info do produto pai
                produto_pai = CadastroPalletizacao.query.filter_by(
                    cod_produto=cod_produto_pai
                ).first()

                nome_produto_pai = produto_pai.nome_produto if produto_pai else cod_produto_pai

                # Se intermediário, mostrar caminho completo
                caminho_hierarquia = []
                if eh_intermediario:
                    caminho_hierarquia = self._montar_caminho_hierarquia(
                        cod_produto_pai,
                        prog.cod_produto
                    )

                resultados.append({
                    'cod_produto_programado': prog.cod_produto,
                    'nome_produto_programado': prog.nome_produto,
                    'qtd_programada': float(prog.qtd_programada),
                    'data_programacao': prog.data_programacao.isoformat(),
                    'via_intermediario': cod_produto_pai if eh_intermediario else None,
                    'nome_intermediario': nome_produto_pai if eh_intermediario else None,
                    'caminho_hierarquia': caminho_hierarquia if caminho_hierarquia else None,
                    'fator_conversao': fator_conversao,
                    'qtd_consumo_previsto': round(qtd_consumo, 3)
                })

        return resultados

    def _montar_caminho_hierarquia(
        self,
        cod_intermediario: str,
        cod_produto_final: str
    ) -> List[str]:
        """
        Monta o caminho completo da hierarquia BOM

        Ex: ["ACIDO CITRICO", "SALMOURA", "AZEITONA VERDE 180 G"]

        Args:
            cod_intermediario: Código do intermediário
            cod_produto_final: Código do produto final programado

        Returns:
            Lista com nomes dos produtos no caminho
        """
        caminho = []

        # Adicionar intermediário
        produto_int = CadastroPalletizacao.query.filter_by(
            cod_produto=cod_intermediario
        ).first()

        if produto_int:
            caminho.append(produto_int.nome_produto or cod_intermediario)

        # Buscar quem consome o intermediário (subir na hierarquia)
        boms_upstream = ListaMateriais.query.filter(
            ListaMateriais.cod_produto_componente == cod_intermediario,
            ListaMateriais.status == 'ativo'
        ).all()

        # Adicionar próximo nível (recursivamente se necessário)
        for bom in boms_upstream:
            cod_pai = bom.cod_produto_produzido

            # Se chegou no produto final, adicionar e parar
            if cod_pai == cod_produto_final:
                produto_final = CadastroPalletizacao.query.filter_by(
                    cod_produto=cod_produto_final
                ).first()

                if produto_final:
                    caminho.append(produto_final.nome_produto or cod_produto_final)
                break

            # Se é outro intermediário, continuar recursão
            if self._eh_produto_intermediario(cod_pai):
                caminho_restante = self._montar_caminho_hierarquia(cod_pai, cod_produto_final)
                caminho.extend(caminho_restante)
                break

        return caminho
