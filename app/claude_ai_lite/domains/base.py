"""
Interface base obrigatoria para todos os dominios.
Todo loader DEVE herdar desta classe.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseLoader(ABC):
    """
    Classe base para loaders de dominio.

    REGRAS:
    - Maximo 200 linhas no loader
    - Uma funcao principal: buscar()
    - Retorno SEMPRE padronizado
    """

    # Nome do dominio (sobrescrever)
    DOMINIO: str = ""

    # Campos de busca aceitos (sobrescrever)
    CAMPOS_BUSCA: List[str] = []

    @abstractmethod
    def buscar(self, valor: str, campo: str) -> Dict[str, Any]:
        """
        Busca dados no banco.

        Args:
            valor: Valor a buscar
            campo: Campo de busca (deve estar em CAMPOS_BUSCA)

        Returns:
            Dict padronizado:
            {
                "sucesso": bool,
                "valor_buscado": str,
                "campo_busca": str,
                "total_encontrado": int,
                "dados": [...],
                "erro": str (opcional)
            }
        """
        pass

    @abstractmethod
    def formatar_contexto(self, dados: Dict[str, Any]) -> str:
        """
        Formata os dados para enviar ao Claude como contexto.

        Args:
            dados: Resultado do buscar()

        Returns:
            String formatada para o prompt
        """
        pass

    def validar_campo(self, campo: str) -> bool:
        """Valida se campo de busca e aceito."""
        return campo in self.CAMPOS_BUSCA
