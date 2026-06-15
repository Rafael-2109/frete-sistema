# etapa: infra-Odoo (monitor anti-upgrade)
# doc-dono: docs/industrializacao-fb-lf/SOT_OPERACOES.md §6.3
"""Monitor anti-upgrade LEVE das SAs+crons da automação da SAÍDA de industrialização
(DECISÃO SOT §6.3 — Opção B). NÃO é um serviço novo: roda no NOSSO runtime em 2 pontos:
  - **D8 (diário)** → `verificar_e_gravar_flag()`: faz a checagem READ-only via XML-RPC
    (`SaRetornoIndustrializacaoProvisioner.verificar`) e grava um FLAG JSON;
  - **hook `SessionStart`** → `ler_flag()` + `mensagem_alerta()`: injeta um aviso no início
    da sessão SE houver necessidade de re-aplicação (SA/cron sumiram em upgrade CIEL IT —
    precedente DFE NFD).

O hook NÃO conecta no Odoo (rápido); só lê o flag gravado pelo D8. Separação proposital.
"""
import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

FLAG_PATH_DEFAULT = os.path.expanduser('~/.claude/state/industrializacao_sa_health.json')


def verificar_e_gravar_flag(flag_path: str = FLAG_PATH_DEFAULT, odoo=None) -> Dict[str, Any]:
    """D8 (diário) — checagem READ-only via XML-RPC + grava o FLAG. Retorna o status.
    `odoo` opcional (injetável em teste); senão abre conexão. NÃO escreve no Odoo."""
    from app.odoo.estoque.provisioning.sa_retorno_industrializacao import (
        SaRetornoIndustrializacaoProvisioner)
    if odoo is None:
        from app.odoo.utils.connection import get_odoo_connection
        odoo = get_odoo_connection()
        assert odoo.authenticate(), 'falha autenticacao Odoo'
    status = SaRetornoIndustrializacaoProvisioner(odoo).verificar()
    try:
        from app.utils.timezone import agora_utc_naive
        status['verificado_em'] = agora_utc_naive().isoformat()
    except Exception:
        status['verificado_em'] = None
    gravar_flag(status, flag_path)
    return status


def gravar_flag(status: Dict[str, Any], flag_path: str = FLAG_PATH_DEFAULT) -> None:
    """Grava o flag JSON (cria o diretório). Nunca levanta (best-effort)."""
    try:
        os.makedirs(os.path.dirname(flag_path), exist_ok=True)
        with open(flag_path, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f'gravar_flag falhou: {str(e)[:120]}')


def ler_flag(flag_path: str = FLAG_PATH_DEFAULT) -> Optional[Dict[str, Any]]:
    """Lê o flag JSON. Retorna None se ausente/ilegível (hook degrada em silêncio)."""
    try:
        with open(flag_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def mensagem_alerta(flag: Optional[Dict[str, Any]]) -> Optional[str]:
    """Texto a injetar no SessionStart SE houver necessidade de re-aplicação. None = silêncio.
    PURO (sem I/O) — testável."""
    if not flag or not flag.get('acao_necessaria'):
        return None
    pend = [d for d in (flag.get('detalhes') or []) if d.get('acao')]
    linhas = [f"  - {d.get('artefato')}: {d.get('status')} → {d.get('acao')}" for d in pend]
    quando = flag.get('verificado_em') or '?'
    return (
        "⚠️ AUTOMAÇÃO INDUSTRIALIZAÇÃO FB↔LF — SA/cron precisam de RE-APLICAÇÃO "
        f"(checagem D8 {quando}):\n" + "\n".join(linhas) +
        "\n  Re-aplicar: `python -m app.odoo.estoque.provisioning.sa_retorno_industrializacao "
        "provisionar --confirmar` (após go do Rafael). Provável upgrade CIEL IT (precedente DFE NFD)."
    )


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description='Monitor anti-upgrade (D8) — checa SAs/crons e grava o flag.')
    ap.add_argument('--flag-path', default=FLAG_PATH_DEFAULT)
    ap.parse_args(argv)
    status = verificar_e_gravar_flag(FLAG_PATH_DEFAULT)
    print(json.dumps(status, default=str, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    import sys
    main(sys.argv[1:])
