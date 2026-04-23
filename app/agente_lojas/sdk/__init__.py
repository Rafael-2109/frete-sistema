"""SDK wrapper enxuto do Agente Lojas HORA.

Independente do AgentClient do agente logistico (`app/agente/sdk/client.py`)
para evitar acoplamento. Usa ClaudeSDKClient diretamente com ~300 LOC.

Exports:
    get_lojas_client(): singleton AgentLojasClient
    stream_lojas_chat(): funcao high-level usada pelo route chat.py
"""
from .client import AgentLojasClient, get_lojas_client, stream_lojas_chat

__all__ = ['AgentLojasClient', 'get_lojas_client', 'stream_lojas_chat']
