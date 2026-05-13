"""Service de Divergencias (stub minimo - sera expandido no Plano 3).

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md S2.1, S7
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md Task 11

Este stub implementa apenas `criar_divergencia` para que finalizar_carregamento
Fase 7 (Plano 2) funcione antes do Plano 3 (Divergencias completo) ser implementado.

Plano 3 vai expandir esse arquivo com:
- listar_divergencias (filtros)
- resolver_divergencia (com tipos: CANCELAR_NF, CCE, ALTERAR_CARREGAMENTO,
  SUBSTITUIR_CHASSI, IGNORAR)
- automacao de fluxo
"""
from app import db
from app.motos_assai.models import AssaiDivergencia
from app.utils.json_helpers import sanitize_for_json
from app.utils.timezone import agora_brasil_naive


class DivergenciaError(Exception):
    """Erro base de divergencia_service."""


def criar_divergencia(tipo, chassi, nf_id=None, sep_id=None, car_id=None, detalhes=None):
    """Cria uma divergencia centralizada (AssaiDivergencia).

    Args:
        tipo: str - DIVERGENCIA_TIPO_* (validos em DIVERGENCIA_TIPOS_VALIDOS).
        chassi: str | None - chassi associado (pode ser None para alguns tipos).
        nf_id: int | None - id da NF (AssaiNfQpa) associada (pode ser None).
        sep_id: int | None - id da separacao (AssaiSeparacao) associada.
        car_id: int | None - id do carregamento (AssaiCarregamento) associado.
        detalhes: dict | None - JSON com detalhes adicionais (origem, fluxo, etc).

    Returns:
        AssaiDivergencia criada (NAO commitada — caller commita).

    Note:
        sanitize_for_json e usado para garantir que detalhes nao tem
        Decimals/datetimes/UUIDs nao serializaveis.
    """
    div = AssaiDivergencia(
        tipo=tipo,
        chassi=chassi,
        nf_id=nf_id,
        separacao_id=sep_id,
        carregamento_id=car_id,
        detalhes=sanitize_for_json(detalhes or {}),
        criada_em=agora_brasil_naive(),
    )
    db.session.add(div)
    db.session.flush()
    return div
