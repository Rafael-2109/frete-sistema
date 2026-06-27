"""Filtros e escopo de loja da seção Gerencial HORA.

Lógica PURA (sem `current_user`) para ser testável e reusada pelos services de
KPI. A resolução do escopo (`lojas_permitidas_ids()` do usuário) acontece na
rota; aqui recebemos a lista já resolvida (`None` = irrestrito; `[ids]` = restrito).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.utils.timezone import agora_brasil_naive

GRANULARIDADES_VALIDAS = ('dia', 'semana', 'mes')


def _parse_data(valor, default: date) -> date:
    if not valor:
        return default
    try:
        return date.fromisoformat(str(valor).strip())
    except (ValueError, AttributeError):
        return default


def lojas_efetivas(
    loja_id: Optional[int], lojas_permitidas: Optional[list[int]]
) -> Optional[list[int]]:
    """Interseção do filtro de loja com o escopo permitido.

    - `loja_id=None`: usa o escopo inteiro (`None` = irrestrito = todas;
      `[ids]` = restrito).
    - `loja_id` específico: `[loja_id]` se permitido (ou se irrestrito); `[]` se
      estiver fora do escopo (bloqueia tudo — nunca escapa do escopo via param).
    """
    if loja_id is None:
        return lojas_permitidas
    if lojas_permitidas is None:
        return [loja_id]
    if loja_id in lojas_permitidas:
        return [loja_id]
    return []


@dataclass
class Filtros:
    """Parâmetros resolvidos de um dashboard/relatório gerencial."""
    data_ini: date
    data_fim: date
    granularidade: str
    loja_id: Optional[int]
    lojas_permitidas: Optional[list[int]] = None

    @property
    def lojas(self) -> Optional[list[int]]:
        """Lista de loja_id a aplicar no WHERE (`None` = sem filtro = todas)."""
        return lojas_efetivas(self.loja_id, self.lojas_permitidas)

    @property
    def inclui_bucket_sem_loja(self) -> bool:
        """Bucket `loja_id IS NULL` (CNPJ desconhecido) só p/ acesso irrestrito
        e sem filtro de loja específico."""
        return self.lojas_permitidas is None and self.loja_id is None


def parse_filtros(args, lojas_permitidas: Optional[list[int]] = None) -> Filtros:
    """Parseia `request.args` (ou dict) em `Filtros`.

    Default de período = mês corrente (1º dia → hoje, horário Brasil).
    Granularidade inválida cai para 'dia'. `loja_id` vazio/'0' = todas.
    """
    hoje = agora_brasil_naive().date()
    data_ini = _parse_data(args.get('data_ini'), hoje.replace(day=1))
    data_fim = _parse_data(args.get('data_fim'), hoje)
    gran = (args.get('granularidade') or 'dia').strip().lower()
    if gran not in GRANULARIDADES_VALIDAS:
        gran = 'dia'
    loja_raw = args.get('loja_id')
    try:
        loja_id = int(loja_raw) if loja_raw not in (None, '', '0') else None
    except (ValueError, TypeError):
        loja_id = None
    return Filtros(
        data_ini=data_ini, data_fim=data_fim, granularidade=gran,
        loja_id=loja_id, lojas_permitidas=lojas_permitidas,
    )
