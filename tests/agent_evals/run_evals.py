#!/usr/bin/env python3
"""
Framework de avaliação de capabilities do agente logístico.

Envia tasks definidas em tasks.json via API do agente e avalia
as respostas usando graders code-based e model-based.

Uso:
    # Executar todas as tasks (requer servidor Flask rodando)
    python tests/agent_evals/run_evals.py

    # Executar apenas uma categoria
    python tests/agent_evals/run_evals.py --category consulta_basica

    # Executar uma task específica
    python tests/agent_evals/run_evals.py --task CB-001

    # Modo dry-run (apenas valida tasks.json)
    python tests/agent_evals/run_evals.py --dry-run

    # Salvar resultado em arquivo
    python tests/agent_evals/run_evals.py --output results.json

Requisitos:
    - Servidor Flask rodando em localhost:5000 (ou URL configurável)
    - Usuário autenticado (login via sessão)
    - ANTHROPIC_API_KEY configurada (para grader model-based)
"""

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# Adicionar root do projeto ao path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


# =============================================================================
# Dataclasses
# =============================================================================

@dataclass
class EvalResult:
    """Resultado de avaliação de uma task."""
    task_id: str
    task_name: str
    category: str
    prompt: str
    response_text: str
    passed: bool
    score: float  # 0.0 a 1.0
    grading_type: str  # "keywords" ou "model"
    grading_details: dict = field(default_factory=dict)
    tools_used: list = field(default_factory=list)
    elapsed_seconds: float = 0.0
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class EvalReport:
    """Relatório completo de avaliação."""
    total_tasks: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    pass_rate: float = 0.0
    avg_score: float = 0.0
    avg_latency_seconds: float = 0.0
    by_category: dict = field(default_factory=dict)
    results: list = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_seconds: float = 0.0


# =============================================================================
# Graders
# =============================================================================

def grade_keywords(response_text: str, grading_config: dict) -> tuple[bool, float, dict]:
    """
    Grader baseado em keywords.

    Verifica:
    - required_any: pelo menos uma keyword deve estar presente
    - required_none: NENHUMA dessas keywords pode estar presente
    - forbidden: keywords que NÃO devem aparecer

    Returns:
        (passed, score, details)
    """
    text_lower = response_text.lower()
    details = {}

    # required_any: pelo menos uma deve existir
    required_any = grading_config.get("required_any", [])
    found_required = [kw for kw in required_any if kw.lower() in text_lower]
    details["required_any"] = {
        "expected": required_any,
        "found": found_required,
    }
    has_required = len(found_required) > 0 if required_any else True

    # required_none: NENHUMA pode existir
    required_none = grading_config.get("required_none", [])
    found_forbidden_strict = [kw for kw in required_none if kw.lower() in text_lower]
    details["required_none"] = {
        "expected_absent": required_none,
        "found_present": found_forbidden_strict,
    }
    none_clean = len(found_forbidden_strict) == 0

    # forbidden: keywords proibidas
    forbidden = grading_config.get("forbidden", [])
    found_forbidden = [kw for kw in forbidden if kw.lower() in text_lower]
    details["forbidden"] = {
        "forbidden_keywords": forbidden,
        "found": found_forbidden,
    }
    no_forbidden = len(found_forbidden) == 0

    passed = has_required and none_clean and no_forbidden

    # Score: proporção de keywords encontradas
    if required_any:
        score = len(found_required) / len(required_any)
    else:
        score = 1.0 if passed else 0.0

    # Penalizar forbidden encontradas
    if found_forbidden:
        score *= 0.5
    if found_forbidden_strict:
        score *= 0.0

    return passed, score, details


def grade_model(response_text: str, grading_config: dict) -> tuple[bool, float, dict]:
    """
    Grader baseado em modelo (Haiku).

    Envia a resposta + critérios para Haiku avaliar.

    Returns:
        (passed, score, details)
    """
    try:
        import anthropic

        criteria = grading_config.get("criteria", "")
        min_score = grading_config.get("min_score", 0.5)

        client = anthropic.Anthropic()
        evaluation = client.messages.create(
            model="claude-haiku-4-5-20250514",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": (
                    "Avalie a qualidade desta resposta de um assistente de logística.\n\n"
                    f"CRITÉRIOS DE AVALIAÇÃO:\n{criteria}\n\n"
                    f"RESPOSTA A AVALIAR:\n{response_text[:2000]}\n\n"
                    "Responda APENAS com um JSON no formato:\n"
                    '{"score": 0.0 a 1.0, "reason": "explicação curta"}\n'
                    "Onde score é a qualidade da resposta (0=péssima, 1=excelente)."
                )
            }]
        )

        result_text = evaluation.content[0].text.strip()

        # Tentar parsear JSON da resposta
        # Haiku às vezes retorna markdown, limpar
        if "```" in result_text:
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]

        eval_data = json.loads(result_text)
        score = float(eval_data.get("score", 0.0))
        reason = eval_data.get("reason", "")

        passed = score >= min_score

        return passed, score, {
            "criteria": criteria,
            "min_score": min_score,
            "model_score": score,
            "model_reason": reason,
        }

    except json.JSONDecodeError as e:
        logger.warning(f"[EVAL] Model grader retornou JSON inválido: {e}")
        return False, 0.0, {"error": f"JSON inválido: {e}", "raw_response": result_text[:200]}

    except Exception as e:
        logger.error(f"[EVAL] Model grader falhou: {e}")
        return False, 0.0, {"error": str(e)}


# =============================================================================
# API Client
# =============================================================================

class AgentEvalClient:
    """Cliente para enviar tasks ao agente via API."""

    def __init__(self, base_url: str = "http://localhost:5000", username: str = "", password: str = ""):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.authenticated = False
        self.username = username
        self.password = password

    def authenticate(self) -> bool:
        """Autentica no sistema Flask."""
        if not self.username or not self.password:
            logger.warning(
                "[EVAL] Credenciais não fornecidas. Use --username e --password "
                "ou variáveis de ambiente EVAL_USERNAME e EVAL_PASSWORD."
            )
            return False

        try:
            # Login via form POST
            response = self.session.post(
                f"{self.base_url}/login",
                data={"username": self.username, "password": self.password},
                allow_redirects=False,
            )
            # Login bem-sucedido redireciona (302)
            if response.status_code in (200, 302):
                self.authenticated = True
                logger.info("[EVAL] Autenticação bem-sucedida")
                return True

            logger.error(f"[EVAL] Falha na autenticação: status={response.status_code}")
            return False

        except requests.RequestException as e:
            logger.error(f"[EVAL] Erro de conexão na autenticação: {e}")
            return False

    def send_message(self, prompt: str, timeout: int = 120) -> tuple[str, list, float]:
        """
        Envia mensagem ao agente e coleta resposta via SSE.

        Returns:
            (response_text, tools_used, elapsed_seconds)
        """
        start = time.time()

        try:
            response = self.session.post(
                f"{self.base_url}/agente/api/chat",
                json={"message": prompt},
                stream=True,
                timeout=timeout,
                headers={"Accept": "text/event-stream"},
            )

            if response.status_code != 200:
                elapsed = time.time() - start
                return f"HTTP {response.status_code}: {response.text[:200]}", [], elapsed

            # Parse SSE events
            full_text = ""
            tools_used = []

            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue

                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        event = json.loads(data_str)
                        event_type = event.get("type", "")

                        if event_type == "text":
                            full_text += event.get("content", "")

                        elif event_type == "tool_call":
                            tool_name = event.get("metadata", {}).get("tool_name", "unknown")
                            tools_used.append(tool_name)

                        elif event_type == "done":
                            # Pegar texto final se disponível
                            done_content = event.get("content", {})
                            if isinstance(done_content, dict) and done_content.get("text"):
                                full_text = done_content["text"]
                            break

                        elif event_type == "error":
                            full_text += f"\n[ERRO: {event.get('content', '')}]"

                    except json.JSONDecodeError:
                        continue

            elapsed = time.time() - start
            return full_text, tools_used, elapsed

        except requests.Timeout:
            elapsed = time.time() - start
            return f"[TIMEOUT após {timeout}s]", [], elapsed

        except requests.RequestException as e:
            elapsed = time.time() - start
            return f"[ERRO DE CONEXÃO: {e}]", [], elapsed


# =============================================================================
# Runner
# =============================================================================

def load_tasks(tasks_file: str = None) -> dict:
    """Carrega tasks.json."""
    tasks_path: Path
    if tasks_file is None:
        tasks_path = Path(__file__).parent / "tasks.json"
    else:
        tasks_path = Path(tasks_file)

    if not tasks_path.exists():
        raise FileNotFoundError(f"tasks.json não encontrado: {tasks_path}")

    with open(tasks_path) as f:
        return json.load(f)


def run_eval(
    client: AgentEvalClient,
    task: dict,
) -> EvalResult:
    """Executa uma task e avalia o resultado."""
    task_id = task["id"]
    task_name = task["name"]
    category = task["category"]
    prompt = task["prompt"]
    grading = task["grading"]
    timeout = task.get("timeout_seconds", 120)

    logger.info(f"[EVAL] Executando {task_id}: {task_name}")

    # Enviar mensagem
    response_text, tools_used, elapsed = client.send_message(prompt, timeout=timeout)

    if not response_text or response_text.startswith("[ERRO") or response_text.startswith("[TIMEOUT"):
        return EvalResult(
            task_id=task_id,
            task_name=task_name,
            category=category,
            prompt=prompt,
            response_text=response_text,
            passed=False,
            score=0.0,
            grading_type=grading["type"],
            grading_details={"error": response_text},
            tools_used=tools_used,
            elapsed_seconds=elapsed,
            error=response_text,
        )

    # Avaliar resposta
    grading_type = grading["type"]
    if grading_type == "keywords":
        passed, score, details = grade_keywords(response_text, grading)
    elif grading_type == "model":
        passed, score, details = grade_model(response_text, grading)
    else:
        passed, score, details = False, 0.0, {"error": f"Tipo de grading desconhecido: {grading_type}"}

    result = EvalResult(
        task_id=task_id,
        task_name=task_name,
        category=category,
        prompt=prompt,
        response_text=response_text[:1000],  # Truncar para relatório
        passed=passed,
        score=score,
        grading_type=grading_type,
        grading_details=details,
        tools_used=tools_used,
        elapsed_seconds=elapsed,
    )

    status = "✅ PASS" if passed else "❌ FAIL"
    logger.info(f"[EVAL] {task_id}: {status} (score={score:.2f}, {elapsed:.1f}s)")

    return result


def generate_report(results: list[EvalResult], duration: float) -> EvalReport:
    """Gera relatório a partir dos resultados."""
    report = EvalReport(
        total_tasks=len(results),
        passed=sum(1 for r in results if r.passed),
        failed=sum(1 for r in results if not r.passed and not r.error),
        errors=sum(1 for r in results if r.error),
        results=[asdict(r) for r in results],
        duration_seconds=duration,
    )

    if results:
        report.pass_rate = report.passed / report.total_tasks
        scores = [r.score for r in results]
        report.avg_score = sum(scores) / len(scores)
        latencies = [r.elapsed_seconds for r in results]
        report.avg_latency_seconds = sum(latencies) / len(latencies)

    # Agrupar por categoria
    categories = {}
    for r in results:
        cat = r.category
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0, "avg_score": 0.0, "scores": []}
        categories[cat]["total"] += 1
        categories[cat]["scores"].append(r.score)
        if r.passed:
            categories[cat]["passed"] += 1

    for cat, data in categories.items():
        if data["scores"]:
            data["avg_score"] = sum(data["scores"]) / len(data["scores"])
        data["pass_rate"] = data["passed"] / data["total"] if data["total"] > 0 else 0.0
        del data["scores"]  # Limpar dados temporários

    report.by_category = categories

    return report


def print_report(report: EvalReport):
    """Imprime relatório formatado no terminal."""
    print("\n" + "=" * 70)
    print("📊 RELATÓRIO DE AVALIAÇÃO DO AGENTE LOGÍSTICO")
    print("=" * 70)
    print(f"Data: {report.timestamp}")
    print(f"Duração total: {report.duration_seconds:.1f}s")
    print()
    print(f"Total de tasks: {report.total_tasks}")
    print(f"  ✅ Passou:  {report.passed}")
    print(f"  ❌ Falhou:  {report.failed}")
    print(f"  ⚠️  Erros:   {report.errors}")
    print(f"  📈 Taxa:    {report.pass_rate:.0%}")
    print(f"  🎯 Score:   {report.avg_score:.2f}")
    print(f"  ⏱️  Latência: {report.avg_latency_seconds:.1f}s (média)")
    print()

    if report.by_category:
        print("Por categoria:")
        print("-" * 50)
        for cat, data in sorted(report.by_category.items()):
            status = "✅" if data["pass_rate"] >= 0.8 else "⚠️" if data["pass_rate"] >= 0.5 else "❌"
            print(
                f"  {status} {cat:25s} "
                f"{data['passed']}/{data['total']} "
                f"({data['pass_rate']:.0%}) "
                f"score={data['avg_score']:.2f}"
            )

    print()
    print("Detalhes:")
    print("-" * 50)
    for r in report.results:
        status = "✅" if r["passed"] else "❌"
        error_suffix = f" [ERRO: {r['error'][:50]}]" if r.get("error") else ""
        print(
            f"  {status} {r['task_id']:8s} {r['task_name']:40s} "
            f"score={r['score']:.2f} ({r['elapsed_seconds']:.1f}s){error_suffix}"
        )

    print("=" * 70)


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Avaliação de capabilities do agente logístico")
    parser.add_argument("--url", default="http://localhost:5000", help="URL base do servidor")
    parser.add_argument("--username", default=os.getenv("EVAL_USERNAME", ""), help="Usuário para login")
    parser.add_argument("--password", default=os.getenv("EVAL_PASSWORD", ""), help="Senha para login")
    parser.add_argument("--category", help="Executar apenas uma categoria")
    parser.add_argument("--task", help="Executar apenas uma task (por ID)")
    parser.add_argument("--tasks-file", help="Arquivo de tasks customizado")
    parser.add_argument("--output", "-o", help="Salvar relatório em arquivo JSON")
    parser.add_argument("--dry-run", action="store_true", help="Apenas validar tasks.json")
    parser.add_argument("--verbose", "-v", action="store_true", help="Logging detalhado")
    args = parser.parse_args()

    # Configurar logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Carregar tasks
    try:
        tasks_data = load_tasks(args.tasks_file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Erro ao carregar tasks: {e}")
        sys.exit(1)

    tasks = tasks_data["tasks"]
    logger.info(f"Carregadas {len(tasks)} tasks de {len(tasks_data.get('categories', {}))} categorias")

    # Filtrar por categoria/task
    if args.category:
        tasks = [t for t in tasks if t["category"] == args.category]
        logger.info(f"Filtrado para categoria '{args.category}': {len(tasks)} tasks")

    if args.task:
        tasks = [t for t in tasks if t["id"] == args.task]
        logger.info(f"Filtrado para task '{args.task}': {len(tasks)} tasks")

    if not tasks:
        logger.error("Nenhuma task encontrada com os filtros aplicados")
        sys.exit(1)

    # Dry run
    if args.dry_run:
        print(f"✅ tasks.json válido: {len(tasks)} tasks")
        for t in tasks:
            print(f"  - {t['id']}: {t['name']} [{t['category']}] (grading: {t['grading']['type']})")
        sys.exit(0)

    # Criar cliente e autenticar
    client = AgentEvalClient(
        base_url=args.url,
        username=args.username,
        password=args.password,
    )

    if args.username:
        if not client.authenticate():
            logger.error("Falha na autenticação. Abortando.")
            sys.exit(1)
    else:
        logger.warning(
            "Sem credenciais — tentando sem autenticação. "
            "Use --username/--password ou EVAL_USERNAME/EVAL_PASSWORD."
        )

    # Executar tasks
    start_time = time.time()
    results: list[EvalResult] = []

    for i, task in enumerate(tasks, 1):
        logger.info(f"\n{'='*50}")
        logger.info(f"Task {i}/{len(tasks)}")
        result = run_eval(client, task)
        results.append(result)

        # Pausa entre tasks para não sobrecarregar
        if i < len(tasks):
            time.sleep(2)

    duration = time.time() - start_time

    # Gerar relatório
    report = generate_report(results, duration)
    print_report(report)

    # Salvar relatório
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)
        logger.info(f"Relatório salvo em: {output_path}")
    else:
        # Salvar automaticamente em tests/agent_evals/
        default_output = Path(__file__).parent / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(default_output, "w") as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)
        logger.info(f"Relatório salvo em: {default_output}")


if __name__ == "__main__":
    main()
