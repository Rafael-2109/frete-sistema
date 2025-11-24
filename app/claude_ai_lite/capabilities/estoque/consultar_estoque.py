"""
Capacidade: Consultar Estoque

Consulta estoque atual, projeção e análise de rupturas.
Reutiliza lógica do EstoqueLoader existente.
"""

from typing import Dict, Any
import logging

from ..base import BaseCapability

logger = logging.getLogger(__name__)


class ConsultarEstoqueCapability(BaseCapability):
    """Consulta estoque e rupturas."""

    NOME = "consultar_estoque"
    DOMINIO = "estoque"
    TIPO = "consulta"
    INTENCOES = ["consultar_estoque", "consultar_ruptura"]
    CAMPOS_BUSCA = ["cod_produto", "nome_produto", "ruptura"]
    DESCRICAO = "Consulta estoque atual, projeção e rupturas"
    EXEMPLOS = [
        "Qual o estoque de azeitona verde?",
        "Tem estoque de ketchup?",
        "Quais produtos vão dar ruptura?",
        "Projeção de estoque do pêssego",
        "Produtos com ruptura nos próximos 7 dias"
    ]

    def pode_processar(self, intencao: str, entidades: Dict) -> bool:
        """Processa consultas de estoque."""
        return intencao in self.INTENCOES

    def extrair_valor_busca(self, entidades: Dict) -> tuple:
        """Extrai valor de busca, tratando casos especiais."""
        # Para ruptura, não precisa de valor específico
        if entidades.get("_intencao") == "consultar_ruptura":
            return "ruptura", "7"

        # Mapeia 'produto' da classificação para 'nome_produto'
        if entidades.get("produto"):
            return "nome_produto", str(entidades["produto"])
        if entidades.get("cod_produto"):
            return "cod_produto", str(entidades["cod_produto"])

        return None, None

    def executar(self, entidades: Dict, contexto: Dict) -> Dict[str, Any]:
        """Delega para o loader existente."""
        from app.claude_ai_lite.domains.carteira.loaders.estoque import EstoqueLoader

        # Guarda intenção para extrair_valor_busca
        entidades["_intencao"] = contexto.get("intencao", "")

        campo, valor = self.extrair_valor_busca(entidades)

        # Se não tem campo mas a intenção é ruptura, busca rupturas
        if not campo and contexto.get("intencao") == "consultar_ruptura":
            campo, valor = "ruptura", "7"

        if not campo:
            return {"sucesso": False, "erro": "Produto não informado", "total_encontrado": 0}

        loader = EstoqueLoader()
        return loader.buscar(valor, campo, contexto)  # Passa contexto com filtros aprendidos

    def formatar_contexto(self, resultado: Dict[str, Any]) -> str:
        """Delega formatação para o loader existente."""
        from app.claude_ai_lite.domains.carteira.loaders.estoque import EstoqueLoader
        return EstoqueLoader().formatar_contexto(resultado)
