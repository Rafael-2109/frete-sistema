"""
A3 (Onda 3) — Eval Runner + Gate para golden datasets de subagentes.

Avalia a qualidade de subagentes contra golden datasets YAML usando
Haiku-as-judge (injetavel) e publica um gate report-only no D8.

SEAM INJETAVEL:
    - invoke_fn: recebe user_input (str) -> agent_output (str).
      Default raise NotImplementedError (documentado: wiring real na ativacao).
    - judge_fn: recebe prompt (str) -> "pass"|"fail".
      Default _call_haiku_eval (mockavel em testes).

MODO report-only (default):
    eval_gate() NUNCA define blocked=True. Detecta regressao mas apenas loga.
    Modo 'enforce' e' para futuro — nenhum caller ativa hoje.

Ref: app/agente/workers/step_judge.py (padrao _call_haiku_judge + _parse_judge_json)
"""
import logging
import os
import pathlib
import subprocess
from typing import Callable, Optional

logger = logging.getLogger('sistema_fretes')

# ─── Constantes ──────────────────────────────────────────────────────────────

HAIKU_MODEL = 'claude-haiku-4-5-20251001'

EVAL_JUDGE_SYSTEM_PROMPT = """Voce e' um avaliador de qualidade de subagentes logisticos.

Dado:
- OUTPUT do agente (o que ele respondeu)
- EXPECTED_BEHAVIOR (lista de comportamentos que DEVEM ocorrer)
- MUST_NOT (lista de anti-padroes proibidos)

Retorne EXCLUSIVAMENTE uma das palavras: "pass" ou "fail"

Criterio:
- "pass": TODOS os expected_behavior presentes E NENHUM must_not violado.
- "fail": qualquer expected_behavior ausente OU qualquer must_not presente.
"""


# ─── Haiku judge (default — mockavel em testes) ───────────────────────────────

def _call_haiku_eval(prompt: str) -> str:
    """Chama Haiku com EVAL_JUDGE_SYSTEM_PROMPT. Retorna 'pass' ou 'fail'.

    Testavel via mock (mesmo padrao de step_judge._call_haiku_judge).
    """
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=10,
        system=EVAL_JUDGE_SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': prompt}],
    )
    for block in resp.content:
        if getattr(block, 'type', None) == 'text':
            raw = block.text.strip().lower()
            if 'pass' in raw:
                return 'pass'
            return 'fail'
    return 'fail'


# ─── Invoke stub (default — documentado: wiring real na ativacao) ─────────────

def _default_invoke_fn(user_input: str) -> str:  # pragma: no cover
    """Stub do invoke_fn. Levanta NotImplementedError.

    O SEAM injetavel (invoke_fn) e' o mecanismo que permite testar o runner
    sem API real. Em producao, ao ativar A3 completamente, este default sera'
    substituido pelo wiring real do harness SDK do agente.

    Mensagem de erro documentada: qualquer caller que esqueca de passar invoke_fn
    vera' imediatamente esta mensagem clara.
    """
    raise NotImplementedError(
        "invoke_fn nao configurado: wiring real do agente na ativacao. "
        "Para testes, passe um mock como invoke_fn=lambda x: 'output'."
    )


# ─── build_subprocess_invoke_fn (wiring REAL — A3 Fase 1, 3b) ────────────────

# Raiz do repositorio (worktree): eval_gate_service.py vive em
# app/agente/services/ → subir 4 niveis chega na raiz (onde roda `claude -p`).
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent


def build_subprocess_invoke_fn(
    agent_name: str,
    model: Optional[str] = None,
    timeout: int = 120,
    project_dir: Optional[str] = None,
) -> Callable[[str], str]:
    """Constroi o invoke_fn REAL que roda o subagente via `claude -p`.

    Retorna uma closure(user_input: str) -> agent_output: str que executa:
        claude -p --agent <agent_name> --permission-mode bypassPermissions
               [--model <model>] <user_input>

    no cwd da raiz do repo (project_dir override) e captura stdout.

    Comportamento de erro (ambos viram caso 'error' no run_evals, sem
    interromper os demais casos — best-effort INV-6):
    - returncode != 0  -> raise RuntimeError(f"claude -p rc={rc}: {stderr[:300]}")
    - subprocess.TimeoutExpired -> propaga (run_evals trata como caso 'error')

    Args:
        agent_name: Nome do subagente (ex: 'analista-carteira').
        model: Modelo opcional (--model). None → CLI usa o default.
        timeout: Timeout por invocacao em segundos (default 120).
        project_dir: cwd para o subprocess. Default: raiz do repo.

    Returns:
        Callable[[str], str] — a closure injetavel como invoke_fn de run_evals.
    """
    cwd = project_dir or str(_REPO_ROOT)

    def _invoke(user_input: str) -> str:
        cmd = [
            'claude', '-p',
            '--agent', agent_name,
            '--permission-mode', 'bypassPermissions',
        ]
        if model:
            cmd += ['--model', model]
        cmd.append(user_input)

        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ},
        )
        if result.returncode != 0:
            stderr = (result.stderr or '')[:300]
            raise RuntimeError(f"claude -p rc={result.returncode}: {stderr}")
        return (result.stdout or '').strip()

    return _invoke


# ─── load_golden_dataset ──────────────────────────────────────────────────────

def load_golden_dataset(path: str) -> list[dict]:
    """Le dataset YAML do golden set de um subagente.

    Args:
        path: Caminho absoluto para o arquivo dataset.yaml

    Returns:
        Lista de casos (cada caso e' um dict com id, input, expected_behavior, ...).
        Retorna [] se o arquivo nao existir ou falhar a parse (tolerante).
    """
    try:
        import yaml
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        if not data or 'cases' not in data:
            return []
        cases = data['cases']
        if not isinstance(cases, list):
            return []
        return cases
    except FileNotFoundError:
        logger.debug(f"[eval_gate] Dataset nao encontrado: {path}")
        return []
    except Exception as e:
        logger.warning(f"[eval_gate] Falha ao carregar dataset {path}: {e}")
        return []


# ─── _judge_case ─────────────────────────────────────────────────────────────

def _judge_case(
    case: dict,
    agent_output: str,
    judge_fn: Callable[[str], str],
) -> dict:
    """Julga um caso individual do golden dataset.

    Args:
        case: Dict com id, input, expected_behavior e opcionalmente must_not.
        agent_output: Output do agente para o input do caso.
        judge_fn: Funcao que recebe prompt (str) -> "pass"|"fail".
                  Injetavel para testes sem API real.

    Returns:
        Dict com {id, status: 'pass'|'fail', evidence}
    """
    case_id = case.get('id', 'unknown')
    expected = case.get('expected_behavior', [])
    must_not = case.get('must_not', [])

    # Montar prompt para o judge
    prompt_parts = [
        f"## OUTPUT DO AGENTE:\n{agent_output[:3000]}",
        f"\n## EXPECTED_BEHAVIOR (devem ocorrer):",
    ]
    for item in expected:
        prompt_parts.append(f"- {item}")

    if must_not:
        prompt_parts.append("\n## MUST_NOT (nao devem ocorrer):")
        for item in must_not:
            prompt_parts.append(f"- {item}")

    prompt = "\n".join(prompt_parts)

    try:
        verdict = judge_fn(prompt)
        status = 'pass' if str(verdict).strip().lower() == 'pass' else 'fail'
    except Exception as e:
        logger.warning(f"[eval_gate] judge_fn falhou para caso {case_id}: {e}")
        status = 'fail'
        verdict = str(e)

    return {
        'id': case_id,
        'status': status,
        'evidence': str(verdict)[:500],
    }


# ─── run_evals ────────────────────────────────────────────────────────────────

def run_evals(
    agent_name: str,
    dataset_path: str,
    invoke_fn: Optional[Callable[[str], str]] = None,
    judge_fn: Optional[Callable[[str], str]] = None,
) -> dict:
    """Roda avaliacao completa de um agente contra o golden dataset.

    Args:
        agent_name: Nome do agente (ex: 'analista-carteira').
        dataset_path: Caminho para o dataset.yaml.
        invoke_fn: SEAM — funcao que recebe user_input e retorna agent_output.
                   Default: stub que levanta NotImplementedError (documentado).
        judge_fn: Funcao de julgamento. Default: _call_haiku_eval.

    Returns:
        Dict com {agent_name, score: float(0-1), total, passed, cases: [...]}.
        Best-effort: casos com erro sao contados como fail.
    """
    if invoke_fn is None:
        invoke_fn = _default_invoke_fn
    if judge_fn is None:
        judge_fn = _call_haiku_eval

    cases = load_golden_dataset(dataset_path)
    if not cases:
        return {
            'agent_name': agent_name,
            'score': 0.0,
            'total': 0,
            'passed': 0,
            'cases': [],
        }

    case_results = []
    passed = 0

    for case in cases:
        case_id = case.get('id', 'unknown')
        user_input = case.get('input', '')

        # Invocar agente (best-effort — erro de invoke nao interrompe demais casos)
        try:
            agent_output = invoke_fn(user_input)
        except NotImplementedError as nie:
            logger.debug(f"[eval_gate] invoke_fn nao implementado para {case_id}: {nie}")
            case_results.append({
                'id': case_id,
                'status': 'error',
                'evidence': f'invoke_fn nao implementado: {str(nie)[:200]}',
            })
            continue
        except Exception as e:
            logger.warning(f"[eval_gate] invoke_fn falhou para caso {case_id}: {e}")
            case_results.append({
                'id': case_id,
                'status': 'error',
                'evidence': f'invoke_fn erro: {str(e)[:200]}',
            })
            continue

        # Julgar (best-effort)
        try:
            result = _judge_case(case=case, agent_output=agent_output, judge_fn=judge_fn)
        except Exception as e:
            logger.warning(f"[eval_gate] _judge_case falhou para {case_id}: {e}")
            result = {'id': case_id, 'status': 'error', 'evidence': str(e)[:200]}

        case_results.append(result)
        if result['status'] == 'pass':
            passed += 1

    total = len(case_results)
    score = passed / total if total > 0 else 0.0

    return {
        'agent_name': agent_name,
        'score': score,
        'total': total,
        'passed': passed,
        'cases': case_results,
    }


# ─── eval_gate ────────────────────────────────────────────────────────────────

def eval_gate(
    baseline_score: float,
    candidate_score: float,
    threshold: float = 0.05,
    mode: str = 'report_only',
) -> dict:
    """Compara score candidate vs baseline e decide se bloqueia (gate).

    Args:
        baseline_score: Score de referencia (0-1).
        candidate_score: Score do candidato a avaliar (0-1).
        threshold: Queda minima para ser considerada regressao (default 0.05).
        mode: 'report_only' (default) ou 'enforce'.
            - 'report_only': blocked=False SEMPRE. So' detecta e loga.
            - 'enforce': blocked=True se candidate < baseline - threshold.

    Returns:
        Dict com {regression: bool, blocked: bool, delta: float}

    INVARIANTE: Em mode='report_only', blocked e' SEMPRE False.
    """
    delta = candidate_score - baseline_score
    regression = delta < -threshold

    if mode == 'enforce':
        blocked = regression
    else:
        # report_only (default e qualquer outro valor): NUNCA bloqueia
        blocked = False

    if regression:
        logger.warning(
            f"[eval_gate] REGRESSAO DETECTADA: "
            f"baseline={baseline_score:.3f} candidate={candidate_score:.3f} "
            f"delta={delta:+.3f} threshold={threshold:.3f} "
            f"mode={mode} blocked={blocked}"
        )
    else:
        logger.info(
            f"[eval_gate] Gate OK: "
            f"baseline={baseline_score:.3f} candidate={candidate_score:.3f} "
            f"delta={delta:+.3f}"
        )

    return {
        'regression': regression,
        'blocked': blocked,
        'delta': delta,
    }
