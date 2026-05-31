"""
B-TRIAGE — Classificador semântico meta→steps (Onda 2).

Dado um texto de meta do usuário, decompõe em steps de plano ANCORADOS em
entidades reais do KG (ontologia canônica via query_ontology_entities).

SHADOW: esta função existe para shadow/teste. Nenhum caller ativo.
O wiring futuro (sob USE_AGENT_PLANNER, já existente e OFF) alimentaria
o PlanState com os steps retornados.

NÃO é o model_router (que faz downgrade de modelo por regex — o inverso disto).

Uso:
    result = triage_meta("Ver pedidos do Atacadao em aberto", user_id=42)
    # {'steps': [{'subject': 'Consultar pedidos...', 'entities': [...]}, ...],
    #  'grounded_entities': [{'entity_type': 'cliente', ...}]}

    # Degrada gracioso: meta vazia, LLM falha, ontologia falha → vazio sem raise.

Dependências (read-only, sem escrita no DB):
    - query_ontology_entities (D4): busca entidades canônicas no KG.
    - PlanState (B1): a saída de triage_meta alimentaria steps via
      apply_task_event({'tool': 'TaskCreate', 'taskId': ..., 'subject': ...}).
      (wiring futuro, não implementado aqui — SHADOW)

Padrão clonado de: app/agente/sdk/verifiers.py + app/agente/workers/step_judge.py
"""

import json
import logging
import re
from typing import Optional

logger = logging.getLogger('sistema_fretes')

# Importar query_ontology_entities para uso interno e para permitir mock nos testes.
# Importação no nível de módulo permite monkeypatch direto em plan_triage.query_ontology_entities.
from app.agente.tools.ontology_query_tool import query_ontology_entities  # noqa: E402

# Modelos disponíveis (mesmo padrão dos outros módulos)
_HAIKU_MODEL = 'claude-haiku-4-5-20251001'

# Número máximo de termos extraídos da meta para consulta à ontologia
_MAX_TERMOS_CANDIDATOS = 5

# Número máximo de entidades ancoradas retornadas
_MAX_ENTIDADES_GROUNDED = 10

_TRIAGE_SYSTEM_PROMPT = (
    "Você é um classificador semântico de metas logísticas. "
    "Dado um texto de meta do usuário, decomponha em passos de plano sequenciais.\n\n"
    "Regras:\n"
    "  - Cada passo deve ser autocontido e acionável.\n"
    "  - Use linguagem objetiva (verbo + objeto).\n"
    "  - Se a meta é simples (1 ação), retorne 1 passo.\n"
    "  - Máximo 5 passos por meta.\n"
    "  - Inclua 'entities' com nomes de entidades mencionadas (pode ser lista vazia).\n\n"
    "Retorne EXCLUSIVAMENTE JSON válido:\n"
    '{"steps": [{"subject": "descrição do passo", "entities": ["nome1", "nome2"]}, ...]}'
)


# =====================================================================
# CAMADA LLM (mockável — mesmo padrão de _call_haiku_judge / _call_sonnet_verifier)
# =====================================================================

def _call_llm_triage(prompt: str) -> str:
    """Chama Haiku com TRIAGE_SYSTEM_PROMPT e retorna texto da resposta.

    Extraído como helper independente para facilitar mock nos testes
    (mesmo padrão de step_judge._call_haiku_judge e verifiers._call_sonnet_verifier).

    Args:
        prompt: Texto do usuário a ser enviado ao LLM (meta + entidades ancoradas).

    Returns:
        Texto da resposta do LLM. String vazia se nenhum bloco de texto retornado.
    """
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=_HAIKU_MODEL,
        max_tokens=600,
        system=_TRIAGE_SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': prompt}],
    )
    for block in resp.content:
        if getattr(block, 'type', None) == 'text':
            return block.text
    return ''


# =====================================================================
# PARSER (tolerante a prefixos/sufixos — mesmo padrão de _parse_judge_json)
# =====================================================================

def _parse_triage_json(raw: Optional[str]) -> Optional[dict]:
    """Parseia JSON tolerante a prefixos/sufixos. Retorna None se inválido ou sem 'steps'.

    Args:
        raw: String retornada pelo LLM. Pode conter texto antes/depois do JSON.

    Returns:
        Dict com chave 'steps' (lista), ou None se inválido.
    """
    if not raw:
        return None
    try:
        start = raw.find('{')
        end = raw.rfind('}')
        if start < 0 or end < 0 or end <= start:
            return None
        parsed = json.loads(raw[start:end + 1])
        # Validar chave obrigatória
        if 'steps' not in parsed or not isinstance(parsed['steps'], list):
            return None
        return parsed
    except (ValueError, json.JSONDecodeError):
        return None


# =====================================================================
# EXTRAÇÃO DE TERMOS (heurística leve, sem LLM)
# =====================================================================

def _extrair_termos_candidatos(meta_text: str) -> list[str]:
    """Extrai termos candidatos da meta para busca na ontologia.

    Heurística simples: palavras com >= 3 chars, sem stopwords comuns.
    Best-effort: pode retornar lista vazia sem erro.

    Args:
        meta_text: Texto da meta do usuário.

    Returns:
        Lista de termos candidatos (até _MAX_TERMOS_CANDIDATOS).
    """
    _STOPWORDS = frozenset({
        'de', 'do', 'da', 'dos', 'das', 'um', 'uma', 'uns', 'umas',
        'que', 'em', 'no', 'na', 'nos', 'nas', 'por', 'para', 'com',
        'sem', 'ate', 'ou', 'e', 'a', 'o', 'os', 'as', 'se', 'me',
        'te', 'nos', 'lhe', 'isso', 'este', 'esta', 'esse', 'essa',
        'ver', 'quero', 'preciso', 'favor', 'todos', 'todas', 'todo',
        'toda', 'meu', 'minha', 'seu', 'sua',
    })
    palavras = re.findall(r'[a-zA-ZÀ-ÿ]{3,}', meta_text)
    candidatos = [
        p.lower() for p in palavras
        if p.lower() not in _STOPWORDS
    ]
    # Deduplicar mantendo ordem
    vistos = set()
    resultado = []
    for c in candidatos:
        if c not in vistos:
            vistos.add(c)
            resultado.append(c)
    return resultado[:_MAX_TERMOS_CANDIDATOS]


# =====================================================================
# FUNÇÃO PRINCIPAL
# =====================================================================

def triage_meta(meta_text: Optional[str], user_id: int) -> dict:
    """Classifica semânticamente uma meta do usuário em steps de plano ancorados.

    Fluxo:
        1. Guard: meta vazia → retorna vazio sem chamar nada.
        2. (best-effort) Extrai termos candidatos da meta → chama query_ontology_entities
           para achar entidades reais no KG relacionadas (ground).
        3. Monta prompt incluindo a meta + entidades ancoradas.
        4. Chama _call_llm_triage → parseia JSON.
        5. Retorna {'steps': [...], 'grounded_entities': [...]}.

    Degradação gracioso (best-effort total):
        - Se query_ontology_entities falha → grounded_entities=[] (steps ainda tentados).
        - Se _call_llm_triage falha → {'steps': [], 'grounded_entities': []}.
        - Se JSON inválido → {'steps': [], 'grounded_entities': []}.
        - NUNCA propaga exceção.

    Args:
        meta_text: Texto da meta do usuário (ex: "Ver pedidos do Atacadao em aberto").
        user_id: ID do usuário para consulta à ontologia (inclui user_id=0 automaticamente).

    Returns:
        Dict com:
            - 'steps': lista de {'subject': str, 'entities': list[str], ...}
            - 'grounded_entities': lista de entidades encontradas na ontologia

    Notes:
        SHADOW: nenhum caller ativo. O wiring futuro (sob USE_AGENT_PLANNER,
        OFF por default em feature_flags.py) alimentaria o PlanState via:
            for i, step in enumerate(result['steps']):
                ps.apply_task_event({
                    'tool': 'TaskCreate',
                    'taskId': str(i),
                    'subject': step['subject'],
                })
        READ-ONLY: não escreve no DB. Apenas consulta ontologia + LLM.
    """
    _VAZIO = {'steps': [], 'grounded_entities': []}

    # Guard: meta vazia → sem custo, sem I/O
    if not meta_text or not meta_text.strip():
        return _VAZIO

    # ── Passo 1: ancoragem na ontologia (best-effort) ──────────────────
    grounded_entities: list[dict] = []
    try:
        termos = _extrair_termos_candidatos(meta_text)
        # Busca entidades para cada termo candidato (até o primeiro que retorna resultado)
        # Estratégia conservadora: une resultados de até 2 termos mais relevantes
        entidades_set: dict[str, dict] = {}  # entity_key ou entity_name → dict
        for termo in termos[:2]:
            encontradas = query_ontology_entities(
                user_id=user_id,
                name_like=termo,
                limit=5,
            )
            for ent in encontradas:
                chave = ent.get('entity_key') or ent.get('entity_name', '')
                if chave and chave not in entidades_set:
                    entidades_set[chave] = ent
        grounded_entities = list(entidades_set.values())[:_MAX_ENTIDADES_GROUNDED]
    except Exception as e:
        logger.debug(
            '[plan_triage] query_ontology_entities falhou (best-effort): %s', e
        )
        grounded_entities = []

    # ── Passo 2: montar prompt com meta + entidades ancoradas ──────────
    entidades_txt = ''
    if grounded_entities:
        linhas = [
            f"  - [{e.get('entity_type', '?')}] {e.get('entity_name', '')} "
            f"(key={e.get('entity_key', 'N/A')})"
            for e in grounded_entities
        ]
        entidades_txt = (
            '\n\nEntidades identificadas no sistema (use para ancorar os passos):\n'
            + '\n'.join(linhas)
        )

    prompt = f"Meta do usuário:\n{meta_text.strip()}{entidades_txt}"

    # ── Passo 3: chamar LLM e parsear ────────────────────────────────
    try:
        raw = _call_llm_triage(prompt)
    except Exception as e:
        logger.error('[plan_triage] _call_llm_triage falhou: %s', e)
        return _VAZIO

    parsed = _parse_triage_json(raw)
    if parsed is None:
        logger.warning('[plan_triage] JSON inválido retornado pelo LLM: %s', (raw or '')[:200])
        return _VAZIO

    steps = parsed.get('steps', [])
    if not isinstance(steps, list):
        steps = []

    # Normalizar steps: garantir que cada step tem pelo menos 'subject'
    steps_normalizados = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        subject = str(step.get('subject', '')).strip()
        if not subject:
            continue
        steps_normalizados.append({
            'subject': subject,
            'entities': step.get('entities', []) if isinstance(step.get('entities'), list) else [],
        })

    return {
        'steps': steps_normalizados,
        'grounded_entities': grounded_entities,
    }
