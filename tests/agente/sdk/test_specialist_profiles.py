import os
from app.agente.sdk.specialist_profiles import SPECIALIST_PROFILES, SpecialistProfile


def test_piloto_gestor_recebimento_existe():
    p = SPECIALIST_PROFILES.get("gestor-recebimento")
    assert isinstance(p, SpecialistProfile)
    assert p.role == "gestor-recebimento"
    assert "validacao-nf-po" in p.skills


def test_profile_aponta_para_prompt_existente():
    p = SPECIALIST_PROFILES["gestor-recebimento"]
    assert os.path.exists(p.system_prompt_path)
