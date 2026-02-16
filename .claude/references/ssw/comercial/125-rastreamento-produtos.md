# Opção 125 — Rastreamento de Produtos

> **Módulo**: Comercial
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Rastreia produtos específicos constantes da DANFE desde a coleta até a entrega, exibindo histórico de ocorrências em ordem cronológica na tela.

## Quando Usar
- Cliente ou transportadora precisa localizar produto específico dentro de uma NF-e
- Necessidade de rastreamento detalhado de item individual (não apenas do CTRC completo)
- Acompanhamento de produto de alto valor ou sensível
- Auditoria de movimentação de produto específico desde a coleta

## Pré-requisitos
- **DANFE capturada**: Produto deve estar em DANFE capturada pelo SSWMobile na coleta
- **Opção 101**: Consulta de CTRCs (integração para detalhes do CTRC)
- **SSWMobile**: Aplicativo para captura de DANFEs e localização
- **www.ssw.inf.br**: Portal web também permite rastreamento

## Campos / Interface

### Tela Inicial
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Período de emissão | Sim | Período de emissão da NF-e (máximo 10 dias) |
| CNPJ remetente | Condicional | CNPJ do remetente (obrigatório se CNPJ destinatário não informado) |
| CNPJ destinatário | Condicional | CNPJ do destinatário (obrigatório se CNPJ remetente não informado) |
| Parte do nome do produto | Sim | Parte do nome do produto na DANFE (mínimo 5 caracteres) |

### Tela de Escolha do Produto
| Campo | Descrição |
|-------|-----------|
| Remetente | Nome/CNPJ do remetente |
| Destinatário | Nome/CNPJ do destinatário |
| NF-e | Série e número da NF-e |
| Emissão | Data de emissão da NF-e |
| Código | Código do produto constante da DANFE |
| Produto | Descrição do produto constante da DANFE |

### Tela de Rastreamento
| Campo | Descrição |
|-------|-----------|
| Remetente | Nome/CNPJ do remetente |
| Destinatário | Nome/CNPJ do destinatário |
| NF-e | Link para imprimir a DANFE |
| CTRC | Link para consulta detalhada (opção 101) |
| Localização atual | Localização recebida do satélite ou SSWMobile |
| Histórico de ocorrências | Ocorrências da coleta e CTRC em ordem cronológica |

## Fluxo de Uso
1. Aguardar captura da DANFE pelo SSWMobile na coleta (pré-requisito)
2. Acessar opção 125
3. Informar período de emissão (máximo 10 dias)
4. Informar pelo menos um CNPJ (remetente ou destinatário)
5. Informar parte do nome do produto (mínimo 5 caracteres)
6. Clicar para buscar → sistema exibe lista de produtos correspondentes
7. Na tela de escolha, revisar lista de produtos encontrados:
   - Verificar remetente, destinatário, NF-e, emissão
   - Conferir código e descrição do produto
8. Selecionar produto desejado
9. Na tela de rastreamento, visualizar:
   - Dados de remetente e destinatário
   - Link para DANFE (impressão)
   - Link para CTRC (opção 101)
   - Localização atual (satélite/SSWMobile)
   - Histórico completo de ocorrências em ordem cronológica

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 101 | Consulta detalhada do CTRC vinculado ao produto |
| SSWMobile | Captura de DANFEs na coleta (habilita rastreamento) |
| www.ssw.inf.br | Portal web alternativo para rastreamento |

## Observações e Gotchas
- **Disponibilidade**: Rastreamento só é possível após captura da DANFE pelo SSWMobile na coleta
- **Período máximo**: Busca limitada a 10 dias de emissão da NF-e
- **CNPJ obrigatório**: Pelo menos um CNPJ (remetente ou destinatário) deve ser informado
- **Busca por nome**: Parte do nome do produto requer mínimo de 5 caracteres
- **Granularidade**: Diferente da opção 101 (CTRC completo), esta opção rastreia produto individual dentro da NF-e
- **Ordem cronológica**: Ocorrências são exibidas em sequência temporal (coleta → entrega)
- **Localização em tempo real**: Integração com satélite e SSWMobile para posição atual
- **Acesso web**: Cliente pode usar www.ssw.inf.br para rastreamento sem acesso ao SSW
- **Link para DANFE**: Permite impressão da Nota Fiscal diretamente da tela de rastreamento
- **Link para CTRC**: Acesso direto à consulta completa do CT-e (opção 101) para informações adicionais
