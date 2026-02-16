# Opção 117 — Monitoração dos Embarcadores

> **Módulo**: Comercial/Integração
> **Referência interna**: Opção 907
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função

Monitoração em tempo real dos ambientes dos embarcadores, exibindo status de conexões e transações dos últimos logs de 24 horas. Sistema de cores e nomenclatura padronizada facilitam identificação rápida de problemas.

## Quando Usar

- Monitorar saúde das integrações com embarcadores
- Identificar rapidamente problemas de conexão ou transação
- Diagnosticar falhas em Webservices, FTP, SFTP, E-mail ou AWS S3
- Analisar quantidade de erros por tipo de problema

## Campos / Interface

### Nomenclatura das Células

Identificação de 11 caracteres:

**Primeira letra** indica o meio de envio:
- **W** - Webservice
- **F** - FTP
- **S** - SFTP
- **E** - E-mail
- **A** - AWS S3 (Amazon)

**Outros 10 caracteres**: Referenciam o programa/cliente

### Sistema de Cores

- **SEM COR**: Sem erros nas últimas 24 horas
- **AMARELO**: Conexão estabelecida e transação com sucesso, mas houve crítica ao gravar informação (ocorrência não existe, nota não localizada, documento já baixado). Número indica quantidade de erros nas últimas 24h.
- **LARANJA**: Conexão estabelecida mas transação apresentou erro. Divergência nos parâmetros de segurança (usuário/senha inválidos, token inválido, bloqueio de IP). Número indica quantidade de embarcadores com erros (última ocorrência) nas últimas 24h.
- **VERMELHO**: Conexão não estabelecida (erro HTTP 500). Número indica quantidade de embarcadores com conexões não estabelecidas (última ocorrência) nas últimas 24h.

### Interação

- **Número na célula**: Quantidade de erros detectados
- **Clique na célula**: Abre relatório analítico detalhado dos problemas

## Integração com Outras Opções

- Logs considerados são das últimas 24 horas de todas as integrações ativas

## Observações e Gotchas

### Interpretação das Cores

- **Amarelo** não significa falha total - a conexão funciona, mas há críticas de dados (ex: registros duplicados, referências inválidas)
- **Laranja** indica problema de autenticação/autorização - verificar credenciais
- **Vermelho** é o mais crítico - sem comunicação alguma com o embarcador

### Diagnóstico Rápido

A primeira letra da célula permite identificar rapidamente qual canal de integração apresenta problemas (Webservice, FTP, etc.), acelerando troubleshooting.

### Período de Análise

O sistema considera apenas as últimas 24 horas, oferecendo visão de curto prazo. Para análises históricas, outros relatórios devem ser consultados.

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-D02](../pops/POP-D02-romaneio-entregas.md) | Romaneio entregas |
| [POP-D03](../pops/POP-D03-manifesto-mdfe.md) | Manifesto mdfe |
| [POP-G02](../pops/POP-G02-checklist-gerenciadora-risco.md) | Checklist gerenciadora risco |
