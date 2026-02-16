# Indice — Modulo Comercial SSW

> **Diretorio**: `.claude/references/ssw/comercial/`
> **Atualizado em**: 2026-02-14

Este indice consolida toda a documentacao do modulo Comercial do SSW Sistemas, organizada por area tematica.

---

## Documentacao Disponivel

### Tabelas de Frete (CORE)
| Arquivo | Opcoes | Descricao |
|---------|--------|-----------|
| `417-418-420-tabelas-frete.md` | 417, 418, 420, 427, 923 | **DOCUMENTO PRINCIPAL** - Todos tipos tabelas frete (Combinada, Percentual, Faixa Peso, Rota, NTC). Adicionais (GRIS, TDE, TRT, etc). Prioridades e integracao. |

### Comissionamento e Vendas
| Arquivo | Opcao | Descricao |
|---------|-------|-----------|
| `408-comissao-unidades.md` | 408 | Comissionamento unidades (filiais, terceiros, embarcadores). Expedicao, recepcao, transbordo. Parcerias SSW. Formas credito CCF (Mapa/Fatura/Capa). |
| `415-gerenciamento-vendedores.md` | 415 | Gerenciamento vendedores. Vinculos cliente-vendedor. Comissoes (conquista/manutencao). Relatorios. Equipes. |
| `397-metas-clientes-alvo.md` | 397 | Metas vendedores e clientes alvo. Acompanhamento performance (relatorios 125/126). |

### Parametros Comerciais
| Arquivo | Opcao | Descricao |
|---------|-------|-----------|
| `423-parametros-comerciais-cliente.md` | 423 | Parametros por cliente: reentrega, devolucao, recoleta, armazenagem, servicos complementares (paletizacao, agendamento, separacao, capatazia). Cubagem. |
| `422-local-entrega-subcontratados.md` | 422 | Endereco especifico entrega para subcontratados (diferente unidade distribuicao). |

### Operacoes e Processos
| Arquivo | Opcao | Descricao |
|---------|-------|-----------|
| `398-escanear-comprovantes-entregas.md` | 398 | Escaneamento comprovantes entrega. SSWScan. Anexacao manual. |
| `OPCOES-COMPLEMENTARES.md` | 428, 431 | Recepcao Capa Remessa (428). Unidades mesmo armazem (431). Fluxos comissionamento. |

---

## Mapa de Navegacao por Necessidade

### "Preciso configurar fretes para clientes"
→ **START**: `417-418-420-tabelas-frete.md`
- Entenda tipos tabelas (Combinada, Percentual, Faixa Peso, Rota)
- Aprenda adicionais (GRIS, TDE, TRT, TAR, pedagio)
- Veja prioridades e integracao

### "Preciso configurar parcerias/subcontratacao"
→ **START**: `408-comissao-unidades.md`
- Cadastro tabelas comissao
- Expedicao/Recepcao/Transbordo
- Formas credito CCF (Mapa/Fatura/Capa)
- Parcerias SSW vs nao-SSW

### "Preciso configurar vendedores"
→ **START**: `415-gerenciamento-vendedores.md`
- Cadastro vendedores e vinculos
- Comissoes (conquista/manutencao/% DESC NTC)
- Metas: `397-metas-clientes-alvo.md`

### "Preciso configurar servicos adicionais"
→ **START**: `423-parametros-comerciais-cliente.md`
- Reentrega/Devolucao/Recoleta
- Armazenagem
- Servicos complementares
- Tabelas CTRC Complementar

### "Preciso entender comprovantes e arquivamento"
→ **START**: `398-escanear-comprovantes-entregas.md`
→ NEXT: `OPCOES-COMPLEMENTARES.md` (opcao 428)

---

## Opcoes por Categoria

### Precificacao
- **417**: Tabela Combinada (peso + valor)
- **418**: Tabela Percentual (desconto/acrescimo NTC)
- **420**: Tabela Faixa Peso
- **427**: Tabela Rota especifica
- **923**: Tabela NTC (referencia)
- **423**: Parametros cliente (servicos)

### Comissionamento
- **408**: Comissao unidades (parcerias)
- **415**: Vendedores
- **397**: Metas e alvos
- **067**: Supervisao/Suporte (referenciado em 415)

### Operacoes Parceria
- **428**: Recepcao Capa Remessa
- **607**: Conferencia fatura subcontratado (ref em 408)
- **486**: Conta Corrente Fornecedor (ref em 408/428)

### Parametros e Configuracoes
- **422**: Local entrega subcontratados
- **423**: Parametros comerciais cliente
- **431**: Unidades mesmo armazem
- **401**: Cadastro unidades (ref geral)
- **483**: Cadastro clientes (ref geral)

### Comprovantes
- **398**: Escanear comprovantes
- **428**: Recepcao capa remessa
- **040**: Arquivamento fisico (ref em 398)

---

## Integracao com Outros Modulos

### Financeiro
- **CCF** (opcao 486): credito comissoes parcerias/agregados
- **Contas Pagar** (opcao 475): acerto saldos CCF
- **Faturamento** (opcao 436): cobranca cliente

### Operacional
- **Emissao CTRC** (004/005/006): aplica tabelas frete
- **Cotacao** (002): usa tabelas para simular
- **Romaneio** (035): considera unidades mesmo armazem
- **Manifestos** (020/025): comissao transbordo

### Cadastros
- **Unidades** (401): origem/destino, parcerias
- **Clientes** (483): tabelas, parametros, TDE/TDC
- **Cidades** (402): TDA, pedagio, prazos
- **Rotas** (403): distancias, pedagios

### Relatorios
- **056**: Relatorios gerenciais (vendedores, comissoes, resultados)
- **300**: Relatorios pessoais vendedor
- **101**: Resultado CTRC (tabela usada, comissoes)
- **392**: Composicao frete (detalhamento)

---

## Opcoes Nao Documentadas (Arquivos Nao Disponiveis)

- **390**: Referenciada como PGR (Plano Gerenciamento Risco) em 407
- **409**: Remuneracao veiculos (referencias indiretas em 075/076)
- **433**: [Consulta/Relatorio]
- **435**: [Consulta/Relatorio]
- **469**: [Impressao/Relatorio - possivelmente relacionado a 468]
- **518**: [Especifico]

**Nota**: Para estas opcoes, consultar ajuda nativa do SSW ou solicitar documentacao adicional.

---

## Glossario Rapido

- **CTRC**: Conhecimento Transporte Rodoviario Carga
- **DACTE**: Documento Auxiliar CT-e
- **CCF**: Conta Corrente Fornecedor
- **NTC**: Tabela generica referencia (923)
- **TDE**: Taxa Dificil Entrega
- **TDC**: Taxa Dificil Coleta
- **TRT**: Taxa Restricao Transito
- **TAR**: Taxa Area Risco
- **TDA**: Taxa Dificil Acesso
- **GRIS**: Gerenciamento Risco
- **FOB Dirigido**: Remetente escolhe transportadora
- **Subcontrato**: Documento fiscal parceria
- **Redespacho**: Transferencia outra transportadora
- **OS**: Ordem Servico (remuneracao agregado)
- **CTRB**: Contrato Transporte Rodoviario Bens
- **RPA**: Recibo Pagamento Autonomo

---

## Proximos Passos

### Para desenvolvedores integrando com SSW:
1. Ler `417-418-420-tabelas-frete.md` para entender precificacao
2. Ler `408-comissao-unidades.md` para entender parcerias
3. Consultar INDEX.md principal (`.claude/references/ssw/INDEX.md`) para visao geral sistema

### Para analistas de negocio:
1. Ler `415-gerenciamento-vendedores.md` para gestao comercial
2. Ler `397-metas-clientes-alvo.md` para acompanhamento performance
3. Ler `423-parametros-comerciais-cliente.md` para servicos adicionais

### Para administradores sistema:
1. Ler `408-comissao-unidades.md` para configurar parcerias
2. Ler `OPCOES-COMPLEMENTARES.md` para fluxos operacionais
3. Ler documentacao infraestrutura (INDEX.md principal)
