"""
Verifiers de qualidade de resposta — B2, Onda 2.

SHADOW: estas funções existem para uso shadow/teste. O ponto de ativação
(enqueue no loop principal) virá na Onda 3 sob a flag USE_AGENT_VERIFY.

Nenhum caller ativo — nenhum hook/SSE/loop chama estas funções nesta versão.

Verifiers implementados:
    - verify_arithmetic: valida inconsistências aritméticas via Sonnet (Parte A)

Verifier diferido:
    - domain: depende de ontologia ainda não bootstrapada (Parte C, futura)
"""
import logging
from typing import Optional

logger = logging.getLogger('sistema_fretes')

SONNET_MODEL = 'claude-sonnet-4-6'

ARITHMETIC_SYSTEM_PROMPT = (
    "Você verifica EXCLUSIVAMENTE inconsistências ARITMÉTICAS em respostas.\n"
    "Critérios:\n"
    "  - Soma de itens não bate com total declarado\n"
    "  - Percentual diverge dos valores absolutos\n"
    "  - Contagem de linhas contradiz quantidade mencionada\n\n"
    "NÃO avalie: qualidade da escrita, completude, formatação ou "
    "informações que não envolvem cálculos.\n\n"
    "Se não há erro aritmético, responda EXATAMENTE: OK\n"
    "Se encontrar um erro, descreva em UMA frase curta "
    "(ex: 'Total diz 5 itens mas tabela tem 8')."
)


def _call_sonnet_verifier(prompt: str) -> str:
    """Chama Sonnet com ARITHMETIC_SYSTEM_PROMPT e retorna texto da resposta.

    Extraído como helper independente para facilitar mock nos testes
    (mesmo padrão de step_judge._call_haiku_judge).
    """
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=300,
        system=ARITHMETIC_SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': prompt}],
    )
    for block in resp.content:
        if getattr(block, 'type', None) == 'text':
            return block.text
    return ''


def verify_arithmetic(
    response_text: Optional[str],
    contexto: Optional[str] = None,
) -> dict:
    """Verifier aritmético — Parte A (B2, Onda 2).

    Promove a mecânica de revisão de _self_correct_response (client.py ~:790)
    a VEREDITO estruturado. Ao contrário do auto-corrector (advisory, injeção
    de texto na resposta), este verifier retorna um dict com ok/issues para
    uso em gate de qualidade (futuro, Onda 3).

    Reusa o mesmo modelo (Sonnet) e escopo (inconsistências aritméticas) do
    _self_correct_response, mas como saída estruturada em vez de texto livre.

    Args:
        response_text: Texto completo da resposta do agente para verificar.
        contexto: Contexto opcional (session_id, usuário, etc.) incluído no
                  prompt para rastreabilidade.

    Returns:
        {'ok': bool, 'issues': list[str]}
        - ok=True, issues=[]: sem erros aritméticos detectados
        - ok=False, issues=[...]: erros encontrados com descrição

    Best-effort: qualquer exceção retorna ok=True, issues=[] sem propagar.

    SHADOW: não há caller ativo nesta versão. O enqueue no loop (gate Onda 3)
    virá sob USE_AGENT_VERIFY (feature_flags.py, OFF por default).
    """
    # Guard: entrada vazia/nula → ok sem chamar LLM
    if not response_text:
        return {'ok': True, 'issues': []}

    try:
        # Monta prompt com contexto opcional
        partes = []
        if contexto:
            partes.append(f"Contexto: {contexto}\n")
        partes.append(f"Resposta a verificar:\n{response_text[:3000]}")
        prompt = ''.join(partes)

        raw = _call_sonnet_verifier(prompt)
        resultado = raw.strip() if raw else ''

        # "OK" (case-insensitive) ou resultado muito curto = sem problemas
        if not resultado or resultado.upper() == 'OK' or len(resultado) < 5:
            logger.debug('[verify_arithmetic] OK — nenhuma inconsistência aritmética')
            return {'ok': True, 'issues': []}

        logger.warning(f'[verify_arithmetic] inconsistência detectada: {resultado}')
        return {'ok': False, 'issues': [resultado]}

    except Exception as exc:
        # Best-effort: falha silenciosa — verifier nunca quebra o caller
        logger.debug(f'[verify_arithmetic] erro ignorado (best-effort): {exc}')
        return {'ok': True, 'issues': []}
