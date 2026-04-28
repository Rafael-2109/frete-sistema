"""Service de HoraVenda: importa DANFE de saida, cria venda + itens + evento VENDIDA.

Fluxo de import (atualmente unico; fluxo TagPlus sera adicionado em sessao futura):
  1. Parseia PDF via danfe_adapter (parser CarVia reusado).
  2. Valida chave_44 nao duplicada (UNIQUE em HoraVenda.nf_saida_chave_44).
  3. Resolve loja emitente por CNPJ -> HoraLoja ativa; se nao bate, loja_id=NULL
     e registra divergencia CNPJ_DESCONHECIDO para correcao manual.
  4. Resolve preco_tabela vigente por modelo+data; se nao existe, usa preco_final
     como preco_tabela_referencia + desconto=0 e registra TABELA_PRECO_AUSENTE.
  5. Para cada chassi:
     - get_or_create_moto (cria se nao existe + divergencia CHASSI_NAO_CADASTRADO).
     - Valida ultimo evento em EVENTOS_EM_ESTOQUE (divergencia se nao).
     - Valida loja do ultimo evento == loja emitente (divergencia se nao).
     - Cria HoraVendaItem + evento VENDIDA.
  6. Persiste PDF no S3 (folder='hora/vendas/'). Falha de storage nao aborta.

Fluxo permissivo: problemas geram divergencia, nao rejeitam. Decidido com usuario.
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
)
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
)


def _para_datetime(valor) -> Optional[datetime]:
    """Converte date em datetime (meia-noite); preserva datetime; retorna None
    se for None. Usado para persistir `nf_saida_emitida_em` (DateTime) a partir
    do `data_emissao` (que pode vir como date pelo parser).
    """
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, date):
        return datetime.combine(valor, time.min)
    return None


class NfSaidaJaImportada(Exception):
    """NF com mesma chave_44 já existe em HoraVenda."""


# --------------------------------------------------------------------------
# Helpers internos
# --------------------------------------------------------------------------

def _salvar_pdf_storage(
    pdf_bytes: bytes, chave_44: str, nome_arquivo_origem: Optional[str]
) -> Optional[str]:
    """Persiste bytes do DANFE em hora/vendas/ e retorna s3_key salvo (ou None).

    Falha de storage nao aborta o import — loga e continua (venda ja importou).
    """
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
    """Cria divergencia (idempotente via UNIQUE venda+tipo+chassi)."""
    if tipo not in TIPOS_DIVERGENCIA_VENDA:
        raise ValueError(f'tipo de divergencia invalido: {tipo}')
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
    """Mesma regra de cadastro_service.buscar_preco_vigente, mas inline p/ evitar
    import circular (cadastro_service nao depende de venda_service; venda_service
    depende de cadastro_service — OK, mas inline mantem boundary limpo).
    """
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
    """Busca HoraLoja ativa por CNPJ. Normaliza dois lados (so digitos)."""
    if not cnpj_emitente:
        return None
    digitos = ''.join(c for c in cnpj_emitente if c.isdigit())
    if not digitos:
        return None
    return HoraLoja.query.filter_by(cnpj=digitos, ativa=True).first()


# --------------------------------------------------------------------------
# Fluxo principal: import DANFE -> HoraVenda
# --------------------------------------------------------------------------

def importar_nf_saida_pdf(
    pdf_bytes: bytes,
    nome_arquivo_origem: Optional[str] = None,
    criado_por: Optional[str] = None,
) -> HoraVenda:
    """Parseia PDF e cria HoraVenda + itens + eventos VENDIDA + divergencias.

    Args:
        pdf_bytes: bytes do DANFE da NF de saida.
        nome_arquivo_origem: nome original do arquivo (para log e storage).
        criado_por: usuario que subiu a NF (nao vira vendedor — campo e preenchido
                    manualmente depois; ver decisao do usuario em 2026-04-24).

    Returns:
        HoraVenda criada (com itens, divergencias e eventos VENDIDA emitidos).

    Raises:
        NfSaidaJaImportada: se chave_44 ja existe.
        DanfeParseError: se parser falhar.
        ValueError: se dados obrigatorios (CPF cliente, nome) nao puderem ser
                    extraidos da NF.
    """
    payload = parse_danfe_to_hora_payload(
        pdf_bytes=pdf_bytes,
        nome_arquivo_origem=nome_arquivo_origem,
    )
    nf_data = payload['nf']
    itens_data = payload['itens']

    chave_44 = nf_data['chave_44']

    # 1. Dedupe por chave_44 (UNIQUE em hora_venda).
    existente = HoraVenda.query.filter_by(nf_saida_chave_44=chave_44).first()
    if existente:
        raise NfSaidaJaImportada(
            f'NF de saida com chave {chave_44} ja importada (venda_id={existente.id})'
        )

    # 2. Cliente: extrair CPF + nome do destinatario.
    cpf_cliente = nf_data.get('cpf_destinatario')
    nome_cliente = nf_data.get('nome_destinatario')
    if not cpf_cliente:
        raise ValueError(
            'NF de saida sem CPF do destinatario (parser extraiu documento nao-CPF). '
            'Confira se o DANFE e de venda ao consumidor final.'
        )
    if not nome_cliente:
        raise ValueError(
            'NF de saida sem nome do destinatario. Parser falhou em extrair.'
        )

    # 3. Resolver loja por CNPJ emitente (permissivo: NULL + divergencia se nao bate).
    cnpj_emitente = nf_data.get('cnpj_emitente')
    loja_emitente = _resolver_loja_por_cnpj(cnpj_emitente)

    # 4. Persistir PDF (falha nao aborta).
    s3_key = _salvar_pdf_storage(
        pdf_bytes=pdf_bytes,
        chave_44=chave_44,
        nome_arquivo_origem=nome_arquivo_origem,
    )

    # 5. Criar HoraVenda (flush para obter id; itens/divergencias vao logo em seguida).
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
        # nf_saida_emitida_em deve refletir a data de emissao da NF fiscal
        # (vinda do DANFE), nao o momento do import (C1 do code review).
        nf_saida_emitida_em=_para_datetime(data_emissao),
        arquivo_pdf_s3_key=s3_key,
        parser_usado=nf_data.get('parser_usado', 'danfe_pdf_parser_v1'),
        parseada_em=agora_utc_naive(),
        cnpj_emitente=cnpj_emitente,
        status='CONCLUIDA',
        vendedor=None,  # preenchido manualmente pos-import
    )
    db.session.add(venda)
    db.session.flush()

    # 5b. Divergencia header: CNPJ emitente nao bate.
    if not loja_emitente:
        _registrar_divergencia(
            venda_id=venda.id,
            tipo='CNPJ_DESCONHECIDO',
            detalhe=(
                'CNPJ emitente da NF nao bate com nenhuma HoraLoja ativa. '
                'Defina a loja manualmente na tela de detalhe.'
            ),
            valor_conferido=cnpj_emitente,
        )

    # 6. Itens + eventos + divergencias por chassi.
    _criar_itens_e_eventos(
        venda=venda,
        itens_data=itens_data,
        loja_emitente_id=loja_emitente.id if loja_emitente else None,
        data_venda=data_emissao,
        operador=criado_por,
    )

    db.session.commit()
    return venda


def _criar_itens_e_eventos(
    venda: HoraVenda,
    itens_data: List[dict],
    loja_emitente_id: Optional[int],
    data_venda,
    operador: Optional[str],
) -> None:
    """Cria HoraVendaItem + HoraMotoEvento(VENDIDA) + divergencias por chassi."""
    for item in itens_data:
        chassi = item['numero_chassi']
        preco_final = Decimal(str(item['preco_real']))

        # 6a. get_or_create_moto (pode criar nova HoraMoto).
        moto_existia = HoraMoto.query.get(chassi) is not None
        moto = get_or_create_moto(
            numero_chassi=chassi,
            modelo_nome=item.get('modelo_texto_original'),
            cor=item.get('cor_texto_original') or 'NAO_INFORMADA',
            numero_motor=item.get('numero_motor'),
            ano_modelo=item.get('ano_modelo'),
            criado_por=operador,
        )
        if not moto_existia:
            _registrar_divergencia(
                venda_id=venda.id,
                tipo='CHASSI_NAO_CADASTRADO',
                numero_chassi=chassi,
                detalhe=(
                    'Chassi nao existia em hora_moto (criado a partir da NF). '
                    'Indica que a moto nunca passou pelo fluxo de entrada/recebimento.'
                ),
            )

        # 6b. Valida ultimo evento e loja.
        ult = _ultimo_evento(chassi)
        if ult is None:
            # Chassi recem-criado ou nunca movimentado — registramos como indisponivel
            # apenas se a moto JA existia antes do import (ai era esperada alguma
            # movimentacao). Chassi novo criado no proprio import: sem evento antes.
            if moto_existia:
                _registrar_divergencia(
                    venda_id=venda.id,
                    tipo='CHASSI_INDISPONIVEL',
                    numero_chassi=chassi,
                    detalhe='Chassi existia em hora_moto mas sem nenhum evento.',
                )
        else:
            if ult.tipo not in EVENTOS_EM_ESTOQUE:
                _registrar_divergencia(
                    venda_id=venda.id,
                    tipo='CHASSI_INDISPONIVEL',
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
                    venda_id=venda.id,
                    tipo='LOJA_DIVERGENTE',
                    numero_chassi=chassi,
                    detalhe=(
                        f'Chassi estava na loja_id={ult.loja_id} '
                        f'mas NF foi emitida pela loja_id={loja_emitente_id}.'
                    ),
                    valor_esperado=str(loja_emitente_id),
                    valor_conferido=str(ult.loja_id),
                )

        # 6c. Resolver preco de tabela vigente; fallback: preco_final.
        tabela_preco = _buscar_preco_vigente(moto.modelo_id, data_venda)
        if tabela_preco:
            preco_tabela_ref = Decimal(str(tabela_preco.preco_tabela))
            desconto = preco_tabela_ref - preco_final
            if desconto < 0:
                # Vendeu acima da tabela (promo negativa = acrescimo). Para nao
                # violar a invariante preco_final = tabela - desconto (desconto>=0),
                # registramos com preco_tabela_ref=preco_final e desconto=0 e
                # emitimos divergencia especifica PRECO_ACIMA_TABELA (distinta
                # de TABELA_PRECO_AUSENTE) para o operador revisar.
                _registrar_divergencia(
                    venda_id=venda.id,
                    tipo='PRECO_ACIMA_TABELA',
                    numero_chassi=chassi,
                    detalhe=(
                        f'Preco final (R${preco_final}) > preco tabela '
                        f'(R${preco_tabela_ref}). Item gravado sem desconto '
                        'negativo; revise se houve acrescimo ou tabela desatualizada.'
                    ),
                    valor_esperado=str(preco_tabela_ref),
                    valor_conferido=str(preco_final),
                )
                preco_tabela_ref = preco_final
                desconto = Decimal('0.00')
                tabela_preco_id = None
            else:
                tabela_preco_id = tabela_preco.id
        else:
            _registrar_divergencia(
                venda_id=venda.id,
                tipo='TABELA_PRECO_AUSENTE',
                numero_chassi=chassi,
                detalhe=(
                    f'Sem HoraTabelaPreco vigente para modelo {moto.modelo_id} '
                    f'na data {data_venda}. Usado preco final como referencia.'
                ),
                valor_conferido=str(preco_final),
            )
            preco_tabela_ref = preco_final
            desconto = Decimal('0.00')
            tabela_preco_id = None

        # 6d. Cria HoraVendaItem.
        venda_item = HoraVendaItem(
            venda_id=venda.id,
            numero_chassi=chassi,
            tabela_preco_id=tabela_preco_id,
            preco_tabela_referencia=preco_tabela_ref,
            desconto_aplicado=desconto,
            preco_final=preco_final,
        )
        db.session.add(venda_item)
        db.session.flush()

        # 6e. Evento VENDIDA (invariante 4 do HORA: estado via evento).
        registrar_evento(
            numero_chassi=chassi,
            tipo='VENDIDA',
            origem_tabela='hora_venda_item',
            origem_id=venda_item.id,
            loja_id=loja_emitente_id,
            operador=operador,
            detalhe=(
                f'Venda #{venda.id} NF {venda.nf_saida_numero} '
                f'para {venda.nome_cliente}'
            ),
        )


# --------------------------------------------------------------------------
# Manutencao pos-import
# --------------------------------------------------------------------------

def editar_venda(
    venda_id: int,
    vendedor: Optional[str] = None,
    forma_pagamento: Optional[str] = None,
    telefone_cliente: Optional[str] = None,
    email_cliente: Optional[str] = None,
    observacoes: Optional[str] = None,
) -> HoraVenda:
    """Edita campos da venda editaveis pos-import.

    Os demais campos (CPF/nome/valor/chave_44/itens) vem da NF e sao imutaveis.
    """
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    if venda.status == 'CANCELADA':
        raise ValueError('Venda cancelada nao pode ser editada')

    if vendedor is not None:
        venda.vendedor = vendedor.strip()[:100] or None
    if forma_pagamento is not None:
        fp_norm = (forma_pagamento or '').strip().upper() or 'NAO_INFORMADO'
        venda.forma_pagamento = fp_norm[:20]
    if telefone_cliente is not None:
        venda.telefone_cliente = telefone_cliente.strip()[:20] or None
    if email_cliente is not None:
        venda.email_cliente = email_cliente.strip()[:120] or None
    if observacoes is not None:
        venda.observacoes = observacoes.strip() or None

    db.session.commit()
    return venda


def definir_loja_venda(
    venda_id: int,
    loja_id: int,
    usuario: Optional[str] = None,
) -> HoraVenda:
    """Preenche loja_id em venda importada com CNPJ emitente desconhecido.

    Resolve a divergencia CNPJ_DESCONHECIDO. Para cada chassi da venda, emite
    um NOVO evento VENDIDA com loja_id corrigida (respeitando a invariante 4
    do HORA — eventos sao append-only, nunca UPDATE). O evento VENDIDA original
    com loja_id=NULL e preservado no historico. O "ultimo evento" do chassi
    passa a apontar para a nova loja automaticamente (calculo por MAX(id)).
    """
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    if venda.loja_id:
        raise ValueError(f'Venda {venda_id} ja tem loja {venda.loja_id} definida.')

    loja = HoraLoja.query.get(loja_id)
    if not loja:
        raise ValueError(f'Loja {loja_id} nao encontrada')

    venda.loja_id = loja_id

    # Emite um novo evento VENDIDA por chassi apontando a loja corrigida.
    # Invariante 4: eventos append-only — nao mutamos o evento antigo.
    for item in venda.itens:
        registrar_evento(
            numero_chassi=item.numero_chassi,
            tipo='VENDIDA',
            origem_tabela='hora_venda_item',
            origem_id=item.id,
            loja_id=loja_id,
            operador=usuario,
            detalhe=(
                f'Loja definida retroativamente na venda #{venda.id} '
                f'(evento anterior emitido com loja_id=NULL por CNPJ_DESCONHECIDO).'
            ),
        )

    # Resolve divergencia CNPJ_DESCONHECIDO (se havia).
    div = (
        HoraVendaDivergencia.query
        .filter_by(venda_id=venda.id, tipo='CNPJ_DESCONHECIDO')
        .first()
    )
    if div and div.resolvida_em is None:
        div.resolvida_em = agora_utc_naive()
        div.resolvida_por = usuario

    db.session.commit()
    return venda


def cancelar_venda(
    venda_id: int,
    motivo: str,
    usuario: Optional[str] = None,
) -> HoraVenda:
    """Cancela venda: marca status=CANCELADA e emite evento DEVOLVIDA nos chassis.

    Reversao do fluxo: evento DEVOLVIDA volta o chassi para EVENTOS_FORA_ESTOQUE
    (nao em estoque). Se operador quer voltar ao estoque, precisa criar nova
    NF de entrada (simetria com fluxo de devolucao ja existente).

    O registro da venda e PRESERVADO (append-only audit trail); apenas muda status.
    """
    motivo_limpo = (motivo or '').strip()
    if len(motivo_limpo) < 3:
        raise ValueError('Motivo obrigatorio (min 3 chars)')

    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    if venda.status == 'CANCELADA':
        return venda  # idempotente

    venda.status = 'CANCELADA'
    venda.observacoes = (
        (venda.observacoes or '') + f'\n[CANCELADA em {agora_utc_naive()} por {usuario}: {motivo_limpo}]'
    ).strip()

    for item in venda.itens:
        registrar_evento(
            numero_chassi=item.numero_chassi,
            tipo='DEVOLVIDA',
            origem_tabela='hora_venda',
            origem_id=venda.id,
            loja_id=venda.loja_id,
            operador=usuario,
            detalhe=f'Venda #{venda.id} cancelada: {motivo_limpo[:180]}',
        )

    db.session.commit()
    return venda


def resolver_divergencia(
    divergencia_id: int,
    usuario: Optional[str] = None,
) -> HoraVendaDivergencia:
    """Marca divergencia como resolvida (acao tomada pelo operador fora do sistema).

    Nao altera a venda — e so auditoria de "revisei e aceitei/tratei".
    """
    div = HoraVendaDivergencia.query.get(divergencia_id)
    if not div:
        raise ValueError(f'Divergencia {divergencia_id} nao encontrada')
    if div.resolvida_em is not None:
        return div  # idempotente
    div.resolvida_em = agora_utc_naive()
    div.resolvida_por = usuario
    db.session.commit()
    return div


# --------------------------------------------------------------------------
# Listagem
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
    forma_pagamento: str,
    telefone_cliente: Optional[str] = None,
    email_cliente: Optional[str] = None,
    vendedor: Optional[str] = None,
    observacoes: Optional[str] = None,
    criado_por: Optional[str] = None,
) -> HoraVenda:
    """Cria HoraVenda manual (fluxo "Novo Pedido de Venda" no menu Faturamento).

    Diferente de `importar_nf_saida_pdf`, NAO ha NF previa: o operador preenche
    todos os campos via formulario web. O fluxo:
      1. Valida CPF (11 digitos) e nome.
      2. Valida chassi: existe em hora_moto + ultimo evento em EVENTOS_EM_ESTOQUE.
      3. Resolve loja_id pelo ultimo evento do chassi (sempre tem para in-stock).
      4. Resolve preco_tabela_referencia + desconto (preco_tabela_vigente OU
         preco_final como fallback).
      5. Cria HoraVenda + HoraVendaItem + emite evento VENDIDA.
      6. NAO cria NF; venda fica pronta para emissao de NFe via TagPlus.

    Validacoes que NAO sao feitas aqui (sao do PayloadBuilder na hora de emitir):
      - forma_pagamento mapeada em HoraTagPlusFormaPagamentoMap
      - modelo mapeado em HoraTagPlusProdutoMap
      O esboco (`/hora/tagplus/esboco/<id>`) ja exibe esses problemas de forma
      amigavel, e a emissao bloqueia se faltar mapeamento.

    Args:
        cpf_cliente: CPF (11 digitos, com ou sem mascara).
        nome_cliente: Nome completo do consumidor final.
        cep, endereco_*: Endereco (campos podem ser NULL para vendas sem
            endereco — mas TagPlus rejeita destinatario sem endereco).
        numero_chassi: Chassi da moto (deve estar em estoque).
        valor_final: Preco final (apos desconto). Deve ser > 0.
        forma_pagamento: PIX | CARTAO_CREDITO | CARTAO_DEBITO | DINHEIRO etc.
            Validado contra HoraTagPlusFormaPagamentoMap so na emissao.
        telefone_cliente, email_cliente, vendedor, observacoes: opcionais.
        criado_por: Operador (current_user.nome) — registrado em HoraMotoEvento.

    Returns:
        HoraVenda criada (com 1 item e evento VENDIDA emitido).

    Raises:
        ValueError: dados invalidos (CPF, nome, chassi indisponivel, valor <=0).
    """
    # ----- 1. Validacao de cabecalho -----
    cpf_norm = ''.join(c for c in (cpf_cliente or '') if c.isdigit())
    if len(cpf_norm) != 11:
        raise ValueError(f'CPF invalido: {cpf_cliente!r} (esperado 11 digitos)')

    nome_norm = (nome_cliente or '').strip()
    if not nome_norm:
        raise ValueError('Nome do cliente obrigatorio')

    if valor_final is None or Decimal(valor_final) <= 0:
        raise ValueError('Valor final deve ser maior que zero')

    forma_norm = (forma_pagamento or '').strip().upper()
    if not forma_norm or forma_norm == 'NAO_INFORMADO':
        raise ValueError('Forma de pagamento obrigatoria')

    # ----- 2. Validacao do chassi -----
    chassi_norm = (numero_chassi or '').strip().upper()
    if not chassi_norm:
        raise ValueError('Chassi obrigatorio')

    moto = HoraMoto.query.get(chassi_norm)
    if not moto:
        raise ValueError(f'Chassi {chassi_norm} nao cadastrado')

    ult = _ultimo_evento(chassi_norm)
    from app.hora.services.estoque_service import EVENTOS_EM_ESTOQUE
    if ult is None or ult.tipo not in EVENTOS_EM_ESTOQUE:
        ult_tipo = ult.tipo if ult else 'sem eventos'
        raise ValueError(
            f'Chassi {chassi_norm} nao esta disponivel para venda '
            f'(ultimo evento: {ult_tipo})'
        )

    loja_id = ult.loja_id
    if not loja_id:
        raise ValueError(
            f'Chassi {chassi_norm} sem loja definida no ultimo evento — '
            f'investigar inconsistencia em hora_moto_evento.'
        )

    # ----- 3. Endereco (sanitizacao basica) -----
    cep_norm = ''.join(c for c in (cep or '') if c.isdigit()) or None
    if cep_norm and len(cep_norm) != 8:
        raise ValueError(f'CEP invalido: {cep!r} (esperado 8 digitos)')
    cep_formatado = (
        f'{cep_norm[:5]}-{cep_norm[5:]}' if cep_norm else None
    )
    uf_norm = (endereco_uf or '').strip().upper() or None
    if uf_norm and len(uf_norm) != 2:
        raise ValueError(f'UF invalido: {endereco_uf!r} (esperado 2 letras)')

    # ----- 4. Resolver preco tabela vigente -----
    valor_final_dec = Decimal(str(valor_final))
    data_venda = date.today()
    tabela_preco = _buscar_preco_vigente(moto.modelo_id, data_venda)
    if tabela_preco:
        preco_tabela_ref = Decimal(str(tabela_preco.preco_tabela))
        desconto = preco_tabela_ref - valor_final_dec
        if desconto < 0:
            # Vendeu acima da tabela: gravar sem desconto negativo (mesmo
            # comportamento de importar_nf_saida_pdf — invariante de venda).
            preco_tabela_ref = valor_final_dec
            desconto = Decimal('0.00')
            tabela_preco_id = None
        else:
            tabela_preco_id = tabela_preco.id
    else:
        preco_tabela_ref = valor_final_dec
        desconto = Decimal('0.00')
        tabela_preco_id = None

    # ----- 5. Persistir HoraVenda + Item + Evento -----
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
        status='CONCLUIDA',
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
    )
    db.session.add(venda)
    db.session.flush()

    venda_item = HoraVendaItem(
        venda_id=venda.id,
        numero_chassi=chassi_norm,
        tabela_preco_id=tabela_preco_id,
        preco_tabela_referencia=preco_tabela_ref,
        desconto_aplicado=desconto,
        preco_final=valor_final_dec,
    )
    db.session.add(venda_item)
    db.session.flush()

    registrar_evento(
        numero_chassi=chassi_norm,
        tipo='VENDIDA',
        origem_tabela='hora_venda_item',
        origem_id=venda_item.id,
        loja_id=loja_id,
        operador=criado_por,
        detalhe=(
            f'Venda manual #{venda.id} para {nome_norm} '
            f'(CPF {cpf_norm}) - sem NF (TagPlus pendente)'
        ),
    )

    db.session.commit()
    return venda


def listar_vendas(
    limit: int = 200,
    lojas_permitidas_ids: Optional[Iterable[int]] = None,
    status: Optional[str] = None,
) -> List[HoraVenda]:
    """Lista vendas com filtro por lojas permitidas e status.

    lojas_permitidas_ids=None -> sem filtro de loja (admin).
    lojas_permitidas_ids=[]   -> usuario sem lojas -> retorna [].

    Vendas com loja_id=NULL (CNPJ_DESCONHECIDO) so aparecem para admin.
    """
    query = HoraVenda.query.order_by(
        HoraVenda.data_venda.desc(), HoraVenda.id.desc()
    )
    if status:
        query = query.filter(HoraVenda.status == status)

    if lojas_permitidas_ids is not None:
        ids_list = list(lojas_permitidas_ids)
        if not ids_list:
            return []
        # Usuario restrito NAO ve vendas com loja_id=NULL (evita vazamento).
        query = query.filter(HoraVenda.loja_id.in_(ids_list))

    return query.limit(limit).all()
