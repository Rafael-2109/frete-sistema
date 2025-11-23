"""
Base para todas as Capacidades do Claude AI Lite.

Uma Capacidade é uma unidade auto-registrável que:
- Define suas intenções (quando deve ser ativada)
- Define seus campos de busca
- Executa a lógica de negócio
- Formata a resposta

Limite: 100 linhas
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseCapability(ABC):
    """
    Contrato base para todas as capacidades.

    Cada capacidade DEVE definir:
    - NOME: identificador único
    - DOMINIO: categoria (carteira, estoque, fretes, etc)
    - INTENCOES: lista de intenções que ativam esta capacidade
    - DESCRICAO: descrição curta para o classificador
    - EXEMPLOS: exemplos de uso para o prompt de classificação
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

    def validar_campo(self, campo: str) -> bool:
        """Valida se campo de busca é aceito."""
        return campo in self.CAMPOS_BUSCA

    def __repr__(self):
        return f"<{self.__class__.__name__} nome={self.NOME} dominio={self.DOMINIO}>"
