"""
Capacidade: Analisar Gargalos

Identifica produtos que travam pedidos por falta de estoque.
Reutiliza lógica do GargalosLoader existente.
"""

from typing import Dict, Any
import logging

from ..base import BaseCapability

logger = logging.getLogger(__name__)


class AnalisarGargalosCapability(BaseCapability):
    """Identifica gargalos de estoque."""

    NOME = "analisar_gargalos"
    DOMINIO = "carteira"
    TIPO = "consulta"
    INTENCOES = ["analisar_gargalo"]
    CAMPOS_BUSCA = ["num_pedido", "geral", "cod_produto"]
    DESCRICAO = "Identifica produtos que travam pedidos por falta de estoque"
    EXEMPLOS = [
        "O que está travando o pedido VCD123?",
        "Quais produtos são gargalo?",
        "Por que não consigo enviar o VCD456?",
        "Qual o impacto da azeitona nos pedidos?"
    ]

    def pode_processar(self, intencao: str, entidades: Dict) -> bool:
        """Processa se for análise de gargalo."""
        return intencao == "analisar_gargalo"

    def extrair_valor_busca(self, entidades: Dict) -> tuple:
        """Extrai valor de busca."""
        if entidades.get("num_pedido"):
            return "num_pedido", str(entidades["num_pedido"])
        if entidades.get("cod_produto"):
            return "cod_produto", str(entidades["cod_produto"])
        # Se não especificou, faz análise geral
        return "geral", "geral"

    def executar(self, entidades: Dict, contexto: Dict) -> Dict[str, Any]:
        """Delega para o loader existente."""
        from app.claude_ai_lite.domains.carteira.loaders.gargalos import GargalosLoader

        campo, valor = self.extrair_valor_busca(entidades)
        loader = GargalosLoader()
        return loader.buscar(valor, campo, contexto)  # Passa contexto com filtros aprendidos

    def formatar_contexto(self, resultado: Dict[str, Any]) -> str:
        """Delega formatação para o loader existente."""
        from app.claude_ai_lite.domains.carteira.loaders.gargalos import GargalosLoader
        return GargalosLoader().formatar_contexto(resultado)
