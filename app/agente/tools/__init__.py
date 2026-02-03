"""
Custom Tools MCP do Agente Logístico.

Contém ferramentas in-process que o SDK invoca diretamente,
sem overhead de subprocess.

Tools disponíveis:
- consultar_sql: Converte linguagem natural → SQL → executa read-only
- memory: Gerenciamento de memória persistente do usuário
- schema: Descoberta de schema de tabelas e valores válidos de campos categóricos

Referência: https://platform.claude.com/docs/pt-BR/agent-sdk/custom-tools
"""
