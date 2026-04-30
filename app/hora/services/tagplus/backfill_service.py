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
from app.hora.models.tagplus import HoraTagPlusConta, HoraTagPlusProdutoMap
from app.hora.models.venda import VENDA_STATUS_FATURADO
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
) -> Iterator[dict]:
    """Itera NFes da API TagPlus filtradas por data_emissao.

    Yields cada NFe (dict resumido — id, chave_acesso, status, data_emissao,
    valor_nota etc.). Paginacao via parametro `page`.

    Header X-Data-Filter: data_emissao (sobrescreve default data_criacao do TagPlus).
    """
    page = 1
    while True:
        params = {'page': page, 'per_page': per_page}
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


def _extrair_chassi_motor(detalhes: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Parsa string `detalhes` do item TagPlus.

    Formato emitido pelo nosso PayloadBuilder: 'Chassi: XYZ / Motor: ABC'.
    Tolera variacoes (espacos, caso, motor ausente).
    """
    if not detalhes:
        return (None, None)
    m = _RE_CHASSI_MOTOR.search(detalhes)
    if not m:
        return (None, None)
    chassi = (m.group(1) or '').strip().upper() or None
    motor = (m.group(2) or '').strip().upper() or None
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


def _resolver_modelo_id(codigo_produto: Optional[str]) -> Optional[int]:
    if not codigo_produto:
        return None
    cod = str(codigo_produto).strip()
    if not cod:
        return None
    mapa = HoraTagPlusProdutoMap.query.filter_by(tagplus_codigo=cod).first()
    return mapa.modelo_id if mapa else None


# --------------------------------------------------------------------------
# Importador unitario
# --------------------------------------------------------------------------

class NfeJaImportada(Exception):
    """Mesma chave_acesso ja existe em hora_venda.nf_saida_chave_44."""


class NfeIncompleta(Exception):
    """NFe da API TagPlus sem campos obrigatorios (chave_acesso, valor_nota)."""


def importar_nfe_da_api(
    api: ApiClient,
    nfe_id_tagplus: int,
    operador: Optional[str] = None,
) -> HoraVenda:
    """Puxa GET /nfes/{id} e cria HoraVenda + itens + eventos + divergencias.

    Idempotente: levanta `NfeJaImportada` quando chave_acesso ja existe.
    Retorna `HoraVenda` criada.
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

    chave = nfe.get('chave_acesso')
    valor_nota = nfe.get('valor_nota')
    if not chave or valor_nota is None:
        raise NfeIncompleta(
            f'NFe {nfe_id_tagplus} sem chave_acesso ou valor_nota '
            f'(chave={chave!r}, valor={valor_nota!r})'
        )
    chave = chave.strip()
    if len(chave) != 44:
        raise NfeIncompleta(
            f'NFe {nfe_id_tagplus} chave_acesso invalida (len={len(chave)})'
        )

    existente = HoraVenda.query.filter_by(nf_saida_chave_44=chave).first()
    if existente:
        raise NfeJaImportada(
            f'NF chave={chave} ja importada (venda_id={existente.id})'
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

    # ------ Cria HoraVenda ------
    venda = HoraVenda(
        loja_id=loja_emitente.id if loja_emitente else None,
        cpf_cliente=cpf[:14],
        nome_cliente=nome_cliente,
        data_venda=data_emissao,
        forma_pagamento='NAO_INFORMADO',
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
        # numero_parcelas e intervalo_parcelas_dias permanecem default (1 / 30) —
        # parcelas reais ficam refletidas em hora_tagplus_nfe_emissao se for
        # NF emitida pelo nosso fluxo. Para NF historica, defaults bastam.
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
    itens_raw = nfe.get('itens') or []
    _ = serie_nf  # serie capturada para futuro armazenamento (hoje hora_venda nao guarda)
    _criar_itens_da_api(
        venda=venda,
        itens_api=itens_raw,
        loja_emitente_id=loja_emitente.id if loja_emitente else None,
        data_venda=data_emissao,
        operador=operador,
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
    return venda


def _criar_itens_da_api(
    venda: HoraVenda,
    itens_api: list,
    loja_emitente_id: Optional[int],
    data_venda,
    operador: Optional[str],
) -> None:
    """Cria HoraVendaItem para cada chassi listado em `itens_api`.

    Cada item TagPlus pode ter `qtd > 1` — nesse caso espera-se 1 chassi por
    unidade (formato esperado: campo `detalhes` da resposta lista os chassis
    OU multiplos itens com qtd=1 cada).

    Estrategia:
      1. Tenta extrair chassi do campo `detalhes` do item ('Chassi: X / Motor: Y').
      2. Se nao achar, registra divergencia tipo CHASSI_NAO_CADASTRADO.
    """
    from app.hora.services.venda_service import (
        _registrar_divergencia, _resolver_preco_tabela,
    )

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

        # Extrair chassis do campo detalhes (1 ou multiplos separados por ';' ou '|').
        detalhes = (it.get('detalhes') or '').strip()
        chassis_motores = _extrair_chassis_multiplos(detalhes)

        if not chassis_motores:
            _registrar_divergencia(
                venda_id=venda.id, tipo='CHASSI_NAO_CADASTRADO',
                detalhe=(
                    f'Item produto={codigo_produto or descricao!r} qtd={qtd} '
                    f'sem chassi extraivel de detalhes={detalhes!r}'
                ),
                valor_conferido=detalhes,
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
    n_ok = n_dup = n_err = n_div = 0

    iterador = listar_nfes_emitidas(api, since=since, until=until)
    for i, nfe_resumo in enumerate(iterador):
        if limite is not None and i >= limite:
            break

        nfe_id = nfe_resumo.get('id')
        chave_resumo = nfe_resumo.get('chave_acesso')
        numero_resumo = nfe_resumo.get('numero')

        entry = {
            'tagplus_nfe_id': nfe_id,
            'numero_nf': numero_resumo,
            'chave': chave_resumo,
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
            venda = importar_nfe_da_api(api, nfe_id, operador=operador)
            entry.update({
                'status': 'sucesso',
                'venda_id': venda.id,
                'numero_nf': venda.nf_saida_numero,
                'qtd_chassis': len(venda.itens),
                'qtd_divergencias': len(venda.divergencias_abertas),
                'mensagem': (
                    f'NF {venda.nf_saida_numero} importada — '
                    f'{len(venda.itens)} chassi(s) para {venda.nome_cliente}.'
                ),
            })
            n_ok += 1
            n_div += len(venda.divergencias_abertas)
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
        'sucesso': n_ok,
        'duplicado': n_dup,
        'erro': n_err,
        'divergencias': n_div,
        'resultados': resultados,
    }
