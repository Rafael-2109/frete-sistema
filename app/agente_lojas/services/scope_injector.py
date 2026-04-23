"""
Scope injector — constroi bloco XML de escopo de loja para o prompt.

Invocado pelo hook `user_prompt_submit` a cada turno. Resultado:

    <loja_context>
      loja_ids_permitidas: [3]
      loja_default: 3
      pode_ver_todas: false
      usuario_loja_hora_id: 3
    </loja_context>

Para admin (sem restricao):

    <loja_context>
      loja_ids_permitidas: null
      pode_ver_todas: true
    </loja_context>
"""
from typing import Optional


def build_loja_context_block(
    perfil: str,
    loja_hora_id: Optional[int],
) -> str:
    """Retorna bloco XML de escopo de loja para injecao no prompt.

    Args:
        perfil: `current_user.perfil` ('administrador', 'vendedor', etc.)
        loja_hora_id: `current_user.loja_hora_id` (NULL = todas)

    Returns:
        string XML pronta para concatenar no contexto do turno
    """
    # Admin ou usuario sem loja setada -> acesso total
    if perfil == 'administrador' or loja_hora_id is None:
        return (
            "<loja_context>\n"
            "  loja_ids_permitidas: null\n"
            "  pode_ver_todas: true\n"
            "</loja_context>"
        )

    # Usuario escopado a 1 loja
    return (
        "<loja_context>\n"
        f"  loja_ids_permitidas: [{loja_hora_id}]\n"
        f"  loja_default: {loja_hora_id}\n"
        "  pode_ver_todas: false\n"
        f"  usuario_loja_hora_id: {loja_hora_id}\n"
        "</loja_context>"
    )
