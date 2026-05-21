"""Service de devolucao por NF de venda Q.P.A.

Cliente (Sendas/Assai) emite NF de devolucao (NFd) para 1+ chassis de uma NF
Q.P.A. de venda ja FATURADA. Cada chassi devolvido:
  1. Recebe novo evento PENDENTE (volta ao estoque para conserto)
  2. Observacao do evento: "Moto devolvida - {motivo}"
  3. AssaiNfQpaItem.devolvido=True (+ devolvido_em/devolucao_item_id).
     recalcular_status_pedido EXCLUI o AssaiSeparacaoItem.id ligado
     (via nf_item.separacao_item_id) da contagem qtd_faturada, restituindo
     o saldo do MODELO ao pedido de vendas.
  4. NF original NAO e cancelada (devolucao parcial e legitima).

Idempotencia: UNIQUE (nf_qpa_origem_id, numero_nfd).
Anexos: S3 com rollback do arquivo se commit DB falhar.
"""

from __future__ import annotations

from datetime import date
from typing import Iterable, Optional, Dict, Any, List

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app import db
from app.motos_assai.models import (
    AssaiDevolucaoNfd, AssaiDevolucaoItem, AssaiDevolucaoAnexo,
    AssaiNfQpa, AssaiNfQpaItem,
    AssaiMoto, AssaiModelo,
    AssaiMotoEvento,
    EVENTO_PENDENTE, EVENTO_FATURADA, EVENTO_PENDENCIA_RESOLVIDA,
    DEVOLUCAO_ANEXO_TIPO_PDF, DEVOLUCAO_ANEXO_TIPO_XML,
    DEVOLUCAO_ANEXO_TIPO_IMAGEM, DEVOLUCAO_ANEXO_TIPO_OUTRO,
)
from app.motos_assai.services.moto_evento_service import (
    emitir_evento, status_efetivo,
)
from app.utils.file_storage import get_file_storage
from app.utils.timezone import agora_brasil_naive


class DevolucaoValidationError(Exception):
    """Erro de validacao em devolucao_service."""


EXTENSOES_PDF = {'pdf'}
EXTENSOES_XML = {'xml'}
EXTENSOES_IMAGEM = {'png', 'jpg', 'jpeg'}
EXTENSOES_PERMITIDAS = EXTENSOES_PDF | EXTENSOES_XML | EXTENSOES_IMAGEM


def detectar_tipo_anexo(filename: str) -> str:
    """Mapeia extensao -> categoria do anexo (PDF / XML / IMAGEM / OUTRO)."""
    if not filename or '.' not in filename:
        return DEVOLUCAO_ANEXO_TIPO_OUTRO
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext in EXTENSOES_PDF:
        return DEVOLUCAO_ANEXO_TIPO_PDF
    if ext in EXTENSOES_XML:
        return DEVOLUCAO_ANEXO_TIPO_XML
    if ext in EXTENSOES_IMAGEM:
        return DEVOLUCAO_ANEXO_TIPO_IMAGEM
    return DEVOLUCAO_ANEXO_TIPO_OUTRO


def _medir_tamanho_stream(arquivo) -> Optional[int]:
    """Mede tamanho do stream do upload sem consumir o cursor.

    Padrao identico a pos_venda_service._medir_tamanho_stream — Werkzeug
    `FileStorage.content_length` retorna 0 para uploads multipart individuais.
    """
    stream = getattr(arquivo, 'stream', arquivo)
    try:
        pos = stream.tell()
        stream.seek(0, 2)  # EOF
        size = stream.tell()
        stream.seek(pos)
        return int(size) if size else None
    except (OSError, AttributeError):
        return None


# ----- Criacao da devolucao --------------------------------------------------

def criar_devolucao(
    *,
    nf_id: int,
    numero_nfd: str,
    data_devolucao: date,
    motivo: str,
    chassis: Iterable[str],
    anexos: Optional[Iterable] = None,  # iterable de werkzeug FileStorage
    operador_id: int,
) -> AssaiDevolucaoNfd:
    """Cria uma devolucao (NFd) cobrindo 1+ chassis da NF.

    Etapas:
      1. Valida NF existe e nao esta CANCELADA.
      2. Valida cada chassi: pertence a esta NF; ultimo evento = FATURADA.
      3. Cria AssaiDevolucaoNfd (UNIQUE (nf_id, numero_nfd) garante idempotencia).
      4. Para cada chassi:
         a. Emite EVENTO_PENDENTE com observacao "Moto devolvida - {motivo}".
         b. Cria AssaiDevolucaoItem (devolucao, chassi, nf_qpa_item, evento).
         c. Marca AssaiSeparacaoItem correspondente (devolvido_em + devolucao_item_id).
      5. Sobe anexos para S3 + cria AssaiDevolucaoAnexo (rollback S3 se DB falhar).
      6. Recalcula status do pedido (saldo do modelo retorna).

    Args:
        nf_id: id da AssaiNfQpa de origem.
        numero_nfd: numero da NF de devolucao emitida pelo cliente.
        data_devolucao: data da NFd (campo do cabecalho).
        motivo: justificativa (>=3 chars).
        chassis: iteravel de chassis a devolver (>=1).
        anexos: iteravel de FileStorage (PDF/XML/PNG/JPG). Opcional.
        operador_id: usuario que esta registrando.

    Returns:
        AssaiDevolucaoNfd com itens e anexos populados.

    Raises:
        DevolucaoValidationError: validacao falhou (chassi nao FATURADA,
                                  chassi nao pertence a NF, motivo curto,
                                  NFd duplicada, etc).
    """
    motivo_norm = (motivo or '').strip()
    if len(motivo_norm) < 3:
        raise DevolucaoValidationError('Motivo obrigatorio (>= 3 caracteres).')
    numero_nfd_norm = (numero_nfd or '').strip()
    if not numero_nfd_norm:
        raise DevolucaoValidationError('Numero da NFd obrigatorio.')
    if not isinstance(data_devolucao, date):
        raise DevolucaoValidationError('Data de devolucao invalida.')

    chassis_norm = [
        (c or '').strip().upper() for c in (chassis or []) if (c or '').strip()
    ]
    if not chassis_norm:
        raise DevolucaoValidationError('Selecione pelo menos 1 chassi.')
    chassis_unicos = list(dict.fromkeys(chassis_norm))  # remove duplicatas mantendo ordem
    if len(chassis_unicos) != len(chassis_norm):
        raise DevolucaoValidationError(
            'Chassis duplicados na selecao — selecione cada chassi apenas uma vez.'
        )

    nf = AssaiNfQpa.query.get(nf_id)
    if not nf:
        raise DevolucaoValidationError(f'NF {nf_id} nao encontrada.')
    if nf.status_match == 'CANCELADA':
        raise DevolucaoValidationError(
            f'NF {nf.numero} esta CANCELADA — nao aceita devolucao.'
        )

    # Mapa chassi -> AssaiNfQpaItem da NF (validacao 1: chassis ∈ NF)
    nf_items_por_chassi: Dict[str, AssaiNfQpaItem] = {
        it.chassi: it for it in nf.itens
    }
    chassis_fora_nf = [c for c in chassis_unicos if c not in nf_items_por_chassi]
    if chassis_fora_nf:
        raise DevolucaoValidationError(
            'Chassis nao pertencem a esta NF: ' + ', '.join(chassis_fora_nf)
        )

    # Validacao 2: chassi com ultimo evento = FATURADA
    chassis_nao_faturados: List[str] = []
    for chassi in chassis_unicos:
        if status_efetivo(chassi) != EVENTO_FATURADA:
            chassis_nao_faturados.append(chassi)
    if chassis_nao_faturados:
        raise DevolucaoValidationError(
            'Chassis nao estao FATURADA (estado atual diferente): '
            + ', '.join(chassis_nao_faturados)
        )

    # Cria cabecalho — idempotencia via UNIQUE (nf_id, numero_nfd)
    devolucao = AssaiDevolucaoNfd(
        nf_qpa_origem_id=nf.id,
        numero_nfd=numero_nfd_norm,
        data_devolucao=data_devolucao,
        motivo=motivo_norm,
        criado_em=agora_brasil_naive(),
        criado_por_id=operador_id,
    )
    db.session.add(devolucao)
    try:
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        raise DevolucaoValidationError(
            f'NFd {numero_nfd_norm} ja registrada para esta NF.'
        ) from exc

    obs_evento = f'Moto devolvida - {motivo_norm}'

    for chassi in chassis_unicos:
        nf_item = nf_items_por_chassi[chassi]

        evento = emitir_evento(
            chassi=chassi,
            tipo=EVENTO_PENDENTE,
            operador_id=operador_id,
            observacao=obs_evento,
            dados_extras={
                'origem': 'devolucao_nfd',
                'devolucao_id': devolucao.id,
                'nf_origem_id': nf.id,
                'numero_nfd': numero_nfd_norm,
            },
        )

        item = AssaiDevolucaoItem(
            devolucao_id=devolucao.id,
            chassi=chassi,
            nf_qpa_item_id=nf_item.id,
            evento_pendencia_id=evento.id,
            criado_em=agora_brasil_naive(),
        )
        db.session.add(item)
        db.session.flush()

        # Marca AssaiNfQpaItem.devolvido = True (regra: definido pelo MODELO).
        # `recalcular_status_pedido` exclui o SeparacaoItem referenciado por
        # nf_item.separacao_item_id da contagem de qtd_faturada.
        nf_item.devolvido = True
        nf_item.devolvido_em = agora_brasil_naive()
        nf_item.devolucao_item_id = item.id

    # Recalcular status do pedido (saldo do MODELO restituido). Best-effort.
    if nf.separacao_id:
        try:
            from app.motos_assai.services.pedido_status_service import (
                recalcular_status_pedido,
            )
            sep = nf.separacao
            if sep and sep.pedido_id:
                recalcular_status_pedido(sep.pedido_id)
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                'recalcular_status_pedido falhou apos devolucao %s', devolucao.id,
            )

    # Anexos: upload S3 com rollback do arquivo se commit falhar
    s3_keys_criados: List[str] = []
    storage = get_file_storage()
    folder = f'motos_assai/devolucoes/{devolucao.id}'

    try:
        for arquivo in (anexos or []):
            if not arquivo or not getattr(arquivo, 'filename', None):
                continue
            filename = arquivo.filename
            tamanho = _medir_tamanho_stream(arquivo)
            try:
                s3_key = storage.save_file(
                    arquivo, folder,
                    allowed_extensions=list(EXTENSOES_PERMITIDAS),
                )
            except ValueError as e:
                raise DevolucaoValidationError(str(e)) from e
            if not s3_key:
                raise DevolucaoValidationError(
                    f'Falha ao salvar anexo {filename} no storage.'
                )
            s3_keys_criados.append(s3_key)
            db.session.add(AssaiDevolucaoAnexo(
                devolucao_id=devolucao.id,
                tipo=detectar_tipo_anexo(filename),
                nome_original=filename,
                s3_key=s3_key,
                content_type=getattr(arquivo, 'content_type', None),
                tamanho_bytes=tamanho,
                criado_em=agora_brasil_naive(),
                criado_por_id=operador_id,
            ))

        db.session.commit()
    except Exception:
        db.session.rollback()
        # S3 ja gravou mas DB falhou: remove S3 best-effort para nao orfanar
        for key in s3_keys_criados:
            try:
                storage.delete_file(key)
            except Exception:
                pass
        raise

    return devolucao


# ----- Listagem --------------------------------------------------------------

def listar_devolucoes(
    *,
    nf_numero: Optional[str] = None,
    numero_nfd: Optional[str] = None,
    chassi: Optional[str] = None,
    modelo_id: Optional[int] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    limit: int = 250,
) -> List[AssaiDevolucaoNfd]:
    """Lista devolucoes com filtros opcionais ordenadas por criado_em DESC.

    modelo_id (2026-05-20): resolve via chassi -> assai_moto. Filtra NFds que
    contem um item cujo chassi pertence a um AssaiMoto do modelo informado.
    """
    q = (
        AssaiDevolucaoNfd.query
        .options(
            joinedload(AssaiDevolucaoNfd.nf_origem),
            joinedload(AssaiDevolucaoNfd.criado_por),
        )
        .order_by(AssaiDevolucaoNfd.criado_em.desc())
    )

    if nf_numero:
        q = (
            q.join(AssaiNfQpa, AssaiDevolucaoNfd.nf_qpa_origem_id == AssaiNfQpa.id)
             .filter(AssaiNfQpa.numero.ilike(f'%{nf_numero.strip()}%'))
        )
    if numero_nfd:
        q = q.filter(AssaiDevolucaoNfd.numero_nfd.ilike(f'%{numero_nfd.strip()}%'))
    if chassi:
        q = (
            q.join(AssaiDevolucaoItem,
                   AssaiDevolucaoItem.devolucao_id == AssaiDevolucaoNfd.id)
             .filter(AssaiDevolucaoItem.chassi.ilike(f'%{chassi.strip().upper()}%'))
        )
    if modelo_id:
        # Subquery (nao JOIN) para nao conflitar com o JOIN do filtro chassi.
        from app.motos_assai.models import AssaiMoto
        chassis_do_modelo = db.session.query(AssaiMoto.chassi).filter(
            AssaiMoto.modelo_id == modelo_id
        )
        dev_ids_modelo = db.session.query(AssaiDevolucaoItem.devolucao_id).filter(
            AssaiDevolucaoItem.chassi.in_(chassis_do_modelo)
        )
        q = q.filter(AssaiDevolucaoNfd.id.in_(dev_ids_modelo))
    if data_inicio:
        q = q.filter(AssaiDevolucaoNfd.data_devolucao >= data_inicio)
    if data_fim:
        q = q.filter(AssaiDevolucaoNfd.data_devolucao <= data_fim)

    return q.limit(limit).all()


def listar_devolucoes_da_nf(nf_id: int) -> List[AssaiDevolucaoNfd]:
    """Devolucoes vinculadas a uma NF Q.P.A. de venda."""
    return (
        AssaiDevolucaoNfd.query
        .filter(AssaiDevolucaoNfd.nf_qpa_origem_id == nf_id)
        .order_by(AssaiDevolucaoNfd.criado_em.desc())
        .all()
    )


def get_devolucao(devolucao_id: int) -> Optional[AssaiDevolucaoNfd]:
    return (
        AssaiDevolucaoNfd.query
        .options(
            joinedload(AssaiDevolucaoNfd.nf_origem),
            joinedload(AssaiDevolucaoNfd.criado_por),
        )
        .filter(AssaiDevolucaoNfd.id == devolucao_id)
        .first()
    )


# ----- Pendencias do chassi (botao "Pendencias(qtd)" por linha) --------------

def pendencias_do_chassi(chassi: str, limit: int = 50) -> Dict[str, Any]:
    """Historico de pendencias do chassi para o modal "Pendencias(qtd)".

    Retorna eventos PENDENTE e PENDENCIA_RESOLVIDA do chassi, mais recentes
    primeiro. qtd = numero de eventos PENDENTE (abertura de pendencia).
    """
    if not chassi:
        return {'chassi': '', 'qtd': 0, 'eventos': []}
    chassi_norm = chassi.strip().upper()

    eventos = (
        AssaiMotoEvento.query
        .options(joinedload(AssaiMotoEvento.operador))
        .filter(
            AssaiMotoEvento.chassi == chassi_norm,
            AssaiMotoEvento.tipo.in_([EVENTO_PENDENTE, EVENTO_PENDENCIA_RESOLVIDA]),
        )
        .order_by(AssaiMotoEvento.ocorrido_em.desc(), AssaiMotoEvento.id.desc())
        .limit(limit)
        .all()
    )

    qtd_aberturas = sum(1 for e in eventos if e.tipo == EVENTO_PENDENTE)

    payload = []
    for ev in eventos:
        descricao = ev.observacao
        if (not descricao) and isinstance(ev.dados_extras, dict):
            descricao = ev.dados_extras.get('descricao')
        payload.append({
            'id': ev.id,
            'tipo': ev.tipo,
            'observacao': descricao or '(sem descricao)',
            'operador': ev.operador.nome if ev.operador else '-',
            'ocorrido_em': (
                ev.ocorrido_em.strftime('%d/%m/%Y %H:%M')
                if ev.ocorrido_em else '-'
            ),
            'origem_devolucao': (
                isinstance(ev.dados_extras, dict)
                and ev.dados_extras.get('origem') == 'devolucao_nfd'
            ),
        })

    return {
        'chassi': chassi_norm,
        'qtd': qtd_aberturas,
        'eventos': payload,
    }


# ----- Anexos: URLs presigned ------------------------------------------------

def url_visualizacao_anexo(s3_key: str) -> Optional[str]:
    """Presigned URL para visualizacao inline (1h)."""
    if not s3_key:
        return None
    try:
        return get_file_storage().get_file_url(s3_key)
    except Exception:
        return None


def url_download_anexo(s3_key: str, nome_original: Optional[str] = None) -> Optional[str]:
    """Presigned URL com Content-Disposition: attachment (1h)."""
    if not s3_key:
        return None
    try:
        return get_file_storage().get_download_url(s3_key, nome_original)
    except Exception:
        return None


# ----- Auxiliar: payload de chassis para a tela ------------------------------

def itens_da_nf_para_tela(nf_id: int) -> List[Dict[str, Any]]:
    """Lista chassis da NF com modelo/cor/qtd_pendencias e flag ja_devolvido.

    Usado na tela de form da devolucao para popular a tabela com checkbox.
    ja_devolvido=True bloqueia checkbox no template (anti-duplicate).
    """
    nf = AssaiNfQpa.query.get(nf_id)
    if not nf:
        return []

    chassis = [it.chassi for it in nf.itens]
    if not chassis:
        return []

    motos = (
        AssaiMoto.query
        .options(joinedload(AssaiMoto.modelo))
        .filter(AssaiMoto.chassi.in_(chassis))
        .all()
    )
    moto_por_chassi = {m.chassi: m for m in motos}

    # Chassis ja devolvidos (em qualquer devolucao da MESMA NF)
    devolvidos = (
        db.session.query(AssaiDevolucaoItem.chassi)
        .join(AssaiDevolucaoNfd,
              AssaiDevolucaoNfd.id == AssaiDevolucaoItem.devolucao_id)
        .filter(AssaiDevolucaoNfd.nf_qpa_origem_id == nf_id)
        .all()
    )
    set_devolvidos = {c for (c,) in devolvidos}

    # qtd_pendencias por chassi (eventos PENDENTE)
    from sqlalchemy import func
    pend_rows = (
        db.session.query(AssaiMotoEvento.chassi, func.count(AssaiMotoEvento.id))
        .filter(
            AssaiMotoEvento.chassi.in_(chassis),
            AssaiMotoEvento.tipo == EVENTO_PENDENTE,
        )
        .group_by(AssaiMotoEvento.chassi)
        .all()
    )
    pend_por_chassi = {c: int(q) for c, q in pend_rows}

    resultado = []
    for it in nf.itens:
        moto = moto_por_chassi.get(it.chassi)
        modelo_codigo = moto.modelo.codigo if moto and moto.modelo else (
            it.modelo_extraido or '-'
        )
        modelo_nome = moto.modelo.nome if moto and moto.modelo else '-'
        cor = (moto.cor if moto else None) or '-'
        ja_devolvido = it.chassi in set_devolvidos
        status_atual = status_efetivo(it.chassi)
        resultado.append({
            'chassi': it.chassi,
            'modelo_codigo': modelo_codigo,
            'modelo_nome': modelo_nome,
            'cor': cor,
            'valor_unitario': float(it.valor_extraido or 0),
            'qtd_pendencias': pend_por_chassi.get(it.chassi, 0),
            'ja_devolvido': ja_devolvido,
            'status_atual': status_atual or '-',
            'pode_devolver': (not ja_devolvido) and (status_atual == EVENTO_FATURADA),
        })
    return resultado
