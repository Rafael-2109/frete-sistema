"""
Service para cálculo de Necessidade de Produção
Implementa a lógica de negócio conforme escopo.md item 2
"""
import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional
from sqlalchemy import func, extract
from app import db
from app.manufatura.models import PrevisaoDemanda
from app.carteira.models import CarteiraPrincipal
from app.producao.models import ProgramacaoProducao, CadastroPalletizacao
from app.estoque.models import UnificacaoCodigos
from app.estoque.services.estoque_simples import ServicoEstoqueSimples
from app.separacao.models import Separacao

logger = logging.getLogger(__name__)


class NecessidadeProducaoService:
    """
    Service para cálculo da necessidade de produção por produto.
    Considera unificação de códigos para não duplicar resultados.
    """

    def __init__(self):
        self.estoque_service = ServicoEstoqueSimples()

    def calcular_necessidade_producao(
        self,
        mes: int,
        ano: int,
        cod_produto: Optional[str] = None,
        linha_producao: Optional[str] = None,
        marca: Optional[str] = None,
        mp: Optional[str] = None,
        embalagem: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Calcula necessidade de produção para produtos.

        Fórmula:
        1. previsao_vendas = SUM(PrevisaoDemanda.qtd_demanda_prevista) [todos grupos]
        2. pedidos_inseridos = SUM(CarteiraPrincipal.qtd_produto_pedido - qtd_cancelada) [do mês]
        3. carteira_pedidos = SUM(CarteiraPrincipal.qtd_saldo_produto_pedido) [todos]
        4. IF previsao_vendas > pedidos_inseridos:
               saldo_vendas = previsao_vendas - pedidos_inseridos + carteira_pedidos
           ELSE:
               saldo_vendas = carteira_pedidos
        5. necessidade_producao = saldo_vendas - estoque - programacao
        6. IF necessidade_producao <= 0: necessidade_producao = 0

        Args:
            mes: Mês de referência
            ano: Ano de referência
            cod_produto: Código específico (opcional)

        Returns:
            Lista de dicionários com dados calculados por produto
        """
        try:
            logger.info(f"[NECESSIDADE] Calculando para {mes}/{ano}, produto={cod_produto}, linha={linha_producao}, marca={marca}, mp={mp}, embalagem={embalagem}")

            # 1. Obter todos os produtos únicos (considerando unificação e filtros)
            produtos_unificados = self._obter_produtos_unificados(
                mes, ano, cod_produto, linha_producao, marca, mp, embalagem
            )

            logger.info(f"[NECESSIDADE] Encontrados {len(produtos_unificados)} produtos únicos após unificação")

            # 2. Calcular necessidade para cada produto unificado
            resultados = []
            for produto_info in produtos_unificados:
                cod_unificado = produto_info['cod_produto']
                nome_produto = produto_info['nome_produto']
                codigos_relacionados = produto_info['codigos_relacionados']

                logger.debug(f"[NECESSIDADE] Calculando {cod_unificado} (códigos: {codigos_relacionados})")

                # Cálculos agregados para todos os códigos relacionados
                previsao_vendas = self._calcular_previsao_vendas(
                    codigos_relacionados, mes, ano
                )

                pedidos_inseridos = self._calcular_pedidos_inseridos(
                    codigos_relacionados, mes, ano
                )

                carteira_pedidos = self._calcular_carteira_pedidos(
                    codigos_relacionados
                )

                estoque_atual = self._calcular_estoque(cod_unificado)

                programacao_producao = self._calcular_programacao(
                    codigos_relacionados, mes, ano
                )

                # ✅ NOVOS CÁLCULOS
                carteira_sem_data = self._calcular_carteira_sem_data(
                    codigos_relacionados
                )

                saldo_demanda = previsao_vendas - pedidos_inseridos

                # Aplicar fórmula de saldo de vendas
                if previsao_vendas > pedidos_inseridos:
                    saldo_vendas = previsao_vendas - pedidos_inseridos + carteira_pedidos
                else:
                    saldo_vendas = carteira_pedidos

                # Calcular necessidade de produção
                necessidade_producao = saldo_vendas - estoque_atual - programacao_producao

                # Se negativo ou zero, zerar
                if necessidade_producao < 0:
                    necessidade_producao = 0

                # Calcular Ruptura Carteira
                ruptura_carteira = estoque_atual - carteira_pedidos

                resultados.append({
                    'cod_produto': cod_unificado,
                    'nome_produto': nome_produto,
                    'codigos_relacionados': codigos_relacionados,
                    'previsao_vendas': float(previsao_vendas),
                    'pedidos_inseridos': float(pedidos_inseridos),
                    'saldo_demanda': float(saldo_demanda),  # ✅ NOVO
                    'carteira_pedidos': float(carteira_pedidos),
                    'ruptura_carteira': float(ruptura_carteira),  # ✅ NOVO
                    'carteira_sem_data': float(carteira_sem_data),  # ✅ NOVO
                    'saldo_vendas': float(saldo_vendas),
                    'estoque_atual': float(estoque_atual),
                    'programacao_producao': float(programacao_producao),
                    'necessidade_producao': float(necessidade_producao),
                    'mes': mes,
                    'ano': ano,
                    # ✅ CAMPOS ADICIONAIS para UI
                    'tipo_embalagem': produto_info.get('tipo_embalagem'),
                    'tipo_materia_prima': produto_info.get('tipo_materia_prima'),
                    'categoria_produto': produto_info.get('categoria_produto'),
                    'linha_producao': produto_info.get('linha_producao')
                })

            logger.info(f"[NECESSIDADE] Calculado para {len(resultados)} produtos")
            return resultados

        except Exception as e:
            logger.error(f"[NECESSIDADE] Erro ao calcular: {str(e)}", exc_info=True)
            raise

    def _obter_produtos_unificados(
        self,
        mes: int,
        ano: int,
        cod_produto: Optional[str] = None,
        linha_producao: Optional[str] = None,
        marca: Optional[str] = None,
        mp: Optional[str] = None,
        embalagem: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtém lista de TODOS os produtos produzidos (produto_produzido=True).
        Aplica filtros adicionais de linha, marca, MP e embalagem.
        """
        try:
            # ✅ Buscar produtos com produto_produzido=True e aplicar filtros
            query = db.session.query(
                CadastroPalletizacao.cod_produto
            ).filter(
                CadastroPalletizacao.ativo == True,
                CadastroPalletizacao.produto_produzido == True
            )

            # Filtro por produto específico
            if cod_produto:
                codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
                query = query.filter(CadastroPalletizacao.cod_produto.in_(codigos_relacionados))

            # ✅ NOVOS FILTROS
            if linha_producao:
                query = query.filter(CadastroPalletizacao.linha_producao == linha_producao)
            if marca:
                query = query.filter(CadastroPalletizacao.categoria_produto == marca)
            if mp:
                query = query.filter(CadastroPalletizacao.tipo_materia_prima == mp)
            if embalagem:
                query = query.filter(CadastroPalletizacao.tipo_embalagem == embalagem)

            produtos = query.distinct().all()

            # Mapear produtos para códigos unificados
            produtos_map = {}
            for (cod,) in produtos:
                cod_unificado = UnificacaoCodigos.get_codigo_unificado(cod)
                cod_unificado_str = str(cod_unificado)

                if cod_unificado_str not in produtos_map:
                    # Obter todos os códigos relacionados ao código unificado
                    codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_unificado)

                    # Buscar dados do produto no cadastro (já sabemos que existe e produto_produzido=True)
                    cadastro = CadastroPalletizacao.query.filter_by(
                        cod_produto=cod_unificado_str
                    ).first()

                    # Por segurança, verificar se encontrou
                    if not cadastro:
                        logger.warning(f"[NECESSIDADE] Produto {cod_unificado_str} não encontrado no cadastro (não deveria acontecer)")
                        continue

                    produtos_map[cod_unificado_str] = {
                        'cod_produto': cod_unificado_str,
                        'nome_produto': cadastro.nome_produto,
                        'codigos_relacionados': codigos_relacionados,
                        'tipo_embalagem': cadastro.tipo_embalagem,
                        'tipo_materia_prima': cadastro.tipo_materia_prima,
                        'categoria_produto': cadastro.categoria_produto,
                        'linha_producao': cadastro.linha_producao
                    }

            logger.info(f"[NECESSIDADE] Total de produtos produzidos encontrados: {len(produtos_map)}")
            return list(produtos_map.values())

        except Exception as e:
            logger.error(f"[NECESSIDADE] Erro ao obter produtos unificados: {str(e)}")
            raise

    def _calcular_previsao_vendas(
        self,
        codigos_relacionados: List[str],
        mes: int,
        ano: int
    ) -> float:
        """
        Calcula previsão de vendas somando TODOS os grupos.
        Considera todos os códigos relacionados (unificados).
        """
        try:
            resultado = db.session.query(
                func.sum(PrevisaoDemanda.qtd_demanda_prevista).label('total')
            ).filter(
                PrevisaoDemanda.data_mes == mes,
                PrevisaoDemanda.data_ano == ano,
                PrevisaoDemanda.cod_produto.in_(codigos_relacionados)
            ).scalar()

            return float(resultado or 0)

        except Exception as e:
            logger.error(f"[NECESSIDADE] Erro ao calcular previsão vendas: {str(e)}")
            return 0

    def _calcular_pedidos_inseridos(
        self,
        codigos_relacionados: List[str],
        mes: int,
        ano: int
    ) -> float:
        """
        Calcula pedidos inseridos no mês (faturados ou não).
        SUM(qtd_produto_pedido - qtd_cancelada) do mês.

        🚀 OTIMIZADO: Usa range de datas em vez de extract() para usar índices
        """
        try:
            from calendar import monthrange

            # Calcular primeiro e último dia do mês
            primeiro_dia = date(ano, mes, 1)
            ultimo_dia_num = monthrange(ano, mes)[1]
            ultimo_dia = date(ano, mes, ultimo_dia_num)

            resultado = db.session.query(
                func.sum(
                    CarteiraPrincipal.qtd_produto_pedido -
                    CarteiraPrincipal.qtd_cancelada_produto_pedido
                ).label('total')
            ).filter(
                CarteiraPrincipal.data_pedido >= primeiro_dia,
                CarteiraPrincipal.data_pedido <= ultimo_dia,
                CarteiraPrincipal.cod_produto.in_(codigos_relacionados)
            ).scalar()

            return float(resultado or 0)

        except Exception as e:
            logger.error(f"[NECESSIDADE] Erro ao calcular pedidos inseridos: {str(e)}")
            return 0

    def _calcular_carteira_pedidos(self, codigos_relacionados: List[str]) -> float:
        """
        Calcula saldo pendente da carteira (independente do mês).
        SUM(qtd_saldo_produto_pedido) WHERE qtd_saldo_produto_pedido > 0.
        """
        try:
            resultado = db.session.query(
                func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('total')
            ).filter(
                CarteiraPrincipal.cod_produto.in_(codigos_relacionados),
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0  # ✅ Filtrar apenas saldo positivo
            ).scalar()

            return float(resultado or 0)

        except Exception as e:
            logger.error(f"[NECESSIDADE] Erro ao calcular carteira pedidos: {str(e)}")
            return 0

    def _calcular_carteira_sem_data(self, codigos_relacionados: List[str]) -> float:
        """
        Calcula saldo da carteira SEM separação (Carteira s/ Data).
        Fórmula: SUM(CarteiraPrincipal.qtd_saldo_produto_pedido) - SUM(Separacao.qtd_saldo WHERE sincronizado_nf=False)
        """
        try:
            # Total da carteira (apenas saldo positivo)
            total_carteira = db.session.query(
                func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('total')
            ).filter(
                CarteiraPrincipal.cod_produto.in_(codigos_relacionados),
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0  # ✅ Filtrar apenas saldo positivo
            ).scalar()

            # Total separado (não sincronizado)
            total_separado = db.session.query(
                func.sum(Separacao.qtd_saldo).label('total')
            ).filter(
                Separacao.cod_produto.in_(codigos_relacionados),
                Separacao.sincronizado_nf == False
            ).scalar()

            carteira = float(total_carteira or 0)
            separado = float(total_separado or 0)

            return carteira - separado

        except Exception as e:
            logger.error(f"[NECESSIDADE] Erro ao calcular carteira sem data: {str(e)}")
            return 0

    def _calcular_estoque(self, cod_produto: str) -> float:
        """
        Calcula estoque atual usando ServicoEstoqueSimples.
        O serviço já considera unificação de códigos internamente.
        """
        try:
            return self.estoque_service.calcular_estoque_atual(cod_produto)
        except Exception as e:
            logger.error(f"[NECESSIDADE] Erro ao calcular estoque: {str(e)}")
            return 0

    def _calcular_programacao(
        self,
        codigos_relacionados: List[str],
        mes: int,
        ano: int
    ) -> float:
        """
        Calcula programação de produção do mês especificado.
        Considera apenas programações:
        - Do mês/ano especificado
        - Com data >= hoje (futuras)

        SUM(ProgramacaoProducao.qtd_programada).

        🚀 OTIMIZADO: Usa range de datas em vez de extract() para usar índices
        """
        try:
            from calendar import monthrange

            hoje = date.today()

            # Calcular primeiro e último dia do mês
            primeiro_dia = date(ano, mes, 1)
            ultimo_dia_num = monthrange(ano, mes)[1]
            ultimo_dia = date(ano, mes, ultimo_dia_num)

            # ✅ Garantir que primeiro_dia >= hoje para apenas programações futuras
            data_inicio = max(primeiro_dia, hoje)

            resultado = db.session.query(
                func.sum(ProgramacaoProducao.qtd_programada).label('total')
            ).filter(
                ProgramacaoProducao.cod_produto.in_(codigos_relacionados),
                ProgramacaoProducao.data_programacao >= data_inicio,
                ProgramacaoProducao.data_programacao <= ultimo_dia
            ).scalar()

            return float(resultado or 0)

        except Exception as e:
            logger.error(f"[NECESSIDADE] Erro ao calcular programação: {str(e)}", exc_info=True)
            return 0

    def calcular_projecao_estoque(self, cod_produto: str, dias: int = 60) -> Dict[str, Any]:
        """
        Calcula projeção de estoque D0-D60 usando ServicoEstoqueSimples.
        O serviço já considera unificação de códigos internamente.
        """
        try:
            logger.info(f"[PROJECAO] Calculando projeção {dias} dias para {cod_produto}")

            projecao = self.estoque_service.calcular_projecao(cod_produto, dias=dias)

            return projecao

        except Exception as e:
            logger.error(f"[PROJECAO] Erro ao calcular projeção: {str(e)}")
            raise

    def programar_producao(
        self,
        cod_produto: str,
        quantidade: float,
        data_programada: Optional[str] = None,
        usuario: str = 'Sistema'
    ) -> Dict[str, Any]:
        """
        Programa produção criando registro em ProgramacaoProducao.

        Args:
            cod_produto: Código do produto
            quantidade: Quantidade a programar
            data_programada: Data da programação (opcional, padrão=hoje)
            usuario: Usuário que programou

        Returns:
            Resultado da operação
        """
        try:
            logger.info(f"[PROGRAMAR] Programando {quantidade} de {cod_produto}")

            # Obter nome do produto
            produto_info = db.session.query(
                PrevisaoDemanda.nome_produto
            ).filter(
                PrevisaoDemanda.cod_produto == cod_produto
            ).first()

            nome_produto = produto_info[0] if produto_info else f"Produto {cod_produto}"

            # Data de programação
            if data_programada:
                data_prog = datetime.strptime(data_programada, '%Y-%m-%d').date()
            else:
                data_prog = date.today()

            # Criar programação
            programacao = ProgramacaoProducao(
                data_programacao=data_prog,
                cod_produto=cod_produto,
                nome_produto=nome_produto,
                qtd_programada=quantidade,
                created_by=usuario
            )

            db.session.add(programacao)
            db.session.commit()

            logger.info(f"[PROGRAMAR] Programação criada com sucesso ID={programacao.id}")

            return {
                'sucesso': True,
                'mensagem': f'Programação criada: {quantidade} unidades para {data_prog.strftime("%d/%m/%Y")}',
                'id': programacao.id,
                'cod_produto': cod_produto,
                'quantidade': float(quantidade),
                'data_programada': data_prog.isoformat()
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"[PROGRAMAR] Erro ao programar: {str(e)}", exc_info=True)
            raise
