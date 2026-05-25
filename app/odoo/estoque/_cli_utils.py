"""Helpers compartilhados para CLIs de skills do orquestrador-Odoo.

Resolvem 2 gaps identificados na sessao v7 (2026-05-24):

1. `silenciar_stdout()` / `criar_app_silencioso(quiet=True)`:
   Suprime stdout + logging INFO de Flask boot (~50 linhas por call).
   Em batches de N chamadas, reduz output em 40-60%.
   Default: quiet=False (retrocompatibilidade — sem mudanca de comportamento).

2. `verificar_concorrencia(script_name)`:
   Detecta se ja ha outro processo do mesmo script rodando (via pgrep -f).
   Previne race condition de batch background + smoke paralelo.
   Retorna lista de PIDs concorrentes (vazia = OK para prosseguir).

Adicionar `--quiet` flag aos CLIs CLI argparse:
    ap.add_argument('--quiet', action='store_true',
                    help='Suprimir Flask boot stdout (recomendado em batches)')
    args = ap.parse_args()
    if check_concorrencia:
        verificar_concorrencia_e_avisar(__file__)
    app = criar_app_silencioso(quiet=args.quiet)
"""
import contextlib
import io
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import List


@contextlib.contextmanager
def silenciar_stdout():
    """Suprime stdout + stderr + logging INFO/DEBUG temporariamente.

    Util durante create_app() do Flask que polui o output com:
      - prints "✅ Tipos PostgreSQL registrados..." (codigo direto)
      - logging INFO de "Sistema de Fretes iniciado", redis cache, etc.
      - SAWarning cycles entre tables (warnings.warn → stderr)
      - 1349 SAWarning (stderr)

    CUIDADO: este context manager suprime stderr TAMBEM (caso contrario
    o logging Flask escapa). Erros reais durante create_app() sao engolidos.
    NAO usar em codigo de producao — apenas durante boot de CLI scripts.

    Pos-yield: stdout/stderr restaurados; nivel de logging restaurado.
    """
    # Salvar nivel de root logger E de loggers conhecidos do app
    root_logger = logging.getLogger()
    nivel_anterior = root_logger.level
    niveis_loggers_anteriores = {}
    for nome in ['sistema_fretes', 'app', 'werkzeug', 'sqlalchemy',
                 'app.__init__']:
        lg = logging.getLogger(nome)
        niveis_loggers_anteriores[nome] = lg.level
        lg.setLevel(logging.WARNING)
    root_logger.setLevel(logging.WARNING)

    # Redirecionar stdout E stderr para sinks (handlers de logging podem
    # escrever em qualquer um deles dependendo da configuracao)
    sink_out = io.StringIO()
    sink_err = io.StringIO()
    try:
        with contextlib.redirect_stdout(sink_out), \
             contextlib.redirect_stderr(sink_err):
            yield sink_out
    finally:
        # Restaurar niveis de logging
        root_logger.setLevel(nivel_anterior)
        for nome, nivel in niveis_loggers_anteriores.items():
            logging.getLogger(nome).setLevel(nivel)


def criar_app_silencioso(quiet: bool = False):
    """Wrapper de create_app() com opcao quiet.

    Args:
        quiet: se True, suprime stdout + logging INFO durante boot.
            Default False (retrocompatibilidade — sem mudanca).

    Returns:
        Flask app (instancia normal de create_app()).
    """
    # Lazy import — evita ciclo com app.__init__
    from app import create_app
    if quiet:
        with silenciar_stdout():
            return create_app()
    return create_app()


def verificar_concorrencia(
    script_path: str,
    excluir_pid_atual: bool = True,
) -> List[int]:
    """Detecta outros processos rodando o MESMO script via pgrep -f.

    Args:
        script_path: caminho do script (geralmente __file__ ou sys.argv[0]).
        excluir_pid_atual: se True, exclui o proprio PID e PPID da lista.

    Returns:
        Lista de PIDs de processos concorrentes. Vazia = OK para prosseguir.

    Pre-condicoes: `pgrep` disponivel no PATH (Linux/Mac).

    Exemplo:
        pids = verificar_concorrencia(__file__)
        if pids:
            print(f'AVISO: ja ha {len(pids)} outro(s) processo(s) rodando: {pids}')
            sys.exit(2)
    """
    # Extrair nome basename para pattern
    nome_script = Path(script_path).name
    pid_atual = os.getpid()
    ppid_atual = os.getppid()

    try:
        result = subprocess.run(
            ['pgrep', '-f', nome_script],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            # pgrep retorna 1 se nao achou nada (esperado)
            return []
        pids = [
            int(p.strip()) for p in result.stdout.split('\n')
            if p.strip().isdigit()
        ]
        if excluir_pid_atual:
            pids = [p for p in pids if p != pid_atual and p != ppid_atual]
        return pids
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        # pgrep nao disponivel ou timeout — nao bloquear
        return []


def verificar_concorrencia_e_avisar(
    script_path: str,
    forcar: bool = False,
) -> bool:
    """Verifica concorrencia e AVISA via stderr; se houver, recomenda EXIT 2.

    Args:
        script_path: caminho do script (geralmente __file__).
        forcar: se True, apenas avisa mas nao retorna False (continuar).

    Returns:
        True se OK para prosseguir (sem concorrencia OU forcar=True).
        False se ha concorrencia e forcar=False (caller deve sys.exit(2)).
    """
    pids = verificar_concorrencia(script_path)
    if not pids:
        return True
    msg = (
        f'\n  AVISO concorrencia: {len(pids)} outro(s) processo(s) do mesmo '
        f'script ja esta(o) rodando (PIDs: {pids}). '
        f'Risco de DUPLICAcaO de operacoes em PROD.\n'
        f'  Recomendacao: encerrar processo(s) concorrente(s) antes de '
        f'prosseguir (kill {" ".join(str(p) for p in pids)}).\n'
        f'  Para FORcAR continuacao (use com cuidado): adicionar --forcar-concorrencia.\n'
    )
    print(msg, file=sys.stderr)
    return bool(forcar)


def adicionar_args_padrao(ap):
    """Adiciona --quiet e --forcar-concorrencia ao argparse.

    Padrao reutilizavel para todos CLIs de scripts estoque.

    Args:
        ap: argparse.ArgumentParser instance.

    Returns:
        ap (mesmo objeto, modificado in-place — para encadeamento).
    """
    ap.add_argument(
        '--quiet', action='store_true',
        help='Suprime Flask boot stdout (recomendado em batches; '
             'NAO afeta JSON output do script)',
    )
    ap.add_argument(
        '--forcar-concorrencia', action='store_true',
        help='Forca prosseguimento mesmo se houver outro processo do '
             'mesmo script rodando (use com cuidado em PROD)',
    )
    return ap


def setup_cli_completo(script_path: str, quiet: bool, forcar: bool):
    """Setup unificado: verifica concorrencia + cria app silencioso.

    Args:
        script_path: __file__ do CLI script.
        quiet: valor de args.quiet.
        forcar: valor de args.forcar_concorrencia.

    Returns:
        Flask app pronto para uso (ou sys.exit(2) se concorrencia + nao forcar).

    Exemplo de uso completo:
        from app.odoo.estoque._cli_utils import adicionar_args_padrao, setup_cli_completo

        ap = argparse.ArgumentParser(...)
        adicionar_args_padrao(ap)
        # ... outros args ...
        args = ap.parse_args()

        app = setup_cli_completo(__file__, args.quiet, args.forcar_concorrencia)
        with app.app_context():
            ...
    """
    # Verificar concorrencia primeiro
    ok = verificar_concorrencia_e_avisar(script_path, forcar=forcar)
    if not ok:
        sys.exit(2)
    # Criar app (quiet ou normal)
    return criar_app_silencioso(quiet=quiet)
