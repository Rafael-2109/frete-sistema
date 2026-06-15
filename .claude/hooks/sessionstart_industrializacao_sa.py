#!/usr/bin/env python3
"""Hook SessionStart — injeta um aviso no início da sessão SE a automação da
industrialização FB↔LF (SAs+crons no Odoo) precisar de re-aplicação.

Auto-contido (stdlib pura): lê o FLAG gravado pela checagem D8
(`app/odoo/estoque/provisioning/monitor_sa_industrializacao.py::verificar_e_gravar_flag`).
NÃO conecta no Odoo (rápido). NUNCA levanta — hook que quebra trava a sessão.

Ativação (handoff): registrar em `.claude/settings.json` sob `hooks.SessionStart`.
Confirmar o contrato de saída contra um hook existente (additionalContext).
"""
import json
import os
import sys

FLAG_PATH = os.path.expanduser('~/.claude/state/industrializacao_sa_health.json')


def main():
    try:
        with open(FLAG_PATH, 'r', encoding='utf-8') as f:
            flag = json.load(f)
    except Exception:
        return  # sem flag (D8 ainda não rodou) ou ilegível → silêncio
    if not flag.get('acao_necessaria'):
        return
    pend = [d for d in (flag.get('detalhes') or []) if d.get('acao')]
    linhas = "\n".join(f"  - {d.get('artefato')}: {d.get('status')} → {d.get('acao')}" for d in pend)
    quando = flag.get('verificado_em') or '?'
    print(
        f"⚠️ AUTOMAÇÃO INDUSTRIALIZAÇÃO FB↔LF — SA/cron precisam de RE-APLICAÇÃO (checagem D8 {quando}):\n"
        f"{linhas}\n"
        "  Re-aplicar: `python -m app.odoo.estoque.provisioning.sa_retorno_industrializacao "
        "provisionar --confirmar` (após go do Rafael). Provável upgrade CIEL IT (precedente DFE NFD)."
    )


if __name__ == '__main__':
    try:
        main()
    except Exception:
        sys.exit(0)  # nunca quebra a sessão
