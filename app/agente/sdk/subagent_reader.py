"""
Wrapper do Claude Agent SDK 0.1.60 para inspecionar transcripts de subagentes.

Encapsula list_subagents() e get_subagent_messages() do SDK em uma API
orientada a dominio — retorna SubagentSummary pronto para serializacao,
com suporte opcional a mascaramento de PII.

Todos os consumidores (endpoint admin, UI, cost tracking, memory mining,
validacao anti-alucinacao) leem por aqui. Ponto unico de adaptacao para
futuras mudancas da API do SDK.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from claude_agent_sdk import get_subagent_messages, list_subagents

from app.agente.utils.pii_masker import mask_pii
from app.utils.timezone import agora_brasil_naive

logger = logging.getLogger('sistema_fretes')

Status = Literal['running', 'done', 'error']

# UUID ou hex-like (agent_id/session_id). Rejeita ../, **, /, \
_RE_SAFE_ID = re.compile(r'^[0-9a-fA-F-]{1,64}$')


def _is_safe_id(value: str) -> bool:
    """Valida que value nao contem path traversal nem glob wildcards."""
    if not value:
        return False
    return bool(_RE_SAFE_ID.match(value))


@dataclass
class SubagentSummary:
    """Resumo estruturado de um subagente para serializacao JSON."""
    agent_id: str
    agent_type: str
    status: Status
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    duration_ms: Optional[int]
    tools_used: list[dict] = field(default_factory=list)
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    num_turns: int = 0
    findings_text: str = ''
    stop_reason: Optional[str] = None

    def to_dict(self, include_cost: bool = True) -> dict:
        """Serializa para dict. Se include_cost=False, remove cost_usd."""
        d = {
            'agent_id': self.agent_id,
            'agent_type': self.agent_type,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration_ms': self.duration_ms,
            'tools_used': self.tools_used,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'cache_read_tokens': self.cache_read_tokens,
            'num_turns': self.num_turns,
            'findings_text': self.findings_text,
            'stop_reason': self.stop_reason,
        }
        if include_cost:
            d['cost_usd'] = self.cost_usd
        return d


def _candidate_directories(directory: Optional[str]) -> list[Optional[str]]:
    """
    Diretorios candidatos para list_subagents/get_subagent_messages.

    Ordem:
    1. directory explicito (se fornecido)
    2. None (SDK default: $CLAUDE_CONFIG_DIR ou ~/.claude)
    3. /tmp/.claude (Render: CLI bundled escreve aqui)
    """
    if directory:
        return [directory]
    return [None, '/tmp/.claude']


def list_session_subagents(
    session_id: str,
    directory: Optional[str] = None,
) -> list[str]:
    """Wrapper de list_subagents(). Tenta multiplos diretorios (Render fallback)."""
    for candidate in _candidate_directories(directory):
        try:
            # SDK: directory=None usa ~/.claude, string sobrescreve
            kwargs = {'directory': candidate} if candidate else {}
            result = list(list_subagents(session_id, **kwargs))
            if result:
                logger.info(
                    f"[subagent_reader] list_subagents found {len(result)} "
                    f"agents in directory={candidate or '<default>'}"
                )
                return result
        except Exception as e:
            logger.debug(
                f"[subagent_reader] list_subagents dir={candidate}: {e}"
            )
    logger.info(
        f"[subagent_reader] list_subagents empty for session={session_id[:16]}"
    )

    # P2 fallback: tenta restore do S3 e re-procura
    try:
        from .session_archive import restore_session_from_s3
        if restore_session_from_s3(session_id):
            # Apos restore, /tmp/agent_archive_restore/<session>/ tem os JSONLs
            # SDK list_subagents aceita directory customizado
            restore_dir = Path('/tmp/agent_archive_restore') / session_id
            if restore_dir.exists():
                try:
                    result = list(list_subagents(
                        session_id, directory=str(restore_dir)
                    ))
                    if result:
                        logger.info(
                            f"[subagent_reader] list_subagents recovered "
                            f"{len(result)} agents from S3 archive"
                        )
                        return result
                except Exception as e:
                    logger.debug(f"[subagent_reader] post-restore list: {e}")
    except Exception as e:
        logger.debug(f"[subagent_reader] S3 restore falhou: {e}")

    return []


def _default_metadata() -> dict:
    """Metadata zerada — formato padrao retornado por funcoes de leitura."""
    return {
        'cost_usd': 0.0, 'duration_ms': 0, 'num_turns': 0,
        'input_tokens': 0, 'output_tokens': 0,
        'cache_read_tokens': 0, 'cache_creation_tokens': 0,
        'stop_reason': None, 'started_at': None, 'ended_at': None,
    }


def _read_result_metadata(transcript_path: Optional[str]) -> dict:
    """
    Parseia a ultima ResultMessage do JSONL (se existir) para extrair
    cost/tokens/duration. Compat forward: se o CLI comecar a gravar
    type:'result' no transcript de subagent, sera aproveitado.

    Retorna dict com `_default_metadata()`. Campos ausentes = 0.

    NOTA: SDK 0.1.60 NAO grava type:'result' em transcript de SUBAGENT
    (apenas no PAI). Para subagents, usar `_compute_subagent_metadata_from_jsonl`
    como fallback.
    FONTE: claude_agent_sdk/_internal/sessions.py:791-794 (_TRANSCRIPT_ENTRY_TYPES).
    """
    default = _default_metadata()
    if not transcript_path or not Path(transcript_path).exists():
        return default

    try:
        last_result = None
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    if msg.get('type') == 'result':
                        last_result = msg
                except json.JSONDecodeError:
                    continue

        if not last_result:
            return default

        usage = last_result.get('usage', {}) or {}
        return {
            **default,
            'cost_usd': last_result.get('total_cost_usd') or 0.0,
            'duration_ms': last_result.get('duration_ms') or 0,
            'num_turns': last_result.get('num_turns') or 0,
            'input_tokens': usage.get('input_tokens') or 0,
            'output_tokens': usage.get('output_tokens') or 0,
            'cache_read_tokens': usage.get('cache_read_input_tokens') or 0,
            'cache_creation_tokens': usage.get('cache_creation_input_tokens') or 0,
            'stop_reason': last_result.get('stop_reason'),
        }
    except (OSError, IOError) as e:
        logger.debug(f"[subagent_reader] transcript inacessivel: {e}")
        return default


def _parse_iso_timestamp(value) -> Optional[datetime]:
    """Parseia timestamp do JSONL. Tolera varios formatos:

    - ISO string com Z: `'2026-04-17T12:20:13.600Z'`
    - ISO string com offset: `'2026-04-17T12:20:13.600+00:00'`
    - ISO string naive: `'2026-04-17T12:20:13'`
    - Epoch milliseconds (int ou float): `1713352813600`
    - Epoch seconds: `1713352813.6` (diferencia via magnitude)
    - datetime object (retorna as-is se timezone-naive, converte aware→naive)

    Retorna sempre **timezone-naive** para consistencia com _TIMEZONE_BRASIL
    padrao do projeto. Facilita max/min sem TypeError (B5 pre-mortem).
    """
    if value is None:
        return None
    # Datetime direto
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value
    # Epoch numerico
    if isinstance(value, (int, float)):
        try:
            from datetime import timezone as _tz
            # Heuristica: > 1e12 = milliseconds (post-2001); caso contrario segundos
            ts = value / 1000.0 if value > 1e12 else float(value)
            # Python 3.12+: utcfromtimestamp e deprecated — usar
            # fromtimestamp(tz=UTC) + replace(tzinfo=None) para manter naive.
            return datetime.fromtimestamp(ts, _tz.utc).replace(tzinfo=None)
        except (ValueError, OverflowError, OSError):
            return None
    # String ISO
    if isinstance(value, str) and value:
        try:
            normalized = value.replace('Z', '+00:00') if value.endswith('Z') else value
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is not None:
                return parsed.replace(tzinfo=None)
            return parsed
        except (ValueError, TypeError):
            return None
    return None


def _compute_subagent_metadata_from_jsonl(transcript_path: Optional[str]) -> dict:
    """
    Calcula metadata (cost/duration/tokens/num_turns/timestamps) de subagent
    somando `usage` de cada AssistantMessage + diff de timestamps.

    Necessario porque SDK 0.1.60 NAO grava type:'result' em transcript de
    subagent (apenas no PAI). Ver `_read_result_metadata` para compat forward.

    Usa pricing com cache correto via `sdk/pricing.py`.

    Defesa contra JSONL corrompido:
    - Linhas invalidas ignoradas (json.JSONDecodeError)
    - Usage ausente/None trata como zeros
    - Timestamps invalidos ignorados (duration_ms=0)
    - Multiplas linhas `assistant` somadas (nao sao cumulativas per-message
      em transcript de disco — cada AssistantMessage e 1 turno completo).
    """
    default = _default_metadata()
    if not transcript_path or not Path(transcript_path).exists():
        return default

    try:
        from .pricing import calculate_cost_with_cache
    except ImportError as e:
        logger.warning(f"[subagent_reader] pricing module indisponivel: {e}")
        return default

    input_total = 0
    output_total = 0
    cache_read_total = 0
    cache_creation_total = 0
    num_turns = 0
    model_seen: Optional[str] = None
    first_ts: Optional[datetime] = None
    last_ts: Optional[datetime] = None
    cost_total = 0.0

    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(msg, dict):
                    continue

                # Timestamps: aproveitar de toda linha valida para bounds.
                ts = _parse_iso_timestamp(msg.get('timestamp'))
                if ts is not None:
                    if first_ts is None or ts < first_ts:
                        first_ts = ts
                    if last_ts is None or ts > last_ts:
                        last_ts = ts

                if msg.get('type') != 'assistant':
                    continue

                # B4 fix: filtrar sidechains (mensagens de subagents aninhados
                # chamados por este mesmo subagent). O SDK marca com
                # `isSidechain: true` — contar somaria tokens 2x.
                if msg.get('isSidechain') is True:
                    continue

                # AssistantMessage: extrair usage + model
                inner = msg.get('message') or {}
                if not isinstance(inner, dict):
                    continue

                usage = inner.get('usage') or {}
                if not isinstance(usage, dict):
                    usage = {}

                msg_input = usage.get('input_tokens') or 0
                msg_output = usage.get('output_tokens') or 0
                msg_cache_read = usage.get('cache_read_input_tokens') or 0
                msg_cache_create = usage.get('cache_creation_input_tokens') or 0

                # Agregar
                input_total += max(0, int(msg_input))
                output_total += max(0, int(msg_output))
                cache_read_total += max(0, int(msg_cache_read))
                cache_creation_total += max(0, int(msg_cache_create))
                num_turns += 1

                # Model para pricing (usa o primeiro visto — subagent geralmente
                # usa 1 modelo consistente; variacao e incomum)
                msg_model = inner.get('model')
                if msg_model and not model_seen:
                    model_seen = str(msg_model)

                # Custo por turno (cache correto)
                cost_total += calculate_cost_with_cache(
                    input_tokens=int(msg_input) or 0,
                    output_tokens=int(msg_output) or 0,
                    cache_creation_tokens=int(msg_cache_create) or 0,
                    cache_read_tokens=int(msg_cache_read) or 0,
                    model=model_seen,
                )
    except (OSError, IOError) as e:
        logger.debug(f"[subagent_reader] compute_metadata: transcript inacessivel: {e}")
        return default

    # Calcular duration: max de 0 (protege contra timestamps fora de ordem)
    duration_ms = 0
    if first_ts and last_ts:
        delta_sec = (last_ts - first_ts).total_seconds()
        duration_ms = max(0, int(delta_sec * 1000))

    return {
        'cost_usd': round(cost_total, 6),
        'duration_ms': duration_ms,
        'num_turns': num_turns,
        'input_tokens': input_total,
        'output_tokens': output_total,
        'cache_read_tokens': cache_read_total,
        'cache_creation_tokens': cache_creation_total,
        'stop_reason': 'end_turn' if num_turns > 0 else None,
        'started_at': first_ts,
        'ended_at': last_ts,
    }


def _resolve_transcript_path(
    session_id: str,
    agent_id: str,
    directory: Optional[str] = None,
) -> Optional[str]:
    """Resolve caminho do JSONL do subagente em ~/.claude/projects/.../subagents/.

    Validacao anti-path-traversal: session_id e agent_id devem ser UUID-like.
    Rejeita valores contendo '..', '/', '\\', '*' — previne escapar do
    diretorio de projeto e expor JSONLs adjacentes.
    """
    if not _is_safe_id(session_id) or not _is_safe_id(agent_id):
        logger.debug(
            f"[subagent_reader] rejected path resolve — unsafe id: "
            f"session={session_id!r} agent={agent_id!r}"
        )
        return None

    # Descobre projects_dir. Ordem de precedencia:
    # 1. directory explicito (argumento)
    # 2. $CLAUDE_CONFIG_DIR (honrar SDK behavior)
    # 3. ~/.claude/projects/ (home)
    # 4. /tmp/.claude/projects/ (Render: CLI escreve aqui por default)
    if directory:
        bases = [Path(directory)]
    else:
        import os as _os
        bases = []
        if _os.environ.get('CLAUDE_CONFIG_DIR'):
            bases.append(Path(_os.environ['CLAUDE_CONFIG_DIR']) / 'projects')
        bases.append(Path.home() / '.claude' / 'projects')
        # Fallback: Render CLI escreve em /tmp/.claude/projects/ quando
        # HOME=/opt/render nao e writable pelo subprocess CLI.
        bases.append(Path('/tmp/.claude/projects'))

    for base in bases:
        try:
            if not base.exists() or not base.is_dir():
                continue
            for proj_dir in base.iterdir():
                if not proj_dir.is_dir():
                    continue
                sub_dir = proj_dir / session_id / 'subagents'
                if sub_dir.exists():
                    # agent_id ja validado como UUID-like, sem wildcards
                    for f in sub_dir.rglob(f'{agent_id}*.jsonl'):
                        return str(f)
        except (OSError, PermissionError) as e:
            logger.debug(f"[subagent_reader] base={base} inaccessible: {e}")
            continue
    return None


def _summarize_tool_call(
    block: dict,
    result_content: Optional[str] = None,
    max_chars: int = 500,
    include_pii: bool = False,
) -> dict:
    """Condensa tool_use + tool_result em entrada para SubagentSummary.tools_used."""
    name = block.get('name', 'unknown')
    input_str = json.dumps(block.get('input', {}), ensure_ascii=False)[:max_chars]
    result_str = (result_content or '')[:max_chars]

    if not include_pii:
        input_str = mask_pii(input_str)
        result_str = mask_pii(result_str)

    return {
        'name': name,
        'args_summary': input_str,
        'result_summary': result_str,
        'tool_use_id': block.get('id', ''),
    }


def get_subagent_summary(
    session_id: str,
    agent_id: str,
    agent_type: str = '',
    directory: Optional[str] = None,
    include_pii: bool = False,
    max_tool_chars: int = 500,
) -> SubagentSummary:
    """
    Le mensagens do transcript + metadata do ResultMessage e monta summary.

    Se o subagente nao for encontrado, retorna SubagentSummary com status='error'.
    """
    messages = []
    for candidate in _candidate_directories(directory):
        try:
            kwargs = {'directory': candidate} if candidate else {}
            messages = list(get_subagent_messages(
                session_id, agent_id, **kwargs
            ))
            if messages:
                break
        except Exception as e:
            logger.debug(
                f"[subagent_reader] get_subagent_messages dir={candidate}: {e}"
            )

    if not messages:
        return SubagentSummary(
            agent_id=agent_id, agent_type=agent_type, status='error',
            started_at=None, ended_at=None, duration_ms=None,
        )

    # T4b: SessionMessage do SDK 0.1.60 tem shape:
    #   SessionMessage(type, uuid, session_id, message, parent_tool_use_id)
    # onde `message` e dict Anthropic API {role, content, ...}.
    # Parser anterior acessava msg.content que NAO existe — retornava vazio.
    # FONTE: sessions.py:1005-1017 e types.py:1134-1155.
    def _extract_content_list(msg) -> list:
        """Extrai lista de content blocks da SessionMessage, tolerante a
        formatos variantes (dict Anthropic OU atributo direto content)."""
        # SDK 0.1.60: SessionMessage.message = dict Anthropic
        msg_dict = getattr(msg, 'message', None)
        if isinstance(msg_dict, dict):
            content = msg_dict.get('content')
        else:
            # Fallback: formato legacy com content direto
            content = getattr(msg, 'content', None)
        if isinstance(content, list):
            return content
        if isinstance(content, str):
            # Mensagem simples sem blocks — envolver em bloco text
            return [{'type': 'text', 'text': content}]
        return []

    # Mapeia tool_use_id -> conteudo do tool_result
    tool_results: dict[str, str] = {}
    for msg in messages:
        for block in _extract_content_list(msg):
            if isinstance(block, dict) and block.get('type') == 'tool_result':
                tid = block.get('tool_use_id', '')
                res = block.get('content', '')
                if isinstance(res, list):
                    res = ' '.join(
                        b.get('text', '') for b in res
                        if isinstance(b, dict)
                    )
                tool_results[tid] = str(res)

    # Extrai tool_calls e findings_text em ordem cronologica
    tools_used: list[dict] = []
    findings_parts: list[str] = []

    for msg in messages:
        blocks = _extract_content_list(msg)
        if not blocks:
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            btype = block.get('type')
            if btype == 'tool_use':
                tid = block.get('id', '')
                tools_used.append(_summarize_tool_call(
                    block,
                    result_content=tool_results.get(tid),
                    max_chars=max_tool_chars,
                    include_pii=include_pii,
                ))
            elif btype == 'text':
                findings_parts.append(block.get('text', ''))

    findings_text = '\n'.join(findings_parts).strip()
    if not include_pii:
        findings_text = mask_pii(findings_text)

    # Metadata: tenta ResultMessage primeiro (compat forward), fallback para
    # compute baseado em AssistantMessage.usage + timestamps (T4).
    transcript_path = _resolve_transcript_path(session_id, agent_id, directory)
    meta = _read_result_metadata(transcript_path)
    if not meta.get('cost_usd') and not meta.get('num_turns'):
        # Transcript de subagent NAO tem type:'result' (SDK 0.1.60 exclui
        # 'result' de _TRANSCRIPT_ENTRY_TYPES em sessions.py:791-794).
        # Fallback: somar usage de cada assistant message + diff timestamps.
        computed = _compute_subagent_metadata_from_jsonl(transcript_path)
        if computed.get('num_turns'):
            meta = computed

    # started_at/ended_at do JSONL (SessionMessage nao expoe timestamp)
    started_at = meta.get('started_at')
    ended_at = meta.get('ended_at')

    return SubagentSummary(
        agent_id=agent_id,
        agent_type=agent_type,
        status='done',
        started_at=started_at,
        ended_at=ended_at,
        duration_ms=meta['duration_ms'] or None,
        tools_used=tools_used,
        cost_usd=meta['cost_usd'],
        input_tokens=meta['input_tokens'],
        output_tokens=meta['output_tokens'],
        cache_read_tokens=meta['cache_read_tokens'],
        num_turns=meta['num_turns'],
        findings_text=findings_text,
        stop_reason=meta['stop_reason'],
    )


def get_session_subagents_summary(
    session_id: str,
    directory: Optional[str] = None,
    include_pii: bool = False,
) -> list[SubagentSummary]:
    """Batch helper — summary de todos os subagentes da sessao."""
    agent_ids = list_session_subagents(session_id, directory=directory)
    return [
        get_subagent_summary(session_id, aid, directory=directory,
                              include_pii=include_pii)
        for aid in agent_ids
    ]


def get_subagent_findings(
    session_id: str,
    agent_type: str,
    directory: Optional[str] = None,
) -> Optional[str]:
    """
    Retorna findings_text do subagente mais recente do agent_type na sessao.

    Usado pelo parent como alternativa canonica ao /tmp/subagent-findings/.
    Retorna None se SDK nao encontrou nada (caller deve fallback para /tmp/).
    """
    summaries = get_session_subagents_summary(session_id, directory=directory,
                                               include_pii=True)
    matching = [s for s in summaries if s.agent_type == agent_type
                and s.status == 'done']
    if not matching:
        return None
    # Mais recente primeiro (ended_at desc)
    matching.sort(key=lambda s: s.ended_at or agora_brasil_naive(), reverse=True)
    return matching[0].findings_text
