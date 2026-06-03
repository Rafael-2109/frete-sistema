"""Testes do _build_task_event_from_result — parser de Task* tools (SDK 0.2.82+).

Substitui o antigo test_todos_parser.py: o SDK 0.2.82+ trocou TodoWrite
(JSON {todos:[]}) pelas tools TaskCreate/TaskUpdate/TaskList, cujo output do
CLI eh TEXTO formatado. `_try_parse_todos` foi removido do client.py e
`_build_task_event_from_result` o sucedeu. Estes testes cobrem a funcao viva.

Formatos parseados (ver docstring da funcao em client.py):
  - TaskCreate: 'Task #N created successfully: <subject>'  -> action=created
  - TaskUpdate: 'Updated task #N ...'                      -> action=updated
  - TaskList:   linhas '#N [status] subject'               -> action=snapshot
"""
import pytest

from app.agente_lojas.sdk.client import _build_task_event_from_result as build


class TestTaskCreate:
    def test_create_com_expected_tool(self):
        ev = build('Task #3 created successfully: Verificar estoque', 'TaskCreate')
        assert ev == {
            'action': 'created',
            'task_id': '3',
            'subject': 'Verificar estoque',
            'status': 'pending',
        }

    def test_create_case_insensitive_e_sem_expected(self):
        ev = build('task #7 CREATED successfully: Conferir recebimento', None)
        assert ev is not None
        assert ev['action'] == 'created'
        assert ev['task_id'] == '7'
        assert ev['subject'] == 'Conferir recebimento'

    def test_task_id_e_string(self):
        ev = build('Task #42 created successfully: X', 'TaskCreate')
        assert ev is not None
        assert ev['task_id'] == '42'  # string, nao int (vem do regex group)


class TestTaskUpdate:
    def test_update_retorna_action_e_id(self):
        ev = build('Updated task #5 status', 'TaskUpdate')
        assert ev == {'action': 'updated', 'task_id': '5'}

    def test_update_anchored_no_inicio(self):
        # 're.match' ancora no inicio — texto que apenas CONTEM o padrao no
        # meio nao deve casar.
        assert build('log: Updated task #5 ocorreu', 'TaskUpdate') is None


class TestTaskList:
    def test_snapshot_multiplas_linhas(self):
        texto = "#1 [completed] Verificar estoque\n#2 [in_progress] Conferir NF"
        ev = build(texto, 'TaskList')
        assert ev is not None
        assert ev['action'] == 'snapshot'
        assert ev['tasks'] == [
            {'task_id': '1', 'status': 'completed', 'subject': 'Verificar estoque'},
            {'task_id': '2', 'status': 'in_progress', 'subject': 'Conferir NF'},
        ]

    def test_tasklist_vazio_emite_snapshot_vazio(self):
        # content='' + expected='TaskList' => snapshot vazio (UI limpa lista).
        ev = build('', 'TaskList')
        assert ev == {'action': 'snapshot', 'tasks': []}

    def test_tasklist_com_lixo_ignora_linhas_invalidas(self):
        ev = build('linha qualquer sem padrao', 'TaskList')
        assert ev == {'action': 'snapshot', 'tasks': []}


class TestLegacyFallbackEGuards:
    def test_fallback_none_so_snapshot_se_todas_linhas_casam(self):
        texto = "#1 [completed] A\n#2 [pending] B"
        ev = build(texto, None)
        assert ev is not None
        assert ev['action'] == 'snapshot'
        assert len(ev['tasks']) == 2

    def test_fallback_none_texto_comum_retorna_none(self):
        assert build('Hello world', None) is None
        assert build('Erro: arquivo nao encontrado', None) is None

    def test_expected_tool_name_evita_falso_positivo(self):
        # Output de Bash contendo 'Updated task #5' NAO deve virar task_event
        # quando o tool real nao e Task* (guard via expected_tool_name).
        assert build('Updated task #5 status', 'Bash') is None

    def test_content_vazio_ou_none_nao_tasklist(self):
        assert build('', None) is None
        assert build(None, None) is None
        assert build(None, 'TaskCreate') is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
