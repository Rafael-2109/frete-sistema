"""
Password Health Service
=======================

Avalia forca e saude de senhas:
- zxcvbn para score/entropia/feedback (0-4)
- Lista de senhas comuns brasileiras (top 100)
- HIBP password check via k-anonymity

SEGURANCA CRITICA:
- NUNCA armazena ou loga senha — avaliacao 100% em memoria
- Resultado NAO contem a senha original
"""

from typing import Dict, Any

from app.utils.logging_config import logger


# Top 100 senhas comuns brasileiras (embarcada, sem dependencia externa)
SENHAS_COMUNS_BR = {
    '123456', '123456789', '12345678', '1234567', '12345',
    '1234567890', 'senha', 'password', '123123', '111111',
    'abc123', 'senha123', '102030', '010203', 'brasil',
    'master', 'qwerty', 'iloveyou', 'trustno1', 'sunshine',
    'princess', 'admin', 'welcome', 'monkey', 'dragon',
    'login', 'passw0rd', 'hello', 'charlie', 'donald',
    '654321', '666666', '123', '1234', '12345678910',
    'abcd1234', 'p@ssw0rd', 'letmein', 'football', 'shadow',
    'michael', 'access', 'master123', 'mustang', 'batman',
    'jesus', 'amor', 'amorzinho', 'flamengo', 'corinthians',
    'palmeiras', 'vasco', 'santos', 'gremio', 'cruzeiro',
    'inter', 'sp', 'rj', 'mg', 'bahia',
    'familia', 'deus', 'felicidade', 'saudade', 'mudanca',
    'sucesso', 'liberdade', 'vitoria', 'estrela', 'sol',
    'lua', 'vida', 'paz', 'forca', 'poder',
    'rei', 'rainha', 'principe', 'princesa', 'guerreiro',
    'campeao', 'fenix', 'tigre', 'leao', 'aguia',
    'amordemae', 'minhafilha', 'meufilho', 'meubem', 'minhavida',
    'teamo', 'teadoro', 'euteamo', 'forever', 'always',
    'qwe123', 'asd123', 'zxc123', 'q1w2e3', 'a1b2c3',
}


def avaliar_senha(senha: str, verificar_hibp: bool = True) -> Dict[str, Any]:
    """
    Avalia saude de uma senha de forma transiente (sem persistir).

    Args:
        senha: Senha a avaliar (NUNCA armazenada/logada)
        verificar_hibp: Se True, verifica contra HIBP (k-anonymity)

    Returns:
        dict com score (0-4), feedback, vazada, etc.
        NAO contem a senha original.
    """
    resultado = {
        'score': 0,  # 0=muito fraca, 4=muito forte
        'score_label': 'Muito Fraca',
        'feedback_avisos': [],
        'feedback_sugestoes': [],
        'entropia_estimada': 0,
        'tempo_crack': '',
        'na_lista_comum_br': False,
        'vazada_hibp': False,
        'ocorrencias_hibp': 0,
        'hibp_erro': None,
        'comprimento': len(senha),
        'problemas': [],
    }

    # 1. Verificar lista brasileira
    if senha.lower() in SENHAS_COMUNS_BR:
        resultado['na_lista_comum_br'] = True
        resultado['problemas'].append(
            'Senha esta na lista de senhas comuns brasileiras'
        )

    # 2. zxcvbn
    try:
        from zxcvbn import zxcvbn as zxcvbn_check
        analise = zxcvbn_check(senha)

        resultado['score'] = analise.get('score', 0)
        resultado['entropia_estimada'] = analise.get('guesses_log10', 0)
        resultado['tempo_crack'] = (
            analise.get('crack_times_display', {})
            .get('offline_slow_hashing_1e4_per_second', 'N/A')
        )

        feedback = analise.get('feedback', {})
        resultado['feedback_avisos'] = feedback.get('warning', '').split('\n') \
            if feedback.get('warning') else []
        resultado['feedback_sugestoes'] = feedback.get('suggestions', [])

    except ImportError:
        logger.warning("zxcvbn nao instalado — usando avaliacao basica")
        resultado['score'] = _avaliar_basico(senha)
    except Exception as e:
        logger.error(f"Erro no zxcvbn: {e}")
        resultado['score'] = _avaliar_basico(senha)

    # 3. HIBP password check (k-anonymity, gratis)
    if verificar_hibp:
        try:
            from app.seguranca.services.hibp_service import verificar_senha_vazada
            hibp = verificar_senha_vazada(senha)
            resultado['vazada_hibp'] = hibp['vazada']
            resultado['ocorrencias_hibp'] = hibp['ocorrencias']
            resultado['hibp_erro'] = hibp['erro']

            if hibp['vazada']:
                resultado['problemas'].append(
                    f"Senha apareceu em {hibp['ocorrencias']:,} vazamentos conhecidos"
                )
        except Exception as e:
            logger.error(f"Erro ao verificar HIBP password: {e}")
            resultado['hibp_erro'] = str(e)

    # Penalizar score se na lista comum ou vazada
    if resultado['na_lista_comum_br'] or resultado['vazada_hibp']:
        resultado['score'] = min(resultado['score'], 1)

    # Label do score
    labels = {
        0: 'Muito Fraca',
        1: 'Fraca',
        2: 'Razoavel',
        3: 'Boa',
        4: 'Forte',
    }
    resultado['score_label'] = labels.get(resultado['score'], 'Desconhecido')

    # Problemas adicionais
    if len(senha) < 8:
        resultado['problemas'].append('Senha muito curta (minimo 8 caracteres)')
    if len(senha) < 12:
        resultado['feedback_sugestoes'].append(
            'Use pelo menos 12 caracteres para maior seguranca'
        )

    return resultado


def _avaliar_basico(senha: str) -> int:
    """
    Avaliacao basica de senha quando zxcvbn nao esta disponivel.

    Returns:
        Score 0-4
    """
    score = 0
    if len(senha) >= 8:
        score += 1
    if len(senha) >= 12:
        score += 1
    if any(c.isupper() for c in senha) and any(c.islower() for c in senha):
        score += 1
    if any(c.isdigit() for c in senha) and any(not c.isalnum() for c in senha):
        score += 1
    return min(score, 4)
