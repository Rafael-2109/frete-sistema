#!/usr/bin/env python3
"""
Test script para validar refatoracao .claude/ (routing de skills, references, disambiguation).
Usa Anthropic API (claude-sonnet-4-20250514) com prompts reais.

Custo estimado: ~$0.14 USD (10 prompts x ~3.1K input + ~300 output tokens)

Uso:
    source .venv/bin/activate
    python .claude/tests/test_routing_refactoring.py
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from anthropic import Anthropic
except ImportError:
    print("ERRO: pip install anthropic")
    sys.exit(1)

# ============================================================
# CONFIGURACAO
# ============================================================

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 512
RESULTS_FILE = Path(__file__).parent / "routing_test_results.json"
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .claude/tests/ -> projeto raiz


# ============================================================
# CARREGAR CONTEXTO DO SISTEMA
# ============================================================

def load_system_context() -> str:
    """Carrega CLAUDE.md + frontmatter/QUANDO NAO USAR de cada skill como system prompt."""

    # 1. CLAUDE.md completo
    claude_md_path = PROJECT_ROOT / "CLAUDE.md"
    claude_md = claude_md_path.read_text(encoding="utf-8")

    # 2. Extrair frontmatter + QUANDO NAO USAR de cada skill
    skills_dir = PROJECT_ROOT / ".claude" / "skills"
    skills_context = []

    skill_names = [
        "conciliando-odoo-po",
        "descobrindo-odoo-estrutura",
        "executando-odoo-financeiro",
        "integracao-odoo",
        "rastreando-odoo",
        "razao-geral-odoo",
        "recebimento-fisico-odoo",
        "validacao-nf-po",
    ]

    for skill_name in skill_names:
        skill_path = skills_dir / skill_name / "SKILL.md"
        if not skill_path.exists():
            continue

        content = skill_path.read_text(encoding="utf-8")

        # Extrair frontmatter (entre --- e ---)
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
        else:
            frontmatter = ""

        # Extrair secao QUANDO NAO USAR
        quando_nao_usar = ""
        for line_idx, line in enumerate(content.split("\n")):
            if "QUANDO NAO USAR" in line:
                # Capturar proximas linhas ate linha em branco ou novo header
                nao_usar_lines = [line]
                for subsequent in content.split("\n")[line_idx + 1:]:
                    if subsequent.startswith("#") and "QUANDO" not in subsequent:
                        break
                    if subsequent.strip() == "" and len(nao_usar_lines) > 2:
                        break
                    nao_usar_lines.append(subsequent)
                quando_nao_usar = "\n".join(nao_usar_lines)
                break

        skills_context.append(
            f"### Skill: {skill_name}\n"
            f"```yaml\n{frontmatter}\n```\n"
            f"{quando_nao_usar}\n"
        )

    # 3. Montar system prompt
    system_prompt = (
        f"{claude_md}\n\n"
        f"---\n\n"
        f"# SKILLS DISPONIVEIS (com regras de exclusao)\n\n"
        + "\n".join(skills_context)
    )

    return system_prompt


# ============================================================
# TEST CASES
# ============================================================

TEST_CASES = [
    # --- Categoria A: Routing Accuracy ---
    {
        "id": "A1",
        "category": "routing",
        "prompt": "Preciso criar um pagamento no Odoo para a NF 54321. O titulo esta em aberto.",
        "expected_skill": "executando-odoo-financeiro",
        "anti_skills": ["rastreando-odoo", "descobrindo-odoo-estrutura"],
        "detection_keywords": ["executando-odoo-financeiro", "pagamento", "financeiro"],
    },
    {
        "id": "A2",
        "category": "routing",
        "prompt": "Rastreie o fluxo completo da NF 12345 desde a entrada fiscal ate o pagamento final.",
        "expected_skill": "rastreando-odoo",
        "anti_skills": ["executando-odoo-financeiro", "validacao-nf-po"],
        "detection_keywords": ["rastreando-odoo", "rastrear", "rastreie", "fluxo"],
    },
    {
        "id": "A3",
        "category": "routing",
        "prompt": "O picking do recebimento nao valida, os lotes nao foram preenchidos e o quality check esta pendente.",
        "expected_skill": "recebimento-fisico-odoo",
        "anti_skills": ["validacao-nf-po", "conciliando-odoo-po"],
        "detection_keywords": ["recebimento-fisico-odoo", "Fase 4", "lote", "quality", "picking"],
    },
    {
        "id": "A4",
        "category": "routing",
        "prompt": "Preciso exportar o razao geral contabil do periodo de janeiro de 2026 em Excel.",
        "expected_skill": "razao-geral-odoo",
        "anti_skills": ["executando-odoo-financeiro", "rastreando-odoo"],
        "detection_keywords": ["razao-geral-odoo", "razao geral", "General Ledger", "account.move.line"],
    },

    # --- Categoria B: Reference Resolution ---
    {
        "id": "B1",
        "category": "reference",
        "prompt": "Quais campos tem o modelo CarteiraPrincipal? Preciso saber o nome correto do campo de saldo pendente.",
        "expected_skill": None,
        "expected_reference": "modelos/CAMPOS_CARTEIRA_SEPARACAO",
        "anti_skills": [],
        "detection_keywords": ["CAMPOS_CARTEIRA_SEPARACAO", "qtd_saldo_produto_pedido", "modelos/"],
    },
    {
        "id": "B2",
        "category": "reference",
        "prompt": "Qual o picking_type_id correto para recebimento na empresa SC? Preciso do ID fixo.",
        "expected_skill": None,
        "expected_reference": "odoo/IDS_FIXOS",
        "anti_skills": [],
        "detection_keywords": ["IDS_FIXOS", "odoo/IDS_FIXOS", "picking_type_id"],
    },

    # --- Categoria C: Disambiguation ---
    {
        "id": "C1",
        "category": "disambiguation",
        "prompt": "Quero ver a estrutura do modelo purchase.order no Odoo, listar todos os campos disponiveis.",
        "expected_skill": "descobrindo-odoo-estrutura",
        "anti_skills": ["validacao-nf-po", "conciliando-odoo-po"],
        "detection_keywords": ["descobrindo-odoo-estrutura", "descobrindo", "listar-campos", "listar campos"],
    },
    {
        "id": "C2",
        "category": "disambiguation",
        "prompt": "Preciso consolidar os POs da NF 12345, criar o PO Conciliador e ajustar os saldos.",
        "expected_skill": "conciliando-odoo-po",
        "anti_skills": ["validacao-nf-po", "recebimento-fisico-odoo", "rastreando-odoo"],
        "detection_keywords": ["conciliando-odoo-po", "consolidar", "PO Conciliador", "Fase 3"],
    },

    # --- Categoria D: Decision Tree ---
    {
        "id": "D1",
        "category": "decision_tree",
        "prompt": "Preciso criar uma nova integracao para sincronizar devolucoes do Odoo com o sistema local, com service, route e migration.",
        "expected_skill": "integracao-odoo",
        "anti_skills": ["descobrindo-odoo-estrutura", "rastreando-odoo"],
        "detection_keywords": ["integracao-odoo", "16 etapas", "service", "integracao"],
    },
    {
        "id": "D2",
        "category": "decision_tree",
        "prompt": "A validacao da NF 98765 contra o PO esta dando divergencia de quantidade, o De-Para parece estar configurado errado.",
        "expected_skill": "validacao-nf-po",
        "anti_skills": ["conciliando-odoo-po", "recebimento-fisico-odoo"],
        "detection_keywords": ["validacao-nf-po", "Fase 2", "De-Para", "divergencia", "match"],
    },
]


# ============================================================
# SCORING
# ============================================================

def evaluate_response(test_case: dict, response_text: str) -> dict:
    """Pontua resposta contra expectativas. Max 5 pontos."""
    score = 0.0
    max_score = 5.0
    details = []
    text_lower = response_text.lower()

    # 1. Skill correta mencionada (2 pontos)
    if test_case.get("expected_skill"):
        expected = test_case["expected_skill"].lower()
        if expected in text_lower:
            score += 2.0
            details.append(f"PASS: Skill correta '{test_case['expected_skill']}' mencionada")
        else:
            details.append(f"FAIL: Skill '{test_case['expected_skill']}' NAO mencionada")
    else:
        # Test de reference, nao de skill
        score += 2.0
        details.append("N/A: Teste de reference, nao de skill")

    # 2. Anti-skills ausentes (1 ponto)
    if test_case.get("anti_skills"):
        wrong = [s for s in test_case["anti_skills"] if s.lower() in text_lower]
        if not wrong:
            score += 1.0
            details.append("PASS: Nenhuma anti-skill mencionada como principal")
        else:
            details.append(f"WARN: Anti-skills detectadas: {wrong}")
    else:
        score += 1.0
        details.append("N/A: Sem anti-skills definidas")

    # 3. Keywords detectadas (1 ponto)
    keywords = test_case.get("detection_keywords", [])
    found = sum(1 for kw in keywords if kw.lower() in text_lower)
    if found >= 2:
        score += 1.0
        details.append(f"PASS: {found}/{len(keywords)} keywords encontradas")
    elif found == 1:
        score += 0.5
        details.append(f"PARTIAL: {found}/{len(keywords)} keywords encontradas")
    else:
        details.append(f"FAIL: {found}/{len(keywords)} keywords encontradas")

    # 4. Path no formato novo (1 ponto)
    old_patterns = [
        "ODOO_IDS_FIXOS.md", "ODOO_GOTCHAS.md", "ODOO_MODELOS_CAMPOS.md",
        "ODOO_PADROES_AVANCADOS.md", "ODOO_PIPELINE_RECEBIMENTO.md",
        "CONVERSAO_UOM_ODOO.md",
    ]
    new_patterns = ["odoo/", "modelos/", "negocio/", "design/"]

    uses_old = any(p in response_text for p in old_patterns)
    uses_new = any(p in response_text for p in new_patterns)

    if test_case.get("expected_reference"):
        if test_case["expected_reference"] in response_text:
            score += 1.0
            details.append(f"PASS: Reference correta '{test_case['expected_reference']}' encontrada")
        elif uses_new and not uses_old:
            score += 0.5
            details.append("PARTIAL: Path novo usado mas reference especifica nao encontrada")
        elif uses_old:
            details.append("FAIL: Path no formato ANTIGO detectado")
        else:
            score += 0.5
            details.append("PARTIAL: Nenhum path de referencia mencionado")
    else:
        if uses_old:
            details.append("WARN: Path antigo detectado (nao esperado)")
        elif uses_new:
            score += 1.0
            details.append("PASS: Path novo usado")
        else:
            score += 0.5
            details.append("NEUTRAL: Nenhum path mencionado")

    return {
        "score": round(score, 1),
        "max_score": max_score,
        "percentage": round(score / max_score * 100),
        "details": details,
    }


# ============================================================
# EXECUCAO
# ============================================================

def run_tests():
    """Executa todos os testes via API Anthropic."""

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERRO: ANTHROPIC_API_KEY nao configurada")
        sys.exit(1)

    client = Anthropic(api_key=api_key)

    print("=" * 60)
    print("TESTE DE ROUTING - REFATORACAO .claude/")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Modelo: {MODEL}")
    print(f"Testes: {len(TEST_CASES)}")
    print("=" * 60)

    # Carregar system prompt
    print("\nCarregando contexto do sistema...")
    system_prompt = load_system_context()
    system_tokens_est = len(system_prompt) // 4  # estimativa grosseira
    print(f"System prompt: ~{system_tokens_est} tokens estimados")

    user_instruction = (
        "Voce eh um assistente especializado no sistema de fretes da Nacom Goya. "
        "Com base nas skills e references disponiveis no CLAUDE.md, responda:\n"
        "1. Qual SKILL voce usaria para esta tarefa? (nome exato)\n"
        "2. Qual REFERENCE FILE voce consultaria? (path completo)\n"
        "3. Por que esta skill e NAO outra?\n"
        "Seja conciso (max 200 palavras)."
    )

    results = []
    total_input_tokens = 0
    total_output_tokens = 0
    start_time = time.time()

    for i, tc in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] {tc['id']} ({tc['category']})")
        print(f"  Prompt: {tc['prompt'][:80]}...")

        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": f"{user_instruction}\n\nTAREFA DO USUARIO:\n{tc['prompt']}"
                }],
            )

            response_text = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens

            # Avaliar
            evaluation = evaluate_response(tc, response_text)

            result = {
                "id": tc["id"],
                "category": tc["category"],
                "prompt": tc["prompt"],
                "expected_skill": tc.get("expected_skill"),
                "expected_reference": tc.get("expected_reference"),
                "response": response_text,
                "score": evaluation["score"],
                "max_score": evaluation["max_score"],
                "percentage": evaluation["percentage"],
                "details": evaluation["details"],
                "tokens": {"input": input_tokens, "output": output_tokens},
            }
            results.append(result)

            status = "PASS" if evaluation["percentage"] >= 70 else "FAIL"
            print(f"  Score: {evaluation['score']}/{evaluation['max_score']} ({evaluation['percentage']}%) [{status}]")
            for d in evaluation["details"]:
                print(f"    {d}")

        except Exception as e:
            print(f"  ERRO: {e}")
            results.append({
                "id": tc["id"],
                "category": tc["category"],
                "prompt": tc["prompt"],
                "error": str(e),
                "score": 0,
                "max_score": 5,
                "percentage": 0,
                "details": [f"ERROR: {e}"],
                "tokens": {"input": 0, "output": 0},
            })

        # Rate limiting (respeitar limites)
        time.sleep(1)

    elapsed = time.time() - start_time

    # ============================================================
    # SUMMARY
    # ============================================================

    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"score": 0, "max": 0, "count": 0}
        categories[cat]["score"] += r["score"]
        categories[cat]["max"] += r["max_score"]
        categories[cat]["count"] += 1

    for cat in categories:
        categories[cat]["pct"] = round(
            categories[cat]["score"] / categories[cat]["max"] * 100
        )

    overall_score = sum(r["score"] for r in results)
    overall_max = sum(r["max_score"] for r in results)
    overall_pct = round(overall_score / overall_max * 100) if overall_max > 0 else 0

    # Custo estimado (Sonnet pricing: $3/M input, $15/M output)
    cost_input = total_input_tokens * 3.0 / 1_000_000
    cost_output = total_output_tokens * 15.0 / 1_000_000
    total_cost = cost_input + cost_output

    summary = {
        "overall_score": overall_score,
        "overall_max": overall_max,
        "overall_percentage": overall_pct,
        "by_category": categories,
        "pass_threshold": 70,
        "verdict": "PASS" if overall_pct >= 70 else "FAIL",
    }

    output = {
        "metadata": {
            "date": datetime.now().isoformat(),
            "model": MODEL,
            "total_tests": len(TEST_CASES),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_cost_usd": round(total_cost, 4),
            "execution_time_s": round(elapsed, 1),
        },
        "results": results,
        "summary": summary,
    }

    # Salvar JSON
    RESULTS_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    # Imprimir resumo
    print("\n" + "=" * 60)
    print("RESUMO")
    print("=" * 60)
    print(f"Score Total: {overall_score}/{overall_max} ({overall_pct}%)")
    print(f"Veredicto: {summary['verdict']}")
    print(f"Tempo: {elapsed:.1f}s")
    print(f"Tokens: {total_input_tokens} input + {total_output_tokens} output")
    print(f"Custo: ${total_cost:.4f} USD")
    print()

    print("Por Categoria:")
    for cat, data in sorted(categories.items()):
        status = "PASS" if data["pct"] >= 70 else "FAIL"
        print(f"  {cat:20s}: {data['score']}/{data['max']} ({data['pct']}%) [{status}]")

    print(f"\nResultados salvos em: {RESULTS_FILE}")

    return output


if __name__ == "__main__":
    run_tests()
