"""
Servico de Custeio
Calcula custos de produtos comprados, intermediarios e acabados
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from decimal import Decimal
import logging

from app import db
from app.custeio.models import CustoMensal, CustoConsiderado
from app.manufatura.models import PedidoCompras, ListaMateriais
from app.producao.models import CadastroPalletizacao
from app.manufatura.services.bom_service import ServicoBOM
from sqlalchemy import func, extract

logger = logging.getLogger(__name__)


class ServicoCusteio:
    """
    Servico principal para calculo de custos

    Ordem de processamento:
    1. COMPRADOS   -> Custo = (Valor - ICMS - PIS - COFINS) / Qtd
    2. INTERMEDIARIOS -> Custo BOM usando custos de COMPRADOS
    3. ACABADOS    -> Custo BOM usando COMPRADOS + INTERMEDIARIOS
    """

    # ================================================
    # CALCULOS PARA PRODUTOS COMPRADOS
    # ================================================

    @staticmethod
    def calcular_custo_comprados(cod_produto: str, mes: int, ano: int) -> Dict[str, Any]:
        """
        Calcula custos para produtos COMPRADOS

        Formula Custo Liquido Medio:
        (Soma valores - ICMS - PIS - COFINS) / Soma quantidades

        Formula Custo Medio Estoque:
        (custo_estoque_inicial + custo_compras_liquido) / (qtd_inicial + qtd_compras)

        Args:
            cod_produto: Codigo do produto
            mes: Mes de referencia (1-12)
            ano: Ano de referencia

        Returns:
            Dict com custos calculados
        """
        try:
            # Definir periodo do mes
            data_inicio = date(ano, mes, 1)
            if mes == 12:
                data_fim = date(ano + 1, 1, 1)
            else:
                data_fim = date(ano, mes + 1, 1)

            # Buscar compras do mes com status 'done' ou 'purchase' (recebidas)
            # NOTA: Usar data_pedido_criacao pois data_pedido_entrega nao esta preenchida
            # FILTRO: Apenas pedidos de compra/importacao (exclui remessa, transferencia, serv-industrializacao)
            # Tipos validos: 'compra', 'importacao' ou NULL (registros antigos antes do campo existir)
            compras = PedidoCompras.query.filter(
                PedidoCompras.cod_produto == cod_produto,
                PedidoCompras.data_pedido_criacao >= data_inicio,
                PedidoCompras.data_pedido_criacao < data_fim,
                PedidoCompras.status_odoo.in_(['done', 'purchase']),
                db.or_(
                    PedidoCompras.tipo_pedido.in_(['compra', 'importacao']),
                    PedidoCompras.tipo_pedido.is_(None)  # NULL = registros antigos (compras válidas)
                )
            ).all()

            if not compras:
                logger.debug(f"Nenhuma compra encontrada para {cod_produto} em {mes}/{ano}")
                return {
                    'custo_liquido_medio': None,
                    'custo_medio_estoque': None,
                    'ultimo_custo': None,
                    'qtd_comprada': 0,
                    'valor_bruto': 0,
                    'valor_icms': 0,
                    'valor_pis': 0,
                    'valor_cofins': 0,
                    'valor_liquido': 0,
                    'estoque_inicial': {'qtd': 0, 'custo': 0}
                }

            # Somar valores - usar qtd_recebida se disponivel, senao qtd_produto_pedido
            qtd_total = 0
            valor_bruto = 0
            valor_icms = 0
            valor_pis = 0
            valor_cofins = 0

            for c in compras:
                # Preferir qtd_recebida (quantidade realmente recebida)
                qtd = float(c.qtd_recebida or c.qtd_produto_pedido or 0)
                preco = float(c.preco_produto_pedido or 0)

                qtd_total += qtd
                valor_bruto += preco * qtd
                valor_icms += float(c.icms_produto_pedido or 0)
                valor_pis += float(c.pis_produto_pedido or 0)
                valor_cofins += float(c.cofins_produto_pedido or 0)

            # Valor liquido (descontando impostos)
            valor_liquido = valor_bruto - valor_icms - valor_pis - valor_cofins

            # Custo liquido medio
            custo_liquido_medio = valor_liquido / qtd_total if qtd_total > 0 else 0

            # Ultimo custo (ultima compra do periodo)
            compras_ordenadas = sorted(
                [c for c in compras if c.data_pedido_criacao],
                key=lambda c: c.data_pedido_criacao,
                reverse=True
            )

            ultimo_custo = 0
            if compras_ordenadas:
                ultima_compra = compras_ordenadas[0]
                preco_unitario = float(ultima_compra.preco_produto_pedido or 0)

                # Descontar impostos proporcionalmente do ultimo custo
                if valor_bruto > 0:
                    taxa_impostos = (valor_icms + valor_pis + valor_cofins) / valor_bruto
                    ultimo_custo = preco_unitario * (1 - taxa_impostos)
                else:
                    ultimo_custo = preco_unitario

            # Buscar estoque inicial do mes
            estoque_inicial = ServicoCusteio._buscar_estoque_inicial(cod_produto, mes, ano)

            # Custo medio do estoque
            qtd_total_estoque = estoque_inicial['qtd'] + qtd_total
            custo_total_estoque = estoque_inicial['custo'] + valor_liquido
            custo_medio_estoque = custo_total_estoque / qtd_total_estoque if qtd_total_estoque > 0 else 0

            return {
                'custo_liquido_medio': round(custo_liquido_medio, 6),
                'custo_medio_estoque': round(custo_medio_estoque, 6),
                'ultimo_custo': round(ultimo_custo, 6),
                'qtd_comprada': qtd_total,
                'valor_bruto': valor_bruto,
                'valor_icms': valor_icms,
                'valor_pis': valor_pis,
                'valor_cofins': valor_cofins,
                'valor_liquido': valor_liquido,
                'estoque_inicial': estoque_inicial
            }

        except Exception as e:
            logger.error(f"Erro ao calcular custo de {cod_produto}: {e}")
            return {
                'custo_liquido_medio': None,
                'custo_medio_estoque': None,
                'ultimo_custo': None,
                'qtd_comprada': 0,
                'valor_bruto': 0,
                'valor_icms': 0,
                'valor_pis': 0,
                'valor_cofins': 0,
                'valor_liquido': 0,
                'estoque_inicial': {'qtd': 0, 'custo': 0},
                'erro': str(e)
            }

    # ================================================
    # CALCULOS PARA PRODUTOS INTERMEDIARIOS E ACABADOS
    # ================================================

    @staticmethod
    def calcular_custo_bom(
        cod_produto: str,
        custos_componentes: Dict[str, float],
        custos_intermediarios: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Calcula custo de produto pela explosao BOM

        Args:
            cod_produto: Codigo do produto a calcular
            custos_componentes: Dict {cod_produto: custo} dos componentes comprados
            custos_intermediarios: Dict {cod_produto: custo} dos intermediarios (opcional)

        Returns:
            Dict com custo BOM calculado e detalhamento
        """
        try:
            if custos_intermediarios is None:
                custos_intermediarios = {}

            # Explodir BOM do produto
            bom = ServicoBOM.explodir_bom(cod_produto, 1.0)

            if bom.get('erro') or not bom.get('tem_estrutura'):
                return {
                    'custo_bom': None,
                    'componentes': [],
                    'erro': bom.get('erro', 'Produto sem estrutura BOM')
                }

            # Funcao recursiva para calcular custo
            def calcular_custo_recursivo(componentes: List[Dict], nivel: int = 0) -> tuple:
                """Retorna (custo_total, lista_componentes_usados)"""
                custo = 0
                componentes_usados = []

                for comp in componentes:
                    cod_comp = comp['cod_produto']
                    qtd = comp['qtd_necessaria']
                    tipo = comp.get('tipo', 'DESCONHECIDO')

                    custo_unit = 0

                    if tipo == 'COMPONENTE' or comp.get('produto_comprado'):
                        # Produto comprado - usar custo ja calculado
                        custo_unit = custos_componentes.get(cod_comp, 0)
                    elif tipo == 'INTERMEDIARIO':
                        # Produto intermediario - usar custo BOM calculado
                        custo_unit = custos_intermediarios.get(cod_comp, 0)
                    elif comp.get('tem_estrutura') and comp.get('componentes'):
                        # Recursao para sub-componentes
                        custo_unit, _ = calcular_custo_recursivo(comp['componentes'], nivel + 1)

                    custo_parcial = custo_unit * qtd
                    custo += custo_parcial

                    componentes_usados.append({
                        'cod_produto': cod_comp,
                        'nome_produto': comp.get('nome_produto', ''),
                        'tipo': tipo,
                        'qtd_necessaria': qtd,
                        'custo_unitario': custo_unit,
                        'custo_total': custo_parcial,
                        'nivel': nivel
                    })

                return custo, componentes_usados

            custo_total, componentes_detalhados = calcular_custo_recursivo(bom['componentes'])

            return {
                'custo_bom': round(custo_total, 6),
                'componentes': componentes_detalhados,
                'estrutura': bom,
                'erro': None
            }

        except Exception as e:
            logger.error(f"Erro ao calcular custo BOM de {cod_produto}: {e}")
            return {
                'custo_bom': None,
                'componentes': [],
                'erro': str(e)
            }

    # ================================================
    # FECHAMENTO MENSAL
    # ================================================

    @staticmethod
    def fechar_mes(mes: int, ano: int, usuario: str) -> Dict[str, Any]:
        """
        Executa fechamento mensal de custos

        Ordem de processamento:
        1. Produtos COMPRADOS
        2. Produtos INTERMEDIARIOS (dependem dos comprados)
        3. Produtos ACABADOS (dependem de intermediarios + comprados)

        Args:
            mes: Mes de referencia (1-12)
            ano: Ano de referencia
            usuario: Nome do usuario que executou

        Returns:
            Dict com resultado do fechamento
        """
        try:
            logger.info(f"Iniciando fechamento de custos para {mes}/{ano} por {usuario}")

            resultado = {
                'comprados': {'processados': 0, 'erros': []},
                'intermediarios': {'processados': 0, 'erros': []},
                'acabados': {'processados': 0, 'erros': []},
                'total': 0,
                'erro': None
            }

            # Dicionarios para custos calculados
            custos_comprados = {}
            custos_intermediarios = {}

            # ============================================
            # FASE 1: Produtos COMPRADOS
            # ============================================
            logger.info("Fase 1: Processando produtos COMPRADOS...")

            produtos_comprados = CadastroPalletizacao.query.filter_by(
                produto_comprado=True,
                ativo=True
            ).all()

            for produto in produtos_comprados:
                try:
                    custos = ServicoCusteio.calcular_custo_comprados(
                        produto.cod_produto, mes, ano
                    )

                    # Criar/atualizar registro de custo mensal
                    ServicoCusteio._salvar_custo_mensal(
                        cod_produto=produto.cod_produto,
                        nome_produto=produto.nome_produto,
                        mes=mes,
                        ano=ano,
                        tipo_produto='COMPRADO',
                        custos=custos,
                        usuario=usuario
                    )

                    # Guardar custo para uso nos intermediarios/acabados
                    if custos.get('custo_liquido_medio') is not None:
                        custos_comprados[produto.cod_produto] = custos['custo_liquido_medio']

                    resultado['comprados']['processados'] += 1

                except Exception as e:
                    logger.error(f"Erro ao processar {produto.cod_produto}: {e}")
                    resultado['comprados']['erros'].append(f"{produto.cod_produto}: {str(e)}")

            logger.info(f"Fase 1 concluida: {resultado['comprados']['processados']} comprados processados")

            # ============================================
            # FASE 2: Produtos INTERMEDIARIOS
            # ============================================
            logger.info("Fase 2: Processando produtos INTERMEDIARIOS...")

            produtos_intermediarios = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.produto_produzido == True,
                CadastroPalletizacao.produto_vendido == False,
                CadastroPalletizacao.ativo == True
            ).all()

            for produto in produtos_intermediarios:
                try:
                    custos = ServicoCusteio.calcular_custo_bom(
                        produto.cod_produto,
                        custos_comprados
                    )

                    if custos.get('custo_bom') is not None:
                        ServicoCusteio._salvar_custo_mensal(
                            cod_produto=produto.cod_produto,
                            nome_produto=produto.nome_produto,
                            mes=mes,
                            ano=ano,
                            tipo_produto='INTERMEDIARIO',
                            custos={'custo_bom': custos['custo_bom']},
                            usuario=usuario
                        )

                        custos_intermediarios[produto.cod_produto] = custos['custo_bom']
                        resultado['intermediarios']['processados'] += 1
                    else:
                        resultado['intermediarios']['erros'].append(
                            f"{produto.cod_produto}: {custos.get('erro', 'Sem estrutura BOM')}"
                        )

                except Exception as e:
                    logger.error(f"Erro ao processar intermediario {produto.cod_produto}: {e}")
                    resultado['intermediarios']['erros'].append(f"{produto.cod_produto}: {str(e)}")

            logger.info(f"Fase 2 concluida: {resultado['intermediarios']['processados']} intermediarios processados")

            # ============================================
            # FASE 3: Produtos ACABADOS
            # ============================================
            logger.info("Fase 3: Processando produtos ACABADOS...")

            produtos_acabados = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.produto_produzido == True,
                CadastroPalletizacao.produto_vendido == True,
                CadastroPalletizacao.ativo == True
            ).all()

            for produto in produtos_acabados:
                try:
                    custos = ServicoCusteio.calcular_custo_bom(
                        produto.cod_produto,
                        custos_comprados,
                        custos_intermediarios
                    )

                    if custos.get('custo_bom') is not None:
                        ServicoCusteio._salvar_custo_mensal(
                            cod_produto=produto.cod_produto,
                            nome_produto=produto.nome_produto,
                            mes=mes,
                            ano=ano,
                            tipo_produto='ACABADO',
                            custos={'custo_bom': custos['custo_bom']},
                            usuario=usuario
                        )

                        resultado['acabados']['processados'] += 1
                    else:
                        resultado['acabados']['erros'].append(
                            f"{produto.cod_produto}: {custos.get('erro', 'Sem estrutura BOM')}"
                        )

                except Exception as e:
                    logger.error(f"Erro ao processar acabado {produto.cod_produto}: {e}")
                    resultado['acabados']['erros'].append(f"{produto.cod_produto}: {str(e)}")

            logger.info(f"Fase 3 concluida: {resultado['acabados']['processados']} acabados processados")

            # ============================================
            # ATUALIZAR CUSTO CONSIDERADO
            # ============================================
            logger.info("Atualizando custos considerados...")
            ServicoCusteio._atualizar_custos_considerados(mes, ano)

            resultado['total'] = (
                resultado['comprados']['processados'] +
                resultado['intermediarios']['processados'] +
                resultado['acabados']['processados']
            )

            db.session.commit()

            logger.info(f"Fechamento concluido: {resultado['total']} produtos processados")
            return resultado

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro fatal no fechamento: {e}")
            return {
                'comprados': {'processados': 0, 'erros': []},
                'intermediarios': {'processados': 0, 'erros': []},
                'acabados': {'processados': 0, 'erros': []},
                'total': 0,
                'erro': str(e)
            }

    # ================================================
    # PREVIEW (SIMULACAO)
    # ================================================

    @staticmethod
    def simular_fechamento(mes: int, ano: int) -> Dict[str, Any]:
        """
        Simula fechamento sem persistir dados

        Returns:
            Dict com preview dos calculos
        """
        try:
            preview = {
                'comprados': [],
                'intermediarios': [],
                'acabados': [],
                'resumo': {
                    'total_comprados': 0,
                    'total_intermediarios': 0,
                    'total_acabados': 0
                }
            }

            custos_comprados = {}
            custos_intermediarios = {}

            # Produtos comprados
            produtos_comprados = CadastroPalletizacao.query.filter_by(
                produto_comprado=True,
                ativo=True
            ).all()

            for produto in produtos_comprados:
                custos = ServicoCusteio.calcular_custo_comprados(
                    produto.cod_produto, mes, ano
                )

                if custos.get('custo_liquido_medio') is not None:
                    custos_comprados[produto.cod_produto] = custos['custo_liquido_medio']

                preview['comprados'].append({
                    'cod_produto': produto.cod_produto,
                    'nome_produto': produto.nome_produto,
                    **custos
                })

            preview['resumo']['total_comprados'] = len(preview['comprados'])

            # Produtos intermediarios
            produtos_intermediarios = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.produto_produzido == True,
                CadastroPalletizacao.produto_vendido == False,
                CadastroPalletizacao.ativo == True
            ).all()

            for produto in produtos_intermediarios:
                custos = ServicoCusteio.calcular_custo_bom(
                    produto.cod_produto,
                    custos_comprados
                )

                if custos.get('custo_bom') is not None:
                    custos_intermediarios[produto.cod_produto] = custos['custo_bom']

                preview['intermediarios'].append({
                    'cod_produto': produto.cod_produto,
                    'nome_produto': produto.nome_produto,
                    'custo_bom': custos.get('custo_bom'),
                    'erro': custos.get('erro')
                })

            preview['resumo']['total_intermediarios'] = len(preview['intermediarios'])

            # Produtos acabados
            produtos_acabados = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.produto_produzido == True,
                CadastroPalletizacao.produto_vendido == True,
                CadastroPalletizacao.ativo == True
            ).all()

            for produto in produtos_acabados:
                custos = ServicoCusteio.calcular_custo_bom(
                    produto.cod_produto,
                    custos_comprados,
                    custos_intermediarios
                )

                preview['acabados'].append({
                    'cod_produto': produto.cod_produto,
                    'nome_produto': produto.nome_produto,
                    'custo_bom': custos.get('custo_bom'),
                    'erro': custos.get('erro')
                })

            preview['resumo']['total_acabados'] = len(preview['acabados'])

            return preview

        except Exception as e:
            logger.error(f"Erro na simulacao: {e}")
            return {'erro': str(e)}

    # ================================================
    # METODOS AUXILIARES
    # ================================================

    @staticmethod
    def _buscar_estoque_inicial(cod_produto: str, mes: int, ano: int) -> Dict:
        """Busca estoque inicial do mes a partir do fechamento anterior"""
        # Buscar custo mensal do mes anterior
        mes_anterior = mes - 1 if mes > 1 else 12
        ano_anterior = ano if mes > 1 else ano - 1

        custo_anterior = CustoMensal.query.filter_by(
            cod_produto=cod_produto,
            mes=mes_anterior,
            ano=ano_anterior,
            status='FECHADO'
        ).first()

        if custo_anterior:
            return {
                'qtd': float(custo_anterior.qtd_estoque_final or 0),
                'custo': float(custo_anterior.custo_estoque_final or 0)
            }

        return {'qtd': 0, 'custo': 0}

    @staticmethod
    def _salvar_custo_mensal(
        cod_produto: str,
        nome_produto: str,
        mes: int,
        ano: int,
        tipo_produto: str,
        custos: Dict,
        usuario: str
    ):
        """Salva ou atualiza registro de custo mensal"""
        registro = CustoMensal.query.filter_by(
            cod_produto=cod_produto,
            mes=mes,
            ano=ano
        ).first()

        if not registro:
            registro = CustoMensal(
                cod_produto=cod_produto,
                nome_produto=nome_produto,
                mes=mes,
                ano=ano,
                tipo_produto=tipo_produto
            )
            db.session.add(registro)

        # Atualizar campos baseado no tipo de produto
        if tipo_produto == 'COMPRADO':
            registro.custo_liquido_medio = custos.get('custo_liquido_medio')
            registro.custo_medio_estoque = custos.get('custo_medio_estoque')
            registro.ultimo_custo = custos.get('ultimo_custo')
            registro.qtd_comprada = custos.get('qtd_comprada')
            registro.valor_compras_bruto = custos.get('valor_bruto')
            registro.valor_icms = custos.get('valor_icms')
            registro.valor_pis = custos.get('valor_pis')
            registro.valor_cofins = custos.get('valor_cofins')
            registro.valor_compras_liquido = custos.get('valor_liquido')

            estoque = custos.get('estoque_inicial', {})
            registro.qtd_estoque_inicial = estoque.get('qtd', 0)
            registro.custo_estoque_inicial = estoque.get('custo', 0)

            # Calcular estoque final
            registro.qtd_estoque_final = (
                float(registro.qtd_estoque_inicial or 0) +
                float(registro.qtd_comprada or 0)
            )
            registro.custo_estoque_final = (
                float(registro.custo_estoque_inicial or 0) +
                float(registro.valor_compras_liquido or 0)
            )
        else:
            registro.custo_bom = custos.get('custo_bom')

        registro.tipo_produto = tipo_produto
        registro.status = 'FECHADO'
        registro.fechado_em = datetime.utcnow()
        registro.fechado_por = usuario

    @staticmethod
    def _atualizar_custos_considerados(mes: int, ano: int):
        """
        Atualiza tabela de custos considerados apos fechamento
        Cria nova versao apenas se houve mudanca de valores
        """
        custos_mes = CustoMensal.query.filter_by(
            mes=mes,
            ano=ano,
            status='FECHADO'
        ).all()

        for custo in custos_mes:
            # Buscar versao atual
            considerado = CustoConsiderado.query.filter_by(
                cod_produto=custo.cod_produto,
                custo_atual=True
            ).first()

            if not considerado:
                # Primeiro registro - criar versao 1
                considerado = CustoConsiderado(
                    cod_produto=custo.cod_produto,
                    nome_produto=custo.nome_produto,
                    tipo_produto=custo.tipo_produto,
                    versao=1,
                    custo_atual=True,
                    vigencia_inicio=datetime.utcnow(),
                    motivo_alteracao=f'Fechamento {mes}/{ano}'
                )
                db.session.add(considerado)

                # Atualizar valores do novo registro
                considerado.custo_medio_mes = custo.custo_liquido_medio
                considerado.ultimo_custo = custo.ultimo_custo
                considerado.custo_medio_estoque = custo.custo_medio_estoque
                considerado.custo_bom = custo.custo_bom
                considerado.qtd_estoque_inicial = custo.qtd_estoque_inicial
                considerado.custo_estoque_inicial = custo.custo_estoque_inicial
                considerado.qtd_comprada_periodo = custo.qtd_comprada
                considerado.custo_compras_periodo = custo.valor_compras_liquido
                considerado.qtd_estoque_final = custo.qtd_estoque_final
                considerado.custo_estoque_final = custo.custo_estoque_final
                considerado.ultimo_mes_fechado = mes
                considerado.ultimo_ano_fechado = ano
                considerado.recalcular_custo_considerado()
            else:
                # Ja existe - atualizar versao atual (fechamento nao cria nova versao)
                # Apenas alterar tipo de custo cria nova versao
                considerado.custo_medio_mes = custo.custo_liquido_medio
                considerado.ultimo_custo = custo.ultimo_custo
                considerado.custo_medio_estoque = custo.custo_medio_estoque
                considerado.custo_bom = custo.custo_bom
                considerado.qtd_estoque_inicial = custo.qtd_estoque_inicial
                considerado.custo_estoque_inicial = custo.custo_estoque_inicial
                considerado.qtd_comprada_periodo = custo.qtd_comprada
                considerado.custo_compras_periodo = custo.valor_compras_liquido
                considerado.qtd_estoque_final = custo.qtd_estoque_final
                considerado.custo_estoque_final = custo.custo_estoque_final
                considerado.ultimo_mes_fechado = mes
                considerado.ultimo_ano_fechado = ano
                considerado.recalcular_custo_considerado()

    # ================================================
    # CONSULTAS
    # ================================================

    @staticmethod
    def listar_custos_mensais(
        mes: Optional[int] = None,
        ano: Optional[int] = None,
        tipo_produto: Optional[str] = None,
        cod_produto: Optional[str] = None
    ) -> List[Dict]:
        """Lista custos mensais com filtros"""
        query = CustoMensal.query

        if mes:
            query = query.filter_by(mes=mes)
        if ano:
            query = query.filter_by(ano=ano)
        if tipo_produto:
            query = query.filter_by(tipo_produto=tipo_produto)
        if cod_produto:
            query = query.filter(CustoMensal.cod_produto.ilike(f'%{cod_produto}%'))

        custos = query.order_by(CustoMensal.cod_produto).all()
        return [c.to_dict() for c in custos]

    @staticmethod
    def listar_custos_considerados(
        tipo_produto: Optional[str] = None,
        cod_produto: Optional[str] = None,
        apenas_atuais: bool = True
    ) -> List[Dict]:
        """
        Lista custos considerados com filtros

        Args:
            tipo_produto: Filtrar por tipo (COMPRADO, INTERMEDIARIO, ACABADO)
            cod_produto: Filtrar por codigo ou nome
            apenas_atuais: Se True, retorna apenas versoes atuais (default)

        Returns:
            Lista de custos considerados
        """
        query = CustoConsiderado.query

        if apenas_atuais:
            query = query.filter_by(custo_atual=True)
        if tipo_produto:
            query = query.filter_by(tipo_produto=tipo_produto)
        if cod_produto:
            query = query.filter(CustoConsiderado.cod_produto.ilike(f'%{cod_produto}%'))

        custos = query.order_by(CustoConsiderado.cod_produto).all()
        return [c.to_dict() for c in custos]

    @staticmethod
    def alterar_tipo_custo(
        cod_produto: str,
        tipo_custo: str,
        usuario: str,
        motivo: str = None
    ) -> Dict:
        """
        Altera o tipo de custo considerado para um produto
        Cria nova versao mantendo historico

        Args:
            cod_produto: Codigo do produto
            tipo_custo: Novo tipo de custo (MEDIO_MES, ULTIMO_CUSTO, MEDIO_ESTOQUE, BOM)
            usuario: Nome do usuario que fez a alteracao
            motivo: Motivo da alteracao (opcional)

        Returns:
            Dict com resultado da operacao
        """
        tipos_validos = ['MEDIO_MES', 'ULTIMO_CUSTO', 'MEDIO_ESTOQUE', 'BOM']

        if tipo_custo not in tipos_validos:
            return {'erro': f'Tipo invalido. Valores permitidos: {tipos_validos}'}

        # Buscar versao atual
        custo_atual = CustoConsiderado.query.filter_by(
            cod_produto=cod_produto,
            custo_atual=True
        ).first()

        if not custo_atual:
            return {'erro': 'Produto nao encontrado'}

        # Se o tipo nao mudou, apenas atualizar sem criar nova versao
        if custo_atual.tipo_custo_selecionado == tipo_custo:
            custo_atual.recalcular_custo_considerado()
            db.session.commit()
            return {
                'sucesso': True,
                'custo_considerado': float(custo_atual.custo_considerado or 0),
                'tipo_selecionado': tipo_custo,
                'versao': custo_atual.versao
            }

        # Criar nova versao com versionamento
        nova_versao = ServicoCusteio._criar_nova_versao_custo(
            custo_atual=custo_atual,
            tipo_custo=tipo_custo,
            usuario=usuario,
            motivo=motivo or f'Alteracao de tipo: {custo_atual.tipo_custo_selecionado} -> {tipo_custo}'
        )

        db.session.commit()

        return {
            'sucesso': True,
            'custo_considerado': float(nova_versao.custo_considerado or 0),
            'tipo_selecionado': tipo_custo,
            'versao': nova_versao.versao,
            'versao_anterior': custo_atual.versao
        }

    @staticmethod
    def _criar_nova_versao_custo(
        custo_atual: CustoConsiderado,
        tipo_custo: str = None,
        usuario: str = None,
        motivo: str = None,
        novos_valores: Dict = None
    ) -> CustoConsiderado:
        """
        Cria nova versao de custo considerado mantendo historico

        Args:
            custo_atual: Versao atual do custo
            tipo_custo: Novo tipo de custo (opcional)
            usuario: Usuario que fez a alteracao
            motivo: Motivo da alteracao
            novos_valores: Dict com novos valores a atualizar

        Returns:
            Nova versao do CustoConsiderado
        """
        # Marcar versao atual como historica
        custo_atual.custo_atual = False
        custo_atual.vigencia_fim = datetime.utcnow()

        # Criar nova versao
        nova_versao = CustoConsiderado(
            cod_produto=custo_atual.cod_produto,
            nome_produto=custo_atual.nome_produto,
            tipo_produto=custo_atual.tipo_produto,
            versao=custo_atual.versao + 1,
            custo_atual=True,
            vigencia_inicio=datetime.utcnow(),
            motivo_alteracao=motivo,
            # Copiar valores da versao anterior
            custo_medio_mes=custo_atual.custo_medio_mes,
            ultimo_custo=custo_atual.ultimo_custo,
            custo_medio_estoque=custo_atual.custo_medio_estoque,
            custo_bom=custo_atual.custo_bom,
            custo_producao=custo_atual.custo_producao,
            tipo_custo_selecionado=tipo_custo or custo_atual.tipo_custo_selecionado,
            qtd_estoque_inicial=custo_atual.qtd_estoque_inicial,
            custo_estoque_inicial=custo_atual.custo_estoque_inicial,
            qtd_comprada_periodo=custo_atual.qtd_comprada_periodo,
            custo_compras_periodo=custo_atual.custo_compras_periodo,
            qtd_estoque_final=custo_atual.qtd_estoque_final,
            custo_estoque_final=custo_atual.custo_estoque_final,
            ultimo_mes_fechado=custo_atual.ultimo_mes_fechado,
            ultimo_ano_fechado=custo_atual.ultimo_ano_fechado,
            atualizado_por=usuario
        )

        # Aplicar novos valores se fornecidos
        custo_definido_manual = False
        if novos_valores:
            for campo, valor in novos_valores.items():
                if hasattr(nova_versao, campo):
                    setattr(nova_versao, campo, valor)
                    # Se custo_considerado foi passado explicitamente, não recalcular
                    if campo == 'custo_considerado' and valor is not None:
                        custo_definido_manual = True

        # Recalcular custo considerado APENAS se não foi definido manualmente
        # Caso contrário, o valor manual seria sobrescrito pelo tipo_custo_selecionado
        if not custo_definido_manual:
            nova_versao.recalcular_custo_considerado()

        db.session.add(nova_versao)
        return nova_versao

    @staticmethod
    def cadastrar_custo_manual(
        cod_produto: str,
        custo_considerado: float,
        custo_producao: float = None,
        tipo_custo: str = 'MEDIO_MES',
        usuario: str = None,
        motivo: str = None
    ) -> Dict:
        """
        Cadastra ou atualiza custo considerado manualmente
        Permite cadastrar sem depender de fechamento mensal

        Args:
            cod_produto: Codigo do produto
            custo_considerado: Valor do custo considerado
            custo_producao: Custo de producao adicional (opcional)
            tipo_custo: Tipo de custo base
            usuario: Usuario que fez a alteracao
            motivo: Motivo da alteracao

        Returns:
            Dict com resultado da operacao
        """
        from app.producao.models import CadastroPalletizacao

        # Buscar produto no cadastro
        produto = CadastroPalletizacao.query.filter_by(cod_produto=cod_produto).first()

        if not produto:
            return {'erro': 'Produto nao encontrado no cadastro'}

        # Determinar tipo do produto
        if produto.produto_comprado:
            tipo_produto = 'COMPRADO'
        elif produto.produto_produzido and not produto.produto_vendido:
            tipo_produto = 'INTERMEDIARIO'
        else:
            tipo_produto = 'ACABADO'

        # Buscar versao atual
        custo_atual = CustoConsiderado.query.filter_by(
            cod_produto=cod_produto,
            custo_atual=True
        ).first()

        if custo_atual:
            # Criar nova versao
            nova_versao = ServicoCusteio._criar_nova_versao_custo(
                custo_atual=custo_atual,
                tipo_custo=tipo_custo,
                usuario=usuario,
                motivo=motivo or 'Cadastro manual de custo',
                novos_valores={
                    'custo_considerado': custo_considerado,
                    'custo_producao': custo_producao
                }
            )
        else:
            # Criar primeiro registro
            nova_versao = CustoConsiderado(
                cod_produto=cod_produto,
                nome_produto=produto.nome_produto,
                tipo_produto=tipo_produto,
                versao=1,
                custo_atual=True,
                vigencia_inicio=datetime.utcnow(),
                motivo_alteracao=motivo or 'Cadastro manual inicial',
                tipo_custo_selecionado=tipo_custo,
                custo_considerado=custo_considerado,
                custo_producao=custo_producao,
                atualizado_por=usuario
            )
            db.session.add(nova_versao)

        db.session.commit()

        return {
            'sucesso': True,
            'cod_produto': cod_produto,
            'custo_considerado': float(nova_versao.custo_considerado or 0),
            'custo_producao': float(nova_versao.custo_producao or 0),
            'versao': nova_versao.versao
        }

    @staticmethod
    def listar_historico_custo(cod_produto: str) -> List[Dict]:
        """
        Lista historico completo de custos de um produto

        Args:
            cod_produto: Codigo do produto

        Returns:
            Lista de versoes ordenadas por versao (mais recente primeiro)
        """
        custos = CustoConsiderado.query.filter_by(
            cod_produto=cod_produto
        ).order_by(CustoConsiderado.versao.desc()).all()

        return [c.to_dict() for c in custos]

    # ================================================
    # PROPAGACAO AUTOMATICA DE CUSTOS VIA BOM
    # ================================================

    @staticmethod
    def propagar_custos_bom(usuario: str = 'Sistema') -> Dict[str, Any]:
        """
        Propaga custos dos COMPRADOS para INTERMEDIARIOS e ACABADOS via BOM.

        Ordem de processamento:
        1. Busca custos considerados de todos COMPRADOS
        2. Calcula e salva custos de INTERMEDIARIOS
        3. Calcula e salva custos de ACABADOS

        Args:
            usuario: Usuario que disparou a propagacao

        Returns:
            Dict com resultado da propagacao
        """
        from app.manufatura.models import ListaMateriais

        resultado = {
            'sucesso': True,
            'intermediarios': {'atualizados': 0, 'erros': []},
            'acabados': {'atualizados': 0, 'erros': []},
            'total_atualizados': 0
        }

        try:
            # ============================================
            # FASE 1: Carregar custos dos COMPRADOS
            # ============================================
            custos_comprados = {}
            for c in CustoConsiderado.query.filter_by(custo_atual=True).all():
                produto = CadastroPalletizacao.query.filter_by(cod_produto=c.cod_produto).first()
                if produto and produto.produto_comprado and c.custo_considerado:
                    custos_comprados[c.cod_produto] = float(c.custo_considerado)

            logger.info(f"Propagacao: {len(custos_comprados)} comprados com custo definido")

            if not custos_comprados:
                resultado['aviso'] = 'Nenhum componente COMPRADO com custo definido'
                return resultado

            # ============================================
            # FASE 2: Identificar produtos com BOM
            # ============================================
            produtos_com_bom = set(
                bom.cod_produto_produzido for bom in
                ListaMateriais.query.filter_by(status='ativo')
                .with_entities(ListaMateriais.cod_produto_produzido).distinct()
            )

            # Cache de BOMs
            bom_cache = {}
            for bom in ListaMateriais.query.filter_by(status='ativo').all():
                if bom.cod_produto_produzido not in bom_cache:
                    bom_cache[bom.cod_produto_produzido] = []
                bom_cache[bom.cod_produto_produzido].append({
                    'cod_componente': bom.cod_produto_componente,
                    'qtd': float(bom.qtd_utilizada) if bom.qtd_utilizada else 0
                })

            # ============================================
            # FASE 3: Funcao de calculo recursivo
            # ============================================
            custos_calculados = dict(custos_comprados)  # Começa com comprados

            def calcular_custo_bom_recursivo(cod_produto, visitados=None):
                """Calcula custo via BOM recursivamente"""
                if visitados is None:
                    visitados = set()

                if cod_produto in visitados:
                    return None  # Evitar loop

                # Se já tem custo calculado, retorna
                if cod_produto in custos_calculados:
                    return custos_calculados[cod_produto]

                # Se não tem BOM, não pode calcular
                if cod_produto not in produtos_com_bom:
                    return None

                visitados.add(cod_produto)
                componentes = bom_cache.get(cod_produto, [])

                custo_total = 0
                todos_componentes_ok = True

                for comp in componentes:
                    custo_comp = calcular_custo_bom_recursivo(comp['cod_componente'], visitados.copy())
                    if custo_comp is not None:
                        custo_total += custo_comp * comp['qtd']
                    else:
                        todos_componentes_ok = False

                if todos_componentes_ok and custo_total > 0:
                    custos_calculados[cod_produto] = custo_total
                    return custo_total

                return None

            # ============================================
            # FASE 4: Processar INTERMEDIARIOS
            # ============================================
            produtos_intermediarios = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.produto_produzido == True,
                CadastroPalletizacao.produto_vendido == False,
                CadastroPalletizacao.ativo == True
            ).all()

            for produto in produtos_intermediarios:
                try:
                    custo = calcular_custo_bom_recursivo(produto.cod_produto)
                    if custo is not None:
                        ServicoCusteio._salvar_custo_propagado(
                            cod_produto=produto.cod_produto,
                            nome_produto=produto.nome_produto,
                            tipo_produto='INTERMEDIARIO',
                            custo_considerado=custo,
                            usuario=usuario
                        )
                        resultado['intermediarios']['atualizados'] += 1
                except Exception as e:
                    resultado['intermediarios']['erros'].append(f"{produto.cod_produto}: {str(e)}")

            # ============================================
            # FASE 5: Processar ACABADOS
            # ============================================
            produtos_acabados = CadastroPalletizacao.query.filter(
                CadastroPalletizacao.produto_produzido == True,
                CadastroPalletizacao.produto_vendido == True,
                CadastroPalletizacao.ativo == True
            ).all()

            for produto in produtos_acabados:
                try:
                    custo = calcular_custo_bom_recursivo(produto.cod_produto)
                    if custo is not None:
                        ServicoCusteio._salvar_custo_propagado(
                            cod_produto=produto.cod_produto,
                            nome_produto=produto.nome_produto,
                            tipo_produto='ACABADO',
                            custo_considerado=custo,
                            usuario=usuario
                        )
                        resultado['acabados']['atualizados'] += 1
                except Exception as e:
                    resultado['acabados']['erros'].append(f"{produto.cod_produto}: {str(e)}")

            resultado['total_atualizados'] = (
                resultado['intermediarios']['atualizados'] +
                resultado['acabados']['atualizados']
            )

            logger.info(f"Propagacao concluida: {resultado['total_atualizados']} produtos atualizados")

            return resultado

        except Exception as e:
            logger.error(f"Erro na propagacao de custos: {e}")
            resultado['sucesso'] = False
            resultado['erro'] = str(e)
            return resultado

    @staticmethod
    def _salvar_custo_propagado(
        cod_produto: str,
        nome_produto: str,
        tipo_produto: str,
        custo_considerado: float,
        usuario: str
    ):
        """
        Salva custo propagado via BOM (uso interno)
        """
        custo_atual = CustoConsiderado.query.filter_by(
            cod_produto=cod_produto,
            custo_atual=True
        ).first()

        if custo_atual:
            # Só atualiza se o valor mudou
            if custo_atual.custo_considerado and abs(float(custo_atual.custo_considerado) - custo_considerado) < 0.000001:
                return  # Sem alteração

            # Criar nova versão
            custo_atual.custo_atual = False
            custo_atual.vigencia_fim = datetime.utcnow()

            nova_versao = CustoConsiderado(
                cod_produto=cod_produto,
                nome_produto=nome_produto,
                tipo_produto=tipo_produto,
                versao=custo_atual.versao + 1,
                custo_atual=True,
                vigencia_inicio=datetime.utcnow(),
                motivo_alteracao='Propagacao automatica via BOM',
                tipo_custo_selecionado='BOM',
                custo_considerado=custo_considerado,
                custo_medio_mes=custo_atual.custo_medio_mes,
                ultimo_custo=custo_atual.ultimo_custo,
                custo_medio_estoque=custo_atual.custo_medio_estoque,
                atualizado_por=usuario
            )
            db.session.add(nova_versao)
        else:
            # Primeiro registro
            nova_versao = CustoConsiderado(
                cod_produto=cod_produto,
                nome_produto=nome_produto,
                tipo_produto=tipo_produto,
                versao=1,
                custo_atual=True,
                vigencia_inicio=datetime.utcnow(),
                motivo_alteracao='Propagacao automatica via BOM',
                tipo_custo_selecionado='BOM',
                custo_considerado=custo_considerado,
                atualizado_por=usuario
            )
            db.session.add(nova_versao)

        db.session.commit()
