# CLAUDE_MODELOS.md — Modelos do modulo Devolucao

> Detalhamento de `app/devolucao/models.py` (~1951 LOC, 18 modelos).
> Ver `CLAUDE.md` para visao geral e gotchas de nivel sistema.

---

## Diagrama de Relacionamentos

```
EntregaMonitorada (app/monitoramento)
  ├── teve_devolucao (bool)
  └── NFDevolucao [1:N via entrega_monitorada_id]
        │
        ├── NFDevolucaoLinha [1:N via nf_devolucao_id, CASCADE]
        │     ├── ContagemDevolucao [1:1, CASCADE]
        │     │     └── AnexoOcorrencia [1:N] (fotos)
        │     └── DescarteItem [1:N via nfd_linha_id, CASCADE]
        │
        ├── NFDevolucaoNFReferenciada [1:N, CASCADE]
        │     └── EntregaMonitorada [N:1 via entrega_monitorada_id]
        │
        └── OcorrenciaDevolucao [1:1 UNIQUE, CASCADE]
              │
              ├── OcorrenciaCategoria [N:M via ocorrencia_devolucao_categoria]
              ├── OcorrenciaSubcategoria [N:M via ocorrencia_devolucao_subcategoria]
              ├── OcorrenciaResponsavel [N:1 via responsavel_id]
              ├── OcorrenciaOrigem [N:1 via origem_id]
              ├── OcorrenciaAutorizadoPor [N:1 via autorizado_por_id]
              ├── Transportadora [N:1 via transportadora_retorno_id]
              │
              ├── FreteDevolucao [1:N]
              │     ├── Transportadora [N:1]
              │     └── DespesaExtra [1:1 opcional via despesa_extra_id]
              │
              ├── DescarteDevolucao [1:N, CASCADE]
              │     ├── DescarteItem [1:N, CASCADE]
              │     └── DespesaExtra [1:1 opcional via despesa_extra_id]
              │
              └── AnexoOcorrencia [1:N, CASCADE] (emails, docs)

DeParaProdutoCliente                    # Standalone (prefixo_cnpj -> nosso_codigo)
PermissaoCadastroDevolucao              # Standalone (usuario_id x tipo_cadastro)
```

---

## NFDevolucao (`nf_devolucao`)

Tabela central — **unifica registro manual + dados do DFe Odoo**.

**PK**: `id`
**Indices unicos**: `odoo_dfe_id`, `chave_nfd`
**Indices compostos**: `numero_nfd+serie_nfd`, `cnpj_emitente+status`, `status_odoo+status_monitoramento`

### Campos chave

| Campo | Tipo | Observacao |
|-------|------|------------|
| `numero_nfd` | str(20) NOT NULL | Numero da NFD (ou da NF revertida, se `tipo_documento='NF'`) |
| `motivo` | str(50) NOT NULL | Uma de `MOTIVOS_DEVOLUCAO` (10 valores) |
| `descricao_motivo` | TEXT | Pode ser preenchido por IA |
| `confianca_motivo` | Numeric(5,4) | Confianca da extracao por IA (NULL = nao processado) |
| `numero_nf_venda` | str(20) | NF de venda original (pode vir do XML refNFe) |
| `odoo_dfe_id` | int UNIQUE | ID do DFe no Odoo (None para manual) |
| `odoo_name` | str(100) | Ex: `DFE/2025/15797` |
| `odoo_status_codigo` | str(10) | `'06'` = Concluido (= **entrada fisica realizada**) |
| `chave_nfd` | str(44) UNIQUE | Chave de acesso fiscal |
| `data_emissao` | Date | Data de emissao da NFD |
| `data_entrada` | Date | Data de lancamento (ANTES da entrada fisica — nao confundir) |
| `cnpj_emitente` | str(20) | **RAW** (sem mascara). Ver Gotcha 6 em CLAUDE.md |
| `cnpj_destinatario` | str(20) | Nosso CNPJ (Nacom) — raw |
| `info_complementar` | TEXT | Texto livre (tag `<infCpl>` do XML) — input para IA |
| `nfd_xml_path` | str(500) | S3 path do XML |
| `nfd_pdf_path` | str(500) | S3 path do DANFE |
| `status` | str(30) | Uma de `STATUS_CHOICES` (8 valores). Default `REGISTRADA` |
| `origem_registro` | str(20) | `MONITORAMENTO` ou `ODOO` |
| `tipo_documento` | str(10) | `NFD` (devolucao real) ou `NF` (venda revertida) |
| `status_odoo` | str(30) | `Devolucao` / `Revertida` / `Cancelada` |
| `status_monitoramento` | str(30) | `Cancelada` / `Devolvida` / `Troca de NF` |
| `odoo_nf_venda_id` | int | ID da NF original no Odoo (para reversao) |
| `odoo_nota_credito_id` | int | ID da NC (`out_refund`) |
| `numero_nota_credito` | str(20) | Numero da NC |
| `e_pallet_devolucao` | bool | True quando CFOPs de vasilhame — **NAO tratar neste modulo** |
| `ativo` | bool | Soft delete |

### Enums

```python
MOTIVOS_DEVOLUCAO = [
    ('AVARIA', 'FALTA', 'SOBRA', 'PRODUTO_ERRADO', 'VENCIDO',
     'PEDIDO_CANCELADO', 'CLIENTE_RECUSOU', 'ENDERECO_NAO_ENCONTRADO',
     'PROBLEMA_FISCAL', 'OUTROS')
]

STATUS_CHOICES = [
    ('REGISTRADA', 'VINCULADA_DFE', 'EM_TRATATIVA', 'AGUARDANDO_RECEBIMENTO',
     'RECEBIDA', 'CONTADA', 'FINALIZADA', 'CANCELADA')
]

TIPOS_DOCUMENTO = [('NFD', 'NF')]
ORIGENS_REGISTRO = [('MONITORAMENTO', 'ODOO')]
```

### Properties / metodos uteis

- `status_descricao`, `motivo_descricao`, `tipo_documento_descricao` — converte codigo para label
- `prefixo_cnpj_emitente` — 8 primeiros digitos (para lookup em `DeParaProdutoCliente`)
- `tem_dfe_vinculado` — bool (`odoo_dfe_id is not None`)
- `status_entrada_odoo` — `'Entrada OK'` (se `odoo_status_codigo == '06'`) ou `'Pendente'`
- `numero_com_prefixo` — ex: `NFD 12345` ou `NF 12345`
- `numero_com_status_entrada` — ex: `NFD - 12345 - Entrada OK`
- `to_dict()` — serializacao JSON com **tudo** (inclusive campos denormalizados)

---

## NFDevolucaoLinha (`nf_devolucao_linha`)

Linhas de produto da NFD — importadas do DFe ou criadas em reversao.

| Campo | Tipo | Observacao |
|-------|------|------------|
| `codigo_produto_cliente` | str(255) | Original da NFD (pode ter lote/validade concatenado) |
| `codigo_produto_interno` | str(50) | Resolvido via De-Para ou Haiku |
| `descricao_produto_cliente` | TEXT | Descricao original |
| `produto_resolvido` | bool | True se `codigo_produto_interno` preenchido |
| `metodo_resolucao` | str(20) | `DEPARA` / `HAIKU` / `MANUAL` / `ODOO` |
| `confianca_resolucao` | Numeric(5,4) | 0.0000 a 1.0000 |
| `quantidade` | Numeric(15,3) | Qtd original |
| `unidade_medida` | str(20) | UN / CX / KG / PC |
| `quantidade_convertida` | Numeric(15,4) | **Convertido para caixas** (padrao de venda) |
| `qtd_por_caixa` | int | Ex: 12 (para produto `12X180G`) |
| `valor_unitario` | Numeric(15,4) | Preco unitario (da unidade original) |
| `valor_total` | Numeric(15,2) | Valor total da linha (fiscalmente exato) |
| `cfop`, `ncm` | str | Dados fiscais |
| `numero_item` | int | Ordem na NFD |

**Regras de calculo** (ver `ocorrencia_routes.py:1386` para logica fiscalmente correta):
```python
preco_por_caixa = valor_total / quantidade_convertida  # preferido
# Fallbacks (em ordem):
preco_por_caixa = valor_total / quantidade
preco_por_caixa = valor_unitario * qtd_por_caixa
preco_por_caixa = valor_unitario
```

---

## NFDevolucaoNFReferenciada (`nf_devolucao_nf_referenciada`)

NFs de venda referenciadas pela NFD (M:N, pois uma NFD pode referenciar varias NFs e vice-versa).

| Campo | Tipo | Observacao |
|-------|------|------------|
| `numero_nf` | str(20) NOT NULL | Numero da NF de venda |
| `serie_nf` | str(10) | Serie |
| `chave_nf` | str(44) | Chave de acesso (se disponivel) |
| `data_emissao_nf` | Date | Data de emissao da NF referenciada |
| `origem` | str(20) | `XML` / `MANUAL` / `MONITORAMENTO` / `ODOO_REVERSAO` |
| `entrega_monitorada_id` | int FK | Vinculo opcional com `EntregaMonitorada` |

**Unique constraint**: `(nf_devolucao_id, numero_nf, serie_nf)`

---

## OcorrenciaDevolucao (`ocorrencia_devolucao`)

Ocorrencia unificada **1:1 com NFDevolucao**. Tem duas "secoes":
- **Logistica** — destino, localizacao, transportadora de retorno
- **Comercial** — categoria/subcategoria (N:M), responsavel, origem, momento, desfecho

| Campo | Tipo | Observacao |
|-------|------|------------|
| `nf_devolucao_id` | int FK UNIQUE | 1:1 obrigatorio com NFD |
| `numero_ocorrencia` | str(20) UNIQUE | Formato `{NNNNN}/{AA}` (sequencia global ≥17500) |
| `destino` | str(20) | `RETORNO` / `DESCARTE` / `REENTREGA` / `INDEFINIDO` |
| `localizacao_atual` | str(20) | `CLIENTE` / `TRANSPORTADORA` / `EM_TRANSITO` / `CD` / `DESCARTADO` |
| `transportadora_retorno_id` | int FK | FK para `transportadoras` |
| `data_previsao_retorno` | Date | Planejamento |
| `data_chegada_cd` | DateTime | Efetivo |
| `recebido_por` | str(100) | Quem recebeu no CD |
| `categoria` | str(30) | **Legado** (cache denormalizado). Usar `categorias` N:M como fonte |
| `subcategoria` | str(50) | **Legado**. Usar `subcategorias` N:M |
| `responsavel` | str(30) | **Legado**. Usar `responsavel_id` FK |
| `responsavel_id` | int FK | Para `OcorrenciaResponsavel` |
| `origem_id` | int FK | Para `OcorrenciaOrigem` |
| `autorizado_por_id` | int FK | Para `OcorrenciaAutorizadoPor` |
| `momento_devolucao` | str(20) | `ATO_ENTREGA` / `POSTERIOR_ENTREGA` / `INDEFINIDO` |
| `autorizado_por` | str(100) | **Legado varchar** (texto livre) |
| `resolvido_por` | str(100) | Quem resolveu |
| `desfecho` | TEXT | Descricao do desfecho |
| `status` | str(30) | **Auto-computado** (ver `calcular_status()`). `PENDENTE`/`EM_ANDAMENTO`/`RESOLVIDO` |
| `data_abertura` | DateTime | Quando criada |
| `data_acao_comercial` | DateTime | Quando comercial agiu |
| `data_resolucao` | DateTime | Quando resolveu |

### Enums

```python
DESTINOS = [('RETORNO','DESCARTE','REENTREGA','INDEFINIDO')]
LOCALIZACOES = [('CLIENTE','TRANSPORTADORA','EM_TRANSITO','CD','DESCARTADO')]
STATUS_OCORRENCIA = [('PENDENTE','EM_ANDAMENTO','RESOLVIDO')]

# Legados (manter por compat — usar lookup tables FK):
CATEGORIAS = [('QUALIDADE','COMERCIAL','LOGISTICA','FISCAL','CLIENTE','PRODUCAO')]
RESPONSAVEIS = [('NACOM','TRANSPORTADORA','CLIENTE','FORNECEDOR','INDEFINIDO')]
ORIGENS = [('PRODUCAO','EXPEDICAO','TRANSPORTE','CLIENTE','COMERCIAL','INDEFINIDO')]
```

### Metodos criticos

```python
def _campos_comerciais_preenchidos() -> bool:
    """Verifica os 7 campos comerciais obrigatorios:
    1. categorias (N:M, ≥1)
    2. subcategorias (N:M, ≥1)
    3. responsavel_id (FK)
    4. origem_id (FK)
    5. autorizado_por_id (FK)
    6. momento_devolucao (!= None, != 'INDEFINIDO')
    7. desfecho (!= None, strip != '')
    """

def calcular_status() -> str:
    """Auto-computa status:
    - RESOLVIDO: 7 campos + NFD com entrada (odoo_status_codigo='06')
    - EM_ANDAMENTO: 7 campos mas sem entrada
    - PENDENTE: campos comerciais incompletos
    """

@classmethod
def gerar_numero_ocorrencia() -> str:
    """Retorna '{NNNNN}/{AA}' com sequencia GLOBAL >= 17500.
    NAO reinicia por mes/ano.
    """
```

**Gotcha**: quando atualizar campos comerciais, chamar `calcular_status()` e persistir. Nunca setar `status` por fora.

---

## FreteDevolucao (`frete_devolucao`)

Cotacao de frete de retorno.

| Campo | Tipo | Observacao |
|-------|------|------------|
| `ocorrencia_devolucao_id` | int FK | Pode ser NULL (para devolucoes antigas) |
| `despesa_extra_id` | int FK | `DespesaExtra` gerada (opcional) |
| `transportadora_id` | int FK | FK `transportadoras` |
| `transportadora_nome` | str(255) NOT NULL | Cache (mesmo com FK) |
| `valor_cotado` | Numeric(15,2) NOT NULL | Valor inicial |
| `valor_negociado` | Numeric(15,2) | Valor apos negociacao |
| `peso_kg` | Numeric(15,3) | Calculado via `/api/{oc}/calcular-peso` |
| `data_cotacao` | Date NOT NULL | Obrigatorio |
| `local_coleta` | str(255) | Nome do local de coleta (digitavel) |
| `uf_origem`, `cidade_origem`, `uf_destino`, `cidade_destino` | | Rota |
| `status` | str(20) | `COTADO`/`APROVADO`/`COLETADO`/`EM_TRANSITO`/`ENTREGUE`/`CANCELADO` |
| `numero_cte`, `chave_cte` | | CTe do retorno |

Property `valor_final` → retorna `valor_negociado or valor_cotado`.

---

## DescarteDevolucao (`descarte_devolucao`)

Autorizacao de descarte quando nao compensa retornar a mercadoria.

**Fluxo de status**: `AUTORIZADO` → `TERMO_ENVIADO` → `TERMO_RETORNADO` → `DESCARTADO` (ou `CANCELADO` a qualquer momento)

| Campo | Tipo | Observacao |
|-------|------|------------|
| `numero_termo` | str(50) | Formato `TD-YYYYMM-XXXX` (gerado por `gerar_numero_termo()`) |
| `data_autorizacao` | DateTime | Obrigatorio |
| `autorizado_por` | str(100) NOT NULL | Quem autorizou internamente |
| `motivo_descarte` | str(50) NOT NULL | Uma de `MOTIVOS_DESCARTE` |
| `descricao_motivo` | TEXT | Detalhes |
| `valor_mercadoria` | Numeric(15,2) | Para % de descarte vs total |
| `empresa_autorizada_nome` | str(255) | Razao social (transportador OU cliente) |
| `empresa_autorizada_documento` | str(20) | CNPJ ou CPF |
| `empresa_autorizada_tipo` | str(20) | `TRANSPORTADOR` / `CLIENTE` |
| `termo_path`, `termo_nome_arquivo` | | S3 termo original |
| `termo_enviado_em`, `termo_enviado_para` | | Rastreio envio |
| `termo_assinado_path`, `termo_retornado_em` | | S3 termo assinado |
| `comprovante_path`, `data_descarte` | | S3 comprovante + data efetiva |
| `tem_custo` | bool | True se descarte pago |
| `valor_descarte` | Numeric(15,2) | Custo de destruicao |
| `fornecedor_descarte` | str(255) | Empresa de descarte |
| `despesa_extra_id` | int FK | `DespesaExtra` para o custo |
| `termo_impresso_por`, `termo_impresso_em` | | Rastreio PDF |
| `termo_salvo_por`, `termo_salvo_em` | | Rastreio download |

```python
MOTIVOS_DESCARTE = [
    ('CUSTO_ALTO', 'PERECIVEIS', 'AVARIA_TOTAL',
     'CONTAMINACAO', 'CLIENTE_SOLICITOU', 'OUTROS')
]
```

---

## DescarteItem (`descarte_item`)

Itens individuais de um descarte (permite descarte parcial de uma NFD).

| Campo | Tipo | Observacao |
|-------|------|------------|
| `descarte_id` | int FK CASCADE | |
| `nfd_linha_id` | int FK CASCADE | Vinculo com a linha |
| `quantidade_descarte` | Numeric(15,3) | Qtd em unidades originais |
| `quantidade_caixas` | Numeric(15,3) | Qtd em caixas |
| `valor_descarte` | Numeric(15,2) | Valor da linha descartada |

---

## ContagemDevolucao (`contagem_devolucao`)

**Fase 5 (NAO implementada)** — model ja existe, sem UI.

| Campo | Tipo | Observacao |
|-------|------|------------|
| `nf_devolucao_linha_id` | int FK UNIQUE CASCADE | 1:1 com linha |
| `caixas_conforme`, `unidades_conforme` | int | OK |
| `caixas_nao_conforme`, `unidades_nao_conforme` | int | Avariado |
| `caixas_faltantes`, `unidades_faltantes` | int | Diff declarado vs contado |
| `status_qualidade` | str(20) | `PENDENTE`/`APROVADO`/`REPROVADO`/`PARCIAL` |
| `destino_produto` | str(20) | `PENDENTE`/`ESTOQUE`/`QUARENTENA`/`DESCARTE` |
| `conferente` | str(100) NOT NULL | Quem contou |

Properties: `total_conforme`, `total_nao_conforme`, `total_faltante`.

---

## AnexoOcorrencia (`anexo_ocorrencia`)

Anexos vinculados a **ocorrencia OU contagem** (XOR via CHECK constraint).

| Campo | Tipo | Observacao |
|-------|------|------------|
| `ocorrencia_devolucao_id` | int FK | Pode ser NULL (se contagem) |
| `contagem_devolucao_id` | int FK | Pode ser NULL (se ocorrencia) |
| `tipo` | str(20) | `EMAIL`/`FOTO`/`DOCUMENTO`/`PLANILHA`/`OUTROS` |
| `nome_original`, `nome_arquivo` | str | Uploadado pelo usuario / renomeado |
| `caminho_s3` | str(500) NOT NULL | Path no S3 |
| `tamanho_bytes`, `content_type` | | Metadata |
| `email_remetente`, `email_assunto`, `email_data_envio`, `email_preview` | | Se `tipo=EMAIL` (parseado de .msg) |
| `descricao` | TEXT | Contexto do anexo |

**Check constraint**: `ocorrencia_devolucao_id IS NOT NULL OR contagem_devolucao_id IS NOT NULL`.

Properties: `extensao`, `tamanho_kb`.

---

## DeParaProdutoCliente (`depara_produto_cliente`)

Mapeamento **prefixo CNPJ (8 digitos) → nosso codigo**. Cache populado por `AIResolverService` quando confianca > 0.9.

| Campo | Tipo | Observacao |
|-------|------|------------|
| `prefixo_cnpj` | str(8) NOT NULL | **8 primeiros digitos** (raiz do grupo) |
| `codigo_cliente` | str(255) NOT NULL | Codigo na NFD |
| `nosso_codigo` | str(50) NOT NULL | Nosso SKU |
| `descricao_cliente`, `descricao_nosso` | str | Cache para exibicao |
| `fator_conversao` | Numeric(10,4) | Default 1.0. Ex: `1 CX cliente = 12 UN nosso → fator 12` |
| `unidade_medida_cliente`, `unidade_medida_nosso` | str(20) | UN / CX / KG |
| `nome_grupo` | str(255) | Ex: `Atacadao`, `Assai` |
| `ativo` | bool | |

**Unique constraint**: `(prefixo_cnpj, codigo_cliente)`.

### Metodo estatico util

```python
@classmethod
def obter_nosso_codigo(cnpj_cliente, codigo_cliente) -> dict | None:
    """Lookup por prefixo CNPJ + codigo do cliente.
    Retorna dict com nosso_codigo, fator_conversao, unidades.
    """
```

---

## Tabelas Lookup (para CRUD via modal)

Todas tem `id`, `codigo`, `descricao`, `ativo`, auditoria (`criado_em`, `criado_por`, etc.).

### OcorrenciaCategoria (`ocorrencia_categoria`)
Nao tem FK. Standalone.

### OcorrenciaSubcategoria (`ocorrencia_subcategoria`)
**FK obrigatoria**: `categoria_id`. Subcategorias pertencem a 1 categoria.

### OcorrenciaResponsavel (`ocorrencia_responsavel`)
**FK obrigatoria**: `categoria_id`. Responsaveis filtrados por categoria.

### OcorrenciaOrigem (`ocorrencia_origem`)
Nao tem FK. Standalone.

### OcorrenciaAutorizadoPor (`ocorrencia_autorizado_por`)
Nao tem FK. Standalone.

---

## Tabelas de Juncao N:M

### OcorrenciaDevolucaoCategoria (`ocorrencia_devolucao_categoria`)
- FKs CASCADE: `ocorrencia_devolucao_id`, `categoria_id`
- Unique: `(ocorrencia_devolucao_id, categoria_id)`

### OcorrenciaDevolucaoSubcategoria (`ocorrencia_devolucao_subcategoria`)
- FKs CASCADE: `ocorrencia_devolucao_id`, `subcategoria_id`
- Unique: `(ocorrencia_devolucao_id, subcategoria_id)`

**SQLAlchemy overlap flag**: `overlaps='categoria'` / `overlaps='subcategoria'` (evita warning com campos varchar legados).

---

## PermissaoCadastroDevolucao (`permissao_cadastro_devolucao`)

Controla CRUD de lookup tables por usuario.

| Campo | Tipo | Observacao |
|-------|------|------------|
| `usuario_id` | int FK | FK `usuarios.id` |
| `tipo_cadastro` | str(30) NOT NULL | `categorias` / `subcategorias` / `responsaveis` / `origens` |
| `pode_criar`, `pode_editar`, `pode_excluir` | bool | Default False |
| `concedido_por`, `concedido_em` | | Auditoria |
| `ativo` | bool | Soft delete |

**Unique**: `(usuario_id, tipo_cadastro)`.

**Bypass automatico**: `administrador` e `gerente_comercial` nao precisam de registro — ver `_verificar_permissao_cadastro` em `cadastro_routes.py:43`.

---

## Fluxo de vinculacao NFD ↔ Registro Manual

```
Entrada A (Manual): usuario clica "Sim, Registrar NFD" no monitoramento
  → cria NFDevolucao com origem_registro='MONITORAMENTO',
    sem odoo_dfe_id, sem chave_nfd.

Entrada B (Odoo): NFDService roda via cron
  → busca DFe com finnfe=4 no Odoo
  → tenta vincular por (numero_nfd, cnpj_emitente) com registro existente
  → SE encontrar: atualiza campos fiscais (chave, valor, XML, PDF, etc.)
  → SE nao: cria orfa com origem_registro='ODOO' + ocorrencia automatica
```

Status transitions:
- `REGISTRADA` → `VINCULADA_DFE` (quando importa XML do Odoo)
- Manual pode ir direto para `EM_TRATATIVA` ao abrir ocorrencia
