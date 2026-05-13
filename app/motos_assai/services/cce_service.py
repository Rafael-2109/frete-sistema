"""Service centralizado de Carta de Correcao Eletronica (CCe).

Spec interna: feature CCe avulsa (2026-05-13).

Fluxos cobertos:
1. CCe avulsa SEM NF correspondente → registra como PENDENTE (tem_nf=False).
2. CCe avulsa COM NF presente → registra + aplica imediatamente.
3. Importacao de NF Q.P.A. → query CCes pendentes que casem (match reverso).
4. CCe vinda de divergencia → registra + aplica + fecha divergencia.

Idempotencia:
- UNIQUE em assai_cce.protocolo_cce: se PDF da mesma CCe re-enviado, retorna o
  registro existente (nao cria duplicata).

Match CCe → NF:
- Preferido: chave_44 (44 digitos, identidade SEFAZ da NF).
- Fallback: numero da NF (com lstrip('0') para normalizar).
"""
from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Any, Dict, Optional, List

from sqlalchemy.exc import IntegrityError

from app import db
from app.utils.timezone import agora_brasil_naive
from app.utils.file_storage import FileStorage
from app.utils.json_helpers import sanitize_for_json

from app.motos_assai.models import (
    AssaiCce, AssaiNfQpa, NF_STATUS_CANCELADA,
    CCE_STATUS_PENDENTE, CCE_STATUS_APLICADA,
    CCE_STATUS_IGNORADA, CCE_STATUS_ERRO,
    DIVERGENCIA_RESOLUCAO_CCE,
)
from app.motos_assai.services.parsers.cce_pdf_extractor import (
    extrair_cce, CceParseError, CONFIANCA_LIMIAR,
)


logger = logging.getLogger(__name__)


class CceServiceError(Exception):
    """Erro no fluxo de registro/aplicacao de CCe."""


# =============================================================================
# Entrada principal
# =============================================================================

def registrar_cce(
    pdf_bytes: bytes,
    nome_arquivo: str,
    operador_id: int,
    divergencia_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Registra CCe no banco (idempotente) e tenta aplicar imediatamente se NF
    correspondente ja existir.

    Args:
        pdf_bytes: conteudo do PDF da CCe.
        nome_arquivo: nome original do arquivo (auditoria).
        operador_id: usuario que enviou.
        divergencia_id: opcional — se veio do botao CCe em uma divergencia.

    Returns:
        dict com chaves:
            - ok (bool)
            - cce_id (int)
            - status (PENDENTE | APLICADA | IGNORADA | ERRO)
            - tem_nf (bool)
            - tipo_correcao (str)
            - chassis_aplicados (list)
            - mensagem (str legivel)
            - duplicada (bool — true se CCe ja existia com mesmo protocolo)
            - confianca (float)
            - parser_usado (str)

    Raises:
        CceServiceError: PDF invalido ou erro irrecuperavel no parser.
    """
    if not pdf_bytes:
        raise CceServiceError('PDF vazio')

    # 1. Parser deterministico (com fallback LLM se confianca baixa)
    dados = _parsear_cce_com_fallback(pdf_bytes)

    protocolo = dados.get('protocolo_cce')
    if not protocolo:
        # Sem protocolo SEFAZ, nao temos identidade unica — recusar.
        # (Pode ocorrer com formato MOTOCHEFE que nao expoe protocolo no PDF.)
        # Fallback: usar chave_nfe + sequencia como pseudo-protocolo.
        chave = dados.get('chave_nfe')
        seq = dados.get('numero_cce') or 'SEQ-DESCONHECIDA'
        if chave:
            protocolo = f'PSEUDO-{chave}-{seq}'
        else:
            raise CceServiceError(
                'CCe sem protocolo SEFAZ nem chave de NF — '
                'nao e possivel garantir idempotencia.'
            )

    # 2. Idempotencia: verificar se ja existe
    existente = AssaiCce.query.filter_by(protocolo_cce=protocolo).first()
    if existente:
        return {
            'ok': True,
            'cce_id': existente.id,
            'status': existente.status,
            'tem_nf': existente.tem_nf,
            'tipo_correcao': existente.tipo_correcao,
            'chassis_aplicados': existente.chassis_aplicados or [],
            'mensagem': (
                f'CCe {protocolo} ja registrada anteriormente '
                f'(status={existente.status}).'
            ),
            'duplicada': True,
            'confianca': float(existente.confianca_parser or 0),
            'parser_usado': existente.parser_usado,
        }

    # 3. Persistir PDF em S3 (best-effort — se falhar, segue sem pdf_s3_key)
    pdf_s3_key = None
    try:
        buf = io.BytesIO(pdf_bytes)
        buf.name = nome_arquivo or 'cce.pdf'
        pdf_s3_key = FileStorage().save_file(
            buf, folder='motos_assai/cce', filename=nome_arquivo or 'cce.pdf',
            allowed_extensions=['pdf'],
        )
    except Exception as e:
        logger.warning(
            'Falha ao salvar CCe %s no S3 — seguindo sem pdf_s3_key: %s',
            protocolo, e,
        )

    # 4. Criar registro
    chave_nfe = dados.get('chave_nfe') or ''
    numero_nf = dados.get('numero_nf_referenciada') or ''
    sequencia = _extrair_sequencia(dados)

    cce = AssaiCce(
        protocolo_cce=protocolo,
        chave_nfe=chave_nfe,
        numero_nf_referenciada=numero_nf,
        sequencia_cce=sequencia,
        numero_cce=dados.get('numero_cce'),
        tipo_correcao=dados.get('tipo_correcao') or 'OUTRO',
        formato_detectado=dados.get('formato_detectado'),
        parser_usado=dados.get('parser_usado'),
        confianca_parser=dados.get('confianca'),
        dados_parsed=_sanitizar_dados_parsed(dados),
        pdf_s3_key=pdf_s3_key,
        nome_arquivo_original=nome_arquivo,
        data_emissao_cce=_parse_data(dados.get('data_emissao')),
        tem_nf=False,
        nf_id=None,
        status=CCE_STATUS_PENDENTE,
        divergencia_origem_id=divergencia_id,
        criado_por_id=operador_id,
    )
    db.session.add(cce)
    try:
        db.session.flush()  # popular cce.id (lanca IntegrityError em race)
    except IntegrityError:
        # Race condition: outro request inseriu mesmo protocolo entre nosso query
        # (linha 105) e flush. Rollback + cleanup S3 orfao + buscar existente.
        db.session.rollback()

        # Fix C1 (code review 2026-05-13): se PDF ja foi uploadado para S3
        # antes do flush falhar, o rollback do DB nao remove o objeto S3.
        # Limpar para evitar acumulo de PDFs orfaos a cada race condition.
        if pdf_s3_key:
            try:
                FileStorage().delete_file(pdf_s3_key)
            except Exception as e_s3:
                logger.warning(
                    'Falha ao limpar S3 key %s apos race: %s', pdf_s3_key, e_s3,
                )

        logger.info(
            'registrar_cce race condition para protocolo %s — retornando existente',
            protocolo,
        )
        existente = AssaiCce.query.filter_by(protocolo_cce=protocolo).first()
        if existente:
            return {
                'ok': True,
                'cce_id': existente.id,
                'status': existente.status,
                'tem_nf': existente.tem_nf,
                'tipo_correcao': existente.tipo_correcao,
                'chassis_aplicados': existente.chassis_aplicados or [],
                'mensagem': (
                    f'CCe {protocolo} ja registrada (race condition resolvida).'
                ),
                'duplicada': True,
                'confianca': float(existente.confianca_parser or 0),
                'parser_usado': existente.parser_usado,
            }
        # Race resolveu mas registro nao apareceu (improvavel) — re-lanca
        raise CceServiceError(
            f'IntegrityError ao salvar CCe {protocolo} mas registro nao foi '
            'localizado depois do rollback.'
        )

    # 5. Tentar aplicar imediatamente se NF existe
    resultado_aplicar = _tentar_aplicar_cce(
        cce, operador_id=operador_id, divergencia_id=divergencia_id,
    )

    db.session.commit()

    return {
        'ok': True,
        'cce_id': cce.id,
        'status': cce.status,
        'tem_nf': cce.tem_nf,
        'tipo_correcao': cce.tipo_correcao,
        'chassis_aplicados': cce.chassis_aplicados or [],
        'mensagem': resultado_aplicar['mensagem'],
        'duplicada': False,
        'confianca': float(cce.confianca_parser or 0),
        'parser_usado': cce.parser_usado,
    }


# =============================================================================
# Match reverso: ao importar NF, ver CCes pendentes
# =============================================================================

def aplicar_cce_pendentes_para_nf(
    nf: AssaiNfQpa, operador_id: int,
) -> List[Dict[str, Any]]:
    """Ao importar NF, busca CCes registradas SEM nf vinculada e que casem com
    esta NF (chave_44 igual OU numero igual normalizado). Aplica cada uma.

    Args:
        nf: AssaiNfQpa recem-importada (ja persistida com id).
        operador_id: usuario que importou a NF.

    Returns:
        Lista de dicts (um por CCe processada). Vazia se nao havia pendentes.

    Nota:
        Caller (importar_nf_qpa) chama ANTES do commit final — esta funcao
        flush mas NAO commita.
    """
    if not nf.id:
        return []

    numero_normalizado = (nf.numero or '').lstrip('0') or '0'

    pendentes = AssaiCce.query.filter(
        AssaiCce.tem_nf == False,  # noqa: E712  (SQLAlchemy precisa de ==)
        AssaiCce.status == CCE_STATUS_PENDENTE,
        db.or_(
            AssaiCce.chave_nfe == nf.chave_44,
            AssaiCce.numero_nf_referenciada == numero_normalizado,
            AssaiCce.numero_nf_referenciada == nf.numero,
        ),
    ).all()

    if not pendentes:
        return []

    logger.info(
        'aplicar_cce_pendentes_para_nf: NF %s (chave=%s) matched %d CCes pendentes',
        nf.numero, nf.chave_44, len(pendentes),
    )

    resultados = []
    for cce in pendentes:
        # Fix H4 (code review 2026-05-13): isolar mutacao de cada CCe num savepoint.
        # Se uma CCe falhar (ex: aplicar_correcao_cce lanca, ou flush emite erro
        # de constraint), o rollback do savepoint reverte SOMENTE essa CCe — a
        # NF principal e demais CCes ja aplicadas permanecem intactas. Sem
        # savepoint, uma falha contaminaria a sessao inteira e a transacao
        # principal de `importar_nf_qpa` quebraria.
        savepoint = db.session.begin_nested()
        try:
            resultado = _tentar_aplicar_cce(
                cce, operador_id=operador_id,
                nf_alvo=nf,  # otimizacao — ja sabemos qual NF e
            )
            db.session.flush()  # confirma mutacoes dentro do savepoint
            savepoint.commit()
            resultados.append({
                'cce_id': cce.id,
                'protocolo': cce.protocolo_cce,
                'status_final': cce.status,
                'mensagem': resultado['mensagem'],
            })
        except Exception as e:
            logger.exception(
                'aplicar_cce_pendentes_para_nf: CCe %s falhou — %s',
                cce.protocolo_cce, e,
            )
            savepoint.rollback()  # reverte mutacoes desta CCe

            # Re-marcar CCe como ERRO numa transacao separada (savepoint novo)
            # para que o status fique persistido apesar do rollback acima.
            try:
                cce_fresh = AssaiCce.query.get(cce.id)
                if cce_fresh:
                    sp_err = db.session.begin_nested()
                    cce_fresh.status = CCE_STATUS_ERRO
                    cce_fresh.observacao = f'Erro no match reverso: {e}'[:1000]
                    db.session.flush()
                    sp_err.commit()
            except Exception as e_marcar:
                logger.warning(
                    'Nao foi possivel marcar CCe %s como ERRO: %s',
                    cce.id, e_marcar,
                )

            resultados.append({
                'cce_id': cce.id,
                'protocolo': cce.protocolo_cce,
                'status_final': CCE_STATUS_ERRO,
                'mensagem': f'Erro: {e}',
            })

    return resultados


# =============================================================================
# Aplicacao da CCe — chamado por registrar_cce E aplicar_cce_pendentes_para_nf
# =============================================================================

def _tentar_aplicar_cce(
    cce: AssaiCce,
    operador_id: int,
    divergencia_id: Optional[int] = None,
    nf_alvo: Optional[AssaiNfQpa] = None,
) -> Dict[str, Any]:
    """Tenta aplicar a CCe: resolve NF, troca chassis, fecha divergencia.

    Args:
        cce: AssaiCce (com id, ainda nao commitada se vem de registrar_cce).
        operador_id: usuario que aplicou.
        divergencia_id: opcional — se foi originada de uma divergencia para fechar.
        nf_alvo: otimizacao — se ja sabemos qual NF, passar para evitar lookup.

    Returns:
        dict com {ok, mensagem, status_final}.

    Nao commita — caller decide.
    """
    # 1. Tipo NAO_CHASSI: registrar como IGNORADA mas tentar vincular NF
    if cce.tipo_correcao not in ('CHASSI',):
        nf = nf_alvo or _resolver_nf_da_cce(cce)
        if nf:
            cce.nf_id = nf.id
            cce.tem_nf = True
        cce.status = CCE_STATUS_IGNORADA
        cce.observacao = (
            f'CCe tipo {cce.tipo_correcao} — nenhuma alteracao automatica '
            f'aplicada (apenas registro). Acao manual necessaria.'
        )
        return {
            'ok': True,
            'status_final': cce.status,
            'mensagem': (
                f'CCe registrada como {cce.tipo_correcao} — '
                'nao altera chassis. Verifique manualmente.'
            ),
        }

    # 2. Tipo CHASSI sem chassis_corrigidos no parser → ERRO
    chassis = _extrair_chassis_corrigidos(cce.dados_parsed)
    if not chassis:
        cce.status = CCE_STATUS_ERRO
        cce.observacao = 'CCe tipo CHASSI mas parser nao identificou chassis_corrigidos.'
        return {
            'ok': False,
            'status_final': cce.status,
            'mensagem': cce.observacao,
        }

    # 3. Resolver NF (chave_44 ou numero)
    nf = nf_alvo or _resolver_nf_da_cce(cce)
    if not nf:
        # NF nao chegou ainda — fica PENDENTE
        cce.status = CCE_STATUS_PENDENTE
        cce.tem_nf = False
        return {
            'ok': True,
            'status_final': cce.status,
            'mensagem': (
                f'CCe registrada como PENDENTE — NF {cce.numero_nf_referenciada} '
                f'(chave {cce.chave_nfe[:8]}...) ainda nao importada. '
                'Sera aplicada automaticamente quando a NF chegar.'
            ),
        }

    # 3b. GUARD: quando vem com divergencia_id, validar que a NF resolvida pelo
    # PDF corresponde a NF da divergencia. Evita aplicar chassis na NF errada
    # se operador fez upload do PDF da CCe X numa divergencia da NF Y.
    if divergencia_id:
        from app.motos_assai.models import AssaiDivergencia
        div = AssaiDivergencia.query.get(divergencia_id)
        if div and div.nf_id and div.nf_id != nf.id:
            cce.nf_id = nf.id  # vincula a NF correta (auditoria)
            cce.tem_nf = True
            cce.status = CCE_STATUS_ERRO
            cce.observacao = (
                f'PDF da CCe referencia NF {nf.numero} (id={nf.id}), '
                f'mas a divergencia {divergencia_id} aponta para NF id={div.nf_id}. '
                'Upload rejeitado para evitar trocar chassis na NF errada.'
            )
            return {
                'ok': False,
                'status_final': cce.status,
                'mensagem': cce.observacao,
            }

    # 4. NF cancelada nao aceita CCe
    if nf.status_match == NF_STATUS_CANCELADA:
        cce.nf_id = nf.id
        cce.tem_nf = True
        cce.status = CCE_STATUS_ERRO
        cce.observacao = f'NF {nf.numero} esta CANCELADA — CCe nao aplicada.'
        return {
            'ok': False,
            'status_final': cce.status,
            'mensagem': cce.observacao,
        }

    # 5. Aplicar correcao
    from app.motos_assai.services.cancelamento_nf_service import (
        aplicar_correcao_cce, CancelamentoValidationError,
    )

    try:
        aplicar_correcao_cce(
            nf_id=nf.id,
            chassis_corrigidos=chassis,
            numero_cce=cce.numero_cce or cce.protocolo_cce,
            operador_id=operador_id,
        )
    except CancelamentoValidationError as e:
        cce.nf_id = nf.id
        cce.tem_nf = True
        cce.status = CCE_STATUS_ERRO
        cce.observacao = f'aplicar_correcao_cce falhou: {e}'
        return {
            'ok': False,
            'status_final': cce.status,
            'mensagem': cce.observacao,
        }

    # 6. Sucesso — atualizar registros
    cce.nf_id = nf.id
    cce.tem_nf = True
    cce.status = CCE_STATUS_APLICADA
    cce.aplicada_em = agora_brasil_naive()
    cce.aplicada_por_id = operador_id
    # Fix H1 (code review 2026-05-13): sanitize_for_json garante JSONB-safe
    cce.chassis_aplicados = sanitize_for_json([list(par) for par in chassis])

    # 7. Se veio de divergencia, fechar
    if divergencia_id:
        try:
            from app.motos_assai.services.divergencia_service import (
                resolver_divergencia, DivergenciaError,
            )
            resolver_divergencia(
                div_id=divergencia_id,
                tipo_resolucao=DIVERGENCIA_RESOLUCAO_CCE,
                observacao=(
                    f'CCe {cce.numero_cce or cce.protocolo_cce} aplicada — '
                    f'{len(chassis)} chassis trocados (parser={cce.parser_usado})'
                ),
                operador_id=operador_id,
            )
        except DivergenciaError as e:
            logger.warning(
                'CCe %s aplicada mas resolver_divergencia(%s) falhou: %s',
                cce.protocolo_cce, divergencia_id, e,
            )
            cce.observacao = (
                f'Chassis aplicados, mas falha ao fechar divergencia {divergencia_id}: {e}'
            )

    return {
        'ok': True,
        'status_final': cce.status,
        'mensagem': (
            f'CCe aplicada — {len(chassis)} chassis trocados na NF {nf.numero}.'
        ),
    }


# =============================================================================
# Helpers
# =============================================================================

def _resolver_nf_da_cce(cce: AssaiCce) -> Optional[AssaiNfQpa]:
    """Busca AssaiNfQpa correspondente: chave_44 primario, numero fallback."""
    # 1. Match por chave_44 (mais robusto)
    if cce.chave_nfe:
        nf = AssaiNfQpa.query.filter_by(chave_44=cce.chave_nfe).first()
        if nf:
            return nf

    # 2. Fallback: numero da NF (com e sem zeros a esquerda)
    if cce.numero_nf_referenciada:
        numero_normalizado = cce.numero_nf_referenciada.lstrip('0') or '0'
        # Tentar com normalizado primeiro
        nf = AssaiNfQpa.query.filter_by(numero=numero_normalizado).first()
        if nf:
            return nf
        # Tentar com zeros a esquerda (se for diferente)
        if cce.numero_nf_referenciada != numero_normalizado:
            nf = AssaiNfQpa.query.filter_by(numero=cce.numero_nf_referenciada).first()
            if nf:
                return nf

    return None


def _parsear_cce_com_fallback(pdf_bytes: bytes) -> Dict[str, Any]:
    """Parser deterministico → fallback LLM se confianca < CONFIANCA_LIMIAR."""
    try:
        dados = extrair_cce(pdf_bytes)
    except CceParseError as e:
        logger.info('cce_pdf_extractor falhou (%s) — escalando para LLM', e)
        dados = {
            'confianca': 0.0,
            'chassis_corrigidos': [],
            'tipo_correcao': 'OUTRO',
        }

    if dados.get('confianca', 0.0) <= CONFIANCA_LIMIAR:
        try:
            from app.motos_assai.services.parsers.cce_llm_fallback import (
                extrair_cce_via_llm,
            )
            dados_llm = extrair_cce_via_llm(pdf_bytes)
            if dados_llm.get('confianca', 0) >= dados.get('confianca', 0):
                dados = dados_llm
        except Exception as e:
            logger.warning(
                'cce_llm_fallback falhou: %s — usando dados deterministicos parciais',
                e,
            )

    if not dados.get('numero_nf_referenciada'):
        raise CceServiceError(
            'PDF nao parece ser uma CCe valida — '
            'nem parser deterministico nem LLM identificou NF referenciada.'
        )

    return dados


def _extrair_sequencia(dados: Dict[str, Any]) -> int:
    """Extrai sequencia da CCe (default 1)."""
    numero_cce = dados.get('numero_cce') or ''
    # Tenta extrair de "CCe-1-NF1729" → 1
    import re
    m = re.search(r'CCe-(\d+)', numero_cce)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return 1


def _extrair_chassis_corrigidos(dados_parsed: Any) -> List[tuple]:
    """Extrai lista de tuplas (antigo, novo) do dict de dados_parsed."""
    if not isinstance(dados_parsed, dict):
        return []
    chassis_raw = dados_parsed.get('chassis_corrigidos') or []
    resultado = []
    for par in chassis_raw:
        if isinstance(par, (list, tuple)) and len(par) == 2:
            antigo, novo = par
            if antigo and novo:
                resultado.append((str(antigo).strip().upper(), str(novo).strip().upper()))
    return resultado


def _parse_data(data_str: Optional[str]):
    """Converte 'DD/MM/AAAA' para date (None se invalido)."""
    if not data_str:
        return None
    try:
        return datetime.strptime(data_str, '%d/%m/%Y').date()
    except (ValueError, TypeError):
        return None


def _sanitizar_dados_parsed(dados: Dict[str, Any]) -> Dict[str, Any]:
    """Prepara dict para persistencia em JSONB.

    1. Limita texto_correcao_bruto a 2KB (audit-friendly).
    2. Fix H1 (code review 2026-05-13): aplica sanitize_for_json (regra CLAUDE.md)
       — protege contra Decimal/datetime/UUID/bytes que LLM ou parser futuro
       possam introduzir. Tuples viram lists automaticamente.
    """
    sanitizado = dict(dados)
    if 'texto_correcao_bruto' in sanitizado:
        texto = sanitizado['texto_correcao_bruto'] or ''
        sanitizado['texto_correcao_bruto'] = texto[:2000]
    return sanitize_for_json(sanitizado)
