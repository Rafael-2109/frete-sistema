"""
Capacidade: Consultar Rota

Busca pedidos por rota, sub-rota ou UF.
Reutiliza lógica do RotasLoader existente.
"""

from typing import Dict, Any
import logging

from ..base import BaseCapability

logger = logging.getLogger(__name__)


class ConsultarRotaCapability(BaseCapability):
    """Consulta pedidos por rota, sub-rota ou UF."""

    NOME = "consultar_rota"
    DOMINIO = "carteira"
    TIPO = "consulta"
    INTENCOES = ["buscar_rota", "buscar_uf"]
    CAMPOS_BUSCA = ["rota", "sub_rota", "cod_uf"]
    DESCRICAO = "Busca pedidos por rota, sub-rota ou UF"
    EXEMPLOS = [
        "Pedidos na rota MG",
        "O que tem na rota NE?",
        "Pedidos da rota B",
        "O que tem pra sub-rota CAP?",
        "Pedidos para São Paulo",
        "O que tem para MG?"
    ]

    def pode_processar(self, intencao: str, entidades: Dict) -> bool:
        """Processa se for busca por rota/UF."""
        if intencao in self.INTENCOES:
            return True
        if entidades.get("rota") or entidades.get("sub_rota") or entidades.get("uf"):
            return True
        return False

    def extrair_valor_busca(self, entidades: Dict) -> tuple:
        """Extrai valor de busca, mapeando 'uf' para 'cod_uf'."""
        if entidades.get("rota"):
            return "rota", str(entidades["rota"])
        if entidades.get("sub_rota"):
            return "sub_rota", str(entidades["sub_rota"])
        if entidades.get("uf"):
            return "cod_uf", str(entidades["uf"])
        return None, None

    def executar(self, entidades: Dict, contexto: Dict) -> Dict[str, Any]:
        """Delega para o loader existente."""
        from app.claude_ai_lite.domains.carteira.loaders.rotas import RotasLoader

        campo, valor = self.extrair_valor_busca(entidades)
        if not campo or not valor:
            return {"sucesso": False, "erro": "Rota/UF não informada", "total_encontrado": 0}

        loader = RotasLoader()
        return loader.buscar(valor, campo)

    def formatar_contexto(self, resultado: Dict[str, Any]) -> str:
        """Delega formatação para o loader existente."""
        from app.claude_ai_lite.domains.carteira.loaders.rotas import RotasLoader
        return RotasLoader().formatar_contexto(resultado)
