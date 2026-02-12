"""
Serviço de Consumo Automático de Componentes na Produção

Implementa a lógica de consumo cascateado (Opção D):
- Ao registrar PRODUÇÃO, consome componentes da ListaMateriais
- Se componente é intermediário e estoque insuficiente, gera PRODUÇÃO automática
- Tudo vinculado por operacao_producao_id

Autor: Claude Code
Data: 2025-12-09
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional, Set
import logging
import random
import string

from app import db
from app.estoque.models import MovimentacaoEstoque
from app.estoque.services.estoque_simples import ServicoEstoqueSimples
from app.manufatura.models import ListaMateriais
from app.producao.models import CadastroPalletizacao
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


class ServicoConsumoProducao:
    """
    Serviço para consumo automático de componentes durante produção.

    Lógica Opção D:
    - Se estoque >= consumo: registra CONSUMO total
    - Se estoque < consumo: registra CONSUMO parcial + PRODUÇÃO automática do intermediário
    - Recursão para componentes do intermediário
    """

    # Tipos de origem para rastreabilidade
    TIPO_RAIZ = 'RAIZ'                    # Produção original (do Excel)
    TIPO_CONSUMO_DIRETO = 'CONSUMO_DIRETO'  # Consumo de componente com estoque suficiente
    TIPO_PRODUCAO_AUTO = 'PRODUCAO_AUTO'    # Produção gerada automaticamente para intermediário
    TIPO_CONSUMO_AUTO = 'CONSUMO_AUTO'      # Consumo gerado por produção automática

    @staticmethod
    def gerar_operacao_id() -> str:
        """
        Gera ID único para operação de produção.
        Formato: PROD_YYYYMMDD_HHMMSS_XXXX
        """
        agora = agora_utc_naive()
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"PROD_{agora.strftime('%Y%m%d_%H%M%S')}_{random_suffix}"

    @staticmethod
    def _buscar_componentes_bom(cod_produto: str) -> List[Dict[str, Any]]:
        """
        Busca componentes da ListaMateriais para um produto.

        Returns:
            Lista de dicts com cod_produto_componente, nome_produto_componente, qtd_utilizada
        """
        componentes = ListaMateriais.query.filter_by(
            cod_produto_produzido=cod_produto,
            status='ativo'
        ).all()

        resultado = []
        for comp in componentes:
            # Buscar nome do componente no cadastro
            cadastro = CadastroPalletizacao.query.filter_by(
                cod_produto=comp.cod_produto_componente,
                ativo=True
            ).first()

            nome = cadastro.nome_produto if cadastro else comp.nome_produto_componente or f"Produto {comp.cod_produto_componente}"

            resultado.append({
                'cod_produto': comp.cod_produto_componente,
                'nome_produto': nome,
                'qtd_utilizada': float(comp.qtd_utilizada or 0)
            })

        return resultado

    @staticmethod
    def _eh_produto_produzido(cod_produto: str) -> bool:
        """Verifica se produto tem flag produto_produzido=True"""
        cadastro = CadastroPalletizacao.query.filter_by(
            cod_produto=cod_produto,
            ativo=True
        ).first()

        return cadastro.produto_produzido if cadastro else False

    @staticmethod
    def _tem_bom(cod_produto: str) -> bool:
        """Verifica se produto tem ListaMateriais cadastrada"""
        return ListaMateriais.query.filter_by(
            cod_produto_produzido=cod_produto,
            status='ativo'
        ).first() is not None

    @staticmethod
    def processar_producao_com_consumo(
        cod_produto: str,
        qtd_produzida: float,
        data_movimentacao: date,
        nome_produto: str,
        local_movimentacao: str,
        observacao: Optional[str] = None,
        usuario: Optional[str] = None,
        operacao_id: Optional[str] = None,
        cod_produto_raiz: Optional[str] = None,
        producao_pai_id: Optional[int] = None,
        tipo_origem: Optional[str] = None,
        nivel_recursao: int = 0,
        max_nivel_recursao: int = 10,
        visitados: Optional[Set[str]] = None,
        ordem_producao: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processa produção com consumo automático de componentes.

        Implementa Opção D:
        1. Registra PRODUÇÃO do produto
        2. Para cada componente na BOM:
           - Calcula quantidade necessária
           - Verifica estoque
           - Se estoque >= necessário: registra CONSUMO
           - Se estoque < necessário:
             - Registra CONSUMO do estoque disponível
             - Se componente é produzido: gera PRODUÇÃO automática + recursão

        Args:
            cod_produto: Código do produto sendo produzido
            qtd_produzida: Quantidade produzida
            data_movimentacao: Data da movimentação
            nome_produto: Nome do produto
            local_movimentacao: Local da produção (linha de produção)
            observacao: Observação adicional
            usuario: Usuário que está importando
            operacao_id: ID da operação (None = gerar novo)
            cod_produto_raiz: Código do produto raiz (None = usar cod_produto)
            producao_pai_id: ID da produção pai (None = é raiz)
            tipo_origem: Tipo de origem (None = RAIZ)
            nivel_recursao: Nível atual de recursão
            max_nivel_recursao: Limite de níveis
            visitados: Set de produtos já visitados (proteção contra loops)

        Returns:
            {
                'sucesso': bool,
                'operacao_id': str,
                'producao_id': int,
                'consumos': [...],
                'producoes_automaticas': [...],
                'avisos': [...],
                'erro': str | None
            }
        """
        try:
            # Proteção contra loops infinitos
            if visitados is None:
                visitados = set()

            if cod_produto in visitados:
                logger.warning(f"⚠️ LOOP DETECTADO: {cod_produto} já foi processado nesta cascata!")
                return {
                    'sucesso': False,
                    'operacao_id': operacao_id,
                    'producao_id': None,
                    'consumos': [],
                    'producoes_automaticas': [],
                    'avisos': [],
                    'erro': f'Loop detectado: {cod_produto} já foi processado'
                }

            if nivel_recursao > max_nivel_recursao:
                logger.warning(f"⚠️ Limite de recursão atingido ({max_nivel_recursao})")
                return {
                    'sucesso': False,
                    'operacao_id': operacao_id,
                    'producao_id': None,
                    'consumos': [],
                    'producoes_automaticas': [],
                    'avisos': [],
                    'erro': f'Limite de recursão ({max_nivel_recursao}) atingido'
                }

            visitados.add(cod_produto)

            # Gerar operação ID se não fornecido (produção raiz)
            if operacao_id is None:
                operacao_id = ServicoConsumoProducao.gerar_operacao_id()
                cod_produto_raiz = cod_produto
                tipo_origem = ServicoConsumoProducao.TIPO_RAIZ

            # Verificar se produto tem BOM
            tem_bom = ServicoConsumoProducao._tem_bom(cod_produto)
            avisos = []

            # Ajustar observação se não tem BOM
            observacao_final = observacao or ''
            if not tem_bom:
                aviso_sem_bom = "⚠️ SEM BOM: Produção registrada sem consumo de componentes"
                avisos.append(aviso_sem_bom)
                if observacao_final:
                    observacao_final = f"{observacao_final} | {aviso_sem_bom}"
                else:
                    observacao_final = aviso_sem_bom

            # 1. REGISTRAR PRODUÇÃO (entrada de estoque)
            producao = MovimentacaoEstoque(
                cod_produto=cod_produto,
                nome_produto=nome_produto,
                data_movimentacao=data_movimentacao,
                tipo_movimentacao='PRODUÇÃO',
                local_movimentacao=local_movimentacao,
                qtd_movimentacao=Decimal(str(qtd_produzida)),
                tipo_origem='MANUAL',
                observacao=observacao_final,
                criado_por=usuario,
                # Campos de vinculação
                operacao_producao_id=operacao_id,
                tipo_origem_producao=tipo_origem,
                cod_produto_raiz=cod_produto_raiz,
                producao_pai_id=producao_pai_id,
                ordem_producao=ordem_producao,
                ativo=True
            )

            db.session.add(producao)
            db.session.flush()  # Para obter o ID

            producao_id = producao.id
            consumos = []
            producoes_automaticas = []

            # Se não tem BOM, retornar apenas a produção
            if not tem_bom:
                logger.info(f"📦 Produção {cod_produto} registrada sem BOM (operação: {operacao_id})")
                return {
                    'sucesso': True,
                    'operacao_id': operacao_id,
                    'producao_id': producao_id,
                    'consumos': [],
                    'producoes_automaticas': [],
                    'avisos': avisos,
                    'erro': None
                }

            # 2. BUSCAR COMPONENTES DA BOM
            componentes = ServicoConsumoProducao._buscar_componentes_bom(cod_produto)

            logger.info(f"📋 Processando {len(componentes)} componentes para {cod_produto}")

            # 3. PROCESSAR CADA COMPONENTE
            for comp in componentes:
                resultado_comp = ServicoConsumoProducao._processar_consumo_componente(
                    componente=comp,
                    qtd_produzida=qtd_produzida,
                    data_movimentacao=data_movimentacao,
                    local_movimentacao=local_movimentacao,
                    operacao_id=operacao_id,
                    cod_produto_raiz=cod_produto_raiz,
                    producao_pai_id=producao_id,
                    usuario=usuario,
                    nivel_recursao=nivel_recursao + 1,
                    max_nivel_recursao=max_nivel_recursao,
                    visitados=visitados.copy(),  # Cópia para cada branch
                    ordem_producao=ordem_producao
                )

                consumos.extend(resultado_comp.get('consumos', []))
                producoes_automaticas.extend(resultado_comp.get('producoes_automaticas', []))
                avisos.extend(resultado_comp.get('avisos', []))

            logger.info(
                f"✅ Produção {cod_produto} processada: "
                f"produção_id={producao_id}, "
                f"{len(consumos)} consumos, "
                f"{len(producoes_automaticas)} produções automáticas"
            )

            return {
                'sucesso': True,
                'operacao_id': operacao_id,
                'producao_id': producao_id,
                'consumos': consumos,
                'producoes_automaticas': producoes_automaticas,
                'avisos': avisos,
                'erro': None
            }

        except Exception as e:
            logger.error(f"❌ Erro ao processar produção {cod_produto}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'sucesso': False,
                'operacao_id': operacao_id,
                'producao_id': None,
                'consumos': [],
                'producoes_automaticas': [],
                'avisos': [],
                'erro': str(e)
            }

    @staticmethod
    def _processar_consumo_componente(
        componente: Dict[str, Any],
        qtd_produzida: float,
        data_movimentacao: date,
        local_movimentacao: str,
        operacao_id: str,
        cod_produto_raiz: str,
        producao_pai_id: int,
        usuario: Optional[str],
        nivel_recursao: int,
        max_nivel_recursao: int,
        visitados: Set[str],
        ordem_producao: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processa consumo de um componente específico.

        Lógica Opção D:
        1. Calcula qtd_consumo = qtd_produzida × qtd_utilizada
        2. Verifica estoque atual do componente
        3. Se estoque >= qtd_consumo:
           - Registra CONSUMO integral
        4. Se estoque < qtd_consumo:
           - Registra CONSUMO do estoque disponível
           - Se componente é produzido (intermediário):
             - Gera PRODUÇÃO automática de (qtd_consumo - estoque)
             - Recursão para consumir componentes dessa produção
        """
        try:
            cod_componente = componente['cod_produto']
            nome_componente = componente['nome_produto']
            qtd_utilizada = componente['qtd_utilizada']

            # Calcular quantidade necessária
            qtd_consumo = qtd_produzida * qtd_utilizada

            if qtd_consumo <= 0:
                return {'consumos': [], 'producoes_automaticas': [], 'avisos': []}

            # Verificar estoque atual
            estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_componente)

            consumos = []
            producoes_automaticas = []
            avisos = []

            logger.debug(
                f"  🔍 Componente {cod_componente}: "
                f"necessário={qtd_consumo:.3f}, estoque={estoque_atual:.3f}"
            )

            # Caso 1: Estoque suficiente - consumo integral
            if estoque_atual >= qtd_consumo:
                consumo = ServicoConsumoProducao._registrar_consumo(
                    cod_produto=cod_componente,
                    nome_produto=nome_componente,
                    qtd_consumo=qtd_consumo,
                    data_movimentacao=data_movimentacao,
                    local_movimentacao=local_movimentacao,
                    operacao_id=operacao_id,
                    cod_produto_raiz=cod_produto_raiz,
                    producao_pai_id=producao_pai_id,
                    tipo_origem=ServicoConsumoProducao.TIPO_CONSUMO_DIRETO,
                    usuario=usuario,
                    observacao=f"Consumo para produção de {cod_produto_raiz}",
                    ordem_producao=ordem_producao
                )
                consumos.append(consumo)

            # Caso 2: Estoque insuficiente
            else:
                qtd_consumir_estoque = estoque_atual if estoque_atual > 0 else 0
                qtd_falta = qtd_consumo - qtd_consumir_estoque

                # Consumir estoque disponível (se houver)
                if qtd_consumir_estoque > 0:
                    consumo_parcial = ServicoConsumoProducao._registrar_consumo(
                        cod_produto=cod_componente,
                        nome_produto=nome_componente,
                        qtd_consumo=qtd_consumir_estoque,
                        data_movimentacao=data_movimentacao,
                        local_movimentacao=local_movimentacao,
                        operacao_id=operacao_id,
                        cod_produto_raiz=cod_produto_raiz,
                        producao_pai_id=producao_pai_id,
                        tipo_origem=ServicoConsumoProducao.TIPO_CONSUMO_DIRETO,
                        usuario=usuario,
                        observacao=f"Consumo parcial (estoque) para produção de {cod_produto_raiz}",
                        ordem_producao=ordem_producao
                    )
                    consumos.append(consumo_parcial)

                # Verificar se componente pode ser produzido
                eh_produzido = ServicoConsumoProducao._eh_produto_produzido(cod_componente)
                tem_bom_comp = ServicoConsumoProducao._tem_bom(cod_componente)

                if eh_produzido and tem_bom_comp:
                    # Gerar PRODUÇÃO AUTOMÁTICA do intermediário
                    logger.info(
                        f"  🔄 Gerando produção automática de {cod_componente}: "
                        f"{qtd_falta:.3f} unidades"
                    )

                    resultado_producao_auto = ServicoConsumoProducao.processar_producao_com_consumo(
                        cod_produto=cod_componente,
                        qtd_produzida=qtd_falta,
                        data_movimentacao=data_movimentacao,
                        nome_produto=nome_componente,
                        local_movimentacao=local_movimentacao,
                        observacao=f"Produção automática para suprir {cod_produto_raiz}",
                        usuario=usuario,
                        operacao_id=operacao_id,
                        cod_produto_raiz=cod_produto_raiz,
                        producao_pai_id=producao_pai_id,
                        tipo_origem=ServicoConsumoProducao.TIPO_PRODUCAO_AUTO,
                        nivel_recursao=nivel_recursao,
                        max_nivel_recursao=max_nivel_recursao,
                        visitados=visitados,
                        ordem_producao=ordem_producao
                    )

                    if resultado_producao_auto['sucesso']:
                        producoes_automaticas.append({
                            'cod_produto': cod_componente,
                            'nome_produto': nome_componente,
                            'qtd_produzida': qtd_falta,
                            'producao_id': resultado_producao_auto['producao_id']
                        })

                        # Adicionar consumos e produções da recursão
                        consumos.extend(resultado_producao_auto.get('consumos', []))
                        producoes_automaticas.extend(resultado_producao_auto.get('producoes_automaticas', []))
                        avisos.extend(resultado_producao_auto.get('avisos', []))

                        # Consumir a quantidade produzida automaticamente
                        consumo_auto = ServicoConsumoProducao._registrar_consumo(
                            cod_produto=cod_componente,
                            nome_produto=nome_componente,
                            qtd_consumo=qtd_falta,
                            data_movimentacao=data_movimentacao,
                            local_movimentacao=local_movimentacao,
                            operacao_id=operacao_id,
                            cod_produto_raiz=cod_produto_raiz,
                            producao_pai_id=producao_pai_id,
                            tipo_origem=ServicoConsumoProducao.TIPO_CONSUMO_AUTO,
                            usuario=usuario,
                            observacao=f"Consumo após produção automática para {cod_produto_raiz}",
                            ordem_producao=ordem_producao
                        )
                        consumos.append(consumo_auto)
                    else:
                        aviso = f"Falha na produção automática de {cod_componente}: {resultado_producao_auto.get('erro')}"
                        avisos.append(aviso)
                        logger.warning(f"  ⚠️ {aviso}")

                else:
                    # Componente final (comprado) - consumir mesmo ficando negativo
                    if qtd_falta > 0:
                        consumo_negativo = ServicoConsumoProducao._registrar_consumo(
                            cod_produto=cod_componente,
                            nome_produto=nome_componente,
                            qtd_consumo=qtd_falta,
                            data_movimentacao=data_movimentacao,
                            local_movimentacao=local_movimentacao,
                            operacao_id=operacao_id,
                            cod_produto_raiz=cod_produto_raiz,
                            producao_pai_id=producao_pai_id,
                            tipo_origem=ServicoConsumoProducao.TIPO_CONSUMO_DIRETO,
                            usuario=usuario,
                            observacao=f"Consumo (estoque ficará negativo) para {cod_produto_raiz}",
                            ordem_producao=ordem_producao
                        )
                        consumos.append(consumo_negativo)

                        aviso = f"Componente {cod_componente} ficará com estoque negativo ({estoque_atual - qtd_consumo:.3f})"
                        avisos.append(aviso)
                        logger.warning(f"  ⚠️ {aviso}")

            return {
                'consumos': consumos,
                'producoes_automaticas': producoes_automaticas,
                'avisos': avisos
            }

        except Exception as e:
            logger.error(f"❌ Erro ao processar componente {componente.get('cod_produto')}: {e}")
            return {
                'consumos': [],
                'producoes_automaticas': [],
                'avisos': [f"Erro no componente {componente.get('cod_produto')}: {str(e)}"]
            }

    @staticmethod
    def _registrar_consumo(
        cod_produto: str,
        nome_produto: str,
        qtd_consumo: float,
        data_movimentacao: date,
        local_movimentacao: str,
        operacao_id: str,
        cod_produto_raiz: str,
        producao_pai_id: int,
        tipo_origem: str,
        usuario: Optional[str],
        observacao: Optional[str] = None,
        ordem_producao: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Registra movimentação de CONSUMO (valor negativo).

        Returns:
            Dict com id, cod_produto, qtd_consumida, tipo
        """
        consumo = MovimentacaoEstoque(
            cod_produto=cod_produto,
            nome_produto=nome_produto,
            data_movimentacao=data_movimentacao,
            tipo_movimentacao='CONSUMO',
            local_movimentacao=local_movimentacao,
            qtd_movimentacao=Decimal(str(-abs(qtd_consumo))),  # Valor NEGATIVO
            tipo_origem='MANUAL',
            observacao=observacao,
            criado_por=usuario,
            # Campos de vinculação
            operacao_producao_id=operacao_id,
            tipo_origem_producao=tipo_origem,
            cod_produto_raiz=cod_produto_raiz,
            producao_pai_id=producao_pai_id,
            ordem_producao=ordem_producao,
            ativo=True
        )

        db.session.add(consumo)
        db.session.flush()  # Para obter o ID

        logger.debug(
            f"  📤 Consumo registrado: {cod_produto} = -{qtd_consumo:.3f} "
            f"(id={consumo.id}, tipo={tipo_origem})"
        )

        return {
            'id': consumo.id,
            'cod_produto': cod_produto,
            'nome_produto': nome_produto,
            'qtd_consumida': qtd_consumo,
            'tipo': tipo_origem
        }


# Funções de conveniência para uso externo
def processar_producao(
    cod_produto: str,
    qtd_produzida: float,
    data_movimentacao: date,
    nome_produto: str,
    local_movimentacao: str,
    observacao: Optional[str] = None,
    usuario: Optional[str] = None
) -> Dict[str, Any]:
    """
    Função de conveniência para processar produção com consumo.
    Use esta função para chamadas simples.
    """
    return ServicoConsumoProducao.processar_producao_com_consumo(
        cod_produto=cod_produto,
        qtd_produzida=qtd_produzida,
        data_movimentacao=data_movimentacao,
        nome_produto=nome_produto,
        local_movimentacao=local_movimentacao,
        observacao=observacao,
        usuario=usuario
    )
