📋 ANÁLISE COMPLETA DO SISTEMA DE INCONSISTÊNCIAS

  1. ESTRUTURA DO SISTEMA

  O sistema possui DOIS MODELOS principais para gerenciar inconsistências:

  A) InconsistenciaFaturamento - Inconsistências gerais

  # Tabela: inconsistencia_faturamento
  # Propósito: Registrar problemas entre NFs e separações/embarques

  Campos principais:
  - tipo: String(50) → TIPOS POSSÍVEIS:
    • "NF_SEM_SEPARACAO" - NF sem pedido/separação correspondente
    • "DIVERGENCIA_NF_EMBARQUE" - NF vinculada mas pedido divergente

  - numero_nf: String(20) → Número da NF com problema
  - num_pedido: String(50) → Pedido relacionado
  - cod_produto: String(50) → Produto (ou "MULTIPLOS")
  - qtd_faturada: Numeric(15,3) → Quantidade total faturada
  - resolvida: Boolean → Se foi resolvida
  - observacao_resolucao: Text → Detalhes do problema

  B) FaturamentoParcialJustificativa - Divergências de quantidade

  # Tabela: faturamento_parcial_justificativa  
  # Propósito: Registrar quando separou X mas faturou Y

  Campos principais:
  - qtd_separada: Quantidade que foi separada
  - qtd_faturada: Quantidade que foi faturada
  - qtd_saldo: Diferença (saldo não faturado)
  - motivo_nao_faturamento: Razão da divergência

  ---
  2. FLUXO DE CRIAÇÃO DE INCONSISTÊNCIAS

  O processo ocorre em ProcessadorFaturamento durante o processamento de NFs:

  CENÁRIO 1: NF SEM SEPARAÇÃO

  # Quando: NF não tem embarque ativo correspondente
  # Local: _processar_nf_simplificado linha ~296

  if not embarque_items:
      # Cria MovimentacaoEstoque sem lote
      mov_criadas =
  self._criar_movimentacao_sem_separacao(nf, usuario)

      # GERA INCONSISTÊNCIA TIPO "NF_SEM_SEPARACAO"
      # Mas ATUALMENTE NÃO ESTÁ SENDO CHAMADA! ⚠️

  PROBLEMA IDENTIFICADO: A função _gerar_inconsistencia_sem_separacao() existe mas NÃO está sendo chamada no fluxo atual!

  CENÁRIO 2: DIVERGÊNCIA NF x EMBARQUE

  # Quando: NF tem EmbarqueItem mas pedido não bate
  # Este cenário NÃO EXISTE no _processar_nf_simplificado atual! ⚠️

  PROBLEMA IDENTIFICADO: A função _gerar_inconsistencia_divergencia_embarque() existe mas NUNCA é chamada porque essa lógica foi removida!

  CENÁRIO 3: DIVERGÊNCIA DE QUANTIDADE

  # Quando: Quantidade faturada ≠ quantidade separada
  # Local: _criar_justificativa_divergencia linha ~617

  if abs(qtd_fat - qtd_sep) > 0:  # Qualquer diferença
      just = FaturamentoParcialJustificativa()
      just.motivo_nao_faturamento = "DIVERGENCIA_AUTO"

  PROBLEMA: Cria justificativa para QUALQUER diferença, mesmo mínima.

  ---
  3. FLUXO DE VISUALIZAÇÃO (Dashboard)

  # API: /faturamento/inconsistencias

  1. BUSCA inconsistências não resolvidas:
     InconsistenciaFaturamento.query.filter_by(resolvida=False)

  2. ENRIQUECE com dados do cliente:
     Para cada inconsistência → busca RelatorioFaturamentoImportado

  3. BUSCA embarques com erro:
     EmbarqueItem com erro_validacao != None

  4. SUGERE NF para correção:
     buscar_nf_por_lote(separacao_lote_id)

  ---
  4. FLUXO DE RESOLUÇÃO

  # API: /api/resolver-inconsistencia/<id>

  1. Marca como resolvida:
     inconsistencia.resolvida = True

  2. Adiciona observação:
     inconsistencia.observacao_resolucao += "RESOLVIDO:
   {observacao}"

  3. NÃO atualiza data de resolução ⚠️
     # Campo resolvida_em existe mas não é preenchido!

  ---
  5. PROBLEMAS CRÍTICOS IDENTIFICADOS ⚠️

  A) INCONSISTÊNCIAS NÃO ESTÃO SENDO CRIADAS!

  # NO CÓDIGO ATUAL:
  # ❌ _gerar_inconsistencia_sem_separacao → NUNCA  CHAMADA
  # ❌ _gerar_inconsistencia_divergencia_embarque → NUNCA CHAMADA

  # RESULTADO: Dashboard vazio ou com dados antigos!

  B) CAMPOS NÃO UTILIZADOS NO MODELO

  InconsistenciaFaturamento tem campos não usados:
  - saldo_disponivel → Nunca preenchido
  - qtd_excesso → Nunca preenchido
  - acao_tomada → Nunca preenchido
  - detectada_em → Tem default mas não é gerenciado
  - resolvida_em → NUNCA atualizado quando resolve
  - resolvida_por → NUNCA preenchido

  C) FALTA DE AUDITORIA

  # Modelo tem campos mas API não usa:
  - criado_por → Existe mas não é passado
  - atualizado_por → Campo inexistente sendo usado
  - atualizado_em → Campo inexistente sendo usado

  ---
  6. FLUXO CORRETO ESPERADO

  graph TD
      A[ProcessadorFaturamento] --> B{NF tem embarque?}
      B -->|NÃO| C[Criar MovimentacaoEstoque sem lote]
      C --> D[CRIAR InconsistenciaFaturamento tipo NF_SEM_SEPARACAO]

      B -->|SIM| E{Quantidades batem?}
      E -->|NÃO| F[CRIAR FaturamentoParcialJustificativa]

      G[Dashboard] --> H[Listar inconsistências não resolvidas]
      H --> I[Usuário resolve]
      I --> J[Marcar resolvida=True + preencher campos auditoria]

  ---
  7. CORREÇÕES NECESSÁRIAS

  1. ATIVAR criação de inconsistências:
    - Chamar _gerar_inconsistencia_sem_separacao() quando não encontrar embarque
    - Remover ou adaptar _gerar_inconsistencia_divergencia_embarque()
  2. CORRIGIR modelo InconsistenciaFaturamento:
    - Usar campos de auditoria corretamente
    - Preencher resolvida_em e resolvida_por ao resolver
  3. MELHORAR lógica de divergência:
    - Adicionar tolerância (ex: 1%) antes de criar justificativa
    - Não criar para diferenças irrelevantes
  4. LIMPAR dados obsoletos:
    - API tem /api/limpar-resolvidas mas sem filtro de data
    - Implementar limpeza periódica automática

  O sistema está parcialmente implementado mas com várias funções desconectadas do fluxo principal, resultando em inconsistências não sendo registradas adequadamente.

✻ Thinking…

  O usuário pediu foco no processo e demonstração com código. Acho que expliquei bem o processo mas preciso destacar mais claramente os problemas principais.

● RESUMO EXECUTIVO DOS PROBLEMAS 🚨

  1. INCONSISTÊNCIAS NÃO ESTÃO SENDO GERADAS

  As funções existem mas foram desconectadas do fluxo:

  # ATUALMENTE em _processar_nf_simplificado:
  if not embarque_items:
      mov_criadas =
  self._criar_movimentacao_sem_separacao(nf, usuario)
      return True, mov_criadas, 0
      # ❌ DEVERIA CHAMAR: 
  self._gerar_inconsistencia_sem_separacao(nf, usuario)

  2. MODELO COM CAMPOS ERRADOS

  O código tenta usar campos que não existem:

  # TENTANDO USAR (linhas 741, 780):
  inc_existente.atualizado_por = usuario  # ❌ Campo NÃO existe
  inc_existente.atualizado_em = datetime.now()  # ❌ Campo NÃO existe

  # CAMPOS QUE EXISTEM mas NÃO são usados:
  inc.resolvida_em  # ✅ Existe mas NUNCA preenchido
  inc.resolvida_por  # ✅ Existe mas NUNCA preenchido

  3. DASHBOARD MOSTRA DADOS INCORRETOS/ANTIGOS

  Como as inconsistências não estão sendo criadas corretamente, o dashboard está mostrando:
  - Dados antigos de quando o sistema funcionava
  - Ou vazio se nunca funcionou
  - Embarques com erro mas sem contexto adequado

  CONCLUSÃO: O sistema de inconsistências está quebrado
   - as funções existem mas não estão conectadas ao fluxo principal, e quando tentam ser usadas, referenciam campos inexistentes no modelo.

