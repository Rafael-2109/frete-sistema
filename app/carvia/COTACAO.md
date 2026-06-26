# CarVia — Cotacao e Pricing

**Referenciado por**: `app/carvia/CLAUDE.md`

Fluxo de cotacao de frete CarVia: calculo via CidadeAtendida, categorias de moto, cotacoes comerciais e de rotas.

---

## Fluxo via CidadeAtendida

`CotacaoService` usa o MESMO fluxo do sistema principal:
```
Cidade nome + UF → buscar_cidade_unificada() → Cidade.codigo_ibge
→ CidadeAtendida → grupo_empresarial → TabelaFrete → TabelaFreteManager → CalculadoraFrete
```

**Reutiliza** (NAO cria novas utils):
- `buscar_cidade_unificada(cidade, uf)` de `app/utils/frete_simulador.py`
- `CidadeAtendida.query.filter(codigo_ibge)` de `app/vinculos/models.py`
- `GrupoEmpresarialService.obter_transportadoras_grupo()` de `app/utils/grupo_empresarial.py`
- `TabelaFreteManager.preparar_dados_tabela()` de `app/utils/tabela_frete_manager.py`
- `CalculadoraFrete.calcular_frete_unificado()` de `app/utils/calculadora_frete.py`

**Retorno enriquecido**: `lead_time` (do vinculo CidadeAtendida), `icms_destino` (da Cidade)
**Fallback**: Se cidade nao encontrada ou sem vinculos, busca por UF (comportamento anterior)

---

## Cotacao por Categoria de Moto (Preco por Unidade)

Empresas de moto podem ter preco fixo por unidade em vez de calculo por peso.
Deteccao automatica: se `categorias_moto` fornecido E tabela tem `CarviaPrecoCategoriaMoto`, usa preco por categoria.

```
CarviaTabelaService.cotar_carvia(categorias_moto=[{categoria_id, quantidade}]):
  1. Resolver grupo (existente)
  2. Buscar tabelas (existente)
  3. Para cada tabela:
     → TEM precos por categoria? → _calcular_por_categoria_moto()
     → NAO TEM → calcular_com_tabela_carvia() (peso, existente)
  4. Retorno inclui tipo_calculo: 'CATEGORIA_MOTO' | 'PESO'
```

**ICMS**: Aplicado sobre o total por categoria (mesma logica de `icms_incluso`/`icms_proprio`).
**Backward compat**: Tabelas sem `CarviaPrecoCategoriaMoto` continuam usando calculo por peso.

---

## Dois Tipos de Cotacao — Coexistem

| Feature | Modelo | Prefixo | Label UI | Uso |
|---------|--------|---------|----------|-----|
| Cotacao Comercial | `CarviaCotacao` | `COT-###` | "Cotacao Comercial" | Fluxo formal: cliente → pricing → desconto → gravar (aprova direto) → pedido |
| Cotacao de Rotas | `CarviaSessaoCotacao` | `COTACAO-###` | "Cotacao de Rotas" | Ferramenta pontual: cotar rota para cliente sob demanda |

Ambos coexistem sem colisao de prefixo. NAO deprecar nenhum.

---

## Cotacao Comercial (`CarviaCotacao`) — fluxo de status e pricing

`CotacaoV2Service` + `routes/cotacao_v2_routes.py` (wizard `/carvia/cotacoes/nova`).

### Fluxo de status (2026-06-20)

```
RASCUNHO ──(Gravar = marcar_enviado)──> APROVADO ──> [Pedido / Embarque / CTe]
   │  desconto > limite OU valor manual (toggle exigir_aprovacao_admin ON)
   └──> PENDENTE_ADMIN ──(admin_aprovar)──> RASCUNHO
CANCELADO <── cancelar (qualquer status); reabrir: APROVADO ──> RASCUNHO
```

- **"Gravar" pula a aprovacao do cliente**: `marcar_enviado` vai DIRETO de
  `RASCUNHO`/`RECUSADO` para `APROVADO` (grava `aprovado_por`/`aprovado_em`). A
  etapa intermediaria `ENVIADO` + as transicoes `registrar_aprovacao_cliente` /
  `registrar_recusa_cliente` / `registrar_contra_proposta` permanecem APENAS para
  cotacoes legadas que ja estejam em `ENVIADO` (botoes mantidos no `detalhe.html`).
  `STATUSES` do model ainda inclui `ENVIADO` (retrocompat).

### `tipo_carga` OPCIONAL

`tipo_carga` (`DIRETA`/`FRACIONADA`) e **opcional** na criacao/edicao. Vazio = "sem
distincao" → `cotar_carvia(tipo_carga=None)` busca em TODAS as modalidades e pega a
menor (so `DIRETA` exige veiculo). Form: `<select>` sem `required`, com opcao vazia.

### Aproveitamento automatico do CTe

Se a(s) NF(s) vinculadas a cotacao ja possuem CTe CarVia (`CarviaOperacao.cte_valor`),
`CotacaoV2Service.aproveitar_cte_se_houver` usa a **SOMA dos `cte_valor`** (dedup por
operacao — 1 CTe pode cobrir N NFs) como valor de venda e marca `criacao_tardia=True`,
**substituindo** o calculo de tabela. Roda no fim de `criar_cotacao_v2`, APOS criar
pedidos/NFs; so cai em `calcular_preco` (tabela) quando nao ha CTe. Independe da flag
`criacao_tardia` do link — e automatico para qualquer NF anexada.

---

## Cotacao de Rotas (Ferramenta Comercial)

**Prefixo**: `COTACAO-###` (anteriormente SC-###, backfill aplicado)
**Campos contato cliente**: `cliente_nome`, `cliente_email`, `cliente_telefone`, `cliente_responsavel` (opcionais)
**Autocomplete cidade**: Via `GET /localidades/ajax/cidades_por_uf/<uf>` + cache client-side + filtro debounce 200ms

**Fluxo de status**:
```
RASCUNHO ── enviar ──> ENVIADO ── resposta ──> APROVADO
                                           └─> CONTRA_PROPOSTA (com valor)
CANCELADO <── cancelar (de qualquer estado exceto APROVADO)
```

**Rotas** (`sessao_cotacao_routes.py`):
- HTML: `GET /sessoes-cotacao` (listar), `GET|POST /sessoes-cotacao/nova`, `GET /sessoes-cotacao/<id>` (detalhe)
- HTML: `POST .../adicionar-demanda`, `POST .../remover-demanda/<did>`, `POST .../enviar`, `POST .../resposta`, `POST .../cancelar`
- API: `POST /api/sessao-cotacao/<id>/cotar-demanda/<did>` (retorna todas opcoes + lead_time + breakdown), `POST .../selecionar-opcao/<did>` (grava escolha)

**Validacoes**:
- Enviar: TODAS demandas devem ter frete selecionado
- Cancelar: bloqueado se APROVADO
- Contra proposta: `valor_contra_proposta` obrigatorio
- Remover demanda: bloqueado se for a unica

---

## Cotacao Rapida (efemera) — `/carvia/cotacao-rapida` (2026-06-25)

Tela leve para cotar frete de MOTO por destino, **sem persistir nada** (cotacao
efemera — nenhuma migration). Origem fixa SP.

**Fluxo**: `modelo + qtd` (manual OU upload de PDF/imagem lido por LLM) +
`cidade/UF` (ou CEP) -> cotacao por TODAS as tabelas da rota + historico + PDF
em papel timbrado.

| Camada | Arquivo |
|--------|---------|
| Rotas | `routes/cotacao_rapida_routes.py` (`register_cotacao_rapida_routes`) — `GET /cotacao-rapida`, `POST .../calcular`, `POST .../upload`, `GET .../cep/<cep>`, `POST .../pdf` |
| Service cotacao | `services/pricing/cotacao_rapida_service.py` (`CotacaoRapidaService.cotar` / `historico_por_tabela`) |
| Service LLM | `services/parsers/cotacao_rapida_llm_service.py` (`extrair_motos_regiao`) |
| CEP -> IBGE | `app/utils/cep_service.py` (`resolver_cep`, via ViaCEP) |
| Templates | `templates/carvia/cotacao_rapida/{form,pdf}.html` |
| Menu | `_quick_nav.html` grupo Comercial (`carvia_active='cotacao_rapida'`) |

**Decisoes** (do dono, 2026-06-25):
- **Modelo -> categoria**: o motor `cotar_carvia` precifica por `categoria_id`;
  o service agrupa `(modelo_id, qtd)` por categoria e **re-expande** o valor por
  modelo (valor/moto = `valor_unitario` da categoria; total da opcao = soma, que
  coincide com o `valor_frete` do motor).
- **Todas as tabelas detalhadas juntas** — cada `CarviaTabelaFrete` da rota vira
  um card com breakdown por modelo.
- **Tabela sem preco por categoria de moto** -> avisada e PULADA (nao cai no
  calculo por peso). Modelo sem categoria -> avisado, fora do calculo.
- **CEP -> IBGE -> Cidade Atendida (chave canonica)**: `cotar(codigo_ibge=...)`
  resolve a `Cidade` PELO `codigo_ibge` (do ViaCEP/datalist) e usa o nome
  CANONICO do banco — o nome do ViaCEP pode divergir do cadastrado (hifen/acento:
  `BIRITIBA-MIRIM` vs `BIRITIBA MIRIM`), o que faria o match por nome falhar mesmo
  com o IBGE correto. O front propaga `codigo_ibge` (CEP + datalist
  `cidades_por_uf_ibge`) no payload.
- **Cidade nao atendida -> fallback por UF + aviso**: se a cidade informada nao
  tem vinculo em `CarviaCidadeAtendida`, em vez de zerar o resultado a cotacao
  cai para as tabelas da UF com aviso explicito (evita o footgun "preencher campo
  opcional zera tudo").
- **Historico**: ultimas 5 `CarviaCotacao(tipo_material='MOTO')` por
  `nome_tabela + uf_destino`, EXCLUINDO `CANCELADO`/`RECUSADO` (preco rejeitado
  nao e referencia). valor/moto = valor da cotacao / qtd de motos (selecao por
  `is not None`, considera `valor_manual`); destinatario = `endereco_destino`,
  fallback no cliente.
- **LLM**: Haiku 4.5 -> Sonnet 4.6 (aceita a 1a resposta com JSON bem-formado);
  lista de modelos+categorias injetada no prompt; nomes normalizados por
  `MotoRecognitionService.resolver_modelo_em_lista`. Robustez: formato resolvido
  por mime->extensao->magic bytes (octet-stream nao rejeita PDF valido); JSON
  recortado do 1o `{` ao ultimo `}` (tolera pos-ambulo); `_normalizar` defensivo
  (motos/regiao malformados degradam sem 500). Upload com cap de 20MB.
- **PDF**: weasyprint + logo `static/carvia/logo.jpg` (geracao em try/except).

Testes: `tests/carvia/test_cotacao_rapida_service.py`, `test_cep_service.py`,
`test_cotacao_rapida_llm_service.py` (17 casos). Revisao adversarial
(2026-06-25, 4 agentes): aprovado, achados alto/medio corrigidos.
