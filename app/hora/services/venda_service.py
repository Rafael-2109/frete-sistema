"""Service de HoraVenda — pedido de venda ao consumidor final.

Maquina de estado (status):
    COTACAO    -> CONFIRMADO  (confirmar_venda)
    CONFIRMADO -> FATURADO    (webhook TagPlus nfe_aprovada)
    *          -> CANCELADO   (cancelar_venda; FATURADO so apos NFe cancelada)
    DANFE legado -> FATURADO direto (importar_nf_saida_pdf).

Estoque:
    COTACAO/CONFIRMADO/FATURADO reservam o chassi (saem do estoque disponivel).
    CANCELADO devolve via evento DEVOLVIDA.

Lock pessimista:
    criar_venda_manual + editar_item_pedido + adicionar_item_pedido fazem
    SELECT FOR UPDATE no chassi para impedir reserva concorrente.

Auditoria:
    Toda transicao registra HoraVendaAuditoria via venda_audit.registrar_auditoria.
"""
from __future__ import annotations

import io
from datetime import date, datetime, time
from decimal import Decimal
from typing import Iterable, List, Optional

from flask import current_app

from app import db
from app.hora.models import (
    HoraLoja,
    HoraMoto,
    HoraMotoEvento,
    HoraTabelaPreco,
    HoraVenda,
    HoraVendaDivergencia,
    HoraVendaItem,
    HoraVendaPagamento,
    VENDA_STATUS_CANCELADO,
    VENDA_STATUS_CONFIRMADO,
    VENDA_STATUS_COTACAO,
    VENDA_STATUS_FATURADO,
    VENDA_STATUS_INCOMPLETO,
)
from app.hora.models.tagplus import (
    HoraTagPlusNfeEmissao,
    HoraTagPlusProdutoMap,
    NFE_STATUS_APROVADA,
    NFE_STATUS_CANCELAMENTO_SOLICITADO,
    NFE_STATUS_EM_ENVIO,
    NFE_STATUS_ENVIADA_SEFAZ,
)
from app.hora.services import venda_audit
from app.hora.services.estoque_service import EVENTOS_EM_ESTOQUE
from app.hora.services.moto_service import get_or_create_moto, registrar_evento
from app.hora.services.parsers import parse_danfe_to_hora_payload
from app.utils.file_storage import FileStorage
from app.utils.timezone import agora_utc_naive


# --------------------------------------------------------------------------
# Tipos de divergencia (espelhado em hora_17_nf_saida.sql)
# --------------------------------------------------------------------------
TIPOS_DIVERGENCIA_VENDA = (
    'CHASSI_NAO_CADASTRADO',
    'CHASSI_INDISPONIVEL',
    'LOJA_DIVERGENTE',
    'CNPJ_DESCONHECIDO',
    'TABELA_PRECO_AUSENTE',
    'PRECO_ACIMA_TABELA',
    # Adicionado migration hora_29: nome do produto na origem (TagPlus,
    # NF, pedido) nao bate em nenhum HoraModeloAlias — pendencia foi
    # criada em hora_modelo_pendente. Item da venda fica sem HoraMoto
    # ate operador resolver em /hora/modelos/pendencias.
    'MODELO_PENDENTE',
)

# Estados de NFe que bloqueiam edicao/cancelamento livre da venda.
_NFE_EM_VOO = (NFE_STATUS_EM_ENVIO, NFE_STATUS_ENVIADA_SEFAZ, NFE_STATUS_CANCELAMENTO_SOLICITADO)


def _para_datetime(valor) -> Optional[datetime]:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, date):
        return datetime.combine(valor, time.min)
    return None


class NfSaidaJaImportada(Exception):
    """NF com mesma chave_44 já existe em HoraVenda."""


class ChassiIndisponivelError(ValueError):
    """Chassi nao esta disponivel para reserva (ja reservado / vendido / fora de estoque)."""


class TransicaoInvalidaError(ValueError):
    """Transicao de status nao permitida."""


# --------------------------------------------------------------------------
# Helpers internos
# --------------------------------------------------------------------------

def _salvar_pdf_storage(
    pdf_bytes: bytes, chave_44: str, nome_arquivo_origem: Optional[str]
) -> Optional[str]:
    try:
        buf = io.BytesIO(pdf_bytes)
        buf.name = (nome_arquivo_origem or f'venda_{chave_44}.pdf')
        s3_key = FileStorage().save_file(
            buf, folder='hora/vendas', filename=f'{chave_44}.pdf',
            allowed_extensions=['pdf'],
        )
        return s3_key
    except Exception as exc:
        current_app.logger.warning(
            f'hora: falha ao persistir PDF da NF de saida chave={chave_44}: {exc}'
        )
        return None


def _registrar_divergencia(
    venda_id: int,
    tipo: str,
    numero_chassi: Optional[str] = None,
    detalhe: Optional[str] = None,
    valor_esperado: Optional[str] = None,
    valor_conferido: Optional[str] = None,
) -> HoraVendaDivergencia:
    """UPSERT idempotente em HoraVendaDivergencia.

    A tabela tem UNIQUE (venda_id, tipo, numero_chassi). Em re-execucoes do
    backfill TagPlus, INSERT puro violava `uq_hora_venda_divergencia_tipo_chassi`
    e cada NF re-importada falhava (50s perdidos no retry de SSL drop antes
    de marcar erro). Agora reutilizamos a divergencia existente — se algo
    mudou no detalhe/valores, atualizamos; se ja foi resolvida, mantemos
    como esta (operador ja decidiu).
    """
    if tipo not in TIPOS_DIVERGENCIA_VENDA:
        raise ValueError(f'tipo de divergencia invalido: {tipo}')

    # Procura divergencia existente (chassi NULL precisa de filtro `IS NULL`).
    query = HoraVendaDivergencia.query.filter_by(venda_id=venda_id, tipo=tipo)
    if numero_chassi is None:
        query = query.filter(HoraVendaDivergencia.numero_chassi.is_(None))
    else:
        query = query.filter(HoraVendaDivergencia.numero_chassi == numero_chassi)
    div = query.first()

    if div is not None:
        # Atualiza apenas se ainda esta aberta (preserva resolucoes do operador).
        if div.aberta:
            if detalhe is not None and div.detalhe != detalhe:
                div.detalhe = detalhe
            if valor_esperado is not None and div.valor_esperado != valor_esperado:
                div.valor_esperado = valor_esperado
            if valor_conferido is not None and div.valor_conferido != valor_conferido:
                div.valor_conferido = valor_conferido
            db.session.flush()
        return div

    div = HoraVendaDivergencia(
        venda_id=venda_id,
        tipo=tipo,
        numero_chassi=numero_chassi,
        detalhe=detalhe,
        valor_esperado=valor_esperado,
        valor_conferido=valor_conferido,
    )
    db.session.add(div)
    db.session.flush()
    return div


def _ultimo_evento(chassi: str) -> Optional[HoraMotoEvento]:
    return (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi)
        .order_by(HoraMotoEvento.timestamp.desc())
        .first()
    )


def _buscar_preco_vigente(modelo_id: int, na_data) -> Optional[HoraTabelaPreco]:
    from sqlalchemy import or_
    return (
        HoraTabelaPreco.query
        .filter(
            HoraTabelaPreco.modelo_id == modelo_id,
            HoraTabelaPreco.ativo.is_(True),
            HoraTabelaPreco.vigencia_inicio <= na_data,
            or_(
                HoraTabelaPreco.vigencia_fim.is_(None),
                HoraTabelaPreco.vigencia_fim >= na_data,
            ),
        )
        .order_by(HoraTabelaPreco.vigencia_inicio.desc())
        .first()
    )


def _resolver_loja_por_cnpj(cnpj_emitente: Optional[str]) -> Optional[HoraLoja]:
    if not cnpj_emitente:
        return None
    digitos = ''.join(c for c in cnpj_emitente if c.isdigit())
    if not digitos:
        return None
    return HoraLoja.query.filter_by(cnpj=digitos, ativa=True).first()


def _lock_chassi_e_validar_disponivel(chassi: str) -> tuple[HoraMoto, HoraMotoEvento]:
    """SELECT ... FOR UPDATE no HoraMoto + valida disponibilidade.

    Retorna (moto, ultimo_evento). Levanta ChassiIndisponivelError se nao
    estiver em EVENTOS_EM_ESTOQUE.
    """
    chassi_norm = (chassi or '').strip().upper()
    if not chassi_norm:
        raise ValueError('Chassi obrigatorio')

    moto = (
        db.session.query(HoraMoto)
        .filter(HoraMoto.numero_chassi == chassi_norm)
        .with_for_update()
        .first()
    )
    if not moto:
        raise ChassiIndisponivelError(f'Chassi {chassi_norm} nao cadastrado')

    ult = _ultimo_evento(chassi_norm)
    if ult is None or ult.tipo not in EVENTOS_EM_ESTOQUE:
        ult_tipo = ult.tipo if ult else 'sem eventos'
        raise ChassiIndisponivelError(
            f'Chassi {chassi_norm} nao esta disponivel para reserva '
            f'(ultimo evento: {ult_tipo})'
        )
    return moto, ult


def _emissao_nfe(venda_id: int) -> Optional[HoraTagPlusNfeEmissao]:
    return HoraTagPlusNfeEmissao.query.filter_by(venda_id=venda_id).first()


def _buscar_preco_modelo(
    modelo_id: int, forma_pagamento_hora: Optional[str], na_data,
) -> tuple[Optional[Decimal], str, Optional[int]]:
    """Resolve preço de tabela do modelo conforme forma de pagamento.

    Retorna `(preco, fonte, tabela_preco_id)`:
      preco: Decimal ou None se nao houver tabela alguma para o modelo.
      fonte: 'MODELO_A_VISTA' | 'MODELO_A_PRAZO' | 'TABELA_LEGADA' | 'AUSENTE'.
      tabela_preco_id: id da HoraTabelaPreco usada (so quando fonte='TABELA_LEGADA').

    Prioridade:
      1. HoraModelo.preco_a_vista / preco_a_prazo conforme tipo da forma de
         pagamento (HoraTagPlusFormaPagamentoMap.tipo_pagamento).
      2. Se forma desconhecida ou tipo nao classificado, prefere preco_a_vista
         (default mais comum); fallback para preco_a_prazo.
      3. Ultimo recurso: HoraTabelaPreco vigente em na_data (legado).
    """
    from app.hora.models import HoraModelo
    from app.hora.models.tagplus import (
        HoraTagPlusFormaPagamentoMap,
        TIPO_PAGAMENTO_A_VISTA,
        TIPO_PAGAMENTO_A_PRAZO,
    )

    modelo = HoraModelo.query.get(modelo_id) if modelo_id else None
    if modelo is None:
        return None, 'AUSENTE', None

    tipo = None
    if forma_pagamento_hora:
        forma_norm = forma_pagamento_hora.strip().upper()
        if forma_norm and forma_norm != 'NAO_INFORMADO':
            mapa = HoraTagPlusFormaPagamentoMap.query.filter_by(
                forma_pagamento_hora=forma_norm,
            ).first()
            if mapa is not None:
                tipo = mapa.tipo_pagamento

    if tipo == TIPO_PAGAMENTO_A_VISTA and modelo.preco_a_vista is not None:
        return Decimal(str(modelo.preco_a_vista)), 'MODELO_A_VISTA', None
    if tipo == TIPO_PAGAMENTO_A_PRAZO and modelo.preco_a_prazo is not None:
        return Decimal(str(modelo.preco_a_prazo)), 'MODELO_A_PRAZO', None

    # Fallback intra-modelo: prefere a vista, depois a prazo.
    if modelo.preco_a_vista is not None:
        return Decimal(str(modelo.preco_a_vista)), 'MODELO_A_VISTA', None
    if modelo.preco_a_prazo is not None:
        return Decimal(str(modelo.preco_a_prazo)), 'MODELO_A_PRAZO', None

    # Ultimo fallback: HoraTabelaPreco legado.
    tabela = _buscar_preco_vigente(modelo_id, na_data)
    if tabela is not None:
        return Decimal(str(tabela.preco_tabela)), 'TABELA_LEGADA', tabela.id

    return None, 'AUSENTE', None


def buscar_preco_para_pedido(
    modelo_id: int,
    forma_pagamento_hora: Optional[str] = None,
    na_data=None,
) -> dict:
    """API publica para o JS do pedido de venda manual.

    Retorna dict com preço sugerido e qual a fonte:
      {
        'preco': Decimal | None,
        'fonte': 'MODELO_A_VISTA' | 'MODELO_A_PRAZO' | 'TABELA_LEGADA' | 'AUSENTE',
        'tipo_pagamento': 'A_VISTA' | 'A_PRAZO' | None,
        'preco_a_vista': Decimal | None,   # campo direto do modelo (informativo).
        'preco_a_prazo': Decimal | None,
      }
    """
    from app.hora.models import HoraModelo
    from app.hora.models.tagplus import HoraTagPlusFormaPagamentoMap

    if na_data is None:
        na_data = date.today()

    preco, fonte, _tab_id = _buscar_preco_modelo(
        modelo_id, forma_pagamento_hora, na_data,
    )

    tipo = None
    if forma_pagamento_hora:
        forma_norm = forma_pagamento_hora.strip().upper()
        if forma_norm and forma_norm != 'NAO_INFORMADO':
            mapa = HoraTagPlusFormaPagamentoMap.query.filter_by(
                forma_pagamento_hora=forma_norm,
            ).first()
            if mapa is not None:
                tipo = mapa.tipo_pagamento

    modelo = HoraModelo.query.get(modelo_id) if modelo_id else None
    return {
        'preco': preco,
        'fonte': fonte,
        'tipo_pagamento': tipo,
        'preco_a_vista': modelo.preco_a_vista if modelo else None,
        'preco_a_prazo': modelo.preco_a_prazo if modelo else None,
    }


def _resolver_preco_tabela(
    modelo_id: int,
    na_data,
    valor_final: Decimal,
    forma_pagamento_hora: Optional[str] = None,
) -> tuple[Decimal, Decimal, Decimal, Optional[int], Optional[str]]:
    """Retorna (preco_tabela_ref, desconto_rs, desconto_pct, tabela_preco_id, divergencia_tipo).

    `desconto_pct` e Decimal(5,2) — coerente com hora_venda_item.desconto_percentual.
    `divergencia_tipo` (se preenchido) deve ser registrado pelo chamador com
    detalhe apropriado (vence aqui o calculo, nao o registro).

    Assinatura atualizada (migration hora_33): agora aceita `forma_pagamento_hora`
    para escolher entre preco_a_vista / preco_a_prazo do modelo. Callers legacy
    (DANFE import) podem omitir; nesse caso usa fallback prefere-A_VISTA.
    """
    preco_ref, _fonte, tabela_id = _buscar_preco_modelo(
        modelo_id, forma_pagamento_hora, na_data,
    )
    if preco_ref is None:
        return (
            Decimal(str(valor_final)),
            Decimal('0.00'),
            Decimal('0.00'),
            None,
            'TABELA_PRECO_AUSENTE',
        )
    desconto = preco_ref - Decimal(str(valor_final))
    if desconto < 0:
        # Preço final acima da tabela — registra como divergencia, item nao
        # ganha desconto negativo (preserva auditoria).
        return (
            Decimal(str(valor_final)),
            Decimal('0.00'),
            Decimal('0.00'),
            None,
            'PRECO_ACIMA_TABELA',
        )
    if preco_ref > 0:
        pct = (desconto / preco_ref) * Decimal('100')
        pct = pct.quantize(Decimal('0.01'))
    else:
        pct = Decimal('0.00')
    return preco_ref, desconto, pct, tabela_id, None


# --------------------------------------------------------------------------
# Helpers de pagamento (multi-formas — migration hora_34)
# --------------------------------------------------------------------------

def _normalizar_pagamentos(pagamentos: Optional[List[dict]]) -> List[dict]:
    """Sanitiza lista de pagamentos vindas do form/API.

    Cada item de entrada deve ter as chaves:
        forma_pagamento_hora: str (obrigatorio)
        valor: Decimal | str (obrigatorio, > 0)
        numero_parcelas: int (default 1)
        aut_id: str | None (opcional)

    Retorna lista normalizada (forma upper, valor Decimal, parcelas int >= 1,
    aut_id stripped). Pagamentos com `valor <= 0` ou `forma` vazia sao
    descartados silenciosamente.
    """
    if not pagamentos:
        return []
    out: List[dict] = []
    for p in pagamentos:
        forma = (p.get('forma_pagamento_hora') or '').strip().upper()
        if not forma:
            continue
        try:
            valor = Decimal(str(p.get('valor') or '0'))
        except Exception:
            continue
        if valor <= 0:
            continue
        try:
            parcelas = int(p.get('numero_parcelas') or 1)
        except (TypeError, ValueError):
            parcelas = 1
        if parcelas < 1 or parcelas > 60:
            parcelas = 1
        aut = (p.get('aut_id') or '').strip() or None
        out.append({
            'forma_pagamento_hora': forma[:20],
            'valor': valor,
            'numero_parcelas': parcelas,
            'aut_id': aut[:50] if aut else None,
        })
    return out


def _classificar_formas_para_preco(pagamentos: List[dict]) -> Optional[str]:
    """Retorna nome da forma representativa para resolver preco do modelo.

    Regra (decisao do dono em 2026-05-07): se QUALQUER pagamento e A_PRAZO,
    o preco do modelo deve ser A_PRAZO. Senao, A_VISTA. Esta funcao escolhe
    uma forma "vencedora" para passar ao `_buscar_preco_modelo` existente.

    Retorna:
        - Nome de uma forma A_PRAZO se houver alguma na lista.
        - Senao, nome de uma forma A_VISTA se houver.
        - Senao, primeiro nome bruto (caller cai em fallback de tabela legada).
        - None se lista vazia.
    """
    from app.hora.models.tagplus import (
        HoraTagPlusFormaPagamentoMap,
        TIPO_PAGAMENTO_A_PRAZO,
        TIPO_PAGAMENTO_A_VISTA,
    )
    if not pagamentos:
        return None
    nomes = [p['forma_pagamento_hora'] for p in pagamentos]
    mapas = (
        HoraTagPlusFormaPagamentoMap.query
        .filter(HoraTagPlusFormaPagamentoMap.forma_pagamento_hora.in_(nomes))
        .all()
    )
    mapas_por_nome = {m.forma_pagamento_hora: m for m in mapas}
    for nome in nomes:
        m = mapas_por_nome.get(nome)
        if m and m.tipo_pagamento == TIPO_PAGAMENTO_A_PRAZO:
            return nome
    for nome in nomes:
        m = mapas_por_nome.get(nome)
        if m and m.tipo_pagamento == TIPO_PAGAMENTO_A_VISTA:
            return nome
    return nomes[0]


def _avaliar_status_pagamento(
    pagamentos: List[dict],
    valor_total: Decimal,
) -> tuple[str, List[str]]:
    """Decide se a venda nasce COTACAO ou INCOMPLETO baseado nos pagamentos.

    Criterios para INCOMPLETO (qualquer um dispara):
      - lista de pagamentos vazia.
      - soma dos valores != valor_total (tolerancia R$ 0,01 para arred).
      - alguma forma exige_aut_id=True com aut_id vazio/None.

    Returns:
        (status, motivos): status = VENDA_STATUS_COTACAO ou VENDA_STATUS_INCOMPLETO.
        motivos: lista de strings explicativas (vazio se status=COTACAO).
    """
    motivos: List[str] = []
    if not pagamentos:
        motivos.append('Nenhuma forma de pagamento informada.')
        return VENDA_STATUS_INCOMPLETO, motivos

    soma = sum((p['valor'] for p in pagamentos), Decimal('0'))
    diff = (soma - Decimal(str(valor_total))).copy_abs()
    if diff > Decimal('0.01'):
        motivos.append(
            f'Soma das formas de pagamento (R$ {soma}) difere do valor total '
            f'(R$ {valor_total}).'
        )

    # Aut/ID: checar formas com exige_aut_id=True.
    from app.hora.models.tagplus import HoraTagPlusFormaPagamentoMap
    nomes = [p['forma_pagamento_hora'] for p in pagamentos]
    mapas = (
        HoraTagPlusFormaPagamentoMap.query
        .filter(HoraTagPlusFormaPagamentoMap.forma_pagamento_hora.in_(nomes))
        .all()
    )
    mapas_por_nome = {m.forma_pagamento_hora: m for m in mapas}
    for p in pagamentos:
        m = mapas_por_nome.get(p['forma_pagamento_hora'])
        if m and m.exige_aut_id and not p.get('aut_id'):
            motivos.append(
                f'Forma {p["forma_pagamento_hora"]} exige AUT/ID — preencher '
                f'numero de autorizacao.'
            )

    if motivos:
        return VENDA_STATUS_INCOMPLETO, motivos
    return VENDA_STATUS_COTACAO, []


# --------------------------------------------------------------------------
# Fluxo de criacao manual: COTACAO/INCOMPLETO + lock pessimista + RESERVADA
# --------------------------------------------------------------------------

def criar_venda_manual(
    cpf_cliente: str,
    nome_cliente: str,
    cep: Optional[str],
    endereco_logradouro: Optional[str],
    endereco_numero: Optional[str],
    endereco_complemento: Optional[str],
    endereco_bairro: Optional[str],
    endereco_cidade: Optional[str],
    endereco_uf: Optional[str],
    numero_chassi: str,
    valor_final: Decimal,
    forma_pagamento: Optional[str] = None,
    telefone_cliente: Optional[str] = None,
    email_cliente: Optional[str] = None,
    vendedor: Optional[str] = None,
    observacoes: Optional[str] = None,
    modalidade_frete: str = '9',
    numero_parcelas: int = 1,
    intervalo_parcelas_dias: int = 30,
    criado_por: Optional[str] = None,
    loja_id_override: Optional[int] = None,
    pagamentos: Optional[List[dict]] = None,
    consumidor_final: Optional[bool] = None,
) -> HoraVenda:
    """Cria pedido de venda manual em status COTACAO ou INCOMPLETO.

    1. Valida CPF, nome, valor, chassi.
    2. SELECT FOR UPDATE no chassi (impede 2 operadores reservarem o mesmo).
    3. Resolve loja_id da venda (override do form ou loja do chassi).
    4. Multi-formas (migration hora_34): aceita `pagamentos: List[dict]` com
       N formas. Compat: se nao informado mas `forma_pagamento` sim, gera
       1 pagamento sintetico com valor=valor_final.
    5. Resolve preco do modelo: se QUALQUER forma e A_PRAZO -> preco a prazo.
    6. Decide status final via `_avaliar_status_pagamento`:
       - COTACAO se pagamentos validos (soma == valor_total + AUT/ID OK).
       - INCOMPLETO senao (vendedor pode editar e completar depois).
    7. Cria HoraVenda + HoraVendaItem + N HoraVendaPagamento.
    8. Emite evento RESERVADA mesmo em INCOMPLETO (chassi reservado).
    9. Auditoria: CRIOU.

    Args:
        forma_pagamento: legacy. Quando `pagamentos` nao fornecido, gera 1
            pagamento sintetico com essa forma e valor=valor_final. Se ambos
            None, status final sera INCOMPLETO (sem forma).
        pagamentos: lista de dicts com keys forma_pagamento_hora, valor,
            numero_parcelas, aut_id. Soma deve igualar valor_final para sair
            INCOMPLETO. Pagamentos invalidos (valor<=0 ou forma vazia) sao
            descartados.
    """
    # Aceita CPF (11) ou CNPJ (14) — coluna `cpf_cliente` eh String(14) e
    # comporta ambos. Ver app/hora/services/tagplus/_documento.py.
    from app.hora.services.tagplus._documento import (
        inferir_consumidor_final,
        normalizar_documento,
    )
    cpf_norm, _tipo_doc = normalizar_documento(cpf_cliente)
    if not _tipo_doc:
        raise ValueError(
            f'Documento invalido: {cpf_cliente!r} '
            f'(esperado CPF com 11 digitos ou CNPJ com 14 digitos)'
        )

    nome_norm = (nome_cliente or '').strip()
    if not nome_norm:
        raise ValueError('Nome do cliente obrigatorio')

    if valor_final is None or Decimal(valor_final) <= 0:
        raise ValueError('Valor final deve ser maior que zero')

    valor_final_dec_pre = Decimal(str(valor_final))

    # Compat: se `pagamentos` nao foi fornecido mas `forma_pagamento` sim,
    # cria pagamento sintetico (1 forma com valor=valor_final). Se nem um
    # nem outro, lista fica vazia -> status final sera INCOMPLETO.
    pagamentos_norm = _normalizar_pagamentos(pagamentos)
    if not pagamentos_norm and forma_pagamento:
        forma_legacy = (forma_pagamento or '').strip().upper()
        if forma_legacy and forma_legacy != 'NAO_INFORMADO':
            pagamentos_norm = [{
                'forma_pagamento_hora': forma_legacy[:20],
                'valor': valor_final_dec_pre,
                'numero_parcelas': max(1, int(numero_parcelas or 1)),
                'aut_id': None,
            }]

    # Forma representativa para resolucao de preco (qualquer A_PRAZO -> A_PRAZO).
    forma_para_preco = _classificar_formas_para_preco(pagamentos_norm)

    # forma_pagamento legacy (cache em HoraVenda): MISTO se >1 forma distinta;
    # senao, a unica forma; senao, 'NAO_INFORMADO'.
    formas_distintas = {p['forma_pagamento_hora'] for p in pagamentos_norm}
    if len(formas_distintas) >= 2:
        forma_norm = 'MISTO'
    elif len(formas_distintas) == 1:
        forma_norm = next(iter(formas_distintas))
    else:
        forma_norm = 'NAO_INFORMADO'

    mod_frete = (modalidade_frete or '9').strip()
    if mod_frete not in ('0', '1', '2', '3', '4', '9'):
        raise ValueError(
            f'modalidade_frete invalida: {modalidade_frete!r} '
            f"(esperado '0','1','2','3','4','9')"
        )
    n_parcelas = int(numero_parcelas or 1)
    if n_parcelas < 1 or n_parcelas > 60:
        raise ValueError(
            f'numero_parcelas fora do intervalo 1..60: {numero_parcelas!r}'
        )
    intervalo = int(intervalo_parcelas_dias or 30)
    if intervalo < 1 or intervalo > 90:
        raise ValueError(
            f'intervalo_parcelas_dias fora do intervalo 1..90: {intervalo_parcelas_dias!r}'
        )

    moto, ult = _lock_chassi_e_validar_disponivel(numero_chassi)
    chassi_norm = moto.numero_chassi
    loja_id_chassi = ult.loja_id
    if not loja_id_chassi:
        raise ValueError(
            f'Chassi {chassi_norm} sem loja definida no ultimo evento — '
            f'investigar inconsistencia em hora_moto_evento.'
        )

    # Loja oficial da venda: override do form (se fornecido) OU loja do chassi.
    # Quando override e diferente da loja fisica do chassi, equivale a uma
    # transferencia implicita: o evento RESERVADA gravado abaixo move o chassi
    # para a loja escolhida (sem evento TRANSFERIDA formal). Decisao de
    # negocio: usuario optou por nao restringir a coerencia loja-chassi.
    loja_id = (
        int(loja_id_override) if loja_id_override is not None else int(loja_id_chassi)
    )

    cep_norm = ''.join(c for c in (cep or '') if c.isdigit()) or None
    if cep_norm and len(cep_norm) != 8:
        raise ValueError(f'CEP invalido: {cep!r} (esperado 8 digitos)')
    cep_formatado = f'{cep_norm[:5]}-{cep_norm[5:]}' if cep_norm else None
    uf_norm = (endereco_uf or '').strip().upper() or None
    if uf_norm and len(uf_norm) != 2:
        raise ValueError(f'UF invalido: {endereco_uf!r} (esperado 2 letras)')

    valor_final_dec = Decimal(str(valor_final))
    data_venda = date.today()
    (
        preco_tabela_ref, desconto, desconto_pct,
        tabela_preco_id, divergencia_tipo,
    ) = _resolver_preco_tabela(
        moto.modelo_id, data_venda, valor_final_dec,
        forma_pagamento_hora=forma_para_preco,
    )

    # Status final: COTACAO se pagamentos consistentes, senao INCOMPLETO.
    # INCOMPLETO ainda reserva chassi; bloqueia confirmar/emitir NFe.
    status_final, motivos_incompleto = _avaliar_status_pagamento(
        pagamentos_norm, valor_final_dec,
    )

    venda = HoraVenda(
        loja_id=loja_id,
        cpf_cliente=cpf_norm,
        nome_cliente=nome_norm[:200],
        telefone_cliente=(telefone_cliente or '').strip()[:20] or None,
        email_cliente=(email_cliente or '').strip()[:120] or None,
        data_venda=data_venda,
        forma_pagamento=forma_norm[:20],
        valor_total=valor_final_dec,
        nf_saida_numero=None,
        nf_saida_chave_44=None,
        nf_saida_emitida_em=None,
        arquivo_pdf_s3_key=None,
        parser_usado=None,
        parseada_em=None,
        cnpj_emitente=None,
        status=status_final,
        vendedor=(vendedor or '').strip()[:100] or None,
        observacoes=(observacoes or '').strip() or None,
        cep=cep_formatado,
        endereco_logradouro=(endereco_logradouro or '').strip()[:255] or None,
        endereco_numero=(endereco_numero or '').strip()[:20] or None,
        endereco_complemento=(endereco_complemento or '').strip()[:100] or None,
        endereco_bairro=(endereco_bairro or '').strip()[:100] or None,
        endereco_cidade=(endereco_cidade or '').strip()[:100] or None,
        endereco_uf=uf_norm,
        origem_criacao='MANUAL',
        modalidade_frete=mod_frete,
        numero_parcelas=n_parcelas,
        intervalo_parcelas_dias=intervalo,
        # consumidor_final: se nao explicito, infere via tipo de documento
        # (CPF=True / CNPJ=False). Operador pode sobrescrever na tela de
        # detalhe enquanto pedido estiver em COTACAO ou CONFIRMADO.
        consumidor_final=(
            bool(consumidor_final) if consumidor_final is not None
            else inferir_consumidor_final(cpf_norm)
        ),
    )
    db.session.add(venda)
    db.session.flush()

    venda_item = HoraVendaItem(
        venda_id=venda.id,
        numero_chassi=chassi_norm,
        tabela_preco_id=tabela_preco_id,
        preco_tabela_referencia=preco_tabela_ref,
        desconto_aplicado=desconto,
        desconto_percentual=desconto_pct,
        preco_final=valor_final_dec,
    )
    db.session.add(venda_item)
    db.session.flush()

    if divergencia_tipo:
        if divergencia_tipo == 'PRECO_ACIMA_TABELA':
            _registrar_divergencia(
                venda_id=venda.id, tipo=divergencia_tipo,
                numero_chassi=chassi_norm,
                detalhe=(
                    f'Preco final R${valor_final_dec} > tabela vigente. '
                    'Item gravado sem desconto negativo.'
                ),
                valor_conferido=str(valor_final_dec),
            )
        else:
            _registrar_divergencia(
                venda_id=venda.id, tipo=divergencia_tipo,
                numero_chassi=chassi_norm,
                detalhe=f'Sem HoraTabelaPreco vigente para modelo {moto.modelo_id}.',
                valor_conferido=str(valor_final_dec),
            )

    # Persistencia das N formas de pagamento (multi-formas).
    for p in pagamentos_norm:
        db.session.add(HoraVendaPagamento(
            venda_id=venda.id,
            forma_pagamento_hora=p['forma_pagamento_hora'],
            valor=p['valor'],
            numero_parcelas=p['numero_parcelas'],
            aut_id=p['aut_id'],
        ))
    if pagamentos_norm:
        db.session.flush()

    # Evento RESERVADA: tira chassi do estoque disponivel — emitido mesmo em
    # INCOMPLETO (a reserva e' valida; a venda e' que ainda esta a completar).
    registrar_evento(
        numero_chassi=chassi_norm,
        tipo='RESERVADA',
        origem_tabela='hora_venda_item',
        origem_id=venda_item.id,
        loja_id=loja_id,
        operador=criado_por,
        detalhe=f'Pedido #{venda.id} ({status_final}) para {nome_norm} CPF {cpf_norm}',
    )

    detalhe_audit = (
        f'Pedido manual ({status_final}) chassi={chassi_norm} '
        f'cliente={nome_norm} valor={valor_final_dec}'
    )
    if motivos_incompleto:
        detalhe_audit += f' INCOMPLETO: {"; ".join(motivos_incompleto)}'
    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=criado_por or '',
        acao='CRIOU',
        detalhe=detalhe_audit,
    )

    db.session.commit()
    return venda


# --------------------------------------------------------------------------
# Confirmacao: COTACAO -> CONFIRMADO
# --------------------------------------------------------------------------

def confirmar_venda(venda_id: int, usuario: Optional[str] = None) -> HoraVenda:
    """Transiciona pedido de COTACAO para CONFIRMADO.

    Mantem evento RESERVADA (chassi continua reservado). Registra auditoria.
    """
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    if venda.status == VENDA_STATUS_INCOMPLETO:
        raise TransicaoInvalidaError(
            f'Pedido {venda_id} esta INCOMPLETO — complete formas de pagamento '
            f'(soma == valor total + AUT/ID quando exigido) antes de confirmar.'
        )
    if venda.status != VENDA_STATUS_COTACAO:
        raise TransicaoInvalidaError(
            f'Pedido {venda_id} esta em {venda.status}; so COTACAO pode ser confirmado.'
        )
    if venda.tem_divergencia_aberta:
        # Politica: divergencias podem ser confirmadas, mas operador deve ter
        # marcado-as como resolvidas antes (sao avisos, nao bloqueios).
        # Nao bloqueamos aqui — alinhado com fluxo permissivo do import DANFE.
        pass

    venda.status = VENDA_STATUS_CONFIRMADO
    venda.confirmado_em = agora_utc_naive()
    venda.confirmado_por = usuario or 'desconhecido'

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='CONFIRMOU',
        detalhe=f'Pedido confirmado ({len(venda.itens)} chassi(s)).',
    )

    db.session.commit()
    return venda


def editar_pagamentos(
    venda_id: int,
    pagamentos: List[dict],
    usuario: Optional[str] = None,
) -> HoraVenda:
    """Substitui as formas de pagamento de uma venda e re-avalia status.

    Permitido em status INCOMPLETO ou COTACAO (vendedor completando ou
    ajustando antes de confirmar). Bloqueado em CONFIRMADO/FATURADO/CANCELADO.

    Mecanica:
      1. Apaga HoraVendaPagamento existentes da venda.
      2. Cria os novos a partir de `pagamentos` (normalizados).
      3. Re-avalia status via _avaliar_status_pagamento (INCOMPLETO ou COTACAO).
      4. Atualiza HoraVenda.forma_pagamento legacy (MISTO se >1 forma).
      5. Auditoria EDITOU_HEADER.

    Args:
        pagamentos: lista [{forma_pagamento_hora, valor, numero_parcelas, aut_id}].
    """
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    if venda.status not in (VENDA_STATUS_INCOMPLETO, VENDA_STATUS_COTACAO):
        raise TransicaoInvalidaError(
            f'Pedido {venda_id} esta em {venda.status}; pagamentos so podem ser '
            f'editados em INCOMPLETO ou COTACAO.'
        )

    pagamentos_norm = _normalizar_pagamentos(pagamentos)
    valor_total_dec = Decimal(str(venda.valor_total))

    novo_status, motivos = _avaliar_status_pagamento(pagamentos_norm, valor_total_dec)

    # Apaga pagamentos atuais e recria.
    HoraVendaPagamento.query.filter_by(venda_id=venda.id).delete()
    db.session.flush()
    for p in pagamentos_norm:
        db.session.add(HoraVendaPagamento(
            venda_id=venda.id,
            forma_pagamento_hora=p['forma_pagamento_hora'],
            valor=p['valor'],
            numero_parcelas=p['numero_parcelas'],
            aut_id=p['aut_id'],
        ))

    # forma_pagamento legacy (cache).
    formas_distintas = {p['forma_pagamento_hora'] for p in pagamentos_norm}
    if len(formas_distintas) >= 2:
        venda.forma_pagamento = 'MISTO'
    elif len(formas_distintas) == 1:
        venda.forma_pagamento = next(iter(formas_distintas))[:20]
    else:
        venda.forma_pagamento = 'NAO_INFORMADO'

    status_antes = venda.status
    venda.status = novo_status

    detalhe = (
        f'Pagamentos editados: {len(pagamentos_norm)} forma(s). '
        f'Status {status_antes}->{novo_status}.'
    )
    if motivos:
        detalhe += ' Motivos INCOMPLETO: ' + '; '.join(motivos)
    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='EDITOU_HEADER',
        campo_alterado='pagamentos',
        detalhe=detalhe,
    )

    db.session.commit()
    return venda


def voltar_para_cotacao(venda_id: int, usuario: Optional[str] = None) -> HoraVenda:
    """Reverte CONFIRMADO -> COTACAO para permitir edicao de itens.

    Bloqueado se houver emissao TagPlus em estado em-voo ou aprovada — nesses
    casos cancele a NFe primeiro. Registra auditoria.
    """
    from app.hora.models.tagplus import HoraTagPlusNfeEmissao

    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    if venda.status != VENDA_STATUS_CONFIRMADO:
        raise TransicaoInvalidaError(
            f'Pedido {venda_id} esta em {venda.status}; so CONFIRMADO pode voltar para COTACAO.'
        )

    emissao = HoraTagPlusNfeEmissao.query.filter_by(venda_id=venda.id).first()
    estados_bloqueio = (
        'EM_ENVIO', 'ENVIADA_SEFAZ', 'APROVADA',
        'CANCELAMENTO_SOLICITADO',
    )
    if emissao and emissao.status in estados_bloqueio:
        raise TransicaoInvalidaError(
            f'Pedido tem emissao NFe em status {emissao.status}; '
            f'cancele a NFe na SEFAZ antes de voltar para cotacao.'
        )

    venda.status = VENDA_STATUS_COTACAO
    venda.confirmado_em = None
    venda.confirmado_por = None

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='VOLTOU_PARA_COTACAO',
        detalhe='Pedido revertido CONFIRMADO -> COTACAO para edicao.',
    )

    db.session.commit()
    return venda


# --------------------------------------------------------------------------
# Edicao do header (vendedor, contato, endereco, observacoes, forma_pagamento)
# --------------------------------------------------------------------------

# Campos editaveis em cada status. FATURADO so permite observacoes.
# INCOMPLETO usa o mesmo conjunto de COTACAO — pedido em INCOMPLETO precisa
# ser livremente editavel para o vendedor corrigir cliente/endereco/etc.
# antes de promover via editar_pagamentos.
_CAMPOS_COTACAO_FULL = {
    'vendedor', 'forma_pagamento', 'telefone_cliente', 'email_cliente',
    'observacoes', 'nome_cliente', 'cpf_cliente',
    'cep', 'endereco_logradouro', 'endereco_numero', 'endereco_complemento',
    'endereco_bairro', 'endereco_cidade', 'endereco_uf',
    'modalidade_frete', 'numero_parcelas', 'intervalo_parcelas_dias',
    'consumidor_final',
}
_CAMPOS_EDITAVEIS_HEADER = {
    VENDA_STATUS_INCOMPLETO: _CAMPOS_COTACAO_FULL,
    VENDA_STATUS_COTACAO: _CAMPOS_COTACAO_FULL,
    VENDA_STATUS_CONFIRMADO: {
        'vendedor', 'forma_pagamento', 'telefone_cliente', 'email_cliente',
        'observacoes',
        'cep', 'endereco_logradouro', 'endereco_numero', 'endereco_complemento',
        'endereco_bairro', 'endereco_cidade', 'endereco_uf',
        'modalidade_frete', 'numero_parcelas', 'intervalo_parcelas_dias',
        # consumidor_final permanece editavel ate FATURADO porque influencia
        # diretamente o payload da NFe ainda nao enviada.
        'consumidor_final',
    },
    VENDA_STATUS_FATURADO: {'observacoes'},
    VENDA_STATUS_CANCELADO: set(),
}


def _validar_campo_editavel(venda: HoraVenda, campo: str) -> None:
    permitidos = _CAMPOS_EDITAVEIS_HEADER.get(venda.status, set())
    if campo not in permitidos:
        raise TransicaoInvalidaError(
            f'Campo {campo!r} nao pode ser editado em pedido {venda.status}. '
            f'Campos permitidos: {sorted(permitidos) or "(nenhum)"}'
        )
    # Defesa adicional: se ha NFe em-voo, bloqueia edicao livre.
    emissao = _emissao_nfe(venda.id)
    if emissao and emissao.status in _NFE_EM_VOO and campo != 'observacoes':
        raise TransicaoInvalidaError(
            f'NFe em estado {emissao.status} — apenas observacoes editaveis.'
        )


def editar_venda(
    venda_id: int,
    vendedor: Optional[str] = None,
    forma_pagamento: Optional[str] = None,
    telefone_cliente: Optional[str] = None,
    email_cliente: Optional[str] = None,
    observacoes: Optional[str] = None,
    nome_cliente: Optional[str] = None,
    cpf_cliente: Optional[str] = None,
    cep: Optional[str] = None,
    endereco_logradouro: Optional[str] = None,
    endereco_numero: Optional[str] = None,
    endereco_complemento: Optional[str] = None,
    endereco_bairro: Optional[str] = None,
    endereco_cidade: Optional[str] = None,
    endereco_uf: Optional[str] = None,
    modalidade_frete: Optional[str] = None,
    numero_parcelas: Optional[int] = None,
    intervalo_parcelas_dias: Optional[int] = None,
    consumidor_final: Optional[bool] = None,
    usuario: Optional[str] = None,
) -> HoraVenda:
    """Edita campos do header conforme regra por status.

    - COTACAO: tudo (incluindo cliente/endereco e consumidor_final).
    - CONFIRMADO: contato/endereco/operacionais + consumidor_final (sem mexer
      em CPF/nome — sao do payload TagPlus).
    - FATURADO: so observacoes.
    - CANCELADO: nada (raise).
    """
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    if venda.status == VENDA_STATUS_CANCELADO:
        raise TransicaoInvalidaError('Pedido cancelado nao pode ser editado.')

    def _atualizar(campo: str, novo_valor):
        antes = getattr(venda, campo)
        if novo_valor == antes:
            return
        _validar_campo_editavel(venda, campo)
        setattr(venda, campo, novo_valor)
        venda_audit.registrar_auditoria(
            venda_id=venda.id, usuario=usuario or '',
            acao='EDITOU_HEADER',
            campo_alterado=campo,
            valor_antes=antes,
            valor_depois=novo_valor,
        )

    if vendedor is not None:
        _atualizar('vendedor', (vendedor.strip()[:100] or None))
    if forma_pagamento is not None:
        fp_norm = (forma_pagamento or '').strip().upper() or 'NAO_INFORMADO'
        _atualizar('forma_pagamento', fp_norm[:20])
    if telefone_cliente is not None:
        _atualizar('telefone_cliente', telefone_cliente.strip()[:20] or None)
    if email_cliente is not None:
        _atualizar('email_cliente', email_cliente.strip()[:120] or None)
    if observacoes is not None:
        _atualizar('observacoes', observacoes.strip() or None)
    if nome_cliente is not None:
        _atualizar('nome_cliente', nome_cliente.strip()[:200] or venda.nome_cliente)
    if cpf_cliente is not None:
        # Aceita CPF (11) ou CNPJ (14). String vazia mantem valor anterior.
        from app.hora.services.tagplus._documento import normalizar_documento
        cpf_norm, _tipo_doc = normalizar_documento(cpf_cliente)
        if cpf_norm and not _tipo_doc:
            raise ValueError(
                f'Documento invalido: {cpf_cliente!r} '
                f'(esperado CPF com 11 digitos ou CNPJ com 14 digitos)'
            )
        _atualizar('cpf_cliente', cpf_norm or venda.cpf_cliente)
    if cep is not None:
        cep_norm = ''.join(c for c in cep if c.isdigit()) or None
        if cep_norm and len(cep_norm) != 8:
            raise ValueError(f'CEP invalido: {cep!r}')
        _atualizar('cep', f'{cep_norm[:5]}-{cep_norm[5:]}' if cep_norm else None)
    if endereco_logradouro is not None:
        _atualizar('endereco_logradouro', endereco_logradouro.strip()[:255] or None)
    if endereco_numero is not None:
        _atualizar('endereco_numero', endereco_numero.strip()[:20] or None)
    if endereco_complemento is not None:
        _atualizar('endereco_complemento', endereco_complemento.strip()[:100] or None)
    if endereco_bairro is not None:
        _atualizar('endereco_bairro', endereco_bairro.strip()[:100] or None)
    if endereco_cidade is not None:
        _atualizar('endereco_cidade', endereco_cidade.strip()[:100] or None)
    if endereco_uf is not None:
        uf_norm = endereco_uf.strip().upper() or None
        if uf_norm and len(uf_norm) != 2:
            raise ValueError(f'UF invalido: {endereco_uf!r}')
        _atualizar('endereco_uf', uf_norm)
    if modalidade_frete is not None:
        mod_norm = (modalidade_frete or '').strip()
        if mod_norm not in ('0', '1', '2', '3', '4', '9'):
            raise ValueError(
                f'modalidade_frete invalida: {modalidade_frete!r} '
                f"(esperado '0','1','2','3','4','9')"
            )
        _atualizar('modalidade_frete', mod_norm)
    if numero_parcelas is not None:
        try:
            n = int(numero_parcelas)
        except (TypeError, ValueError):
            raise ValueError(f'numero_parcelas invalido: {numero_parcelas!r}')
        if n < 1 or n > 60:
            raise ValueError(
                f'numero_parcelas fora do intervalo 1..60: {n}'
            )
        _atualizar('numero_parcelas', n)
    if intervalo_parcelas_dias is not None:
        try:
            d = int(intervalo_parcelas_dias)
        except (TypeError, ValueError):
            raise ValueError(
                f'intervalo_parcelas_dias invalido: {intervalo_parcelas_dias!r}'
            )
        if d < 1 or d > 90:
            raise ValueError(
                f'intervalo_parcelas_dias fora do intervalo 1..90: {d}'
            )
        _atualizar('intervalo_parcelas_dias', d)
    if consumidor_final is not None:
        _atualizar('consumidor_final', bool(consumidor_final))

    db.session.commit()
    return venda


# --------------------------------------------------------------------------
# Edicao de itens — so em COTACAO
# --------------------------------------------------------------------------

def _exigir_cotacao(venda: HoraVenda, acao: str) -> None:
    if venda.status != VENDA_STATUS_COTACAO:
        raise TransicaoInvalidaError(
            f'{acao} so e permitido em pedido COTACAO (atual: {venda.status}).'
        )


def adicionar_item_pedido(
    venda_id: int,
    numero_chassi: str,
    valor_final: Decimal,
    usuario: Optional[str] = None,
) -> HoraVendaItem:
    """Adiciona item ao pedido em COTACAO. Lock pessimista no chassi."""
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    _exigir_cotacao(venda, 'Adicionar item')

    if valor_final is None or Decimal(valor_final) <= 0:
        raise ValueError('Valor final deve ser maior que zero')

    moto, ult = _lock_chassi_e_validar_disponivel(numero_chassi)
    chassi_norm = moto.numero_chassi
    if ult.loja_id and venda.loja_id and ult.loja_id != venda.loja_id:
        raise ValueError(
            f'Chassi {chassi_norm} esta na loja {ult.loja_id}, mas pedido e da '
            f'loja {venda.loja_id} — adicione um chassi da mesma loja.'
        )

    valor_final_dec = Decimal(str(valor_final))
    preco_ref, desconto, desconto_pct, tabela_id, _ = _resolver_preco_tabela(
        moto.modelo_id, venda.data_venda, valor_final_dec,
        forma_pagamento_hora=venda.forma_pagamento,
    )

    item = HoraVendaItem(
        venda_id=venda.id,
        numero_chassi=chassi_norm,
        tabela_preco_id=tabela_id,
        preco_tabela_referencia=preco_ref,
        desconto_aplicado=desconto,
        desconto_percentual=desconto_pct,
        preco_final=valor_final_dec,
    )
    db.session.add(item)
    db.session.flush()

    registrar_evento(
        numero_chassi=chassi_norm,
        tipo='RESERVADA',
        origem_tabela='hora_venda_item',
        origem_id=item.id,
        loja_id=venda.loja_id or ult.loja_id,
        operador=usuario,
        detalhe=f'Pedido #{venda.id} item adicionado',
    )

    # Atualiza valor_total (header).
    venda.valor_total = Decimal(str(venda.valor_total)) + valor_final_dec

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='ADICIONOU_ITEM', item_id=item.id,
        detalhe=f'chassi={chassi_norm} valor={valor_final_dec}',
    )

    db.session.commit()
    return item


def remover_item_pedido(
    venda_id: int,
    item_id: int,
    usuario: Optional[str] = None,
) -> HoraVenda:
    """Remove item do pedido em COTACAO. Emite evento DEVOLVIDA no chassi."""
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    _exigir_cotacao(venda, 'Remover item')

    item = HoraVendaItem.query.get(item_id)
    if not item or item.venda_id != venda.id:
        raise ValueError(f'Item {item_id} nao pertence ao pedido {venda_id}')

    if len(venda.itens) <= 1:
        raise ValueError('Pedido deve ter ao menos 1 item — cancele o pedido em vez de remover o ultimo item.')

    chassi = item.numero_chassi
    valor_removido = Decimal(str(item.preco_final))

    # Devolve chassi ao estoque (evento DEVOLVIDA).
    registrar_evento(
        numero_chassi=chassi,
        tipo='DEVOLVIDA',
        origem_tabela='hora_venda_item',
        origem_id=item.id,
        loja_id=venda.loja_id,
        operador=usuario,
        detalhe=f'Item removido do pedido #{venda.id} (COTACAO)',
    )

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='REMOVEU_ITEM', item_id=item.id,
        detalhe=f'chassi={chassi} valor={valor_removido}',
    )

    db.session.delete(item)
    venda.valor_total = Decimal(str(venda.valor_total)) - valor_removido

    db.session.commit()
    return venda


def editar_item_pedido(
    venda_id: int,
    item_id: int,
    novo_chassi: Optional[str] = None,
    novo_valor: Optional[Decimal] = None,
    usuario: Optional[str] = None,
) -> HoraVendaItem:
    """Edita item: troca chassi e/ou ajusta preco. So em COTACAO.

    Trocar chassi: emite DEVOLVIDA no antigo + RESERVADA no novo (com lock).
    """
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    _exigir_cotacao(venda, 'Editar item')

    item = HoraVendaItem.query.get(item_id)
    if not item or item.venda_id != venda.id:
        raise ValueError(f'Item {item_id} nao pertence ao pedido {venda_id}')

    chassi_atual = item.numero_chassi
    valor_atual = Decimal(str(item.preco_final))

    chassi_alvo = (novo_chassi or '').strip().upper() or None
    valor_alvo = Decimal(str(novo_valor)) if novo_valor is not None else None

    if not chassi_alvo and valor_alvo is None:
        return item  # nada a fazer

    if valor_alvo is not None and valor_alvo <= 0:
        raise ValueError('Valor final deve ser maior que zero')

    # Troca de chassi.
    if chassi_alvo and chassi_alvo != chassi_atual:
        moto, ult = _lock_chassi_e_validar_disponivel(chassi_alvo)
        if ult.loja_id and venda.loja_id and ult.loja_id != venda.loja_id:
            raise ValueError(
                f'Chassi {chassi_alvo} esta na loja {ult.loja_id}; pedido e da '
                f'loja {venda.loja_id}.'
            )
        # Devolve antigo.
        registrar_evento(
            numero_chassi=chassi_atual,
            tipo='DEVOLVIDA',
            origem_tabela='hora_venda_item',
            origem_id=item.id,
            loja_id=venda.loja_id,
            operador=usuario,
            detalhe=f'Substituido por {chassi_alvo} no pedido #{venda.id}',
        )
        # Reserva novo.
        registrar_evento(
            numero_chassi=chassi_alvo,
            tipo='RESERVADA',
            origem_tabela='hora_venda_item',
            origem_id=item.id,
            loja_id=venda.loja_id or ult.loja_id,
            operador=usuario,
            detalhe=f'Substituido a partir de {chassi_atual} no pedido #{venda.id}',
        )
        venda_audit.registrar_auditoria(
            venda_id=venda.id, usuario=usuario or '',
            acao='EDITOU_ITEM', item_id=item.id,
            campo_alterado='numero_chassi',
            valor_antes=chassi_atual, valor_depois=chassi_alvo,
        )
        item.numero_chassi = chassi_alvo
        # Re-resolve preco_tabela com modelo do novo chassi.
        preco_ref, desconto, desconto_pct, tabela_id, _ = _resolver_preco_tabela(
            moto.modelo_id, venda.data_venda, valor_alvo or valor_atual,
            forma_pagamento_hora=venda.forma_pagamento,
        )
        item.tabela_preco_id = tabela_id
        item.preco_tabela_referencia = preco_ref
        item.desconto_aplicado = desconto
        item.desconto_percentual = desconto_pct

    # Mudanca de valor.
    if valor_alvo is not None and valor_alvo != valor_atual:
        # Re-resolve preco_tabela apenas para ajustar desconto (mesmo modelo).
        moto = HoraMoto.query.get(item.numero_chassi)
        if moto:
            preco_ref, desconto, desconto_pct, tabela_id, _ = _resolver_preco_tabela(
                moto.modelo_id, venda.data_venda, valor_alvo,
                forma_pagamento_hora=venda.forma_pagamento,
            )
            item.tabela_preco_id = tabela_id
            item.preco_tabela_referencia = preco_ref
            item.desconto_aplicado = desconto
            item.desconto_percentual = desconto_pct
        item.preco_final = valor_alvo
        venda.valor_total = Decimal(str(venda.valor_total)) - valor_atual + valor_alvo
        venda_audit.registrar_auditoria(
            venda_id=venda.id, usuario=usuario or '',
            acao='EDITOU_ITEM', item_id=item.id,
            campo_alterado='preco_final',
            valor_antes=valor_atual, valor_depois=valor_alvo,
        )

    db.session.commit()
    return item


# --------------------------------------------------------------------------
# Cancelamento de pedido
# --------------------------------------------------------------------------

def cancelar_venda(
    venda_id: int,
    motivo: str,
    usuario: Optional[str] = None,
) -> HoraVenda:
    """Cancela pedido. Reage ao status atual e ao estado da NFe.

    Regras de bloqueio:
      - Se NFe em estado em-voo (EM_ENVIO / ENVIADA_SEFAZ /
        CANCELAMENTO_SOLICITADO): aguardar resolucao, nao aceita.
      - Se NFe APROVADA: exige que ja tenha sido cancelada na SEFAZ
        (status CANCELADA). Operador deve cancelar a NFe primeiro
        (rota /vendas/<id>/nfe/cancelar), aguardar webhook nfe_cancelada,
        e so depois cancelar o pedido.
      - Se status ja CANCELADO: idempotente.

    Efeito:
      - status -> CANCELADO, marcadores cancelado_em/por/motivo preenchidos.
      - Para cada chassi do pedido: emite DEVOLVIDA (devolve ao estoque
        disponivel).
      - Auditoria: CANCELOU.
    """
    motivo_limpo = (motivo or '').strip()
    if len(motivo_limpo) < 3:
        raise ValueError('Motivo obrigatorio (min 3 chars)')

    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    if venda.status == VENDA_STATUS_CANCELADO:
        return venda

    emissao = _emissao_nfe(venda.id)
    if emissao:
        if emissao.status in _NFE_EM_VOO:
            raise TransicaoInvalidaError(
                f'NFe em estado {emissao.status} — aguarde resolucao SEFAZ '
                'antes de cancelar o pedido.'
            )
        if emissao.status == NFE_STATUS_APROVADA:
            raise TransicaoInvalidaError(
                'NFe esta APROVADA — cancele a NFe primeiro (janela 24h SEFAZ) '
                'e aguarde a confirmacao SEFAZ antes de cancelar o pedido.'
            )
        # NFe em REJEITADA_LOCAL/SEFAZ/ERRO_INFRA/CANCELADA: pode cancelar pedido livre.

    venda.status = VENDA_STATUS_CANCELADO
    venda.cancelado_em = agora_utc_naive()
    venda.cancelado_por = usuario or 'desconhecido'
    venda.cancelamento_motivo = motivo_limpo[:500]

    for item in venda.itens:
        registrar_evento(
            numero_chassi=item.numero_chassi,
            tipo='DEVOLVIDA',
            origem_tabela='hora_venda',
            origem_id=venda.id,
            loja_id=venda.loja_id,
            operador=usuario,
            detalhe=f'Pedido #{venda.id} cancelado: {motivo_limpo[:180]}',
        )

    # Devolve pecas ao estoque (DEVOLUCAO_VENDA).
    if venda.itens_peca:
        from app.hora.services import peca_estoque_service
        for ip in venda.itens_peca:
            peca_estoque_service.registrar_movimento(
                peca_id=ip.peca_id, loja_id=venda.loja_id,
                tipo='DEVOLUCAO_VENDA', qtd=Decimal(str(ip.qtd)),
                ref_tabela='hora_venda_item_peca', ref_id=ip.id,
                motivo=f'Pedido #{venda.id} cancelado',
                operador=usuario,
            )

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='CANCELOU',
        detalhe=motivo_limpo[:500],
    )

    db.session.commit()
    return venda


# --------------------------------------------------------------------------
# Itens PECA em pedido de venda
# --------------------------------------------------------------------------

def adicionar_item_peca(
    venda_id: int,
    peca_id: int,
    qtd,
    valor_unitario_final,
    usuario: Optional[str] = None,
) -> 'HoraVendaItemPeca':
    """Adiciona peca em pedido COTACAO. Emite SAIDA_VENDA na loja do pedido.

    Validacoes:
    - status precisa ser COTACAO
    - peca_id existe
    - qtd > 0 e valor_unitario_final > 0
    - venda.loja_id definido
    - saldo na loja suficiente
    """
    from app.hora.models import HoraVenda, HoraVendaItemPeca, HoraPeca
    from app.hora.services import peca_estoque_service

    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    _exigir_cotacao(venda, 'Adicionar peca')

    peca = HoraPeca.query.get(peca_id)
    if not peca:
        raise ValueError(f'Peca {peca_id} nao existe')
    qtd_dec = Decimal(str(qtd or 0))
    if qtd_dec <= 0:
        raise ValueError('qtd deve ser positiva')
    valor_uni = Decimal(str(valor_unitario_final or 0))
    if valor_uni <= 0:
        raise ValueError('valor_unitario_final deve ser positivo')

    if not venda.loja_id:
        raise ValueError('Venda sem loja_id - defina loja antes de adicionar pecas')
    saldo_atual = peca_estoque_service.saldo(peca.id, venda.loja_id)
    if saldo_atual < qtd_dec:
        raise ValueError(
            f'Saldo insuficiente: loja {venda.loja_id} tem {saldo_atual} {peca.unidade}, '
            f'pedido exige {qtd_dec}'
        )

    preco_ref = Decimal(str(peca.preco_venda_padrao))
    desconto_uni = max(Decimal('0'), preco_ref - valor_uni)
    preco_final_total = qtd_dec * valor_uni

    item = HoraVendaItemPeca(
        venda_id=venda.id, peca_id=peca.id, qtd=qtd_dec,
        preco_unitario_referencia=preco_ref,
        desconto_aplicado=desconto_uni,
        preco_final=preco_final_total,
    )
    db.session.add(item)
    db.session.flush()

    peca_estoque_service.registrar_movimento(
        peca_id=peca.id, loja_id=venda.loja_id,
        tipo='SAIDA_VENDA', qtd=-qtd_dec,
        ref_tabela='hora_venda_item_peca', ref_id=item.id,
        motivo=f'Pedido #{venda.id}', operador=usuario,
    )

    venda.valor_total = Decimal(str(venda.valor_total)) + preco_final_total
    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='ADICIONOU_ITEM_PECA',
        detalhe=f'peca={peca.codigo_interno} qtd={qtd_dec} total={preco_final_total}',
    )
    db.session.commit()
    return item


def remover_item_peca(venda_id: int, item_id: int, usuario: Optional[str] = None) -> None:
    """Remove peca de pedido COTACAO. Emite DEVOLUCAO_VENDA (devolve estoque)."""
    from app.hora.models import HoraVenda, HoraVendaItemPeca
    from app.hora.services import peca_estoque_service

    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    _exigir_cotacao(venda, 'Remover peca')

    item = HoraVendaItemPeca.query.get(item_id)
    if not item or item.venda_id != venda.id:
        raise ValueError(f'Item peca {item_id} nao pertence ao pedido {venda_id}')

    peca_estoque_service.registrar_movimento(
        peca_id=item.peca_id, loja_id=venda.loja_id,
        tipo='DEVOLUCAO_VENDA', qtd=Decimal(str(item.qtd)),
        ref_tabela='hora_venda_item_peca', ref_id=item.id,
        motivo=f'Item peca removido do pedido #{venda.id}',
        operador=usuario,
    )

    venda.valor_total = Decimal(str(venda.valor_total)) - Decimal(str(item.preco_final))
    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='REMOVEU_ITEM_PECA',
        detalhe=f'peca={item.peca.codigo_interno} qtd={item.qtd}',
    )
    db.session.delete(item)
    db.session.commit()


# --------------------------------------------------------------------------
# Descarte de NF de teste (pos janela 24h SEFAZ)
# --------------------------------------------------------------------------

def descartar_venda_teste(
    venda_id: int,
    motivo: str,
    usuario: Optional[str] = None,
) -> HoraVenda:
    """Descarta venda de teste cuja NFe estourou janela 24h SEFAZ.

    Diferenca de cancelar_venda: NAO checa se NFe foi cancelada na SEFAZ.
    A NFe permanece valida na SEFAZ; apenas marca o pedido como CANCELADO
    no sistema interno e libera os chassis para o estoque. Uso restrito a
    limpar NFs de teste poluindo o sistema.

    Bloqueios mantidos:
      - Motivo obrigatorio (min 3 chars).
      - Venda deve existir.
      - NFe em estado em-voo (EM_ENVIO/ENVIADA_SEFAZ/CANCELAMENTO_SOLICITADO):
        ainda bloqueia (race condition real).
      - Idempotente se ja CANCELADO.

    Efeito (identico a cancelar_venda):
      - status -> CANCELADO; cancelado_em/por preenchidos.
      - cancelamento_motivo persistido com prefixo "[DESCARTE TESTE] ".
      - DEVOLVIDA em todos os chassis (libera estoque).
      - Auditoria: acao DESCARTOU_TESTE (distinta de CANCELOU).
    """
    motivo_limpo = (motivo or '').strip()
    if len(motivo_limpo) < 3:
        raise ValueError('Motivo obrigatorio (min 3 chars)')

    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    if venda.status == VENDA_STATUS_CANCELADO:
        return venda

    emissao = _emissao_nfe(venda.id)
    if emissao and emissao.status in _NFE_EM_VOO:
        raise TransicaoInvalidaError(
            f'NFe em estado {emissao.status} — aguarde resolucao SEFAZ '
            'antes de descartar o pedido.'
        )

    motivo_persistido = f'[DESCARTE TESTE] {motivo_limpo}'[:500]
    venda.status = VENDA_STATUS_CANCELADO
    venda.cancelado_em = agora_utc_naive()
    venda.cancelado_por = usuario or 'desconhecido'
    venda.cancelamento_motivo = motivo_persistido

    for item in venda.itens:
        registrar_evento(
            numero_chassi=item.numero_chassi,
            tipo='DEVOLVIDA',
            origem_tabela='hora_venda',
            origem_id=venda.id,
            loja_id=venda.loja_id,
            operador=usuario,
            detalhe=f'Pedido #{venda.id} descartado (NF teste): {motivo_limpo[:160]}',
        )

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='DESCARTOU_TESTE',
        detalhe=motivo_limpo[:500],
    )

    db.session.commit()
    return venda


# --------------------------------------------------------------------------
# Definir loja (CNPJ_DESCONHECIDO)
# --------------------------------------------------------------------------

def definir_loja_venda(
    venda_id: int,
    loja_id: int,
    usuario: Optional[str] = None,
) -> HoraVenda:
    """Define ou TROCA a loja fisica do pedido.

    Caso de uso primario: como NFe da Lojas HORA sai sempre com CNPJ da
    matriz (regra fiscal — invariante 2026-04-27 em CLAUDE.md), o
    backfill resolve `loja_id` pelo CNPJ emitente e cai sempre na matriz.
    Operador precisa indicar a loja fisica real onde a venda aconteceu.

    Comportamento:
      - Se loja_id atual == novo loja_id: no-op (idempotente).
      - Se atual e NULL ou diferente: atualiza + emite VENDIDA com a nova
        loja_id (auditoria de movimentacao). Resolve divergencia
        CNPJ_DESCONHECIDO se houver.
    """
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')

    loja = HoraLoja.query.get(loja_id)
    if not loja:
        raise ValueError(f'Loja {loja_id} nao encontrada')

    loja_anterior_id = venda.loja_id
    if loja_anterior_id == loja_id:
        return venda

    venda.loja_id = loja_id

    if loja_anterior_id is None:
        detalhe_evt = (
            f'Loja definida retroativamente no pedido #{venda.id} '
            '(evento anterior com loja_id=NULL).'
        )
    else:
        loja_ant = HoraLoja.query.get(loja_anterior_id)
        rotulo_ant = loja_ant.rotulo_display if loja_ant else f'#{loja_anterior_id}'
        detalhe_evt = (
            f'Loja trocada de {rotulo_ant} para {loja.rotulo_display} '
            f'no pedido #{venda.id}.'
        )

    for item in venda.itens:
        registrar_evento(
            numero_chassi=item.numero_chassi,
            tipo='VENDIDA',
            origem_tabela='hora_venda_item',
            origem_id=item.id,
            loja_id=loja_id,
            operador=usuario,
            detalhe=detalhe_evt,
        )

    div = (
        HoraVendaDivergencia.query
        .filter_by(venda_id=venda.id, tipo='CNPJ_DESCONHECIDO')
        .first()
    )
    if div and div.resolvida_em is None:
        div.resolvida_em = agora_utc_naive()
        div.resolvida_por = usuario

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='DEFINIU_LOJA',
        valor_antes=str(loja_anterior_id) if loja_anterior_id else None,
        valor_depois=str(loja_id),
        detalhe=(
            f'Loja {"definida" if loja_anterior_id is None else "trocada"}: '
            f'{loja.rotulo_display}'
        ),
    )

    db.session.commit()
    return venda


def resolver_divergencia(
    divergencia_id: int,
    usuario: Optional[str] = None,
) -> HoraVendaDivergencia:
    div = HoraVendaDivergencia.query.get(divergencia_id)
    if not div:
        raise ValueError(f'Divergencia {divergencia_id} nao encontrada')
    if div.resolvida_em is not None:
        return div
    div.resolvida_em = agora_utc_naive()
    div.resolvida_por = usuario

    venda_audit.registrar_auditoria(
        venda_id=div.venda_id, usuario=usuario or '',
        acao='RESOLVEU_DIVERGENCIA',
        detalhe=f'tipo={div.tipo} chassi={div.numero_chassi or "-"}',
    )
    db.session.commit()
    return div


# --------------------------------------------------------------------------
# Import DANFE legado: nasce em FATURADO direto
# --------------------------------------------------------------------------

def importar_nf_saida_pdf(
    pdf_bytes: bytes,
    nome_arquivo_origem: Optional[str] = None,
    criado_por: Optional[str] = None,
) -> HoraVenda:
    """Parseia DANFE de saida e cria pedido FATURADO (NF ja existe)."""
    payload = parse_danfe_to_hora_payload(
        pdf_bytes=pdf_bytes,
        nome_arquivo_origem=nome_arquivo_origem,
    )
    nf_data = payload['nf']
    itens_data = payload['itens']

    chave_44 = nf_data['chave_44']

    existente = HoraVenda.query.filter_by(nf_saida_chave_44=chave_44).first()
    if existente:
        raise NfSaidaJaImportada(
            f'NF de saida com chave {chave_44} ja importada (venda_id={existente.id})'
        )

    # `cpf_destinatario` no payload do parser comporta CPF (11) ou CNPJ (14)
    # — ver app/hora/services/parsers/danfe_adapter.py.
    cpf_cliente = nf_data.get('cpf_destinatario')
    nome_cliente = nf_data.get('nome_destinatario')
    if not cpf_cliente:
        raise ValueError(
            'NF de saida sem CPF/CNPJ do destinatario.'
        )
    if not nome_cliente:
        raise ValueError('NF de saida sem nome do destinatario.')

    cnpj_emitente = nf_data.get('cnpj_emitente')
    loja_emitente = _resolver_loja_por_cnpj(cnpj_emitente)

    s3_key = _salvar_pdf_storage(
        pdf_bytes=pdf_bytes, chave_44=chave_44,
        nome_arquivo_origem=nome_arquivo_origem,
    )

    data_emissao = nf_data['data_emissao']
    valor_total_nf = Decimal(str(nf_data['valor_total']))
    venda = HoraVenda(
        loja_id=loja_emitente.id if loja_emitente else None,
        cpf_cliente=cpf_cliente[:14],
        nome_cliente=nome_cliente[:200],
        data_venda=data_emissao,
        forma_pagamento='NAO_INFORMADO',
        valor_total=valor_total_nf,
        nf_saida_numero=nf_data['numero_nf'][:20],
        nf_saida_chave_44=chave_44,
        nf_saida_emitida_em=_para_datetime(data_emissao),
        arquivo_pdf_s3_key=s3_key,
        parser_usado=nf_data.get('parser_usado', 'danfe_pdf_parser_v1'),
        parseada_em=agora_utc_naive(),
        cnpj_emitente=cnpj_emitente,
        status=VENDA_STATUS_FATURADO,
        faturado_em=_para_datetime(data_emissao) or agora_utc_naive(),
        vendedor=None,
        origem_criacao='DANFE',
    )
    db.session.add(venda)
    db.session.flush()

    if not loja_emitente:
        _registrar_divergencia(
            venda_id=venda.id, tipo='CNPJ_DESCONHECIDO',
            detalhe=(
                'CNPJ emitente da NF nao bate com nenhuma HoraLoja ativa. '
                'Defina a loja manualmente na tela de detalhe.'
            ),
            valor_conferido=cnpj_emitente,
        )

    _criar_itens_e_eventos(
        venda=venda,
        itens_data=itens_data,
        loja_emitente_id=loja_emitente.id if loja_emitente else None,
        data_venda=data_emissao,
        operador=criado_por,
    )

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=criado_por or '',
        acao='CRIOU',
        detalhe=(
            f'Import DANFE legado (FATURADO direto) NF {venda.nf_saida_numero} '
            f'chave {chave_44}'
        ),
    )

    db.session.commit()
    return venda


def _resolver_modelo_id_por_codigo(codigo_produto: Optional[str]) -> Optional[int]:
    """Resolve modelo_id deterministicamente via tagplus_codigo.

    Migration hora_29: usa resolver_via_tagplus (que cobre HoraModeloAlias
    com tipo TAGPLUS_CODIGO + fallback legado em hora_tagplus_produto_map).
    """
    if not codigo_produto:
        return None
    cod = codigo_produto.strip()
    if not cod:
        return None
    from app.hora.services.modelo_resolver_service import resolver_via_tagplus
    modelo = resolver_via_tagplus(tagplus_codigo=cod)
    return modelo.id if modelo else None


def _criar_itens_e_eventos(
    venda: HoraVenda,
    itens_data: List[dict],
    loja_emitente_id: Optional[int],
    data_venda,
    operador: Optional[str],
) -> None:
    """Cria HoraVendaItem + evento VENDIDA + divergencias por chassi (DANFE legado)."""
    for item in itens_data:
        chassi = item['numero_chassi']
        preco_final = Decimal(str(item['preco_real']))
        codigo_produto = item.get('codigo_produto')

        moto_existia = HoraMoto.query.get(chassi) is not None

        # Caminho 1 (DETERMINISTICO): codigo TagPlus -> modelo_id via mapa.
        # Caminho 2 (FALLBACK): nome textual extraido do PDF — pode criar
        # 'BICICLETA ELETRICA' generico, registrar divergencia.
        modelo_id_resolvido = _resolver_modelo_id_por_codigo(codigo_produto)
        if modelo_id_resolvido and not moto_existia:
            # Cria moto vinculada direto ao modelo correto.
            moto = HoraMoto(
                numero_chassi=chassi,
                modelo_id=modelo_id_resolvido,
                cor=(item.get('cor_texto_original') or 'NAO_INFORMADA').strip().upper(),
                numero_motor=item.get('numero_motor') or None,
                ano_modelo=item.get('ano_modelo'),
                criado_por=operador,
            )
            db.session.add(moto)
            db.session.flush()
        else:
            # Migration hora_29: get_or_create_moto pode levantar
            # ModeloPendenteError. Capturamos e SKIPAMOS o item — operador
            # resolve via /hora/modelos/pendencias e re-importa NF (UNIQUE
            # em chave_44 detecta + atualiza).
            from app.hora.services.modelo_resolver_service import ModeloPendenteError
            from app.hora.models import PENDENTE_ORIGEM_DANFE_PDF
            try:
                moto = get_or_create_moto(
                    numero_chassi=chassi,
                    modelo_nome=item.get('modelo_texto_original'),
                    cor=item.get('cor_texto_original') or 'NAO_INFORMADA',
                    numero_motor=item.get('numero_motor'),
                    ano_modelo=item.get('ano_modelo'),
                    criado_por=operador,
                    origem_pendencia=PENDENTE_ORIGEM_DANFE_PDF,
                    origem_id=venda.id,
                    tagplus_codigo=codigo_produto,
                )
            except ModeloPendenteError as exc:
                _registrar_divergencia(
                    venda_id=venda.id, tipo='MODELO_PENDENTE',
                    numero_chassi=chassi,
                    detalhe=(
                        f'Modelo {(item.get("modelo_texto_original") or codigo_produto)!r} '
                        f'nao reconhecido. Pendencia #{exc.pendencia.id} aguardando '
                        f'decisao em /hora/modelos/pendencias. Re-importe a NF apos '
                        f'resolver.'
                    ),
                    valor_conferido=(
                        item.get('modelo_texto_original') or codigo_produto or ''
                    )[:255],
                )
                continue
            # Se chegou ate aqui sem modelo_id resolvido E havia codigo no PDF,
            # operador esqueceu de mapear -> registra divergencia.
            if codigo_produto and not modelo_id_resolvido and not moto_existia:
                _registrar_divergencia(
                    venda_id=venda.id, tipo='TABELA_PRECO_AUSENTE',
                    numero_chassi=chassi,
                    detalhe=(
                        f'Codigo TagPlus {codigo_produto!r} nao mapeado em '
                        f'hora_tagplus_produto_map. Modelo criado por nome '
                        f'textual (pode ser duplicata). Mapear em '
                        f'/hora/modelos/{moto.modelo_id}/editar.'
                    ),
                    valor_conferido=codigo_produto,
                )
        if not moto_existia:
            _registrar_divergencia(
                venda_id=venda.id, tipo='CHASSI_NAO_CADASTRADO',
                numero_chassi=chassi,
                detalhe='Chassi nao existia em hora_moto (criado a partir da NF).',
            )

        ult = _ultimo_evento(chassi)
        if ult is None:
            if moto_existia:
                _registrar_divergencia(
                    venda_id=venda.id, tipo='CHASSI_INDISPONIVEL',
                    numero_chassi=chassi,
                    detalhe='Chassi existia em hora_moto mas sem nenhum evento.',
                )
        else:
            if ult.tipo not in EVENTOS_EM_ESTOQUE:
                _registrar_divergencia(
                    venda_id=venda.id, tipo='CHASSI_INDISPONIVEL',
                    numero_chassi=chassi,
                    detalhe=(
                        f'Ultimo evento do chassi era {ult.tipo} '
                        f'(em {ult.timestamp.strftime("%d/%m/%Y %H:%M")})'
                    ),
                    valor_conferido=ult.tipo,
                )
            if (
                loja_emitente_id is not None
                and ult.loja_id is not None
                and ult.loja_id != loja_emitente_id
            ):
                _registrar_divergencia(
                    venda_id=venda.id, tipo='LOJA_DIVERGENTE',
                    numero_chassi=chassi,
                    detalhe=(
                        f'Chassi estava na loja_id={ult.loja_id} '
                        f'mas NF foi emitida pela loja_id={loja_emitente_id}.'
                    ),
                    valor_esperado=str(loja_emitente_id),
                    valor_conferido=str(ult.loja_id),
                )

        preco_ref, desconto, desconto_pct, tabela_id, divergencia_tipo = _resolver_preco_tabela(
            moto.modelo_id, data_venda, preco_final,
            forma_pagamento_hora=venda.forma_pagamento,
        )
        if divergencia_tipo:
            _registrar_divergencia(
                venda_id=venda.id, tipo=divergencia_tipo,
                numero_chassi=chassi,
                detalhe=(
                    f'Sem tabela vigente OU preco acima da tabela. '
                    f'preco_final=R${preco_final}'
                ),
                valor_esperado=str(preco_ref),
                valor_conferido=str(preco_final),
            )

        venda_item = HoraVendaItem(
            venda_id=venda.id,
            numero_chassi=chassi,
            tabela_preco_id=tabela_id,
            preco_tabela_referencia=preco_ref,
            desconto_aplicado=desconto,
            desconto_percentual=desconto_pct,
            preco_final=preco_final,
        )
        db.session.add(venda_item)
        db.session.flush()

        # DANFE legado: vai direto para VENDIDA + NF_EMITIDA (faturado).
        registrar_evento(
            numero_chassi=chassi,
            tipo='VENDIDA',
            origem_tabela='hora_venda_item',
            origem_id=venda_item.id,
            loja_id=loja_emitente_id,
            operador=operador,
            detalhe=(
                f'Pedido FATURADO (DANFE legado) #{venda.id} '
                f'NF {venda.nf_saida_numero} para {venda.nome_cliente}'
            ),
        )


# --------------------------------------------------------------------------
# Listagem
# --------------------------------------------------------------------------

def listar_vendas(
    limit: int = 200,
    lojas_permitidas_ids: Optional[Iterable[int]] = None,
    status: Optional[str] = None,
) -> List[HoraVenda]:
    """Lista pedidos com filtro por lojas permitidas e status (sem paginacao)."""
    query = _query_vendas(lojas_permitidas_ids=lojas_permitidas_ids, status=status)
    if query is None:
        return []
    return query.limit(limit).all()


def _query_vendas(
    lojas_permitidas_ids: Optional[Iterable[int]] = None,
    status: Optional[str] = None,
    *,
    busca: Optional[str] = None,
    loja_id: Optional[int] = None,
    data_inicio=None,
    data_fim=None,
    chassi: Optional[str] = None,
    eager_itens: bool = False,
):
    """Constroi query base de vendas com filtros — usado por listar e paginar.

    busca: substring que casa em nf_saida_numero, nome_cliente ou cpf_cliente.
    loja_id: id especifico de loja_id (precisa estar dentro de lojas_permitidas).
    data_inicio/data_fim: faixa em data_venda.
    chassi: substring (case-insensitive) que casa em HoraVendaItem.numero_chassi.
        Usa EXISTS para evitar duplicacao de linhas no resultado.
    eager_itens: quando True, faz `selectinload` em itens+moto+modelo para
        permitir exibicao inline na listagem sem N+1. NAO ativar quando o
        caller nao precisa dos itens (custa 3 SELECT IN extras —
        listar_vendas/exportacao geralmente nao precisa).
    """
    from sqlalchemy import or_
    from sqlalchemy.orm import selectinload

    opts = []
    if eager_itens:
        opts.append(
            selectinload(HoraVenda.itens)
            .selectinload(HoraVendaItem.moto)
            .selectinload(HoraMoto.modelo),
        )

    query = HoraVenda.query
    if opts:
        query = query.options(*opts)
    query = query.order_by(
        HoraVenda.data_venda.desc(), HoraVenda.id.desc()
    )
    if status:
        query = query.filter(HoraVenda.status == status)
    if lojas_permitidas_ids is not None:
        ids_list = list(lojas_permitidas_ids)
        if not ids_list:
            return None
        query = query.filter(HoraVenda.loja_id.in_(ids_list))

    if busca:
        b = busca.strip()
        digits = ''.join(c for c in b if c.isdigit())
        cond = or_(
            HoraVenda.nf_saida_numero.ilike(f'%{b}%'),
            HoraVenda.nome_cliente.ilike(f'%{b}%'),
        )
        if digits:
            cond = or_(cond, HoraVenda.cpf_cliente.ilike(f'%{digits}%'))
        query = query.filter(cond)
    if loja_id:
        query = query.filter(HoraVenda.loja_id == loja_id)
    if data_inicio:
        query = query.filter(HoraVenda.data_venda >= data_inicio)
    if data_fim:
        query = query.filter(HoraVenda.data_venda <= data_fim)
    if chassi:
        ch = chassi.strip().upper()
        if ch:
            # EXISTS evita duplicar HoraVenda quando chassi casa multiplos
            # itens (raro mas possivel em pedido com itens trocados via
            # editar_item_pedido). Mantem ordering estavel.
            sub = (
                db.session.query(HoraVendaItem.id)
                .filter(HoraVendaItem.venda_id == HoraVenda.id)
                .filter(HoraVendaItem.numero_chassi.ilike(f'%{ch}%'))
            )
            query = query.filter(sub.exists())
    return query


def paginar_vendas(
    page: int = 1,
    per_page: int = 50,
    lojas_permitidas_ids: Optional[Iterable[int]] = None,
    status: Optional[str] = None,
    *,
    busca: Optional[str] = None,
    loja_id: Optional[int] = None,
    data_inicio=None,
    data_fim=None,
    chassi: Optional[str] = None,
):
    """Pagina vendas com filtros. Retorna `Pagination` (Flask-SQLAlchemy)
    ou None quando o usuario nao tem nenhuma loja permitida (lista vazia).
    """
    page = max(1, int(page or 1))
    per_page = max(1, min(int(per_page or 50), 200))
    query = _query_vendas(
        lojas_permitidas_ids=lojas_permitidas_ids,
        status=status,
        busca=busca,
        loja_id=loja_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        chassi=chassi,
        eager_itens=True,  # listagem mostra itens (chassi+modelo+cor) inline.
    )
    if query is None:
        return None
    return query.paginate(page=page, per_page=per_page, error_out=False)


__all__ = [
    'NfSaidaJaImportada',
    'ChassiIndisponivelError',
    'TransicaoInvalidaError',
    'criar_venda_manual',
    'confirmar_venda',
    'editar_venda',
    'editar_pagamentos',
    'adicionar_item_pedido',
    'remover_item_pedido',
    'editar_item_pedido',
    'cancelar_venda',
    'descartar_venda_teste',
    'definir_loja_venda',
    'resolver_divergencia',
    'importar_nf_saida_pdf',
    'listar_vendas',
]
