"""
Custom Tool MCP: build_artifact

Permite ao agente criar artifact (bundle.html auto-contido) renderizado em
modal no chat web. Pipeline:
  1. Agente chama tool com {titulo, spec={components, dependencies?}}
  2. Tool cria AgenteArtifact (status=queued) e enfileira RQ job
  3. Tool retorna {uuid, token, render_url, status_url}
  4. Agente responde texto + marker [ARTIFACT:<uuid>]
  5. Frontend detecta marker, faz polling status, abre modal quando ready

Use APENAS no chat web (NAO no Teams — sem render integrado de artifact).
Skill complementar: .claude/skills/gerando-artifact/SKILL.md

Output schema:
    {
        "uuid": str,           # UUID4 do artifact
        "token": str,          # token assinado para URL publica
        "render_url": str,     # pagina wrapper com iframe sandboxed
        "status_url": str,     # JSON polling endpoint
        "marker": str          # "[ARTIFACT:<uuid>]" para incluir na resposta
    }
"""

import logging
from typing import Annotated, Any

logger = logging.getLogger(__name__)


# =====================================================================
# Flask app context helper (BUG IMP-2026-05-12-001)
# =====================================================================
# MCP tools rodam em thread "sdk-pool-daemon" do Claude Agent SDK, separada
# da thread Flask. ContextVar nao se propaga, e mais importante: o app
# context Flask nao esta ativo nessa thread — qualquer chamada a db.session,
# current_app, ou create_app() fora do contexto levanta:
#   RuntimeError: Working outside of application context.
#
# Solucao: detectar se ja estamos em app context (raro — quando chamado
# via Teams dispatcher que ja roda em contexto). Se nao, criar via
# create_app() e usar `with ctx:` no handler.
#
# Mesmo padrao usado em memory_mcp_tool._get_app_context() e
# session_search_tool. Aqui reaproveitamos via import direto.

def _get_app_context():
    """Retorna context manager Flask app, ou None se ja estamos em contexto."""
    try:
        from flask import current_app
        _ = current_app.name  # raise se sem contexto
        return None
    except RuntimeError:
        from app import create_app
        app = create_app()
        return app.app_context()


# Output schema MCP Enhanced
ARTIFACT_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "uuid": {"type": "string"},
        "token": {"type": "string"},
        "render_url": {"type": "string"},
        "status_url": {"type": "string"},
        "marker": {"type": "string"},
    },
    "required": ["uuid", "token", "render_url", "marker"],
    "additionalProperties": False,
}


try:
    from claude_agent_sdk import ToolAnnotations
    from app.agente.tools._mcp_enhanced import (
        enhanced_tool,
        create_enhanced_mcp_server,
    )

    @enhanced_tool(
        "build_artifact",
        "Cria um artifact (bundle.html auto-contido com React + TS + Tailwind) "
        "renderizado em modal no chat web do agente. USE APENAS no chat web — "
        "NAO funciona no Teams. "
        "Quando usar: usuario pede 'monte um dashboard', 'crie uma visualizacao "
        "interativa', 'faca uma tela com filtros', ou qualquer UI multi-componente. "
        "NAO usar para tabelas simples (markdown), graficos pontuais (chart inline) "
        "ou respostas em texto. "
        "Como usar: prepare uma spec com {components: [{path, content}], "
        "dependencies?: {name: version}}. O campo 'components' deve conter "
        "OBRIGATORIAMENTE 'src/App.tsx' como entry component. Outros componentes "
        "podem ser referenciados via import com path alias '@/' (que aponta para "
        "src/). Tailwind CSS esta pre-configurado. Apos chamar a tool, RESPONDA "
        "AO USUARIO com texto curto + o marker RETORNADO no campo 'marker' do "
        "structuredContent (formato '[ARTIFACT:<token>]'). O frontend detecta o "
        "marker e renderiza o card de visualizacao. "
        "Build leva 30-60 segundos em background. "
        "Exemplo: build_artifact({"
        "'titulo': 'Custos Frete Mai/2026', "
        "'spec': {"
        "'components': ["
        "{'path': 'src/App.tsx', 'content': '...React entry...'}, "
        "{'path': 'src/Chart.tsx', 'content': '...component...'}"
        "], "
        "'dependencies': {'recharts': '^2.10.0'}"
        "}}). "
        "Limites: 5 artifacts/usuario/hora, 5MB bundle final, 200KB por arquivo.",
        {
            "titulo": Annotated[
                str,
                "Titulo curto e amigavel do artifact (max 200 chars). Exemplo: "
                "'Dashboard Fretes Mai/2026', 'Custos por Transportadora'.",
            ],
            "spec": Annotated[
                dict,
                "Spec do artifact com {components: [{path, content}], "
                "dependencies?: {name: version}}. 'components' deve conter "
                "'src/App.tsx'. 'path' relativo 'src/'. 'dependencies' opcional "
                "(libs alem do baseline Tailwind/clsx/lucide).",
            ],
        },
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
        output_schema=ARTIFACT_OUTPUT_SCHEMA,
    )
    async def build_artifact(args: dict[str, Any]) -> dict[str, Any]:
        """
        Cria AgenteArtifact e enfileira build async. Retorna URLs publicas.

        Args:
            args: {"titulo": str, "spec": dict}

        Returns:
            MCP tool response com texto + structuredContent.
        """
        titulo = (args.get("titulo") or "").strip()
        spec = args.get("spec")

        if not titulo:
            return {
                "content": [{"type": "text", "text":
                    "[ERRO] Parametro 'titulo' obrigatorio."}],
                "is_error": True,
            }
        if not isinstance(spec, dict):
            return {
                "content": [{"type": "text", "text":
                    "[ERRO] Parametro 'spec' deve ser dict."}],
                "is_error": True,
            }

        # Resolver user_id e session_id do contexto
        try:
            from app.agente.tools.memory_mcp_tool import get_current_user_id
            from app.agente.config.permissions import get_current_session_id
            user_id = get_current_user_id()
        except RuntimeError as e:
            return {
                "content": [{"type": "text", "text":
                    f"[ERRO] Contexto invalido: {e}"}],
                "is_error": True,
            }
        except ImportError as e:
            logger.error(f"[ARTIFACT_TOOL] import permissions: {e}")
            return {
                "content": [{"type": "text", "text":
                    "[ERRO] Contexto nao disponivel."}],
                "is_error": True,
            }

        session_id = get_current_session_id()

        # FIX IMP-2026-05-12-001: garantir Flask app context.
        # MCP tool roda em sdk-pool-daemon thread sem app context. service
        # faz db.session.add/commit + current_app.config[SECRET_KEY] (token
        # signing) — ambos exigem app context ativo.
        ctx = _get_app_context()

        def _do_create():
            """
            Extrai TODOS os atributos do ORM em valores primitivos antes do
            context fechar — caso contrario `with ctx:` exit deta-cha
            session e qualquer acesso subsequente a artifact.uuid levanta
            DetachedInstanceError.
            """
            from app.agente.services import artifact_service
            artifact = artifact_service.create_artifact(
                user_id=user_id,
                session_id=session_id,
                titulo=titulo,
                spec=spec,
            )
            token = artifact_service.generate_token(artifact.uuid)
            # Retorna primitivos (nao o ORM) — seguro fora do ctx
            return {
                'uuid': artifact.uuid,
                'token': token,
            }

        # Criar artifact via service (dentro de app context).
        # Wrapper garante rollback defensivo se _do_create levantar exception
        # apos algum INSERT/UPDATE pendente — sem isso, session fica abortada
        # e contamina pool (InFailedSqlTransaction em outras threads).
        def _do_create_with_rollback():
            try:
                return _do_create()
            except Exception:
                try:
                    from app import db
                    db.session.rollback()
                except Exception:
                    pass
                raise

        try:
            from app.agente.services import artifact_service
            if ctx is None:
                created = _do_create_with_rollback()
            else:
                with ctx:
                    created = _do_create_with_rollback()
            artifact_uuid = created['uuid']
            token = created['token']
        except artifact_service.ArtifactRateLimitError as e:
            return {
                "content": [{"type": "text", "text":
                    f"[ERRO] Rate limit: {e}. Aguarde 1 hora ou conclua artifacts pendentes."}],
                "is_error": True,
            }
        except artifact_service.ArtifactError as e:
            return {
                "content": [{"type": "text", "text":
                    f"[ERRO] Spec invalida: {e}"}],
                "is_error": True,
            }
        except Exception as e:
            logger.error(f"[ARTIFACT_TOOL] create falhou: {e}", exc_info=True)
            return {
                "content": [{"type": "text", "text":
                    f"[ERRO] Falha ao criar artifact: {str(e)[:200]}"}],
                "is_error": True,
            }

        render_url = f"/agente/artifact/{token}"
        status_url = f"/agente/artifact/{token}/status"
        # Marker contem o TOKEN assinado (nao uuid) — frontend usa direto
        # para polling e iframe src sem precisar resolver uuid->token.
        marker = f"[ARTIFACT:{token}]"

        logger.info(
            f"[ARTIFACT_TOOL] criado uuid={artifact_uuid[:8]} "
            f"user={user_id} session={session_id}"
        )

        return {
            "content": [{"type": "text", "text":
                f"[OK] Artifact '{titulo}' enfileirado para build. "
                f"Inclua na resposta o marker {marker} para renderizar."}],
            "structuredContent": {
                "uuid": artifact_uuid,
                "token": token,
                "render_url": render_url,
                "status_url": status_url,
                "marker": marker,
            },
        }

    # Criar MCP server in-process com Enhanced wrapper
    artifact_server = create_enhanced_mcp_server(
        name="artifact",
        version="1.0.0",
        tools=[build_artifact],
    )

    logger.info(
        "[ARTIFACT_TOOL] Custom Tool MCP 'artifact' registrada "
        "(1 operacao, Enhanced v1.0)"
    )

except ImportError as e:
    artifact_server = None
    logger.debug(f"[ARTIFACT_TOOL] claude_agent_sdk nao disponivel: {e}")
