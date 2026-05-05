"""Leitura de pedidos no TagPlus (GET /pedidos/{id}).

Usado pelo backfill de enriquecimento de venda. Requer scope `read:pedidos`
(adicionado em 2026-05-01 — verificar via tagplus_checklist se token vigente
ainda esta com scope antigo, caso em que admin precisa reautorizar OAuth).

Campos uteis no payload do pedido (testado em producao 2026-05-01):
  - vendedor.nome           -> HoraVenda.vendedor
  - departamento.descricao  -> HoraVenda.tagplus_departamento (loja fisica)
  - faturas[].forma_pagamento.id -> mapeia via HoraTagPlusFormaPagamentoMap
  - cliente.razao_social / cpf
  - itens[].produto_servico.codigo
  - observacoes (texto livre, pode ter chassi como fallback)
  - data_entrega
"""
from __future__ import annotations

import logging
from typing import Optional

from app.hora.services.tagplus.api_client import ApiClient

logger = logging.getLogger(__name__)


class PedidoTagPlusError(Exception):
    """Falha generica ao consultar pedido TagPlus."""


class ScopeInsuficienteError(PedidoTagPlusError):
    """GET /pedidos/{id} retornou 401 — scope read:pedidos ausente.

    Solucao: admin precisa reautorizar OAuth em /hora/tagplus/conta/oauth
    com scope_contratado contendo `read:pedidos read:vendas`. Refresh_token
    NAO re-emite scope (RFC OAuth2).
    """


class PedidoNaoEncontrado(PedidoTagPlusError):
    """GET /pedidos/{id} retornou 404 ou similar."""


def importar_pedido(api: ApiClient, pedido_id: int) -> dict:
    """GET /pedidos/{pedido_id} -> dict bruto do TagPlus.

    Args:
        api: ApiClient autenticado.
        pedido_id: ID do pedido no TagPlus (vem em
            nfe.pedido_os_vinculada.id no GET /nfes/{id}).

    Returns:
        dict com chaves: id, numero, status, data_criacao, data_confirmacao,
        cliente{}, vendedor{}, departamento{}, valor_total, itens[],
        faturas[], observacoes, data_entrega.

    Raises:
        ScopeInsuficienteError: 401 (scope read:pedidos ausente no token).
        PedidoNaoEncontrado: 404.
        PedidoTagPlusError: outros erros HTTP.
    """
    r = api.get(f'/pedidos/{pedido_id}')
    if r.status_code == 401:
        raise ScopeInsuficienteError(
            f'GET /pedidos/{pedido_id} retornou 401: '
            'scope read:pedidos ausente no token vigente. '
            'Reautorizar OAuth em /hora/tagplus/conta/oauth.'
        )
    if r.status_code == 404:
        raise PedidoNaoEncontrado(
            f'Pedido TagPlus {pedido_id} nao encontrado (404).'
        )
    if r.status_code != 200:
        raise PedidoTagPlusError(
            f'GET /pedidos/{pedido_id} retornou {r.status_code}: {r.text[:300]}'
        )
    try:
        return r.json()
    except ValueError as exc:
        raise PedidoTagPlusError(
            f'Resposta nao-JSON em /pedidos/{pedido_id}: {exc}'
        )


def extrair_vendedor_nome(pedido: dict) -> Optional[str]:
    """vendedor.nome -> string ou None.

    TagPlus pode retornar vendedor=None ou {nome: null} para pedidos
    sem vendedor associado (raros em producao mas possivel).
    """
    vend = pedido.get('vendedor') or {}
    if not isinstance(vend, dict):
        return None
    nome = vend.get('nome')
    if not nome or not isinstance(nome, str):
        return None
    return nome.strip()[:100] or None


def extrair_departamento_descricao(pedido: dict) -> Optional[str]:
    """departamento.descricao -> string ou None.

    departamento e a LOJA FISICA (REGRA FISCAL HORA: cnpj_emitente sempre
    matriz, departamento identifica filial real).
    """
    dep = pedido.get('departamento') or {}
    if not isinstance(dep, dict):
        return None
    desc = dep.get('descricao')
    if not desc or not isinstance(desc, str):
        return None
    return desc.strip()[:100] or None


def extrair_forma_pagamento_id(pedido: dict) -> Optional[int]:
    """faturas[0].forma_pagamento.id -> int ou None.

    Pega a primeira fatura (vendas multi-fatura sao raras em B2C HORA).
    Esse ID casa com HoraTagPlusFormaPagamentoMap.tagplus_forma_id ja
    cadastrado no sistema (mapa criado para emissao de NFe).
    """
    faturas = pedido.get('faturas') or []
    if not isinstance(faturas, list) or not faturas:
        return None
    primeira = faturas[0]
    if not isinstance(primeira, dict):
        return None
    fp = primeira.get('forma_pagamento') or {}
    if not isinstance(fp, dict):
        return None
    fp_id = fp.get('id')
    if not isinstance(fp_id, int):
        return None
    return fp_id


def normalizar_departamento(raw: Optional[str]) -> Optional[str]:
    """Normaliza string para chave UNIQUE em hora_tagplus_departamento_map.

    lowercase + remove acentos + strip + colapsa espacos.
    """
    if not raw:
        return None
    import unicodedata
    s = unicodedata.normalize('NFKD', raw)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.lower().strip()
    s = ' '.join(s.split())
    return s[:200] or None
