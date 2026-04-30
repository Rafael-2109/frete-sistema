"""Service de empréstimo de moto entre nossa loja HORA e loja externa.

Operações:
  criar_emprestimo(...)         -> cria registro EM_ABERTO + emite evento
                                   EMPRESTIMO_SAIDA ou EMPRESTIMO_ENTRADA
                                   no chassi correspondente.
  ressarcir_emprestimo(...)     -> fecha EM_ABERTO -> RESSARCIDO; emite
                                   evento RESSARCIMENTO_* no chassi oposto.
                                   Modelo do chassi de ressarcimento DEVE
                                   bater com o do emprestimo.
  cancelar_emprestimo(...)      -> EM_ABERTO -> CANCELADO. Reverte o
                                   evento original com DEVOLVIDA.
  listar_emprestimos(...)       -> filtros + paginacao.

Regras:
  * 1 emprestimo = 1 moto.
  * `chassi_saida` e `chassi_entrada` sao do MESMO modelo (validado).
  * Chassi nao pode estar em outro emprestimo EM_ABERTO simultaneamente.
  * Para SAIDA, o chassi a sair deve estar EM_ESTOQUE na loja_hora_id.
"""
from __future__ import annotations

from datetime import date
from typing import Iterable, Optional

from app import db
from app.hora.models import (
    HoraEmprestimoMoto, HoraLoja, HoraModelo, HoraMoto,
    EMPRESTIMO_TIPO_SAIDA, EMPRESTIMO_TIPO_ENTRADA,
    EMPRESTIMO_STATUS_EM_ABERTO, EMPRESTIMO_STATUS_RESSARCIDO,
    EMPRESTIMO_STATUS_CANCELADO,
)
from app.hora.services.estoque_service import EVENTOS_EM_ESTOQUE
from app.hora.services.moto_service import (
    get_or_create_moto, registrar_evento, ultimo_evento,
)
from app.utils.timezone import agora_utc_naive


class EmprestimoError(Exception):
    """Erro de negocio em operacao de emprestimo."""


def _validar_loja_hora(loja_hora_id: int) -> HoraLoja:
    loja = HoraLoja.query.get(loja_hora_id)
    if not loja or not loja.ativa:
        raise EmprestimoError(f'Loja HORA {loja_hora_id} nao encontrada ou inativa.')
    return loja


def _validar_modelo(modelo_id: int) -> HoraModelo:
    modelo = HoraModelo.query.get(modelo_id)
    if not modelo:
        raise EmprestimoError(f'Modelo {modelo_id} nao encontrado.')
    return modelo


def _normalizar_chassi(c: Optional[str]) -> Optional[str]:
    if not c:
        return None
    cn = c.strip().upper()
    return cn or None


def _normalizar_cnpj(c: Optional[str]) -> Optional[str]:
    if not c:
        return None
    digitos = ''.join(d for d in c if d.isdigit())
    return digitos[:20] or None


def _chassi_em_emprestimo_aberto(chassi: str) -> Optional[HoraEmprestimoMoto]:
    """Retorna emprestimo EM_ABERTO que envolve este chassi (saida ou entrada)."""
    return (
        HoraEmprestimoMoto.query
        .filter(HoraEmprestimoMoto.status == EMPRESTIMO_STATUS_EM_ABERTO)
        .filter(
            (HoraEmprestimoMoto.chassi_saida == chassi)
            | (HoraEmprestimoMoto.chassi_entrada == chassi)
        )
        .first()
    )


# ---------------------------------------------------------------------
# CRIAR
# ---------------------------------------------------------------------

def criar_emprestimo(
    tipo: str,
    loja_hora_id: int,
    loja_externa_nome: str,
    modelo_id: int,
    data_emprestimo: date,
    chassi: str,
    loja_externa_cnpj: Optional[str] = None,
    observacoes: Optional[str] = None,
    operador: Optional[str] = None,
) -> HoraEmprestimoMoto:
    """Cria emprestimo EM_ABERTO + emite evento adequado no chassi.

    Args:
        tipo: 'SAIDA' (nossa loja -> externa) ou 'ENTRADA' (externa -> nossa).
        chassi: chassi da moto. Em SAIDA, deve existir e estar em estoque
            na loja_hora_id. Em ENTRADA, sera cadastrada em hora_moto se
            ainda nao existir.
    """
    if tipo not in (EMPRESTIMO_TIPO_SAIDA, EMPRESTIMO_TIPO_ENTRADA):
        raise EmprestimoError(f'tipo invalido: {tipo!r}')

    loja = _validar_loja_hora(loja_hora_id)
    modelo = _validar_modelo(modelo_id)

    nome_externa = (loja_externa_nome or '').strip()
    if not nome_externa:
        raise EmprestimoError('Nome da loja externa eh obrigatorio.')
    nome_externa = nome_externa[:200]

    chassi_norm = _normalizar_chassi(chassi)
    if not chassi_norm:
        raise EmprestimoError('Chassi obrigatorio.')
    if len(chassi_norm) > 30:
        raise EmprestimoError(f'Chassi excede 30 chars: {chassi_norm!r}')

    aberto = _chassi_em_emprestimo_aberto(chassi_norm)
    if aberto:
        raise EmprestimoError(
            f'Chassi {chassi_norm} ja esta em emprestimo aberto #{aberto.id}.'
        )

    if tipo == EMPRESTIMO_TIPO_SAIDA:
        # Chassi precisa existir, ser do modelo correto, estar em estoque
        # na loja_hora_id.
        moto = HoraMoto.query.get(chassi_norm)
        if not moto:
            raise EmprestimoError(
                f'Chassi {chassi_norm} nao cadastrado em hora_moto. '
                f'Em SAIDA, a moto deve existir no nosso estoque.'
            )
        if moto.modelo_id != modelo.id:
            raise EmprestimoError(
                f'Chassi {chassi_norm} eh do modelo "{moto.modelo.nome_modelo}" '
                f'mas o emprestimo e do modelo "{modelo.nome_modelo}".'
            )
        ult = ultimo_evento(chassi_norm)
        if ult is None or ult.tipo not in EVENTOS_EM_ESTOQUE:
            raise EmprestimoError(
                f'Chassi {chassi_norm} nao esta em estoque '
                f'(ultimo evento: {ult.tipo if ult else "nenhum"}).'
            )
        if ult.loja_id and ult.loja_id != loja_hora_id:
            raise EmprestimoError(
                f'Chassi {chassi_norm} esta na loja_id={ult.loja_id}, '
                f'mas emprestimo SAIDA e da loja_id={loja_hora_id}.'
            )
        chassi_saida = chassi_norm
        chassi_entrada = None
        evento_tipo = 'EMPRESTIMO_SAIDA'
        detalhe_evt = (
            f'Emprestimo SAIDA #X para "{nome_externa}" — moto sai do estoque '
            f'(aguardando ressarcimento de outra moto do modelo '
            f'{modelo.nome_modelo}).'
        )
    else:
        # ENTRADA: cria/usa moto com este chassi vinculada ao modelo.
        moto = HoraMoto.query.get(chassi_norm)
        if moto and moto.modelo_id != modelo.id:
            raise EmprestimoError(
                f'Chassi {chassi_norm} ja existe vinculado ao modelo '
                f'"{moto.modelo.nome_modelo}", incompativel com '
                f'"{modelo.nome_modelo}".'
            )
        if not moto:
            moto = get_or_create_moto(
                numero_chassi=chassi_norm,
                modelo_nome=modelo.nome_modelo,
                cor='NAO_INFORMADA',
                criado_por=operador,
            )
        chassi_saida = None
        chassi_entrada = chassi_norm
        evento_tipo = 'EMPRESTIMO_ENTRADA'
        detalhe_evt = (
            f'Emprestimo ENTRADA #X de "{nome_externa}" — moto entra no estoque '
            f'(compromisso de ressarcir com outra moto do modelo '
            f'{modelo.nome_modelo}).'
        )

    emp = HoraEmprestimoMoto(
        tipo=tipo,
        status=EMPRESTIMO_STATUS_EM_ABERTO,
        loja_hora_id=loja.id,
        loja_externa_nome=nome_externa,
        loja_externa_cnpj=_normalizar_cnpj(loja_externa_cnpj),
        modelo_id=modelo.id,
        chassi_saida=chassi_saida,
        chassi_entrada=chassi_entrada,
        data_emprestimo=data_emprestimo,
        observacoes=(observacoes or '').strip() or None,
        criado_por=operador,
    )
    db.session.add(emp)
    db.session.flush()

    registrar_evento(
        numero_chassi=chassi_norm,
        tipo=evento_tipo,
        origem_tabela='hora_emprestimo_moto',
        origem_id=emp.id,
        loja_id=loja.id,
        operador=operador,
        detalhe=detalhe_evt.replace('#X', f'#{emp.id}'),
    )

    db.session.commit()
    return emp


# ---------------------------------------------------------------------
# RESSARCIR
# ---------------------------------------------------------------------

def ressarcir_emprestimo(
    emprestimo_id: int,
    chassi_ressarcimento: str,
    data_ressarcimento: date,
    operador: Optional[str] = None,
    observacoes_extra: Optional[str] = None,
) -> HoraEmprestimoMoto:
    """Fecha emprestimo EM_ABERTO emitindo evento RESSARCIMENTO_* no chassi
    oposto. Modelo do chassi de ressarcimento DEVE bater com modelo_id.
    """
    emp = HoraEmprestimoMoto.query.get(emprestimo_id)
    if not emp:
        raise EmprestimoError(f'Emprestimo #{emprestimo_id} nao encontrado.')
    if emp.status != EMPRESTIMO_STATUS_EM_ABERTO:
        raise EmprestimoError(
            f'Emprestimo #{emprestimo_id} esta {emp.status}, nao pode ressarcir.'
        )

    chassi_norm = _normalizar_chassi(chassi_ressarcimento)
    if not chassi_norm:
        raise EmprestimoError('Chassi de ressarcimento obrigatorio.')

    aberto_outro = _chassi_em_emprestimo_aberto(chassi_norm)
    if aberto_outro and aberto_outro.id != emp.id:
        raise EmprestimoError(
            f'Chassi {chassi_norm} ja esta em emprestimo aberto '
            f'#{aberto_outro.id} — nao pode ser usado em ressarcimento.'
        )

    if emp.tipo == EMPRESTIMO_TIPO_SAIDA:
        # Operador esta enviando UMA NOVA moto vinda da externa para fechar.
        # chassi_norm entra no estoque (cria moto se nao existe).
        moto = HoraMoto.query.get(chassi_norm)
        if moto and moto.modelo_id != emp.modelo_id:
            raise EmprestimoError(
                f'Chassi {chassi_norm} eh modelo "{moto.modelo.nome_modelo}", '
                f'mas o emprestimo e do modelo "{emp.modelo.nome_modelo}".'
            )
        if not moto:
            moto = get_or_create_moto(
                numero_chassi=chassi_norm,
                modelo_nome=emp.modelo.nome_modelo,
                cor='NAO_INFORMADA',
                criado_por=operador,
            )
        emp.chassi_entrada = chassi_norm
        evento_tipo = 'RESSARCIMENTO_SAIDA'
        detalhe = (
            f'Ressarcimento de SAIDA #{emp.id} — chassi {chassi_norm} entra no '
            f'estoque (vindo de "{emp.loja_externa_nome}").'
        )
    else:
        # ENTRADA: vamos enviar UMA NOSSA moto para fechar.
        moto = HoraMoto.query.get(chassi_norm)
        if not moto:
            raise EmprestimoError(
                f'Chassi {chassi_norm} nao cadastrado. Para ressarcir ENTRADA, '
                f'envie um chassi nosso ja existente.'
            )
        if moto.modelo_id != emp.modelo_id:
            raise EmprestimoError(
                f'Chassi {chassi_norm} eh modelo "{moto.modelo.nome_modelo}", '
                f'mas o emprestimo e do modelo "{emp.modelo.nome_modelo}".'
            )
        ult = ultimo_evento(chassi_norm)
        if ult is None or ult.tipo not in EVENTOS_EM_ESTOQUE:
            raise EmprestimoError(
                f'Chassi {chassi_norm} nao esta em estoque '
                f'(ultimo evento: {ult.tipo if ult else "nenhum"}).'
            )
        if ult.loja_id and ult.loja_id != emp.loja_hora_id:
            raise EmprestimoError(
                f'Chassi {chassi_norm} esta na loja {ult.loja_id}, '
                f'emprestimo eh da loja {emp.loja_hora_id}.'
            )
        emp.chassi_saida = chassi_norm
        evento_tipo = 'RESSARCIMENTO_ENTRADA'
        detalhe = (
            f'Ressarcimento de ENTRADA #{emp.id} — chassi {chassi_norm} sai do '
            f'estoque (devolvido a "{emp.loja_externa_nome}").'
        )

    emp.status = EMPRESTIMO_STATUS_RESSARCIDO
    emp.data_ressarcimento = data_ressarcimento
    emp.ressarcido_em = agora_utc_naive()
    emp.ressarcido_por = operador
    if observacoes_extra:
        sufixo = f'\n[Ressarcimento {data_ressarcimento.isoformat()}]: {observacoes_extra.strip()}'
        emp.observacoes = (emp.observacoes or '') + sufixo

    registrar_evento(
        numero_chassi=chassi_norm,
        tipo=evento_tipo,
        origem_tabela='hora_emprestimo_moto',
        origem_id=emp.id,
        loja_id=emp.loja_hora_id,
        operador=operador,
        detalhe=detalhe,
    )

    db.session.commit()
    return emp


# ---------------------------------------------------------------------
# CANCELAR
# ---------------------------------------------------------------------

def cancelar_emprestimo(
    emprestimo_id: int,
    motivo: str,
    operador: Optional[str] = None,
) -> HoraEmprestimoMoto:
    """Cancela emprestimo EM_ABERTO. Reverte o evento original emitindo
    DEVOLVIDA no chassi original (chassi_saida em SAIDA / chassi_entrada
    em ENTRADA).
    """
    motivo_l = (motivo or '').strip()
    if len(motivo_l) < 3:
        raise EmprestimoError('Motivo de cancelamento obrigatorio (>= 3 chars).')

    emp = HoraEmprestimoMoto.query.get(emprestimo_id)
    if not emp:
        raise EmprestimoError(f'Emprestimo #{emprestimo_id} nao encontrado.')
    if emp.status != EMPRESTIMO_STATUS_EM_ABERTO:
        raise EmprestimoError(
            f'Emprestimo #{emprestimo_id} esta {emp.status}, nao pode cancelar.'
        )

    if emp.tipo == EMPRESTIMO_TIPO_SAIDA:
        # Chassi nosso volta ao estoque.
        chassi_a_devolver = emp.chassi_saida
        detalhe = (
            f'Cancelamento de emprestimo SAIDA #{emp.id} — chassi volta ao estoque. '
            f'Motivo: {motivo_l[:200]}'
        )
    else:
        # Chassi externo sai do nosso estoque.
        chassi_a_devolver = emp.chassi_entrada
        detalhe = (
            f'Cancelamento de emprestimo ENTRADA #{emp.id} — chassi externo '
            f'devolvido. Motivo: {motivo_l[:200]}'
        )

    emp.status = EMPRESTIMO_STATUS_CANCELADO
    emp.cancelado_em = agora_utc_naive()
    emp.cancelado_por = operador
    emp.cancelamento_motivo = motivo_l[:1000]

    if chassi_a_devolver:
        registrar_evento(
            numero_chassi=chassi_a_devolver,
            tipo='DEVOLVIDA',
            origem_tabela='hora_emprestimo_moto',
            origem_id=emp.id,
            loja_id=emp.loja_hora_id,
            operador=operador,
            detalhe=detalhe,
        )

    db.session.commit()
    return emp


# ---------------------------------------------------------------------
# CONSULTAS
# ---------------------------------------------------------------------

def emprestimo_aberto_por_chassi(chassi: str) -> Optional[HoraEmprestimoMoto]:
    """Retorna emprestimo EM_ABERTO envolvendo o chassi, se houver."""
    chassi_norm = _normalizar_chassi(chassi)
    if not chassi_norm:
        return None
    return _chassi_em_emprestimo_aberto(chassi_norm)


def paginar_emprestimos(
    page: int = 1,
    per_page: int = 50,
    lojas_permitidas_ids: Optional[Iterable[int]] = None,
    status: Optional[str] = None,
    tipo: Optional[str] = None,
):
    """Pagina emprestimos respeitando escopo de loja."""
    page = max(1, int(page or 1))
    per_page = max(1, min(int(per_page or 50), 200))

    query = HoraEmprestimoMoto.query.order_by(
        HoraEmprestimoMoto.data_emprestimo.desc(),
        HoraEmprestimoMoto.id.desc(),
    )
    if status:
        query = query.filter(HoraEmprestimoMoto.status == status)
    if tipo:
        query = query.filter(HoraEmprestimoMoto.tipo == tipo)
    if lojas_permitidas_ids is not None:
        ids_list = list(lojas_permitidas_ids)
        if not ids_list:
            return None
        query = query.filter(HoraEmprestimoMoto.loja_hora_id.in_(ids_list))

    return query.paginate(page=page, per_page=per_page, error_out=False)


__all__ = [
    'EmprestimoError',
    'criar_emprestimo',
    'ressarcir_emprestimo',
    'cancelar_emprestimo',
    'emprestimo_aberto_por_chassi',
    'paginar_emprestimos',
]
