1. Primeiro, verificar integridade:
  python verificar_pre_migracao.py

  2. Se houver problemas, recompor separações:
  python recompor_separacoes_perdidas.py

  3. Verificar novamente:
  python verificar_pre_migracao.py

  4. Se tudo OK, executar migração completa:
  python executar_migracao.py



Script para migração das pré separações e campos de MovimentacaoEstoque.
