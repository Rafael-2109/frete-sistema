"""Service de Divergencias (Fase 4 - Plano 3).

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md S2.1, S7
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase4-nf-divergencias.md Tasks 1-2

Funcoes:
- criar_divergencia: insert em assai_divergencia (NAO commita - caller decide)
- resolver_divergencia: marca como resolvida + re-roda _calcular_match (S21=a + A14)
"""
from app import db
from app.motos_assai.models import (
    AssaiDivergencia, AssaiNfQpa,
    DIVERGENCIA_TIPOS_VALIDOS, DIVERGENCIA_RESOLUCAO_VALIDAS,
    DIVERGENCIA_RESOLUCAO_IGNORAR, DIVERGENCIA_RESOLUCAO_CANCELAR_NF,
    DIVERGENCIA_RESOLUCAO_CCE, DIVERGENCIA_RESOLUCAO_ALTERAR_CARREGAMENTO,
    DIVERGENCIA_RESOLUCAO_SUBSTITUIR_CHASSI,
    NF_STATUS_CANCELADA,
)
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
        AssaiDivergencia criada (NAO commitada - caller commita).

    Raises:
        DivergenciaError: tipo invalido.

    Note:
        N-B2 fix: sanitize_for_json garante que detalhes nao tem
        Decimals/datetimes/UUIDs nao serializaveis.
    """
    if tipo not in DIVERGENCIA_TIPOS_VALIDOS:
        raise DivergenciaError(
            f'tipo invalido: {tipo}. Validos: {sorted(DIVERGENCIA_TIPOS_VALIDOS)}'
        )

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


def resolver_divergencia(div_id, tipo_resolucao, observacao, operador_id):
    """Marca divergencia como resolvida + re-roda _calcular_match (S21=a + A14).

    Args:
        div_id: ID da AssaiDivergencia
        tipo_resolucao: deve estar em DIVERGENCIA_RESOLUCAO_VALIDAS
        observacao: texto explicativo (obrigatorio se tipo=IGNORAR)
        operador_id: usuario que resolveu

    Raises:
        DivergenciaError: divergencia ja resolvida ou tipo_resolucao invalido

    Note:
        S21=a: re-rodar _calcular_match na NF associada (se houver).
        A14: idempotencia - NAO re-roda se NF esta CANCELADA.
        NAO commita - caller decide.
    """
    if tipo_resolucao not in DIVERGENCIA_RESOLUCAO_VALIDAS:
        raise DivergenciaError(
            f'tipo_resolucao invalido: {tipo_resolucao}. '
            f'Validos: {sorted(DIVERGENCIA_RESOLUCAO_VALIDAS)}'
        )

    div = AssaiDivergencia.query.get(div_id)
    if not div:
        raise DivergenciaError(f'Divergencia {div_id} nao encontrada')
    if div.resolvida_em is not None:
        raise DivergenciaError(f'Divergencia {div_id} ja resolvida em {div.resolvida_em}')

    if tipo_resolucao == DIVERGENCIA_RESOLUCAO_IGNORAR:
        if not observacao or not observacao.strip():
            raise DivergenciaError('Observacao obrigatoria para resolucao IGNORAR')

    div.resolvida_em = agora_brasil_naive()
    div.resolvida_por_id = operador_id
    div.tipo_resolucao = tipo_resolucao
    div.observacao_resolucao = observacao

    # S21=a: re-rodar _calcular_match na NF associada
    # A14: idempotencia - NAO re-roda se NF esta CANCELADA
    if div.nf_id:
        nf = AssaiNfQpa.query.get(div.nf_id)
        if nf and nf.status_match != NF_STATUS_CANCELADA:
            _calcular_match(nf, operador_id)

    db.session.flush()
    return div


def _calcular_match(nf, operador_id):
    """Wrapper para `nf_qpa_adapter._calcular_match` (evita import circular).

    Lazy import para nao depender adapter no momento de import do service.
    """
    from app.motos_assai.services.parsers.nf_qpa_adapter import _calcular_match as adapter_calc
    adapter_calc(nf, operador_id)
