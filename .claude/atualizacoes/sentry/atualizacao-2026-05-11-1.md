# Atualizacao Sentry — 2026-05-11-1

**Data**: 2026-05-11
**Org**: nacom | **Projeto**: python-flask
**Issues avaliadas**: 6 (unresolved)
**Issues corrigidas**: 2
**Issues fora de escopo / ignoradas**: 4

## Resumo

Triagem de 6 issues abertas. 2 fixes aplicados (PYTHON-FLASK-RN: AttributeError
`saldo_estoque_pedido` em `carteira.obter_estoque_pedido` apos remocao de colunas
da `CarteiraPrincipal`; PYTHON-FLASK-RK: TypeError `Decimal * float` em
`custeio.listar_definicao` no calculo recursivo de custo via BOM). 4 issues fora
de escopo: 1 em development (RM), 1 ad-hoc script Render Shell (RP), 1 erro de
infra OpenClaw gateway (RJ), 1 validacao de negocio "NF remessa nao encontrada" (2A).

---

## Issues Corrigidas

### PYTHON-FLASK-RN: AttributeError 'CarteiraPrincipal' has no attribute 'saldo_estoque_pedido'
- **Frequencia**: 3 eventos, 1 usuario (rafael@nacomgoya.com.br, iOS Safari + Chrome Windows)
- **Culprit**: `carteira.obter_estoque_pedido`
- **Pedidos afetados**: VCD2669842, VCD2669302
- **Causa raiz**: a migration `remover_campos_nao_utilizados_carteira.sql` removeu
  `saldo_estoque_pedido`, `menor_estoque_produto_d7`, `estoque`, `estoque_d0..d28`
  da tabela `carteira_principal` (todos eram 100% NULL/vazios). O modelo
  `CarteiraPrincipal` tambem nao tem mais esses atributos. Mas
  `app/carteira/routes/estoque_api.py:50,67` (rota `/api/pedido/<num_pedido>/estoque`)
  ainda referenciava `produto.saldo_estoque_pedido` diretamente, levantando
  `AttributeError` ao processar produtos do pedido.
- **Fix**: `app/carteira/routes/estoque_api.py:43-72` — substituido acesso direto
  aos atributos removidos por valores de `projecao_completa` (fonte canonica via
  `ServicoEstoqueSimples`). Fallback (quando servico falha) agora retorna zeros
  ao inves de tentar `getattr(produto, 'estoque_dN', 0)` em campos inexistentes.
  Comentario adicionado citando a migration que removeu os campos.
- **Status**: resolved no Sentry

### PYTHON-FLASK-RK: TypeError unsupported operand type(s) for *: 'decimal.Decimal' and 'float'
- **Frequencia**: 2 eventos, 1 usuario
- **Culprit**: `custeio.listar_definicao`
- **Causa raiz**: `app/custeio/routes/custeio_routes.py:1927` — funcao recursiva
  `calcular_custo_bom` multiplicava `custo_comp * comp['qtd']` onde:
  - `custo_comp` vinha de `custos_dinamicos_dict[...][campo_custo]`, retornado por
    `ServicoCusteio.calcular_custo_comprados()` que aplica
    `_quantize_custo(...)` retornando `Decimal`.
  - `comp['qtd']` era `float(bom.qtd_utilizada)` (linha 1901).
  - Em Python, `Decimal * float` levanta TypeError (sem coercao implicita).
- **Fix**: `app/custeio/routes/custeio_routes.py:1923-1929` — coercao explicita
  `float(custo_comp) * float(comp['qtd'])`. Acumulador `custo_total` inicializado
  como `0.0`. Comentario adicionado explicando origem do Decimal.
- **Status**: resolved no Sentry

---

## Issues Fora de Escopo / Ignoradas

### PYTHON-FLASK-RM (1 evento, env=development)
- **Titulo**: `UndefinedError: 'tabela_produtos' is undefined`
- **Culprit**: `produtos.auditoria` (template `app/templates/produtos/auditoria.html`)
- **Motivo da exclusao**: `environment=development`, release=`dev`, server=`NACOM052`
  (maquina local rafael). Bug de template de auditoria — variavel `tabela_produtos`
  nao foi passada pela rota. Responsabilidade do dev fixar localmente; nao recorrente em prod.

### PYTHON-FLASK-RP (1 evento, ad-hoc script via Render Shell)
- **Titulo**: `FileNotFoundError: '/tmp/agente_files/menos_vendidos_data.json'`
- **Culprit**: `__main__ in <module>`, location=`<stdin>`, mechanism=`excepthook`
- **Motivo da exclusao**: script ad-hoc rodado em Render Shell (stdin). Nao e
  bug de codigo de app — usuario tentou abrir arquivo que nao existia no `/tmp`
  do container.

### PYTHON-FLASK-RJ (2 eventos, infra OpenClaw)
- **Titulo**: `[WHATSAPP] Falha de rede ao chamar gateway OpenClaw: HTTPConnectionPool(host='127.0.0.1', port=18789)`
- **Culprit**: `whatsapp.inbound`
- **Motivo da exclusao**: erro infra externa — gateway OpenClaw em `127.0.0.1:18789`
  estava indisponivel/reiniciando no momento dos eventos. Nao corrigivel via codigo
  do app de fretes (gateway roda em maquina local separada). Workers tem retry.
  Referencia: `memory/openclaw_whatsapp_integration.md`.

### PYTHON-FLASK-2A (4 eventos, 3 usuarios, validacao de negocio)
- **Titulo**: `✗ Erro ao vincular NF remessa #147938: NF de remessa #147938 nao encontrada`
- **Culprit**: `pallet_v3.unified_actions.acao_vincular_devolucao`
- **Motivo da exclusao**: e validacao de negocio (raise intencional quando a NF
  de remessa informada pelo usuario nao existe no sistema). Sentry "Seer Actionability: low".
  Comportamento esperado — a UI deve mostrar a mensagem ao usuario. Para reduzir
  ruido, decisao futura seria filtrar via `before_send` ou rebaixar para warning.
  Fora do escopo desta triagem (corretivo simples nao se aplica — sem bug tecnico).

---

## Arquivos modificados

- `app/carteira/routes/estoque_api.py` — fix AttributeError em
  `obter_estoque_pedido` apos remocao de colunas da `CarteiraPrincipal`.
- `app/custeio/routes/custeio_routes.py` — coercao Decimal/float em
  `calcular_custo_bom` (funcao aninhada de `listar_definicao`).

## Metricas

- Issues abertas antes: 6
- Issues fechadas pela triagem: 2 (RN + RK)
- Issues abertas depois (esperado): 4
- Reducao: 33%

## Observacoes

1. **RN — drift entre migration e codigo**: a migration foi rodada em
   23/11/2025 removendo 30+ colunas, mas a rota `obter_estoque_pedido`
   nao foi atualizada. O outro endpoint na mesma rota
   (`obter_workspace_estoque`) ja usa o padrao correto (linhas 100-208:
   query explicita com `qtd_saldo_produto_pedido`/`preco_produto_pedido`
   apenas + JOIN `CadastroPalletizacao` + delegacao para
   `processar_dados_workspace_produto`). Sugestao futura (fora desta
   triagem): considerar marcar `obter_estoque_pedido` como deprecated
   ou migrar para usar `processar_dados_workspace_produto` igual ao
   workspace endpoint.

2. **RK — Decimal vs float em custeio**: caso classico do `_quantize_custo`
   retornar Decimal mas o consumidor (BOM recursivo) tratar como float.
   O resto de `listar_definicao` ja funcionava pois os valores
   `custos_considerados_dict[c.cod_produto]['custo_considerado']`
   sao explicitamente `float(c.custo_considerado)` (linha 1861). Apenas
   o caminho BOM recursivo escapou. Outras rotas custeio (`detalhe_bom_por_criterio`
   a partir de 1971) podem ter padrao similar — vale revisao futura.

3. **2A — frequencia maior que ja-fixed**: 4 eventos e 3 usuarios distintos,
   recorrente. Sugere que a UI nao esta tratando o erro bem (usuarios tentando
   vincular NF que nao existe). Decisao de UX/produto, nao de bug.
