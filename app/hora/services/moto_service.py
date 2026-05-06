"""Helpers para `HoraMoto` (identidade imutável) + `HoraMotoEvento` (log).

Invariante 3: `HoraMoto` é insert-once. Só criamos uma linha; nunca fazemos UPDATE.
Invariante 4: estado atual consulta `HoraMotoEvento`, não UPDATE em `HoraMoto`.
"""
from __future__ import annotations

from typing import Optional

from app import db
from app.hora.models import HoraMoto, HoraMotoEvento


def get_or_create_moto(
    numero_chassi: str,
    modelo_nome: Optional[str],
    cor: str,
    numero_motor: Optional[str] = None,
    ano_modelo: Optional[int] = None,
    criado_por: Optional[str] = None,
    *,
    origem_pendencia: Optional[str] = None,
    origem_id: Optional[int] = None,
    tagplus_codigo: Optional[str] = None,
    tagplus_produto_id: Optional[str] = None,
    pendenciar: bool = True,
) -> HoraMoto:
    """Get-or-create respeitando o invariante insert-once.

    Se moto já existe, retorna sem alterar. Se não, cria com os atributos
    imutáveis. Diferenças entre o que já está na base e o que veio na nova
    fonte (ex.: cor diferente na NF vs pedido) NÃO atualizam a linha — elas
    devem virar conferência de divergência no momento do recebimento.

    Resolucao de modelo (migration hora_29):
        Usa `modelo_resolver_service.resolver_ou_pendenciar` para mapear
        `modelo_nome` -> HoraModelo canonico via aliases.

        Se modelo NAO resolver:
          - Se pendenciar=True (default): registra pendencia e levanta
            `ModeloPendenteError`. Chamador trata (NAO cria HoraMoto sem
            modelo — invariante 3 exige modelo_id NOT NULL).
          - Se pendenciar=False: levanta ValueError direto sem pendencia
            (callsites que ja gerenciam divergencia fora deste service).

    Args:
        origem_pendencia: PENDENTE_ORIGEM_* (qual fluxo disparou). Default
            None faz cair em NF_ENTRADA (fluxo mais comum).
        origem_id: id da entidade que disparou (venda, NF, pedido).
        tagplus_codigo / tagplus_produto_id: pistas TagPlus para resolver.
        pendenciar: True cria pendencia + raise; False raise sem pendencia.

    Raises:
        ModeloPendenteError: modelo nao resolvido + pendencia criada.
        ValueError: chassi invalido OU pendenciar=False com modelo nao resolvido.
    """
    from app.hora.models import PENDENTE_ORIGEM_NF_ENTRADA
    from app.hora.services.modelo_resolver_service import (
        ModeloPendenteError,
        resolver_ou_pendenciar,
    )

    numero_chassi_norm = numero_chassi.strip().upper()
    if not numero_chassi_norm:
        raise ValueError("numero_chassi obrigatório")
    if len(numero_chassi_norm) > 30:
        raise ValueError(f"chassi excede 30 chars: {numero_chassi_norm}")

    existente = HoraMoto.query.get(numero_chassi_norm)
    if existente:
        return existente

    # Resolve modelo via aliases. Se nao encontrar, cria pendencia (ou
    # raise ValueError quando pendenciar=False).
    modelo, pendente = resolver_ou_pendenciar(
        modelo_nome,
        origem=(origem_pendencia or PENDENTE_ORIGEM_NF_ENTRADA),
        origem_id=origem_id,
        tagplus_codigo=tagplus_codigo,
        tagplus_produto_id=tagplus_produto_id,
    )
    if modelo is None:
        if pendenciar and pendente is not None:
            raise ModeloPendenteError(pendente)
        raise ValueError(
            f'Modelo {modelo_nome!r} nao reconhecido e pendencia desativada.'
        )

    moto = HoraMoto(
        numero_chassi=numero_chassi_norm,
        modelo_id=modelo.id,
        cor=(cor or 'NAO_INFORMADA').strip().upper(),
        numero_motor=(numero_motor or None),
        ano_modelo=ano_modelo,
        criado_por=criado_por,
    )
    db.session.add(moto)
    db.session.flush()
    return moto


def registrar_evento(
    numero_chassi: str,
    tipo: str,
    origem_tabela: Optional[str] = None,
    origem_id: Optional[int] = None,
    loja_id: Optional[int] = None,
    operador: Optional[str] = None,
    detalhe: Optional[str] = None,
) -> HoraMotoEvento:
    """Registra transição em `hora_moto_evento`. Append-only."""
    TIPOS_VALIDOS = {
        'RECEBIDA', 'CONFERIDA', 'TRANSFERIDA',
        'EM_TRANSITO', 'CANCELADA',
        'RESERVADA', 'VENDIDA', 'DEVOLVIDA', 'AVARIADA',
        'FALTANDO_PECA',
        # Emprestimo entre lojas (nossa HORA <-> loja externa).
        # EMPRESTIMO_SAIDA: chassi nosso saiu para loja externa (fora estoque).
        # EMPRESTIMO_ENTRADA: chassi externo entrou no nosso estoque.
        # RESSARCIMENTO_*: ao fechar, complementa com chassi do mesmo modelo.
        'EMPRESTIMO_SAIDA', 'EMPRESTIMO_ENTRADA',
        'RESSARCIMENTO_SAIDA', 'RESSARCIMENTO_ENTRADA',
    }
    if tipo not in TIPOS_VALIDOS:
        raise ValueError(f"Tipo de evento inválido: {tipo}. Aceitos: {TIPOS_VALIDOS}")

    evento = HoraMotoEvento(
        numero_chassi=numero_chassi.strip().upper(),
        tipo=tipo,
        origem_tabela=origem_tabela,
        origem_id=origem_id,
        loja_id=loja_id,
        operador=operador,
        detalhe=detalhe,
    )
    db.session.add(evento)
    db.session.flush()
    return evento


def ultimo_evento(numero_chassi: str) -> Optional[HoraMotoEvento]:
    """Estado atual da moto = último evento (invariante 4)."""
    return (
        HoraMotoEvento.query
        .filter_by(numero_chassi=numero_chassi.strip().upper())
        .order_by(HoraMotoEvento.timestamp.desc())
        .first()
    )


def status_atual(numero_chassi: str) -> Optional[str]:
    """Retorna o tipo do último evento (ou None se moto nunca foi movimentada)."""
    ult = ultimo_evento(numero_chassi)
    return ult.tipo if ult else None
