"""
Serviço de Explosão de Lista de Materiais (BOM)
Gerencia estrutura hierárquica de produtos (Acabados → Intermediários → Componentes)
"""

from typing import Dict, List, Any, Optional, Set
from datetime import date
from app.utils.timezone import agora_utc_naive  # corte "hoje" em BRT (servidor roda em UTC)
import logging

from app import db
from app.manufatura.models import ListaMateriais
from app.producao.models import CadastroPalletizacao
from app.estoque.models import UnificacaoCodigos
from app.estoque.services.estoque_simples import ServicoEstoqueSimples

logger = logging.getLogger(__name__)


class ServicoBOM:
    """
    Serviço para explosão de BOM (Bill of Materials)
    Trabalha com estrutura recursiva baseada em flags produto_produzido/produto_comprado
    SUPORTA UnificacaoCodigos para componentes substitutos
    """

    @staticmethod
    def _agrupar_componentes_unificados(componentes_bom: List) -> List[Dict[str, Any]]:
        """
        Agrupa componentes que possuem unificação de códigos

        Args:
            componentes_bom: Lista de objetos ListaMateriais

        Returns:
            Lista de dicts com componentes agrupados:
            [
                {
                    'cod_produto_unificado': str,  # Código destino da unificação
                    'codigos_relacionados': List[str],  # Todos os códigos relacionados
                    'qtd_utilizada': float,  # Soma das quantidades
                    'cod_produto_componente': str,  # Código principal (para compatibilidade)
                    'nome_produto_componente': str  # Nome do produto unificado
                }
            ]
        """
        try:
            # Dicionário para agrupar: {cod_unificado: dados_agregados}
            componentes_agrupados = {}

            for comp in componentes_bom:
                cod_comp = comp.cod_produto_componente

                # Buscar código unificado (se houver)
                cod_unificado = UnificacaoCodigos.get_codigo_unificado(cod_comp)

                # Buscar TODOS os códigos relacionados ao unificado
                codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_unificado)

                # Usar código unificado como chave de agrupamento
                if cod_unificado not in componentes_agrupados:
                    # Buscar nome do produto (preferir do cadastro do código unificado)
                    cadastro = CadastroPalletizacao.query.filter_by(
                        cod_produto=str(cod_unificado),
                        ativo=True
                    ).first()

                    nome_produto = (
                        cadastro.nome_produto if cadastro
                        else comp.nome_produto_componente or f"Produto {cod_unificado}"
                    )

                    componentes_agrupados[cod_unificado] = {
                        'cod_produto_unificado': str(cod_unificado),
                        'codigos_relacionados': codigos_relacionados,
                        'qtd_utilizada': 0,
                        'cod_produto_componente': str(cod_unificado),  # Para compatibilidade
                        'nome_produto_componente': nome_produto
                    }

                # Somar quantidade utilizada
                componentes_agrupados[cod_unificado]['qtd_utilizada'] += float(comp.qtd_utilizada or 0)

            resultado = list(componentes_agrupados.values())

            # Log se houve agrupamento
            if len(resultado) < len(componentes_bom):
                logger.info(
                    f"🔗 Unificação BOM: {len(componentes_bom)} componentes "
                    f"→ {len(resultado)} componentes únicos"
                )

            return resultado

        except Exception as e:
            logger.error(f"Erro ao agrupar componentes unificados: {e}")
            # Em caso de erro, retornar componentes sem agrupamento
            return [
                {
                    'cod_produto_unificado': comp.cod_produto_componente,
                    'codigos_relacionados': [comp.cod_produto_componente],
                    'qtd_utilizada': float(comp.qtd_utilizada or 0),
                    'cod_produto_componente': comp.cod_produto_componente,
                    'nome_produto_componente': comp.nome_produto_componente or f"Produto {comp.cod_produto_componente}"
                }
                for comp in componentes_bom
            ]

    @staticmethod
    def _classificar_produto(cod_produto: str) -> Dict[str, Any]:
        """
        Classifica produto com base nas flags de CadastroPalletizacao

        Returns:
            {
                'tipo': 'ACABADO' | 'INTERMEDIARIO' | 'COMPONENTE' | 'DESCONHECIDO',
                'produto_produzido': bool,
                'produto_comprado': bool,
                'produto_vendido': bool,
                'dados': CadastroPalletizacao | None
            }
        """
        try:
            cadastro = CadastroPalletizacao.query.filter_by(
                cod_produto=cod_produto,
                ativo=True
            ).first()

            if not cadastro:
                logger.warning(f"Produto {cod_produto} não encontrado em CadastroPalletizacao")
                return {
                    'tipo': 'DESCONHECIDO',
                    'produto_produzido': False,
                    'produto_comprado': False,
                    'produto_vendido': False,
                    'dados': None
                }

            # Classificação baseada nas flags
            if cadastro.produto_produzido and cadastro.produto_vendido:
                tipo = 'ACABADO'
            elif cadastro.produto_produzido and not cadastro.produto_vendido:
                tipo = 'INTERMEDIARIO'
            elif cadastro.produto_comprado:
                tipo = 'COMPONENTE'
            else:
                tipo = 'DESCONHECIDO'

            return {
                'tipo': tipo,
                'produto_produzido': cadastro.produto_produzido,
                'produto_comprado': cadastro.produto_comprado,
                'produto_vendido': cadastro.produto_vendido,
                'dados': cadastro
            }

        except Exception as e:
            logger.error(f"Erro ao classificar produto {cod_produto}: {e}")
            return {
                'tipo': 'DESCONHECIDO',
                'produto_produzido': False,
                'produto_comprado': False,
                'produto_vendido': False,
                'dados': None
            }

    @staticmethod
    def explodir_bom(
        cod_produto: str,
        qtd_necessaria: float,
        nivel_atual: int = 0,
        max_nivel: int = 10,
        visitados: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Explode BOM recursivamente até encontrar componentes comprados

        Args:
            cod_produto: Código do produto a explodir
            qtd_necessaria: Quantidade necessária do produto
            nivel_atual: Nível atual da recursão (0 = raiz)
            max_nivel: Limite de níveis de recursão (proteção contra loops)
            visitados: Set de códigos já visitados (proteção contra loops)

        Returns:
            {
                'cod_produto': str,
                'nome_produto': str,
                'qtd_necessaria': float,
                'tipo': 'ACABADO' | 'INTERMEDIARIO' | 'COMPONENTE',
                'nivel': int,
                'componentes': List[Dict],  # Recursivo
                'tem_estrutura': bool,
                'erro': str | None
            }
        """
        try:
            # Proteção contra loops infinitos
            if visitados is None:
                visitados = set()

            if cod_produto in visitados:
                logger.warning(f"⚠️ LOOP DETECTADO: {cod_produto} já foi visitado!")
                return {
                    'cod_produto': cod_produto,
                    'nome_produto': 'ERRO: Loop na estrutura',
                    'qtd_necessaria': qtd_necessaria,
                    'tipo': 'ERRO',
                    'nivel': nivel_atual,
                    'componentes': [],
                    'tem_estrutura': False,
                    'erro': 'Loop infinito detectado na estrutura BOM'
                }

            if nivel_atual > max_nivel:
                logger.warning(f"⚠️ Limite de níveis atingido ({max_nivel}) para {cod_produto}")
                return {
                    'cod_produto': cod_produto,
                    'nome_produto': 'ERRO: Estrutura muito profunda',
                    'qtd_necessaria': qtd_necessaria,
                    'tipo': 'ERRO',
                    'nivel': nivel_atual,
                    'componentes': [],
                    'tem_estrutura': False,
                    'erro': f'Estrutura excede {max_nivel} níveis'
                }

            # Adicionar à lista de visitados
            visitados.add(cod_produto)

            # Classificar produto
            classificacao = ServicoBOM._classificar_produto(cod_produto)

            if not classificacao['dados']:
                return {
                    'cod_produto': cod_produto,
                    'nome_produto': f'Produto {cod_produto} não cadastrado',
                    'qtd_necessaria': qtd_necessaria,
                    'tipo': 'DESCONHECIDO',
                    'nivel': nivel_atual,
                    'componentes': [],
                    'tem_estrutura': False,
                    'erro': 'Produto não encontrado em CadastroPalletizacao'
                }

            produto_dados = classificacao['dados']

            # Buscar componentes na ListaMateriais
            componentes_bom = ListaMateriais.query.filter_by(
                cod_produto_produzido=cod_produto,
                status='ativo'
            ).all()

            resultado_componentes = []

            # Se tem componentes, AGRUPAR UNIFICADOS e explodir recursivamente
            if componentes_bom:
                # 🔗 AGRUPAR componentes com códigos unificados
                componentes_agrupados = ServicoBOM._agrupar_componentes_unificados(componentes_bom)

                for comp in componentes_agrupados:
                    qtd_comp_necessaria = qtd_necessaria * float(comp['qtd_utilizada'])

                    # 🔁 RECURSÃO: Explodir componente (usar código unificado)
                    comp_explodido = ServicoBOM.explodir_bom(
                        cod_produto=comp['cod_produto_componente'],
                        qtd_necessaria=qtd_comp_necessaria,
                        nivel_atual=nivel_atual + 1,
                        max_nivel=max_nivel,
                        visitados=visitados.copy()  # Criar cópia para cada branch
                    )

                    # Adicionar informações de unificação ao resultado
                    comp_explodido['codigos_relacionados'] = comp['codigos_relacionados']
                    comp_explodido['eh_unificado'] = len(comp['codigos_relacionados']) > 1

                    resultado_componentes.append(comp_explodido)

            return {
                'cod_produto': cod_produto,
                'nome_produto': produto_dados.nome_produto,
                'qtd_necessaria': qtd_necessaria,
                'tipo': classificacao['tipo'],
                'nivel': nivel_atual,
                'componentes': resultado_componentes,
                'tem_estrutura': len(resultado_componentes) > 0,
                'produto_produzido': classificacao['produto_produzido'],
                'produto_comprado': classificacao['produto_comprado'],
                'produto_vendido': classificacao['produto_vendido'],
                'erro': None
            }

        except Exception as e:
            logger.error(f"Erro ao explodir BOM para {cod_produto}: {e}")
            return {
                'cod_produto': cod_produto,
                'nome_produto': f'Erro ao processar {cod_produto}',
                'qtd_necessaria': qtd_necessaria,
                'tipo': 'ERRO',
                'nivel': nivel_atual,
                'componentes': [],
                'tem_estrutura': False,
                'erro': str(e)
            }

    @staticmethod
    def calcular_necessidade_liquida(
        cod_produto: str,
        qtd_necessaria: float,
        data_necessidade: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Calcula necessidade líquida considerando estoque atual

        Args:
            cod_produto: Código do produto
            qtd_necessaria: Quantidade bruta necessária
            data_necessidade: Data em que o produto será necessário (default: hoje)

        Returns:
            {
                'cod_produto': str,
                'nome_produto': str,
                'qtd_necessaria': float,  # Quantidade bruta
                'estoque_atual': float,
                'estoque_projetado': float,  # Estoque na data_necessidade
                'qtd_falta': float,  # Necessidade líquida (0 se tiver estoque)
                'necessita_programacao': bool,
                'data_necessidade': str
            }
        """
        try:
            if data_necessidade is None:
                data_necessidade = agora_utc_naive().date()

            # Buscar dados do produto
            cadastro = CadastroPalletizacao.query.filter_by(
                cod_produto=cod_produto,
                ativo=True
            ).first()

            nome_produto = cadastro.nome_produto if cadastro else f"Produto {cod_produto}"

            # Calcular estoque atual
            estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)

            # Calcular estoque projetado na data
            if data_necessidade == agora_utc_naive().date():
                estoque_projetado = estoque_atual
            else:
                dias = (data_necessidade - agora_utc_naive().date()).days
                projecao = ServicoEstoqueSimples.calcular_projecao(cod_produto, dias)

                # Buscar estoque na data específica
                estoque_projetado = estoque_atual
                for dia_proj in projecao.get('projecao', []):
                    if dia_proj.get('data') == data_necessidade.isoformat():
                        estoque_projetado = dia_proj.get('saldo_final', estoque_atual)
                        break

            # Calcular falta
            qtd_falta = max(0, qtd_necessaria - estoque_projetado)

            return {
                'cod_produto': cod_produto,
                'nome_produto': nome_produto,
                'qtd_necessaria': qtd_necessaria,
                'estoque_atual': estoque_atual,
                'estoque_projetado': estoque_projetado,
                'qtd_falta': qtd_falta,
                'necessita_programacao': qtd_falta > 0,
                'data_necessidade': data_necessidade.isoformat()
            }

        except Exception as e:
            logger.error(f"Erro ao calcular necessidade líquida para {cod_produto}: {e}")
            return {
                'cod_produto': cod_produto,
                'nome_produto': f"Produto {cod_produto}",
                'qtd_necessaria': qtd_necessaria,
                'estoque_atual': 0,
                'estoque_projetado': 0,
                'qtd_falta': qtd_necessaria,
                'necessita_programacao': True,
                'data_necessidade': data_necessidade.isoformat() if data_necessidade else agora_utc_naive().date().isoformat(),
                'erro': str(e)
            }

    @staticmethod
    def sugerir_programacao_intermediarios(
        cod_produto: str,
        qtd_necessaria: float,
        data_necessidade: Optional[date] = None,
        incluir_componentes_completos: bool = False
    ) -> Dict[str, Any]:
        """
        Sugere programação de produtos intermediários necessários para produzir um produto

        Args:
            cod_produto: Código do produto acabado ou intermediário
            qtd_necessaria: Quantidade necessária do produto
            data_necessidade: Data em que o produto será necessário
            incluir_componentes_completos: Se True, inclui análise completa até componentes comprados

        Returns:
            {
                'produto_principal': Dict,  # Dados do produto solicitado
                'estrutura_completa': Dict,  # BOM explodido
                'intermediarios_necessarios': List[Dict],  # Intermediários que precisam programação
                'componentes_necessarios': List[Dict],  # Componentes comprados que faltam
                'viabilidade': {
                    'pode_produzir': bool,
                    'bloqueios': List[str],
                    'percentual_disponibilidade': float
                }
            }
        """
        try:
            if data_necessidade is None:
                data_necessidade = agora_utc_naive().date()

            # 1. Explodir BOM completo
            bom_explodido = ServicoBOM.explodir_bom(cod_produto, qtd_necessaria)

            # 2. Calcular necessidade líquida do produto principal
            necessidade_principal = ServicoBOM.calcular_necessidade_liquida(
                cod_produto, qtd_necessaria, data_necessidade
            )

            # 3. Analisar intermediários e componentes recursivamente
            intermediarios_necessarios = []
            componentes_necessarios = []

            def analisar_componentes(componente_info: Dict, data_ref: date):
                """Analisa recursivamente componentes para identificar necessidades"""
                componentes = componente_info.get('componentes', [])

                for comp in componentes:
                    # Calcular necessidade líquida
                    necessidade = ServicoBOM.calcular_necessidade_liquida(
                        comp['cod_produto'],
                        comp['qtd_necessaria'],
                        data_ref
                    )

                    # Se é INTERMEDIÁRIO e falta
                    if comp['tipo'] == 'INTERMEDIARIO' and necessidade['qtd_falta'] > 0:
                        intermediarios_necessarios.append({
                            **comp,
                            'necessidade_liquida': necessidade
                        })

                    # Se é COMPONENTE COMPRADO e falta (apenas se solicitado)
                    elif comp['tipo'] == 'COMPONENTE' and necessidade['qtd_falta'] > 0:
                        if incluir_componentes_completos:
                            componentes_necessarios.append({
                                **comp,
                                'necessidade_liquida': necessidade
                            })

                    # Recursão para sub-componentes
                    if comp.get('tem_estrutura'):
                        analisar_componentes(comp, data_ref)

            # Executar análise
            analisar_componentes(bom_explodido, data_necessidade)

            # 4. Calcular viabilidade
            total_itens = len(intermediarios_necessarios) + len(componentes_necessarios)
            itens_disponiveis = 0
            bloqueios = []

            # Verificar intermediários
            for inter in intermediarios_necessarios:
                if inter['necessidade_liquida']['qtd_falta'] > 0:
                    bloqueios.append(
                        f"{inter['nome_produto']} ({inter['cod_produto']}): "
                        f"falta {inter['necessidade_liquida']['qtd_falta']:.2f} unidades"
                    )
                else:
                    itens_disponiveis += 1

            # Verificar componentes (se incluídos)
            if incluir_componentes_completos:
                for comp in componentes_necessarios:
                    if comp['necessidade_liquida']['qtd_falta'] > 0:
                        bloqueios.append(
                            f"{comp['nome_produto']} ({comp['cod_produto']}): "
                            f"falta {comp['necessidade_liquida']['qtd_falta']:.2f} unidades"
                        )
                    else:
                        itens_disponiveis += 1

            percentual_disponibilidade = (
                (itens_disponiveis / total_itens * 100) if total_itens > 0 else 100
            )
            pode_produzir = len(bloqueios) == 0

            return {
                'produto_principal': {
                    'cod_produto': cod_produto,
                    'nome_produto': bom_explodido['nome_produto'],
                    'qtd_necessaria': qtd_necessaria,
                    'tipo': bom_explodido['tipo'],
                    'necessidade_liquida': necessidade_principal
                },
                'estrutura_completa': bom_explodido,
                'intermediarios_necessarios': intermediarios_necessarios,
                'componentes_necessarios': componentes_necessarios if incluir_componentes_completos else [],
                'viabilidade': {
                    'pode_produzir': pode_produzir,
                    'bloqueios': bloqueios,
                    'percentual_disponibilidade': round(percentual_disponibilidade, 2),
                    'total_itens_analisados': total_itens,
                    'itens_disponiveis': itens_disponiveis
                }
            }

        except Exception as e:
            logger.error(f"Erro ao sugerir programação de intermediários para {cod_produto}: {e}")
            return {
                'produto_principal': {
                    'cod_produto': cod_produto,
                    'qtd_necessaria': qtd_necessaria,
                    'erro': str(e)
                },
                'estrutura_completa': {},
                'intermediarios_necessarios': [],
                'componentes_necessarios': [],
                'viabilidade': {
                    'pode_produzir': False,
                    'bloqueios': [f"Erro ao analisar: {str(e)}"],
                    'percentual_disponibilidade': 0,
                    'total_itens_analisados': 0,
                    'itens_disponiveis': 0
                }
            }

    @staticmethod
    def validar_hierarquia_bom(cod_produto: str) -> Dict[str, Any]:
        """
        Valida hierarquia BOM para detectar problemas (loops, inconsistências)

        Returns:
            {
                'valido': bool,
                'erros': List[str],
                'avisos': List[str],
                'estrutura_valida': bool
            }
        """
        try:
            erros = []
            avisos = []

            # Tentar explodir BOM
            bom = ServicoBOM.explodir_bom(cod_produto, 1.0)

            # Verificar se houve erros na explosão
            if bom.get('erro'):
                erros.append(f"Erro na explosão BOM: {bom['erro']}")

            # Verificar componentes recursivamente
            def validar_componentes(comp_info: Dict, caminho: List[str]):
                componentes = comp_info.get('componentes', [])
                caminho_atual = caminho + [comp_info['cod_produto']]

                for comp in componentes:
                    # Detectar loop
                    if comp['cod_produto'] in caminho_atual:
                        erros.append(
                            f"Loop detectado: {' → '.join(caminho_atual)} → {comp['cod_produto']}"
                        )

                    # Validar tipo
                    if comp['tipo'] == 'DESCONHECIDO':
                        avisos.append(
                            f"Produto {comp['cod_produto']} não está classificado corretamente"
                        )

                    # Recursão
                    if comp.get('tem_estrutura'):
                        validar_componentes(comp, caminho_atual)

            validar_componentes(bom, [])

            return {
                'valido': len(erros) == 0,
                'erros': erros,
                'avisos': avisos,
                'estrutura_valida': bom.get('tem_estrutura', False)
            }

        except Exception as e:
            logger.error(f"Erro ao validar hierarquia BOM para {cod_produto}: {e}")
            return {
                'valido': False,
                'erros': [str(e)],
                'avisos': [],
                'estrutura_valida': False
            }
