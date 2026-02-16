# Opção 616 — Envio Automático de EDIs Seguradora

> **Módulo**: EDI
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Parametriza a geração e envio automático de EDIs para seguradoras objetivando a averbação de mercadorias.

## Quando Usar
- Para configurar geração automática de arquivos de averbação para seguradoras
- Para definir periodicidade e forma de envio dos EDIs
- Para automatizar processo de averbação de mercadorias

## Pré-requisitos
- Ajuste de lay-out pela equipe SSW (programas que geram arquivos no formato da seguradora)
- CNPJ da seguradora cadastrado

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| CNPJ completo | Sim | CNPJ (14 dígitos) da seguradora |
| Periodicidade | Sim | Dias da semana OU dias do mês (apenas uma opção) |
| Nome do arquivo | Sim | Nome livre + data/hora + extensão |
| Emails | Sim | Emails destino separados por ponto-e-vírgula |
| Observações | Não | Instruções sobre geração e envio |
| Último envio | Informativo | Data do último envio de arquivo |

## Fluxo de Uso

### Configuração Inicial
1. Solicitar à equipe SSW ajuste do lay-out conforme especificação da seguradora
2. Acessar opção 616
3. Informar CNPJ completo da seguradora
4. Definir periodicidade de geração
5. Configurar nome do arquivo
6. Cadastrar emails destino
7. Incluir observações relevantes
8. Confirmar configuração

### Estabilização do Envio
1. Até verificar que arquivos estão sendo recepcionados, cadastrar email da transportadora também
2. Acompanhar opção 615 para verificar sucesso do processo
3. Após confirmar funcionamento, retirar email da transportadora do cadastro

### Operação
- Arquivos gerados e enviados automaticamente nas primeiras horas do dia seguinte
- Acompanhar diariamente situação via opção 615
- Arquivos não enviados devem ser processados manualmente

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 615 | Situação dos arquivos EDIs gerados/enviados automaticamente |
| 101 | Número do arquivo gravado em cada CTRC incluído na averbação |

## Observações e Gotchas

### Processo Completo
1. **Ajuste do lay-out**: Equipe SSW constrói programas conforme especificação da seguradora
2. **Parametrização**: Opção 616 define critérios de geração e envio por CNPJ
3. **Situação**: Opção 615 mostra arquivos gerados/enviados conforme parametrização

### Características Importantes
- **Horário de envio**: Primeiras horas do dia seguinte
- **Número do arquivo**: Sistema gera número sequencial incluído no nome do arquivo
- **Rastreamento**: Número gravado em cada CTRC (opção 101) incluído no arquivo de averbação
- **Periodicidade**: Apenas uma opção pode ser escolhida (dias da semana OU dias do mês)
- **Clientes sem email**: Efetuar download do arquivo e enviá-lo manualmente ao cliente
- **Estabilização**: Cadastrar email da transportadora até confirmar recepção pelo cliente
- **Acompanhamento diário**: Verificar opção 615 para garantir que processo está funcionando
- **Falhas de envio**: Arquivos que não puderam ser enviados devem ser processados manualmente
