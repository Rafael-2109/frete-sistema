"""Retomada adaptativa de sessao idle (caso conversa-nacom-1781122686256, 2026-06-10).

Bug: ao retomar sessao com idle >= 2h, a idle rotation criava session_id novo
SEM transferir nenhum contexto — agente "zerado" apesar da UI prometer
"Continue a conversa abaixo". Agravante: o briefing injetava o resumo da
ULTIMA sessao global (assunto errado).

Fix adaptativo (decisao Rafael 2026-06-10):
- Transcript PEQUENO (<= AGENT_ROTATION_RESUME_MAX_KB): NAO rotaciona —
  resume real do SDK (custo de cache write pequeno, pago uma vez).
- Transcript GRANDE: rotaciona (controle de custo mantido) MAS leva
  <sessao_anterior_rotacionada> com resumo M1 + cauda GENEROSA das ultimas
  mensagens (AGENT_ROTATION_TAIL_CHARS, default 12K chars).
"""

from app.agente.routes._helpers import build_rotation_continuity_xml


def _msgs(n=12, char_por_msg=400):
    out = []
    for i in range(n):
        role = 'user' if i % 2 == 0 else 'assistant'
        out.append({'role': role, 'content': f'mensagem {i:02d} ' + ('x' * char_por_msg)})
    return out


class TestBuildRotationContinuityXml:
    def test_inclui_resumo_e_cauda(self):
        summary = {'resumo': 'Avaliacao do contexto de boot do agente',
                   'pendencias': 'gerar versao PDF'}
        xml = build_rotation_continuity_xml(
            summary=summary, messages=_msgs(6, 100), idle_hours=29.6,
            tail_chars=12000, per_msg_chars=3000,
        )
        assert xml is not None
        assert '<sessao_anterior_rotacionada' in xml
        assert 'Avaliacao do contexto de boot' in xml      # resumo M1
        assert 'mensagem 05' in xml                          # ultima mensagem presente
        assert 'idle_horas="29.6"' in xml

    def test_cauda_prioriza_ultimas_mensagens(self):
        # 12 msgs x ~400c com teto de 2000c de cauda: so as ULTIMAS cabem
        xml = build_rotation_continuity_xml(
            summary=None, messages=_msgs(12, 400), idle_hours=5.0,
            tail_chars=2000, per_msg_chars=3000,
        )
        assert 'mensagem 11' in xml          # a mais recente SEMPRE entra
        assert 'mensagem 00' not in xml      # a mais antiga cai fora do teto

    def test_cauda_generosa_default_carrega_mais_que_2k(self):
        # Pedido explicito do Rafael: cauda maior que 1-2K chars
        xml = build_rotation_continuity_xml(
            summary=None, messages=_msgs(12, 1500), idle_hours=3.0,
            tail_chars=12000, per_msg_chars=3000,
        )
        assert len(xml) > 5000

    def test_mensagem_individual_respeita_cap(self):
        msgs = [{'role': 'assistant', 'content': 'y' * 50_000}]
        xml = build_rotation_continuity_xml(
            summary=None, messages=msgs, idle_hours=3.0,
            tail_chars=12000, per_msg_chars=3000,
        )
        assert len(xml) < 6000  # 1 msg capada a 3000 + envelope

    def test_escapa_xml_no_conteudo(self):
        msgs = [{'role': 'user', 'content': 'comparar <embarques> & "fretes"'}]
        xml = build_rotation_continuity_xml(
            summary=None, messages=msgs, idle_hours=3.0,
            tail_chars=12000, per_msg_chars=3000,
        )
        assert '<embarques>' not in xml      # conteudo nao vira tag
        assert '&lt;embarques&gt;' in xml

    def test_sem_nada_retorna_none(self):
        assert build_rotation_continuity_xml(
            summary=None, messages=[], idle_hours=3.0,
            tail_chars=12000, per_msg_chars=3000,
        ) is None


class TestResumeFallbackNotice:
    def test_notice_rotacao_explica_continuidade(self):
        from app.agente.sdk.hooks import _build_resume_fallback_notice
        notice = _build_resume_fallback_notice('rotated')
        assert 'continua' in notice.lower() or 'continuidade' in notice.lower()
        # NAO pode usar o texto de falha de resume
        assert 'não pôde ser restaurada' not in notice

    def test_notice_default_permanece_resume_failed(self):
        from app.agente.sdk.hooks import _build_resume_fallback_notice
        notice = _build_resume_fallback_notice('resume_failed')
        assert 'não pôde ser restaurada' in notice
