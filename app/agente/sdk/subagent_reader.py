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
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from claude_agent_sdk import get_subagent_messages, list_subagents

from app.agente.utils.pii_masker import mask_pii
from app.utils.timezone import agora_brasil_naive

logger = logging.getLogger('sistema_fretes')

Status = Literal['running', 'done', 'error']


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


def list_session_subagents(
    session_id: str,
    directory: Optional[str] = None,
) -> list[str]:
    """Wrapper de list_subagents(). Retorna lista de agent_ids."""
    try:
        return list(list_subagents(session_id, directory=directory))
    except Exception as e:
        logger.debug(f"[subagent_reader] list_subagents falhou: {e}")
        return []


def _read_result_metadata(transcript_path: Optional[str]) -> dict:
    """
    Parseia a ultima ResultMessage do JSONL para extrair cost/tokens/duration.

    Retorna dict com: cost_usd, duration_ms, num_turns, input_tokens,
    output_tokens, cache_read_tokens, stop_reason. Campos ausentes = 0.
    """
    default = {
        'cost_usd': 0.0, 'duration_ms': 0, 'num_turns': 0,
        'input_tokens': 0, 'output_tokens': 0, 'cache_read_tokens': 0,
        'stop_reason': None,
    }
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
            'cost_usd': last_result.get('total_cost_usd') or 0.0,
            'duration_ms': last_result.get('duration_ms') or 0,
            'num_turns': last_result.get('num_turns') or 0,
            'input_tokens': usage.get('input_tokens') or 0,
            'output_tokens': usage.get('output_tokens') or 0,
            'cache_read_tokens': usage.get('cache_read_input_tokens') or 0,
            'stop_reason': last_result.get('stop_reason'),
        }
    except (OSError, IOError) as e:
        logger.debug(f"[subagent_reader] transcript inacessivel: {e}")
        return default


def _resolve_transcript_path(
    session_id: str,
    agent_id: str,
    directory: Optional[str] = None,
) -> Optional[str]:
    """Resolve caminho do JSONL do subagente em ~/.claude/projects/.../subagents/."""
    base = Path(directory) if directory else Path.home() / '.claude' / 'projects'
    if directory is None:
        # Busca cross-project (SDK default behavior)
        for proj_dir in base.iterdir():
            if not proj_dir.is_dir():
                continue
            sub_dir = proj_dir / session_id / 'subagents'
            if sub_dir.exists():
                for f in sub_dir.rglob(f'{agent_id}*.jsonl'):
                    return str(f)
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
    try:
        messages = list(get_subagent_messages(session_id, agent_id,
                                               directory=directory))
    except Exception as e:
        logger.debug(f"[subagent_reader] get_subagent_messages falhou: {e}")
        messages = []

    if not messages:
        return SubagentSummary(
            agent_id=agent_id, agent_type=agent_type, status='error',
            started_at=None, ended_at=None, duration_ms=None,
        )

    # Mapeia tool_use_id -> conteudo do tool_result
    tool_results: dict[str, str] = {}
    for msg in messages:
        content = getattr(msg, 'content', None)
        if isinstance(content, list):
            for block in content:
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
        content = getattr(msg, 'content', None)
        if not isinstance(content, list):
            if isinstance(content, str):
                findings_parts.append(content)
            continue
        for block in content:
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

    # Metadata do ResultMessage
    transcript_path = _resolve_transcript_path(session_id, agent_id, directory)
    meta = _read_result_metadata(transcript_path)

    started_at = getattr(messages[0], 'timestamp', None)
    ended_at = getattr(messages[-1], 'timestamp', None)

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
