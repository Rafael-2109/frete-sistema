# Sistema de Gestao de Devolucoes

## Visao Geral

Sistema completo para gerenciar devolucoes de mercadorias, desde o registro no monitoramento ate o lancamento no Odoo. Integra Logistica e Comercial em uma unica tela de ocorrencias.

**Criado em**: 30/12/2024
**Versao**: 3.0.0 (FASE 3 - FreteDevolucao + DescarteDevolucao)

---

## Arquitetura

### Estrutura de Diretorios

```
app/devolucao/
├── __init__.py              # Blueprint principal
├── models.py                # 9 modelos SQLAlchemy
├── README.md                # Esta documentacao
├── routes/
│   ├── __init__.py
│   ├── registro_routes.py   # APIs de registro NFD (FASE 1)
│   ├── ocorrencia_routes.py # APIs de ocorrencias (FASE 2)
│   ├── frete_routes.py      # APIs de frete e descarte (FASE 3)
│   ├── vinculacao_routes.py # APIs de vinculacao DFe (FASE 4)
│   └── ai_routes.py         # APIs de resolucao via Haiku (FASE 4.5)
└── services/
    ├── __init__.py
    ├── nfd_service.py       # Service de importacao do Odoo
    ├── nfd_xml_parser.py    # Parser de XML de NFD
    └── ai_resolver_service.py # Resolucao via Claude Haiku 4.5

app/templates/devolucao/
├── registro/
│   └── modal_nfd.html       # Modal de registro NFD
├── ocorrencias/
│   ├── index.html           # Dashboard de ocorrencias
│   └── detalhe.html         # Detalhe da ocorrencia
└── depara/
    ├── index.html           # Gerenciamento De-Para
    └── resolver_nfd.html    # Resolver produtos de NFD
```

### Modelos de Dados

| Modelo | Tabela | Descricao |
|--------|--------|-----------|
| NFDevolucao | `nf_devolucao` | Tabela principal unificada (registro + DFe) |
| NFDevolucaoLinha | `nf_devolucao_linha` | Linhas de produtos da NFD |
| NFDevolucaoNFReferenciada | `nf_devolucao_nf_referenciada` | NFs de venda referenciadas (M:N) |
| OcorrenciaDevolucao | `ocorrencia_devolucao` | Tratativa Comercial/Logistica |
| FreteDevolucao | `frete_devolucao` | Cotacao de frete de retorno |
| DescarteDevolucao | `descarte_devolucao` | Autorizacao de descarte com termo |
| ContagemDevolucao | `contagem_devolucao` | Contagem fisica por linha |
| AnexoOcorrencia | `anexo_ocorrencia` | Emails e fotos anexados |
| DeParaProdutoCliente | `depara_produto_cliente` | Mapeamento de codigos por CNPJ |

### Diagrama de Relacionamentos

```
EntregaMonitorada (existente)
    │
    └──< NFDevolucao (1:N)
            │
            ├──< NFDevolucaoLinha (1:N)
            │       │
            │       └──< ContagemDevolucao (1:1)
            │               │
            │               └──< AnexoOcorrencia (1:N) - Fotos
            │
            ├──< NFDevolucaoNFReferenciada (1:N) - NFs de venda referenciadas
            │       (extraidas do XML ou inseridas manualmente)
            │
            └──< OcorrenciaDevolucao (1:1)
                    │
                    ├──< FreteDevolucao (1:N)
                    │       │
                    │       └─── DespesaExtra (1:1 opcional)
                    │
                    ├──< DescarteDevolucao (1:N)
                    │       │
                    │       └─── DespesaExtra (1:1 opcional, custo descarte)
                    │
                    └──< AnexoOcorrencia (1:N) - Emails

DeParaProdutoCliente (tabela independente)
    - prefixo_cnpj (8 digitos)
    - codigo_cliente -> nosso_codigo
```

---

## FASE 1: Registro no Monitoramento

### Fluxo de Uso

1. Usuario acessa entrega no monitoramento
2. Clica em "Finalizar Entrega"
3. Modal pergunta: "Houve devolucao nesta entrega?"
   - **Cancelar**: Fecha modal
   - **Nao, Finalizar sem Devolucao**: Submete formulario normalmente
   - **Sim, Registrar NFD**: Abre modal de registro
4. Usuario preenche: numero NFD, motivo, descricao
5. Sistema cria NFDevolucao + OcorrenciaDevolucao automaticamente
6. Campo `teve_devolucao` da entrega e marcado como True

### APIs Disponiveis

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/devolucao/registro/api/registrar` | Registrar NFD |
| GET | `/devolucao/registro/api/listar/<entrega_id>` | Listar NFDs da entrega |
| GET | `/devolucao/registro/api/<nfd_id>` | Obter detalhes NFD |
| PUT | `/devolucao/registro/api/<nfd_id>` | Atualizar NFD |
| DELETE | `/devolucao/registro/api/<nfd_id>` | Excluir NFD (soft delete) |
| GET | `/devolucao/registro/api/motivos` | Listar motivos disponiveis |
| GET | `/devolucao/registro/modal/<entrega_id>` | Carregar modal HTML |

### APIs de Ocorrencias (FASE 2)

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/devolucao/ocorrencias/` | Dashboard de ocorrencias |
| GET | `/devolucao/ocorrencias/<ocorrencia_id>` | Detalhe da ocorrencia |
| GET | `/devolucao/ocorrencias/api/<ocorrencia_id>` | Obter dados da ocorrencia |
| PUT | `/devolucao/ocorrencias/api/<ocorrencia_id>/logistica` | Atualizar secao Logistica |
| PUT | `/devolucao/ocorrencias/api/<ocorrencia_id>/comercial` | Atualizar secao Comercial |
| GET | `/devolucao/ocorrencias/api/stats` | Estatisticas das ocorrencias |
| POST | `/devolucao/ocorrencias/api/<ocorrencia_id>/anexos` | Upload de anexo |
| GET | `/devolucao/ocorrencias/api/<ocorrencia_id>/anexos` | Listar anexos |
| GET | `/devolucao/ocorrencias/api/<ocorrencia_id>/anexos/<anexo_id>/download` | Download de anexo |
| DELETE | `/devolucao/ocorrencias/api/<ocorrencia_id>/anexos/<anexo_id>` | Excluir anexo |

### APIs de Vinculacao (FASE 4)

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/devolucao/vinculacao/api/sincronizar` | Sincronizar NFDs do Odoo |
| POST | `/devolucao/vinculacao/api/sincronizar/incremental` | Sincronizacao incremental (60min) |
| GET | `/devolucao/vinculacao/api/orfas` | Listar NFDs orfas |
| GET | `/devolucao/vinculacao/api/<nfd_id>` | Obter detalhes da NFD |
| GET | `/devolucao/vinculacao/api/<nfd_id>/candidatos` | Listar candidatos para vinculacao |
| POST | `/devolucao/vinculacao/api/<nfd_id>/vincular` | Vincular NFD manualmente |
| POST | `/devolucao/vinculacao/api/<nfd_id>/nfs-referenciadas` | Adicionar NF referenciada |
| DELETE | `/devolucao/vinculacao/api/<nfd_id>/nfs-referenciadas/<ref_id>` | Remover NF referenciada |
| GET | `/devolucao/vinculacao/api/estatisticas` | Estatisticas de NFDs |

### Exemplo de Requisicao

```json
POST /devolucao/registro/api/registrar
{
    "entrega_id": 123,
    "numero_nfd": "12345",
    "motivo": "AVARIA",
    "descricao_motivo": "Produto chegou danificado",
    "numero_nf_venda": "654321"
}
```

### Resposta

```json
{
    "success": true,
    "nfd_id": 1,
    "numero_nfd": "12345",
    "ocorrencia_id": 1,
    "numero_ocorrencia": "OC-202412-0001",
    "message": "NFD 12345 registrada com sucesso!"
}
```

### Motivos de Devolucao

| Codigo | Descricao |
|--------|-----------|
| AVARIA | Avaria |
| FALTA | Falta de Mercadoria |
| SOBRA | Sobra de Mercadoria |
| PRODUTO_ERRADO | Produto Errado |
| VENCIDO | Produto Vencido |
| PEDIDO_CANCELADO | Pedido Cancelado |
| CLIENTE_RECUSOU | Cliente Recusou |
| ENDERECO_NAO_ENCONTRADO | Endereco Nao Encontrado |
| PROBLEMA_FISCAL | Problema Fiscal |
| OUTROS | Outros |

---

## Migracao de Banco de Dados

### Scripts Disponiveis

| Arquivo | Uso |
|---------|-----|
| `scripts/migrations/criar_tabelas_devolucao_fase1.py` | Rodar localmente (FASE 1) |
| `scripts/migrations/criar_tabelas_devolucao_fase1.sql` | Copiar para Render Shell (FASE 1) |
| `scripts/migrations/add_descarte_devolucao.py` | Rodar localmente (FASE 3) |
| `scripts/migrations/criar_tabela_nf_referenciada_fase4.py` | Rodar localmente (FASE 4) |
| `scripts/migrations/criar_tabela_nf_referenciada_fase4.sql` | Copiar para Render Shell (FASE 4) |

### Executar Localmente

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
python scripts/migrations/criar_tabelas_devolucao_fase1.py
```

### Tabelas Criadas

1. `nf_devolucao` - Tabela principal (FASE 1)
2. `nf_devolucao_linha` - Linhas de produtos (FASE 1)
3. `nf_devolucao_nf_referenciada` - NFs de venda referenciadas (FASE 4)
4. `ocorrencia_devolucao` - Ocorrencias (FASE 1)
5. `frete_devolucao` - Fretes de retorno (FASE 1)
6. `descarte_devolucao` - Descartes autorizados (FASE 3)
7. `contagem_devolucao` - Contagem fisica (FASE 1)
8. `anexo_ocorrencia` - Anexos (FASE 1)
9. `depara_produto_cliente` - De-Para de produtos (FASE 1)

### Alteracao em Tabela Existente

```sql
ALTER TABLE entregas_monitoradas
ADD COLUMN IF NOT EXISTS teve_devolucao BOOLEAN DEFAULT FALSE NOT NULL;
```

---

## Fases de Implementacao

### FASE 1 - Registro no Monitoramento (CONCLUIDA)
- [x] Modelos de dados
- [x] APIs de registro
- [x] Modal de registro
- [x] Integracao com visualizar_entrega.html
- [x] Scripts de migracao

### FASE 2 - Tela de Ocorrencias (CONCLUIDA)
- [x] Dashboard de ocorrencias com filtros e paginacao
- [x] Secao Logistica (destino, localizacao, previsao retorno)
- [x] Secao Comercial (categoria, responsavel, status, desfecho)
- [x] Upload de anexos (emails, fotos, documentos)

### FASE 3 - FreteDevolucao + DescarteDevolucao (CONCLUIDA)
- [x] Modelo FreteDevolucao completo
- [x] Modelo DescarteDevolucao com fluxo de termo
- [x] APIs de CRUD para frete e descarte
- [x] Upload de documentos (termo, termo assinado, comprovante)
- [x] UI integrada na tela de ocorrencias
- [x] Atualizacao de status com reflexo em localizacao_atual

**Fluxo de Frete**:
```
1. Logistica decide por RETORNO
2. Cria cotacao de frete (transportadora, valor, rota)
3. Status: COTADO → APROVADO → COLETADO → ENTREGUE
4. Vincula a DespesaExtra quando faturado
```

**Fluxo de Descarte**:
```
1. Logistica decide por DESCARTE (custo > valor mercadoria)
2. Cria autorizacao com motivo
3. Gera e envia termo para cliente assinar
4. Cliente retorna termo assinado
5. Anexa comprovante de descarte (foto/documento)
6. Status: AUTORIZADO → TERMO_ENVIADO → TERMO_RETORNADO → DESCARTADO
```

**APIs de Frete/Descarte (FASE 3)**:

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/devolucao/frete/api/<ocorrencia_id>/fretes` | Listar fretes da ocorrencia |
| POST | `/devolucao/frete/api/<ocorrencia_id>/fretes` | Criar frete |
| GET | `/devolucao/frete/api/frete/<frete_id>` | Obter frete |
| PUT | `/devolucao/frete/api/frete/<frete_id>` | Atualizar frete |
| PUT | `/devolucao/frete/api/frete/<frete_id>/status` | Atualizar status |
| DELETE | `/devolucao/frete/api/frete/<frete_id>` | Excluir frete |
| GET | `/devolucao/frete/api/<ocorrencia_id>/descartes` | Listar descartes |
| POST | `/devolucao/frete/api/<ocorrencia_id>/descartes` | Criar descarte |
| GET | `/devolucao/frete/api/descarte/<descarte_id>` | Obter descarte |
| PUT | `/devolucao/frete/api/descarte/<descarte_id>/status` | Atualizar status |
| POST | `/devolucao/frete/api/descarte/<descarte_id>/upload/<tipo>` | Upload documento |
| DELETE | `/devolucao/frete/api/descarte/<descarte_id>` | Excluir descarte |

**Motivos de Descarte**:
| Codigo | Descricao |
|--------|-----------|
| CUSTO_ALTO | Custo de frete maior que valor da mercadoria |
| PERECIVEIS | Produtos pereciveis/vencidos |
| AVARIA_TOTAL | Avaria total - sem condicoes de retorno |
| CONTAMINACAO | Contaminacao/risco sanitario |
| CLIENTE_SOLICITOU | Cliente solicitou o descarte |
| OUTROS | Outros |

### FASE 4 - Vinculacao DFe + NFs Referenciadas (CONCLUIDA)
- [x] Modelo NFDevolucaoNFReferenciada (M:N NFs de venda)
- [x] NFDService para importar DFes do Odoo (finnfe=4)
- [x] Parser de XML para extrair NFs referenciadas
- [x] Vinculacao automatica por numero + CNPJ
- [x] Criacao automatica de OcorrenciaDevolucao para orfas
- [x] APIs de vinculacao manual (fallback)

### FASE 4.5 - Claude Haiku para Resolucao Inteligente (CONCLUIDA)

**Modelo**: `claude-haiku-4-5-20251001` (custo estimado: ~$0.003/chamada)

**Funcionalidades Implementadas**:
1. **De-Para de Produtos** - Identificar nosso codigo a partir do codigo/descricao do cliente
2. **NF de Venda Original** - Extrair numero da NF das observacoes em texto livre
3. **Motivo da Devolucao** - Identificar motivo a partir das observacoes
4. **Unidade de Medida** - Normalizar unidades (CXA1, UNI9 → Caixa, Unidade)

**Fluxo de Resolucao de Produtos**:
```
1. Recebe: codigo_cliente + descricao_cliente + prefixo_cnpj
2. Consulta: De-Para existente no banco
3. Se nao encontrar: busca candidatos via resolver_entidades
4. Envia: Lista de candidatos para Haiku analisar
5. Retorna:
   - Certeza ALTA (>90%) → Match automatico, grava De-Para
   - Certeza MEDIA (50-90%) → Lista opcoes provaveis para usuario
   - Certeza BAIXA (<50%) → Solicita cadastro manual
```

**Fluxo de Extracao de Observacoes**:
```
Entrada: "DEVOLUÇÃO REF NF 123456 - PRODUTO AVARIADO NO TRANSPORTE"
Saida:
  - numero_nf_venda: "123456"
  - motivo_sugerido: "AVARIA"
  - descricao_motivo: "Produto avariado no transporte"
  - confianca: 0.95
```

**APIs de Resolucao via Haiku (FASE 4.5)**:

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/devolucao/ai/depara` | Pagina de gerenciamento De-Para |
| GET | `/devolucao/ai/resolver/<nfd_id>` | Pagina para resolver produtos de NFD |
| POST | `/devolucao/ai/api/resolver-produto` | Resolver codigo do cliente |
| POST | `/devolucao/ai/api/extrair-observacao` | Extrair NF/motivo de texto |
| POST | `/devolucao/ai/api/normalizar-unidade` | Normalizar unidade de medida |
| POST | `/devolucao/ai/api/nfd/<nfd_id>/resolver-linhas` | Resolver todas as linhas de NFD |
| POST | `/devolucao/ai/api/nfd/<nfd_id>/atualizar-motivo` | Aplicar motivo extraido pela IA |
| POST | `/devolucao/ai/api/linha/<linha_id>/confirmar` | Confirmar resolucao |
| GET | `/devolucao/ai/api/depara` | Listar De-Para cadastrados |
| POST | `/devolucao/ai/api/depara` | Criar novo De-Para |
| PUT | `/devolucao/ai/api/depara/<id>` | Atualizar De-Para |
| DELETE | `/devolucao/ai/api/depara/<id>` | Excluir De-Para |
| GET | `/devolucao/ai/api/estatisticas` | Estatisticas de resolucao |

**Arquivos Criados**:
- `app/devolucao/services/ai_resolver_service.py` - AIResolverService com Haiku
- `app/devolucao/routes/ai_routes.py` - APIs e rotas de pagina
- `app/templates/devolucao/depara/index.html` - Tela De-Para
- `app/templates/devolucao/depara/resolver_nfd.html` - Resolver produtos NFD
- `scripts/migrations/add_confianca_resolucao_nfd_linha.py` - Campo confianca

**Campos Adicionados aos Modelos**:
- `NFDevolucaoLinha.confianca_resolucao` - NUMERIC(5,4) para armazenar confianca (0.0000 a 1.0000)
- `NFDevolucao.info_complementar` - TEXT para armazenar infCpl do XML (motivo da devolucao)

**Extracao de Motivo da NFD (v2.6.0)**:

A funcionalidade de extracao de motivo permite analisar o campo `info_complementar` (tag infCpl do XML) usando Claude Haiku para identificar automaticamente:
- Numero da NF de venda original
- Motivo da devolucao (AVARIA, FALTA, PRODUTO_ERRADO, etc.)
- Descricao detalhada do motivo

**Fluxo**:
```
1. NFD importada do Odoo → info_complementar extraido automaticamente do XML
2. Na tela "Resolver NFD", usuario ve o texto em um textarea
3. Botao "Extrair Motivo (IA)" chama /api/extrair-observacao
4. Haiku analisa e sugere NF de venda + motivo + confianca
5. Usuario clica "Aplicar" para salvar via /api/nfd/{id}/atualizar-motivo
```

**Tarefas Concluidas**:
- [x] Documentar plano
- [x] Criar AIResolverService (Claude Haiku 4.5)
- [x] Extrair NF de venda e motivo das observacoes
- [x] Normalizar unidade de medida
- [x] Criar tela De-Para com sugestoes do Haiku
- [x] Criar rotas API para resolucao
- [x] Adicionar campo confianca_resolucao ao modelo
- [x] Adicionar campo info_complementar para armazenar infCpl do XML
- [x] Extrair info_complementar automaticamente na importacao de NFDs
- [x] Criar UI para extracao de motivo com botao "Extrair Motivo (IA)"
- [x] API para aplicar motivo extraido (`/api/nfd/{id}/atualizar-motivo`)

### FASE 5 - Contagem/Inspecao (PENDENTE)
- [ ] Interface de contagem
- [ ] Upload de fotos
- [ ] Qualidade do produto

### FASE 6 - Lancamento no Odoo (PENDENTE)
- [ ] Processo de 16 etapas
- [ ] Lancamento fiscal

---

## Campos do Modelo NFDevolucao

### Dados do Registro Inicial
- `numero_nfd` - Numero da NFD
- `data_registro` - Data do registro
- `motivo` - Motivo da devolucao
- `descricao_motivo` - Descricao detalhada
- `numero_nf_venda` - NF de venda relacionada
- `info_complementar` - Texto livre extraido do XML (tag infCpl) com motivo/observacoes do cliente

### Dados do DFe Odoo (preenchido na importacao)
- `odoo_dfe_id` - ID do DFe no Odoo
- `odoo_name` - Nome no Odoo (ex: DFE/2025/15797)
- `chave_nfd` - Chave de acesso (44 digitos)
- `serie_nfd` - Serie da NFD
- `data_emissao` - Data de emissao
- `valor_total` - Valor total

### Arquivos
- `nfd_xml_path` - Caminho do XML no S3
- `nfd_pdf_path` - Caminho do PDF no S3

### Status
- `REGISTRADA` - Registro inicial
- `VINCULADA_DFE` - DFe importado do Odoo
- `EM_TRATATIVA` - Em analise comercial/logistica
- `AGUARDANDO_RECEBIMENTO` - Aguardando chegada no CD
- `RECEBIDA` - Mercadoria recebida
- `CONTADA` - Contagem realizada
- `FINALIZADA` - Processo concluido

### Origem do Registro (FASE 4)
- `MONITORAMENTO` - NFD registrada manualmente no monitoramento
- `ODOO` - NFD importada automaticamente do Odoo (orfa)

---

## Configuracao

### Blueprint

```python
# app/__init__.py
from app.devolucao import devolucao_bp
app.register_blueprint(devolucao_bp)
```

### URL Prefix

O modulo usa o prefixo `/devolucao`:
- `/devolucao/registro/...` - Rotas de registro (FASE 1)
- `/devolucao/ocorrencias/...` - Rotas de ocorrencias (FASE 2)
- `/devolucao/frete/...` - Rotas de frete e descarte (FASE 3)
- `/devolucao/vinculacao/...` - Rotas de vinculacao DFe (FASE 4)
- `/devolucao/ai/...` - Rotas de resolucao via Haiku (FASE 4.5)

---

## Arquivos Modificados

| Arquivo | Alteracao |
|---------|-----------|
| `app/__init__.py` | Import e registro do blueprint |
| `app/monitoramento/models.py` | Campo `teve_devolucao` em EntregaMonitorada |
| `app/templates/monitoramento/visualizar_entrega.html` | Botao e modais de finalizacao/NFD |
| `app/devolucao/models.py` | Modelo NFDevolucaoNFReferenciada e campo origem_registro (FASE 4) |
| `app/devolucao/__init__.py` | Registro do vinculacao_bp (FASE 4) |

## Arquivos Criados (FASE 4)

| Arquivo | Descricao |
|---------|-----------|
| `app/devolucao/services/nfd_service.py` | Service de importacao de NFDs do Odoo |
| `app/devolucao/services/nfd_xml_parser.py` | Parser de XML para extrair NFs referenciadas |
| `app/devolucao/routes/vinculacao_routes.py` | APIs de vinculacao e sincronizacao |
| `scripts/migrations/criar_tabela_nf_referenciada_fase4.py` | Script de migracao local |
| `scripts/migrations/criar_tabela_nf_referenciada_fase4.sql` | Script SQL para Render |

## Arquivos Criados (FASE 4.5)

| Arquivo | Descricao |
|---------|-----------|
| `app/devolucao/services/ai_resolver_service.py` | AIResolverService com Claude Haiku 4.5 |
| `app/devolucao/routes/ai_routes.py` | APIs de resolucao e paginas De-Para |
| `app/templates/devolucao/depara/index.html` | Tela de gerenciamento De-Para |
| `app/templates/devolucao/depara/resolver_nfd.html` | Tela para resolver produtos de NFD |
| `scripts/migrations/add_confianca_resolucao_nfd_linha.py` | Script de migracao do campo confianca |
| `scripts/migrations/add_info_complementar_nf_devolucao.py` | Script de migracao do campo info_complementar |

## Arquivos Criados (FASE 3)

| Arquivo | Descricao |
|---------|-----------|
| `app/devolucao/routes/frete_routes.py` | APIs de frete e descarte |
| `scripts/migrations/add_descarte_devolucao.py` | Script de migracao da tabela descarte_devolucao |

---

## Dependencias

- Flask
- Flask-Login
- SQLAlchemy
- Bootstrap 5 (frontend)
- Anthropic (Claude Haiku 4.5 para FASE 4.5)

---

## Contato

Para duvidas ou sugestoes, consulte o arquivo `.claude/plans/foamy-juggling-lynx.md` com o plano completo de implementacao.
