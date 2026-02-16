# Opcao 180 — Observacoes das Tabelas de Fretes

> **Modulo**: Comercial
> **Paginas de ajuda**: 2 paginas consolidadas (referencias na opcao 419)
> **Atualizado em**: 2026-02-14

## Funcao
Cadastra observacoes genericas da transportadora a serem impressas em todas as Tabelas de Fretes enviadas aos clientes. Texto generico e combinado com observacoes especificas de cada cliente (cadastradas na opcao 419), formando a observacao completa das tabelas. Tambem permite configurar mensagens padroes nos e-mails que enviam as tabelas de fretes.

## Quando Usar
- Definir texto generico padrao da transportadora para todas as tabelas de frete
- Configurar mensagens padroes nos e-mails de envio de tabelas de frete
- Atualizar politicas gerais de cobranca, prazo, condicoes de pagamento
- Incluir disclaimers legais ou informacoes regulatorias comuns a todas as tabelas
- Padronizar comunicacao com clientes sobre tabelas de frete

## Pre-requisitos
- Acesso a opcao 180 (configuracao de observacoes genericas)
- Definicao de politicas de cobranca da transportadora
- Texto generico padrao preparado (formatacao clara e concisa)

## Campos / Interface

### Tela de Observacoes Genericas (Opcao 180)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Observacao da transportadora | Sim | Texto generico padrao da transportadora impresso em todas as tabelas de fretes de todos os clientes |
| Mensagens padroes nos e-mails | Nao | Mensagens padroes incluidas nos e-mails que enviam as tabelas de fretes aos clientes |

### Observacao do Cliente (Opcao 419)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Cliente | Sim | Identificacao do cliente dono das tabelas de fretes e desta observacao |
| Observacao do cliente | Nao | Texto com 3 linhas especifico do cliente (combinado com observacao da transportadora) |
| Observacao da transportadora | Informativo | Texto generico da transportadora cadastrado pela opcao 180 (nao pode ser alterado na opcao 419) |

## Composicao da Observacao Completa

### Estrutura
1. **Observacao do cliente** (3 linhas especificas, cadastradas na opcao 419)
2. **Observacao da transportadora** (texto generico padrao, cadastrado na opcao 180)

### Exemplo
```
[Observacao do cliente - 3 linhas]
Desconto de 10% valido ate 31/12/2026.
Frete minimo de R$ 50,00 por CTRC.
Tabela sujeita a reajuste mediante aviso previo de 30 dias.

[Observacao da transportadora]
Valores nao incluem ICMS. Cobranca de pedagio conforme tabela de rotas.
Prazo de pagamento: 15 dias apos emissao da fatura.
Tabela valida para cargas paletizadas e sem restricoes especiais.
Sujeito a alteracao sem aviso previo conforme variacao de custos operacionais.
```

## Fluxo de Uso

### Cadastrar Observacao Generica da Transportadora
1. Acessar opcao 180
2. Incluir ou editar texto generico padrao da transportadora
3. Incluir ou editar mensagens padroes nos e-mails
4. Salvar configuracao
5. Observacao sera aplicada automaticamente a todas as tabelas de fretes (impressas e enviadas por e-mail)

### Cadastrar Observacao Especifica do Cliente
1. Acessar opcao 419 (Tabela Desconto Sobre NTC)
2. Selecionar cliente pagador
3. Acessar link "Observacoes" no rodape
4. Incluir ou editar observacao especifica do cliente (ate 3 linhas)
5. Visualizar observacao completa (cliente + transportadora)
6. Salvar observacao

### Imprimir ou Enviar Tabela com Observacoes
1. Acessar opcao 419
2. Selecionar cliente pagador
3. Clicar em "Imprimir tabelas" OU "ENVIAR POR E-MAIL"
4. Tabela sera gerada com observacao completa (cliente + transportadora)
5. Se envio por e-mail, mensagem padrao cadastrada na opcao 180 sera incluida

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 419 | Tabela Desconto Sobre NTC (usa observacao generica da opcao 180 + observacao especifica do cliente) |
| 454 | Revalidacao de tabelas (preserva observacoes) |
| Impressao de tabelas | Inclui observacao completa no rodape da tabela impressa |
| Envio por e-mail | Inclui mensagem padrao e observacao completa no e-mail |

## Observacoes e Gotchas
- **Texto generico aplicado a TODAS as tabelas**: Observacao cadastrada na opcao 180 e impressa em todas as tabelas de fretes de todos os clientes — cuidado com informacoes especificas
- **Observacao do cliente e limitada a 3 linhas**: Observacao especifica do cliente (opcao 419) tem limite de 3 linhas — texto deve ser conciso
- **Observacao da transportadora NAO pode ser alterada na opcao 419**: Texto generico so pode ser editado na opcao 180 — na opcao 419 e apenas visualizado
- **Composicao automatica**: Sistema combina automaticamente observacao do cliente (topo) + observacao da transportadora (base)
- **Mensagens padroes nos e-mails**: Mensagens cadastradas na opcao 180 sao incluidas nos e-mails de envio de tabelas, alem da observacao completa
- **Impressao e e-mail usam mesma observacao**: Observacao completa e incluida tanto na impressao quanto no envio por e-mail (formatacao pode variar)
- **Revalidacao preserva observacoes**: Ao revalidar tabelas (opcao 454), observacoes sao preservadas (nao precisam ser recadastradas)
- **Atualizacao retroativa**: Alteracao na observacao generica da transportadora (opcao 180) afeta todas as tabelas (impressas ou enviadas) a partir da alteracao — tabelas ja enviadas nao sao atualizadas
- **Conteudo tipico da observacao generica**: Politicas de pagamento, exclusoes de cobranca (ex: ICMS), validade da tabela, condicoes especiais gerais, disclaimers legais
- **Conteudo tipico da observacao do cliente**: Descontos especificos, fretes minimos, prazos de validade personalizados, condicoes excepcionais acordadas
