# Opção 087 — Apreensão Fiscal de Mercadorias (TAD)

> **Módulo**: Operacional — Controle Fiscal
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Controla apreensões de mercadorias devido a pendências fiscais, registrando TAD (Termo de Apreensão e Depósito) e liberações após regularização.

## Quando Usar
- Mercadoria retida pela fiscalização devido a pendências fiscais
- Registrar TAD emitido pela fiscalização
- Liberar mercadoria após resolução de pendências fiscais
- Consultar TADs cadastrados

## Pré-requisitos
- Ocorrências SSW cadastradas na opção 405:
  - **56 — MERCAD RETIDA PELA FISCALIZACAO** (tipo pendência do cliente)
  - **58 — MERCAD LIBERADA PELA FISCALIZACAO** (tipo informativo)
- CTRCs retidos pela fiscalização

## Campos / Interface — Tela Inicial
| Campo | Descrição |
|-------|-----------|
| CADASTRAR/ALTERAR TAD | Informar UF emitente e número da TAD, tela seguinte permite cadastrar CTRCs e impostos devidos |
| LIBERAR/CONSULTAR TAD | Liberação da TAD cadastrada, elimina pendência fiscal, permite consulta |
| LIBERAR/CONSULTAR Nº Controle | Liberação e consulta usando Número de Controle da TAD |
| RELATÓRIOS | Relaciona todas as TADs cadastradas |

## Campos / Interface — Tela Principal
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Emissão | Sim | Data de emissão da TAD |
| Nº Controle (opc) | Não | Número de controle da TAD com dígito verificador |
| Inform complementares | Não | Informações complementares da TAD |

### Identificação dos CTRCs
Escolher UMA das formas:
- **Série e nº CTRC (com DV)**
- OU **Nota Fiscal (série opc/número) + CNPJ Remetente**
- OU **chave DACTE**

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| ICMS a recolher | Sim | Valor do ICMS devido por CTRC |

## Fluxo de Uso
### Cadastramento TAD
1. Fiscalização apreende mercadoria e emite TAD
2. Usuário acessa opção 087 → CADASTRAR/ALTERAR TAD
3. Informa UF emitente e número da TAD
4. Cadastra CTRCs apreendidos e ICMS a recolher
5. Sistema grava ocorrência **56 — MERCAD RETIDA PELA FISCALIZACAO** no CTRC
6. Cliente é comunicado (opção 383)

### Liberação TAD
1. Pendências fiscais resolvidas
2. Usuário acessa opção 087 → LIBERAR/CONSULTAR TAD
3. Informa número da TAD ou Número de Controle
4. Sistema libera TAD e elimina pendência
5. Sistema grava ocorrência **58 — MERCAD LIBERADA PELA FISCALIZACAO** no CTRC
6. Cliente é comunicado (opção 383)
7. Operação do CTRC pode prosseguir

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 101 | Visualização de ocorrências gravadas no CTRC |
| 383 | Comunicação com cliente sobre retenção/liberação |
| 405 | Cadastro de ocorrências 56 (retenção) e 58 (liberação) |

## Observações e Gotchas
- **TAD**: Termo oficialmente usado em algumas UFs, mas utilizado genericamente no SSW para todas UFs
- **Ocorrências necessárias**: Códigos SSW 56 e 58 devem ter correspondentes da transportadora cadastrados (opção 405)
- **Liberação**: Permite prosseguimento da operação do CTRC
- **Relatórios**: Opção relaciona todas as TADs para acompanhamento
- **Consulta**: Possível por número da TAD ou Número de Controle
- **ICMS por CTRC**: Cada CTRC da TAD deve ter ICMS a recolher informado
