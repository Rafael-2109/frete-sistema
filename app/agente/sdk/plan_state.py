"""
B1 — Onda 2: PlanState durável.
B3 — Onda 2: replan + budget + escalate.

Captura eventos TaskCreate/TaskUpdate e persiste em AgentSession.data['plan'].
Classe pura (sem DB), determinística, tolerante a eventos inválidos.

Uso:
    ps = PlanState()
    ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '1', 'subject': 'consultar X'})
    ps.apply_task_event({'tool': 'TaskUpdate', 'taskId': '1', 'status': 'completed'})
    plan_dict = ps.to_dict()  # {'steps': {'1': {'subject': 'consultar X', 'status': 'completed'}}}

    # Roundtrip
    ps2 = PlanState.from_dict(plan_dict)

    # Replan / escalate (B3)
    ps.mark_step_failed('1')               # failures++ + status='failed'
    ps.should_escalate(max_retries=2)      # True se algum step > max_retries
    ps.steps_to_retry(max_retries=2)       # IDs de steps falhos dentro do budget

Integração (wiring em chat.py):
    Sob USE_AGENT_PLANNER, os task_events acumulados em response_state['task_events']
    são processados no final do turno e persistidos em session.data['plan'].

Flag:
    USE_AGENT_PLANNER=false (default) — zero writes em data['plan'].
    USE_AGENT_PLANNER=true  — ativa acumulação + persistência.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


# Tools que modificam estado (write). TaskGet/TaskList sao read-only -> no-op
# por fall-through (apply_task_event so trata as de escrita).
_WRITE_TOOLS = frozenset({'TaskCreate', 'TaskUpdate'})


class PlanState:
    """
    Representa o plano de execução de um turno do agente.

    steps: dict[taskId → {subject, status, description, ...}]

    Regras:
    - TaskCreate: cria step com subject/description/status='pending'
    - TaskUpdate: merge parcial (só sobrescreve campos fornecidos); upsert se
      taskId não existe
    - TaskGet / TaskList: no-op (read-only)
    - Qualquer outro tool: no-op
    - Evento sem 'tool' ou 'taskId' quando necessário: no-op sem exceção
    """

    def __init__(self) -> None:
        # taskId (str) → dict de campos
        self.steps: Dict[str, Dict[str, Any]] = {}

    # ──────────────────────────────────────────────
    # Mutação
    # ──────────────────────────────────────────────

    def apply_task_event(self, event: dict) -> None:
        """
        Aplica um evento de Task ao estado do plano.

        Aceita dois formatos:
        1. Formato spec (tests/wiring direto):
               {'tool': 'TaskCreate', 'taskId': '1', 'subject': '...'}
               {'tool': 'TaskUpdate', 'taskId': '1', 'status': 'completed'}

        2. Formato SSE _build_task_event (wiring via task_event stream):
               {'action': 'created', 'task_id': '1', 'subject': '...'}
               {'action': 'updated', 'task_id': '1', 'status': 'completed'}
               {'action': 'snapshot', 'tasks': [...]}  → no-op (snapshot read)

        Args:
            event: dict com campos de task event.

        Returns:
            None. Qualquer evento inválido é tratado como no-op silencioso.
        """
        if not event or not isinstance(event, dict):
            return

        # Normalizar para formato interno: tool + taskId
        tool, task_id = self._normalize_event(event)

        # No-op para tools read-only ou desconhecidas
        if tool not in _WRITE_TOOLS:
            return

        if not task_id:
            return

        if tool == 'TaskCreate':
            self._apply_create(task_id, event)
        elif tool == 'TaskUpdate':
            self._apply_update(task_id, event)

    def _normalize_event(self, event: dict):
        """
        Normaliza evento para (tool, task_id) independente do formato de entrada.

        Formato spec:   event['tool']   + event['taskId'] / event['task_id']
        Formato SSE:    event['action'] + event['task_id']
        """
        # Formato spec (tool explícito)
        tool = event.get('tool', '')
        if tool:
            task_id = str(event.get('taskId') or event.get('task_id') or '').strip()
            return tool, task_id

        # Formato SSE (action → mapeia para tool)
        action = event.get('action', '')
        _ACTION_TO_TOOL = {
            'created': 'TaskCreate',
            'updated': 'TaskUpdate',
            'snapshot': 'TaskList',  # no-op
        }
        tool = _ACTION_TO_TOOL.get(action, '')
        task_id = str(event.get('task_id') or event.get('taskId') or '').strip()
        return tool, task_id

    def _apply_create(self, task_id: str, event: dict) -> None:
        """Cria step; se já existe, não sobrescreve (idempotente)."""
        if task_id in self.steps:
            return
        self.steps[task_id] = {
            'subject': event.get('subject') or event.get('content') or '',
            'description': event.get('description', ''),
            'status': event.get('status', 'pending'),
        }
        # Campos extras opcionais do SDK (ex: activeForm)
        for extra_key in ('activeForm',):
            if extra_key in event:
                self.steps[task_id][extra_key] = event[extra_key]

    def _apply_update(self, task_id: str, event: dict) -> None:
        """Merge parcial; cria o step se não existir (upsert)."""
        if task_id not in self.steps:
            self.steps[task_id] = {}

        # Campos permitidos para update
        _UPDATE_FIELDS = ('subject', 'status', 'description', 'activeForm', 'content')
        for field in _UPDATE_FIELDS:
            if field in event:
                value = event[field]
                # 'content' é alias de 'subject' no SDK em alguns contextos
                target = 'subject' if field == 'content' else field
                self.steps[task_id][target] = value

    # ──────────────────────────────────────────────
    # Serialização
    # ──────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializa para dict JSON-safe.

        Returns:
            {'steps': {taskId: {subject, status, description, ...}}}
        """
        return {
            'steps': {
                task_id: dict(step)
                for task_id, step in self.steps.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> 'PlanState':
        """
        Desserializa de dict (ex: carregado do JSONB).

        Tolerante: dict vazio ou None retorna PlanState sem steps.
        """
        ps = cls()
        if not data or not isinstance(data, dict):
            return ps
        steps = data.get('steps', {})
        if isinstance(steps, dict):
            for task_id, step in steps.items():
                if isinstance(step, dict):
                    ps.steps[str(task_id)] = dict(step)
        return ps

    # ──────────────────────────────────────────────
    # Replan / Escalate (B3)
    # ──────────────────────────────────────────────

    def mark_step_failed(self, task_id: str) -> None:
        """
        Marca um step como falho, incrementando o contador de falhas.

        - Se o step não existe, cria-o (upsert defensivo).
        - Incrementa step['failures'] (inicia em 0).
        - Seta status='failed'.

        Args:
            task_id: ID do step que falhou.
        """
        if task_id not in self.steps:
            self.steps[task_id] = {}
        step = self.steps[task_id]
        step['failures'] = step.get('failures', 0) + 1
        step['status'] = 'failed'

    def should_escalate(self, max_retries: int = 2) -> bool:
        """
        Retorna True se algum step superou o budget de retentativas.

        Um step está "fora do budget" quando failures > max_retries.
        Isso significa que foi tentado (max_retries + 1) vezes ou mais.

        Args:
            max_retries: número máximo de falhas permitidas antes de escalar.
                         Default=2 (tolera até 2 falhas; na 3ª, escala).

        Returns:
            True se deve escalar (algum step esgotou o budget), False caso contrário.
        """
        for step in self.steps.values():
            if step.get('failures', 0) > max_retries:
                return True
        return False

    def steps_to_retry(self, max_retries: int = 2) -> list:
        """
        Retorna lista de task_ids que falharam mas ainda estão dentro do budget.

        "Dentro do budget" = failures > 0 AND failures <= max_retries.
        Steps que excederam o budget (failures > max_retries) devem ser escalados,
        não retried — portanto NÃO aparecem nesta lista.

        Args:
            max_retries: número máximo de falhas permitidas antes de escalar.

        Returns:
            Lista de task_ids que precisam de replan/retry.
        """
        return [
            task_id
            for task_id, step in self.steps.items()
            if 0 < step.get('failures', 0) <= max_retries
        ]

    # ──────────────────────────────────────────────
    # Utilidades
    # ──────────────────────────────────────────────

    def is_empty(self) -> bool:
        """True se não há steps registrados."""
        return not self.steps

    def __repr__(self) -> str:
        return f"PlanState(steps={len(self.steps)})"
