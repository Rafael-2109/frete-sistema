"""
Base para todas as Capacidades do Claude AI Lite.

Uma Capacidade é uma unidade auto-registrável que:
- Define suas intenções (quando deve ser ativada)
- Define seus campos de busca
- Executa a lógica de negócio
- Formata a resposta
- Aplica filtros aprendidos pelo IA Trainer

Limite: 150 linhas
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class BaseCapability(ABC):
    """
    Contrato base para todas as capacidades.

    Cada capacidade DEVE definir:
    - NOME: identificador único
    - DOMINIO: categoria (carteira, estoque, fretes, etc)
    - INTENCOES: lista de intenções que ativam esta capacidade
    - DESCRICAO: descrição curta para o classificador
    - EXEMPLOS: exemplos de uso para o prompt de classificação

    NOVO: Suporta aplicação de filtros aprendidos via IA Trainer.
    """

    # === METADADOS (sobrescrever em cada capacidade) ===
    NOME: str = ""                      # Ex: "consultar_pedido"
    DOMINIO: str = ""                   # Ex: "carteira"
    TIPO: str = "consulta"              # "consulta" ou "acao"
    INTENCOES: List[str] = []           # Ex: ["consultar_status", "buscar_pedido"]
    CAMPOS_BUSCA: List[str] = []        # Ex: ["num_pedido", "cnpj_cpf"]
    DESCRICAO: str = ""                 # Ex: "Consulta status de pedidos"
    EXEMPLOS: List[str] = []            # Ex: ["Pedido VCD123?", "Status do pedido X"]

    # === MÉTODOS OBRIGATÓRIOS ===

    def pode_processar(self, intencao: str, entidades: Dict) -> bool:
        """
        Verifica se esta capacidade deve processar a requisição.

        Override para lógica customizada. Default: verifica se intenção está na lista.
        """
        return intencao in self.INTENCOES

    @abstractmethod
    def executar(self, entidades: Dict, contexto: Dict) -> Dict[str, Any]:
        """
        Executa a capacidade.

        Args:
            entidades: Entidades extraídas (num_pedido, cliente, etc)
            contexto: Contexto adicional (usuario_id, usuario_nome, etc)

        Returns:
            Dict padronizado:
            {
                "sucesso": bool,
                "dados": Any,
                "total_encontrado": int,
                "mensagem": str (opcional),
                "erro": str (opcional)
            }
        """
        pass

    @abstractmethod
    def formatar_contexto(self, resultado: Dict[str, Any]) -> str:
        """
        Formata o resultado para enviar ao Claude como contexto.

        Args:
            resultado: Retorno do executar()

        Returns:
            String formatada para o prompt
        """
        pass

    # === MÉTODOS AUXILIARES ===

    def extrair_valor_busca(self, entidades: Dict) -> tuple:
        """
        Extrai campo e valor de busca das entidades.

        Returns:
            Tupla (campo, valor) ou (None, None)
        """
        for campo in self.CAMPOS_BUSCA:
            valor = entidades.get(campo)
            if valor and str(valor).lower() not in ("null", "none", ""):
                return campo, str(valor)
        return None, None

    def extrair_todos_valores_busca(self, entidades: Dict) -> Dict[str, str]:
        """
        Extrai TODOS os campos de busca presentes nas entidades.
        
        Diferente de extrair_valor_busca que retorna apenas o primeiro,
        este método retorna todos os campos válidos para filtros combinados.
        
        Returns:
            Dict com {campo: valor} para todos os campos com valor válido
        """
        resultado = {}
        for campo in self.CAMPOS_BUSCA:
            valor = entidades.get(campo)
            if valor and str(valor).lower() not in ("null", "none", ""):
                resultado[campo] = str(valor)
        return resultado

    def validar_campo(self, campo: str) -> bool:
        """Valida se campo de busca é aceito."""
        return campo in self.CAMPOS_BUSCA

    def aplicar_filtros_aprendidos(self, query, contexto: Dict, modelo_classe=None):
        """
        Aplica filtros aprendidos pelo IA Trainer E filtros compostos extraídos à query.

        Suporta dois formatos de filtro:
        1. Filtro SQL (antigo): {"filtro": "campo = valor", "nome": "..."}
        2. Filtro estruturado (novo): {"campo": "x", "operador": "==", "valor": "y"}

        Args:
            query: Query SQLAlchemy em construção
            contexto: Contexto com 'filtros_aprendidos'
            modelo_classe: Classe do modelo (opcional, para validação)

        Returns:
            Query com filtros aplicados

        Uso na capacidade:
            query = CarteiraPrincipal.query
            query = self.aplicar_filtros_aprendidos(query, contexto, CarteiraPrincipal)
        """
        filtros = contexto.get('filtros_aprendidos', [])

        if not filtros:
            return query

        from sqlalchemy import text

        for filtro in filtros:
            try:
                # Valida se o modelo é compatível
                modelo_esperado = filtro.get('modelo')
                if modelo_esperado and modelo_classe:
                    nome_modelo = modelo_classe.__name__
                    if modelo_esperado != nome_modelo:
                        logger.debug(f"[FILTRO] Ignorando filtro para {modelo_esperado} (query usa {nome_modelo})")
                        continue

                # FORMATO 1: Filtro SQL direto (IA Trainer antigo)
                filtro_sql = filtro.get('filtro')
                if filtro_sql:
                    query = query.filter(text(filtro_sql))
                    logger.info(f"[FILTRO] SQL aplicado: {filtro.get('nome')} -> {filtro_sql[:50]}...")
                    continue

                # FORMATO 2: Filtro estruturado (CompositeExtractor)
                campo = filtro.get('campo')
                operador = filtro.get('operador')
                valor = filtro.get('valor')

                if campo and operador and modelo_classe:
                    # Obtém coluna do modelo
                    if hasattr(modelo_classe, campo):
                        coluna = getattr(modelo_classe, campo)
                        query = self._aplicar_filtro_estruturado(query, coluna, operador, valor, campo)
                        logger.info(f"[FILTRO] Estruturado aplicado: {campo} {operador} {valor}")

            except Exception as e:
                nome_filtro = filtro.get('nome', filtro.get('campo', 'desconhecido'))
                logger.error(f"[FILTRO] Erro ao aplicar filtro '{nome_filtro}': {e}")
                # Propaga erro - melhor falhar do que retornar dados incorretos
                raise ValueError(f"Filtro '{nome_filtro}' falhou: {e}")

        return query

    def _aplicar_filtro_estruturado(self, query, coluna, operador: str, valor, campo_nome: str):
        """
        Aplica filtro estruturado à query.

        Args:
            query: Query SQLAlchemy
            coluna: Coluna do modelo
            operador: Operador (==, is_null, >, etc)
            valor: Valor para comparação
            campo_nome: Nome do campo (para logs)

        Returns:
            Query com filtro aplicado
        """
        if operador == 'is_null':
            return query.filter(coluna.is_(None))
        elif operador == 'is_not_null':
            return query.filter(coluna.isnot(None))
        elif operador == '==':
            return query.filter(coluna == valor)
        elif operador == '!=':
            return query.filter(coluna != valor)
        elif operador == '>':
            return query.filter(coluna > valor)
        elif operador == '>=':
            return query.filter(coluna >= valor)
        elif operador == '<':
            return query.filter(coluna < valor)
        elif operador == '<=':
            return query.filter(coluna <= valor)
        elif operador == 'ilike':
            return query.filter(coluna.ilike(f'%{valor}%'))
        elif operador == 'like':
            return query.filter(coluna.like(f'%{valor}%'))
        elif operador == 'in':
            return query.filter(coluna.in_(valor))
        elif operador == 'between' and isinstance(valor, list) and len(valor) == 2:
            return query.filter(coluna.between(valor[0], valor[1]))
        else:
            logger.warning(f"[FILTRO] Operador não suportado: {operador}")
            return query

    def __repr__(self):
        return f"<{self.__class__.__name__} nome={self.NOME} dominio={self.DOMINIO}>"
