"""
Capacidade: Consultar Produto

Busca produtos na carteira e separações.
Reutiliza lógica do ProdutosLoader existente.
"""

from typing import Dict, Any
import logging

from ..base import BaseCapability

logger = logging.getLogger(__name__)


class ConsultarProdutoCapability(BaseCapability):
    """Consulta produtos na carteira."""

    NOME = "consultar_produto"
    DOMINIO = "carteira"
    TIPO = "consulta"
    INTENCOES = ["buscar_produto"]
    CAMPOS_BUSCA = ["nome_produto", "cod_produto"]
    DESCRICAO = "Busca produtos na carteira por nome ou código"
    EXEMPLOS = [
        "Tem azeitona na carteira?",
        "Qual a situação do ketchup?",
        "Produto 12345 está na carteira?",
        "Quanto de pêssego está separado?"
    ]

    def pode_processar(self, intencao: str, entidades: Dict) -> bool:
        """Processa se for busca de produto."""
        if intencao == "buscar_produto":
            return True
        # Também processa se tiver produto/cod_produto sem num_pedido
        if (entidades.get("produto") or entidades.get("cod_produto")) and not entidades.get("num_pedido"):
            return True
        return False

    def extrair_valor_busca(self, entidades: Dict) -> tuple:
        """Extrai valor de busca, mapeando 'produto' para 'nome_produto'."""
        # Mapeia 'produto' da classificação para 'nome_produto' do campo
        if entidades.get("produto"):
            return "nome_produto", str(entidades["produto"])
        if entidades.get("cod_produto"):
            return "cod_produto", str(entidades["cod_produto"])
        return None, None

    def executar(self, entidades: Dict, contexto: Dict) -> Dict[str, Any]:
        """Delega para o loader existente."""
        # Reutiliza lógica existente do ProdutosLoader
        from app.claude_ai_lite.domains.carteira.loaders.produtos import ProdutosLoader

        campo, valor = self.extrair_valor_busca(entidades)
        if not campo or not valor:
            return {"sucesso": False, "erro": "Produto não informado", "total_encontrado": 0}

        loader = ProdutosLoader()
        return loader.buscar(valor, campo)

    def formatar_contexto(self, resultado: Dict[str, Any]) -> str:
        """Delega formatação para o loader existente."""
        from app.claude_ai_lite.domains.carteira.loaders.produtos import ProdutosLoader
        return ProdutosLoader().formatar_contexto(resultado)
