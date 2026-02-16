# Opção 405 — Cadastro de Ocorrências

> **Módulo**: Cadastros
> **Páginas de ajuda**: 10 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Cadastra tabela de ocorrências operacionais da transportadora utilizadas em transferências, entregas e operações pelo SSWMobile. As ocorrências são trocadas entre transportadoras usuárias SSW e clientes (EDI) através do **Código SSW**.

## Quando Usar
- Cadastrar novas ocorrências operacionais
- Vincular ocorrências da transportadora aos códigos SSW padrão
- Configurar ocorrências que pagam comissão de recepção
- Definir ocorrências que remuneram agregados
- Configurar ocorrências que geram CTRCs complementares (reentrega, estadia, etc.)
- Habilitar ocorrências para uso no SSWMobile
- Configurar tabelas de conversão para EDI de clientes/parceiros
- Definir ocorrências finalizadoras (mercadoria perdida/avariada)

## Pré-requisitos
- Nenhum pré-requisito obrigatório
- Recomendado: entender fluxo operacional antes de criar novas ocorrências

## Campos / Interface

### Tela Principal

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Código | Sim | Código da ocorrência (usar 01 para Entrega Realizada) |
| Código SSW | Não | Código que faz intermediação com outras transportadoras SSW e clientes EDI. Vinculo um-a-um |
| Descrição | Sim | Texto simples, claro, objetivo e autoexplicativo (usado por conferentes) |
| Tipo | Sim | E=Entrega, B=Baixa, P=Pendência transportadora, C=Pendência cliente, S=Pendência solucionada, R=Pré-entrega, I=Informativo |
| Processo | Sim | Coleta, operacional, entrega, reentrega, devolução, agendamento, finalizadora, baixa, indenização, geral |
| Ativo | Sim | X=ocorrência ativa e utilizável |
| Impede carregamento no SSWBAR | Não | CTRCs com esta ocorrência não podem ter volumes carregados no SSWBAR |
| Paga Comissão de Recepção | Não | X=comissão de agenciamento de recepção deve ser paga ao parceiro que efetua entrega |
| Paga Agregado | Não | X=agregado de entrega deve ser remunerado (opção 409) |
| Reentrega | Não | X=deve emitir CTRC complementar de reentrega (opção 016). Emissão automática via opção 423 |
| Estadia | Não | X=emite CTRC complementar de estadia automaticamente se ativado na opção 903 e cliente tiver tabela (opção 423) |
| Armazenagem | Não | X=inicia período de contagem para cobrança de armazenagem (opções 199 e 136) se cliente tiver tabela (opção 423) |
| Informa cliente | Não | X=enviada automaticamente via e-mail ao cliente e disponível no site de rastreamento |
| Unidade origem | Não | X=unidade origem do CTRC (emissora) é responsável por instruir resolução via opção 108 |
| Unidade anterior | Não | X=unidade anterior (carregamento do Manifesto) é responsável por instruir resolução via opção 108. Não pode ser marcada com unidade origem |
| SSWMobile | Não | X=ocorrência disponível no SSWMobile. Opção 903/Operação define se retira CTRC do Romaneio |
| Grupo de usuários (opc) | Não | Restringe uso da ocorrência a grupos específicos (opção 918). Evitar restrições demasiadas |

## Fluxo de Uso

### Cadastrar Nova Ocorrência
1. Acessar opção 405
2. Clicar em "incluir"
3. Informar código (numérico)
4. Definir descrição clara e objetiva
5. Vincular a Código SSW (se aplicável)
6. Selecionar tipo (define características da ocorrência)
7. Escolher processo
8. Marcar checkboxes conforme necessidade operacional
9. Salvar ocorrência

### Vincular Código SSW
**Regras para vínculo**:
- Tipo da ocorrência da transportadora deve ser o mesmo do Código SSW
- Para cada Código SSW apenas um código da transportadora pode ser vinculado
- Vinculo um-a-um é necessário para troca de ocorrências entre parceiros

### Configurar Tabela EDI - Recebe (Opção 927)
1. Informar CNPJ do cliente/parceiro
2. Para cada ocorrência da transportadora (opção 405), informar até 5 códigos correspondentes do cliente/parceiro
3. Código do cliente deve ter mesma quantidade e tipo de caracteres definido pelo cliente
4. Link REPLICAR PARA CNPJS permite copiar tabela para outros CNPJs

### Configurar Tabela EDI - Envia (Opção 908)
**Para CTRC**:
- Equipe SSW configura tabela DE-PARA
- Transportadora configura: se ENVIA a ocorrência e se é FINALIZADORA
- Ocorrências vinculadas a códigos SSW são convertidas automaticamente

**Para COLETA**:
- Transportadora configura tabela diretamente
- Define códigos para operação NORMAL e REVERSA

### Atribuir Ocorrências a CTRCs
**Opção 033** (Transferências):
- Registra ocorrências durante transferências

**Opção 038** (Entregas):
- Atribui ocorrências de entrega (tipo ENTREGA só pode ser atribuída pela unidade destino)

**Opção 101**:
- Permite atribuir ocorrências manualmente
- Permite incluir instruções (texto livre sem código)
- Permite segregar CTRC (S=indisponível para operação até opção 091)

**SSWMobile**:
- Motorista registra ocorrências pelo smartphone
- Data/hora do smartphone são consideradas
- Localização GPS é gravada

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 007 | Emissão de CTRCs (recebe ocorrências) |
| 016 | Emissão de CTRC complementar de reentrega |
| 033 | Ocorrências em transferências |
| 038 | Ocorrências em entregas |
| 051 | Relatório de CTRCs com reentrega obrigatória |
| 089 | Paletização (gera ocorrência SSW 89) |
| 091 | Retirada de segregação |
| 099 | CTRC complementar de estadia |
| 101 | Consulta e atribuição de ocorrências |
| 108 | Instrução de resolução de ocorrências |
| 136 | Cobrança de armazenagem |
| 138 | Estorno de última ocorrência |
| 199 | Cálculo de armazenagem |
| 201 | Situação do CTRC complementar/reembolso |
| 205 | Configurações para CTRC complementar/reembolso |
| 233 | Atribuição de ocorrências em lote |
| 398 | SSWScan (anexa comprovante) |
| 409 | Tabela de remuneração de veículos (usa "Paga Agregado") |
| 414 | Encerramento de parceria (usa "Paga Comissão") |
| 423 | Tabelas de cobrança complementares (reentrega, estadia, armazenagem) |
| 600 | Importação de arquivos EDI |
| 602 | Diretório de arquivos EDIs processados |
| 603 | Configuração de recebimento automático de EDI |
| 903 | Configuração geral (comportamento SSWMobile, CTRCs complementares) |
| 908 | Tabela de ocorrências EDI - Envia |
| 918 | Grupos de usuários (restrição de uso) |
| 927 | Tabela de ocorrências EDI - Recebe |
| 943 | Liberação de ocorrências finalizadoras para cliente |

## Observações e Gotchas

### Códigos SSW com Características Especiais

| Código SSW | Descrição |
|------------|-----------|
| **01** | Mercadoria entregue. Código universal em todas as transportadoras SSW |
| **03** | Mercadoria devolvida ao remetente. Envia evento de insucesso ao SEFAZ (Ajuste SINIEF 9/2007) |
| **19** | Anexado comprovante de entrega complementar (nova imagem obtida via SSWScan, SSWMobile, etc.) |
| **31, 32, 33** | Tentativas de entrega (1ª, 2ª, 3ª). Só aceitas na sequência |
| **38** | Recebedor recusa/não pode receber. Envia evento de insucesso ao SEFAZ |
| **61** | Mercadoria confiscada. Desfaz unitização, libera CTRCs para operação individual |
| **70** | Pesagem/cubagem efetuada. Altera peso/volume para recálculo de frete (opção 007) |
| **80** | Documento de transporte emitido. Não grava no CTRC da subcontratante quando atribuída pela subcontratada |
| **83** | Chegada em unidade de transbordo. Registrada automaticamente na opção 030 |
| **84** | Chegada em unidade de entrega. Registrada automaticamente na opção 030 |
| **88** | Resgate de mercadoria. Impede carregamento em Romaneio e recebimento de ocorrência ENTREGA |
| **89** | Paletização efetuada. Útil para identificação de cobrança não realizada (opção 056 - Relatório 130) |
| **95** | Estou chegando. Registrada via SSWMobile, calcula horário provável de entrega usando Google |

### Imagem do Comprovante
- Associada via opção 033, 101 ou SSWMobile
- **Exclusão**: só pode excluir quem inseriu e se for a última ocorrência do CTRC (master quebra regra)
- **Comprovante de Entrega**: imagem da última ocorrência tipo ENTREGA torna-se o comprovante
- **Imagem complementar**: nova imagem em CTRC que já tem entrega é gravada com código 19
- **Formatos aceitos**: JPEG, WEBP, PNG, TIFF, TIF, JP2, J2K, HEIC, HEIF, HEVC, PDF (convertidos para JPEG, máx 200KB)

### Ocorrências em CTRCs Unitizados
- Todos os CTRCs unitizados por NR Unitizador recebem a mesma ocorrência atribuída a um dos CTRCs
- Consultar ajuda da opção 004/Marketplace para mais detalhes

### Ocorrências em Lotes
- Opção 233 permite atribuir em lotes (filtros ou arquivo)
- Opção muito crítica - precisa ser liberada pela opção 918 (usuário master)

### Ocorrências Gravadas como Instruções
- SSWMobile e SSWScan registram com data/hora do local
- Gravadas como instruções (sem código) se:
  - Data diferente da data do servidor SSW
  - Data igual mas diferença de horário > 2 horas
- Ocorrência de entrega (01) não sofre validação - sempre atribui código
- Ocorrência com data/hora anterior à última que informa cliente é gravada como instrução

### Ocorrências Finalizadoras
- Tipo que indica mercadoria perdida/avariada
- Não são enviadas ao cliente via EDI automaticamente (evitar duplicação de mercadoria)
- Opção 943 deve ser usada para liberar envio ao cliente
- Sugestões de códigos SSW finalizadores:
  - 20: Cliente alega falta de mercadoria
  - 23: Cliente alega mercadoria avariada
  - 50: Falta de mercadoria
  - 53: Mercadoria avariada
  - 54: Embalagem avariada
  - 55: Carga roubada ou sinistrada

### Estorno de Ocorrência
- Última ocorrência tipo BAIXA/ENTREGA ou resgate (SSW 88) pode ser estornada pela opção 138
- Apenas a última pode ser estornada

### Evento de Insucesso no CT-e
- Ocorrências SSW 03 e 38 gravam automaticamente evento de insucesso no SEFAZ
- Conforme Ajuste SINIEF 9/2007, inciso XXIII do § 1º da cláusula décima oitava-A

### Configuração de CTRCs Complementares Automáticos
**Opção 205** configura identificação e cobrança automática:
- **Serviços**: Recoleta, Reentrega, Devolução, Agendamento, Estadia, Paletização, Armazenagem, Reembolso
- **Identificação**: Através de ocorrências cadastradas (opção 405)
- **Verificação**: Diária ou semanal
- **Autorização**: Pode exigir autorização do cliente via e-mail antes da cobrança
- **Opção 201**: Verifica e atualiza situação do reembolso

### Rastreamento e E-mail
- Ocorrências com "Informa cliente=X" são enviadas automaticamente por e-mail
- Disponíveis no site de rastreamento www.ssw.inf.br
- Opção 383 configura parâmetros de rastreamento

### Integração EDI
- Arquivos CSV de ocorrências podem ser importados manualmente (opção 600)
- Recebimento automático configurado pela opção 603 (FTP/SFTP)
- Opção 101/Arquivos EDI mostra status dos recebimentos
- Opção 602 relaciona arquivos EDIs processados no período

### Remuneração de Agregados
- Ocorrência marca "Paga Agregado=X" é considerada no cálculo (opção 076)
- Ocorrências sem esta marcação são consideradas insucesso (dedução na remuneração)
- Opção 409 permite configurar valores diferenciados por ocorrência
- Redução por insucesso pode ser configurada na tabela de remuneração

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-D05](../pops/POP-D05-baixa-entrega.md) | Baixa entrega |
| [POP-D06](../pops/POP-D06-registrar-ocorrencias.md) | Registrar ocorrencias |
