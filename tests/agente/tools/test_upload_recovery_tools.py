"""Testes das MCP tools list_session_uploads + recover_upload — IMP-2026-06-19-007."""
import asyncio
from datetime import timedelta

from app.utils.timezone import agora_brasil_naive


def _run(coro):
    return asyncio.run(coro)


def test_recover_upload_inexistente_retorna_none(db):
    """Service: sem manifesto ativo para (user, file_id) -> None."""
    from app.agente.services.upload_recovery_service import recuperar_upload
    assert recuperar_upload(78, 'nao-existe', target_session_id='s9') is None


def test_list_session_uploads_tool_vazio(db):
    """Tool: usuario sem uploads -> count=0 e mensagem 'Nenhum...'."""
    from app.agente.tools import session_search_tool as sst
    sst.set_current_user_id(91001)
    try:
        result = _run(sst.list_session_uploads.handler({}))
    finally:
        sst.clear_current_user_id()
    assert result["structuredContent"]["count"] == 0
    assert "Nenhum" in result["content"][0]["text"]


def test_list_session_uploads_tool_lista_recentes(db):
    """Tool: lista uploads do usuario (recencia + escopo), expoe file_id."""
    from app.agente.models import AgenteUpload
    from app.agente.tools import session_search_tool as sst
    now = agora_brasil_naive()
    db.session.add(AgenteUpload(
        user_id=91002, session_id='s1', file_id='ff11', original_name='nota.xlsx',
        safe_name='ff11_nota.xlsx', s3_key='agente-uploads/91002/ff11_nota.xlsx',
        file_type='excel', size_bytes=10, criado_em=now, ativo=True))
    db.session.add(AgenteUpload(
        user_id=91002, session_id='s0', file_id='ee22', original_name='antigo.pdf',
        safe_name='ee22_antigo.pdf', s3_key='k', file_type='pdf', size_bytes=5,
        criado_em=now - timedelta(days=30), ativo=True))
    db.session.flush()
    sst.set_current_user_id(91002)
    try:
        result = _run(sst.list_session_uploads.handler({"dias": 7}))
    finally:
        sst.clear_current_user_id()
    structured = result["structuredContent"]
    assert structured["count"] == 1
    nomes = {u["original_name"] for u in structured["uploads"]}
    assert nomes == {"nota.xlsx"}
    assert structured["uploads"][0]["file_id"] == "ff11"


def test_recover_upload_tool_file_id_vazio_erro(db):
    """Tool: file_id vazio -> is_error (validacao antes de tocar o service)."""
    from app.agente.tools import session_search_tool as sst
    sst.set_current_user_id(91003)
    try:
        result = _run(sst.recover_upload.handler({"file_id": "", "target_session_id": "s"}))
    finally:
        sst.clear_current_user_id()
    assert result.get("is_error") is True


def test_recover_upload_tool_inexistente_erro(db):
    """Tool: file_id sem manifesto -> is_error com mensagem de indisponivel."""
    from app.agente.tools import session_search_tool as sst
    sst.set_current_user_id(91004)
    try:
        result = _run(sst.recover_upload.handler(
            {"file_id": "nao-existe", "target_session_id": "sess-atual"}))
    finally:
        sst.clear_current_user_id()
    assert result.get("is_error") is True
