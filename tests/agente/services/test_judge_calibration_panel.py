"""T5 (GATE-1 / E3) — UI de spot-check humano do ONLINE judge.

Cobre a lógica do painel de calibração (sem HTTP):
- `_serialize_calibration_case` (PURO): deriva `prioritario` da evidence
  (marcador ⚠ADVERSARIAL = discordância de alto valor, achado Task 3).
- `AgentEvalCase.record_human_verdict` (model, escrita): grava o veredito
  humano (agree/disagree) com validação; FLUSH (caller commita).
- `get_judge_calibration_panel` (service, leitura): concordance + amostra de
  spot-check, garantindo que os prioritários (⚠ADVERSARIAL) sempre apareçam.

DB via `db` fixture do conftest (savepoint + rollback automático). agent_name
de teste único por teste isola de casos reais ('__online_judge__').
"""
import uuid


class _FakeCase:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _an():
    """agent_name de teste único — isola concordance/panel de casos reais."""
    return f'__test_judge_{uuid.uuid4().hex[:8]}__'


class TestSerializeCalibrationCase:
    """Função PURA — sem DB."""

    def test_marca_prioritario_quando_adversarial(self):
        from app.agente.services.insights_service import _serialize_calibration_case
        c = _FakeCase(id=1, case_id='s:1', case_score=0.9, status='pass',
                      evidence='label=success score=90 | ok | ⚠ADVERSARIAL REFUTOU: nao confirmou',
                      recorded_at=None)
        d = _serialize_calibration_case(c)
        assert d['prioritario'] is True
        assert d['id'] == 1 and d['case_id'] == 's:1'
        assert d['case_score'] == 0.9 and d['status'] == 'pass'

    def test_nao_prioritario_sem_adversarial(self):
        from app.agente.services.insights_service import _serialize_calibration_case
        c = _FakeCase(id=2, case_id='s:2', case_score=0.45, status='fail',
                      evidence='label=partial score=45 | meio', recorded_at=None)
        assert _serialize_calibration_case(c)['prioritario'] is False

    def test_evidence_none_nao_quebra(self):
        from app.agente.services.insights_service import _serialize_calibration_case
        c = _FakeCase(id=3, case_id='s:3', case_score=0.0, status='fail',
                      evidence=None, recorded_at=None)
        d = _serialize_calibration_case(c)
        assert d['prioritario'] is False and d['evidence'] == ''


class TestRecordHumanVerdict:
    """Model — escrita do veredito humano (FLUSH, caller commita)."""

    def test_grava_verdict_valido(self, db):
        from app.agente.models import AgentEvalCase
        c = AgentEvalCase.insert_case(agent_name=_an(), case_id='s:1',
                                      case_score=0.9, status='pass', evidence='x')
        db.session.flush()
        out = AgentEvalCase.record_human_verdict(
            c.id, AgentEvalCase.VERDICT_DISAGREE, reviewed_by=74, note='judge credulo'
        )
        assert out is not None
        assert out.human_verdict == 'disagree'
        assert out.reviewed_by == 74
        assert out.human_note == 'judge credulo'
        assert out.reviewed_at is not None

    def test_verdict_invalido_retorna_none_sem_gravar(self, db):
        from app.agente.models import AgentEvalCase
        c = AgentEvalCase.insert_case(agent_name=_an(), case_id='s:9',
                                      case_score=0.5, status='fail', evidence='y')
        db.session.flush()
        out = AgentEvalCase.record_human_verdict(c.id, 'talvez', reviewed_by=74)
        assert out is None
        # não gravou nada
        assert c.human_verdict is None and c.reviewed_by is None

    def test_case_inexistente_retorna_none(self, db):
        from app.agente.models import AgentEvalCase
        out = AgentEvalCase.record_human_verdict(
            999_999_999, AgentEvalCase.VERDICT_AGREE, reviewed_by=74
        )
        assert out is None


class TestJudgeCalibrationPanel:
    """Service — concordance + amostra de spot-check."""

    def test_concordance_e_lista_de_nao_revisados(self, db):
        from app.agente.models import AgentEvalCase
        from app.agente.services.insights_service import get_judge_calibration_panel
        an = _an()
        AgentEvalCase.insert_case(agent_name=an, case_id='s:1', case_score=0.9, status='pass',
                                  evidence='label=success score=90 | ok | ⚠ADVERSARIAL REFUTOU: x')
        AgentEvalCase.insert_case(agent_name=an, case_id='s:2', case_score=0.4, status='fail',
                                  evidence='label=partial')
        rev = AgentEvalCase.insert_case(agent_name=an, case_id='s:3', case_score=0.8, status='pass',
                                        evidence='ok')
        db.session.flush()
        AgentEvalCase.record_human_verdict(rev.id, AgentEvalCase.VERDICT_AGREE, reviewed_by=74)
        db.session.flush()

        panel = get_judge_calibration_panel(agent_name=an, fraction=1.0, seed=1)
        assert panel['concordance']['reviewed'] == 1
        assert panel['concordance']['agree'] == 1
        assert panel['concordance']['rate'] == 1.0

        case_ids = {c['case_id'] for c in panel['casos']}
        assert 's:1' in case_ids and 's:2' in case_ids  # não-revisados listados
        assert 's:3' not in case_ids                    # revisado não volta
        prio = next(c for c in panel['casos'] if c['case_id'] == 's:1')
        assert prio['prioritario'] is True

    def test_prioritario_sempre_presente_mesmo_fora_da_amostra(self, db):
        from app.agente.models import AgentEvalCase
        from app.agente.services.insights_service import get_judge_calibration_panel
        an = _an()
        # 1 prioritário (⚠ADVERSARIAL) + 30 comuns; amostra mínima
        AgentEvalCase.insert_case(agent_name=an, case_id='prio:1', case_score=0.9, status='pass',
                                  evidence='label=success | ⚠ADVERSARIAL REFUTOU: discorda')
        for i in range(30):
            AgentEvalCase.insert_case(agent_name=an, case_id=f'c:{i}', case_score=0.5,
                                      status='fail', evidence='comum')
        db.session.flush()
        panel = get_judge_calibration_panel(agent_name=an, fraction=0.01, seed=1, limit=50)
        case_ids = {c['case_id'] for c in panel['casos']}
        assert 'prio:1' in case_ids, 'caso prioritário (⚠ADVERSARIAL) deve sempre aparecer'
        assert panel['prioritarios'] >= 1
