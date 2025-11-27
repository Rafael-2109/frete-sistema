"""
LoaderExecutor - Executor de Loaders Estruturados.

Permite ao Claude compor consultas complexas via JSON estruturado,
SEM executar codigo Python arbitrario.

Funcionalidades:
- JOINs seguros entre Models conhecidos
- Filtros complexos (ilike, is_null, in, between, etc)
- Agregacoes e agrupamentos
- Subqueries seguras
- Ordenacao e limite
- Validacao de campos e Models
- Read-only garantido
- Timeout em todas as queries

FORMATO DO JSON:
{
    "modelo_base": "Separacao",
    "joins": [
        {"modelo": "CarteiraPrincipal", "tipo": "left", "on": {"local": "num_pedido", "remoto": "num_pedido"}}
    ],
    "filtros": [
        {"campo": "raz_social_red", "operador": "ilike", "valor": "%Assai%"},
        {"campo": "agendamento", "operador": "is_null"},
        {"campo": "sincronizado_nf", "operador": "==", "valor": false}
    ],
    "campos_retorno": ["num_pedido", "raz_social_red", "qtd_saldo", "agendamento"],
    "agregacao": {
        "tipo": "agrupar",
        "por": ["num_pedido", "raz_social_red"],
        "funcoes": [{"func": "sum", "campo": "qtd_saldo", "alias": "total_qtd"}]
    },
    "ordenar": [{"campo": "num_pedido", "direcao": "asc"}],
    "limite": 100
}

Criado em: 23/11/2025
Limite: 500 linhas
"""

import logging
from typing import Dict, Any, List, Optional, Type
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURAÇÃO DINÂMICA DE LIMITES
# =============================================================================

def _get_max_registros_query() -> int:
    """Retorna limite máximo de registros baseado na config."""
    try:
        from app.claude_ai_lite.config import get_config
        return get_config().limites.max_registros_query
    except ImportError:
        return 1000  # Fallback

# ============================================
# MODELS PERMITIDOS (whitelist de seguranca)
# ============================================
#
# IMPORTANTE: Apenas models listados aqui podem ser usados em consultas.
# Para adicionar novo model:
#   1. Verificar se o model existe no caminho especificado
#   2. Adicionar entrada: 'NomeModel': 'caminho.do.modulo'
#   3. Testar: from caminho.do.modulo import NomeModel
#
# NOTAS:
#   - Pedido: E uma VIEW (read-only), nao uma tabela. Funciona para SELECT.
#   - Para projecao de estoque, use ServicoEstoqueSimples (servico, nao model)
#
# ============================================

MODELS_PERMITIDOS = {
    # === CARTEIRA E SEPARACAO ===
    'CarteiraPrincipal': 'app.carteira.models',      # Itens da carteira de pedidos
    'Separacao': 'app.separacao.models',             # Itens separados/pre-separados
    'Pedido': 'app.pedidos.models',                  # VIEW agregada de Separacao (read-only!)
    'PreSeparacaoItem': 'app.carteira.models',       # Pre-separacoes (deprecated, mas ainda usado)
    'SaldoStandby': 'app.carteira.models',           # Saldos em standby

    # === PRODUCAO E ESTOQUE ===
    'CadastroPalletizacao': 'app.producao.models',   # Palletizacao e peso dos produtos
    'ProgramacaoProducao': 'app.producao.models',    # Programacao de producao
    'MovimentacaoEstoque': 'app.estoque.models',     # Movimentacoes de entrada/saida
    'UnificacaoCodigos': 'app.estoque.models',       # Codigos unificados de produtos

    # === FATURAMENTO ===
    'FaturamentoProduto': 'app.faturamento.models',  # Produtos faturados por NF

    # === EMBARQUES ===
    'Embarque': 'app.embarques.models',              # Embarques (cabecalho)
    'EmbarqueItem': 'app.embarques.models',          # Itens do embarque

    # === LOCALIDADES E ROTAS ===
    'CadastroRota': 'app.localidades.models',        # Rotas principais
    'CadastroSubRota': 'app.localidades.models',     # Sub-rotas

    # === FRETES (expandir quando necessario) ===
    'Frete': 'app.fretes.models',                    # Fretes
}

# ============================================
# OPERADORES PERMITIDOS (whitelist)
# ============================================

OPERADORES_PERMITIDOS = {
    '==': 'eq',
    '!=': 'ne',
    '>': 'gt',
    '>=': 'ge',
    '<': 'lt',
    '<=': 'le',
    'ilike': 'ilike',
    'like': 'like',
    'in': 'in_',
    'not_in': 'notin_',
    'is_null': 'is_null',
    'is_not_null': 'is_not_null',
    'between': 'between',
    'contains': 'contains',
    'startswith': 'startswith',
    'endswith': 'endswith',
}

# ============================================
# FUNCOES DE AGREGACAO PERMITIDAS
# ============================================

AGREGACOES_PERMITIDAS = ['count', 'sum', 'avg', 'min', 'max']


class LoaderExecutor:
    """
    Executa consultas estruturadas de forma segura.

    Uso:
        executor = LoaderExecutor()
        resultado = executor.executar(definicao_json, parametros)
    """

    def __init__(self, timeout_segundos: int = 10):
        self.timeout = timeout_segundos
        self._models_cache: Dict[str, Type] = {}
        self._campos_cache: Dict[str, List[str]] = {}

    def executar(self, definicao: Dict[str, Any], parametros: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executa uma consulta estruturada.

        Args:
            definicao: JSON com a definicao da consulta
            parametros: Valores dinamicos (ex: {"$cliente": "Assai"})

        Returns:
            Dict com sucesso, dados, total e metadados
        """
        resultado = {
            'sucesso': False,
            'dados': [],
            'total': 0,
            'query_executada': '',
            'erro': None
        }

        try:
            # 1. Valida definicao
            validacao = self._validar_definicao(definicao)
            if not validacao['valido']:
                resultado['erro'] = f"Definicao invalida: {validacao['erros']}"
                return resultado

            # 2. Substitui parametros
            definicao_processada = self._substituir_parametros(definicao, parametros or {})

            # 3. Carrega modelo base
            modelo_base = self._carregar_modelo(definicao_processada['modelo_base'])
            if not modelo_base:
                resultado['erro'] = f"Modelo nao encontrado: {definicao_processada['modelo_base']}"
                return resultado

            # 4. Constroi query
            query = self._construir_query(modelo_base, definicao_processada)

            # 5. Executa com timeout
            dados = self._executar_com_timeout(query, definicao_processada)

            # 6. Formata resultado
            resultado['sucesso'] = True
            resultado['dados'] = dados
            resultado['total'] = len(dados)
            resultado['query_executada'] = str(query)

        except Exception as e:
            logger.error(f"[LOADER_EXECUTOR] Erro: {e}")
            resultado['erro'] = str(e)

            # Faz rollback para limpar transacao com erro
            try:
                from app import db
                db.session.rollback()
                logger.debug("[LOADER_EXECUTOR] Rollback executado apos erro")
            except Exception:
                pass  # Ignora erros de rollback

        return resultado

    def _validar_definicao(self, definicao: Dict) -> Dict[str, Any]:
        """Valida a estrutura da definicao JSON."""
        erros = []
        avisos = []

        # Modelo base obrigatorio
        if not definicao.get('modelo_base'):
            erros.append("Campo 'modelo_base' obrigatorio")
        elif definicao['modelo_base'] not in MODELS_PERMITIDOS:
            erros.append(f"Modelo '{definicao['modelo_base']}' nao permitido")

        # Valida JOINs
        for i, join in enumerate(definicao.get('joins', [])):
            if not join.get('modelo'):
                erros.append(f"JOIN #{i}: campo 'modelo' obrigatorio")
            elif join['modelo'] not in MODELS_PERMITIDOS:
                erros.append(f"JOIN #{i}: modelo '{join['modelo']}' nao permitido")
            if not join.get('on'):
                erros.append(f"JOIN #{i}: campo 'on' obrigatorio")

        # Valida filtros (suporta lista simples ou dict com and/or)
        filtros = definicao.get('filtros', [])
        erros_filtros = self._validar_filtros_recursivo(filtros)
        erros.extend(erros_filtros)

        # Valida agregacoes
        if definicao.get('agregacao'):
            ag = definicao['agregacao']
            if ag.get('tipo') not in ('agrupar', 'contar', 'somar'):
                avisos.append(f"Tipo de agregacao '{ag.get('tipo')}' pode nao ser suportado")
            for func in ag.get('funcoes', []):
                if func.get('func') not in AGREGACOES_PERMITIDAS:
                    erros.append(f"Funcao de agregacao '{func.get('func')}' nao permitida")

        # Valida limite (usa config dinâmica)
        max_permitido = _get_max_registros_query()
        limite = definicao.get('limite', 100)
        if limite > max_permitido:
            avisos.append(f"Limite {limite} muito alto, usando {max_permitido}")

        return {
            'valido': len(erros) == 0,
            'erros': erros,
            'avisos': avisos
        }

    def _validar_filtros_recursivo(self, filtros, path: str = "filtros") -> List[str]:
        """Valida filtros recursivamente (suporta and/or aninhados)."""
        erros = []

        if filtros is None:
            return erros

        # Se for dict com "or" ou "and"
        if isinstance(filtros, dict):
            if 'or' in filtros:
                for i, f in enumerate(filtros['or']):
                    erros.extend(self._validar_filtros_recursivo(f, f"{path}.or[{i}]"))
            elif 'and' in filtros:
                for i, f in enumerate(filtros['and']):
                    erros.extend(self._validar_filtros_recursivo(f, f"{path}.and[{i}]"))
            else:
                # Filtro simples
                if not filtros.get('campo'):
                    erros.append(f"{path}: campo 'campo' obrigatorio")
                if not filtros.get('operador'):
                    erros.append(f"{path}: campo 'operador' obrigatorio")
                elif filtros['operador'] not in OPERADORES_PERMITIDOS:
                    erros.append(f"{path}: operador '{filtros['operador']}' nao permitido")

        # Se for lista (AND implicito)
        elif isinstance(filtros, list):
            for i, f in enumerate(filtros):
                erros.extend(self._validar_filtros_recursivo(f, f"{path}[{i}]"))

        return erros

    def _substituir_parametros(self, definicao: Dict, parametros: Dict) -> Dict:
        """Substitui parametros dinamicos ($variavel) pelos valores."""
        import json
        import re

        # Serializa para string
        json_str = json.dumps(definicao, ensure_ascii=False)

        # Substitui cada parametro
        for chave, valor in parametros.items():
            # Garante que chave comeca com $
            if not chave.startswith('$'):
                chave = f'${chave}'

            # Escapa valor para JSON
            if isinstance(valor, str):
                valor_escaped = valor.replace('"', '\\"')
                # Substitui mantendo aspas
                json_str = json_str.replace(f'"{chave}"', f'"{valor_escaped}"')
                # Substitui dentro de strings (ex: "%$cliente%")
                json_str = json_str.replace(chave, valor_escaped)
            elif isinstance(valor, (int, float, bool)):
                json_str = json_str.replace(f'"{chave}"', str(valor).lower() if isinstance(valor, bool) else str(valor))
            elif valor is None:
                json_str = json_str.replace(f'"{chave}"', 'null')

        return json.loads(json_str)

    def _carregar_modelo(self, nome_modelo: str) -> Optional[Type]:
        """Carrega classe do modelo do cache ou importa."""
        if nome_modelo in self._models_cache:
            return self._models_cache[nome_modelo]

        if nome_modelo not in MODELS_PERMITIDOS:
            return None

        try:
            modulo_path = MODELS_PERMITIDOS[nome_modelo]
            modulo = __import__(modulo_path, fromlist=[nome_modelo])
            classe = getattr(modulo, nome_modelo)
            self._models_cache[nome_modelo] = classe
            return classe
        except Exception as e:
            logger.error(f"[LOADER_EXECUTOR] Erro ao carregar modelo {nome_modelo}: {e}")
            return None

    def _obter_campos_modelo(self, modelo: Type) -> List[str]:
        """Retorna lista de campos de um modelo."""
        nome = modelo.__name__
        if nome in self._campos_cache:
            return self._campos_cache[nome]

        from sqlalchemy import inspect
        try:
            mapper = inspect(modelo)
            campos = [c.key for c in mapper.columns]
            self._campos_cache[nome] = campos
            return campos
        except Exception:
            return []

    def _construir_query(self, modelo_base: Type, definicao: Dict):
        """Constroi query SQLAlchemy a partir da definicao."""
        from sqlalchemy import and_, or_, func, desc, asc
        from app import db

        # Verifica se tem agregacao (muda a forma de construir a query)
        tem_agregacao = bool(definicao.get('agregacao'))

        if tem_agregacao:
            # Query com agregacao: usa db.session.query() para controle total
            agregacao = definicao['agregacao']
            campos_grupo = agregacao.get('por', [])

            # Monta lista de colunas para SELECT
            colunas_select = []

            # Adiciona campos de agrupamento
            for campo_nome in campos_grupo:
                campo = getattr(modelo_base, campo_nome, None)
                if campo is not None:
                    colunas_select.append(campo)

            # Adiciona funcoes de agregacao
            for func_def in agregacao.get('funcoes', []):
                func_nome = func_def.get('func')
                campo_nome = func_def.get('campo')
                alias = func_def.get('alias', f'{func_nome}_{campo_nome}')

                # NOVO: Suporte a expressões matemáticas simples (campo1 * campo2)
                campo = self._resolver_expressao_campo(modelo_base, campo_nome)

                if campo is not None and func_nome in AGREGACOES_PERMITIDAS:
                    if func_nome == 'count':
                        colunas_select.append(func.count(campo).label(alias))
                    elif func_nome == 'sum':
                        colunas_select.append(func.sum(campo).label(alias))
                    elif func_nome == 'avg':
                        colunas_select.append(func.avg(campo).label(alias))
                    elif func_nome == 'min':
                        colunas_select.append(func.min(campo).label(alias))
                    elif func_nome == 'max':
                        colunas_select.append(func.max(campo).label(alias))

            # Cria query com colunas especificas E select_from imediato
            query = db.session.query(*colunas_select).select_from(modelo_base)
        else:
            # Query normal: usa modelo_base.query
            query = modelo_base.query

        # Aplica JOINs
        modelos_join = {modelo_base.__name__: modelo_base}
        for join_def in definicao.get('joins', []):
            modelo_join = self._carregar_modelo(join_def['modelo'])
            if modelo_join:
                modelos_join[join_def['modelo']] = modelo_join
                on_config = join_def['on']

                # Suporta dot-notation: "Modelo.campo" ou apenas "campo"
                campo_local = self._resolver_campo_join(
                    modelos_join, on_config['local'], modelo_base
                )
                campo_remoto = self._resolver_campo_join(
                    modelos_join, on_config['remoto'], modelo_join
                )

                if campo_local is not None and campo_remoto is not None:
                    tipo_join = join_def.get('tipo', 'inner')
                    if tipo_join == 'left':
                        query = query.outerjoin(modelo_join, campo_local == campo_remoto)
                    else:
                        query = query.join(modelo_join, campo_local == campo_remoto)

        # Aplica filtros (suporta AND, OR e filtros simples)
        filtros_config = definicao.get('filtros', [])
        filtro_final = self._construir_filtros_compostos(modelo_base, modelos_join, filtros_config)
        if filtro_final is not None:
            query = query.filter(filtro_final)

        # Aplica GROUP BY para agregacao
        campos_group_by_nomes = set()  # Para validar ORDER BY
        aliases_agregacao = {}  # Mapa alias -> expressao SQLAlchemy

        if tem_agregacao:
            agregacao = definicao['agregacao']
            campos_grupo = []
            for campo_nome in agregacao.get('por', []):
                campo = getattr(modelo_base, campo_nome, None)
                if campo is not None:
                    campos_grupo.append(campo)
                    campos_group_by_nomes.add(campo_nome)
            if campos_grupo:
                query = query.group_by(*campos_grupo)

            # Registra aliases das agregacoes para permitir ORDER BY
            for func_def in agregacao.get('funcoes', []):
                alias = func_def.get('alias', f"{func_def.get('func')}_{func_def.get('campo')}")
                aliases_agregacao[alias] = True  # Apenas marca como valido

        # Aplica ordenacao (com validacao para agregacao)
        for ordem in definicao.get('ordenar', []):
            campo_nome = ordem['campo']

            # Se tem agregacao, permite ordenar por:
            # 1. Campos no GROUP BY
            # 2. Aliases das funcoes de agregacao
            if tem_agregacao:
                nome_simples = campo_nome.split('.')[-1] if '.' in campo_nome else campo_nome

                # Verifica se e um alias de agregacao
                if nome_simples in aliases_agregacao:
                    # Ordena pelo alias (SQLAlchemy suporta via text())
                    from sqlalchemy import text
                    if ordem.get('direcao', 'asc') == 'desc':
                        query = query.order_by(text(f"{nome_simples} DESC"))
                    else:
                        query = query.order_by(text(f"{nome_simples} ASC"))
                    continue

                # Verifica se esta no GROUP BY
                if nome_simples not in campos_group_by_nomes:
                    logger.warning(f"[LOADER_EXECUTOR] Ignorando ORDER BY '{campo_nome}' - nao esta no GROUP BY nem e alias")
                    continue

            campo = self._resolver_campo(modelo_base, modelos_join, campo_nome)
            if campo is not None:
                if ordem.get('direcao', 'asc') == 'desc':
                    query = query.order_by(desc(campo))
                else:
                    query = query.order_by(asc(campo))

        # Aplica limite (usa config dinâmica)
        max_permitido = _get_max_registros_query()
        limite = min(definicao.get('limite', 100), max_permitido)
        query = query.limit(limite)

        return query

    def _resolver_campo_join(self, modelos_join: Dict, nome_campo: str, modelo_default: Type):
        """
        Resolve campo para JOIN com suporte a dot-notation.

        Args:
            modelos_join: Dict de modelos disponiveis
            nome_campo: "Modelo.campo" ou "campo"
            modelo_default: Modelo a usar se nao especificado

        Returns:
            Coluna SQLAlchemy ou None
        """
        if '.' in nome_campo:
            partes = nome_campo.split('.')
            nome_modelo = partes[0]
            nome_col = partes[1]
            modelo = modelos_join.get(nome_modelo)
            if modelo:
                return getattr(modelo, nome_col, None)
        else:
            return getattr(modelo_default, nome_campo, None)
        return None

    def _resolver_campo(self, modelo_base: Type, modelos_join: Dict, nome_campo: str):
        """Resolve nome do campo para coluna SQLAlchemy."""
        # Verifica se tem prefixo de modelo (ex: "Separacao.qtd_saldo")
        if '.' in nome_campo:
            partes = nome_campo.split('.')
            nome_modelo = partes[0]
            nome_col = partes[1]
            modelo = modelos_join.get(nome_modelo)
            if modelo:
                return getattr(modelo, nome_col, None)
        else:
            # Tenta no modelo base primeiro
            campo = getattr(modelo_base, nome_campo, None)
            if campo is not None:
                return campo
            # Tenta nos modelos de JOIN
            for modelo in modelos_join.values():
                campo = getattr(modelo, nome_campo, None)
                if campo is not None:
                    return campo
        return None

    def _resolver_expressao_campo(self, modelo_base: Type, expressao: str):
        """
        Resolve expressão de campo, suportando operações matemáticas simples.

        Suporta:
        - Campo simples: "valor_total" -> modelo.valor_total
        - Multiplicação: "preco * qtd" ou "preco_produto_pedido * qtd_saldo_produto_pedido"
        - Adição: "campo1 + campo2"
        - Subtração: "campo1 - campo2"

        Args:
            modelo_base: Modelo SQLAlchemy
            expressao: String com nome do campo ou expressão

        Returns:
            Coluna SQLAlchemy ou expressão matemática
        """
        expressao = expressao.strip()

        # Detecta operadores matemáticos
        operadores = ['*', '+', '-', '/']
        operador_encontrado = None
        for op in operadores:
            if f' {op} ' in expressao:
                operador_encontrado = op
                break

        if operador_encontrado:
            # Separa os operandos
            partes = expressao.split(f' {operador_encontrado} ')
            if len(partes) == 2:
                campo1_nome = partes[0].strip()
                campo2_nome = partes[1].strip()

                campo1 = getattr(modelo_base, campo1_nome, None)
                campo2 = getattr(modelo_base, campo2_nome, None)

                if campo1 is not None and campo2 is not None:
                    if operador_encontrado == '*':
                        return campo1 * campo2
                    elif operador_encontrado == '+':
                        return campo1 + campo2
                    elif operador_encontrado == '-':
                        return campo1 - campo2
                    elif operador_encontrado == '/':
                        return campo1 / campo2
                else:
                    logger.warning(f"[LOADER_EXECUTOR] Campos não encontrados na expressão: {expressao}")
                    return None

        # Campo simples
        return getattr(modelo_base, expressao, None)

    def _construir_filtros_compostos(self, modelo_base: Type, modelos_join: Dict, filtros_config):
        """
        Constroi filtros compostos com suporte a AND/OR.

        Formatos suportados:
        1. Lista simples (AND implicito):
           [{"campo": "...", "operador": "...", "valor": "..."}]

        2. OR explicito:
           {"or": [filtro1, filtro2, ...]}

        3. AND explicito:
           {"and": [filtro1, filtro2, ...]}

        4. Combinado:
           {"and": [filtro1, {"or": [filtro2, filtro3]}]}
        """
        from sqlalchemy import and_, or_

        # Se for None ou vazio
        if not filtros_config:
            return None

        # Se for dict com "or" ou "and"
        if isinstance(filtros_config, dict):
            if 'or' in filtros_config:
                # OR entre os filtros
                subfiltros = []
                for f in filtros_config['or']:
                    subfiltro = self._construir_filtros_compostos(modelo_base, modelos_join, f)
                    if subfiltro is not None:
                        subfiltros.append(subfiltro)
                if subfiltros:
                    return or_(*subfiltros)
                return None

            elif 'and' in filtros_config:
                # AND explicito entre os filtros
                subfiltros = []
                for f in filtros_config['and']:
                    subfiltro = self._construir_filtros_compostos(modelo_base, modelos_join, f)
                    if subfiltro is not None:
                        subfiltros.append(subfiltro)
                if subfiltros:
                    return and_(*subfiltros)
                return None

            else:
                # Filtro simples em formato dict
                return self._construir_filtro(modelo_base, modelos_join, filtros_config)

        # Se for lista (AND implicito)
        elif isinstance(filtros_config, list):
            subfiltros = []
            for f in filtros_config:
                subfiltro = self._construir_filtros_compostos(modelo_base, modelos_join, f)
                if subfiltro is not None:
                    subfiltros.append(subfiltro)
            if subfiltros:
                return and_(*subfiltros)
            return None

        return None

    def _construir_filtro(self, modelo_base: Type, modelos_join: Dict, filtro: Dict):
        """Constroi clausula de filtro SQLAlchemy simples."""
        if not isinstance(filtro, dict) or 'campo' not in filtro:
            return None

        campo = self._resolver_campo(modelo_base, modelos_join, filtro['campo'])
        if campo is None:
            logger.warning(f"[LOADER_EXECUTOR] Campo nao encontrado: {filtro['campo']}")
            return None

        operador = filtro['operador']
        valor = filtro.get('valor')

        try:
            if operador == '==':
                return campo == valor
            elif operador == '!=':
                return campo != valor
            elif operador == '>':
                return campo > valor
            elif operador == '>=':
                return campo >= valor
            elif operador == '<':
                return campo < valor
            elif operador == '<=':
                return campo <= valor
            elif operador == 'ilike':
                return campo.ilike(valor)
            elif operador == 'like':
                return campo.like(valor)
            elif operador == 'in':
                return campo.in_(valor if isinstance(valor, list) else [valor])
            elif operador == 'not_in':
                return campo.notin_(valor if isinstance(valor, list) else [valor])
            elif operador == 'is_null':
                return campo.is_(None)
            elif operador == 'is_not_null':
                return campo.isnot(None)
            elif operador == 'between':
                if isinstance(valor, list) and len(valor) == 2:
                    return campo.between(valor[0], valor[1])
            elif operador == 'contains':
                return campo.contains(valor)
            elif operador == 'startswith':
                return campo.startswith(valor)
            elif operador == 'endswith':
                return campo.endswith(valor)
        except Exception as e:
            logger.error(f"[LOADER_EXECUTOR] Erro ao construir filtro: {e}")

        return None

    # NOTA: _aplicar_agregacao foi removida pois agregacao eh tratada em _construir_query

    def _executar_com_timeout(self, query, definicao: Dict) -> List[Dict]:
        """Executa query e formata resultado."""
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Query excedeu timeout")

        # Configura timeout (apenas em Unix)
        try:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.timeout)
        except (AttributeError, ValueError):
            pass  # Windows nao suporta SIGALRM

        try:
            # Executa query
            resultados = query.all()

            # Formata resultados
            dados = []
            campos_retorno = definicao.get('campos_retorno', [])
            tem_agregacao = bool(definicao.get('agregacao'))

            for row in resultados:
                # Se e um objeto ORM
                if hasattr(row, '__table__'):
                    item = self._serializar_objeto(row, campos_retorno)
                    dados.append(item)
                # Se e uma tupla ou Row (resultado de agregacao/JOIN)
                elif hasattr(row, '_asdict'):
                    # SQLAlchemy Row com _asdict
                    item = {}
                    row_dict = row._asdict()
                    for chave, val in row_dict.items():
                        item[chave] = self._serializar_valor(val)
                    dados.append(item)
                elif hasattr(row, '_fields'):
                    # NamedTuple
                    item = {}
                    for i, field in enumerate(row._fields):
                        item[field] = self._serializar_valor(row[i])
                    dados.append(item)
                elif isinstance(row, tuple):
                    item = {}
                    # Tenta obter nomes das colunas da agregacao
                    if tem_agregacao:
                        agregacao = definicao['agregacao']
                        campos_grupo = agregacao.get('por', [])
                        funcoes = agregacao.get('funcoes', [])

                        idx = 0
                        # Mapeia campos de grupo
                        for campo_nome in campos_grupo:
                            if idx < len(row):
                                item[campo_nome] = self._serializar_valor(row[idx])
                                idx += 1
                        # Mapeia funcoes de agregacao
                        for func_def in funcoes:
                            alias = func_def.get('alias', f"{func_def.get('func')}_{func_def.get('campo')}")
                            if idx < len(row):
                                item[alias] = self._serializar_valor(row[idx])
                                idx += 1
                    else:
                        # Fallback: nomes genericos
                        for i, val in enumerate(row):
                            if hasattr(val, '__table__'):
                                item.update(self._serializar_objeto(val, campos_retorno))
                            else:
                                item[f'valor_{i}'] = self._serializar_valor(val)
                    dados.append(item)
                else:
                    item = {'valor': self._serializar_valor(row)}
                    dados.append(item)

            return dados

        finally:
            # Remove timeout
            try:
                signal.alarm(0)
            except (AttributeError, ValueError):
                pass

    def _serializar_objeto(self, obj, campos_retorno: List[str] = None) -> Dict:
        """Serializa objeto ORM para dict."""
        resultado = {}

        # Se especificou campos, usa apenas esses
        if campos_retorno:
            for campo in campos_retorno:
                if hasattr(obj, campo):
                    resultado[campo] = self._serializar_valor(getattr(obj, campo))
        else:
            # Serializa todos os campos
            from sqlalchemy import inspect
            try:
                mapper = inspect(obj.__class__)
                for col in mapper.columns:
                    resultado[col.key] = self._serializar_valor(getattr(obj, col.key, None))
            except Exception:
                pass

        return resultado

    def _serializar_valor(self, valor) -> Any:
        """Serializa valor para JSON."""
        if valor is None:
            return None
        elif isinstance(valor, datetime):
            return valor.isoformat()
        elif isinstance(valor, Decimal):
            return float(valor)
        elif hasattr(valor, 'strftime'):  # date
            return valor.strftime('%Y-%m-%d')
        elif isinstance(valor, (int, float, str, bool)):
            return valor
        else:
            return str(valor)


# ============================================
# FUNCOES DE CONVENIENCIA
# ============================================

_executor: Optional[LoaderExecutor] = None


def get_executor() -> LoaderExecutor:
    """Retorna instancia singleton do executor."""
    global _executor
    if _executor is None:
        _executor = LoaderExecutor()
    return _executor


def executar_loader(definicao: Dict, parametros: Dict = None) -> Dict[str, Any]:
    """Funcao de conveniencia para executar loader."""
    return get_executor().executar(definicao, parametros)


def validar_definicao(definicao: Dict) -> Dict[str, Any]:
    """Funcao de conveniencia para validar definicao."""
    return get_executor()._validar_definicao(definicao)
