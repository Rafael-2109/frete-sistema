#!/usr/bin/env python3
"""
Script para atualizar todas as referências de geração de lote
para usar a função padronizada
Data: 2025-01-29
"""

# LOCAIS A ATUALIZAR:
print("""
ATUALIZAÇÃO MANUAL NECESSÁRIA:

1. app/pedidos/routes.py (linha ~806):
   REMOVER:
   - def gerar_lote_id():
   -     return f"LOTE_{uuid.uuid4().hex[:8].upper()}"
   
   ADICIONAR NO TOPO:
   + from app.utils.lote_utils import gerar_lote_id
   
   ATUALIZAR (linha ~921):
   - novo_lote_id = gerar_lote_id()
   + novo_lote_id = gerar_lote_id()  # Agora usa a versão padronizada

2. app/carteira/utils/separacao_utils.py (linha ~144):
   REMOVER:
   - def gerar_novo_lote_id(): ... (toda a função)
   
   ADICIONAR NO TOPO:
   + from app.utils.lote_utils import gerar_lote_id as gerar_novo_lote_id

3. app/carteira/routes/pre_separacao_api.py (linha ~37):
   ATUALIZAR IMPORT:
   - from app.carteira.utils.separacao_utils import gerar_novo_lote_id
   + from app.utils.lote_utils import gerar_lote_id as gerar_novo_lote_id
   
   OU simplesmente:
   + from app.utils.lote_utils import gerar_lote_id
   - separacao_lote_id = gerar_novo_lote_id()
   + separacao_lote_id = gerar_lote_id()

4. app/carteira/routes/separacao_api.py (linha ~150):
   ATUALIZAR IMPORT:
   - from app.carteira.utils.separacao_utils import gerar_novo_lote_id
   + from app.utils.lote_utils import gerar_lote_id
   
   ATUALIZAR USO:
   - lote_id = gerar_novo_lote_id()
   + lote_id = gerar_lote_id()

BENEFÍCIOS DA PADRONIZAÇÃO:
✅ Formato único: LOTE_YYYYMMDD_HHMMSS_XXX
✅ Ordenável cronologicamente
✅ Verificação de unicidade
✅ Manutenção centralizada
✅ Facilita hash para ID na VIEW pedidos
""")