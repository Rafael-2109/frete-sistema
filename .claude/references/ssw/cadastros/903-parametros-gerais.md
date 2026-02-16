# Opção 903 — Parâmetros Gerais do SSW

> **Módulo**: Cadastros / Sistema
> **Páginas de ajuda**: 31 páginas consolidadas
> **Atualizado em**: 2026-02-15

## Função

A opção 903 é o **coração do sistema SSW**, responsável por configurar todos os parâmetros gerais que controlam o comportamento da transportadora em diferentes módulos. É uma opção de configuração global dividida em múltiplas abas/sub-módulos, cada uma controlando aspectos específicos da operação.

## Estrutura de Sub-módulos

A opção 903 é dividida em várias seções acessadas por links/abas. As principais identificadas na documentação são:

### 1. Frete

Parâmetros relacionados ao cálculo e gestão de fretes.

| Parâmetro | Descrição | Valores/Configuração |
|-----------|-----------|----------------------|
| **Curva ABC de Clientes** | Define percentuais para classificação ABC de clientes | Primeiro caractere: volume faturamento mês passado<br>Segundo caractere: inadimplência atual |
| **Prazo de vencimento de tabelas** | Validade padrão das tabelas de frete | Data atualizada automaticamente quando tabela é reajustada (opção 913) |
| **Aprovação centralizada de tabelas** | Ativa processo de aprovação de tabelas pela opção 518 | **S** = Tabelas ficam em simulação até aprovação<br>**N** = Tabelas ativas imediatamente |
| **Cubagem padrão** | Densidade padrão quando cliente não tem cubagem específica | Sugestão: 300 Kg/m³ (configurável por cliente na opção 423) |
| **Texto padrão para impressão** | Observações impressas nas tabelas de frete | Até 3 linhas de 70 caracteres (opção 494) |

**Impactos:**
- Tabelas apagadas automaticamente mudam `Transportar = N` na opção 389 (Crédito)
- Curva ABC é usada em relatórios gerenciais (040, 153, 151)

---

### 2. Prazos

Controle de prazos de liquidação e inadimplência.

| Parâmetro | Descrição | Impacto |
|-----------|-----------|---------|
| **Dias para inadimplência** | Prazo após vencimento para considerar fatura inadimplente | Faturas vencidas além deste prazo mudam automaticamente `Transportar = N` (opção 389) |
| **Prazo adicional Entrega Difícil (geral)** | Dias úteis adicionais para CTRCs com Entrega Difícil | Pode ser sobrescrito por cliente específico na opção 698 |

**Prioridade de prazos Entrega Difícil:**
1. Prazo do destinatário (opção 698)
2. Prazo do remetente (opção 698)
3. Prazo do pagador (opção 698)
4. Prazo geral da transportadora (opção 903)

---

### 3. Crédito

Limites de crédito padrão baseados na classificação ABC.

| Parâmetro | Descrição |
|-----------|-----------|
| **Limite grupo A** | Valor máximo de CTRCs não liquidados para clientes classe A |
| **Limite grupo B** | Valor máximo de CTRCs não liquidados para clientes classe B |
| **Limite grupo C** | Valor máximo de CTRCs não liquidados para clientes classe C |

**Hierarquia de limites (opção 389):**
1. Limite do grupo (opção 583) — prevalece se cliente estiver em grupo
2. Limite da transportadora (opção 903) — usado se cliente não tiver grupo
3. Limite individual do cliente — sempre consultado

**Saldo = Limite − Tomado** (onde Tomado = CTRCs não liquidados)

---

### 4. Operação

Parâmetros operacionais diversos.

| Parâmetro | Descrição | Opções |
|-----------|-----------|--------|
| **Controle de conferentes** | Ativa cadastro de conferentes e rastreamento em ocorrências | **S**/**N** (opção 111 para cadastro) |
| **Cubagem obrigatória** | Exige login de conferente (opção 111) no campo APELIDO para opção 084 | **S**/**N** |
| **Controle de pallets** | Ativa estoque de pallets, gaiolas e chapas | **S**/**N** (relatório opção 058) |
| **Controle de gaiolas** | Ativa estoque de gaiolas | **S**/**N** (cadastro opção 021) |
| **Controle de chapas** | Ativa estoque de chapas | **S**/**N** |
| **Prazo adicional Entrega Difícil** | Dias úteis extras para CTRCs Entrega Difícil | Pode ser ZERO para cliente específico (opção 698) |
| **Ativar ESTOU CHEGANDO** | Habilita cálculo de horários de entrega em tempo real | **S**/**N** (requer opção 234 - Horários) |
| **Raio do local de entrega** | Distância (metros) para considerar ocorrência dentro do local | Sugestão: 100m (usado no relatório 087) |
| **Ordenar CTRCs no Romaneio** | Ordem de carregamento no Romaneio | **S** = Conforme digitação/captura<br>**N** = Ordem livre |

**Estou Chegando (opção 234):**
- Exige cadastro de horários por unidade: Início, Permanência no cliente, Almoço, Fim
- Pelo menos MTZ precisa ter horário de início cadastrado
- Desativar: apagar horários de todas unidades
- Ocorrência SSW 95 dispara quando previsão muda
- Horários diferenciados: dia útil, sábado, domingo, feriado

---

### 5. Outros

Parâmetros gerais diversos.

| Parâmetro | Descrição | Valores |
|-----------|-----------|---------|
| **Reter SEST/SENAT dos carreteiros** | Retenção 2,5% sobre 20% do CTRB (pessoa física) | **S**/**N** (opção 489) |
| **Reter Previdência Social dos carreteiros** | Retenção 11% sobre 30% do CTRB (pessoa jurídica) | **S**/**N** (opção 489) |
| **Aprovação centralizada de despesas** | Ativa aprovação de despesas pela opção 560 | **S**/**N** |
| **Aprovação de pedidos de compra** | Pedidos (opção 158) requerem aprovação (opção 169) antes envio | **S**/**N** |

**Processo de aprovação de despesas:**
1. Programação (opção 475 - Contas a Pagar)
2. Aprovação (opção 560)
3. Liquidação (opção 476)

---

### 6. PEF/CIOT

Configuração de Pagamento Eletrônico de Fretes e CIOT.

| Parâmetro | Descrição | Valores |
|-----------|-----------|---------|
| **Login CTF Ipiranga** | Credenciais para integração CTF | Login + Senha (opção 079) |
| **Senha CTF Ipiranga** | Senha de acesso ao CTF | Criptografada |
| **Valor CIOT bruto** | Define se CIOT usa valor bruto ou líquido | **S** = VALOR A PAGAR (opção 072)<br>**N** = TOTAL CTRB (compensa CCF)<br>Não disponível se PEF integrado ao CIOT |
| **PEF parcela adiantamento** | Liquidação automática ou manual do adiantamento CTRB com CIOT/PEF | **M** = Manual (opção 476)<br>**A** = Automática (na emissão CTRB)<br>Apenas **A** para: Repom, e-Frete, Ambipar, Truckpad |

**Tabela de integrações (sub-tela):**

| Coluna | Descrição |
|--------|-----------|
| **Integração** | ID da integração (ex: CTF, Repom, e-Frete) |
| **Programa** | Nome do programa de integração |
| **Descrição** | Descrição da integração |
| **Prioritário** | Integração prioritária quando múltiplas disponíveis (opção 035) |
| **Configurações** | Login, senha, conta bancário (opção 904), dados bancários (opção 027) |
| **Ativo** | **S** = Ativa integração / **N** = Inativa |

**Observação:** PEFs da transportadora são definidos aqui (opção 903). PEFs dos favorecidos são cadastrados na opção 227 (cartões).

---

### 7. Gerenciamento de Risco

Configuração de gerenciadora de risco e iscas.

| Parâmetro | Descrição |
|-----------|-----------|
| **Gerenciadora padrão** | Empresa gerenciadora de risco contratada |
| **Provedor satélite** | Provedor de rastreamento via satélite (usado em jornada de trabalho opção 171) |

**Processo de iscas (opção 391):**
1. Cadastro de iscas na opção 391 (número, identificação, localização inicial)
2. Cadastro de regras de gerenciamento (opção 390)
3. Informar iscas no Manifesto (opção 020 - até 2 iscas por viagem)
4. Localização atualizada automaticamente:
   - Emissão Manifesto → isca vai para Manifesto/CTRC/NR
   - Cancelamento Manifesto (opção 024) → isca volta para unidade
   - Controle de iscas (opção 030) → isca vai para unidade de chegada

**Restrições:**
- Localização só rastreada em transferência (não em Romaneio ou coleta)
- Acesso à opção 391 deve ser restrito

---

### 8. SMS

Configuração de provedor de SMS.

| Parâmetro | Descrição |
|-----------|-----------|
| **Provedor SMS** | Empresa provedora do serviço SMS |
| **Credenciais** | Login/senha para API do provedor |

**Processo de envio (opção 143):**
- Motorista precisa ter celular cadastrado (opção 028)
- Motorista vinculado ao veículo (opção 026)
- Mensagem até 140 caracteres
- Disparo também via opção 038 (Romaneio) e opção 003 (Coleta)
- Ocorrência SSW 95 pode disparar SMS/WhatsApp (integração com Estou Chegando)

---

### 9. Site, e-mails e telefone

Informações de contato da transportadora.

| Campo | Uso |
|-------|-----|
| **Site** | URL exibida em anúncios (opção 175) e comunicações |
| **E-mails** | Contatos para clientes e fornecedores |
| **Telefones** | Centrais de atendimento |

---

### 10. Envio de pré-CTRCs ao SEFAZ

Controle de aprovação automática ou manual de CTRCs.

| Parâmetro | Descrição | Valores |
|-----------|-----------|---------|
| **Envio automático a cada 1 minuto** | Envia pré-CTRCs ao SEFAZ sem intervenção | **S** = Automático<br>**N** = Manual (opção 007) |
| **Transportadora emite > 100k CTRCs/mês** | Ativa envio sem impressão prévia | **S**/**N** |
| **Enviar sem conferência manual** | Permite envio antes da conferência da mercadoria | **S** = Envia direto<br>**N** = Retém até conferência (opção 284) |

**Conferência manual (quando ativada com N):**
1. Opção 381: definir clientes que exigem conferência
2. Emissão pré-CTRC (opções 004, 005, 006)
3. Conferente informa OK (opção 284)
4. Envio ao SEFAZ (opção 007)

**Recálculo antes do SEFAZ (opção 007):**
- Todos pré-CTRCs têm frete recalculado considerando: tabela atual, peso, cubagem
- **Não sofrem recálculo:** Complementares (016, 015, 089), Informados (004), Substitutos (520), Somente efeito frete, Reenvios

**Pesagem/cubagem parcial:**
- Se volumes faltantes: média dos já pesados/cubados é aplicada
- Permitido para usuário com permissão "informa frete" (opção 925)

---

### 11. Autorização e operação com pré-CTRCs

Controle de impressão e uso de pré-CTRCs na operação.

| Parâmetro | Descrição |
|-----------|-----------|
| **Permitir pré-CTRCs em pallets/gaiolas** | Habilita operação com documentos não autorizados | **S**/**N** |

**Processo sem papel:**
- Configurável para operar sem impressão de DACTE
- Link "Não imprime meus/todos" na opção 007 libera para carregamento (opção 020)
- Faturas FOB podem ser impressas junto com DACTEs na expedição (opção 007)

---

### 12. Certificados Digitais

Instalação de certificados A1 para emissão fiscal.

**Tela de cadastro:**

| Campo | Descrição |
|-------|-----------|
| **CNPJ** | CNPJ da unidade emissora (opção 401) |
| **Arquivo .PFX** | Arquivo do certificado enviado pela certificadora |
| **Senha** | Fornecida pela certificadora |
| **RNTRC** | Registro Nacional de Transportadores |

**Observações:**
- Cada raiz de CNPJ precisa de certificado próprio
- Todos CNPJs da mesma raiz usam o mesmo certificado
- Tipo aceito: **A1** (arquivo PFX + senha)
- Alertas de vencimento: opções 007, 551, 707
- Certificados vencidos bloqueiam emissão fiscal

---

### 13. Emissão de CTRCs

Horários de busca de XMLs nos Portais NF-e/CT-e.

| Parâmetro | Descrição |
|-----------|-----------|
| **Não buscar XMLs no período** | Intervalo em que SSW não acessa Portais | **00:00 a 06:00** (madrugada)<br>Mínimo: 1 hora<br>**06:00 a 00:00**: sem interrupção |

**Funcionamento:**
- Busca contínua automática de XMLs em que CNPJ é transportadora ou pagadora
- XMLs transportadora → emissão CTRCs (opções 004, 005, 006)
- XMLs compradora → Contas a Pagar (opção 475)
- Guarda: 60 dias (CTRCs) / 5 anos (Contas a Pagar)
- Atualização automática de cadastros (IE, SN, CEP) via XML do Portal

**Uso Indevido:**
- Evitar conflito com sistemas fiscais/contábeis externos
- Alternativa: sistema externo busca direto no Portal (SSW fica inativo no horário)
- Download XMLs Contas a Pagar: opção 595 (ou via EDI ssw2991)

**Interrupção automática:**
- Domínios sem IE ativo (opção 920) não fazem busca (exceto se em implantação)

---

## Integração com Outras Opções

| Opção | Relação | Dependência |
|-------|---------|-------------|
| **389** | Crédito do cliente | Limites ABC (903/Crédito), bloqueios por inadimplência (903/Prazos) |
| **390** | Regras gerenciamento risco | Gerenciadora padrão (903/Gerenciamento Risco) |
| **391** | Cadastro de iscas | Ativação do processo (903/Gerenciamento Risco) |
| **417, 418** | Tabelas de frete | Aprovação centralizada (903/Frete), cubagem padrão (903/Frete) |
| **423** | Cubagem/taxas por cliente | Sobrescreve cubagem da transportadora (903/Frete) |
| **518** | Aprovação de tabelas | Ativado por (903/Frete) |
| **560** | Aprovação de despesas | Ativado por (903/Outros) |
| **169** | Aprovação de pedidos | Ativado por (903/Outros) |
| **111** | Cadastro conferentes | Ativado por (903/Operação) |
| **058** | Estoque pallets/gaiolas | Ativado por (903/Operação) |
| **234** | Horários de entrega | Requerido por Estou Chegando (903/Operação) |
| **698** | Prazo adicional cliente | Sobrescreve prazo geral (903/Prazos) |
| **079** | Crédito CTF | Login/senha configurados (903/PEF/CIOT) |
| **227** | Cartões PEF | PEFs da transportadora (903/PEF/CIOT) |
| **143** | Envio SMS | Provedor configurado (903/SMS) |
| **284** | Conferência manual | Ativado por (903/Envio SEFAZ) quando Enviar sem conferência = N |
| **007** | Aprovação SEFAZ | Envio automático (903/Envio SEFAZ), certificados (903/Certificados) |
| **595** | Baixa XMLs Contas Pagar | Horários de busca (903/Emissão CTRCs) |
| **171** | Jornada de trabalho | Satélite configurado (903/Gerenciamento Risco) |
| **920** | Numeração CTRCs | Certificados digitais (903/Certificados), busca XMLs (903/Emissão CTRCs) |

---

## Observações e Gotchas

### Hierarquias de Configuração

1. **Cubagem:**
   - Cliente específico (opção 423) → Transportadora (opção 903)
   - Se cliente = 0, cubagem não é calculada

2. **Prazo Entrega Difícil:**
   - Destinatário (opção 698) → Remetente (opção 698) → Pagador (opção 698) → Transportadora (opção 903)
   - Cliente pode ter prazo ZERO para ignorar geral

3. **Limite de Crédito:**
   - Grupo (opção 583) → Transportadora ABC (opção 903) → Individual do cliente

4. **Horários de entrega (Estou Chegando):**
   - Unidade específica (opção 234) → MTZ (opção 234)
   - MTZ precisa ter no mínimo "Início" cadastrado

### Bloqueios Automáticos

**Transportar = N** é ativado automaticamente por:
- Tabelas apagadas (903/Frete)
- Faturas vencidas além do prazo (903/Prazos)
- Faturas protestadas (opção 457)
- Retorno banco protestado (opção 444)
- Inativo no cadastro fiscal (opção 808)
- Consulta SERASA com pendências (opção 389) — exceto se tiver tabela própria

**Exceção:** Clientes especiais (opção 483) não sofrem bloqueio automático.

### Previsão de Entrega

Recalculada automaticamente na aprovação SEFAZ (opção 007), **exceto:**
- CTRCs FEC (fechada)
- CTRCs com prazo definido por EDI (cliente)

### Produtos Perigosos

Identificação automática via código ONU no XML da NF-e:
- DACTE recebe marca d'água "PERIGOSO" (opção 007)
- DAMDFE lista códigos ONU carregados (opção 020)
- Etiquetas SSWBar imprimem "PERIGOSO"

### CTRCs Complementares

**Disponíveis:**
- Geral (opção 222)
- Reentrega/Devolução/Recoleta (opção 016)
- Paletização (opção 089)
- Agendamento (opção 015)
- Estadia (opção 099)
- Armazenagem (opção 199)

**Não permite:** CTRC Simplificado (opção 004)

**Somente para efeito de frete:** Definido na opção 903, usado em taxas (423, 089, 015, 099)

### Retenções CTRB/RPA

| Retenção | Tipo Proprietário | Base | Alíquota | Ativação |
|----------|-------------------|------|----------|----------|
| **INSS** | Pessoa Física | 20% do CTRB | Tabela IR | Automático |
| **IRRF** | Pessoa Física | 20% do CTRB | Tabela IR | Automático |
| **SEST/SENAT** | Pessoa Física | 20% do CTRB | 2,5% | 903/Outros = S |
| **Previdência Social** | Pessoa Jurídica | 30% do CTRB | 11% | 903/Outros = S |

**Opções relacionadas:**
- 151: Comprovante Anual Rendimentos PJ
- 544: Relatório retenções PJ
- 489: Relatório CTRBs (preenchimento guias)
- 599: Arquivo DIRF
- 490: Comprovante DIRF alternativo

### Taxas Adicionais

**Taxa de Devolução Canhoto:**
- Cobra se cliente marcado "Devolve canhoto = SIM" (opção 483)
- Frete CIF apenas
- Valor cadastrado por cliente (opção 423)

**Taxa de Paletização:**
- Cobra via CTRC Complementar (opção 089)
- Valor/pallet cadastrado (opção 423)
- Gera Vale Pallet (cliente fica com pallet)
- Estoque associado ao cliente (sem alterar unidade)

**Taxa de Agendamento:**
- Cobra quando agendamento feito (opção 015)
- Só para CTRCs que faturam e ainda não faturados
- Valor único em R$ por CTRC
- Cobrada como adicional fatura (opção 442)
- Não cobra: CTRCs já faturados, frete à vista, destinatários excluídos (opção 423)

**Taxa de Estadia na Entrega:**
- Cobra horas além da franquia (opção 423)
- Informar horas via opção 099 ou 038
- Fração de hora é arredondada para cima (ex: 3:01h = 4 horas)

**Relatório 130:** Lista taxas não cobradas (disponível diariamente na opção 056)

### Estou Chegando — Detalhes Técnicos

**Requisitos:**
- Ativação (903/Operação)
- Romaneio roteirizado (903/Operação: "Ordenar CTRCs" = S)
- Horários cadastrados (opção 234) — pelo menos MTZ com "Início"
- Carregamento via digitação com sequência (opção 035) ou SSWBar

**Cálculo:**
- 1º cálculo: emissão Romaneio (opção 035) — todos CTRCs da sequência
- Recálculo: a cada ocorrência SSWBar — demais CTRCs da sequência
- Usa Google Maps para calcular tempos de deslocamento
- Respeita restrições: horário início, almoço, fim, permanência no cliente

**Comportamento:**
- Motorista fora da sequência → CTRCs pulados perdem previsão
- Apenas próximo CTRC da sequência recebe Ocorrência SSW 95
- Previsão após horário fim não é mostrada (mas é calculada)

**Disponibilização:**
- Site de rastreamento
- Opção 101
- SMS/WhatsApp (via ocorrência SSW 95)

### Controle de Estoque (Pallets/Gaiolas/Chapas)

**Ativação:** opção 903/Operação

**Cadastros:**
- Gaiolas: opção 021 (cadastradas individualmente)
- Pallets: não cadastrados (controle apenas quantitativo)
- Chapas: não cadastradas (controle apenas quantitativo)

**Movimentação:**
- Saída: Manifesto (opção 020) → Emissão saída (opção 025)
- Entrada: Chegada Manifesto (opção 030)
- Paletização: opção 089 (gera Vale Pallet, estoque fica com cliente)
- Ajuste: opção 021 (apenas pallets e chapas)

**Relatórios:**
- Situação estoque: opção 058 (unidade, veículo, clientes)
- Movimentação 7 dias: opção 058
- Localização gaiola: opção 058 (consulta individual)

### Busca de XMLs — Detalhes de Guarda

| Tipo XML | Uso | Guarda SSW |
|----------|-----|------------|
| **Transportadora** | Emissão CTRCs (004, 005, 006) | 60 dias |
| **Compradora** | Contas a Pagar (475) | 5 anos |

**Download:**
- Contas a Pagar: opção 595 (arquivos ZIP separados NF-e/CT-e)
- EDI automático: ssw2991 (contatar edi@ssw.inf.br)

### Certificado Digital — Avisos Importantes

**Vencimento:**
- Certificados vencidos **bloqueiam totalmente** emissão fiscal
- Alertas antecipados: opções 007, 551, 707
- Monitorar com antecedência mínima 30 dias

**Renovação:**
- Adquirir novo .PFX da certificadora
- Instalar via opção 903/Certificados Digitais
- Certificado antigo permanece na tabela (histórico)

**CNPJs:**
- 1 certificado por raiz de CNPJ
- Todos CNPJs da raiz compartilham o mesmo certificado
- Não é possível ter certificados diferentes para filiais da mesma raiz

### LGPD — Portal

**Acesso:** Opção 903 (sem sub-seção específica, mas integrado)

**Documentos disponíveis:**
- Lei 13.709 (texto atualizado)
- Apresentação e enquadramento de transportadoras
- Plano de Adequação (ações SSW + transportadora)
- Avaliações do Plano (status execução)
- Política de Segurança da Informação
- Plano de ação em caso de incidente

**Campos configuráveis (apenas usuário master):**

| Campo | Descrição |
|-------|-----------|
| **Titular LGPD** | Pessoa natural (cliente pessoa física) |
| **Operador LGPD** | SSW (trata dados em nome do controlador) |
| **Encarregado LGPD** | Login do responsável pela comunicação com ANPD |
| **Controlador** | Transportadora (CNPJ com certificado digital vigente) |

**Assinatura eletrônica:** Usuário master assina contrato com login/senha

---

## Acesso e Permissões

**Usuários autorizados a alterar:**
- Usuários MTZ (matriz)
- Usuários da Unidade Responsável (configurada por cliente na opção 483)

**Grupos de usuários:**
- Liberar acesso à opção 903 via opção 918 (grupos de acesso)
- Recomenda-se restrição severa (apenas gerência e TI)

**Impacto de alterações:**
- Mudanças na opção 903 afetam **TODA a transportadora** (todos CNPJs/unidades)
- Testar alterações em horário de baixa operação
- Documentar mudanças em ocorrências de sistema

---

## Versões e Atualizações

**Páginas de ajuda consolidadas:** 31 arquivos HTML (ssw0042 a ssw3201)

**Última atualização documentada:** 25/09/2024 (ssw3201.htm)

**Arquivos fonte:**
- ssw0042.htm (44 KB) — Relatórios gerenciais
- ssw0767.htm (237 KB) — Aprovação CT-e SEFAZ
- ssw1105.htm (113 KB) — Crédito clientes
- ssw2688.htm (75 KB) — Emissão CTRCs
- ssw3038.htm (111 KB) — Base XMLs
- ssw3074.htm (112 KB) — Horários entregas
- (e 25 outros arquivos)

---

## Dicas de Uso

1. **Antes de alterar qualquer parâmetro:**
   - Verificar quais opções dependem da configuração
   - Comunicar equipe operacional
   - Fazer em horário de baixa operação (se possível)

2. **Configurações críticas (não alterar sem planejamento):**
   - Aprovação centralizada de tabelas (impacta todas opções de cadastro)
   - Envio automático ao SEFAZ (impacta expedição)
   - Horários de busca XMLs (risco de Uso Indevido)
   - Certificados digitais (bloqueio fiscal se errado)

3. **Configurações por cliente vs transportadora:**
   - Sempre preferir configuração por cliente (mais granular)
   - Usar 903 apenas como padrão/fallback
   - Exceção: parâmetros que devem ser únicos (ex: certificado, gerenciadora)

4. **Relatórios de monitoramento:**
   - 040: Faturas vencidas (processa 9:30h e 12:40h)
   - 056: Relatórios gerenciais (diários)
   - 130: Taxas adicionais não cobradas
   - 087: Ocorrências fora do local (diário por unidade e MTZ)

5. **Integrações externas:**
   - CTF Ipiranga: testar credenciais antes de ativar
   - PEFs: cadastrar conta bancária (opção 904) e dados favorecidos (opção 027)
   - SMS: validar mensagens de teste
   - Satélite: validar recepção de coordenadas antes ativar Jornada/Estou Chegando

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A09](../pops/POP-A09-cadastrar-motorista.md) | Cadastrar motorista |
| [POP-B01](../pops/POP-B01-cotar-frete.md) | Cotar frete |
| [POP-B02](../pops/POP-B02-formacao-preco.md) | Formacao preco |
| [POP-B03](../pops/POP-B03-parametros-frete.md) | Parametros frete |
| [POP-B04](../pops/POP-B04-resultado-ctrc.md) | Resultado ctrc |
| [POP-B05](../pops/POP-B05-relatorios-gerenciais.md) | Relatorios gerenciais |
| [POP-C05](../pops/POP-C05-imprimir-cte.md) | Imprimir cte |
| [POP-D02](../pops/POP-D02-romaneio-entregas.md) | Romaneio entregas |
| [POP-E03](../pops/POP-E03-faturamento-automatico.md) | Faturamento automatico |
| [POP-F01](../pops/POP-F01-contas-a-pagar.md) | Contas a pagar |
| [POP-F06](../pops/POP-F06-aprovar-despesas.md) | Aprovar despesas |
| [POP-G01](../pops/POP-G01-sequencia-legal-obrigatoria.md) | Sequencia legal obrigatoria |
