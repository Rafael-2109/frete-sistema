"""
Interface base obrigatoria para todos os dominios.
Todo loader DEVE herdar desta classe.

Suporta filtros aprendidos pelo IA Trainer via contexto opcional.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class BaseLoader(ABC):
    """
    Classe base para loaders de dominio.

    REGRAS:
    - Maximo 200 linhas no loader
    - Uma funcao principal: buscar()
    - Retorno SEMPRE padronizado

    NOVO: Suporta filtros aprendidos via contexto opcional.
    """

    # Nome do dominio (sobrescrever)
    DOMINIO: str = ""

    # Campos de busca aceitos (sobrescrever)
    CAMPOS_BUSCA: List[str] = []

    @abstractmethod
    def buscar(self, valor: str, campo: str, contexto: Dict = None) -> Dict[str, Any]:
        """
        Busca dados no banco.

        Args:
            valor: Valor a buscar
            campo: Campo de busca (deve estar em CAMPOS_BUSCA)
            contexto: Contexto opcional com filtros_aprendidos (NOVO)

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

    def aplicar_filtros_aprendidos(self, query, contexto: Dict = None, modelo_classe=None):
        """
        Aplica filtros aprendidos pelo IA Trainer à query.

        Args:
            query: Query SQLAlchemy em construção
            contexto: Contexto com 'filtros_aprendidos'
            modelo_classe: Classe do modelo (opcional, para validação)

        Returns:
            Query com filtros aplicados
        """
        if not contexto:
            return query

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

                # Aplica o filtro
                filtro_sql = filtro.get('filtro')
                if filtro_sql:
                    query = query.filter(text(filtro_sql))
                    logger.info(f"[FILTRO] Loader aplicou: {filtro.get('nome')} -> {filtro_sql[:50]}...")

            except Exception as e:
                logger.warning(f"[FILTRO] Erro ao aplicar filtro {filtro.get('nome')}: {e}")

        return query
