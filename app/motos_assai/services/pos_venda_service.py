"""Service de Pos-Venda (motos ja vendidas via NF Q.P.A.).

Funcionalidade:
  * listar motos vendidas com filtros (NF, loja, modelo, cor, chassi)
  * agregar qtd_ocorrencias por chassi
  * CRUD de ocorrencia (LOJA ou CLIENTE)
  * upload/listagem/delete de anexos no S3
  * gerar AssaiPendencia a partir de uma ocorrencia + acompanhar (Spec 2 Task 13)

NF Q.P.A. importada e a fronteira: apenas chassis que aparecem em
`assai_nf_qpa_item` sao considerados "vendidos".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func

from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiLoja,
    AssaiNfQpa, AssaiNfQpaItem,
    AssaiPosVendaOcorrencia, AssaiPosVendaOcorrenciaAnexo,
    CATEGORIA_LOJA, CATEGORIAS_VALIDAS,
    ANEXO_TIPO_FOTO, ANEXO_TIPO_VIDEO, ANEXO_TIPO_AUDIO, ANEXO_TIPO_OUTRO,
)
from app.utils.file_storage import get_file_storage
from app.utils.timezone import agora_brasil_naive


class PosVendaValidationError(Exception):
    """Erro de validacao em pos-venda."""


# ----- Mapas auxiliares de extensao -> tipo de anexo --------------------------

EXTENSOES_FOTO = {'jpg', 'jpeg', 'jfif', 'png', 'gif', 'webp', 'bmp', 'heic'}
EXTENSOES_VIDEO = {'mp4', 'mov', 'avi', 'mkv', 'webm', '3gp', 'm4v'}
EXTENSOES_AUDIO = {'mp3', 'wav', 'm4a', 'aac', 'ogg', 'opus', 'flac'}

# Todas as extensoes aceitas pelo upload (uniao)
EXTENSOES_PERMITIDAS = (
    EXTENSOES_FOTO | EXTENSOES_VIDEO | EXTENSOES_AUDIO
)


def detectar_tipo_anexo(filename: str) -> str:
    """Detecta tipo do anexo pela extensao."""
    if not filename or '.' not in filename:
        return ANEXO_TIPO_OUTRO
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext in EXTENSOES_FOTO:
        return ANEXO_TIPO_FOTO
    if ext in EXTENSOES_VIDEO:
        return ANEXO_TIPO_VIDEO
    if ext in EXTENSOES_AUDIO:
        return ANEXO_TIPO_AUDIO
    return ANEXO_TIPO_OUTRO


# ----- DTO de linha da listagem ----------------------------------------------

@dataclass
class LinhaPosVenda:
    chassi: str
    modelo_id: int | None
    modelo_codigo: str | None
    modelo_nome: str | None
    cor: str | None
    nf_id: int | None
    nf_numero: str | None
    nf_chave: str | None
    nf_data_emissao: datetime | None
    loja_id: int | None
    loja_numero: str | None
    loja_nome: str | None
    qtd_ocorrencias: int
    qtd_pendencias_abertas: int = 0


# ----- Listagem ---------------------------------------------------------------

def listar_motos_vendidas(
    *,
    nf_numero: str | None = None,
    loja_id: int | None = None,
    modelo_id: int | None = None,
    cor: str | None = None,
    chassi: str | None = None,
    limit: int = 500,
) -> list[LinhaPosVenda]:
    """Lista motos vendidas (1 chassi = 1 linha).

    Origem: `assai_nf_qpa_item` (chassi que apareceu em NF Q.P.A. importada).
    Agrega qtd_ocorrencias por chassi via subquery.

    Filtros aplicados via WHERE; todos opcionais.
    """
    # Subquery: qtd_ocorrencias por chassi
    subq_oc = (
        db.session.query(
            AssaiPosVendaOcorrencia.chassi.label('c'),
            func.count(AssaiPosVendaOcorrencia.id).label('qtd'),
        )
        .group_by(AssaiPosVendaOcorrencia.chassi)
        .subquery()
    )

    q = (
        db.session.query(
            AssaiNfQpaItem.chassi.label('chassi'),
            AssaiMoto.modelo_id.label('modelo_id'),
            AssaiModelo.codigo.label('modelo_codigo'),
            AssaiModelo.nome.label('modelo_nome'),
            AssaiMoto.cor.label('cor'),
            AssaiNfQpa.id.label('nf_id'),
            AssaiNfQpa.numero.label('nf_numero'),
            AssaiNfQpa.chave_44.label('nf_chave'),
            AssaiNfQpa.data_emissao.label('nf_data_emissao'),
            AssaiLoja.id.label('loja_id'),
            AssaiLoja.numero.label('loja_numero'),
            AssaiLoja.nome.label('loja_nome'),
            func.coalesce(subq_oc.c.qtd, 0).label('qtd_ocorrencias'),
        )
        .select_from(AssaiNfQpaItem)
        .join(AssaiNfQpa, AssaiNfQpaItem.nf_id == AssaiNfQpa.id)
        .outerjoin(AssaiLoja, AssaiNfQpa.loja_id == AssaiLoja.id)
        .outerjoin(AssaiMoto, AssaiMoto.chassi == AssaiNfQpaItem.chassi)
        .outerjoin(AssaiModelo, AssaiMoto.modelo_id == AssaiModelo.id)
        .outerjoin(subq_oc, subq_oc.c.c == AssaiNfQpaItem.chassi)
    )

    if nf_numero:
        q = q.filter(AssaiNfQpa.numero.ilike(f'%{nf_numero.strip()}%'))
    if loja_id:
        q = q.filter(AssaiNfQpa.loja_id == loja_id)
    if modelo_id:
        q = q.filter(AssaiMoto.modelo_id == modelo_id)
    if cor:
        q = q.filter(AssaiMoto.cor.ilike(f'%{cor.strip()}%'))
    if chassi:
        q = q.filter(AssaiNfQpaItem.chassi.ilike(f'%{chassi.strip()}%'))

    # 1 chassi por NF (assai_nf_qpa_item ja e 1:1 com chassi dentro de uma NF;
    # se o mesmo chassi aparecer em 2 NFs distintas, retorna 2 linhas — esperado).
    q = q.order_by(AssaiNfQpa.data_emissao.desc().nullslast(), AssaiNfQpaItem.chassi).limit(limit)

    return [
        LinhaPosVenda(
            chassi=row.chassi,
            modelo_id=row.modelo_id,
            modelo_codigo=row.modelo_codigo,
            modelo_nome=row.modelo_nome,
            cor=row.cor,
            nf_id=row.nf_id,
            nf_numero=row.nf_numero,
            nf_chave=row.nf_chave,
            nf_data_emissao=row.nf_data_emissao,
            loja_id=row.loja_id,
            loja_numero=row.loja_numero,
            loja_nome=row.loja_nome,
            qtd_ocorrencias=int(row.qtd_ocorrencias or 0),
        )
        for row in q.all()
    ]


def contexto_moto_por_chassi(chassi: str) -> dict | None:
    """Retorna ctx (nf/loja/modelo/cor) para o cabecalho do modal.

    Usa a NF Q.P.A. mais recente que contem o chassi. Se nao houver, retorna
    None (chassi nao deveria estar acessivel na listagem nesse caso).
    """
    if not chassi:
        return None
    chassi = chassi.strip()

    row = (
        db.session.query(
            AssaiNfQpaItem.chassi.label('chassi'),
            AssaiModelo.codigo.label('modelo_codigo'),
            AssaiModelo.nome.label('modelo_nome'),
            AssaiMoto.cor.label('cor'),
            AssaiNfQpa.numero.label('nf_numero'),
            AssaiNfQpa.chave_44.label('nf_chave'),
            AssaiNfQpa.data_emissao.label('nf_data_emissao'),
            AssaiLoja.numero.label('loja_numero'),
            AssaiLoja.nome.label('loja_nome'),
        )
        .select_from(AssaiNfQpaItem)
        .join(AssaiNfQpa, AssaiNfQpaItem.nf_id == AssaiNfQpa.id)
        .outerjoin(AssaiLoja, AssaiNfQpa.loja_id == AssaiLoja.id)
        .outerjoin(AssaiMoto, AssaiMoto.chassi == AssaiNfQpaItem.chassi)
        .outerjoin(AssaiModelo, AssaiMoto.modelo_id == AssaiModelo.id)
        .filter(AssaiNfQpaItem.chassi == chassi)
        .order_by(AssaiNfQpa.data_emissao.desc().nullslast(), AssaiNfQpa.id.desc())
        .first()
    )
    if not row:
        return None

    return {
        'chassi': row.chassi,
        'modelo_codigo': row.modelo_codigo,
        'modelo_nome': row.modelo_nome,
        'cor': row.cor,
        'nf_numero': row.nf_numero,
        'nf_chave': row.nf_chave,
        'nf_data_emissao': row.nf_data_emissao,
        'loja_numero': row.loja_numero,
        'loja_nome': row.loja_nome,
    }


def chassi_foi_vendido(chassi: str) -> bool:
    """True se o chassi aparece em alguma NF Q.P.A. importada."""
    if not chassi:
        return False
    return db.session.query(
        AssaiNfQpaItem.id
    ).filter(AssaiNfQpaItem.chassi == chassi.strip()).limit(1).first() is not None


# ----- Ocorrencias ------------------------------------------------------------

def listar_ocorrencias(chassi: str) -> list[AssaiPosVendaOcorrencia]:
    """Lista todas as ocorrencias de um chassi (LOJA + CLIENTE), mais recentes primeiro."""
    return (
        AssaiPosVendaOcorrencia.query
        .filter(AssaiPosVendaOcorrencia.chassi == chassi.strip())
        .order_by(AssaiPosVendaOcorrencia.criado_em.desc())
        .all()
    )


def criar_ocorrencia(
    *,
    chassi: str,
    categoria: str,
    descricao: str,
    operador_id: int,
) -> AssaiPosVendaOcorrencia:
    """Cria nova ocorrencia. Levanta `PosVendaValidationError` se invalido."""
    chassi = (chassi or '').strip()
    if not chassi:
        raise PosVendaValidationError('chassi obrigatorio')
    if categoria not in CATEGORIAS_VALIDAS:
        raise PosVendaValidationError(
            f'categoria invalida: {categoria!r}. Validas: {sorted(CATEGORIAS_VALIDAS)}'
        )
    descricao = (descricao or '').strip()
    if not descricao:
        raise PosVendaValidationError('descricao obrigatoria')
    if not chassi_foi_vendido(chassi):
        raise PosVendaValidationError(
            f'chassi {chassi} nao consta em nenhuma NF Q.P.A. importada'
        )

    oc = AssaiPosVendaOcorrencia(
        chassi=chassi,
        categoria=categoria,
        descricao=descricao,
        criado_em=agora_brasil_naive(),
        criado_por_id=operador_id,
    )
    db.session.add(oc)
    db.session.commit()
    return oc


def atualizar_ocorrencia(
    *,
    ocorrencia_id: int,
    descricao: str | None = None,
    categoria: str | None = None,
    operador_id: int,
) -> AssaiPosVendaOcorrencia:
    """Atualiza descricao/categoria. Levanta `PosVendaValidationError` se nao existe."""
    oc = AssaiPosVendaOcorrencia.query.get(ocorrencia_id)
    if not oc:
        raise PosVendaValidationError(f'ocorrencia {ocorrencia_id} nao encontrada')

    mudou = False
    if descricao is not None:
        descricao = descricao.strip()
        if not descricao:
            raise PosVendaValidationError('descricao nao pode ser vazia')
        if descricao != oc.descricao:
            oc.descricao = descricao
            mudou = True
    if categoria is not None:
        if categoria not in CATEGORIAS_VALIDAS:
            raise PosVendaValidationError(
                f'categoria invalida: {categoria!r}'
            )
        if categoria != oc.categoria:
            oc.categoria = categoria
            mudou = True

    if mudou:
        oc.atualizado_em = agora_brasil_naive()
        oc.atualizado_por_id = operador_id
        db.session.commit()
    return oc


def excluir_ocorrencia(ocorrencia_id: int) -> None:
    """Exclui ocorrencia + anexos (cascade) e remove S3 keys (best-effort)."""
    oc = AssaiPosVendaOcorrencia.query.get(ocorrencia_id)
    if not oc:
        raise PosVendaValidationError(f'ocorrencia {ocorrencia_id} nao encontrada')

    # Coleta s3_keys antes do delete cascade
    s3_keys = [a.s3_key for a in oc.anexos if a.s3_key]
    db.session.delete(oc)
    db.session.commit()

    # Best-effort: deletar S3
    if s3_keys:
        storage = get_file_storage()
        for key in s3_keys:
            try:
                storage.delete_file(key)
            except Exception:
                # Falha silenciosa: registro DB ja foi removido
                pass


# ----- Anexos -----------------------------------------------------------------

def _medir_tamanho_stream(arquivo) -> int | None:
    """Mede tamanho do stream do upload sem consumir o cursor.

    Werkzeug `FileStorage.content_length` retorna 0 para uploads multipart
    individuais — nao confiavel. Usar seek(0, 2)/tell()/seek(0) e robusto
    para qualquer file-like.
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


def adicionar_anexo(
    *,
    ocorrencia_id: int,
    arquivo,  # werkzeug FileStorage
    operador_id: int,
) -> AssaiPosVendaOcorrenciaAnexo:
    """Faz upload de 1 anexo para S3 + persiste row.

    Folder S3: `motos_assai/pos_venda/{ocorrencia_id}/`.

    Se o `db.session.commit()` falhar apos o S3 ja gravar, deleta o S3 key
    (best-effort) para evitar arquivo orfao.
    """
    oc = AssaiPosVendaOcorrencia.query.get(ocorrencia_id)
    if not oc:
        raise PosVendaValidationError(f'ocorrencia {ocorrencia_id} nao encontrada')

    if not arquivo or not getattr(arquivo, 'filename', None):
        raise PosVendaValidationError('arquivo obrigatorio')

    filename = arquivo.filename
    tipo = detectar_tipo_anexo(filename)
    folder = f'motos_assai/pos_venda/{ocorrencia_id}'

    # Medir tamanho ANTES do save_file (que consome o cursor)
    tamanho = _medir_tamanho_stream(arquivo)

    storage = get_file_storage()
    try:
        s3_key = storage.save_file(
            arquivo, folder,
            allowed_extensions=list(EXTENSOES_PERMITIDAS),
        )
    except ValueError as e:
        raise PosVendaValidationError(str(e)) from e

    if not s3_key:
        raise PosVendaValidationError('falha ao salvar arquivo no storage')

    anexo = AssaiPosVendaOcorrenciaAnexo(
        ocorrencia_id=ocorrencia_id,
        tipo=tipo,
        nome_original=filename,
        s3_key=s3_key,
        content_type=getattr(arquivo, 'content_type', None),
        tamanho_bytes=tamanho,
        criado_em=agora_brasil_naive(),
        criado_por_id=operador_id,
    )
    db.session.add(anexo)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        # S3 ja gravou mas DB falhou: remove S3 best-effort para nao orfanar
        try:
            storage.delete_file(s3_key)
        except Exception:
            pass
        raise
    return anexo


def excluir_anexo(anexo_id: int) -> None:
    """Exclui 1 anexo (DB + S3 best-effort)."""
    anexo = AssaiPosVendaOcorrenciaAnexo.query.get(anexo_id)
    if not anexo:
        raise PosVendaValidationError(f'anexo {anexo_id} nao encontrado')

    s3_key = anexo.s3_key
    db.session.delete(anexo)
    db.session.commit()

    if s3_key:
        try:
            get_file_storage().delete_file(s3_key)
        except Exception:
            pass


def url_visualizacao_anexo(s3_key: str) -> str | None:
    """Presigned URL para visualizacao inline (1h)."""
    if not s3_key:
        return None
    try:
        return get_file_storage().get_file_url(s3_key)
    except Exception:
        return None


def url_download_anexo(s3_key: str, nome_original: str | None = None) -> str | None:
    """Presigned URL com Content-Disposition: attachment (1h)."""
    if not s3_key:
        return None
    try:
        return get_file_storage().get_download_url(s3_key, nome_original)
    except Exception:
        return None


# ----- Pendencias (Spec 2 Task 13: gerar pendencia + acompanhar) --------------

def gerar_pendencia_de_ocorrencia(
    *, ocorrencia_id: int, categoria: str, retorno_fisico: bool, operador_id: int,
):
    """Abre uma AssaiPendencia a partir de uma ocorrencia de pos-venda.

    Origem derivada da categoria da ocorrencia: LOJA -> POS_VENDA_LOJA,
    CLIENTE -> POS_VENDA_CLIENTE. add+flush (via `abrir_pendencia`), SEM
    commit — caller commita.
    """
    from app.motos_assai.models import (
        PENDENCIA_ORIGEM_POS_VENDA_LOJA, PENDENCIA_ORIGEM_POS_VENDA_CLIENTE,
    )
    from app.motos_assai.services.pendencia_service import abrir_pendencia

    oc = db.session.get(AssaiPosVendaOcorrencia, ocorrencia_id)
    if oc is None:
        raise PosVendaValidationError(f'Ocorrência {ocorrencia_id} não encontrada.')

    origem = (
        PENDENCIA_ORIGEM_POS_VENDA_LOJA if oc.categoria == CATEGORIA_LOJA
        else PENDENCIA_ORIGEM_POS_VENDA_CLIENTE
    )
    return abrir_pendencia(
        chassi=oc.chassi,
        categoria=categoria,
        origem=origem,
        descricao=(oc.descricao or 'Ocorrência pós-venda')[:2000],
        pos_venda_ocorrencia_id=oc.id,
        retorno_fisico=bool(retorno_fisico),
        operador_id=operador_id,
    )


def pendencias_da_ocorrencia(ocorrencia_id: int) -> list:
    """Lista fichas AssaiPendencia geradas a partir desta ocorrencia (mais recente 1o)."""
    from app.motos_assai.models import AssaiPendencia
    return (
        AssaiPendencia.query
        .filter(AssaiPendencia.pos_venda_ocorrencia_id == ocorrencia_id)
        .order_by(AssaiPendencia.aberta_em.desc())
        .all()
    )


def contar_pendencias_abertas_por_chassi(chassi: str) -> int:
    """Conta fichas AssaiPendencia abertas (nao resolvida/cancelada) do chassi."""
    from app.motos_assai.models import AssaiPendencia
    return (
        AssaiPendencia.query
        .filter(
            AssaiPendencia.chassi == (chassi or '').strip().upper(),
            AssaiPendencia.resolvida_em.is_(None),
            AssaiPendencia.cancelada_em.is_(None),
        )
        .count()
    )


def contar_pendencias_abertas_por_chassis(chassis: list[str]) -> dict[str, int]:
    """Conta fichas AssaiPendencia abertas (nao resolvida/cancelada), agrupado
    por chassi, em UMA query (evita N+1 — ver `contar_pendencias_abertas_por_chassi`
    para o equivalente pontual, mantido por compatibilidade/uso em outros pontos).

    Retorna dict {chassi: count}; chassis sem pendencia aberta simplesmente nao
    aparecem no dict (caller usa `.get(chassi, 0)`). Lista vazia -> {} sem query.
    """
    chassis_normalizados = [
        (c or '').strip().upper() for c in (chassis or []) if (c or '').strip()
    ]
    if not chassis_normalizados:
        return {}

    from app.motos_assai.models import AssaiPendencia
    rows = (
        db.session.query(
            AssaiPendencia.chassi,
            func.count(AssaiPendencia.id),
        )
        .filter(
            AssaiPendencia.chassi.in_(chassis_normalizados),
            AssaiPendencia.resolvida_em.is_(None),
            AssaiPendencia.cancelada_em.is_(None),
        )
        .group_by(AssaiPendencia.chassi)
        .all()
    )
    return {chassi: int(qtd) for chassi, qtd in rows}
