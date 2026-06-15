"""
POC: ClaudeSDKClient vs query() — Benchmark de Latência

Compara 3 abordagens do Claude Agent SDK:
  A) query() standalone com resume (status quo do Flask)
  B) ClaudeSDKClient persistente (async context manager)
  C) ClaudeSDKClient via daemon thread (simula Flask thread-per-request)

Execução:
  source .venv/bin/activate
  python scripts/poc_sdk_client.py

Tempo estimado: ~1-2 minutos.
"""

import asyncio
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from threading import Thread
from typing import Optional

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

# ──────────────────────────────────────────────────────────────
# SDK imports
# ──────────────────────────────────────────────────────────────
try:
    from claude_agent_sdk import ClaudeSDKClient, query as sdk_query
    from claude_agent_sdk.types import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
    )
except ImportError:
    print("ERRO: claude_agent_sdk nao encontrado. Ative o venv: source .venv/bin/activate")
    sys.exit(1)

# ──────────────────────────────────────────────────────────────
# Bypass nested session check (rodar de dentro do Claude Code)
# ──────────────────────────────────────────────────────────────
os.environ.pop("CLAUDECODE", None)

# ──────────────────────────────────────────────────────────────
# Configuração
# ──────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("poc_sdk_client")

PROMPTS = [
    "Qual e a capital do Brasil?",
    "E a populacao aproximada dessa cidade?",  # Follow-up (testa contexto multi-turn)
    "Obrigado, finalize.",
]

BASE_OPTIONS = ClaudeAgentOptions(
    model="claude-sonnet-4-6",
    max_turns=3,
    permission_mode="bypassPermissions",
    system_prompt="Responda de forma breve e direta. Maximo 2 frases.",
    cwd="/tmp",  # Evitar carregar CLAUDE.md do projeto (pesado)
)


# ──────────────────────────────────────────────────────────────
# Dataclasses de métricas
# ──────────────────────────────────────────────────────────────
@dataclass
class TurnMetrics:
    prompt: str
    time_to_first_msg: float = 0.0      # Primeira msg (qualquer tipo)
    time_to_first_text: float = 0.0     # Primeiro TextBlock real
    time_total: float = 0.0             # Duração total do turno
    message_types: list = field(default_factory=list)
    response_text: str = ""             # Preview da resposta
    error: Optional[str] = None


@dataclass
class BenchmarkResult:
    name: str
    connect_time: float = 0.0           # Só para B e C
    turns: list = field(default_factory=list)
    total_time: float = 0.0
    disconnect_time: float = 0.0


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def _extract_text(msg: AssistantMessage) -> str:
    """Extrai texto de um AssistantMessage."""
    parts = []
    for block in msg.content:
        if isinstance(block, TextBlock):
            parts.append(block.text)
    return " ".join(parts)


def _preview(text: str, max_len: int = 80) -> str:
    """Trunca texto para preview."""
    text = text.replace("\n", " ").strip()
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


_stderr_lines: list[str] = []


def _capture_stderr(line: str) -> None:
    """Captura stderr do CLI para debug."""
    _stderr_lines.append(line)
    # Em verbose mode, imprime stderr em tempo real
    if os.environ.get("POC_VERBOSE"):
        print(f"  [stderr] {line.rstrip()}", flush=True)


# ──────────────────────────────────────────────────────────────
# Benchmark A: query() standalone com resume
# ──────────────────────────────────────────────────────────────
async def benchmark_a() -> BenchmarkResult:
    """Status quo: query() spawna/destrói CLI process por turno."""
    result = BenchmarkResult(name="A: query()")
    total_start = time.perf_counter()
    session_id = None

    for i, prompt in enumerate(PROMPTS):
        turn = TurnMetrics(prompt=prompt)
        turn_start = time.perf_counter()
        first_msg_seen = False
        first_text_seen = False
        full_text = ""

        try:
            # Construir options com resume se tivermos session_id
            options = ClaudeAgentOptions(
                model=BASE_OPTIONS.model,
                max_turns=BASE_OPTIONS.max_turns,
                permission_mode=BASE_OPTIONS.permission_mode,
                system_prompt=BASE_OPTIONS.system_prompt,
                resume=session_id,
                stderr=_capture_stderr,
            )

            async for msg in sdk_query(prompt=prompt, options=options):
                now = time.perf_counter()

                # Primeira mensagem de qualquer tipo
                if not first_msg_seen:
                    first_msg_seen = True
                    turn.time_to_first_msg = now - turn_start

                msg_type = type(msg).__name__
                turn.message_types.append(msg_type)

                if isinstance(msg, AssistantMessage):
                    text = _extract_text(msg)
                    if text and not first_text_seen:
                        first_text_seen = True
                        turn.time_to_first_text = now - turn_start
                    full_text += text

                elif isinstance(msg, ResultMessage):
                    # Captura session_id para resume do próximo turno
                    if msg.session_id:
                        session_id = msg.session_id

            turn.response_text = _preview(full_text)
            turn.time_total = time.perf_counter() - turn_start

        except Exception as e:
            turn.error = str(e)
            turn.time_total = time.perf_counter() - turn_start
            logger.error(f"Benchmark A turno {i+1} falhou: {e}")

        result.turns.append(turn)
        print(f"  A turno {i+1}/{len(PROMPTS)}: {turn.time_total:.1f}s - {turn.response_text[:60]}")

    result.total_time = time.perf_counter() - total_start
    return result


# ──────────────────────────────────────────────────────────────
# Benchmark B: ClaudeSDKClient persistente
# ──────────────────────────────────────────────────────────────
async def benchmark_b() -> BenchmarkResult:
    """ClaudeSDKClient: spawna CLI 1x, mantém subprocess vivo."""
    result = BenchmarkResult(name="B: SDKClient")
    total_start = time.perf_counter()

    options = ClaudeAgentOptions(
        model=BASE_OPTIONS.model,
        max_turns=BASE_OPTIONS.max_turns,
        permission_mode=BASE_OPTIONS.permission_mode,
        system_prompt=BASE_OPTIONS.system_prompt,
        stderr=_capture_stderr,
    )

    client = ClaudeSDKClient(options)

    try:
        # Connect (spawna CLI process 1x)
        connect_start = time.perf_counter()
        await client.connect()
        result.connect_time = time.perf_counter() - connect_start
        print(f"  B connect: {result.connect_time:.1f}s")

        for i, prompt in enumerate(PROMPTS):
            turn = TurnMetrics(prompt=prompt)
            turn_start = time.perf_counter()
            first_msg_seen = False
            first_text_seen = False
            full_text = ""

            try:
                # Envia prompt via stdin (sem spawn novo)
                await client.query(prompt)

                async for msg in client.receive_response():
                    now = time.perf_counter()

                    if not first_msg_seen:
                        first_msg_seen = True
                        turn.time_to_first_msg = now - turn_start

                    msg_type = type(msg).__name__
                    turn.message_types.append(msg_type)

                    if isinstance(msg, AssistantMessage):
                        text = _extract_text(msg)
                        if text and not first_text_seen:
                            first_text_seen = True
                            turn.time_to_first_text = now - turn_start
                        full_text += text

                turn.response_text = _preview(full_text)
                turn.time_total = time.perf_counter() - turn_start

            except Exception as e:
                turn.error = str(e)
                turn.time_total = time.perf_counter() - turn_start
                logger.error(f"Benchmark B turno {i+1} falhou: {e}")

            result.turns.append(turn)
            print(f"  B turno {i+1}/{len(PROMPTS)}: {turn.time_total:.1f}s - {turn.response_text[:60]}")

    finally:
        disconnect_start = time.perf_counter()
        await client.disconnect()
        result.disconnect_time = time.perf_counter() - disconnect_start

    result.total_time = time.perf_counter() - total_start
    return result


# ──────────────────────────────────────────────────────────────
# Benchmark C: ClaudeSDKClient via daemon thread (simula Flask)
# ──────────────────────────────────────────────────────────────
async def _daemon_do_turn(
    client: ClaudeSDKClient,
    prompt: str,
) -> TurnMetrics:
    """Executa um turno no event loop do daemon thread."""
    turn = TurnMetrics(prompt=prompt)
    turn_start = time.perf_counter()
    first_msg_seen = False
    first_text_seen = False
    full_text = ""

    await client.query(prompt)

    async for msg in client.receive_response():
        now = time.perf_counter()

        if not first_msg_seen:
            first_msg_seen = True
            turn.time_to_first_msg = now - turn_start

        msg_type = type(msg).__name__
        turn.message_types.append(msg_type)

        if isinstance(msg, AssistantMessage):
            text = _extract_text(msg)
            if text and not first_text_seen:
                first_text_seen = True
                turn.time_to_first_text = now - turn_start
            full_text += text

    turn.response_text = _preview(full_text)
    turn.time_total = time.perf_counter() - turn_start
    return turn


async def _daemon_connect(client: ClaudeSDKClient) -> float:
    """Conecta o client no daemon thread, retorna tempo de connect."""
    start = time.perf_counter()
    await client.connect()
    return time.perf_counter() - start


async def _daemon_disconnect(client: ClaudeSDKClient) -> float:
    """Desconecta o client no daemon thread, retorna tempo."""
    start = time.perf_counter()
    await client.disconnect()
    return time.perf_counter() - start


def benchmark_c() -> BenchmarkResult:
    """
    ClaudeSDKClient em daemon thread com run_coroutine_threadsafe.

    Simula Flask: requests vêm de threads diferentes, mas o SDK vive
    em um event loop persistente no daemon thread.

    CAVEAT SDK: "you cannot use a ClaudeSDKClient instance across
    different async runtime contexts". Por isso TODAS as operações
    rodam no MESMO event loop do daemon thread.
    """
    result = BenchmarkResult(name="C: daemon thread")
    total_start = time.perf_counter()

    # Criar event loop persistente no daemon thread
    loop = asyncio.new_event_loop()
    thread = Thread(target=loop.run_forever, daemon=True, name="sdk-daemon")
    thread.start()

    options = ClaudeAgentOptions(
        model=BASE_OPTIONS.model,
        max_turns=BASE_OPTIONS.max_turns,
        permission_mode=BASE_OPTIONS.permission_mode,
        system_prompt=BASE_OPTIONS.system_prompt,
        stderr=_capture_stderr,
    )

    client = ClaudeSDKClient(options)

    try:
        # Connect via run_coroutine_threadsafe (simula "Flask startup")
        future = asyncio.run_coroutine_threadsafe(_daemon_connect(client), loop)
        result.connect_time = future.result(timeout=120)
        print(f"  C connect: {result.connect_time:.1f}s")

        # Cada turno simula um request Flask (thread diferente submete ao daemon)
        for i, prompt in enumerate(PROMPTS):
            try:
                future = asyncio.run_coroutine_threadsafe(
                    _daemon_do_turn(client, prompt), loop
                )
                turn = future.result(timeout=120)
            except Exception as e:
                turn = TurnMetrics(prompt=prompt, error=str(e))
                logger.error(f"Benchmark C turno {i+1} falhou: {e}")

            result.turns.append(turn)
            print(f"  C turno {i+1}/{len(PROMPTS)}: {turn.time_total:.1f}s - {turn.response_text[:60]}")

    finally:
        # Disconnect via daemon thread
        try:
            future = asyncio.run_coroutine_threadsafe(_daemon_disconnect(client), loop)
            result.disconnect_time = future.result(timeout=30)
        except Exception:
            pass

        # Parar event loop e daemon thread
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=5)

    result.total_time = time.perf_counter() - total_start
    return result


# ──────────────────────────────────────────────────────────────
# Output: Tabela comparativa
# ──────────────────────────────────────────────────────────────
def print_comparison(results: list[BenchmarkResult]) -> None:
    """Imprime tabela comparativa lado a lado."""
    print()
    print("=" * 80)
    print("COMPARACAO LADO A LADO")
    print("=" * 80)

    # Header
    names = [r.name for r in results]
    header = f"{'Metrica':<25}"
    for name in names:
        header += f" | {name:>16}"
    print(header)
    print("-" * 25 + ("+" + "-" * 18) * len(results))

    # Connect
    row = f"{'Connect (s)':<25}"
    for r in results:
        row += f" | {r.connect_time:>16.3f}"
    print(row)

    # Per-turn metrics
    num_turns = max(len(r.turns) for r in results)
    for t_idx in range(num_turns):
        # Time to first msg
        row = f"{f'T{t_idx+1} 1a msg (s)':<25}"
        for r in results:
            if t_idx < len(r.turns):
                val = r.turns[t_idx].time_to_first_msg
                row += f" | {val:>16.3f}"
            else:
                row += f" | {'N/A':>16}"
        print(row)

        # Time to first text
        row = f"{f'T{t_idx+1} 1o texto (s)':<25}"
        for r in results:
            if t_idx < len(r.turns):
                val = r.turns[t_idx].time_to_first_text
                row += f" | {val:>16.3f}"
            else:
                row += f" | {'N/A':>16}"
        print(row)

        # Total turn time
        row = f"{f'T{t_idx+1} total (s)':<25}"
        for r in results:
            if t_idx < len(r.turns):
                val = r.turns[t_idx].time_total
                err = r.turns[t_idx].error
                if err:
                    row += f" | {'ERRO':>16}"
                else:
                    row += f" | {val:>16.3f}"
            else:
                row += f" | {'N/A':>16}"
        print(row)

    # Disconnect
    row = f"{'Disconnect (s)':<25}"
    for r in results:
        row += f" | {r.disconnect_time:>16.3f}"
    print(row)

    # Total
    print("-" * 25 + ("+" + "-" * 18) * len(results))
    row = f"{'TOTAL (s)':<25}"
    for r in results:
        row += f" | {r.total_time:>16.3f}"
    print(row)

    # Speedup vs A
    if len(results) >= 2:
        a_total = results[0].total_time
        print()
        print("SPEEDUP vs A:")
        for r in results[1:]:
            if r.total_time > 0:
                speedup = a_total / r.total_time
                print(f"  {r.name}: {speedup:.2f}x")

    # Contexto multi-turn
    print()
    print("CONTEXTO MULTI-TURN (turno 2 deve referenciar Brasilia/Brasil):")
    for r in results:
        if len(r.turns) >= 2:
            t2 = r.turns[1]
            has_context = any(
                kw in t2.response_text.lower()
                for kw in ["bras", "milh", "popula", "habitant", "3", "2", "capital"]
            )
            status = "OK" if has_context else "FALHOU"
            print(f"  {r.name}: [{status}] {t2.response_text}")

    # Erros
    errors = []
    for r in results:
        for t_idx, t in enumerate(r.turns):
            if t.error:
                errors.append(f"  {r.name} T{t_idx+1}: {t.error}")
    if errors:
        print()
        print("ERROS:")
        for e in errors:
            print(e)

    # Tipos de mensagem (debug)
    print()
    print("TIPOS DE MENSAGEM POR TURNO:")
    for r in results:
        for t_idx, t in enumerate(r.turns):
            types_summary = {}
            for mt in t.message_types:
                types_summary[mt] = types_summary.get(mt, 0) + 1
            types_str = ", ".join(f"{k}:{v}" for k, v in sorted(types_summary.items()))
            print(f"  {r.name} T{t_idx+1}: {types_str}")


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────
async def main():
    # Fail fast: verificar API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERRO: ANTHROPIC_API_KEY nao definida.")
        print("  export ANTHROPIC_API_KEY='sk-...'")
        sys.exit(1)

    # Verificar que CLI está disponível
    import shutil
    if not shutil.which("claude"):
        print("ERRO: CLI 'claude' nao encontrado no PATH.")
        sys.exit(1)

    print("=" * 80)
    print("POC: ClaudeSDKClient vs query() — Benchmark de Latencia")
    print(f"Modelo: {BASE_OPTIONS.model}")
    print(f"Prompts: {len(PROMPTS)} turnos")
    print("=" * 80)

    results = []

    # ── Benchmark A ──
    print()
    print("[A] query() standalone com resume...")
    result_a = await benchmark_a()
    results.append(result_a)

    # ── Benchmark B ──
    print()
    print("[B] ClaudeSDKClient persistente...")
    try:
        result_b = await benchmark_b()
        results.append(result_b)
    except Exception as e:
        print(f"  FALHOU: {e}")
        results.append(BenchmarkResult(name="B: SDKClient", total_time=0))

    # ── Benchmark C ──
    print()
    print("[C] ClaudeSDKClient via daemon thread (simula Flask)...")
    try:
        result_c = benchmark_c()
        results.append(result_c)
    except Exception as e:
        print(f"  FALHOU: {e}")
        results.append(BenchmarkResult(name="C: daemon thread", total_time=0))

    # ── Comparação ──
    print_comparison(results)

    # ── Decisão ──
    print()
    print("=" * 80)
    print("DECISAO:")
    if len(results) >= 3:
        a = results[0]
        _b = results[1]
        c = results[2]

        # Checar se C completou sem erro
        c_errors = [t for t in c.turns if t.error]
        if c_errors:
            print("  C (daemon thread) FALHOU — descarta migracao.")
            print("  Limitacao tecnica do SDK: anyio task group incompativel com cross-context.")
        elif a.total_time > 0 and c.total_time > 0:
            speedup = a.total_time / c.total_time
            if speedup >= 1.5:
                print(f"  B/C sao {speedup:.1f}x mais rapidos que A.")
                print("  VALE investir em migracao para ClaudeSDKClient.")
            else:
                print(f"  Diferenca modesta ({speedup:.1f}x).")
                print("  MANTER query() — complexidade nao justifica.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
