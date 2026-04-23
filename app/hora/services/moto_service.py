"""Helpers para `HoraMoto` (identidade imutável) + `HoraMotoEvento` (log).

Invariante 3: `HoraMoto` é insert-once. Só criamos uma linha; nunca fazemos UPDATE.
Invariante 4: estado atual consulta `HoraMotoEvento`, não UPDATE em `HoraMoto`.
"""
from __future__ import annotations

from typing import Optional

from app import db
from app.hora.models import HoraMoto, HoraMotoEvento
from app.hora.services.cadastro_service import buscar_ou_criar_modelo


def get_or_create_moto(
    numero_chassi: str,
    modelo_nome: Optional[str],
    cor: str,
    numero_motor: Optional[str] = None,
    ano_modelo: Optional[int] = None,
    criado_por: Optional[str] = None,
) -> HoraMoto:
    """Get-or-create respeitando o invariante insert-once.

    Se moto já existe, retorna sem alterar. Se não, cria com os atributos
    imutáveis. Diferenças entre o que já está na base e o que veio na nova
    fonte (ex.: cor diferente na NF vs pedido) NÃO atualizam a linha — elas
    devem virar conferência de divergência no momento do recebimento.
    """
    numero_chassi_norm = numero_chassi.strip().upper()
    if not numero_chassi_norm:
        raise ValueError("numero_chassi obrigatório")
    if len(numero_chassi_norm) > 30:
        raise ValueError(f"chassi excede 30 chars: {numero_chassi_norm}")

    existente = HoraMoto.query.get(numero_chassi_norm)
    if existente:
        return existente

    modelo = buscar_ou_criar_modelo(modelo_nome or 'MODELO_DESCONHECIDO')

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
