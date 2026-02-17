"""
Carregador de Agent Definitions a partir de .claude/agents/*.md.

Le arquivos Markdown com frontmatter YAML e converte para AgentDefinition
do claude_agent_sdk, permitindo que sub-agents customizados funcionem via
Agent SDK web (Task tool com subagent_type).

Mapeamento frontmatter -> AgentDefinition:
- name -> dict key (subagent_type usado no Task tool)
- description -> AgentDefinition.description
- markdown body (apos ---) -> AgentDefinition.prompt
- tools (csv) -> AgentDefinition.tools (list)
- model -> AgentDefinition.model (mapeado para "opus"|"sonnet"|"haiku"|None)
- skills -> incluido no prompt como secao "Skills Disponiveis"
"""

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger('sistema_fretes')

# Mapeamento de valores de model do frontmatter para valores aceitos pelo SDK.
# AgentDefinition.model aceita Literal["sonnet", "opus", "haiku", "inherit"] | None.
_MODEL_MAP: Dict[str, str] = {
    "opus": "opus",
    "opus-4-6": "opus",
    "opus_4_6": "opus",
    "sonnet": "sonnet",
    "sonnet-4-6": "sonnet",
    "sonnet_4_6": "sonnet",
    "haiku": "haiku",
    "haiku-4-5": "haiku",
    "haiku_4_5": "haiku",
    "inherit": "inherit",
}


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parseia frontmatter YAML e corpo markdown de um arquivo .md.

    Espera formato:
    ---
    key: value
    ---
    corpo markdown

    Args:
        content: Conteudo completo do arquivo .md

    Returns:
        Tupla (frontmatter_dict, markdown_body)

    Raises:
        ValueError: Se o formato do frontmatter estiver invalido
    """
    content = content.strip()

    if not content.startswith("---"):
        raise ValueError("Arquivo nao comeca com '---' (frontmatter ausente)")

    # Encontrar o segundo '---'
    second_sep = content.find("---", 3)
    if second_sep == -1:
        raise ValueError("Frontmatter nao fechado (segundo '---' ausente)")

    frontmatter_raw = content[3:second_sep].strip()
    body = content[second_sep + 3:].strip()

    # Parse YAML simples (key: value) sem depender de pyyaml
    # para frontmatter trivial. Se falhar, tenta yaml.safe_load.
    frontmatter = _parse_yaml_simple(frontmatter_raw)

    if frontmatter is None:
        try:
            import yaml
            frontmatter = yaml.safe_load(frontmatter_raw) or {}
        except Exception as e:
            raise ValueError(f"Frontmatter YAML invalido: {e}")

    return frontmatter, body


def _parse_yaml_simple(raw: str) -> Optional[dict]:
    """
    Parser YAML minimalista para frontmatter simples (key: value por linha).

    Suporta apenas strings simples e listas CSV (tools: Read, Bash, Glob).
    Retorna None se encontrar estrutura complexa que precisa de yaml.safe_load.

    Args:
        raw: String do frontmatter (entre os ---)

    Returns:
        dict com os campos parseados, ou None se parsing simples falhar
    """
    result = {}

    for line in raw.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        colon_idx = line.find(":")
        if colon_idx == -1:
            # Linha sem ':', nao eh key:value simples
            return None

        key = line[:colon_idx].strip()
        value = line[colon_idx + 1:].strip()

        # Detectar estrutura complexa (listas YAML, dicts aninhados)
        if value.startswith("[") or value.startswith("{"):
            return None
        if value.startswith("|") or value.startswith(">"):
            return None

        result[key] = value

    return result


def _map_model(model_str: Optional[str]) -> Optional[str]:
    """
    Mapeia string de model do frontmatter para valor aceito pelo SDK.

    Args:
        model_str: Valor do campo 'model' no frontmatter (ex: "opus-4-6")

    Returns:
        String aceita pelo SDK ("opus"|"sonnet"|"haiku"|"inherit") ou None
    """
    if not model_str:
        return None

    model_lower = model_str.strip().lower()
    mapped = _MODEL_MAP.get(model_lower)

    if mapped is None:
        logger.warning(
            f"[AGENT_LOADER] Model '{model_str}' nao reconhecido. "
            f"Valores aceitos: {list(_MODEL_MAP.keys())}. Usando None (herda do pai)."
        )

    return mapped


def _parse_tools(tools_str: Optional[str]) -> Optional[list]:
    """
    Parseia string CSV de tools para lista.

    Args:
        tools_str: String CSV (ex: "Read, Bash, Glob, Grep")

    Returns:
        Lista de tools ou None se vazio
    """
    if not tools_str:
        return None

    tools = [t.strip() for t in tools_str.split(",") if t.strip()]
    return tools if tools else None


def _build_prompt_with_skills(body: str, skills_str: Optional[str]) -> str:
    """
    Constroi prompt final incluindo skills disponiveis.

    AgentDefinition NAO tem campo 'skills', entao incluimos como texto
    no prompt para que o sub-agent saiba quais skills pode invocar.

    Args:
        body: Corpo markdown do arquivo .md
        skills_str: String CSV de skills (ex: "gerindo-expedicao, cotando-frete")

    Returns:
        Prompt completo com secao de skills (se aplicavel)
    """
    if not skills_str:
        return body

    skills = [s.strip() for s in skills_str.split(",") if s.strip()]
    if not skills:
        return body

    # Evitar duplicacao se o corpo ja contem secao de skills
    if "Skills Disponiveis" in body or "skills disponiveis" in body.lower():
        return body

    skills_section = (
        "\n\n## Skills Disponiveis\n\n"
        "Este agente pode usar as seguintes skills via Skill tool: "
        + ", ".join(skills)
        + ".\n"
    )

    return body + skills_section


def load_agent_definitions(agents_dir: str) -> dict:
    """
    Le .claude/agents/*.md e converte para dict[str, AgentDefinition].

    Cada arquivo .md com frontmatter valido gera uma entrada no dict.
    Arquivos com erro sao logados e ignorados (nao bloqueiam os demais).

    Args:
        agents_dir: Caminho para o diretorio .claude/agents/

    Returns:
        dict[str, AgentDefinition] com agents parseados.
        Retorna dict vazio se diretorio nao existir ou nao tiver agents validos.
    """
    try:
        from claude_agent_sdk import AgentDefinition
    except ImportError:
        logger.debug("[AGENT_LOADER] claude_agent_sdk nao disponivel — agents ignorados")
        return {}

    agents_path = Path(agents_dir)

    if not agents_path.is_dir():
        logger.debug(f"[AGENT_LOADER] Diretorio nao encontrado: {agents_dir}")
        return {}

    agent_files = sorted(agents_path.glob("*.md"))

    if not agent_files:
        logger.debug(f"[AGENT_LOADER] Nenhum arquivo .md em: {agents_dir}")
        return {}

    agents: dict = {}

    for agent_file in agent_files:
        try:
            content = agent_file.read_text(encoding="utf-8")

            frontmatter, body = _parse_frontmatter(content)

            # Campo obrigatorio: name
            name = frontmatter.get("name")
            if not name:
                logger.warning(
                    f"[AGENT_LOADER] {agent_file.name}: frontmatter sem 'name' — ignorado"
                )
                continue

            # Campo obrigatorio: description
            description = frontmatter.get("description")
            if not description:
                logger.warning(
                    f"[AGENT_LOADER] {agent_file.name}: frontmatter sem 'description' — ignorado"
                )
                continue

            # Campos opcionais
            model = _map_model(frontmatter.get("model"))
            tools = _parse_tools(frontmatter.get("tools"))
            skills_str = frontmatter.get("skills")

            # Prompt = corpo markdown + skills disponiveis
            prompt = _build_prompt_with_skills(body, skills_str)

            # Construir AgentDefinition
            agent_def = AgentDefinition(
                description=description,
                prompt=prompt,
                tools=tools,
                model=model,
            )

            agents[name] = agent_def

            logger.debug(
                f"[AGENT_LOADER] Carregado: {name} | "
                f"model={model} | tools={tools} | "
                f"prompt_len={len(prompt)} chars"
            )

        except Exception as e:
            logger.warning(
                f"[AGENT_LOADER] Erro ao carregar {agent_file.name}: {e} — ignorado"
            )
            continue

    if agents:
        logger.info(
            f"[AGENT_LOADER] {len(agents)} agents carregados: {list(agents.keys())}"
        )

    return agents
