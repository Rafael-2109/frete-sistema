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
import os
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Callable, Iterator, Optional

from flask import current_app

from app import db
from app.hora.models import HoraMoto, HoraMotoEvento, HoraVenda, HoraVendaItem
from app.hora.models.tagplus import (
    HoraTagPlusConta, HoraTagPlusFormaPagamentoMap, HoraTagPlusNfeEmissao,
    HoraTagPlusProdutoMap,
    NFE_STATUS_APROVADA, NFE_STATUS_CANCELADA,
)
from app.hora.models.venda import VENDA_STATUS_CANCELADO, VENDA_STATUS_FATURADO
from app.hora.services import venda_audit
from app.hora.services.estoque_service import EVENTOS_EM_ESTOQUE
from app.hora.services.moto_service import (
    devolver_ao_estoque, get_or_create_moto, registrar_evento, ultimo_evento,
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
    r'Chassi\s*[:\.\-]?\s*<?\s*([A-Z0-9][A-Z0-9\-]*)\s*>?'
    r'(?:\s*[/,;]?\s*Motor\s*[:\.\-]?\s*<?\s*([A-Z0-9][A-Z0-9\-]*)\s*>?)?',
    re.IGNORECASE,
)

# Padroes alternativos comuns em NFs TagPlus historicas (preenchimento manual):
#   "N° SERIE: XXX / SERIE: XXX / Nº SERIE: XXX / Nº SERIE: < 172922502660076>"
# Suporta:
#   - <, >, espaços ao redor do valor (NFs com chassi 100% numérico).
#   - Chassi alfanumérico OU numérico puro (ex.: 172922502660076).
_RE_NSERIE = re.compile(
    r'(?:N[ºo°]?|Numero)\s*[:\.\-]?\s*(?:SERIE|S[eé]rie|CHASSI|Chassi)\s*[:\.\-]?\s*'
    r'<?\s*([A-Z0-9][A-Z0-9\-]{8,29})\s*>?',
    re.IGNORECASE,
)

# Chassi com label standalone "CHASSI: ###" (sem prefixo "Nº" exigido).
# Necessario para layouts onde a NF lista MOTOR e CHASSI em linhas separadas:
#   MOTOR: 12345
#   CHASSI: 67890
# Sem este regex, o `_RE_CHASSI_MOTOR` (que exige Chassi antes de Motor) e
# o `_RE_NSERIE` (que exige "Nº" prefix) nao matcham, e o fallback
# `_RE_CHASSI_PURO` so funciona se ambos tiverem 13+ chars.
_RE_CHASSI_LABEL = re.compile(
    r'\bCHASSI\s*[:\.\-]\s*<?\s*([A-Z0-9][A-Z0-9\-]{5,29})\s*>?',
    re.IGNORECASE,
)

# Chassis "puros" (string alfanumerica longa) — ultima cartada quando rotulos
# estao ausentes. Aceita 13-30 chars alfanuméricos (incluindo 100% numéricos
# como 172922502660076). Exclui-se motor já capturado para não duplicar.
_RE_CHASSI_PURO = re.compile(r'\b([A-Z0-9]{13,30})\b', re.IGNORECASE)

_RE_MOTOR = re.compile(
    r'Motor\s*[:\.\-]?\s*<?\s*([A-Z0-9][A-Z0-9\-]{5,29})\s*>?',
    re.IGNORECASE,
)

# Cor: aceita "COR: <Cinza>", "COR: Vermelho", "COR Cinza" (sem :)
# Para na próxima palavra reservada (ANO/MOD/MOTOR/Nº/N°/GARANTIA) ou pontuação.
_RE_COR = re.compile(
    r'\bCOR\s*[:\.\-]?\s*<?\s*'
    r'([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]*?)'
    r'\s*>?(?=\s*(?:ANO\b|MOD\b|MOTOR\b|N[ºo°]?\b|Numero\b|GARANTIA\b|[<>\.,;\|]|$))',
    re.IGNORECASE,
)

# Ano modelo: "ANO 2025/MOD 2025", "ANO: 2025", "MOD 2025"
_RE_ANO_MODELO = re.compile(
    r'(?:ANO|MOD)\s*[:\.\-]?\s*(\d{4})',
    re.IGNORECASE,
)


def _extrair_chassi_motor(detalhes: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Parsa string `detalhes` do item TagPlus.

    Tenta na ordem:
      1. 'Chassi: X / Motor: Y'  (formato do nosso PayloadBuilder).
      2. 'N° SERIE: X' ou 'CHASSI: X'  (NFs historicas TagPlus).
      3. Token alfanumerico 13+ chars  (ultima cartada).
    Motor extraido separado quando presente.

    Garante que o token capturado como motor NAO seja recapturado como chassi
    no fallback (`_RE_CHASSI_PURO`).
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

    # Motor independente — extraido cedo para que possa ser excluido do
    # fallback `_RE_CHASSI_PURO` (evita gravar motor como chassi).
    if not motor:
        m = _RE_MOTOR.search(detalhes)
        if m:
            motor = m.group(1).strip().upper()

    # 2) Padrao "N° SERIE: ..." (TagPlus historico) — aceita <,>,espacos
    if not chassi:
        m = _RE_NSERIE.search(detalhes)
        if m:
            chassi = m.group(1).strip().upper()

    # 2.5) Padrao "CHASSI: ..." standalone (sem prefixo Nº exigido).
    # Layouts MOTOR\nCHASSI usam esse formato.
    if not chassi:
        m = _RE_CHASSI_LABEL.search(detalhes)
        if m:
            chassi = m.group(1).strip().upper()

    # 3) Token bruto longo (fallback) — aceita chassi 100% numerico, mas
    # exclui o token ja capturado como motor.
    if not chassi:
        texto_upper = detalhes.upper()
        for cand in _RE_CHASSI_PURO.findall(texto_upper):
            cand_norm = cand.strip()
            if motor and cand_norm == motor:
                continue
            chassi = cand_norm
            break

    # NAO chamamos LLM aqui (per-NF) — em backfill inicial com 500+ NFs ficaria
    # lento e caro. O fallback LLM acontece em UMA UNICA chamada batch ao FIM
    # do job (ver `_resolver_pendencias_chassi_em_batch` em executar_backfill).
    # Os HoraVendaItem sem chassi sao reconciliados depois.

    if motor in ('', '-', 'NONE', 'NULL'):
        motor = None
    return (chassi, motor)


def _extrair_cor_ano(texto: Optional[str]) -> tuple[Optional[str], Optional[int]]:
    """Extrai (cor, ano_modelo) do `inf_contribuinte`/`observacoes` da NFe.

    Padroes suportados:
      - 'COR: <Cinza>'  -> 'CINZA'
      - 'COR Vermelho'  -> 'VERMELHO'
      - 'ANO 2025/MOD 2025' -> 2025
      - 'MOD 2025'      -> 2025

    Retorna (None, None) quando nao consegue extrair.
    """
    if not texto:
        return (None, None)
    cor = None
    ano = None

    m = _RE_COR.search(texto)
    if m:
        cor_raw = (m.group(1) or '').strip().upper()
        # Filtra valores improvaveis (1 char, palavras-reservadas).
        if cor_raw and len(cor_raw) >= 3 and cor_raw not in (
            'NAO', 'NÃO', 'INFORMADA', 'INFORMADO',
        ):
            cor = cor_raw

    # Para ano, prefere o "MOD" (ano modelo) em vez do "ANO" (ano fabricacao).
    matches = list(_RE_ANO_MODELO.finditer(texto))
    if matches:
        # Preferir "MOD <ANO>" se existir; senao usa o primeiro "ANO <ANO>".
        mod_match = next(
            (m for m in matches if m.group(0).upper().startswith('MOD')),
            None,
        )
        chosen = mod_match or matches[0]
        try:
            ano_int = int(chosen.group(1))
            if 1990 <= ano_int <= 2099:
                ano = ano_int
        except (ValueError, TypeError):
            pass

    return (cor, ano)


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

    # Defesa: extrair conta.id ANTES de qualquer query que possa expirar/detachar.
    # Em runs longos do backfill, mesmo com api.conta sendo property, o objeto
    # passado aqui pode estar expired após commits intermediários. Snapshot
    # imediato evita refresh implícito quando acessarmos conta.id no construtor.
    try:
        conta_id_snapshot = int(conta.id)
    except Exception:
        # Se acessar .id falhar (DetachedInstanceError), tenta extrair PK via inspect.
        from sqlalchemy import inspect as _sa_inspect
        try:
            pk = _sa_inspect(conta).identity[0]  # type: ignore[index]
            conta_id_snapshot = int(pk)
        except Exception as exc:
            raise RuntimeError(
                f'Conta TagPlus em estado inválido em _upsert_emissao_nfe: {exc!r}'
            ) from exc

    emissao = HoraTagPlusNfeEmissao.query.filter_by(venda_id=venda.id).first()
    if emissao is None:
        emissao = HoraTagPlusNfeEmissao(
            venda_id=venda.id,
            conta_id=conta_id_snapshot,
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
    """Resolve codigo TagPlus -> modelo canonico.

    Migration hora_29: agora consulta resolver_via_tagplus (que cobre
    HoraModeloAlias com tipo TAGPLUS_CODIGO + fallback legado em
    hora_tagplus_produto_map). Mantem compat com codigo antigo.
    """
    if not codigo_produto:
        return None
    cod = str(codigo_produto).strip()
    if not cod:
        return None
    from app.hora.services.modelo_resolver_service import resolver_via_tagplus
    modelo = resolver_via_tagplus(tagplus_codigo=cod)
    return modelo.id if modelo else None


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

    # Libera cada chassi ao estoque (re-emite o estado-em-estoque anterior;
    # NFe cancelada/inutilizada = a moto nao saiu, volta a ficar disponivel).
    for item in venda.itens:
        devolver_ao_estoque(
            numero_chassi=item.numero_chassi,
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
    pendencias_chassi_llm: Optional[list] = None,
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
        _registrar_divergencia, _resolver_loja_real_venda,
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
    # Aceita PF (CPF, 11 digitos) ou PJ (CNPJ, 14 digitos). Coluna
    # `cpf_cliente` em hora_venda eh String(14) — comporta ambos. O nome
    # da coluna eh historico (modulo nasceu B2C); semanticamente e
    # "documento fiscal do destinatario".
    from app.hora.services.tagplus._documento import normalizar_documento
    dest = nfe.get('destinatario') or {}
    cpf, tipo_doc = normalizar_documento(dest.get('cpf') or dest.get('cnpj'))
    if not tipo_doc:
        raise NfeIncompleta(
            f'NFe {nfe_id_tagplus} destinatario sem CPF/CNPJ valido '
            f'(got={cpf!r}, esperado 11 ou 14 digitos)'
        )
    nome_cliente = (dest.get('razao_social') or '').strip()[:200] or 'CLIENTE_NAO_INFORMADO'

    # ------ emitente -> loja ------
    emit = nfe.get('emitente') or {}
    cnpj_emitente = _so_digitos(emit.get('cnpj'))[:20] or None
    # loja REAL da venda — NUNCA a matriz (emitente fiscal != loja de venda). Sem
    # departamento no create (vem do enriquecimento de pedido depois); resolve por
    # CNPJ NAO-matriz, senao None (loja a definir -> de-para/definir_loja_venda).
    loja_venda = _resolver_loja_real_venda(cnpj_emitente, None)

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
            loja_emitente_id=loja_venda.id if loja_venda else None,
        )
        inf_contribuinte_nf = nfe.get('inf_contribuinte') or ''
        observacoes_nf = nfe.get('observacoes') or ''

        # Se nao tem itens ainda, tenta criar agora.
        criou_itens = False
        atualizou_motos = False
        corrigiu_chassis = 0
        if not existente.itens:
            antes = {it.id for it in existente.itens}
            _criar_itens_da_api(
                venda=existente,
                itens_api=itens_raw,
                loja_emitente_id=loja_venda.id if loja_venda else None,
                data_venda=data_emissao,
                operador=operador,
                inf_contribuinte_nf=inf_contribuinte_nf,
                observacoes_nf=observacoes_nf,
                pendencias_chassi_llm=pendencias_chassi_llm,
            )
            db.session.flush()
            criou_itens = any(it.id not in antes for it in existente.itens)
        else:
            # Itens ja existem: tenta upsert das motos via re-extracao
            # da API (cor, ano, motor) e corrige bug chassi==motor.
            atualizou_motos, corrigiu_chassis = _atualizar_motos_dos_itens_existentes(
                venda=existente,
                itens_api=itens_raw,
                inf_contribuinte_nf=inf_contribuinte_nf,
                observacoes_nf=observacoes_nf,
                operador=operador,
                loja_emitente_id=loja_venda.id if loja_venda else None,
            )

        # Sincroniza HoraTagPlusNfeEmissao (botao 'Baixar DANFE' funcionar).
        emissao_existia = HoraTagPlusNfeEmissao.query.filter_by(venda_id=existente.id).first() is not None
        _upsert_emissao_nfe(
            venda=existente, nfe_id_tagplus=nfe_id_tagplus,
            chave_44=chave, numero_nfe=numero_nf, serie_nfe=serie_nf,
            data_emissao=data_emissao, status_tagplus='A', conta=api.conta,
        )
        criou_emissao = not emissao_existia

        if (
            status_upsert or criou_itens or criou_emissao
            or atualizou_motos or corrigiu_chassis
        ):
            venda_audit.registrar_auditoria(
                venda_id=existente.id, usuario=operador or '',
                acao='EDITOU_HEADER',
                detalhe=(
                    f'Backfill TagPlus refresh — '
                    f'campos atualizados={status_upsert}, '
                    f'itens_criados={criou_itens}, '
                    f'emissao_criada={criou_emissao}, '
                    f'motos_complementadas={atualizou_motos}, '
                    f'chassis_corrigidos={corrigiu_chassis}'
                ),
            )
            db.session.commit()
            return existente, 'atualizado'
        db.session.commit()
        return existente, 'inalterado'

    # ------ Cria HoraVenda (nova) ------
    venda = HoraVenda(
        loja_id=loja_venda.id if loja_venda else None,
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

    if loja_venda is None:
        _registrar_divergencia(
            venda_id=venda.id, tipo='CNPJ_DESCONHECIDO',
            detalhe=(
                f'Loja de venda nao definida: emitente {cnpj_emitente!r} e a matriz '
                f'(ou CNPJ nao cadastrado). Defina a loja fisica (de-para de '
                f'departamento ou tela de detalhe).'
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
        loja_emitente_id=loja_venda.id if loja_venda else None,
        data_venda=data_emissao,
        operador=operador,
        inf_contribuinte_nf=inf_contribuinte_nf,
        observacoes_nf=observacoes_nf,
        pendencias_chassi_llm=pendencias_chassi_llm,
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


def _resolver_conflito_motor_unique(
    motor_norm: str, chassi_destino: str,
) -> bool:
    """Garante que `motor_norm` esteja livre antes de gravar em `chassi_destino`.

    `hora_moto.numero_motor` tem UNIQUE (`hora_moto_numero_motor_key`). Se outra
    `HoraMoto` X ja ocupa esse motor, qualquer UPDATE em `chassi_destino`
    levanta `UniqueViolation`. Esta funcao trata o conflito:

      - Caso A: X eh moto-bug do regex historico (`numero_chassi == numero_motor`).
        Consolidamos X em `chassi_destino`:
          1) re-aponta `HoraVendaItem.numero_chassi=X` -> chassi_destino
          2) re-aponta `HoraMotoEvento.numero_chassi=X` -> chassi_destino
          3) deleta a `HoraMoto` orfa X
          4) flush (libera UNIQUE no banco)
        Retorna True (caller pode setar `chassi_destino.numero_motor=motor_norm`).

      - Caso B: X eh moto valida (chassi != motor). Motor pertence legitimamente
        a outra moto fisica — NAO mexer. Loga warning e retorna False.

      - Sem conflito: retorna True direto.
    """
    outra = HoraMoto.query.filter(
        HoraMoto.numero_motor == motor_norm,
        HoraMoto.numero_chassi != chassi_destino,
    ).first()

    if outra is None:
        return True

    if outra.numero_chassi == outra.numero_motor:
        chassi_bug = outra.numero_chassi
        logger.info(
            'Conflito UNIQUE motor=%s: moto-bug %s sera consolidada em %s',
            motor_norm, chassi_bug, chassi_destino,
        )
        # Re-aponta refs para o chassi correto antes de deletar a moto-bug
        # (FK em hora_venda_item e hora_moto_evento exige a moto destino existir).
        HoraVendaItem.query.filter_by(numero_chassi=chassi_bug).update(
            {'numero_chassi': chassi_destino}, synchronize_session=False,
        )
        HoraMotoEvento.query.filter_by(numero_chassi=chassi_bug).update(
            {'numero_chassi': chassi_destino}, synchronize_session=False,
        )
        db.session.delete(outra)
        # Flush IMEDIATO — sem ele, o autoflush pode emitir o UPDATE em
        # chassi_destino antes do DELETE da moto-bug, perpetuando o conflito.
        db.session.flush()
        return True

    logger.warning(
        'Motor %s pertence a moto valida %s (chassi != motor); '
        'pulando UPDATE em %s para preservar integridade.',
        motor_norm, outra.numero_chassi, chassi_destino,
    )
    return False


def _atualizar_moto_complementar(
    moto: HoraMoto,
    cor_nova: Optional[str],
    ano_modelo_novo: Optional[int],
    motor_novo: Optional[str],
) -> bool:
    """UPSERT de campos complementares de `HoraMoto` durante backfill TagPlus.

    Excecao controlada ao invariante 3 (insert-once): so atualiza campos que
    estao em estado sentinela (NULL, 'NAO_INFORMADA' ou motor==chassi -
    sinal do bug regex que gravava motor como chassi). NUNCA sobrescreve
    valores ja preenchidos com dados reais (preserva edicoes de operador
    e mantem rastreabilidade da identidade da moto).

    PROTECAO DE CHASSI (2026-05-05): se chassi esta vinculado a HoraPedidoItem
    ou HoraNfEntradaItem, considera-se fonte de verdade. NAO atualiza nada -
    apenas registra warning. Vide chassi_protecao_service.chassi_protegido().

    Para motor: alem da checagem de campo vazio/sentinela, valida UNIQUE
    via `_resolver_conflito_motor_unique` (consolida moto-bug ou pula).

    Returns:
        True se algum campo foi alterado, False caso contrario.
    """
    # Defesa contra parser quebrar ciclo de chassi vinculado a compra.
    from app.hora.services.chassi_protecao_service import chassi_protegido
    if chassi_protegido(moto.numero_chassi):
        cor_norm = (cor_nova or '').strip().upper() or None
        motor_norm = (motor_novo or '').strip().upper() or None
        if (
            (cor_norm and cor_norm != moto.cor and moto.cor not in (None, '', 'NAO_INFORMADA'))
            or (motor_norm and motor_norm != moto.numero_motor
                and moto.numero_motor not in (None, '', moto.numero_chassi))
        ):
            current_app.logger.warning(
                'TagPlus backfill: chassi PROTEGIDO %s - parser sugeriu '
                'cor=%r/motor=%r mas dados atuais cor=%r/motor=%r preservados '
                '(fonte de verdade: pedido/NF entrada).',
                moto.numero_chassi, cor_norm, motor_norm,
                moto.cor, moto.numero_motor,
            )
        return False

    alterou = False

    cor_norm = (cor_nova or '').strip().upper() or None
    if (
        cor_norm
        and cor_norm != 'NAO_INFORMADA'
        and (moto.cor in (None, '', 'NAO_INFORMADA'))
    ):
        moto.cor = cor_norm
        alterou = True

    if ano_modelo_novo and moto.ano_modelo is None:
        moto.ano_modelo = ano_modelo_novo
        alterou = True

    motor_norm = (motor_novo or '').strip().upper() or None
    if motor_norm and (
        moto.numero_motor is None
        or moto.numero_motor == ''
        or moto.numero_motor == moto.numero_chassi  # sinal do bug regex
    ) and motor_norm != moto.numero_chassi:
        # Resolve conflito UNIQUE antes de atribuir (libera moto-bug ou skip).
        if _resolver_conflito_motor_unique(motor_norm, moto.numero_chassi):
            moto.numero_motor = motor_norm
            alterou = True

    return alterou


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
      - modalidade_frete: vazio se = '0' (default atual desde 2026-05-11)
        ou = '9' (default legado, mantido para compat com vendas antigas)
        E API retorna outro valor valido ('0' CIF ou '1' FOB).

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

    # Modalidade de frete: '0' (default atual) ou '9' (default legado pre-
    # 2026-05-11) sao tratados como "vazio". Se API retornou valor valido
    # diferente, atualiza. Vendas antigas com '9' ainda sao corrigidas neste
    # fluxo. Vendas novas com '0' (default silencioso) tambem.
    modalidade_atual = venda.modalidade_frete or '0'
    if (
        modalidade_atual in ('0', '9')
        and modalidade_frete
        and modalidade_frete in ('0', '1')
        and modalidade_frete != modalidade_atual
    ):
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
    pendencias_chassi_llm: Optional[list] = None,
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
    texto_nfe_mae = f'{inf_contribuinte_nf}\n{observacoes_nf}'
    nfe_chassis = _extrair_chassis_multiplos(texto_nfe_mae)
    nfe_chassis_iter = iter(nfe_chassis)

    # Cor e ano modelo da NFe-mae (compartilhados entre os itens; quando
    # uma NF tem multiplas motos com cores diferentes, o item.detalhes
    # ainda pode sobrescrever no proprio item).
    cor_nfe, ano_nfe = _extrair_cor_ano(texto_nfe_mae)

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
            div = _registrar_divergencia(
                venda_id=venda.id, tipo='CHASSI_NAO_CADASTRADO',
                detalhe=(
                    f'Item produto={codigo_produto or descricao!r} qtd={qtd} '
                    f'sem chassi extraivel. Fontes consultadas: '
                    f'{" | ".join(fontes_tentadas)}.'
                )[:1000],
                valor_conferido=(detalhes or descricao_raw)[:255],
            )
            # Coleta pendencia para o batch LLM final (1 chamada por chunk
            # no final do job — evita N requests em runs com 500+ NFs).
            if pendencias_chassi_llm is not None:
                texto_consolidado = '\n'.join(filter(None, [
                    detalhes, descricao_raw, complemento, numero_serie,
                    inf_contribuinte_nf, observacoes_nf,
                ]))[:1500]
                if texto_consolidado.strip():
                    pendencias_chassi_llm.append({
                        'venda_id': venda.id,
                        'divergencia_id': getattr(div, 'id', None),
                        'detalhes': texto_consolidado,
                        'codigo_produto': codigo_produto,
                    })
            continue

        modelo_id_resolvido = _resolver_modelo_id(codigo_produto)

        # Cor/ano podem vir do proprio detalhes do item (sobrescreve NFe-mae).
        cor_item, ano_item = _extrair_cor_ano(detalhes or descricao_raw or complemento)
        cor_final = cor_item or cor_nfe
        ano_final = ano_item or ano_nfe

        for chassi, motor in chassis_motores:
            chassi_norm = (chassi or '').strip().upper()
            if not chassi_norm:
                continue

            cor_para_moto = cor_final or 'NAO_INFORMADA'

            moto_existia = HoraMoto.query.get(chassi_norm) is not None

            if modelo_id_resolvido and not moto_existia:
                moto = HoraMoto(
                    numero_chassi=chassi_norm,
                    modelo_id=modelo_id_resolvido,
                    cor=cor_para_moto,
                    numero_motor=motor,
                    ano_modelo=ano_final,
                    criado_por=operador,
                )
                db.session.add(moto)
                db.session.flush()
            else:
                # Migration hora_29: get_or_create_moto pode levantar
                # ModeloPendenteError quando nome nao bate em alias.
                # Capturamos, registramos divergencia MODELO_PENDENTE e
                # SKIPAMOS o item — operador resolve via tela /hora/modelos/pendencias.
                from app.hora.services.modelo_resolver_service import ModeloPendenteError
                from app.hora.models import PENDENTE_ORIGEM_TAGPLUS_BACKFILL
                try:
                    moto = get_or_create_moto(
                        numero_chassi=chassi_norm,
                        modelo_nome=descricao or codigo_produto or 'MODELO_DESCONHECIDO',
                        cor=cor_para_moto,
                        numero_motor=motor,
                        ano_modelo=ano_final,
                        criado_por=operador,
                        origem_pendencia=PENDENTE_ORIGEM_TAGPLUS_BACKFILL,
                        origem_id=venda.id,
                        tagplus_codigo=codigo_produto,
                    )
                except ModeloPendenteError as exc:
                    _registrar_divergencia(
                        venda_id=venda.id, tipo='MODELO_PENDENTE',
                        numero_chassi=chassi_norm,
                        detalhe=(
                            f'Modelo {(descricao or codigo_produto)!r} nao reconhecido. '
                            f'Pendencia #{exc.pendencia.id} aguardando decisao em '
                            f'/hora/modelos/pendencias. Quando resolvida, HoraMoto '
                            f'sera criada retroativamente.'
                        ),
                        valor_conferido=(descricao or codigo_produto or '')[:255],
                    )
                    logger.info(
                        'TagPlus item skip (modelo pendente): chassi=%s pendencia=%s',
                        chassi_norm, exc.pendencia.id,
                    )
                    continue
                # UPSERT: moto ja existia — atualiza campos que estao em
                # estado sentinela ('NAO_INFORMADA' / NULL / motor==chassi).
                if moto_existia:
                    if _atualizar_moto_complementar(
                        moto, cor_nova=cor_final,
                        ano_modelo_novo=ano_final,
                        motor_novo=motor,
                    ):
                        logger.info(
                            'UPSERT moto chassi=%s — cor/ano/motor complementados '
                            'a partir da API TagPlus.', chassi_norm,
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

            preco_ref, desconto, desconto_pct, tabela_id, divergencia_tipo = _resolver_preco_tabela(
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
                desconto_percentual=desconto_pct,
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


def _atualizar_motos_dos_itens_existentes(
    venda: HoraVenda,
    itens_api: list,
    inf_contribuinte_nf: str,
    observacoes_nf: str,
    operador: Optional[str],
    loja_emitente_id: Optional[int],
) -> tuple[bool, int]:
    """UPSERT das motos vinculadas a itens ja persistidos.

    Para cada `HoraVendaItem` da venda, re-extrai (chassi, motor, cor, ano)
    da API TagPlus (campos do item + inf_contribuinte da NF-mae) e:

      - Se moto.cor='NAO_INFORMADA' e API tem cor real -> atualiza.
      - Se moto.ano_modelo IS NULL e API tem ano -> atualiza.
      - Se moto.numero_motor IS NULL ou == numero_chassi (sinal do bug regex)
        e API tem motor diferente -> atualiza.
      - Se moto.numero_chassi == numero_motor extraido E novo extracao tem
        chassi diferente -> dispara `_corrigir_chassi_motor_invertido`
        (renomeia chassi via cascade em FKs e cria moto com chassi correto).

    Returns:
        (alterou_motos: bool, qtd_chassis_corrigidos: int)
    """
    alterou_qq = False
    n_corrigidos = 0
    if not venda.itens or not itens_api:
        return (False, 0)

    texto_nfe_mae = f'{inf_contribuinte_nf}\n{observacoes_nf}'
    cor_nfe, ano_nfe = _extrair_cor_ano(texto_nfe_mae)
    nfe_chassis_pares = _extrair_chassis_multiplos(texto_nfe_mae)

    # Empacota itens da API com sua melhor extracao (chassi, motor, cor, ano).
    api_extracoes: list[dict] = []
    for it in itens_api:
        if not isinstance(it, dict):
            continue
        detalhes = (it.get('detalhes') or '').strip()
        descricao = (it.get('descricao') or '').strip()
        complemento = (it.get('complemento_descricao') or '').strip()
        numero_serie = (it.get('numero_serie') or '').strip()

        chassis_motores: list[tuple[Optional[str], Optional[str]]] = []
        for fonte in (detalhes, descricao, complemento, numero_serie):
            chassis_motores = _extrair_chassis_multiplos(fonte)
            if chassis_motores:
                break

        cor_item, ano_item = _extrair_cor_ano(detalhes or descricao or complemento)
        api_extracoes.append({
            'chassis_motores': chassis_motores,
            'cor': cor_item or cor_nfe,
            'ano': ano_item or ano_nfe,
            'detalhes': detalhes,
        })

    # Fallback: se algum item nao teve chassi proprio, usa fila da NF-mae.
    pares_fila = list(nfe_chassis_pares)
    pares_fila_iter = iter(pares_fila)
    for ext in api_extracoes:
        if not ext['chassis_motores']:
            try:
                ext['chassis_motores'] = [next(pares_fila_iter)]
            except StopIteration:
                pass

    # Casa cada item da venda com a extracao correspondente da API.
    # Usamos casamento posicional (mesma ordem do TagPlus).
    venda_itens_ord = list(venda.itens)
    for idx, item in enumerate(venda_itens_ord):
        if idx >= len(api_extracoes):
            break
        ext = api_extracoes[idx]
        pares = ext['chassis_motores']
        if not pares:
            continue
        chassi_api, motor_api = pares[0]
        chassi_api_norm = (chassi_api or '').strip().upper() or None
        motor_api_norm = (motor_api or '').strip().upper() or None
        cor_api = ext['cor']
        ano_api = ext['ano']

        moto = HoraMoto.query.get(item.numero_chassi)
        if moto is None:
            continue

        # Caso 1: bug chassi==motor — chassi gravado na verdade e o motor.
        if (
            chassi_api_norm
            and motor_api_norm
            and item.numero_chassi == motor_api_norm
            and chassi_api_norm != motor_api_norm
        ):
            try:
                _corrigir_chassi_motor_invertido(
                    venda_id=venda.id,
                    item=item,
                    chassi_errado=item.numero_chassi,
                    chassi_correto=chassi_api_norm,
                    motor_correto=motor_api_norm,
                    cor=cor_api,
                    ano_modelo=ano_api,
                    operador=operador,
                    loja_id=loja_emitente_id,
                )
                n_corrigidos += 1
                alterou_qq = True
                logger.info(
                    'Chassi corrigido na venda #%s item #%s: %s -> %s',
                    venda.id, item.id, motor_api_norm, chassi_api_norm,
                )
                continue
            except Exception as e:
                logger.exception(
                    'Falha ao corrigir chassi invertido na venda #%s item #%s: %s',
                    venda.id, item.id, e,
                )
                continue

        # Caso 2: chassi correto, mas cor/ano/motor podem estar incompletos.
        if _atualizar_moto_complementar(
            moto, cor_nova=cor_api, ano_modelo_novo=ano_api,
            motor_novo=motor_api_norm,
        ):
            alterou_qq = True

    return (alterou_qq, n_corrigidos)


def _corrigir_chassi_motor_invertido(
    venda_id: int,
    item: HoraVendaItem,
    chassi_errado: str,
    chassi_correto: str,
    motor_correto: str,
    cor: Optional[str],
    ano_modelo: Optional[int],
    operador: Optional[str],
    loja_id: Optional[int],
) -> None:
    """Corrige o bug historico onde regex gravou motor como chassi.

    Estado de entrada (bug):
      - HoraMoto(numero_chassi=motor, numero_motor=motor)  # ambos = motor
      - HoraVendaItem.numero_chassi = motor
      - HoraMotoEvento.numero_chassi = motor

    Acao:
      1. Cria HoraMoto(numero_chassi=chassi_correto) com cor/ano/motor reais
         (se ainda nao existe).
      2. Re-aponta HoraVendaItem.numero_chassi -> chassi_correto.
      3. Re-aponta os HoraMotoEvento desta venda (matched por origem_id =
         item.id) -> chassi_correto.
      4. Se nenhum outro registro aponta para o chassi_errado, remove a
         HoraMoto orfa (chassi_errado).

    Idempotente: se ja foi corrigido, nao faz nada.
    """
    chassi_errado_norm = chassi_errado.strip().upper()
    chassi_correto_norm = chassi_correto.strip().upper()
    motor_norm = motor_correto.strip().upper() or None
    cor_norm = (cor or 'NAO_INFORMADA').strip().upper()

    if chassi_errado_norm == chassi_correto_norm:
        return  # ja corrigido, nada a fazer

    moto_errada = HoraMoto.query.get(chassi_errado_norm)
    if moto_errada is None:
        # Nao deveria acontecer (caller checou), mas defesa em profundidade.
        return

    # PRE-PASSO: libera o motor da moto-bug ANTES de criar/atualizar a correta.
    # Sem isso, o INSERT/UPDATE da moto correta com `numero_motor=motor_norm`
    # bate em UniqueViolation porque a moto-bug ainda ocupa esse motor
    # (estado: chassi=motor=motor_norm).
    if motor_norm and moto_errada.numero_motor == motor_norm:
        moto_errada.numero_motor = None
        db.session.flush()

    # 1. Cria moto correta se nao existe.
    moto_correta = HoraMoto.query.get(chassi_correto_norm)
    if moto_correta is None:
        moto_correta = HoraMoto(
            numero_chassi=chassi_correto_norm,
            modelo_id=moto_errada.modelo_id,
            cor=cor_norm,
            numero_motor=motor_norm,
            ano_modelo=ano_modelo,
            criado_por=(operador or 'backfill_corrige_chassi'),
        )
        db.session.add(moto_correta)
        db.session.flush()
    else:
        # Se ja existe, garante que cor/ano/motor estejam preenchidos.
        _atualizar_moto_complementar(
            moto_correta, cor_nova=cor, ano_modelo_novo=ano_modelo,
            motor_novo=motor_norm,
        )

    # 2. Re-aponta item.
    item.numero_chassi = chassi_correto_norm
    db.session.flush()

    # 3. Re-aponta eventos do chassi_errado vinculados a este item.
    eventos = HoraMotoEvento.query.filter_by(
        numero_chassi=chassi_errado_norm,
        origem_tabela='hora_venda_item',
        origem_id=item.id,
    ).all()
    for ev in eventos:
        ev.numero_chassi = chassi_correto_norm
    db.session.flush()

    # 4. Se nenhum outro item ou evento aponta para chassi_errado, remove orfao.
    sobra_itens = HoraVendaItem.query.filter_by(
        numero_chassi=chassi_errado_norm,
    ).count()
    sobra_eventos = HoraMotoEvento.query.filter_by(
        numero_chassi=chassi_errado_norm,
    ).count()
    if sobra_itens == 0 and sobra_eventos == 0:
        db.session.delete(moto_errada)
        db.session.flush()
        logger.info(
            'HoraMoto orfa removida: chassi_errado=%s (sem refs apos correcao, venda=%s)',
            chassi_errado_norm, venda_id,
        )

    # Registra evento auditavel da correcao na linha do tempo do chassi correto.
    try:
        registrar_evento(
            numero_chassi=chassi_correto_norm,
            tipo='VENDIDA',
            origem_tabela='hora_venda_item',
            origem_id=item.id,
            loja_id=loja_id,
            operador=(operador or 'backfill_corrige_chassi'),
            detalhe=(
                f'Correcao chassi invertido (motor): {chassi_errado_norm}'
                f' -> {chassi_correto_norm}'
            ),
        ) if not eventos else None  # se ja re-apontamos, nao duplica
    except ValueError:
        # tipo 'VENDIDA' e valido — fallback so por seguranca.
        pass


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

def _importar_com_retry_db(
    api: ApiClient,
    nfe_id: int,
    operador: Optional[str],
    max_tentativas: int = 3,
    pendencias_chassi_llm: Optional[list] = None,
) -> tuple:
    """Wrapper que recupera de SSL/connection drop no Postgres.

    Em runs longos no Render, conexoes SSL podem cair (timeout, deploy do
    DB, network glitch). SQLAlchemy lanca `OperationalError` /
    `DBAPIError` com `connection_invalidated=True`. Resposta correta:
    rollback, dispose do pool inteiro (forca reabrir TCP+SSL), retry.

    Aplica backoff linear: 5s, 15s, 30s.
    """
    import time
    from sqlalchemy.exc import DBAPIError, OperationalError

    delays = [5, 15, 30]
    ultima_excecao: Optional[Exception] = None

    for tentativa in range(max_tentativas):
        try:
            return importar_nfe_da_api(
                api, nfe_id, operador=operador,
                pendencias_chassi_llm=pendencias_chassi_llm,
            )
        except (OperationalError, DBAPIError) as exc:
            ultima_excecao = exc
            connection_invalidated = getattr(exc, 'connection_invalidated', False)
            logger.warning(
                'DB error em NFe %s (tentativa %d/%d, invalidated=%s): %s',
                nfe_id, tentativa + 1, max_tentativas,
                connection_invalidated, exc,
            )
            try:
                db.session.rollback()
            except Exception:
                pass
            try:
                db.session.close()
                db.engine.dispose()
            except Exception:
                logger.exception(
                    'Falha ao dispose do pool em recovery NFe %s', nfe_id,
                )
            if tentativa + 1 < max_tentativas:
                delay = delays[min(tentativa, len(delays) - 1)]
                logger.info(
                    'Aguardando %ds antes de retentar NFe %s', delay, nfe_id,
                )
                time.sleep(delay)

    # Esgotou tentativas — propaga.
    assert ultima_excecao is not None
    raise ultima_excecao


def executar_backfill(
    since: Optional[date] = None,
    until: Optional[date] = None,
    operador: Optional[str] = None,
    limite: Optional[int] = None,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> dict:
    """Lista NFes da API TagPlus no intervalo + importa cada uma.

    Args:
        since/until: filtros de data_emissao (inclusivo).
        operador: nome do usuario logado para auditoria.
        limite: maximo de NFes a importar (None = sem limite). Util para
            testes ou primeiro lote.
        progress_callback: callable opcional invocado a cada NFe processada
            com snapshot dos contadores parciais. Use para atualizar UI ou
            persistir progresso (ex.: HoraTagPlusBackfillJob).
            Forma do snapshot:
              {
                'processadas': int,        # NFs ja iteradas
                'criado', 'atualizado', 'inalterado', 'cancelado',
                'pulada_cancelada', 'pulada_invalida',
                'duplicado', 'erro', 'divergencias': int,
                'ultima_nfe_id': int|None,
                'ultima_status': str|None,  # 'criado'/'atualizado'/...
                'ultimo_erro': str|None,
              }
            O callback eh executado fora da sessao de import — pode commitar
            em outra sessao com seguranca.

    Returns:
        dict com contadores e lista detalhada de cada NFe processada.
    """
    conta = HoraTagPlusConta.ativa()
    api = ApiClient(conta)

    resultados = []
    # Lista enxuta de erros (subset de `resultados` filtrado) para exibicao
    # incremental na tela de detalhe do job. Persistida no `relatorio['erros']`
    # via `_gravar_progresso` — ver backfill_worker._gravar_progresso.
    # Cap de seguranca: 500 entradas. Em jobs com muitos erros, mantem so
    # os 500 primeiros + sinaliza truncamento via `n_err`.
    MAX_ERROS_PERSISTIDOS = 500
    erros_acumulados: list[dict] = []

    # Coletor de pendencias de chassi (para batch LLM no fim do job).
    # Cada entrada: {venda_id, divergencia_id, detalhes, codigo_produto}.
    # Backfill inicial (volume alto, nao-recorrente) -> 1 chamada Haiku
    # batch por chunk de 30 NFs e atualiza divergencias com sugestao LLM.
    pendencias_chassi_llm: list[dict] = []

    n_criado = n_atualizado = n_inalterado = 0
    n_cancelado = n_pulada_cancelada = n_pulada_invalida = 0
    n_dup = n_err = n_div = 0

    def _emit_progress(ultima_nfe: Optional[int], ultima_status: Optional[str],
                       ultimo_erro: Optional[str]) -> None:
        if not progress_callback:
            return
        try:
            progress_callback({
                'processadas': len(resultados),
                'criado': n_criado,
                'atualizado': n_atualizado,
                'inalterado': n_inalterado,
                'cancelado': n_cancelado,
                'pulada_cancelada': n_pulada_cancelada,
                'pulada_invalida': n_pulada_invalida,
                'duplicado': n_dup,
                'erro': n_err,
                'divergencias': n_div,
                'ultima_nfe_id': ultima_nfe,
                'ultima_status': ultima_status,
                'ultimo_erro': ultimo_erro,
                # Lista enxuta de NFs com erro — visivel na tela de detalhe.
                # Nao trava o backfill: e apenas um snapshot pra UI.
                'erros': list(erros_acumulados),
            })
        except Exception:  # pragma: no cover
            logger.exception('progress_callback falhou — ignorado')

    def _iterador_resiliente():
        """Itera NFes da API com defesa contra DetachedInstanceError.

        A paginacao real do TagPlus eh 50 NFs por request. Em jobs longos no
        worker, a `conta` carregada uma vez no inicio sobrevive a centenas
        de commits e pode ficar DETACHED — quando o iterador pede a proxima
        pagina, `oauth.refresh_if_needed -> conta.token` (lazy) explode
        DetachedInstanceError. Esse erro acontece DENTRO do generator, fora
        do try/except per-NF, e mataria o job.

        Aqui re-emitimos a paginacao reattachando a conta via OAuthClient e
        recriando o iterador. Sintoma classico que isso resolve: job
        congelado em `processadas=50, total_listadas=N>50, status=ERRO,
        ultimo_erro=DetachedInstanceError`.
        """
        from sqlalchemy.orm.exc import DetachedInstanceError

        nfes_ja_vistas: set[int] = set()
        while True:
            try:
                api.oauth._ensure_conta_attached()  # noqa: SLF001
                for nfe_resumo in listar_nfes_emitidas(api, since=since, until=until):
                    nfe_id_local = nfe_resumo.get('id')
                    if nfe_id_local in nfes_ja_vistas:
                        continue  # pula NFs ja entregues antes do retry
                    if nfe_id_local is not None:
                        nfes_ja_vistas.add(nfe_id_local)
                    yield nfe_resumo
                return  # iteracao normal terminou
            except DetachedInstanceError as exc:
                logger.warning(
                    'DetachedInstanceError na paginacao (apos %d NFs); '
                    'reattachando conta e re-iterando. exc=%s',
                    len(nfes_ja_vistas), exc,
                )
                try:
                    db.session.rollback()
                except Exception:
                    pass
                # Re-attach explicitamente; o set `nfes_ja_vistas` evita
                # reprocessar NFs ja entregues nesta paginacao.
                api.oauth._ensure_conta_attached()  # noqa: SLF001

    iterador = _iterador_resiliente()
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
            _emit_progress(None, 'erro', entry['mensagem'])
            continue

        ultimo_erro_str: Optional[str] = None
        try:
            venda, status = _importar_com_retry_db(
                api, nfe_id, operador=operador,
                pendencias_chassi_llm=pendencias_chassi_llm,
            )

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
            ultimo_erro_str = entry['mensagem']
            db.session.rollback()
        except Exception as exc:  # pragma: no cover
            entry['status'] = 'erro'
            entry['mensagem'] = f'Erro inesperado: {exc}'
            n_err += 1
            ultimo_erro_str = entry['mensagem']
            try:
                db.session.rollback()
            except Exception:
                pass
            logger.exception('Backfill: falha NFe %s', nfe_id)
        resultados.append(entry)
        # Acumula entrada simplificada para exibicao na tela quando for erro.
        # Limitado a MAX_ERROS_PERSISTIDOS para nao inflar JSONB do relatorio.
        if entry.get('status') == 'erro' and len(erros_acumulados) < MAX_ERROS_PERSISTIDOS:
            erros_acumulados.append({
                'tagplus_nfe_id': entry.get('tagplus_nfe_id'),
                'numero_nf': entry.get('numero_nf'),
                'chave': entry.get('chave'),
                'status_tagplus': entry.get('status_tagplus'),
                'mensagem': entry.get('mensagem'),
            })
        _emit_progress(nfe_id, entry['status'], ultimo_erro_str)

        # Higiene de sessao: a cada 25 NFs faz close() para liberar a
        # conexao SSL ao pool. Evita "idle in transaction" do Render.
        if (i + 1) % 25 == 0:
            try:
                db.session.close()
            except Exception:
                logger.exception('Falha em session.close() periodico')

    # ----------------------------------------------------------------
    # Pos-processamento: batch LLM para resolver pendencias de chassi.
    # ----------------------------------------------------------------
    n_chassi_sugerido_llm = _resolver_pendencias_chassi_em_batch(
        pendencias_chassi_llm,
    )

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
        # Pos-processamento LLM:
        'chassi_pendencias': len(pendencias_chassi_llm),
        'chassi_sugerido_llm': n_chassi_sugerido_llm,
        # Lista detalhada de cada NF (sucesso e erro). Este campo e REMOVIDO
        # pelo backfill_worker._marcar_fim antes de persistir no DB —
        # significa que so e usado quando executar_backfill roda em modo
        # sincrono (dev/testes). A lista persistida na tela vem de `erros`
        # (apenas erros, cap 500).
        'resultados': resultados,
        'erros': erros_acumulados,
    }


def _resolver_pendencias_chassi_em_batch(
    pendencias: list[dict],
    chunk_size: int = 30,
) -> int:
    """Apos o loop de NFs, resolve em BATCH as pendencias de chassi.

    Para cada chunk de ate `chunk_size` pendencias:
      1. Monta payload [{nfe_id=divergencia_id, detalhes}].
      2. Chama Haiku UMA VEZ com todos via
         `parser_append_service.extrair_lote_via_llm_com_append`.
      3. Para cada resposta, atualiza o detalhe da divergencia com a
         sugestao LLM (chassi/motor) — operador revisa na tela da venda
         antes de criar o `HoraVendaItem` definitivo.

    Returns:
        Quantidade de divergencias enriquecidas com sugestao LLM.
    """
    if not pendencias:
        return 0

    try:
        from app.hora.services.parser_append_service import (
            extrair_lote_via_llm_com_append,
        )
    except Exception:  # pragma: no cover
        logger.exception(
            'Batch LLM indisponivel — pendencias chassi nao resolvidas'
        )
        return 0

    from app.hora.models.venda import HoraVendaDivergencia
    from app.utils.timezone import agora_utc_naive

    n_atualizado = 0
    chunks = [
        pendencias[i:i + chunk_size]
        for i in range(0, len(pendencias), chunk_size)
    ]
    logger.info(
        'Batch LLM chassi: %d pendencias em %d chunks de ate %d.',
        len(pendencias), len(chunks), chunk_size,
    )

    for idx, chunk in enumerate(chunks, start=1):
        # Usa divergencia_id como chave do batch (univoca, persistida).
        casos = [
            {
                'nfe_id': p['divergencia_id'],
                'detalhes': p['detalhes'],
            }
            for p in chunk if p.get('divergencia_id')
        ]
        if not casos:
            continue
        logger.info(
            'Batch LLM chassi: chunk %d/%d (%d casos)',
            idx, len(chunks), len(casos),
        )
        resposta = extrair_lote_via_llm_com_append(casos)
        if resposta is None:
            logger.warning(
                'Batch LLM chassi: chunk %d falhou (LLM indisponivel ou '
                'resposta invalida) — sem sugestao para %d divergencias',
                idx, len(casos),
            )
            continue

        # Resposta -> map por divergencia_id.
        mapa = {item['nfe_id']: item for item in resposta if item.get('nfe_id')}

        # Defensiva: se LLM retorna alucinando IDs (numero certo de items
        # mas nfe_id que nao bate com nenhum divergencia_id enviado),
        # `mapa.get(div_id)` retorna None silenciosamente. Logamos um
        # warning para o operador investigar (ver code review R3 2026-04-30).
        n_matched = sum(
            1 for p in chunk
            if p.get('divergencia_id') and mapa.get(p['divergencia_id'])
        )
        if n_matched == 0 and casos:
            logger.warning(
                'Batch LLM chassi: chunk %d/%d — zero divergencias enriquecidas '
                '(LLM retornou %d items, nenhum nfe_id bateu com divergencia_id '
                'enviado=%s). Possivel alucinacao de IDs pelo LLM.',
                idx, len(chunks), len(resposta),
                [c.get('nfe_id') for c in casos[:5]],
            )

        for p in chunk:
            div_id = p.get('divergencia_id')
            if not div_id:
                continue
            sug = mapa.get(div_id)
            if not sug:
                continue
            chassi_sug = (sug.get('chassi') or '').strip().upper() or None
            motor_sug = (sug.get('motor') or '').strip().upper() or None
            if not chassi_sug and not motor_sug:
                continue

            div = db.session.get(HoraVendaDivergencia, div_id)
            if div is None:
                continue
            sufixo = (
                f"\n\n[LLM SUGESTAO — {agora_utc_naive().strftime('%d/%m %H:%M')}]\n"
                f"chassi={chassi_sug or '?'}  motor={motor_sug or '?'}\n"
                f"(revisar manualmente antes de criar o item — extracao "
                f"feita por LLM apos regex falhar)"
            )
            div.detalhe = ((div.detalhe or '') + sufixo)[:1000]
            n_atualizado += 1

        try:
            db.session.commit()
        except Exception:
            logger.exception(
                'Batch LLM chassi: commit chunk %d falhou — rollback', idx,
            )
            try:
                db.session.rollback()
            except Exception:
                pass

    logger.info(
        'Batch LLM chassi: %d divergencias enriquecidas com sugestao.',
        n_atualizado,
    )
    return n_atualizado


# --------------------------------------------------------------------------
# Backfill sincrono de UMA UNICA NFe (modo teste)
# --------------------------------------------------------------------------

def executar_backfill_unica_nfe(
    nfe_id_tagplus: int,
    operador: Optional[str] = None,
) -> dict:
    """Importa UMA NFe especifica do TagPlus, sincronamente, sem RQ.

    Util para testar o pipeline de backfill com baixa latencia (sem
    enfileirar job e aguardar worker), e para validar fixes em NFes
    especificas que falharam em backfill em lote.

    Args:
        nfe_id_tagplus: ID da NFe no TagPlus (campo `id` em /nfes/{id}).
        operador: nome/email do usuario logado (para auditoria).

    Returns:
        dict com:
            - status: 'criado' | 'atualizado' | 'inalterado' | 'cancelado' |
                      'pulada_cancelada' | 'pulada_status_invalido' |
                      'duplicado' | 'erro'
            - venda_id: int | None
            - tagplus_nfe_id: int
            - numero_nf: str | None
            - chave: str | None
            - mensagem: str (descricao humana do resultado)
            - qtd_chassis: int (apenas se venda criada/atualizada)
            - qtd_divergencias: int (apenas se venda criada/atualizada)

    Levanta:
        RuntimeError se nao houver HoraTagPlusConta ativa.
        Outros erros sao capturados e retornados em status='erro'.
    """
    conta = HoraTagPlusConta.ativa()
    if conta is None:
        raise RuntimeError(
            'Nenhuma HoraTagPlusConta ativa — configure em /hora/tagplus/conta.'
        )
    api = ApiClient(conta)

    entry: dict = {
        'tagplus_nfe_id': nfe_id_tagplus,
        'numero_nf': None,
        'chave': None,
        'status_tagplus': None,
        'status': None,
        'venda_id': None,
        'qtd_chassis': 0,
        'qtd_divergencias': 0,
        'mensagem': '',
    }

    try:
        venda, status = _importar_com_retry_db(
            api, nfe_id_tagplus, operador=operador,
        )
        entry['status'] = status

        if venda is not None:
            entry['venda_id'] = venda.id
            entry['numero_nf'] = venda.nf_saida_numero
            entry['chave'] = venda.nf_saida_chave_44
            entry['qtd_chassis'] = len(venda.itens)
            entry['qtd_divergencias'] = len(venda.divergencias_abertas)

        if status == 'criado':
            entry['mensagem'] = (
                f'NF {entry["numero_nf"]} criada — '
                f'{entry["qtd_chassis"]} chassi(s) para {venda.nome_cliente}.'
            )
        elif status == 'atualizado':
            entry['mensagem'] = (
                f'NF {entry["numero_nf"]} atualizada (campos vazios '
                f'preenchidos a partir da API).'
            )
        elif status == 'inalterado':
            entry['mensagem'] = (
                f'NF {entry["numero_nf"]} ja estava completa — nada a fazer.'
            )
        elif status == 'cancelado':
            entry['mensagem'] = (
                f'NF {entry["numero_nf"]} CANCELADA na SEFAZ. '
                f'Pedido marcado como CANCELADO + DEVOLVIDA emitida nos chassis.'
            )
        elif status == 'pulada_cancelada':
            entry['mensagem'] = (
                f'NFe cancelada/inutilizada e nao existia no sistema — pulada.'
            )
        elif status == 'pulada_status_invalido':
            entry['mensagem'] = (
                f'NFe com status nao-aprovado (denegada/em-digitacao) — pulada.'
            )
        else:
            entry['mensagem'] = f'Status retornado desconhecido: {status!r}'
            entry['status'] = 'erro'
    except NfeJaImportada as exc:
        entry['status'] = 'duplicado'
        entry['mensagem'] = str(exc)
    except NfeIncompleta as exc:
        entry['status'] = 'erro'
        entry['mensagem'] = f'Incompleta: {exc}'
        try:
            db.session.rollback()
        except Exception:
            pass
    except Exception as exc:  # noqa: BLE001
        entry['status'] = 'erro'
        entry['mensagem'] = f'Erro inesperado: {exc}'
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.exception(
            'Backfill unica NFe %s: falha terminal', nfe_id_tagplus,
        )

    return entry


# --------------------------------------------------------------------------
# Background: enfileiramento de jobs RQ
# --------------------------------------------------------------------------

QUEUE_BACKFILL = 'hora_backfill'


def enfileirar_backfill_job(
    since: Optional[date],
    until: Optional[date],
    operador: Optional[str],
    limite: Optional[int] = None,
) -> int:
    """Cria HoraTagPlusBackfillJob + enfileira em RQ. Retorna job_id local.

    Levanta RuntimeError se REDIS_URL nao estiver configurado.
    """
    from app.hora.models import (
        HoraTagPlusBackfillJob,
        BACKFILL_JOB_STATUS_PENDENTE,
    )

    job = HoraTagPlusBackfillJob(
        status=BACKFILL_JOB_STATUS_PENDENTE,
        since=since,
        until=until,
        limite=limite,
        operador=operador,
    )
    db.session.add(job)
    db.session.commit()

    try:
        from rq import Queue, Retry
        from redis import Redis
    except ImportError:
        raise RuntimeError(
            'RQ/Redis nao instalado — backfill background indisponivel.'
        )

    redis_url = os.environ.get('REDIS_URL')
    if not redis_url:
        # Marca job como erro e avisa caller.
        from app.hora.models import BACKFILL_JOB_STATUS_ERRO
        job.status = BACKFILL_JOB_STATUS_ERRO
        job.ultimo_erro = 'REDIS_URL ausente — job nao pode ser enfileirado.'
        db.session.commit()
        raise RuntimeError(job.ultimo_erro)

    redis_conn = Redis.from_url(redis_url)
    queue = Queue(QUEUE_BACKFILL, connection=redis_conn)
    rq_job = queue.enqueue(
        'app.hora.workers.backfill_worker.processar_backfill_job',
        job.id,
        job_timeout=7200,    # 2h — backfill pode ser muito longo
        result_ttl=86400,    # 1 dia
        failure_ttl=86400,
        retry=Retry(max=2, interval=[60, 300]),
        description=f'HORA backfill TagPlus job_id={job.id}',
    )
    job.rq_job_id = rq_job.id
    db.session.commit()
    return job.id


# ============================================================
# Backfill catalogo de produtos TagPlus -> hora_peca
# ============================================================

def _resolver_peca_id_por_codigo(codigo_produto: Optional[str]) -> Optional[int]:
    """Lookup de codigo TagPlus em hora_tagplus_peca_map."""
    if not codigo_produto:
        return None
    from app.hora.models import HoraTagPlusPecaMap
    cod = str(codigo_produto).strip()
    if not cod:
        return None
    m = HoraTagPlusPecaMap.query.filter_by(tagplus_codigo=cod).first()
    return m.peca_id if m else None


def executar_backfill_produtos_pecas(
    operador: Optional[str] = None,
) -> dict:
    """Itera GET /produtos do TagPlus e popula hora_peca + hora_tagplus_peca_map.

    Heuristica: produtos com NCM iniciando em '8711' (motos eletricas)
    sao PULADOS — nao entram como peca.

    Idempotente: re-execucao atualiza, nao duplica.

    Returns:
        dict com contadores: criadas, atualizadas, puladas_moto, erros.
    """
    from app.hora.models import HoraPeca, HoraTagPlusPecaMap, HoraTagPlusConta
    from app.hora.services.tagplus.api_client import ApiClient

    conta = HoraTagPlusConta.ativa()
    api = ApiClient(conta)
    page = 1
    relatorio = {'criadas': 0, 'atualizadas': 0, 'puladas_moto': 0, 'erros': 0}
    erros_detalhe: list[str] = []

    while True:
        try:
            r = api.get('/produtos', params={'per_page': 100, 'page': page})
        except Exception as exc:
            relatorio['erros'] += 1
            erros_detalhe.append(f'page={page}: {exc}')
            break

        if r.status_code != 200:
            relatorio['erros'] += 1
            erros_detalhe.append(f'page={page}: status={r.status_code}')
            break

        try:
            data = r.json() or []
        except ValueError:
            data = []
        if isinstance(data, dict):
            data = data.get('data') or data.get('produtos') or []
        if not data:
            break

        for prod in data:
            try:
                ncm = (prod.get('ncm') or '').strip()
                codigo = (prod.get('codigo') or '').strip()
                descricao = (prod.get('descricao') or prod.get('nome') or '').strip()
                tagplus_id = str(prod.get('id') or '').strip()
                if not codigo or not tagplus_id:
                    continue
                # Heuristica de "e moto": NCM 8711* OU ja mapeado como moto.
                # Necessario porque TagPlus pode retornar NCM vazio (caso real
                # observado em 2026-05-05): so a checagem NCM falhava em
                # detectar motos como MT-MC20, MT-X12 10 - 18X etc.
                e_moto = ncm.startswith('8711')
                if not e_moto:
                    e_moto = db.session.query(
                        HoraTagPlusProdutoMap.id
                    ).filter(
                        (HoraTagPlusProdutoMap.tagplus_codigo == codigo)
                        | (HoraTagPlusProdutoMap.tagplus_produto_id == tagplus_id)
                    ).first() is not None
                if e_moto:
                    relatorio['puladas_moto'] += 1
                    continue

                existing = HoraPeca.query.filter_by(codigo_interno=codigo).first()
                if existing:
                    p = existing
                    if descricao and not p.descricao:
                        p.descricao = descricao
                    if ncm and not p.ncm:
                        p.ncm = ncm
                    relatorio['atualizadas'] += 1
                else:
                    unidade = (prod.get('unidade') or 'UN').strip().upper()[:5]
                    p = HoraPeca(
                        codigo_interno=codigo,
                        descricao=descricao or codigo,
                        ncm=ncm or None,
                        cfop_default='5.102',
                        unidade=unidade or 'UN',
                    )
                    db.session.add(p)
                    db.session.flush()
                    relatorio['criadas'] += 1

                m = HoraTagPlusPecaMap.query.filter_by(peca_id=p.id).first()
                if not m:
                    m = HoraTagPlusPecaMap(peca_id=p.id, tagplus_produto_id=tagplus_id)
                    db.session.add(m)
                m.tagplus_codigo = codigo
                if not m.tagplus_produto_id:
                    m.tagplus_produto_id = tagplus_id
            except Exception as exc:
                relatorio['erros'] += 1
                erros_detalhe.append(f'page={page} prod={prod.get("codigo")}: {exc}')
                continue

        db.session.commit()
        page += 1
        if len(data) < 100:
            break

    relatorio['erros_detalhe'] = erros_detalhe[:20]
    return relatorio


# ============================================================
# Backfill delta: NFes com valor_total > soma(itens) -> tem peca
# ============================================================

def executar_backfill_pecas_faltantes(
    operador: Optional[str] = None,
    limite: int = 100,
) -> dict:
    """Reprocessa vendas FATURADO com delta valor_total > soma(itens) > 0.

    Esse delta indica que peca foi ignorada na importacao original.
    Repuxa NFe via GET /nfes/{id} e tenta classificar itens novos como pecas.
    """
    from sqlalchemy import func
    from app.hora.models import (
        HoraVendaItemPeca, HoraTagPlusConta,
    )
    from app.hora.services.tagplus.api_client import ApiClient

    sub_motos = (
        db.session.query(
            HoraVendaItem.venda_id.label('vid'),
            func.coalesce(func.sum(HoraVendaItem.preco_final), 0).label('soma_motos'),
        ).group_by(HoraVendaItem.venda_id).subquery()
    )
    sub_pecas = (
        db.session.query(
            HoraVendaItemPeca.venda_id.label('vid'),
            func.coalesce(func.sum(HoraVendaItemPeca.preco_final), 0).label('soma_pecas'),
        ).group_by(HoraVendaItemPeca.venda_id).subquery()
    )

    rows = (
        db.session.query(
            HoraVenda, sub_motos.c.soma_motos, sub_pecas.c.soma_pecas,
        )
        .outerjoin(sub_motos, sub_motos.c.vid == HoraVenda.id)
        .outerjoin(sub_pecas, sub_pecas.c.vid == HoraVenda.id)
        .filter(HoraVenda.status == VENDA_STATUS_FATURADO)
        .limit(limite * 5)
        .all()
    )

    relatorio = {
        'analisadas': 0, 'reprocessadas': 0, 'pecas_criadas': 0,
        'sem_emissao': 0, 'sem_mapping': 0, 'erros': 0,
        'detalhes': [],
    }

    conta = HoraTagPlusConta.ativa()
    api = ApiClient(conta)

    for venda, sm, sp in rows:
        if relatorio['reprocessadas'] >= limite:
            break
        relatorio['analisadas'] += 1
        soma = Decimal(str(sm or 0)) + Decimal(str(sp or 0))
        delta = Decimal(str(venda.valor_total or 0)) - soma
        if delta <= Decimal('0.01'):
            continue

        emissao = HoraTagPlusNfeEmissao.query.filter_by(venda_id=venda.id).first()
        if not emissao or not emissao.tagplus_nfe_id:
            relatorio['sem_emissao'] += 1
            continue

        try:
            r = api.get(f'/nfes/{emissao.tagplus_nfe_id}')
            if r.status_code != 200:
                relatorio['erros'] += 1
                continue
            nfe_data = r.json() or {}
            itens_api = nfe_data.get('itens', []) if isinstance(nfe_data, dict) else []

            ids_motos_existentes = {vi.numero_chassi for vi in venda.itens}
            criou_alguma = False
            for it in itens_api:
                prod = it.get('produto') if isinstance(it, dict) else None
                codigo = None
                if isinstance(prod, dict):
                    codigo = (prod.get('codigo') or '').strip() or None
                elif isinstance(prod, (str, int)):
                    codigo = str(prod).strip() or None
                if not codigo:
                    continue

                # Se codigo bate com mapping de peca, cria HoraVendaItemPeca.
                peca_id = _resolver_peca_id_por_codigo(codigo)
                if not peca_id:
                    relatorio['sem_mapping'] += 1
                    continue

                # Idempotencia: nao duplicar peca ja registrada
                ja_existe = HoraVendaItemPeca.query.filter_by(
                    venda_id=venda.id, peca_id=peca_id,
                ).first()
                if ja_existe:
                    continue

                qtd = Decimal(str(it.get('qtd') or 0))
                valor_unit = Decimal(str(it.get('valor_unitario') or 0))
                desconto_unit = Decimal(str(it.get('valor_desconto') or 0))
                if qtd <= 0 or valor_unit <= 0:
                    continue

                preco_final = qtd * (valor_unit - desconto_unit)
                vp = HoraVendaItemPeca(
                    venda_id=venda.id, peca_id=peca_id,
                    qtd=qtd,
                    preco_unitario_referencia=valor_unit,
                    desconto_aplicado=desconto_unit,
                    preco_final=preco_final,
                )
                db.session.add(vp)
                db.session.flush()
                relatorio['pecas_criadas'] += 1
                criou_alguma = True

            if criou_alguma:
                relatorio['reprocessadas'] += 1
                db.session.commit()
        except Exception as exc:
            relatorio['erros'] += 1
            relatorio['detalhes'].append(f'venda={venda.id}: {exc}')
            db.session.rollback()
            continue

    return relatorio
