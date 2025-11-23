"""
Capacidade de Ação: Criar Separação

Gerencia o fluxo interativo de criação de separações:
- Criar rascunho
- Incluir/excluir itens
- Confirmar/cancelar

Delega para o módulo actions existente.
"""

from typing import Dict, Any
import logging

from ..base import BaseCapability

logger = logging.getLogger(__name__)


class CriarSeparacaoCapability(BaseCapability):
    """Ação de criar separações."""

    NOME = "criar_separacao"
    DOMINIO = "acao"
    TIPO = "acao"
    INTENCOES = [
        "criar_separacao",
        "separar_disponiveis",
        "escolher_opcao",
        "incluir_item",
        "excluir_item",
        "alterar_quantidade",
        "confirmar_acao",
        "cancelar",
        "ver_rascunho"
    ]
    CAMPOS_BUSCA = ["num_pedido", "opcao"]
    DESCRICAO = "Cria separações para pedidos"
    EXEMPLOS = [
        "Criar separação do pedido VCD123",
        "Opção A para o pedido VCD456",
        "Separar os itens disponíveis",
        "Incluir azeitona na separação",
        "Excluir ketchup",
        "Confirmar separação",
        "Cancelar"
    ]

    def pode_processar(self, intencao: str, entidades: Dict) -> bool:
        """Processa ações de separação."""
        return intencao in self.INTENCOES

    def executar(self, entidades: Dict, contexto: Dict) -> Dict[str, Any]:
        """
        Delega para o módulo de actions existente.

        Note: Esta capability retorna string direta, não o formato padrão.
        """
        from app.claude_ai_lite.actions import processar_acao_separacao

        intencao = contexto.get("intencao", "")
        usuario = contexto.get("usuario", "Claude AI")
        usuario_id = contexto.get("usuario_id")

        # Adiciona texto original se disponível
        if contexto.get("texto_original"):
            entidades["texto_original"] = contexto["texto_original"]

        # Chama o processador de ação existente
        resposta = processar_acao_separacao(
            intencao=intencao,
            entidades=entidades,
            usuario=usuario,
            usuario_id=usuario_id
        )

        # Retorna no formato esperado pelo orchestrator
        return {
            "sucesso": True,
            "total_encontrado": 1,
            "dados": {"resposta": resposta},
            "resposta_direta": resposta  # Flag para não passar pelo responder
        }

    def formatar_contexto(self, resultado: Dict[str, Any]) -> str:
        """Retorna a resposta direta da ação."""
        # Para ações, a resposta já vem formatada
        if resultado.get("resposta_direta"):
            return resultado["resposta_direta"]
        return resultado.get("dados", {}).get("resposta", "Ação processada.")
