#!/usr/bin/env python3
"""
Hook de Validacao para Pedidos Criticos

Este hook e executado antes de operacoes que envolvem pedidos de clientes criticos
(Atacadao, Assai), alertando sobre possiveis impactos.

Uso: Configurado em .claude/settings.local.json como PreToolUse hook
"""

import json
import sys
import re

# Clientes criticos e seu impacto no faturamento
CLIENTES_CRITICOS = {
    "atacadao": {"impacto": "50%", "gestor": "Junior", "prioridade": "MAXIMA"},
    "assai": {"impacto": "13%", "gestor": "Junior/Miler", "prioridade": "ALTA"},
    "gomes da costa": {"impacto": "4%", "gestor": "Fernando", "prioridade": "MEDIA"},
    "mateus": {"impacto": "3%", "gestor": "Miler", "prioridade": "MEDIA"},
}

# Padroes para identificar operacoes em pedidos
PEDIDO_PATTERNS = [
    r"VCD\d+",
    r"num_pedido",
    r"separacao.*pedido",
]


def identify_client(content: str) -> dict | None:
    """Identifica se o conteudo menciona um cliente critico."""
    content_lower = content.lower()

    for cliente, info in CLIENTES_CRITICOS.items():
        if cliente in content_lower:
            return {"cliente": cliente, **info}

    return None


def is_pedido_operation(tool_input: dict) -> bool:
    """Verifica se a operacao envolve pedidos."""
    content = json.dumps(tool_input).lower()

    for pattern in PEDIDO_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return True

    return False


def main():
    """
    Processa o evento do hook.

    Para PreToolUse, pode retornar:
    - Exit code 0: Continua execucao
    - Exit code 1: Bloqueia execucao (com mensagem)
    """
    try:
        input_data = sys.stdin.read()
        if not input_data:
            sys.exit(0)

        event = json.loads(input_data)

        tool_name = event.get("tool_name", "")
        tool_input = event.get("tool_input", {})

        # Apenas valida Write e Edit
        if tool_name not in ["Write", "Edit"]:
            sys.exit(0)

        # Verifica se e operacao de pedido
        if not is_pedido_operation(tool_input):
            sys.exit(0)

        # Verifica se envolve cliente critico
        content = json.dumps(tool_input)
        cliente_info = identify_client(content)

        if cliente_info:
            # Emite alerta (mas nao bloqueia)
            print(
                f"\n⚠️  ALERTA: Operacao envolve cliente critico!\n"
                f"   Cliente: {cliente_info['cliente'].upper()}\n"
                f"   Impacto no faturamento: {cliente_info['impacto']}\n"
                f"   Gestor responsavel: {cliente_info['gestor']}\n"
                f"   Prioridade: {cliente_info['prioridade']}\n",
                file=sys.stderr,
            )

            # Se for Atacadao, alerta extra
            if cliente_info["cliente"] == "atacadao":
                print(
                    "   🚨 ATACADAO representa 50% do faturamento!\n"
                    "   Certifique-se de que a operacao esta correta.\n",
                    file=sys.stderr,
                )

        # Nao bloqueia, apenas alerta
        sys.exit(0)

    except json.JSONDecodeError:
        sys.exit(0)
    except Exception as e:
        print(f"[VALIDACAO] Erro: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
