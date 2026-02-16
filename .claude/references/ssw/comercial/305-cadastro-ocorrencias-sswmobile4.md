# Opcao 305 — Cadastro de Ocorrencias do SSWMobile 4

> **Modulo**: Comercial
> **Paginas de ajuda**: 2 paginas consolidadas (opcoes 305 e 890)
> **Atualizado em**: 2026-02-14

## Funcao
Cadastra ocorrencias auxiliares a serem utilizadas pelo SSWMobile 4 (aplicativo mobile integrado com SAC), que posteriormente sao vinculadas as ocorrencias principais do SSW via opcao 890.

## Quando Usar
- Configurar ocorrencias de entrega para uso no aplicativo SSWMobile 4
- Criar codigos auxiliares simplificados para motoristas/entregadores registrarem no app mobile
- Integrar SSWMobile 4 com sistema principal de ocorrencias do SSW

## Pre-requisitos
- SSWMobile 4 em uso pela transportadora
- Ocorrencias principais cadastradas no SSW (opcao 405)
- Conhecimento de quais ocorrencias serao utilizadas no mobile

## Campos / Interface

### Opcao 305 (Cadastro de Ocorrencias Auxiliares)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Codigo | Sim | Codigo da ocorrencia de entrega a ser mostrado no SSWMobile 4 |
| Descricao | Sim | Descricao do codigo (texto exibido para motorista/entregador) |

### Opcao 890 (Vinculacao)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Cod Ocorrencia Auxiliar | Sim | Codigo cadastrado pela opcao 305 e utilizado pelo SSWMobile 4 |
| Cod Ocorrencia Principal | Sim | Ocorrencia da transportadora (opcao 405) correspondente a ocorrencia auxiliar |

## Fluxo de Uso
1. Cadastrar ocorrencias auxiliares na opcao 305 (codigos simples para uso no mobile)
2. Vincular cada ocorrencia auxiliar a uma ocorrencia principal do SSW via opcao 890
3. SSWMobile 4 passa a exibir apenas as ocorrencias auxiliares cadastradas
4. Motorista/entregador registra ocorrencia no SSWMobile 4
5. Sistema atualiza automaticamente a ocorrencia do CTRC com a ocorrencia principal correspondente

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 890 | Vinculacao de ocorrencias auxiliares (305) com ocorrencias principais (405) |
| 405 | Cadastro de ocorrencias principais do SSW (vinculadas as auxiliares via 890) |
| 519 | Tabela de ocorrencias do SSW usada diretamente na COLETA (nao usa ocorrencias auxiliares) |

## Observacoes e Gotchas
- **SOMENTE para entregas**: ocorrencias auxiliares (opcao 305 + 890) sao utilizadas APENAS na entrega. Na coleta utiliza-se diretamente a tabela de ocorrencias do SSW (opcao 519)
- **NAO retira CTRC do Romaneio**: ocorrencias auxiliares de entrega dadas no SSWMobile 4 NAO retiram o CTRC do romaneio
- **Baixa de entrega NAO permitida no mobile**: baixa de entrega NAO pode ser efetuada no SSWMobile 4. Esta baixa so pode ser feita pela Expedicao mediante apresentacao do Comprovante de Entregas
- **Dupla configuracao necessaria**: para funcionar, e preciso AMBOS:
  1. Cadastrar ocorrencia auxiliar (opcao 305)
  2. Vincular a ocorrencia principal (opcao 890)
- **Integracao com SAC**: SSWMobile 4 se integra com sistema SAC (Servico de Atendimento ao Cliente)
- **Outras versoes do SSWMobile**: existem outras versoes do aplicativo mobile (verificar documentacao especifica)
- **Atualizacao automatica**: ocorrencias registradas no SSWMobile 4 atualizam automaticamente as ocorrencias do CTRC no sistema principal
