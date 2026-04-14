"""
CarviaConfigService — Acesso a parametros globais do modulo CarVia
"""

import logging
from typing import Optional

from app import db

logger = logging.getLogger(__name__)


class CarviaConfigService:
    """Gerencia parametros chave-valor do modulo CarVia"""

    @staticmethod
    def get(chave: str, default: Optional[str] = None) -> Optional[str]:
        """Busca valor de uma config por chave. Retorna default se nao existir."""
        from app.carvia.models import CarviaConfig
        config = CarviaConfig.query.filter_by(chave=chave).first()
        if config:
            return config.valor
        return default

    @staticmethod
    def get_float(chave: str, default: float = 0.0) -> float:
        """Busca valor numerico de uma config."""
        valor = CarviaConfigService.get(chave)
        if valor is None:
            return default
        try:
            return float(valor)
        except (ValueError, TypeError):
            logger.warning("Config '%s' tem valor nao numerico: %s", chave, valor)
            return default

    @staticmethod
    def get_int(chave: str, default: int = 0) -> int:
        """Busca valor inteiro de uma config."""
        valor = CarviaConfigService.get(chave)
        if valor is None:
            return default
        try:
            return int(float(valor))
        except (ValueError, TypeError):
            logger.warning("Config '%s' tem valor nao inteiro: %s", chave, valor)
            return default

    @staticmethod
    def get_bool(chave: str, default: bool = False) -> bool:
        """Busca valor booleano de uma config."""
        valor = CarviaConfigService.get(chave)
        if valor is None:
            return default
        return valor.lower() in ('true', '1', 'sim', 'yes')

    @staticmethod
    def set(chave: str, valor: str, descricao: Optional[str] = None,
            atualizado_por: str = 'sistema') -> None:
        """Cria ou atualiza uma config."""
        from app.carvia.models import CarviaConfig
        from app.utils.timezone import agora_utc_naive

        config = CarviaConfig.query.filter_by(chave=chave).first()
        if config:
            config.valor = valor
            if descricao is not None:
                config.descricao = descricao
            config.atualizado_por = atualizado_por
            config.atualizado_em = agora_utc_naive()
        else:
            config = CarviaConfig(
                chave=chave,
                valor=valor,
                descricao=descricao,
                atualizado_por=atualizado_por,
                atualizado_em=agora_utc_naive(),
            )
            db.session.add(config)

        db.session.flush()

    @staticmethod
    def listar_todas() -> list:
        """Lista todas as configs ordenadas por chave."""
        from app.carvia.models import CarviaConfig
        return CarviaConfig.query.order_by(CarviaConfig.chave.asc()).all()

    @staticmethod
    def deletar(chave: str) -> bool:
        """Remove uma config. Retorna True se existia."""
        from app.carvia.models import CarviaConfig
        config = CarviaConfig.query.filter_by(chave=chave).first()
        if config:
            db.session.delete(config)
            db.session.flush()
            return True
        return False

    # --- Atalhos para configs conhecidas ---

    @staticmethod
    def limite_desconto_percentual() -> float:
        """Retorna limite de desconto que Jessica pode aprovar sem admin."""
        return CarviaConfigService.get_float('limite_desconto_percentual', 5.0)

    @staticmethod
    def exigir_aprovacao_admin() -> bool:
        """Toggle global: quando False, pula o check PENDENTE_ADMIN."""
        return CarviaConfigService.get_bool('exigir_aprovacao_admin', True)
