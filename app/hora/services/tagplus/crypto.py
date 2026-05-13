"""Encriptacao Fernet para credenciais TagPlus (client_secret + tokens).

Chave em env `HORA_TAGPLUS_ENC_KEY`. Gerar com:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

NUNCA versionar a chave. NUNCA armazenar plaintext no banco.
"""
from __future__ import annotations

import os
from cryptography.fernet import Fernet


_FERNET_INSTANCE: Fernet | None = None


def _sanitizar_chave(raw: str) -> str:
    """Remove whitespace e aspas duplicadas em volta da chave.

    Erros humanos comuns ao copiar/colar no painel do Render:
      - '"abc...="'   -> com aspas envolvendo
      - " abc...= "   -> com espaco antes/depois
      - 'abc...=\n'   -> newline acidental do clipboard

    Fernet exige string ASCII de 44 chars (32 bytes url-safe base64 com
    padding `=` final). Qualquer caractere fora disso resulta em
    'Fernet key must be 32 url-safe base64-encoded bytes'.
    """
    s = raw.strip()
    # Remove um par de aspas (simples ou duplas) envolvendo a chave inteira.
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        s = s[1:-1].strip()
    return s


def _fernet() -> Fernet:
    global _FERNET_INSTANCE
    if _FERNET_INSTANCE is None:
        raw = os.environ.get('HORA_TAGPLUS_ENC_KEY')
        if not raw:
            raise RuntimeError(
                'HORA_TAGPLUS_ENC_KEY nao configurada. '
                'Gerar com Fernet.generate_key() e setar no Render '
                '(env vars do servico sistema-fretes).'
            )
        key = _sanitizar_chave(raw)
        try:
            _FERNET_INSTANCE = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as exc:
            # Mensagem detalhada para diagnostico — NUNCA logar a chave inteira.
            preview = (key[:4] + '...' + key[-4:]) if len(key) >= 12 else '(curta demais)'
            raise RuntimeError(
                'HORA_TAGPLUS_ENC_KEY com formato invalido. '
                f'Tamanho={len(key)} (esperado 44), preview={preview!r}. '
                f'Erro original: {exc}. '
                'Gerar chave nova com: '
                'python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            ) from exc
    return _FERNET_INSTANCE


def encrypt(plain: str) -> str:
    """Encripta string em UTF-8 e retorna ciphertext base64 ASCII."""
    if plain is None:
        raise ValueError('encrypt(None) — passe string vazia se intencional')
    return _fernet().encrypt(plain.encode('utf-8')).decode('ascii')


def decrypt(cipher: str) -> str:
    """Decripta ciphertext base64 ASCII e retorna plaintext UTF-8."""
    if cipher is None:
        raise ValueError('decrypt(None) — token nao encontrado')
    return _fernet().decrypt(cipher.encode('ascii')).decode('utf-8')


def reset_cache_for_tests() -> None:
    """Reset do cache do Fernet (usar so em fixtures de teste)."""
    global _FERNET_INSTANCE
    _FERNET_INSTANCE = None
