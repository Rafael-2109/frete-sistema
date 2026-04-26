"""Encriptacao Fernet para credenciais TagPlus (client_secret + tokens).

Chave em env `HORA_TAGPLUS_ENC_KEY`. Gerar com:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

NUNCA versionar a chave. NUNCA armazenar plaintext no banco.
"""
from __future__ import annotations

import os
from cryptography.fernet import Fernet


_FERNET_INSTANCE: Fernet | None = None


def _fernet() -> Fernet:
    global _FERNET_INSTANCE
    if _FERNET_INSTANCE is None:
        key = os.environ.get('HORA_TAGPLUS_ENC_KEY')
        if not key:
            raise RuntimeError(
                'HORA_TAGPLUS_ENC_KEY nao configurada. '
                'Gerar com Fernet.generate_key() e setar no Render.'
            )
        _FERNET_INSTANCE = Fernet(key.encode() if isinstance(key, str) else key)
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
