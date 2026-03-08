# Portal Atacadao — Navegacao e Seletores

**Portal**: https://atacadao.hodiebooking.com.br
**Ultima Atualizacao**: 2026-03-07
**Status**: Inicial — sera preenchido durante descoberta interativa

---

## URLs Conhecidas

| Pagina | URL | Verificado |
|--------|-----|------------|
| Login | `/` | Sim (config.py) |
| Lista de Pedidos | `/pedidos` | Sim (config.py) |
| Detalhe Pedido | `/pedidos/{pedido_id}` | Sim (config.py) |
| Criar Carga | `/cargas/create?id_pedido={pedido_id}` | Sim (config.py) |
| Detalhe Carga | `/cargas/{carga_id}` | Sim (config.py) |
| Status Agendamento | `/agendamentos/{protocolo}` | Sim (config.py) |
| Relatorio Itens (CSV) | `/relatorio/itens` | Sim (consultar_agendamentos.py) |

---

## Seletores Conhecidos (de config.py)

### Pagina de Pedidos
- Campo busca pedido: `#nr_pedido`
- Botao filtrar: `#enviarFiltros`
- Link exibir pedido: `a[href*="/pedidos/"][title="Exibir"]`

### Pagina do Pedido
- Botao solicitar agendamento: `.btn_solicitar_agendamento`

### Formulario de Carga/Agendamento
- Data leadtime: `#leadtime_minimo`
- Data desejada: `input[name="data_desejada"]`
- Transportadora: `#transportadora`
- Buscar transportadora: `button[data-target="#modal-transportadoras"]`
- Especie carga: `select[name="carga_especie_id"]`
- Tipo veiculo: `select[name="tipo_veiculo"]`
- Quantidade produto: `input[name^="qtd_alocada"]`
- Botao salvar: `#salvar`

### Modal Sucesso
- Modal: `#regSucesso`
- Botao Nao (NF): `#btnNao`
- Botao Sim (NF): `#btnSim`

### Pagina Agendamento
- Protocolo: `.box-numero-protocolo .valor`
- Status: `.box-numero-protocolo .status span`
- Imprimir senha: `.btn_imprimir_senha`
- Modal imprimir: `#modal-imprimir-senha`
- Tabela cargas: `.VueTables__table`

### Indicadores de Sessao
- Menu principal: `.navbar-nav`
- Logout: `a[href*="logout"]`
- Usuario logado: `.user-name, .navbar-user`

---

## Seletores Descobertos Interativamente

> Preencher conforme descoberta com o usuario (Passos 2-5 do plano)

### Acao 1: Imprimir Pedidos

#### Filtro de Unidade (CNPJ) — Fluxo Completo

| Passo | Acao | Seletor |
|-------|------|---------|
| 1 | Abrir area de filtros | `a[data-toggle="collapse"][data-target="#filtros-collapse"]` |
| 2 | Abrir modal Unidade | `#filtro-unidade > div.input-group.f_editando > span:nth-child(3) > button` |
| 3 | Preencher CNPJ no modal | `#modal-unidades > div > div > div.modal-body > form > div > div.col-md-5.form-group > input` |
| 4 | Filtrar no modal | `#modal-unidades > div > div > div.modal-body > form > div > div.col-md-1.form-group > button` |
| 5 | Selecionar filial (radio) | `input[name="m_unidades_modal-unidades"]` (radio, value=JSON) |
| 6 | Confirmar selecao | `#modal-unidades > div > div > div.modal-footer > div > div > button.btn.btn-primary.selecionar` |
| 7 | Aplicar filtros | `#enviarFiltros` |

**Notas**:
- Passo 2 usa `nth-child(3)` — fragil, mas `#filtro-unidade` e estavel
- Passo 5: Se CNPJ retorna >1 resultado, selecionar primeiro radio
- Radio value contem JSON com dados da entidade (nome_fantasia, razao_social, codigo, etc.)

#### Filtro de Pedido

| Passo | Acao | Seletor |
|-------|------|---------|
| 1 | Abrir filtros | `a[data-toggle="collapse"][data-target="#filtros-collapse"]` |
| 2 | Limpar data elaboracao | `button[data-target_daterangepicker="dthr_elaboracao"][data-action="remove"]` |
| 3 | Preencher pedido | `#nr_pedido` |
| 4 | Aplicar filtros | `#enviarFiltros` |
| 5 | Abrir detalhe | `a[href*="/pedidos/"][title="Exibir"]` |

#### Captura PDF

| Componente | Seletor/Tecnica |
|------------|-----------------|
| Area de conteudo | `.content-wrapper` |
| Tecnica | Captura HTML + CSS → nova pagina limpa → `page.pdf()` A4 |
| Diretorio saida | `/tmp/pedidos_atacadao/` |

### Acao 2: Consultar Agendamentos

#### URL
`/relatorio/itens` — Export CSV com range de datas D0-D+N

#### Fluxo Completo

| Passo | Acao | Seletor / Tecnica |
|-------|------|-------------------|
| 1 | Criar sessao com downloads | `criar_sessao_download(headless=True)` — NAO usar `criar_client_com_sessao` |
| 2 | Verificar sessao | `verificar_sessao_sync(page)` → navega /pedidos |
| 3 | Navegar para relatorio | `page.goto('/relatorio/itens')` |
| 4 | Abrir filtros | JS `$('#filtros-collapse').collapse('show')` / click toggle |
| 5 | Filtrar Unidade (CNPJ) | Modal `#modal-unidades` (mesmos seletores de /pedidos) |
| 6 | Selecionar datas agendamento | JS daterangepicker: `picker.setStartDate(moment(...))` |
| 7 | Aplicar filtros | `#enviarFiltros` (JS click) |
| 8 | Screenshot evidencia | `capturar_screenshot(page, 'relatorio_itens_...')` |
| 9 | Export CSV | `#exportarExcel` com `page.expect_download()` |
| 10 | Parsear CSV | `csv.DictReader`, delimitador auto (`;` ou `,`), multi-encoding |

#### Seletores Relatorio

| Elemento | Seletor |
|----------|---------|
| Botao exportar CSV | `#exportarExcel` |
| Container data agendamento | `#filtros-collapse > div.filtros-body > div > div:nth-child(6)` |
| Botao aplicar filtros | `#enviarFiltros` |
| Modal Unidades | `#modal-unidades` (compartilhado com /pedidos) |

#### DateRangePicker — Estrategia

Nivel 1 (JS, preferido): Busca `$(input).data('daterangepicker')` no container `nth-child(6)`, seta datas via `picker.setStartDate/setEndDate` e dispara `apply.daterangepicker`.

Nivel 2 (fallback): Preenche input com `DD/MM/YYYY - DD/MM/YYYY` e dispara `change` event.

**[CONFIRMAR na 1a execucao]**: Nome exato do input de data, se container `nth-child(6)` e correto.

#### CSV Export

- Delimitador: `;` (confirmado)
- Encoding: UTF-8 (confirmado)
- Granularidade: **1 linha = 1 produto por agendamento** (mesmo protocolo aparece N vezes)
- Saida: `/tmp/agendamentos_atacadao/relatorio_<CNPJ>_<timestamp>.csv`
- **ATENCAO**: Coluna `Codigo` aparece DUAS vezes no header (filial e produto). `csv.DictReader` sobrescreve a primeira.

#### Colunas do CSV (confirmadas 2026-03-07)

| # | Coluna | Significado | Exemplo | Uso no sistema |
|---|--------|-------------|---------|----------------|
| 1 | `Codigo` (1a) | Codigo da filial no portal | `30` | `resolver_entidades` resolve para CNPJ/filial |
| 2 | `Unidade` | Nome da filial Atacadao | `UBERLANDIA` | Referencia visual |
| 3 | `Regional` | Diretoria regional | `DR-MG` | Informativo |
| 4 | `CNPJ` | CNPJ da filial (formatado) | `61.724.241/0003-30` | Match com `separacao.cnpj_cpf` |
| 5 | `Fornecedor` | Razao social do fornecedor | `NACOM GOYA...` | Informativo |
| 6 | `Codigo` (2a) | Codigo do produto no Atacadao | `13685` | De-Para (`ProdutoDeParaAtacadao`) |
| 7 | `Produto` | Descricao do produto | `CHAMPIGNON...` | Informativo |
| 8 | `Qtd.` | Quantidade de caixas/unidades | `16` | Quantidade a entregar |
| 9 | `Qtd. Paletes por produto` | Paletes desse produto | `0,14` | Calculo de carga |
| 10 | `Qtd. Paletes por carga` | Paletes total da carga | `5,13` | Calculo de veiculo |
| 11 | `Comprador` | Codigo do comprador Atacadao | `39` | Informativo |
| 12 | `N pedido` | Numero do pedido Atacadao | `145948` | Match com pedido |
| 13 | `Status` | Status do agendamento | `Aguardando check-in` | **Classificacao** (ver tabela abaixo) |
| 14 | `Data Desejada` | Data solicitada pelo fornecedor | `10/03/2026` | Informativo |
| 15 | `Data Agendamento` | Data efetiva do agendamento | `10/03/2026` | **ESTA e a data que usamos no sistema de fretes** |
| 16 | `Agendamento` | Numero do protocolo | `2603020064725` | **ESTE e o protocolo que consideramos no sistema de fretes** |
| 17 | `Protocolo` | Senha de entrega (impressao) | `SPNM074` | Usado para imprimir senha |
| 18 | `Flag sem agendamento` | Item sem agendamento | `0`/`1` | 0=tem, 1=sem |
| 19 | `Embarque` | Numero do embarque | `***` | Mascarado no portal |

#### Mapeamento Portal → Sistema de Fretes

| Conceito | Coluna CSV | Campo no sistema |
|----------|-----------|------------------|
| Protocolo de agendamento | `Agendamento` (NAO `Protocolo`) | `separacao.protocolo` |
| Data do agendamento | `Data Agendamento` (NAO `Data Desejada`) | `separacao.agendamento` |
| Filial | `Codigo` (1a coluna) | Resolver via `resolver_entidades` |
| Status valido nao recebido | `Aguardando check-in` | Agendamento aprovado, entrega pendente |

#### Cruzamento Local (--cruzar-local)

| Fonte | Tabela | Campos chave |
|-------|--------|--------------|
| Separacao | `separacao` | `cnpj_cpf`, `protocolo`, `agendamento`, `sincronizado_nf`, `numero_nf` |
| Entrega | `entregas_monitoradas` | `cnpj_cliente`, `numero_nf`, `entregue` |
| Agendamento | `agendamentos_entrega` | `entrega_id`, `protocolo_agendamento`, `data_agendada`, `status` |

| Classificacao | Criterio |
|---------------|----------|
| `agendamento_disponivel` | Protocolo no portal + `Separacao.sincronizado_nf=False` |
| `agenda_perdida` | `data_agendamento < hoje` + sem NF |
| `em_dia` | Agendamento futuro, tudo ok |
| `entregue` | `EntregaMonitorada.entregue=True` |

### Acao 3: Consultar Saldo
[A ser preenchido]

### Acao 4: Agendar em Lote
[A ser preenchido]
