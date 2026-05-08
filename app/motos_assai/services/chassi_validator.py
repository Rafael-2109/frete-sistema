"""Validador de chassi contra regex configurado em assai_modelo.regex_chassi.

Não bloqueia operação — retorna alerta para UI exibir.
"""

import re
from typing import Optional, Dict, Any
from app.motos_assai.models import AssaiModelo


class ResultadoValidacao(Dict):
    """{ok: bool, mensagem: str, regex_usado: str | None}"""


def validar_chassi(chassi: str, modelo_id: Optional[int]) -> Dict[str, Any]:
    """Valida chassi contra regex_chassi do modelo.

    Args:
        chassi: chassi observado
        modelo_id: id do AssaiModelo (None → não valida)

    Returns:
        {ok: True/False, mensagem: str, regex_usado: str | None}
    """
    if not chassi:
        return {'ok': False, 'mensagem': 'Chassi vazio', 'regex_usado': None}

    if not modelo_id:
        return {'ok': True, 'mensagem': 'Modelo não definido — pulando validação',
                'regex_usado': None}

    modelo = AssaiModelo.query.get(modelo_id)
    if not modelo:
        return {'ok': False, 'mensagem': f'Modelo {modelo_id} não encontrado',
                'regex_usado': None}

    if not modelo.regex_chassi:
        return {'ok': True, 'mensagem': f'Modelo {modelo.codigo} sem regex configurado',
                'regex_usado': None}

    pattern = modelo.regex_chassi
    if not pattern.startswith('^'):
        pattern = '^' + pattern
    if not pattern.endswith('$'):
        pattern = pattern + '$'

    try:
        if re.match(pattern, chassi):
            return {'ok': True, 'mensagem': 'Chassi bate o regex',
                    'regex_usado': modelo.regex_chassi}
        else:
            return {'ok': False,
                    'mensagem': f'Chassi {chassi} não bate o regex de {modelo.codigo}',
                    'regex_usado': modelo.regex_chassi}
    except re.error as e:
        return {'ok': False, 'mensagem': f'regex inválido: {e}',
                'regex_usado': modelo.regex_chassi}
