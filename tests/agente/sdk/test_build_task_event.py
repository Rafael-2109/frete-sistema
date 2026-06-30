"""
Parser de eventos Task* do MOTOR (AgentClient._build_task_event).

Migrado de tests/agente_lojas/test_task_event_parser.py (fork aposentado na FASE B
do cutover agente_lojas). O motor tem API propria — (tool_name, original_input,
result_content): TaskCreate/Update usam original_input + task_id extraido do texto;
TaskList parseia o texto multi-linha do CLI. E generico (nao depende do perfil), por
isso testado via get_client('web').
"""
import pytest

from app.agente.sdk.client import get_client


@pytest.fixture(scope='module')
def client():
    return get_client('web')


def test_task_create_extrai_id_do_texto_e_subject_do_input(client):
    evt = client._build_task_event(
        'TaskCreate',
        {'subject': 'Verificar estoque'},
        'Task #3 created successfully: Verificar estoque',
    )
    assert evt == {
        'action': 'created', 'task_id': '3',
        'subject': 'Verificar estoque', 'description': '', 'status': 'pending',
    }


def test_task_create_sem_id_no_texto_retorna_none(client):
    assert client._build_task_event('TaskCreate', {'subject': 'X'}, 'sem id aqui') is None


def test_task_create_usa_content_quando_sem_subject(client):
    evt = client._build_task_event('TaskCreate', {'content': 'Tarefa Y'}, 'Task #1 created')
    assert evt['subject'] == 'Tarefa Y'


def test_task_update_usa_taskId_do_input_e_propaga_campos(client):
    evt = client._build_task_event(
        'TaskUpdate', {'taskId': '5', 'status': 'completed', 'subject': 'Z'}, 'Updated task #5',
    )
    assert evt['action'] == 'updated'
    assert evt['task_id'] == '5'
    assert evt['status'] == 'completed'
    assert evt['subject'] == 'Z'


def test_task_update_sem_taskId_retorna_none(client):
    assert client._build_task_event('TaskUpdate', {}, 'Updated task #5') is None


def test_task_list_parseia_linhas_em_snapshot(client):
    evt = client._build_task_event(
        'TaskList', {}, '#1 [pending] Estudar\n#2 [completed] Revisar',
    )
    assert evt['action'] == 'snapshot'
    assert evt['tasks'] == [
        {'task_id': '1', 'status': 'pending', 'subject': 'Estudar'},
        {'task_id': '2', 'status': 'completed', 'subject': 'Revisar'},
    ]


def test_task_list_vazio_e_snapshot_vazio(client):
    assert client._build_task_event('TaskList', {}, '') == {'action': 'snapshot', 'tasks': []}


def test_task_get_read_only_nao_emite_evento(client):
    assert client._build_task_event('TaskGet', {'taskId': '1'}, '#1 [pending] X') is None


def test_tool_desconhecido_retorna_none(client):
    # guard anti falso-positivo: Bash com 'Updated task #N' no output nao vira task_event
    assert client._build_task_event('Bash', {}, 'Updated task #9 no log') is None
