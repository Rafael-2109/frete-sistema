"""
Verifiers de qualidade de resposta — B2, Onda 2.

SHADOW: estas funções existem para uso shadow/teste. O ponto de ativação
(enqueue no loop principal) virá na Onda 3 sob a flag USE_AGENT_VERIFY.

Nenhum caller ativo — nenhum hook/SSE/loop chama estas funções nesta versão.

Verifiers implementados:
    - verify_arithmetic: valida inconsistências aritméticas via Sonnet (Parte A)
    - verify_domain: valida entidades referenciadas contra a ontologia canônica (Parte B)

Wiring futuro (Onda 3, USE_AGENT_VERIFY):
    - verify_domain será enfileirado no loop como shadow gate, recebendo o step
      antes da execução e logando issues sem bloquear (flag-gated).
    - Guards de execução (G021/G031/etc.) permanecem responsabilidade das skills
      executoras (dry-run em app/odoo/estoque/), nunca duplicados aqui.
"""
import logging
import re
from typing import Callable, List, Optional

logger = logging.getLogger('sistema_fretes')

SONNET_MODEL = 'claude-sonnet-5'

ARITHMETIC_SYSTEM_PROMPT = (
    "Você verifica EXCLUSIVAMENTE inconsistências ARITMÉTICAS em respostas.\n"
    "Critérios:\n"
    "  - Soma de itens não bate com total declarado\n"
    "  - Percentual diverge dos valores absolutos\n"
    "  - Contagem de linhas contradiz quantidade mencionada\n\n"
    "NÃO avalie: qualidade da escrita, completude, formatação ou "
    "informações que não envolvem cálculos.\n\n"
    "Você PODE raciocinar passo a passo. Mas TERMINE a resposta com uma linha de "
    "veredito, exatamente num destes formatos:\n"
    "  VEREDITO: OK\n"
    "  VEREDITO: ERRO — <frase curta>  "
    "(ex: 'VEREDITO: ERRO — total diz 5 itens mas tabela tem 8')"
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


def _interpreta_veredito_aritmetico(resultado: str) -> dict:
    """Interpreta a saída do verifier aritmético de forma robusta a raciocínio.

    Bug 2026-06-03 (42/201 em PROD): o Sonnet é um modelo de raciocínio e ignora
    "responda EXATAMENTE OK" — raciocina passo-a-passo e conclui com "OK"/✓ quando
    a aritmética está correta. O parser antigo (`resultado.upper() == 'OK'`) tratava
    qualquer raciocínio (len≫5, ≠ 'OK') como inconsistência → falso-positivo.

    Discrimina pela CONCLUSÃO, não por igualdade exata nem pela palavra "ERRO"
    (uma descrição de discrepância pode não conter "ERRO"):
      1. Veredito estruturado `VEREDITO: OK` / `VEREDITO: ERRO ...` (novo prompt) — autoritativo.
      2. Fallback (sem veredito): conclusão = última linha não-vazia normalizada. Se for
         'OK' → sem erro; senão → inconsistência (preserva o contrato p/ descrições de
         erro como 'Total diz 20 mas soma 18').
    """
    texto = (resultado or '').strip()
    if not texto:
        return {'ok': True, 'issues': []}

    # 1) Veredito estruturado explícito (novo prompt).
    m = re.search(r'VEREDITO\s*:\s*(.+)', texto, re.IGNORECASE | re.DOTALL)
    if m:
        verdito = m.group(1).strip()
        if re.match(r'OK\b', verdito, re.IGNORECASE) and not re.search(r'\bERRO\b', verdito, re.IGNORECASE):
            return {'ok': True, 'issues': []}
        return {'ok': False, 'issues': [texto]}

    # 2) Fallback: conclusão = última linha não-vazia (normalizada s/ pontuação/markdown).
    linhas = [ln.strip() for ln in texto.splitlines() if ln.strip()]
    ultima_norm = re.sub(r'[^A-Za-z]', '', linhas[-1]).upper() if linhas else ''
    if ultima_norm == 'OK':
        return {'ok': True, 'issues': []}
    return {'ok': False, 'issues': [texto]}


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
        veredito = _interpreta_veredito_aritmetico(raw)
        if veredito['ok']:
            logger.debug('[verify_arithmetic] OK — nenhuma inconsistência aritmética')
        else:
            logger.warning(
                f"[verify_arithmetic] inconsistência detectada: {veredito['issues'][0][:200]}"
            )
        return veredito

    except Exception as exc:
        # Best-effort: falha silenciosa — verifier nunca quebra o caller
        logger.debug(f'[verify_arithmetic] erro ignorado (best-effort): {exc}')
        return {'ok': True, 'issues': []}


def verify_domain(
    step: Optional[dict],
    user_id: int,
    extra_checks: Optional[List[Callable]] = None,
) -> dict:
    """Verifier de domínio — Parte B (B2-domain, Onda 2).

    Valida se as entidades referenciadas em um passo de plano existem como
    nós canônicos na ontologia (clientes/produtos/transportadoras bootstrapados
    por D2, consultáveis via D4 `query_ontology_entities`).

    Escopo ONTOLÓGICO (consistência do plano):
        - Sinaliza referências a entidades DESCONHECIDAS como issues.
        - NÃO duplica guards de execução de estoque (G021/G031/etc.) — esses
          são enforced em EXECUÇÃO pelas skills de estoque via dry-run
          (app/odoo/estoque/). B2-domain cobre apenas a consistência ontológica.

    Args:
        step: Dict com o passo de plano. Campos inspecionados:
              - ``entities`` (list[str]): entidades explicitamente listadas.
                Se ausente, nenhuma entidade é verificada (sem 'subject' mining).
              - ``subject`` (str): ignorado para extração automática (sem heurística
                de NER nesta versão — evita falso positivos).
        user_id: ID do usuário para consulta ontológica (D4).
        extra_checks: Lista opcional de callables ``fn(step, user_id) -> list[str]``
                      para validadores adicionais plugáveis no futuro.
                      Interface de extensão — guards de estoque NÃO devem ser
                      adicionados aqui; pertencem às skills executoras.

    Returns:
        {'ok': bool, 'issues': list[str]}
        - ok=True, issues=[]: todas as entidades encontradas na ontologia (ou
          nenhuma entidade a verificar).
        - ok=False, issues=[...]: entidades desconhecidas com descrição.

    Best-effort: qualquer exceção retorna ok=True, issues=[] sem propagar.

    SHADOW: não há caller ativo nesta versão. O enqueue no loop virá na
    Onda 3 sob USE_AGENT_VERIFY (feature_flags.py, OFF por default).

    Wiring futuro:
        A ativação seguirá o padrão de verify_arithmetic: flag
        USE_AGENT_VERIFY habilitará o enqueue shadow no loop principal,
        recebendo o step antes da execução e logando issues sem bloquear.
    """
    # Guard: entrada nula → ok sem validar
    if not step:
        return {'ok': True, 'issues': []}

    try:
        issues: List[str] = []

        # Extrai entidades explícitas do campo 'entities' (lista de strings)
        # NÃO extrai do 'subject' — evita falso positivos por NER impreciso
        entities = step.get('entities')
        if not entities or not isinstance(entities, list):
            # Sem entidades explícitas → nada a validar ontologicamente
            _run_extra_checks(step, user_id, extra_checks, issues)
            ok = len(issues) == 0
            return {'ok': ok, 'issues': issues}

        # Importa a função núcleo da ontologia (D4)
        from app.agente.tools.ontology_query_tool import query_ontology_entities

        # Valida cada entidade individualmente
        for entity in entities:
            if not entity or not isinstance(entity, str):
                continue

            results = query_ontology_entities(
                user_id=user_id,
                name_like=entity,
                limit=1,
            )

            if not results:
                issue_msg = f'entidade desconhecida na ontologia: {entity}'
                issues.append(issue_msg)
                logger.warning(
                    '[verify_domain] %s (user_id=%s, step_action=%s)',
                    issue_msg, user_id, step.get('action', '?'),
                )

        # Executa hooks extras plugáveis (sem guards de estoque)
        _run_extra_checks(step, user_id, extra_checks, issues)

        ok = len(issues) == 0
        if ok:
            logger.debug('[verify_domain] OK — todas as entidades encontradas na ontologia')
        return {'ok': ok, 'issues': issues}

    except Exception as exc:
        # Best-effort: falha silenciosa — verifier nunca quebra o caller
        logger.debug(f'[verify_domain] erro ignorado (best-effort): {exc}')
        return {'ok': True, 'issues': []}


def _run_extra_checks(
    step: dict,
    user_id: int,
    extra_checks: Optional[List[Callable]],
    issues: List[str],
) -> None:
    """Executa hooks extra_checks plugáveis e acumula issues na lista fornecida.

    Cada callable recebe (step, user_id) e retorna list[str].
    Falhas individuais são silenciadas (best-effort por hook).

    NÃO é o lugar para guards de estoque (G021/G031/etc.) — esses pertencem
    às skills executoras com dry-run em app/odoo/estoque/.
    """
    if not extra_checks:
        return
    for check_fn in extra_checks:
        try:
            extra_issues = check_fn(step, user_id)
            if extra_issues:
                issues.extend(extra_issues)
        except Exception as exc:
            logger.debug(f'[verify_domain] extra_check ignorado (best-effort): {exc}')
