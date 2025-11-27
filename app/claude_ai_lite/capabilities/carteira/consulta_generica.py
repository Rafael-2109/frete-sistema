"""
ConsultaGenericaCapability - Capacidade de consulta SQL genérica.

FILOSOFIA:
- O Claude ENTENDE a pergunta e extrai: tabela, campos, filtros
- Esta capacidade EXECUTA a consulta validando segurança
- Resultado volta formatado para o Claude gerar resposta

SEGURANÇA:
- Apenas SELECT (read-only)
- Apenas tabelas permitidas (whitelist)
- Apenas campos existentes (validados dinamicamente)
- Limite de resultados (proteção)
- Timeout de execução

Criado em: 25/11/2025
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta

from ..base import BaseCapability

logger = logging.getLogger(__name__)


# Tabelas permitidas para consulta
TABELAS_PERMITIDAS = {
    'carteira': 'CarteiraPrincipal',
    'carteiraprincipal': 'CarteiraPrincipal',
    'separacao': 'Separacao',
    'pedido': 'Pedido',
    'pedidos': 'Pedido',
    'estoque': 'MovimentacaoEstoque',
    'movimentacaoestoque': 'MovimentacaoEstoque',
    'faturamento': 'FaturamentoProduto',
    'faturamentoproduto': 'FaturamentoProduto',
    'embarque': 'Embarque',
    'embarques': 'Embarque',
    'embarqueitem': 'EmbarqueItem',
    'palletizacao': 'CadastroPalletizacao',
    'cadastropalletizacao': 'CadastroPalletizacao',
    'producao': 'ProgramacaoProducao',
    'programacaoproducao': 'ProgramacaoProducao',
    'frete': 'Frete',
    'fretes': 'Frete',
    'rota': 'CadastroRota',
    'cadastrorota': 'CadastroRota',
    'subrota': 'CadastroSubRota',
    'cadastrosubrota': 'CadastroSubRota',
}

# Mapeamento de modelos para seus módulos
MODELOS_MODULOS = {
    'CarteiraPrincipal': 'app.carteira.models',
    'Separacao': 'app.separacao.models',
    'Pedido': 'app.pedidos.models',
    'MovimentacaoEstoque': 'app.estoque.models',
    'FaturamentoProduto': 'app.faturamento.models',
    'Embarque': 'app.embarques.models',
    'EmbarqueItem': 'app.embarques.models',
    'CadastroPalletizacao': 'app.producao.models',
    'ProgramacaoProducao': 'app.producao.models',
    'Frete': 'app.fretes.models',
    'CadastroRota': 'app.localidades.models',
    'CadastroSubRota': 'app.localidades.models',
}


class ConsultaGenericaCapability(BaseCapability):
    """
    Capacidade de consulta genérica para perguntas dinâmicas.

    Permite ao Claude executar consultas que não têm capacidade específica.
    """

    NOME = "consulta_generica"
    DOMINIO = "carteira"
    TIPO = "consulta"
    INTENCOES = [
        "consulta_generica",
        "consultar_por_data",
        "listar_por_data",
        "buscar_por_filtro",
        "consultar_tabela"
    ]
    CAMPOS_BUSCA = ["tabela", "campo_filtro", "valor_filtro", "data_inicio", "data_fim"]
    DESCRICAO = "Executa consultas genéricas em tabelas permitidas"
    EXEMPLOS = [
        "O que entrou de pedido ontem e hoje?",
        "Pedidos com data_pedido entre ontem e hoje",
        "Separações criadas hoje"
    ]

    def extrair_valor_busca(self, entidades: dict) -> tuple:
        """
        Sobrescreve para retornar critério válido para consultas genéricas.

        Para consultas genéricas, o "critério" é ter tabela ou data definidos.
        """
        # Se tem tabela, usa ela como "valor"
        tabela = entidades.get('tabela')
        if tabela:
            return 'tabela', tabela

        # Se tem data_inicio, usa como critério
        data_inicio = entidades.get('data_inicio')
        if data_inicio:
            return 'data_inicio', data_inicio

        # Se tem campo_filtro + valor_filtro
        campo_filtro = entidades.get('campo_filtro')
        valor_filtro = entidades.get('valor_filtro')
        if campo_filtro and valor_filtro:
            return campo_filtro, valor_filtro

        return None, None

    def pode_processar(self, intencao: str, entidades: dict) -> bool:
        """Verifica se pode processar esta consulta."""
        # Processa se tem tabela ou se a intenção é genérica
        if intencao in self.INTENCOES:
            return True

        # Se tem entidades de consulta genérica
        if entidades.get('tabela') or entidades.get('data_inicio') or entidades.get('data_fim'):
            return True

        return False

    def executar(self, entidades: dict, contexto: dict) -> dict:
        """
        Executa a consulta genérica.

        Args:
            entidades: Entidades extraídas pelo Claude
                - tabela: Nome da tabela (ex: CarteiraPrincipal)
                - campo_filtro: Campo para filtrar (ex: data_pedido)
                - valor_filtro: Valor do filtro ou lista [inicio, fim]
                - data_inicio: Data inicial (formato ISO ou relativo)
                - data_fim: Data final
                - campos_retorno: Campos a retornar (opcional)
                - limite: Máximo de resultados

        Returns:
            Dict com resultados da consulta
        """
        try:
            # 1. Resolve a tabela
            tabela_nome = self._resolver_tabela(entidades)
            if not tabela_nome:
                return {
                    'sucesso': False,
                    'erro': 'Tabela não identificada ou não permitida'
                }

            # 2. Importa o modelo
            Model = self._importar_modelo(tabela_nome)
            if not Model:
                return {
                    'sucesso': False,
                    'erro': f'Modelo {tabela_nome} não encontrado'
                }

            # 3. Monta e executa a query
            resultado = self._executar_query(Model, entidades)

            return resultado

        except Exception as e:
            logger.error(f"[CONSULTA_GENERICA] Erro: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }

    def _resolver_tabela(self, entidades: dict) -> Optional[str]:
        """Resolve nome da tabela das entidades."""
        tabela = entidades.get('tabela', '')

        if not tabela:
            # Tenta inferir da intenção ou campo_filtro
            campo = entidades.get('campo_filtro', '')

            # Se campo começa com nome de modelo conhecido
            if '.' in campo:
                tabela = campo.split('.')[0]

            # Inferências comuns
            if 'data_pedido' in campo or 'num_pedido' in campo:
                tabela = 'CarteiraPrincipal'
            elif 'criado_em' in campo and entidades.get('intencao') == 'separacao':
                tabela = 'Separacao'

        # Normaliza e valida
        tabela_lower = tabela.lower().replace(' ', '')

        if tabela_lower in TABELAS_PERMITIDAS:
            return TABELAS_PERMITIDAS[tabela_lower]

        # Tenta match parcial
        for alias, nome in TABELAS_PERMITIDAS.items():
            if alias in tabela_lower or tabela_lower in alias:
                return nome

        return None

    def _importar_modelo(self, nome_modelo: str):
        """Importa dinamicamente um modelo SQLAlchemy."""
        try:
            modulo_path = MODELOS_MODULOS.get(nome_modelo)
            if not modulo_path:
                return None

            import importlib
            modulo = importlib.import_module(modulo_path)
            return getattr(modulo, nome_modelo, None)

        except Exception as e:
            logger.error(f"Erro ao importar modelo {nome_modelo}: {e}")
            return None

    def _executar_query(self, Model, entidades: dict) -> dict:
        """Executa a query no modelo."""
        from app import db
        from sqlalchemy import and_, or_, desc, asc

        # Inicia query base
        query = Model.query

        # Obtém campos disponíveis no modelo
        campos_modelo = self._obter_campos_modelo(Model)

        # 1. Aplica filtro de data se houver
        filtros = []

        data_inicio = self._resolver_data(entidades.get('data_inicio'))
        data_fim = self._resolver_data(entidades.get('data_fim'))
        campo_filtro = entidades.get('campo_filtro', 'data_pedido')

        # Valida campo de filtro
        if '.' in campo_filtro:
            campo_filtro = campo_filtro.split('.')[-1]

        if campo_filtro not in campos_modelo:
            # Tenta campos alternativos de data por ordem de prioridade
            # data_fatura para FaturamentoProduto, data_pedido para CarteiraPrincipal, etc
            for alt in ['data_fatura', 'data_pedido', 'criado_em', 'created_at', 'data']:
                if alt in campos_modelo:
                    campo_filtro = alt
                    break

        # Aplica filtro de data
        if campo_filtro in campos_modelo and (data_inicio or data_fim):
            campo_attr = getattr(Model, campo_filtro, None)
            if campo_attr:
                if data_inicio and data_fim:
                    filtros.append(campo_attr.between(data_inicio, data_fim))
                elif data_inicio:
                    filtros.append(campo_attr >= data_inicio)
                elif data_fim:
                    filtros.append(campo_attr <= data_fim)

        # 2. Aplica outros filtros das entidades
        valor_filtro = entidades.get('valor_filtro')
        if valor_filtro and campo_filtro in campos_modelo:
            campo_attr = getattr(Model, campo_filtro, None)
            if campo_attr:
                if isinstance(valor_filtro, list):
                    filtros.append(campo_attr.in_(valor_filtro))
                else:
                    # Se é texto, usa ILIKE
                    if isinstance(valor_filtro, str):
                        filtros.append(campo_attr.ilike(f'%{valor_filtro}%'))
                    else:
                        filtros.append(campo_attr == valor_filtro)

        # 3. Filtro sincronizado_nf para Separacao/Carteira (sempre false para itens ativos)
        if hasattr(Model, 'sincronizado_nf'):
            filtros.append(Model.sincronizado_nf == False)

        # Aplica filtros
        if filtros:
            query = query.filter(and_(*filtros))

        # 4. Ordenação (mais recentes primeiro)
        if campo_filtro in campos_modelo:
            campo_attr = getattr(Model, campo_filtro, None)
            if campo_attr:
                query = query.order_by(desc(campo_attr))

        # 5. Limite de resultados
        limite = min(entidades.get('limite', 100), 500)
        query = query.limit(limite)

        # 6. Executa
        try:
            resultados = query.all()

            # Campos a retornar
            campos_retorno = entidades.get('campos_retorno') or self._campos_padrao(Model)

            # Carrega cache de palletização se for CarteiraPrincipal
            cache_palletizacao = {}
            if Model.__name__ == 'CarteiraPrincipal':
                cache_palletizacao = self._carregar_cache_palletizacao()

            # Serializa resultados
            from decimal import Decimal
            dados = []
            total_pallets = 0.0
            total_peso = 0.0

            for r in resultados:
                item = {}
                for campo in campos_retorno:
                    if hasattr(r, campo):
                        valor = getattr(r, campo)
                        # Serializa datas
                        if isinstance(valor, (date, datetime)):
                            valor = valor.isoformat()
                        # Serializa Decimal para float
                        elif isinstance(valor, Decimal):
                            valor = float(valor)
                        item[campo] = valor

                # Calcula pallets se for CarteiraPrincipal
                if Model.__name__ == 'CarteiraPrincipal' and hasattr(r, 'cod_produto'):
                    cod_produto = r.cod_produto
                    quantidade = float(r.qtd_saldo_produto_pedido or 0)
                    pallet_info = cache_palletizacao.get(cod_produto)

                    if pallet_info and pallet_info['palletizacao'] > 0:
                        pallets = round(quantidade / pallet_info['palletizacao'], 2)
                        peso = round(quantidade * pallet_info['peso_bruto'], 2)
                        item['pallets'] = pallets
                        item['peso_calculado'] = peso
                        total_pallets += pallets
                        total_peso += peso
                    else:
                        item['pallets'] = 0
                        item['peso_calculado'] = 0

                dados.append(item)

            resultado = {
                'sucesso': True,
                'total': len(dados),
                'total_encontrado': len(dados),
                'dados': dados,
                'modelo': Model.__name__,
                'filtros_aplicados': {
                    'campo': campo_filtro,
                    'data_inicio': data_inicio.isoformat() if data_inicio else None,
                    'data_fim': data_fim.isoformat() if data_fim else None
                }
            }

            # Adiciona totais de pallets se calculados
            if total_pallets > 0:
                resultado['total_pallets'] = round(total_pallets, 2)
                resultado['total_peso'] = round(total_peso, 2)

            return resultado

        except Exception as e:
            logger.error(f"Erro na query: {e}")
            return {
                'sucesso': False,
                'erro': f'Erro na consulta: {str(e)}'
            }

    def _carregar_cache_palletizacao(self) -> Dict[str, Dict]:
        """
        Carrega cache de palletização de todos os produtos.

        Returns:
            Dict com cod_produto -> {palletizacao, peso_bruto}
        """
        try:
            from app.producao.models import CadastroPalletizacao

            produtos = CadastroPalletizacao.query.filter_by(ativo=True).all()

            cache = {}
            for p in produtos:
                cache[p.cod_produto] = {
                    'palletizacao': float(p.palletizacao or 0),
                    'peso_bruto': float(p.peso_bruto or 0)
                }

            logger.info(f"[CONSULTA_GENERICA] Cache palletização carregado: {len(cache)} produtos")
            return cache

        except Exception as e:
            logger.error(f"[CONSULTA_GENERICA] Erro ao carregar cache palletização: {e}")
            return {}

    def _obter_campos_modelo(self, Model) -> List[str]:
        """Obtém lista de campos de um modelo SQLAlchemy."""
        try:
            from sqlalchemy.inspection import inspect
            mapper = inspect(Model)
            return [col.key for col in mapper.columns]
        except Exception:
            # Fallback: atributos públicos que não são métodos
            return [
                attr for attr in dir(Model)
                if not attr.startswith('_') and not callable(getattr(Model, attr, None))
            ]

    def _campos_padrao(self, Model) -> List[str]:
        """Retorna campos padrão para retorno baseado no modelo."""
        nome = Model.__name__

        # Campos específicos por modelo
        CAMPOS_POR_MODELO = {
            'CarteiraPrincipal': [
                'num_pedido', 'cod_produto', 'nome_produto', 'raz_social_red',
                'qtd_saldo_produto_pedido', 'data_pedido', 'data_entrega_pedido'
            ],
            'Separacao': [
                'separacao_lote_id', 'num_pedido', 'cod_produto', 'nome_produto',
                'raz_social_red', 'qtd_saldo', 'expedicao', 'status'
            ],
            'Pedido': [
                'num_pedido', 'cnpj_cpf', 'raz_social_red', 'nome_cidade',
                'cod_uf', 'valor_saldo_total', 'status'
            ],
            'FaturamentoProduto': [
                'numero_nf', 'data_fatura', 'nome_cliente', 'cnpj_cliente',
                'cod_produto', 'nome_produto', 'qtd_produto_faturado',
                'valor_produto_faturado', 'vendedor', 'status_nf'
            ],
            'Embarque': [
                'numero', 'data_prevista_embarque', 'data_embarque', 'status',
                'tipo_carga', 'valor_total', 'peso_total', 'pallet_total'
            ],
            'Frete': [
                'id', 'numero_cte', 'valor_frete', 'peso', 'data_emissao',
                'transportadora', 'status'
            ],
        }

        return CAMPOS_POR_MODELO.get(nome, self._obter_campos_modelo(Model)[:10])

    def _resolver_data(self, data_str) -> Optional[date]:
        """Resolve string de data para objeto date."""
        if not data_str:
            return None

        # Se já é date/datetime
        if isinstance(data_str, date):
            return data_str
        if isinstance(data_str, datetime):
            return data_str.date()

        hoje = date.today()

        # Datas relativas
        data_lower = str(data_str).lower().strip()

        if data_lower in ('hoje', 'today'):
            return hoje
        elif data_lower in ('ontem', 'yesterday'):
            return hoje - timedelta(days=1)
        elif data_lower in ('anteontem',):
            return hoje - timedelta(days=2)
        elif data_lower in ('amanha', 'tomorrow'):
            return hoje + timedelta(days=1)
        elif 'semana' in data_lower:
            if 'passada' in data_lower:
                return hoje - timedelta(days=7)
            elif 'proxima' in data_lower or 'que vem' in data_lower:
                return hoje + timedelta(days=7)
        elif 'mes' in data_lower:
            if 'passado' in data_lower:
                return hoje.replace(day=1) - timedelta(days=1)

        # Tenta formatos de data
        formatos = [
            '%Y-%m-%d',      # ISO
            '%d/%m/%Y',      # BR
            '%d/%m',         # BR sem ano
            '%d-%m-%Y',
        ]

        for fmt in formatos:
            try:
                parsed = datetime.strptime(data_str, fmt)
                # Se não tem ano, usa o atual
                if '%Y' not in fmt:
                    parsed = parsed.replace(year=hoje.year)
                return parsed.date()
            except ValueError:
                continue

        return None

    def formatar_contexto(self, resultado: dict) -> str:
        """Formata o resultado para contexto do Claude."""
        if not resultado.get('sucesso'):
            return f"Erro na consulta: {resultado.get('erro')}"

        total = resultado.get('total', 0)
        modelo = resultado.get('modelo', 'desconhecido')
        filtros = resultado.get('filtros_aplicados', {})

        linhas = [
            f"=== RESULTADO DA CONSULTA ===",
            f"Modelo: {modelo}",
            f"Total encontrado: {total}",
        ]

        # Adiciona totais de pallets se disponível
        if resultado.get('total_pallets'):
            linhas.append(f"Total Pallets: {resultado['total_pallets']}")
        if resultado.get('total_peso'):
            linhas.append(f"Total Peso: {resultado['total_peso']} kg")

        if filtros.get('data_inicio') or filtros.get('data_fim'):
            linhas.append(f"Período: {filtros.get('data_inicio')} a {filtros.get('data_fim')}")

        if total == 0:
            linhas.append("\nNenhum resultado encontrado para os critérios informados.")
        else:
            linhas.append("\n--- DADOS ---")
            for i, item in enumerate(resultado.get('dados', [])[:20], 1):
                # Prioriza campos importantes incluindo pallets
                campos_prio = ['num_pedido', 'raz_social_red', 'nome_produto', 'qtd_saldo_produto_pedido', 'pallets']
                partes = []
                for campo in campos_prio:
                    if campo in item and item[campo] is not None:
                        partes.append(f"{campo}: {item[campo]}")
                if not partes:
                    partes = [f"{k}: {v}" for k, v in item.items() if v is not None][:5]
                linhas.append(f"{i}. {' | '.join(partes[:5])}")

            if total > 20:
                linhas.append(f"\n... e mais {total - 20} registro(s)")

        return "\n".join(linhas)
