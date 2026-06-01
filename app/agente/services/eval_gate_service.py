"""
A3 (Onda 3) — Eval Runner + Gate para golden datasets de subagentes.

Avalia a qualidade de subagentes contra golden datasets YAML usando
Haiku-as-judge (injetavel) e publica um gate report-only no D8.

SEAM INJETAVEL:
    - invoke_fn: recebe user_input (str) -> agent_output (str).
      Default raise NotImplementedError (documentado: wiring real na ativacao).
    - judge_fn: recebe prompt (str) -> veredito.
      Default _call_haiku_eval_granular (BUG-1): retorna dict
      {passed_items, total_items, failing} para score parcial por item.
      Retrocompat: aceita tambem str "pass"|"fail" (judge legado). Mockavel em testes.

MODO report-only (default):
    eval_gate() NUNCA define blocked=True. Detecta regressao mas apenas loga.
    Modo 'enforce' e' para futuro — nenhum caller ativa hoje.

Ref: app/agente/workers/step_judge.py (padrao _call_haiku_judge + _parse_judge_json)
"""
import json
import logging
import os
import pathlib
import statistics
import subprocess
from typing import Callable, Optional, Union

import anthropic

logger = logging.getLogger('sistema_fretes')

# ─── Constantes ──────────────────────────────────────────────────────────────

HAIKU_MODEL = 'claude-haiku-4-5-20251001'

# BUG-1: limite de score_caso para o caso contar como 'pass' (decisao do usuario).
PASS_THRESHOLD = 0.80

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

    LEGADO (BUG-1): mantido por retrocompat. O default de run_evals migrou para
    _call_haiku_eval_granular (judge granular). NAO remover — pode estar referenciado.
    """
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


# ─── Haiku judge GRANULAR (BUG-1 — default novo) ──────────────────────────────

EVAL_JUDGE_GRANULAR_SYSTEM_PROMPT = """Voce e' um avaliador GRANULAR de qualidade de subagentes logisticos.

Dado:
- OUTPUT do agente (o que ele respondeu)
- EXPECTED_BEHAVIOR (lista de comportamentos que DEVEM ocorrer)
- MUST_NOT (lista de anti-padroes proibidos)

Sua tarefa: CONTAR quantos itens foram atendidos, item por item.

REGRAS DE CONTAGEM (criticas):
- Um item de EXPECTED_BEHAVIOR conta como ATENDIDO se a INTENCAO foi cumprida,
  MESMO com fraseado diferente. Seja TOLERANTE a comportamento equivalente OU SUPERIOR.
  (Ex: se o item pede "menciona estoque" e o agente deu o numero exato de estoque,
  o item esta ATENDIDO — comportamento superior tambem conta.)
- Um item de MUST_NOT conta como FALHO se o anti-padrao APARECER no output.
- total_items = numero de EXPECTED_BEHAVIOR + numero de MUST_NOT.
- passed_items = quantos EXPECTED_BEHAVIOR foram atendidos + quantos MUST_NOT NAO foram violados.
- failing = lista curta (texto) dos itens NAO atendidos ou violados.

Retorne EXCLUSIVAMENTE um JSON (sem markdown, sem comentarios) no formato:
{"passed_items": <int>, "total_items": <int>, "failing": [<str>, ...]}
"""


def _call_haiku_eval_granular(prompt: str) -> dict:
    """Chama Haiku com EVAL_JUDGE_GRANULAR_SYSTEM_PROMPT. Retorna dict granular.

    Returns:
        {"passed_items": int, "total_items": int, "failing": [str, ...]}.
        Best-effort: parse falho/JSON invalido -> {0, 0, ["parse_error"]}.

    Parse tolerante a prefixo/sufixo (mesmo padrao de step_judge._parse_judge_json:
    find('{')/rfind('}')). Testavel via mock de anthropic.Anthropic.
    """
    fallback = {"passed_items": 0, "total_items": 0, "failing": ["parse_error"]}

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=300,
        system=EVAL_JUDGE_GRANULAR_SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': prompt}],
    )

    raw = ''
    for block in resp.content:
        if getattr(block, 'type', None) == 'text':
            raw = block.text
            break

    parsed = _parse_granular_json(raw)
    return parsed if parsed is not None else fallback


def _parse_granular_json(raw: str) -> Optional[dict]:
    """Parseia JSON granular tolerante a prefixo/sufixo. None se invalido.

    Mesmo padrao de step_judge._parse_judge_json (find('{')/rfind('}')).
    Valida chaves obrigatorias e normaliza tipos.
    """
    if not raw:
        return None
    try:
        start = raw.find('{')
        end = raw.rfind('}')
        if start < 0 or end < 0 or end <= start:
            return None
        parsed = json.loads(raw[start:end + 1])
        if 'passed_items' not in parsed or 'total_items' not in parsed:
            return None
        passed = int(parsed.get('passed_items', 0))
        total = int(parsed.get('total_items', 0))
        failing = parsed.get('failing', [])
        if not isinstance(failing, list):
            failing = [str(failing)]
        return {
            'passed_items': passed,
            'total_items': total,
            'failing': [str(f) for f in failing],
        }
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


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
    judge_fn: Callable[[str], Union[str, dict]],
) -> dict:
    """Julga um caso individual do golden dataset (BUG-1: score granular).

    Args:
        case: Dict com id, input, expected_behavior e opcionalmente must_not.
        agent_output: Output do agente para o input do caso.
        judge_fn: Funcao que recebe prompt (str) -> veredito. Aceita DOIS formatos
                  (retrocompat inviolavel):
                  - dict {passed_items, total_items, failing} (judge granular novo)
                  - str "pass"/"fail" (judge legado, usado pelos testes existentes)
                  Injetavel para testes sem API real.

    Returns:
        Dict com {id, status: 'pass'|'fail', case_score: float, evidence}.
        - granular: case_score = passed_items/total_items (0.0 se total==0).
        - str: 'pass' -> 1.0; qualquer outro -> 0.0.
        - status = 'pass' se case_score >= PASS_THRESHOLD, senao 'fail'.
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
        case_score, evidence = _score_from_verdict(verdict)
    except Exception as e:
        logger.warning(f"[eval_gate] judge_fn falhou para caso {case_id}: {e}")
        case_score = 0.0
        evidence = str(e)[:500]

    status = 'pass' if case_score >= PASS_THRESHOLD else 'fail'

    return {
        'id': case_id,
        'status': status,
        'case_score': case_score,
        'evidence': evidence[:500],
    }


def _score_from_verdict(verdict: Union[str, dict]) -> tuple:
    """Deriva (case_score: float, evidence: str) do veredito do judge.

    Detecta o formato por tipo (BUG-1):
    - dict {passed_items, total_items, ...}: case_score = passed/total (0.0 se total==0).
    - str (retrocompat): 'pass' -> 1.0; qualquer outro -> 0.0.
    """
    if isinstance(verdict, dict):
        total = int(verdict.get('total_items', 0) or 0)
        passed = int(verdict.get('passed_items', 0) or 0)
        # HIGH-1 (code-review): cap em 1.0. O Haiku pode miscount e retornar
        # passed_items > total_items → case_score > 1.0 → media > 1.0 → baseline
        # envenenado (gate nunca dispara regressao). min() blinda contra isso.
        case_score = min(1.0, passed / total) if total > 0 else 0.0
        failing = verdict.get('failing', []) or []
        if isinstance(failing, list):
            faltou = ', '.join(str(f) for f in failing) if failing else 'nenhum'
        else:
            faltou = str(failing)
        evidence = f"{passed}/{total} itens; faltou: [{faltou}]"
        return case_score, evidence

    # Retrocompat: judge_fn legado retorna str 'pass'/'fail'
    raw = str(verdict).strip().lower()
    case_score = 1.0 if raw == 'pass' else 0.0
    return case_score, str(verdict)


# ─── run_evals ────────────────────────────────────────────────────────────────

def run_evals(
    agent_name: str,
    dataset_path: str,
    invoke_fn: Optional[Callable[[str], str]] = None,
    judge_fn: Optional[Callable[[str], Union[str, dict]]] = None,
    n_runs: int = 3,
) -> dict:
    """Roda avaliacao completa de um agente contra o golden dataset.

    Args:
        agent_name: Nome do agente (ex: 'analista-carteira').
        dataset_path: Caminho para o dataset.yaml.
        invoke_fn: SEAM — funcao que recebe user_input e retorna agent_output.
                   Default: stub que levanta NotImplementedError (documentado).
        judge_fn: Funcao de julgamento. Default: _call_haiku_eval_granular (BUG-1).
                  Aceita judge granular (dict) OU legado (str 'pass'/'fail').
        n_runs: Numero de execucoes invoke+judge POR CASO (A3-R1). LLMs sao
                nao-deterministicos (spec run_eval.md:121). Cada caso roda n_runs
                vezes e o case_score AGREGADO = MEDIANA dos runs (comportamento
                predominante, robusto a outlier). Default 3. n_runs=1 reproduz
                EXATAMENTE o comportamento single-run legado.

    Returns:
        Dict com {agent_name, score: float(0-1), total, passed, cases: [...]}.
        - score = MEDIA dos case_score (medianas) de TODOS os casos (BUG-1: granular).
        - passed = numero de casos com status=='pass' (retrocompat do campo).
        - Best-effort por RUN: um run cujo invoke falha conta case_score 0.0 SEM
          derrubar os demais runs do mesmo caso. Caso so' vira 'error' se TODOS
          os runs falharam no invoke.
        - cada cases[] ganha: case_score (= mediana), n_runs, case_score_variance
          (pvariance; sinal de flaky), runs_scores (scores individuais p/ debug).
    """
    if invoke_fn is None:
        invoke_fn = _default_invoke_fn
    if judge_fn is None:
        judge_fn = _call_haiku_eval_granular
    # Guard: n_runs >= 1 (n_runs<=0 nao faz sentido — degrada para 1 run)
    n_runs = max(1, int(n_runs))

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

        runs_scores = []        # case_score de cada run (best-effort por run)
        last_evidence = ''      # evidence do ultimo run com judge bem-sucedido
        all_invoke_failed = True
        invoke_failures = 0     # quantos runs falharam NO INVOKE (sinal de infra, nao de qualidade — caveat I2)

        for r in range(n_runs):
            # Invocar agente (best-effort POR RUN — um run ruim nao derruba os outros)
            try:
                agent_output = invoke_fn(user_input)
            except NotImplementedError as nie:
                logger.debug(
                    f"[eval_gate] invoke_fn nao implementado para {case_id} (run {r + 1}/{n_runs}): {nie}"
                )
                runs_scores.append(0.0)
                invoke_failures += 1
                last_evidence = f'invoke_fn nao implementado: {str(nie)[:200]}'
                continue
            except Exception as e:
                logger.warning(
                    f"[eval_gate] invoke_fn falhou para caso {case_id} (run {r + 1}/{n_runs}): {e}"
                )
                runs_scores.append(0.0)
                invoke_failures += 1
                last_evidence = f'invoke_fn erro: {str(e)[:200]}'
                continue

            all_invoke_failed = False

            # Julgar (best-effort)
            try:
                result_r = _judge_case(case=case, agent_output=agent_output, judge_fn=judge_fn)
                runs_scores.append(result_r['case_score'])
                last_evidence = result_r.get('evidence', '')
            except Exception as e:
                logger.warning(
                    f"[eval_gate] _judge_case falhou para {case_id} (run {r + 1}/{n_runs}): {e}"
                )
                runs_scores.append(0.0)
                last_evidence = str(e)[:200]

        # Agregacao por caso: MEDIANA (comportamento predominante, robusto a outlier)
        if runs_scores:
            case_score = statistics.median(runs_scores)
        else:
            case_score = 0.0
        # Variance: sinal de flaky (>= 2 runs). pvariance = variancia populacional.
        case_score_variance = statistics.pvariance(runs_scores) if len(runs_scores) >= 2 else 0.0

        # Status: 'error' se TODOS os runs falharam no invoke; senao pass/fail por mediana
        if all_invoke_failed:
            status = 'error'
        else:
            status = 'pass' if case_score >= PASS_THRESHOLD else 'fail'

        # Evidence: resumo informativo (mediana de N runs + variance) + ultima evidencia
        evidence = (
            f"mediana={case_score:.3f} de {len(runs_scores)} run(s), "
            f"var={case_score_variance:.4f}"
        )
        if invoke_failures:
            # Sinaliza instabilidade de INFRA (caveat I2): runs com invoke falho.
            # Distingue "agente ruim" (score baixo c/ invoke OK) de "infra instavel".
            evidence = f"{evidence}, invoke_failures={invoke_failures}/{n_runs}"
        if last_evidence:
            evidence = f"{evidence} | {last_evidence}"

        case_results.append({
            'id': case_id,
            'status': status,
            'case_score': case_score,
            'n_runs': n_runs,
            'case_score_variance': case_score_variance,
            'runs_scores': runs_scores,
            'invoke_failures': invoke_failures,
            'evidence': evidence[:500],
        })
        if status == 'pass':
            passed += 1

    total = len(case_results)
    # BUG-1: score agregado = media dos case_score (medianas; casos 'error' = 0.0).
    case_scores = [c.get('case_score', 0.0) for c in case_results]
    score = (sum(case_scores) / total) if total > 0 else 0.0

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
