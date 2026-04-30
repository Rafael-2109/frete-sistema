"""Backfill de NFs de saida emitidas no TagPlus -> HoraVenda.

Estrategia: usa a API TagPlus (`GET /nfes` + `GET /nfes/{id}`) para puxar dados
**estruturados** das NFes emitidas. Sem parser de PDF, sem chamada de LLM —
caminho 100% deterministico.

Fluxo:
  1. `listar_nfes_emitidas(since, until)` -> itera /nfes paginado, retorna IDs.
  2. `importar_nfe_da_api(nfe_id)` -> GET /nfes/{id}, mapeia para HoraVenda.
  3. `executar_backfill(since, until)` -> orquestra + relatorio consolidado.

Idempotencia: NF ja importada (mesma `chave_acesso` em `hora_venda.nf_saida_chave_44`)
e ignorada.

Resolucao do modelo:
  - PRIMARIO: `item.produto` (codigo TagPlus) -> hora_tagplus_produto_map.tagplus_codigo.
  - FALLBACK: nome textual de `item.descricao` -> buscar_ou_criar_modelo + divergencia.

Resolucao do chassi:
  - Cada item `produto` consome `qtd` chassis do campo `detalhes`
    ("Chassi: XXXX / Motor: YYYY"). Se a NF foi emitida via nosso PayloadBuilder,
    `detalhes` segue esse formato.
  - Fallback: parsear `inf_contribuinte` ou regex generica.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Iterator, Optional

from app import db
from app.hora.models import HoraMoto, HoraVenda, HoraVendaItem
from app.hora.models.tagplus import (
    HoraTagPlusConta, HoraTagPlusFormaPagamentoMap, HoraTagPlusNfeEmissao,
    HoraTagPlusProdutoMap,
    NFE_STATUS_APROVADA, NFE_STATUS_CANCELADA,
)
from app.hora.models.venda import VENDA_STATUS_CANCELADO, VENDA_STATUS_FATURADO
from app.hora.services import venda_audit
from app.hora.services.estoque_service import EVENTOS_EM_ESTOQUE
from app.hora.services.moto_service import (
    get_or_create_moto, registrar_evento, ultimo_evento,
)
from app.hora.services.tagplus.api_client import ApiClient
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Iterator de listagem
# --------------------------------------------------------------------------

def listar_nfes_emitidas(
    api: ApiClient,
    since: Optional[date] = None,
    until: Optional[date] = None,
    per_page: int = 50,
    apenas_aprovadas: bool = False,
) -> Iterator[dict]:
    """Itera NFes da API TagPlus filtradas por data_emissao.

    Yields cada NFe (dict resumido — id, chave_acesso, status, data_emissao,
    valor_nota etc.). Paginacao via parametro `page`.

    Header X-Data-Filter: data_emissao (sobrescreve default data_criacao do TagPlus).

    Args:
        apenas_aprovadas: quando True (default), passa `status=A` no query
            string — TagPlus retorna apenas NFs APROVADAS na SEFAZ.
            Quando False, passa `status=0` (Indiferente) e o caller decide
            o que fazer com Cancelada/Denegada/Inutilizada/Em-digitacao.
    """
    page = 1
    while True:
        params = {'page': page, 'per_page': per_page}
        if apenas_aprovadas:
            # Status TagPlus: A=Aprovada, S=Cancelada, 2=Denegada, 4=Inutilizada,
            # N=Em digitacao, 0=Indiferente (doc:185-188).
            # Default APENAS_APROVADAS=False para detectar canceladas/inutilizadas
            # e refletir o cancelamento em vendas ja existentes no sistema.
            params['status'] = 'A'
        # else: nao envia params['status'] — TagPlus retorna todas (default 0).
        if since:
            params['since'] = since.isoformat()
        if until:
            params['until'] = until.isoformat()
        r = api.get(
            '/nfes',
            params=params,
            extra_headers={'X-Data-Filter': 'data_emissao'},
        )
        if r.status_code != 200:
            logger.warning(
                'TagPlus GET /nfes page=%s status=%s body=%s',
                page, r.status_code, r.text[:300],
            )
            break
        try:
            lote = r.json()
        except ValueError:
            lote = []
        if not isinstance(lote, list) or not lote:
            return
        for nfe in lote:
            if isinstance(nfe, dict):
                yield nfe
        if len(lote) < per_page:
            return
        page += 1


# --------------------------------------------------------------------------
# Helpers de parsing
# --------------------------------------------------------------------------

_RE_CHASSI_MOTOR = re.compile(
    r'Chassi:\s*([A-Z0-9]+)(?:\s*/\s*Motor:\s*([A-Z0-9\-]*))?',
    re.IGNORECASE,
)

# Padroes alternativos comuns em NFs TagPlus historicas (preenchimento manual):
#   "N° SERIE: XXX / SERIE: XXX / Nº SERIE: XXX"
_RE_NSERIE = re.compile(
    r'(?:N[ºo°]?|Numero)\s*[:\.\-]?\s*(?:SERIE|S[eé]rie|CHASSI|Chassi)\s*[:\.\-]?\s*'
    r'([A-Z0-9][A-Z0-9\-]{8,29})',
    re.IGNORECASE,
)

# Chassis "puros" (string alfanumerica longa) — ultima cartada quando rotulos
# estao ausentes. Aceita 13-30 chars com pelo menos 1 letra E 1 numero (evita
# pegar codigos de produto curtos como MT-X11).
_RE_CHASSI_PURO = re.compile(r'\b([A-Z][A-Z0-9]{12,29})\b')

_RE_MOTOR = re.compile(
    r'Motor\s*[:\.\-]?\s*([A-Z0-9\-]{6,30})',
    re.IGNORECASE,
)


def _extrair_chassi_motor(detalhes: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Parsa string `detalhes` do item TagPlus.

    Tenta na ordem:
      1. 'Chassi: X / Motor: Y'  (formato do nosso PayloadBuilder).
      2. 'N° SERIE: X' ou 'CHASSI: X'  (NFs historicas TagPlus).
      3. Token alfanumerico 13+ chars  (ultima cartada).
    Motor extraido separado quando presente.
    """
    if not detalhes:
        return (None, None)

    chassi = None
    motor = None

    # 1) Padrao Chassi+Motor inline
    m = _RE_CHASSI_MOTOR.search(detalhes)
    if m:
        chassi = (m.group(1) or '').strip().upper() or None
        motor = (m.group(2) or '').strip().upper() or None

    # 2) Padrao "N° SERIE: ..." (TagPlus historico)
    if not chassi:
        m = _RE_NSERIE.search(detalhes)
        if m:
            chassi = m.group(1).strip().upper()

    # 3) Token bruto longo (fallback)
    if not chassi:
        m = _RE_CHASSI_PURO.search(detalhes.upper())
        if m:
            chassi = m.group(1).strip()

    # Motor independente (caso o padrao 1 nao tenha capturado)
    if not motor:
        m = _RE_MOTOR.search(detalhes)
        if m:
            motor = m.group(1).strip().upper()

    if motor in ('', '-', 'NONE', 'NULL'):
        motor = None
    return (chassi, motor)


def _so_digitos(valor: Optional[str]) -> str:
    return re.sub(r'\D', '', valor or '')


def _parse_data_emissao(valor) -> Optional[date]:
    """Aceita ISO date ou ISO datetime — retorna `date`."""
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, str) and valor:
        try:
            return datetime.fromisoformat(valor.replace('Z', '+00:00')).date()
        except ValueError:
            return None
    return None


def _upsert_emissao_nfe(
    venda: HoraVenda,
    nfe_id_tagplus: int,
    chave_44: str,
    numero_nfe: Optional[str],
    serie_nfe: Optional[str],
    data_emissao,
    status_tagplus: str,
    conta: HoraTagPlusConta,
) -> HoraTagPlusNfeEmissao:
    """Cria ou atualiza HoraTagPlusNfeEmissao para refletir uma NFe vinda
    da API TagPlus.

    Sem isso, a tela /vendas/<id>/nfe/status mostra 'NFe ainda nao
    emitida' e o botao 'Baixar DANFE' nao aparece — o template depende
    de HoraTagPlusNfeEmissao para descobrir o tagplus_nfe_id que e
    repassado ao endpoint /nfes/pdf/recibo_a4/{id}.

    Mapeamento status TagPlus -> NFE_STATUS:
      'A' -> NFE_STATUS_APROVADA
      'S' -> NFE_STATUS_CANCELADA
      '4' -> NFE_STATUS_CANCELADA (inutilizada cai como cancelada local)
    """
    if status_tagplus == 'A':
        status_local = NFE_STATUS_APROVADA
    elif status_tagplus in ('S', '4'):
        status_local = NFE_STATUS_CANCELADA
    else:
        # Defensivo — caller nao deve chamar com outro status, mas se chamar,
        # nao mexe no registro existente.
        existente = HoraTagPlusNfeEmissao.query.filter_by(venda_id=venda.id).first()
        if existente:
            return existente
        # Cria como APROVADA por padrao (best-effort) para nao perder vinculo.
        status_local = NFE_STATUS_APROVADA

    aprovado_em = (
        datetime.combine(data_emissao, datetime.min.time())
        if status_local == NFE_STATUS_APROVADA else None
    )
    cancelado_em_dt = (
        agora_utc_naive() if status_local == NFE_STATUS_CANCELADA else None
    )

    emissao = HoraTagPlusNfeEmissao.query.filter_by(venda_id=venda.id).first()
    if emissao is None:
        emissao = HoraTagPlusNfeEmissao(
            venda_id=venda.id,
            conta_id=conta.id,
            status=status_local,
            tagplus_nfe_id=nfe_id_tagplus,
            numero_nfe=numero_nfe,
            serie_nfe=serie_nfe,
            chave_44=chave_44,
            aprovado_em=aprovado_em,
            cancelado_em=cancelado_em_dt,
            tentativas=0,
        )
        db.session.add(emissao)
        db.session.flush()
        return emissao

    # Atualiza campos vazios + ajusta status quando necessario.
    if not emissao.tagplus_nfe_id:
        emissao.tagplus_nfe_id = nfe_id_tagplus
    if not emissao.numero_nfe and numero_nfe:
        emissao.numero_nfe = numero_nfe
    if not emissao.serie_nfe and serie_nfe:
        emissao.serie_nfe = serie_nfe
    if not emissao.chave_44 and chave_44:
        emissao.chave_44 = chave_44
    if not emissao.aprovado_em and aprovado_em:
        emissao.aprovado_em = aprovado_em
    # Status: nunca regride APROVADA -> CANCELADA so se TagPlus indicou.
    if status_local == NFE_STATUS_CANCELADA and emissao.status != NFE_STATUS_CANCELADA:
        emissao.status = NFE_STATUS_CANCELADA
        if not emissao.cancelado_em:
            emissao.cancelado_em = agora_utc_naive()
    elif status_local == NFE_STATUS_APROVADA and emissao.status not in (
        NFE_STATUS_APROVADA, NFE_STATUS_CANCELADA,
    ):
        emissao.status = NFE_STATUS_APROVADA
    return emissao


def _resolver_modelo_id(codigo_produto: Optional[str]) -> Optional[int]:
    if not codigo_produto:
        return None
    cod = str(codigo_produto).strip()
    if not cod:
        return None
    mapa = HoraTagPlusProdutoMap.query.filter_by(tagplus_codigo=cod).first()
    return mapa.modelo_id if mapa else None


def _extrair_endereco(dest: dict, nfe: dict) -> dict:
    """Extrai campos de endereco do destinatario.

    Procura na ordem:
      1. nfe['endereco_destinatario'] (objeto completo, formato canonico).
      2. dest['enderecos'][0] com principal=True (lista no destinatario).
      3. dest['enderecos'][0] qualquer (primeiro disponivel).
    Retorna dict com chaves: cep, logradouro, numero, complemento, bairro,
    cidade, uf — todos Optional[str].
    """
    end = nfe.get('endereco_destinatario') or {}
    if not isinstance(end, dict) or not end:
        # Fallback: pegar do destinatario.enderecos[]
        enderecos = dest.get('enderecos') or [] if isinstance(dest, dict) else []
        if isinstance(enderecos, list) and enderecos:
            principal = next(
                (e for e in enderecos if isinstance(e, dict) and e.get('principal')),
                None,
            )
            end = principal or (enderecos[0] if isinstance(enderecos[0], dict) else {})

    cidade_obj = end.get('cidade') or {}
    cidade_nome = None
    uf = None
    if isinstance(cidade_obj, dict):
        cidade_nome = (cidade_obj.get('nome') or cidade_obj.get('descricao') or '').strip() or None
        uf = (
            cidade_obj.get('uf')
            or (cidade_obj.get('estado') or {}).get('sigla')
            or (cidade_obj.get('estado') or {}).get('uf')
        )
        if uf:
            uf = uf.strip().upper() or None
    elif isinstance(cidade_obj, str):
        cidade_nome = cidade_obj.strip() or None

    return {
        'cep': _so_digitos(end.get('cep')) or None,
        'logradouro': (end.get('logradouro') or '').strip() or None,
        'numero': (end.get('numero') or '').strip() or None,
        'complemento': (end.get('complemento') or '').strip() or None,
        'bairro': (end.get('bairro') or '').strip() or None,
        'cidade': cidade_nome,
        'uf': uf,
    }


def _extrair_telefone(dest: dict, nfe: dict) -> Optional[str]:
    """Telefone: tenta dados_entrega_telefone -> destinatario.contatos[]."""
    tel = (nfe.get('dados_entrega_telefone') or '').strip()
    if tel:
        return tel
    if isinstance(dest, dict):
        contatos = dest.get('contatos') or []
        if isinstance(contatos, list):
            for c in contatos:
                if not isinstance(c, dict):
                    continue
                v = (c.get('telefone') or c.get('numero') or c.get('valor') or '').strip()
                if v:
                    return v
    return None


def _extrair_email(dest: dict) -> Optional[str]:
    """Email: tenta destinatario.email_principal -> contatos[]."""
    if not isinstance(dest, dict):
        return None
    e = (dest.get('email_principal') or dest.get('email') or '').strip()
    if e:
        return e
    contatos = dest.get('contatos') or []
    if isinstance(contatos, list):
        for c in contatos:
            if not isinstance(c, dict):
                continue
            v = (c.get('email') or '').strip()
            if v:
                return v
    return None


def _resolver_forma_pagamento(faturas: list) -> Optional[str]:
    """Mapeia ID inteiro do TagPlus -> forma_pagamento_hora (PIX, CARTAO_CREDITO...).

    Lookup em HoraTagPlusFormaPagamentoMap.tagplus_forma_id -> forma_pagamento_hora.
    Retorna None se nao houver fatura ou ID nao mapeado (operador edita depois).
    """
    if not faturas or not isinstance(faturas, list):
        return None
    primeira = faturas[0]
    if not isinstance(primeira, dict):
        return None
    fp_id = primeira.get('forma_pagamento')
    if isinstance(fp_id, dict):
        fp_id = fp_id.get('id')
    if fp_id is None:
        return None
    try:
        fp_id = int(fp_id)
    except (TypeError, ValueError):
        return None
    mapa = HoraTagPlusFormaPagamentoMap.query.filter_by(tagplus_forma_id=fp_id).first()
    return mapa.forma_pagamento_hora if mapa else None


def _extrair_parcelas_info(faturas: list) -> tuple[int, int]:
    """Deriva (numero_parcelas, intervalo_dias) das parcelas TagPlus.

    Numero = len(parcelas[0]).
    Intervalo = media arredondada das diferencas em dias entre vencimentos
                consecutivos (tolera vencimentos fora de ordem).
    Defaults: (1, 30) quando nao da pra inferir.
    """
    if not faturas or not isinstance(faturas, list):
        return (1, 30)
    primeira = faturas[0]
    if not isinstance(primeira, dict):
        return (1, 30)
    parcelas = primeira.get('parcelas') or []
    if not isinstance(parcelas, list) or not parcelas:
        return (1, 30)

    n = len(parcelas)
    if n == 1:
        return (1, 30)

    from datetime import datetime as _dt
    dts = []
    for p in parcelas:
        if not isinstance(p, dict):
            continue
        s = p.get('data_vencimento')
        if not s:
            continue
        try:
            d = _dt.fromisoformat(str(s).replace('Z', '+00:00')).date()
            dts.append(d)
        except (ValueError, TypeError):
            continue
    if len(dts) < 2:
        return (n, 30)

    dts.sort()
    diffs = [(dts[i+1] - dts[i]).days for i in range(len(dts) - 1) if (dts[i+1] - dts[i]).days > 0]
    if not diffs:
        return (n, 30)
    media = round(sum(diffs) / len(diffs))
    return (n, max(1, min(90, media)))


# --------------------------------------------------------------------------
# Importador unitario
# --------------------------------------------------------------------------

class NfeJaImportada(Exception):
    """Chave_acesso ja existe e venda nao foi originada por TAGPLUS_API
    (foi importada via DANFE ou criada manualmente — nao deve ser tocada).
    """


class NfeIncompleta(Exception):
    """NFe da API TagPlus sem campos obrigatorios (chave_acesso, valor_nota)."""


def _cancelar_via_backfill(
    venda: HoraVenda,
    status_tagplus: str,
    operador: Optional[str],
    nfe_id_tagplus: Optional[int] = None,
    chave_44: Optional[str] = None,
    numero_nfe: Optional[str] = None,
    serie_nfe: Optional[str] = None,
    data_emissao=None,
    conta: Optional[HoraTagPlusConta] = None,
) -> HoraVenda:
    """Marca venda como CANCELADA + emite DEVOLVIDA nos chassis.

    Diferente de `cancelar_venda` (no venda_service): NAO valida NFe
    em-voo nem aprovacao SEFAZ — porque o cancelamento ja aconteceu na
    SEFAZ (NF historica vinda do TagPlus com status=S/4).

    Idempotente: se ja CANCELADA, retorna sem alterar.

    Se `nfe_id_tagplus` + `conta` forem passados, sincroniza
    HoraTagPlusNfeEmissao (status=CANCELADA) — necessario para a tela
    /vendas/<id>/nfe oferecer o link 'Baixar DANFE' apontando ao TagPlus.
    """
    if venda.status == VENDA_STATUS_CANCELADO:
        # Mesmo se ja cancelado, garante que a emissao reflete tagplus_nfe_id.
        if nfe_id_tagplus and conta and chave_44:
            _upsert_emissao_nfe(
                venda=venda, nfe_id_tagplus=nfe_id_tagplus,
                chave_44=chave_44, numero_nfe=numero_nfe, serie_nfe=serie_nfe,
                data_emissao=data_emissao or venda.data_venda,
                status_tagplus=status_tagplus, conta=conta,
            )
            db.session.commit()
        return venda

    rotulo = {'S': 'Cancelada', '4': 'Inutilizada'}.get(status_tagplus, status_tagplus)
    motivo = (
        f'Backfill TagPlus: NFe esta {rotulo} na SEFAZ (status TagPlus={status_tagplus}). '
        f'Pedido marcado como CANCELADO automaticamente.'
    )

    venda.status = VENDA_STATUS_CANCELADO
    venda.cancelado_em = agora_utc_naive()
    venda.cancelado_por = operador or 'sistema (backfill)'
    venda.cancelamento_motivo = motivo[:500]

    # Emite DEVOLVIDA para cada chassi (libera ao estoque).
    for item in venda.itens:
        registrar_evento(
            numero_chassi=item.numero_chassi,
            tipo='DEVOLVIDA',
            origem_tabela='hora_venda',
            origem_id=venda.id,
            loja_id=venda.loja_id,
            operador=operador or 'sistema (backfill)',
            detalhe=f'NFe {rotulo} via TagPlus (backfill)',
        )

    # Sincroniza HoraTagPlusNfeEmissao (botao 'Baixar DANFE' funcionar).
    if nfe_id_tagplus and conta and chave_44:
        _upsert_emissao_nfe(
            venda=venda, nfe_id_tagplus=nfe_id_tagplus,
            chave_44=chave_44, numero_nfe=numero_nfe, serie_nfe=serie_nfe,
            data_emissao=data_emissao or venda.data_venda,
            status_tagplus=status_tagplus, conta=conta,
        )

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=operador or '',
        acao='CANCELOU',
        detalhe=motivo[:500],
    )

    db.session.commit()
    return venda


def importar_nfe_da_api(
    api: ApiClient,
    nfe_id_tagplus: int,
    operador: Optional[str] = None,
) -> tuple[Optional[HoraVenda], str]:
    """Puxa GET /nfes/{id} e cria/atualiza/cancela HoraVenda conforme status.

    Status TagPlus tratados (nfe.status, doc:185-188):
      - 'A' (Aprovada)    -> cria ou atualiza venda como FATURADO (path normal).
      - 'S' (Cancelada)   -> se venda existe, marca CANCELADO + DEVOLVIDA;
                             se nao existe, skip (nao cria venda cancelada).
      - '4' (Inutilizada) -> mesmo tratamento de 'S'.
      - '2' (Denegada)    -> skip; logger.warning se venda existe.
      - 'N' (Em digitacao)-> skip; logger.warning se venda existe.
      - '0' / outros      -> skip; logger.warning.

    Modo UPSERT para status='A':
      - Se nao existe HoraVenda com essa chave_44 -> cria tudo (HoraVenda +
        itens + eventos VENDIDA + divergencias). Retorna (venda, 'criado').
      - Se existe E origem='TAGPLUS_API' -> atualiza apenas campos em estado
        default/NULL (nao sobrescreve edicoes do operador). Itens sao criados
        se ainda nao existirem. Retorna (venda, 'atualizado'|'inalterado').
      - Se existe com outra origem (DANFE/MANUAL) -> levanta NfeJaImportada.

    Returns:
        Tupla (Optional[HoraVenda], status) com status in:
        {'criado', 'atualizado', 'inalterado', 'cancelado',
         'pulada_cancelada', 'pulada_status_invalido'}.
    """
    from app.hora.services.venda_service import (
        _registrar_divergencia, _resolver_loja_por_cnpj,
    )

    r = api.get(f'/nfes/{nfe_id_tagplus}')
    if r.status_code != 200:
        raise NfeIncompleta(
            f'GET /nfes/{nfe_id_tagplus} retornou {r.status_code}: {r.text[:200]}'
        )
    try:
        nfe = r.json()
    except ValueError:
        raise NfeIncompleta(f'/nfes/{nfe_id_tagplus} resposta nao-JSON')

    # Log diagnostico do JSON da NFe (apenas chaves relevantes).
    logger.info(
        'TagPlus NFe %s: inf_contrib=%r observacoes=%r '
        'end_dest=%s dados_entrega_tel=%r dest_email=%r '
        'faturas=%s itens=%s',
        nfe_id_tagplus,
        (nfe.get('inf_contribuinte') or '')[:300],
        (nfe.get('observacoes') or '')[:200],
        bool(nfe.get('endereco_destinatario')),
        nfe.get('dados_entrega_telefone'),
        ((nfe.get('destinatario') or {}).get('email_principal') or '')[:80],
        [
            {
                'forma_pagamento': f.get('forma_pagamento') if isinstance(f, dict) else None,
                'parcelas_count': len(f.get('parcelas') or []) if isinstance(f, dict) else 0,
            }
            for f in (nfe.get('faturas') or [])[:2]
        ],
        [
            {
                'produto': (it.get('produto') if isinstance(it.get('produto'), (str, int))
                            else (it.get('produto') or {}).get('codigo')),
                'descricao': (it.get('descricao') or '')[:120],
                'detalhes': (it.get('detalhes') or '')[:200],
                'qtd': it.get('qtd'),
                'numero_serie': it.get('numero_serie'),
                'complemento_descricao': (it.get('complemento_descricao') or '')[:200],
            }
            for it in (nfe.get('itens') or [])[:3]
        ],
    )

    chave = nfe.get('chave_acesso')
    if not chave:
        raise NfeIncompleta(f'NFe {nfe_id_tagplus} sem chave_acesso')
    chave = chave.strip()
    if len(chave) != 44:
        raise NfeIncompleta(
            f'NFe {nfe_id_tagplus} chave_acesso invalida (len={len(chave)})'
        )

    existente = HoraVenda.query.filter_by(nf_saida_chave_44=chave).first()
    if existente and existente.origem_criacao != 'TAGPLUS_API':
        raise NfeJaImportada(
            f'NF chave={chave} ja importada (venda_id={existente.id}) '
            f'com origem={existente.origem_criacao} — backfill nao toca '
            f'vendas DANFE/MANUAL.'
        )

    # ------ Switch por status TagPlus (doc:185-188) ------
    status_tagplus = (nfe.get('status') or '').strip().upper()

    # CANCELADA / INUTILIZADA: cancela venda existente; nao cria nova.
    if status_tagplus in ('S', '4'):
        if existente:
            ja_cancelada = existente.status == VENDA_STATUS_CANCELADO
            # Tenta extrair numero/serie/data para sincronizar emissao.
            numero_nf = str(nfe.get('numero') or '')[:20] or None
            serie_nf = str(nfe.get('serie') or '') or None
            data_emis = _parse_data_emissao(nfe.get('data_emissao')) or date.today()
            cancelada = _cancelar_via_backfill(
                existente, status_tagplus, operador,
                nfe_id_tagplus=nfe_id_tagplus,
                chave_44=chave,
                numero_nfe=numero_nf,
                serie_nfe=serie_nf,
                data_emissao=data_emis,
                conta=api.conta,
            )
            return cancelada, ('inalterado' if ja_cancelada else 'cancelado')
        logger.info(
            'Pulando NFe %s (chave=%s) — status TagPlus=%r (cancelada/inutilizada) '
            'e venda nao existe no sistema.',
            nfe_id_tagplus, chave, status_tagplus,
        )
        return None, 'pulada_cancelada'

    # DENEGADA / EM-DIGITACAO / INDIFERENTE: pular sem criar.
    if status_tagplus in ('2', 'N', '0', ''):
        if existente:
            logger.warning(
                'Venda %s existe localmente mas TagPlus retornou status=%r '
                '(denegada/em-digitacao) — investigar inconsistencia.',
                existente.id, status_tagplus,
            )
        else:
            logger.info(
                'Pulando NFe %s — status TagPlus=%r (nao-aprovada).',
                nfe_id_tagplus, status_tagplus,
            )
        return None, 'pulada_status_invalido'

    # Status APROVADA: continua fluxo normal de criacao/upsert.
    valor_nota = nfe.get('valor_nota')
    if valor_nota is None:
        raise NfeIncompleta(
            f'NFe {nfe_id_tagplus} APROVADA mas sem valor_nota'
        )

    # ------ destinatario (cliente) ------
    dest = nfe.get('destinatario') or {}
    cpf = _so_digitos(dest.get('cpf') or dest.get('cnpj'))
    if len(cpf) != 11:
        raise NfeIncompleta(
            f'NFe {nfe_id_tagplus} destinatario sem CPF valido (got={cpf!r})'
        )
    nome_cliente = (dest.get('razao_social') or '').strip()[:200] or 'CLIENTE_NAO_INFORMADO'

    # ------ emitente -> loja ------
    emit = nfe.get('emitente') or {}
    cnpj_emitente = _so_digitos(emit.get('cnpj'))[:20] or None
    loja_emitente = _resolver_loja_por_cnpj(cnpj_emitente) if cnpj_emitente else None

    # ------ datas / numeros ------
    data_emissao = _parse_data_emissao(nfe.get('data_emissao')) or date.today()
    numero_nf = str(nfe.get('numero') or '')[:20]
    serie_nf = str(nfe.get('serie') or '') or None

    # ------ frete + parcelamento (best-effort, defaults preservam comportamento) ------
    modalidade_frete = str(nfe.get('modalidade_frete') or '9')
    if modalidade_frete not in ('0', '1', '2', '3', '4', '9'):
        modalidade_frete = '9'

    valor_total_dec = Decimal(str(valor_nota))

    # ------ Endereco / contato / pagamento ------
    endereco = _extrair_endereco(dest, nfe)
    telefone = _extrair_telefone(dest, nfe)
    email = _extrair_email(dest)

    faturas_api = nfe.get('faturas') or []
    forma_pgto_hora = _resolver_forma_pagamento(faturas_api)
    n_parcelas, interv_parcelas = _extrair_parcelas_info(faturas_api)

    # CEP: hora_venda armazena no formato "XXXXX-XXX".
    cep_db = endereco['cep']
    if cep_db and len(cep_db) == 8:
        cep_db = f'{cep_db[:5]}-{cep_db[5:]}'

    # Itens da API (compartilhado entre fluxo UPSERT e CREATE).
    itens_raw = nfe.get('itens') or []

    # ------ MODO UPSERT: se ja existe TAGPLUS_API, atualiza campos vazios ------
    if existente:
        status_upsert = _atualizar_campos_vazios(
            venda=existente,
            cep_db=cep_db,
            endereco=endereco,
            telefone=telefone,
            email=email,
            forma_pagamento=forma_pgto_hora,
            modalidade_frete=modalidade_frete,
            n_parcelas=n_parcelas,
            interv_parcelas=interv_parcelas,
            cnpj_emitente=cnpj_emitente,
            loja_emitente_id=loja_emitente.id if loja_emitente else None,
        )
        # Se nao tem itens ainda, tenta criar agora.
        criou_itens = False
        if not existente.itens:
            inf_contribuinte_nf = nfe.get('inf_contribuinte') or ''
            observacoes_nf = nfe.get('observacoes') or ''
            antes = {it.id for it in existente.itens}
            _criar_itens_da_api(
                venda=existente,
                itens_api=itens_raw,
                loja_emitente_id=loja_emitente.id if loja_emitente else None,
                data_venda=data_emissao,
                operador=operador,
                inf_contribuinte_nf=inf_contribuinte_nf,
                observacoes_nf=observacoes_nf,
            )
            db.session.flush()
            criou_itens = any(it.id not in antes for it in existente.itens)

        # Sincroniza HoraTagPlusNfeEmissao (botao 'Baixar DANFE' funcionar).
        emissao_existia = HoraTagPlusNfeEmissao.query.filter_by(venda_id=existente.id).first() is not None
        _upsert_emissao_nfe(
            venda=existente, nfe_id_tagplus=nfe_id_tagplus,
            chave_44=chave, numero_nfe=numero_nf, serie_nfe=serie_nf,
            data_emissao=data_emissao, status_tagplus='A', conta=api.conta,
        )
        criou_emissao = not emissao_existia

        if status_upsert or criou_itens or criou_emissao:
            venda_audit.registrar_auditoria(
                venda_id=existente.id, usuario=operador or '',
                acao='EDITOU_HEADER',
                detalhe=(
                    f'Backfill TagPlus refresh — '
                    f'campos atualizados={status_upsert}, '
                    f'itens_criados={criou_itens}, '
                    f'emissao_criada={criou_emissao}'
                ),
            )
            db.session.commit()
            return existente, 'atualizado'
        db.session.commit()
        return existente, 'inalterado'

    # ------ Cria HoraVenda (nova) ------
    venda = HoraVenda(
        loja_id=loja_emitente.id if loja_emitente else None,
        cpf_cliente=cpf[:14],
        nome_cliente=nome_cliente,
        telefone_cliente=(telefone or '')[:20] or None,
        email_cliente=(email or '')[:120] or None,
        data_venda=data_emissao,
        forma_pagamento=forma_pgto_hora or 'NAO_INFORMADO',
        valor_total=valor_total_dec,
        nf_saida_numero=numero_nf,
        nf_saida_chave_44=chave,
        nf_saida_emitida_em=datetime.combine(data_emissao, datetime.min.time()),
        arquivo_pdf_s3_key=None,
        parser_usado='tagplus_api_v1',
        parseada_em=agora_utc_naive(),
        cnpj_emitente=cnpj_emitente,
        status=VENDA_STATUS_FATURADO,
        faturado_em=datetime.combine(data_emissao, datetime.min.time()),
        vendedor=None,
        origem_criacao='TAGPLUS_API',
        modalidade_frete=modalidade_frete,
        numero_parcelas=n_parcelas,
        intervalo_parcelas_dias=interv_parcelas,
        cep=cep_db,
        endereco_logradouro=(endereco['logradouro'] or '')[:255] or None,
        endereco_numero=(endereco['numero'] or '')[:20] or None,
        endereco_complemento=(endereco['complemento'] or '')[:100] or None,
        endereco_bairro=(endereco['bairro'] or '')[:100] or None,
        endereco_cidade=(endereco['cidade'] or '')[:100] or None,
        endereco_uf=endereco['uf'],
    )
    db.session.add(venda)
    db.session.flush()

    if not loja_emitente:
        _registrar_divergencia(
            venda_id=venda.id, tipo='CNPJ_DESCONHECIDO',
            detalhe=(
                f'CNPJ emitente {cnpj_emitente!r} nao bate com nenhuma HoraLoja. '
                f'Defina manualmente na tela de detalhe.'
            ),
            valor_conferido=cnpj_emitente,
        )

    # ------ Itens -> HoraVendaItem + eventos ------
    _ = serie_nf  # serie capturada para futuro armazenamento (hoje hora_venda nao guarda)
    inf_contribuinte_nf = nfe.get('inf_contribuinte') or ''
    observacoes_nf = nfe.get('observacoes') or ''
    _criar_itens_da_api(
        venda=venda,
        itens_api=itens_raw,
        loja_emitente_id=loja_emitente.id if loja_emitente else None,
        data_venda=data_emissao,
        operador=operador,
        inf_contribuinte_nf=inf_contribuinte_nf,
        observacoes_nf=observacoes_nf,
    )

    # Sincroniza HoraTagPlusNfeEmissao para o botao 'Baixar DANFE'
    # funcionar na tela /vendas/<id>/nfe.
    _upsert_emissao_nfe(
        venda=venda, nfe_id_tagplus=nfe_id_tagplus,
        chave_44=chave, numero_nfe=numero_nf, serie_nfe=serie_nf,
        data_emissao=data_emissao, status_tagplus='A', conta=api.conta,
    )

    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=operador or '',
        acao='CRIOU',
        detalhe=(
            f'Backfill via API TagPlus — NF {numero_nf} chave={chave} '
            f'(tagplus_nfe_id={nfe_id_tagplus})'
        ),
    )

    db.session.commit()
    return venda, 'criado'


def _atualizar_campos_vazios(
    venda: HoraVenda,
    cep_db: Optional[str],
    endereco: dict,
    telefone: Optional[str],
    email: Optional[str],
    forma_pagamento: Optional[str],
    modalidade_frete: str,
    n_parcelas: int,
    interv_parcelas: int,
    cnpj_emitente: Optional[str],
    loja_emitente_id: Optional[int],
) -> bool:
    """Atualiza campos da venda existente que estao em estado default/NULL.

    NAO sobrescreve valores ja preenchidos (preserva edicoes do operador).

    Definicao de "vazio":
      - Strings: None, '' ou 'NAO_INFORMADO' (forma_pagamento).
      - Numero: para parcelas/intervalo, considera vazio se = default
        (1 / 30) E API tem valor diferente (>1 / != 30).
      - modalidade_frete: vazio se = '9' (default) E API retorna outro.

    Returns:
        True se algum campo foi alterado, False caso contrario.
    """
    alterou = False

    def _set_se_vazio(campo: str, novo_valor, vazios=(None, '')):
        nonlocal alterou
        atual = getattr(venda, campo, None)
        if atual in vazios and novo_valor not in vazios:
            setattr(venda, campo, novo_valor)
            alterou = True

    # Endereco / contato
    _set_se_vazio('cep', cep_db)
    _set_se_vazio('endereco_logradouro', (endereco.get('logradouro') or '')[:255] or None)
    _set_se_vazio('endereco_numero', (endereco.get('numero') or '')[:20] or None)
    _set_se_vazio('endereco_complemento', (endereco.get('complemento') or '')[:100] or None)
    _set_se_vazio('endereco_bairro', (endereco.get('bairro') or '')[:100] or None)
    _set_se_vazio('endereco_cidade', (endereco.get('cidade') or '')[:100] or None)
    _set_se_vazio('endereco_uf', endereco.get('uf'))
    _set_se_vazio('telefone_cliente', (telefone or '')[:20] or None)
    _set_se_vazio('email_cliente', (email or '')[:120] or None)

    # Forma de pagamento: 'NAO_INFORMADO' tambem conta como vazio.
    if (
        venda.forma_pagamento in (None, '', 'NAO_INFORMADO')
        and forma_pagamento and forma_pagamento != 'NAO_INFORMADO'
    ):
        venda.forma_pagamento = forma_pagamento
        alterou = True

    # Loja / CNPJ emitente: so preenche se NULL.
    _set_se_vazio('cnpj_emitente', cnpj_emitente)
    if venda.loja_id is None and loja_emitente_id is not None:
        venda.loja_id = loja_emitente_id
        alterou = True

    # Modalidade de frete: '9' eh default; se API retornou outro, atualiza.
    if (venda.modalidade_frete or '9') == '9' and modalidade_frete != '9':
        venda.modalidade_frete = modalidade_frete
        alterou = True

    # Parcelas: defaults sao (1, 30); se API trouxe valores reais, atualiza.
    atual_n = venda.numero_parcelas or 1
    atual_interv = venda.intervalo_parcelas_dias or 30
    if (atual_n, atual_interv) == (1, 30) and (n_parcelas, interv_parcelas) != (1, 30):
        venda.numero_parcelas = n_parcelas
        venda.intervalo_parcelas_dias = interv_parcelas
        alterou = True

    return alterou


def _criar_itens_da_api(
    venda: HoraVenda,
    itens_api: list,
    loja_emitente_id: Optional[int],
    data_venda,
    operador: Optional[str],
    inf_contribuinte_nf: str = '',
    observacoes_nf: str = '',
) -> None:
    """Cria HoraVendaItem para cada chassi listado em `itens_api`.

    Cada item TagPlus pode ter `qtd > 1` — nesse caso espera-se 1 chassi por
    unidade.

    Estrategia (ordem de busca do chassi):
      1. `item.detalhes`               (NFs emitidas via PayloadBuilder).
      2. `item.descricao`              (texto livre do item).
      3. `item.complemento_descricao`  (campo opcional do TagPlus).
      4. `item.numero_serie`           (campo nativo NFe).
      5. `inf_contribuinte` da NFe-mae (texto livre comum em NFs historicas).
      6. `observacoes` da NFe-mae.

    Quando nenhum dos campos tem chassi extraivel, registra divergencia
    CHASSI_NAO_CADASTRADO com diagnostico das fontes consultadas.
    """
    from app.hora.services.venda_service import (
        _registrar_divergencia, _resolver_preco_tabela,
    )

    # Pre-extrai chassi(s) do nivel da NFe-mae (compartilhado entre os itens).
    nfe_chassis = _extrair_chassis_multiplos(
        f'{inf_contribuinte_nf}\n{observacoes_nf}'
    )
    nfe_chassis_iter = iter(nfe_chassis)

    for it in itens_api:
        if not isinstance(it, dict):
            continue
        # `produto` no JSON do TagPlus pode ser dict ou ID inteiro/string.
        prod = it.get('produto')
        codigo_produto = None
        descricao = (it.get('descricao') or '').strip()
        if isinstance(prod, dict):
            codigo_produto = (prod.get('codigo') or prod.get('cod_secundario') or '').strip() or None
            descricao = descricao or (prod.get('descricao') or '').strip()
        elif isinstance(prod, (int, str)):
            # Se vier ID puro, tenta resolver por tagplus_produto_id na map.
            map_ = HoraTagPlusProdutoMap.query.filter_by(
                tagplus_produto_id=str(prod),
            ).first()
            if map_:
                codigo_produto = map_.tagplus_codigo

        qtd = int(it.get('qtd') or 1)
        valor_unitario = Decimal(str(it.get('valor_unitario') or 0))
        valor_desconto = Decimal(str(it.get('valor_desconto') or 0))
        preco_final_unit = (valor_unitario - (valor_desconto / qtd if qtd else 0))

        # ----- Extracao do chassi: tenta multiplas fontes em ordem -----
        detalhes = (it.get('detalhes') or '').strip()
        descricao_raw = (it.get('descricao') or '').strip()
        complemento = (it.get('complemento_descricao') or '').strip()
        numero_serie = (it.get('numero_serie') or '').strip()

        chassis_motores: list[tuple[Optional[str], Optional[str]]] = []
        fontes_tentadas = []

        for fonte_nome, fonte_valor in [
            ('detalhes', detalhes),
            ('descricao', descricao_raw),
            ('complemento_descricao', complemento),
            ('numero_serie', numero_serie),
        ]:
            fontes_tentadas.append(f'{fonte_nome}={fonte_valor[:60]!r}')
            extraidos = _extrair_chassis_multiplos(fonte_valor)
            if extraidos:
                chassis_motores = extraidos
                logger.info(
                    'Chassi extraido de item.%s: %s', fonte_nome,
                    [p[0] for p in extraidos],
                )
                break

        # Fallback final: consome 1 chassi do `inf_contribuinte`/`observacoes`
        # da NFe-mae (na ordem em que aparecem no texto, 1 por item).
        if not chassis_motores:
            try:
                par = next(nfe_chassis_iter)
                chassis_motores = [par]
                fontes_tentadas.append('NFe.inf_contribuinte/observacoes (fallback)')
                logger.info(
                    'Chassi fallback NFe-mae para item produto=%r: %s',
                    codigo_produto, par[0],
                )
            except StopIteration:
                pass

        if not chassis_motores:
            _registrar_divergencia(
                venda_id=venda.id, tipo='CHASSI_NAO_CADASTRADO',
                detalhe=(
                    f'Item produto={codigo_produto or descricao!r} qtd={qtd} '
                    f'sem chassi extraivel. Fontes consultadas: '
                    f'{" | ".join(fontes_tentadas)}.'
                )[:1000],
                valor_conferido=(detalhes or descricao_raw)[:255],
            )
            continue

        modelo_id_resolvido = _resolver_modelo_id(codigo_produto)

        for chassi, motor in chassis_motores:
            chassi_norm = (chassi or '').strip().upper()
            if not chassi_norm:
                continue

            moto_existia = HoraMoto.query.get(chassi_norm) is not None

            if modelo_id_resolvido and not moto_existia:
                moto = HoraMoto(
                    numero_chassi=chassi_norm,
                    modelo_id=modelo_id_resolvido,
                    cor='NAO_INFORMADA',
                    numero_motor=motor,
                    ano_modelo=None,
                    criado_por=operador,
                )
                db.session.add(moto)
                db.session.flush()
            else:
                moto = get_or_create_moto(
                    numero_chassi=chassi_norm,
                    modelo_nome=descricao or codigo_produto or 'MODELO_DESCONHECIDO',
                    cor='NAO_INFORMADA',
                    numero_motor=motor,
                    ano_modelo=None,
                    criado_por=operador,
                )
                if codigo_produto and not modelo_id_resolvido and not moto_existia:
                    _registrar_divergencia(
                        venda_id=venda.id, tipo='TABELA_PRECO_AUSENTE',
                        numero_chassi=chassi_norm,
                        detalhe=(
                            f'Codigo TagPlus {codigo_produto!r} nao mapeado em '
                            f'hora_tagplus_produto_map. Mapear em '
                            f'/hora/modelos/{moto.modelo_id}/editar.'
                        ),
                        valor_conferido=codigo_produto,
                    )

            ult = ultimo_evento(chassi_norm)
            if ult is not None:
                if ult.tipo not in EVENTOS_EM_ESTOQUE:
                    _registrar_divergencia(
                        venda_id=venda.id, tipo='CHASSI_INDISPONIVEL',
                        numero_chassi=chassi_norm,
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
                        numero_chassi=chassi_norm,
                        detalhe=(
                            f'Chassi estava na loja {ult.loja_id} mas NF foi '
                            f'emitida pela loja {loja_emitente_id}'
                        ),
                        valor_esperado=str(loja_emitente_id),
                        valor_conferido=str(ult.loja_id),
                    )

            preco_ref, desconto, tabela_id, divergencia_tipo = _resolver_preco_tabela(
                moto.modelo_id, data_venda, preco_final_unit,
            )
            if divergencia_tipo:
                _registrar_divergencia(
                    venda_id=venda.id, tipo=divergencia_tipo,
                    numero_chassi=chassi_norm,
                    detalhe=f'preco_final={preco_final_unit}',
                    valor_esperado=str(preco_ref),
                    valor_conferido=str(preco_final_unit),
                )

            venda_item = HoraVendaItem(
                venda_id=venda.id,
                numero_chassi=chassi_norm,
                tabela_preco_id=tabela_id,
                preco_tabela_referencia=preco_ref,
                desconto_aplicado=desconto,
                preco_final=preco_final_unit,
            )
            db.session.add(venda_item)
            db.session.flush()

            registrar_evento(
                numero_chassi=chassi_norm,
                tipo='VENDIDA',
                origem_tabela='hora_venda_item',
                origem_id=venda_item.id,
                loja_id=loja_emitente_id,
                operador=operador,
                detalhe=f'Backfill TagPlus venda #{venda.id}',
            )


def _extrair_chassis_multiplos(detalhes: str) -> list[tuple[Optional[str], Optional[str]]]:
    """Extrai pares (chassi, motor) de uma string `detalhes`.

    Suporta:
      - 'Chassi: X / Motor: Y'                       (1 par)
      - 'Chassi: X1 / Motor: Y1 ; Chassi: X2 ...'    (N pares separados por ; ou |)
    """
    if not detalhes:
        return []
    partes = re.split(r'[;|\n]+', detalhes)
    pares: list[tuple[Optional[str], Optional[str]]] = []
    for p in partes:
        c, m = _extrair_chassi_motor(p)
        if c:
            pares.append((c, m))
    if not pares:
        c, m = _extrair_chassi_motor(detalhes)
        if c:
            pares.append((c, m))
    return pares


# --------------------------------------------------------------------------
# Orquestrador
# --------------------------------------------------------------------------

def executar_backfill(
    since: Optional[date] = None,
    until: Optional[date] = None,
    operador: Optional[str] = None,
    limite: Optional[int] = None,
) -> dict:
    """Lista NFes da API TagPlus no intervalo + importa cada uma.

    Args:
        since/until: filtros de data_emissao (inclusivo).
        operador: nome do usuario logado para auditoria.
        limite: maximo de NFes a importar (None = sem limite). Util para
            testes ou primeiro lote.

    Returns:
        dict com contadores e lista detalhada de cada NFe processada.
    """
    conta = HoraTagPlusConta.ativa()
    api = ApiClient(conta)

    resultados = []
    n_criado = n_atualizado = n_inalterado = 0
    n_cancelado = n_pulada_cancelada = n_pulada_invalida = 0
    n_dup = n_err = n_div = 0

    iterador = listar_nfes_emitidas(api, since=since, until=until)
    for i, nfe_resumo in enumerate(iterador):
        if limite is not None and i >= limite:
            break

        nfe_id = nfe_resumo.get('id')
        chave_resumo = nfe_resumo.get('chave_acesso')
        numero_resumo = nfe_resumo.get('numero')
        status_resumo = nfe_resumo.get('status')

        entry = {
            'tagplus_nfe_id': nfe_id,
            'numero_nf': numero_resumo,
            'chave': chave_resumo,
            'status_tagplus': status_resumo,
            'status': None,
            'venda_id': None,
            'qtd_chassis': 0,
            'qtd_divergencias': 0,
            'mensagem': '',
        }
        if not nfe_id:
            entry['status'] = 'erro'
            entry['mensagem'] = 'NFe na listagem sem campo `id`'
            n_err += 1
            resultados.append(entry)
            continue

        try:
            venda, status = importar_nfe_da_api(api, nfe_id, operador=operador)

            if venda is not None:
                entry.update({
                    'venda_id': venda.id,
                    'numero_nf': venda.nf_saida_numero,
                    'qtd_chassis': len(venda.itens),
                    'qtd_divergencias': len(venda.divergencias_abertas),
                })
                n_div += len(venda.divergencias_abertas)
            entry['status'] = status

            if status == 'criado':
                entry['mensagem'] = (
                    f'NF {venda.nf_saida_numero} criada — '
                    f'{len(venda.itens)} chassi(s) para {venda.nome_cliente}.'
                )
                n_criado += 1
            elif status == 'atualizado':
                entry['mensagem'] = (
                    f'NF {venda.nf_saida_numero} atualizada (campos vazios '
                    f'preenchidos a partir da API).'
                )
                n_atualizado += 1
            elif status == 'inalterado':
                entry['mensagem'] = (
                    f'NF {venda.nf_saida_numero} ja estava completa — nada a fazer.'
                )
                n_inalterado += 1
            elif status == 'cancelado':
                entry['mensagem'] = (
                    f'NF {venda.nf_saida_numero} CANCELADA na SEFAZ '
                    f'(TagPlus={status_resumo!r}). Pedido marcado como '
                    f'CANCELADO + DEVOLVIDA emitida nos chassis.'
                )
                n_cancelado += 1
            elif status == 'pulada_cancelada':
                entry['mensagem'] = (
                    f'NFe cancelada/inutilizada (TagPlus={status_resumo!r}) '
                    f'e nao existia no sistema — pulada.'
                )
                n_pulada_cancelada += 1
            elif status == 'pulada_status_invalido':
                entry['mensagem'] = (
                    f'NFe com status nao-aprovado (TagPlus={status_resumo!r}) '
                    f'— pulada.'
                )
                n_pulada_invalida += 1
            else:
                entry['mensagem'] = f'Status retornado desconhecido: {status!r}'
                n_err += 1
        except NfeJaImportada as exc:
            entry['status'] = 'duplicado'
            entry['mensagem'] = str(exc)
            n_dup += 1
        except NfeIncompleta as exc:
            entry['status'] = 'erro'
            entry['mensagem'] = f'Incompleta: {exc}'
            n_err += 1
            db.session.rollback()
        except Exception as exc:  # pragma: no cover
            entry['status'] = 'erro'
            entry['mensagem'] = f'Erro inesperado: {exc}'
            n_err += 1
            db.session.rollback()
            logger.exception('Backfill: falha NFe %s', nfe_id)
        resultados.append(entry)

    return {
        'total': len(resultados),
        'criado': n_criado,
        'atualizado': n_atualizado,
        'inalterado': n_inalterado,
        'cancelado': n_cancelado,
        'pulada_cancelada': n_pulada_cancelada,
        'pulada_invalida': n_pulada_invalida,
        # `sucesso` = criado + atualizado (compat com codigo antigo).
        'sucesso': n_criado + n_atualizado,
        'duplicado': n_dup,
        'erro': n_err,
        'divergencias': n_div,
        'resultados': resultados,
    }
