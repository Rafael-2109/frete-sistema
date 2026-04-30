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
    VENDA_STATUS_CANCELADO,
    VENDA_STATUS_CONFIRMADO,
    VENDA_STATUS_COTACAO,
    VENDA_STATUS_FATURADO,
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


def _resolver_preco_tabela(
    modelo_id: int, na_data, valor_final: Decimal,
) -> tuple[Decimal, Decimal, Optional[int], Optional[str]]:
    """Retorna (preco_tabela_ref, desconto, tabela_preco_id, divergencia_tipo).

    `divergencia_tipo` (se preenchido) deve ser registrado pelo chamador com
    detalhe apropriado (vence aqui o calculo, nao o registro).
    """
    tabela = _buscar_preco_vigente(modelo_id, na_data)
    if tabela:
        preco_ref = Decimal(str(tabela.preco_tabela))
        desconto = preco_ref - valor_final
        if desconto < 0:
            return valor_final, Decimal('0.00'), None, 'PRECO_ACIMA_TABELA'
        return preco_ref, desconto, tabela.id, None
    return valor_final, Decimal('0.00'), None, 'TABELA_PRECO_AUSENTE'


# --------------------------------------------------------------------------
# Fluxo de criacao manual: COTACAO + lock pessimista + evento RESERVADA
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
    modalidade_frete: str = '9',
    numero_parcelas: int = 1,
    intervalo_parcelas_dias: int = 30,
    criado_por: Optional[str] = None,
) -> HoraVenda:
    """Cria pedido de venda manual em status COTACAO.

    1. Valida CPF, nome, valor, forma_pagamento, chassi.
    2. SELECT FOR UPDATE no chassi (impede 2 operadores reservarem o mesmo).
    3. Resolve loja_id pelo ultimo evento.
    4. Resolve preco tabela vigente.
    5. Cria HoraVenda(status=COTACAO) + HoraVendaItem.
    6. Emite evento RESERVADA (saida do estoque disponivel).
    7. Auditoria: CRIOU.
    """
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
    loja_id = ult.loja_id
    if not loja_id:
        raise ValueError(
            f'Chassi {chassi_norm} sem loja definida no ultimo evento — '
            f'investigar inconsistencia em hora_moto_evento.'
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
    preco_tabela_ref, desconto, tabela_preco_id, divergencia_tipo = _resolver_preco_tabela(
        moto.modelo_id, data_venda, valor_final_dec,
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
        status=VENDA_STATUS_COTACAO,
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

    # Evento RESERVADA: tira chassi do estoque disponivel.
    registrar_evento(
        numero_chassi=chassi_norm,
        tipo='RESERVADA',
        origem_tabela='hora_venda_item',
        origem_id=venda_item.id,
        loja_id=loja_id,
        operador=criado_por,
        detalhe=f'Pedido #{venda.id} (COTACAO) para {nome_norm} CPF {cpf_norm}',
    )

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=criado_por or '',
        acao='CRIOU',
        detalhe=(
            f'Pedido manual (COTACAO) chassi={chassi_norm} '
            f'cliente={nome_norm} valor={valor_final_dec}'
        ),
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
_CAMPOS_EDITAVEIS_HEADER = {
    VENDA_STATUS_COTACAO: {
        'vendedor', 'forma_pagamento', 'telefone_cliente', 'email_cliente',
        'observacoes', 'nome_cliente', 'cpf_cliente',
        'cep', 'endereco_logradouro', 'endereco_numero', 'endereco_complemento',
        'endereco_bairro', 'endereco_cidade', 'endereco_uf',
        'modalidade_frete', 'numero_parcelas', 'intervalo_parcelas_dias',
    },
    VENDA_STATUS_CONFIRMADO: {
        'vendedor', 'forma_pagamento', 'telefone_cliente', 'email_cliente',
        'observacoes',
        'cep', 'endereco_logradouro', 'endereco_numero', 'endereco_complemento',
        'endereco_bairro', 'endereco_cidade', 'endereco_uf',
        'modalidade_frete', 'numero_parcelas', 'intervalo_parcelas_dias',
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
    usuario: Optional[str] = None,
) -> HoraVenda:
    """Edita campos do header conforme regra por status.

    - COTACAO: tudo (incluindo cliente/endereco).
    - CONFIRMADO: contato/endereco/operacionais (sem mexer em CPF/nome — sao
      do payload TagPlus).
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
        cpf_norm = ''.join(c for c in cpf_cliente if c.isdigit())
        if cpf_norm and len(cpf_norm) != 11:
            raise ValueError(f'CPF invalido: {cpf_cliente!r}')
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
    preco_ref, desconto, tabela_id, _ = _resolver_preco_tabela(
        moto.modelo_id, venda.data_venda, valor_final_dec,
    )

    item = HoraVendaItem(
        venda_id=venda.id,
        numero_chassi=chassi_norm,
        tabela_preco_id=tabela_id,
        preco_tabela_referencia=preco_ref,
        desconto_aplicado=desconto,
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
        preco_ref, desconto, tabela_id, _ = _resolver_preco_tabela(
            moto.modelo_id, venda.data_venda, valor_alvo or valor_atual,
        )
        item.tabela_preco_id = tabela_id
        item.preco_tabela_referencia = preco_ref
        item.desconto_aplicado = desconto

    # Mudanca de valor.
    if valor_alvo is not None and valor_alvo != valor_atual:
        # Re-resolve preco_tabela apenas para ajustar desconto (mesmo modelo).
        moto = HoraMoto.query.get(item.numero_chassi)
        if moto:
            preco_ref, desconto, tabela_id, _ = _resolver_preco_tabela(
                moto.modelo_id, venda.data_venda, valor_alvo,
            )
            item.tabela_preco_id = tabela_id
            item.preco_tabela_referencia = preco_ref
            item.desconto_aplicado = desconto
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

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='CANCELOU',
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
    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'Venda {venda_id} nao encontrada')
    if venda.loja_id:
        raise ValueError(f'Venda {venda_id} ja tem loja {venda.loja_id} definida.')

    loja = HoraLoja.query.get(loja_id)
    if not loja:
        raise ValueError(f'Loja {loja_id} nao encontrada')

    venda.loja_id = loja_id

    for item in venda.itens:
        registrar_evento(
            numero_chassi=item.numero_chassi,
            tipo='VENDIDA',
            origem_tabela='hora_venda_item',
            origem_id=item.id,
            loja_id=loja_id,
            operador=usuario,
            detalhe=(
                f'Loja definida retroativamente no pedido #{venda.id} '
                '(evento anterior emitido com loja_id=NULL por CNPJ_DESCONHECIDO).'
            ),
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
        valor_depois=str(loja_id),
        detalhe=f'Loja definida: {loja.rotulo_display}',
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

    cpf_cliente = nf_data.get('cpf_destinatario')
    nome_cliente = nf_data.get('nome_destinatario')
    if not cpf_cliente:
        raise ValueError('NF de saida sem CPF do destinatario.')
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

    Caminho principal do BACKFILL TagPlus: o parser DANFE extrai o codigo
    de produto da seção "Dados do Produto" (ex: 'MT-JETMAX', 'MT-X12'),
    e este helper busca o `modelo_id` em `hora_tagplus_produto_map`.

    Returns:
        modelo_id quando ha mapeamento exato; None quando nao ha codigo OU
        codigo nao mapeado (caller cai no fallback `buscar_ou_criar_modelo`
        pelo nome textual e registra divergencia).
    """
    if not codigo_produto:
        return None
    cod = codigo_produto.strip()
    if not cod:
        return None
    mapa = HoraTagPlusProdutoMap.query.filter_by(tagplus_codigo=cod).first()
    return mapa.modelo_id if mapa else None


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
            moto = get_or_create_moto(
                numero_chassi=chassi,
                modelo_nome=item.get('modelo_texto_original'),
                cor=item.get('cor_texto_original') or 'NAO_INFORMADA',
                numero_motor=item.get('numero_motor'),
                ano_modelo=item.get('ano_modelo'),
                criado_por=operador,
            )
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

        preco_ref, desconto, tabela_id, divergencia_tipo = _resolver_preco_tabela(
            moto.modelo_id, data_venda, preco_final,
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
    """Lista pedidos com filtro por lojas permitidas e status."""
    query = HoraVenda.query.order_by(
        HoraVenda.data_venda.desc(), HoraVenda.id.desc()
    )
    if status:
        query = query.filter(HoraVenda.status == status)

    if lojas_permitidas_ids is not None:
        ids_list = list(lojas_permitidas_ids)
        if not ids_list:
            return []
        query = query.filter(HoraVenda.loja_id.in_(ids_list))

    return query.limit(limit).all()


__all__ = [
    'NfSaidaJaImportada',
    'ChassiIndisponivelError',
    'TransicaoInvalidaError',
    'criar_venda_manual',
    'confirmar_venda',
    'editar_venda',
    'adicionar_item_pedido',
    'remover_item_pedido',
    'editar_item_pedido',
    'cancelar_venda',
    'definir_loja_venda',
    'resolver_divergencia',
    'importar_nf_saida_pdf',
    'listar_vendas',
]
