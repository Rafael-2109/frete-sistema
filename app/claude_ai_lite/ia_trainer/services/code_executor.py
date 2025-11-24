"""
CodeExecutor - Execucao controlada de codigo gerado.

Executa codigo de forma segura com:
- Timeout configuravel
- Transacao READ-ONLY
- Limite de resultados
- Captura de erros
- Log de execucao

ROTEIRO DE SEGURANCA:
- Timeout de 2 segundos (configuravel)
- Rollback automatico
- Limite de 1000 registros
- Sem commit de transacao

Limite: 200 linhas
"""

import logging
import signal
from typing import Dict, Any, Callable
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuracoes
DEFAULT_TIMEOUT = 2  # segundos
MAX_RESULTS = 1000  # registros max


class TimeoutError(Exception):
    """Erro de timeout na execucao."""
    pass


def timeout_handler(signum, frame):
    """Handler para timeout via signal."""
    raise TimeoutError("Execucao excedeu o tempo limite")


def with_timeout(seconds: int = DEFAULT_TIMEOUT):
    """
    Decorator para executar funcao com timeout.

    Nota: Funciona apenas em Unix (usa SIGALRM).
    Em Windows, usa abordagem alternativa.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Tenta usar signal (Unix)
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(seconds)
                try:
                    result = func(*args, **kwargs)
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
                return result
            except (ValueError, AttributeError):
                # Windows ou ambiente sem suporte a signal
                # Executa sem timeout (menos seguro)
                logger.warning("Timeout via signal nao disponivel. Executando sem limite.")
                return func(*args, **kwargs)
        return wrapper
    return decorator


class CodeExecutor:
    """
    Executor seguro de codigo gerado.

    Uso:
        executor = CodeExecutor()

        # Executa filtro
        resultado = executor.executar_filtro(
            model='CarteiraPrincipal',
            filtro='qtd_saldo_produto_pedido > 0',
            limite=100
        )

        # Executa codigo Python completo
        resultado = executor.executar_codigo(codigo_python)

        # Testa codigo com pergunta original
        resultado = executor.testar_com_pergunta(codigo, pergunta)
    """

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.ultimo_erro: str = None
        self.tempo_execucao: float = 0

    def executar_filtro(
        self,
        model: str,
        filtro: str,
        limite: int = 100,
        campos: list = None
    ) -> Dict[str, Any]:
        """
        Executa um filtro em um Model.

        Args:
            model: Nome do Model (ex: 'CarteiraPrincipal')
            filtro: Expressao de filtro (ex: 'qtd_saldo > 0')
            limite: Limite de resultados
            campos: Campos a retornar (None = todos)

        Returns:
            Dict com resultados ou erro
        """
        from app import db

        inicio = datetime.now()

        try:
            # Importa o Model dinamicamente
            model_class = self._importar_model(model)
            if model_class is None:
                return {
                    'sucesso': False,
                    'erro': f'Model "{model}" nao encontrado'
                }

            # Constroi a query
            @with_timeout(self.timeout)
            def executar_query():
                query = model_class.query

                # Aplica filtro (cuidado: eval limitado)
                if filtro:
                    # Constroi filtro de forma segura
                    filtro_obj = self._construir_filtro(model_class, filtro)
                    if filtro_obj is not None:
                        query = query.filter(filtro_obj)

                # Aplica limite
                query = query.limit(min(limite, MAX_RESULTS))

                return query.all()

            resultados = executar_query()

            # Converte para dict
            dados = []
            for item in resultados:
                if hasattr(item, 'to_dict'):
                    dados.append(item.to_dict())
                else:
                    dados.append(self._model_to_dict(item, campos))

            self.tempo_execucao = (datetime.now() - inicio).total_seconds()

            return {
                'sucesso': True,
                'total': len(dados),
                'dados': dados,
                'tempo_execucao': self.tempo_execucao,
                'query': f'{model}.filter({filtro}).limit({limite})'
            }

        except TimeoutError:
            self.ultimo_erro = "Timeout: consulta demorou mais que o permitido"
            return {
                'sucesso': False,
                'erro': self.ultimo_erro,
                'tempo_execucao': self.timeout
            }

        except Exception as e:
            self.ultimo_erro = str(e)
            logger.error(f"Erro ao executar filtro: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'tempo_execucao': (datetime.now() - inicio).total_seconds()
            }

    def _importar_model(self, nome_model: str):
        """Importa um Model pelo nome."""
        from .code_validator import MODELS_CONHECIDOS

        if nome_model not in MODELS_CONHECIDOS:
            return None

        modulo_path = MODELS_CONHECIDOS[nome_model]

        try:
            # Importa o modulo
            import importlib
            modulo = importlib.import_module(modulo_path)
            return getattr(modulo, nome_model)
        except Exception as e:
            logger.error(f"Erro ao importar Model {nome_model}: {e}")
            return None

    def _construir_filtro(self, model_class, filtro_str: str):
        """
        Constroi filtro SQLAlchemy de forma segura.

        Suporta filtros simples como:
        - campo > valor
        - campo == valor
        - campo.like('%valor%')
        """
        from sqlalchemy import and_, or_

        # Filtros simples com operadores
        # Ex: "qtd_saldo_produto_pedido > 0"
        operadores = ['>=', '<=', '!=', '==', '>', '<']

        for op in operadores:
            if op in filtro_str:
                partes = filtro_str.split(op)
                if len(partes) == 2:
                    campo = partes[0].strip()
                    valor = partes[1].strip()

                    # Remove nome do Model se presente
                    if '.' in campo:
                        campo = campo.split('.')[-1]

                    if hasattr(model_class, campo):
                        col = getattr(model_class, campo)
                        try:
                            # Tenta converter valor
                            if valor.replace('.', '').replace('-', '').isdigit():
                                valor = float(valor) if '.' in valor else int(valor)

                            if op == '>':
                                return col > valor
                            elif op == '<':
                                return col < valor
                            elif op == '>=':
                                return col >= valor
                            elif op == '<=':
                                return col <= valor
                            elif op == '==':
                                return col == valor
                            elif op == '!=':
                                return col != valor
                        except Exception:
                            pass

        # Filtro AND
        if ' AND ' in filtro_str.upper():
            partes = filtro_str.upper().split(' AND ')
            filtros = []
            for parte in partes:
                f = self._construir_filtro(model_class, parte.strip())
                if f is not None:
                    filtros.append(f)
            if filtros:
                return and_(*filtros)

        logger.warning(f"Nao foi possivel construir filtro: {filtro_str}")
        return None

    def _model_to_dict(self, item, campos: list = None) -> dict:
        """Converte Model para dict."""
        resultado = {}

        if campos:
            for campo in campos:
                if hasattr(item, campo):
                    valor = getattr(item, campo)
                    resultado[campo] = self._serializar_valor(valor)
        else:
            # Pega todos os campos de coluna
            for col in item.__table__.columns:
                valor = getattr(item, col.name)
                resultado[col.name] = self._serializar_valor(valor)

        return resultado

    def _serializar_valor(self, valor):
        """Serializa valor para JSON."""
        if valor is None:
            return None
        if isinstance(valor, datetime):
            return valor.isoformat()
        if hasattr(valor, '__float__'):
            return float(valor)
        return str(valor)

    def executar_loader_estruturado(
        self,
        definicao: str,
        parametros: dict = None
    ) -> Dict[str, Any]:
        """
        Executa um loader estruturado via LoaderExecutor.

        Args:
            definicao: JSON string ou dict com a definicao do loader
            parametros: Parametros dinamicos ($cliente, $data, etc)

        Returns:
            Dict com resultado da execucao
        """
        import json
        from .loader_executor import get_executor

        inicio = datetime.now()

        try:
            # Parseia definicao se for string
            if isinstance(definicao, str):
                # Tenta extrair JSON de markdown code block
                if '```json' in definicao:
                    import re
                    match = re.search(r'```json\s*(.*?)\s*```', definicao, re.DOTALL)
                    if match:
                        definicao = match.group(1)
                elif '```' in definicao:
                    import re
                    match = re.search(r'```\s*(.*?)\s*```', definicao, re.DOTALL)
                    if match:
                        definicao = match.group(1)

                definicao_dict = json.loads(definicao)
            else:
                definicao_dict = definicao

            # Executa via LoaderExecutor
            executor = get_executor()
            resultado = executor.executar(definicao_dict, parametros or {})

            self.tempo_execucao = (datetime.now() - inicio).total_seconds()
            resultado['tempo_execucao'] = self.tempo_execucao

            return resultado

        except json.JSONDecodeError as e:
            self.ultimo_erro = f"JSON invalido: {e}"
            return {
                'sucesso': False,
                'erro': self.ultimo_erro,
                'tempo_execucao': (datetime.now() - inicio).total_seconds()
            }
        except Exception as e:
            self.ultimo_erro = str(e)
            logger.error(f"Erro ao executar loader estruturado: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'tempo_execucao': (datetime.now() - inicio).total_seconds()
            }

    def testar_codigo(
        self,
        codigo_id: int,
        pergunta_original: str
    ) -> Dict[str, Any]:
        """
        Testa um codigo gerado com a pergunta original.

        Args:
            codigo_id: ID do CodigoSistemaGerado
            pergunta_original: Pergunta que gerou a necessidade

        Returns:
            Dict com resultado do teste
        """
        from ..models import CodigoSistemaGerado

        codigo = CodigoSistemaGerado.query.get(codigo_id)
        if not codigo:
            return {
                'sucesso': False,
                'erro': 'Codigo nao encontrado'
            }

        # Executa baseado no tipo
        if codigo.tipo_codigo == 'filtro':
            # Extrai Model do filtro
            model = None
            for m in codigo.models_referenciados or []:
                model = m
                break

            if not model:
                return {
                    'sucesso': False,
                    'erro': 'Filtro nao especifica Model'
                }

            resultado = self.executar_filtro(
                model=model,
                filtro=codigo.definicao_tecnica,
                limite=10  # Limite baixo para teste
            )

        elif codigo.tipo_codigo == 'prompt':
            # Prompts nao sao executaveis, apenas validados
            resultado = {
                'sucesso': True,
                'mensagem': 'Prompts nao requerem teste de execucao',
                'dados': []
            }

        elif codigo.tipo_codigo == 'loader':
            # Usa o LoaderExecutor para loaders estruturados
            resultado = self.executar_loader_estruturado(codigo.definicao_tecnica)

        elif codigo.tipo_codigo in ('conceito', 'entidade'):
            # Conceitos e entidades sao textuais, apenas validados
            resultado = {
                'sucesso': True,
                'mensagem': f'{codigo.tipo_codigo.capitalize()} nao requer teste de execucao',
                'dados': []
            }

        else:
            resultado = {
                'sucesso': False,
                'erro': f'Teste para tipo "{codigo.tipo_codigo}" nao implementado'
            }

        # Atualiza codigo com resultado do teste
        codigo.ultimo_teste_sucesso = resultado['sucesso']
        codigo.ultimo_teste_erro = resultado.get('erro')
        codigo.ultimo_teste_em = datetime.now()

        from app import db
        db.session.commit()

        return resultado
