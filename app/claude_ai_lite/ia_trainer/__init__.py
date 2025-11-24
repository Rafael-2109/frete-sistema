"""
IA Trainer - Modulo de Ensino do Claude AI Lite.

Permite que usuarios ensinem o Claude atraves de:
1. Decomposicao de perguntas nao respondidas
2. Explicacao de termos de negocio
3. Geracao automatica de codigo (loaders, filtros, entidades)
4. Debate e refinamento com Claude
5. Teste e validacao antes de ativar

Segue o ROTEIRO DE SEGURANCA:
- Codigo gerado apenas para consultas (READ-ONLY)
- Validacao de campos/tabelas antes de executar
- Timeout em todas as execucoes
- Versionamento completo de todas as alteracoes
- Logs de rastreabilidade

Criado em: 23/11/2025
"""

from .models import (
    CodigoSistemaGerado,
    VersaoCodigoGerado,
    SessaoEnsinoIA
)

__all__ = [
    'CodigoSistemaGerado',
    'VersaoCodigoGerado',
    'SessaoEnsinoIA'
]
