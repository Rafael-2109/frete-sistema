# Opção 206 — Chaves DANFEs Capturadas pelo SSWMobile 5 - Coleta

> **Módulo**: Comercial / Expedição
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função
Gerencia chaves de DANFEs (Documento Auxiliar de Nota Fiscal Eletrônica) capturadas durante a coleta pelo SSWMobile, permitindo que a expedição gere CT-e antecipadamente, antes mesmo da chegada do veículo.

## Quando Usar
- Para agilizar a emissão de CT-e de mercadorias em trânsito (ainda no veículo de coleta)
- Para rastrear DANFEs capturadas por veículo e período
- Para verificar disponibilidade de XMLs antes da emissão de CTRC
- Para identificar quais coletas já tiveram CTRC emitido

## Pré-requisitos
- SSWMobile 5 configurado nos veículos de coleta
- Motoristas treinados para capturar chaves DANFE durante coleta
- Opção 011 (etiquetas NR1/NR2) para captura complementar (opcional)
- Opção 903/outros para contratação de empresas especializadas em fornecimento de XMLs (opcional)

## Campos / Interface
### Tela de Filtros
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Unidade do veículo | Sim | Unidade à qual estão vinculados os veículos de coleta (SSWMobile 5) |
| Veículo | Não | Filtro opcional por placa de veículo específico |
| Dia da captura | Sim | Data em que a chave DANFE foi capturada pelo SSWMobile 5 |
| A partir de | Não | Horário do dia a partir do qual buscar capturas |
| XML disponível | Não | Filtrar apenas DANFEs com XML já disponível no SSW |
| CTRC emitido | Não | Filtrar apenas DANFEs sem CTRC emitido (pendentes) |

### Relatório Gerado
| Coluna | Descrição |
|--------|-----------|
| NF-E | Número da Nota Fiscal |
| CHAVE DANFE | Chave de 44 dígitos (pode ser copiada com Ctrl+V e colada na opção 004) |
| XML | "S" indica XML disponível (facilita emissão do CT-e, dispensando captcha) |
| NR1 / NR2 | Etiquetas sequenciais dos volumes coletados (usadas no descarregamento com SSWBar) |
| CTR | "S" indica que pré-CTRC já foi emitido |

## Fluxo de Uso
1. **Durante a coleta** (SSWMobile 5):
   - Motorista captura chaves DANFE das mercadorias coletadas
   - Opcionalmente captura NR1 e NR2 (etiquetas sequenciais) junto com a chave
2. **Na expedição** (antes da chegada do veículo):
   - Acessar opção 206
   - Filtrar por unidade, veículo e dia da captura
   - Gerar relatório com as chaves capturadas
3. **Emissão antecipada de CT-e**:
   - Copiar chave DANFE do relatório (Ctrl+V)
   - Colar na opção 004 para gerar CT-e (Ctrl+C)
   - Se XML disponível ("S"), geração é automática (sem captcha)
4. **Obtenção de XMLs** (se necessário):
   - Via Portal NF-e (CNPJ da transportadora deve estar no campo DANFE)
   - Via importação manual (opção 608)
   - Via empresas especializadas (opção 903/Outros)

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 004 | Emissão de CT-e (usa chave DANFE copiada do relatório) |
| 011 | Etiquetas NR1/NR2 (podem ser capturadas junto com a chave DANFE) |
| 115 | Captura de etiquetas (dispensada se NR1/NR2 forem capturados no SSWMobile) |
| 608 | Importação de arquivo XML de DANFE |
| 903 | Cadastro de empresas especializadas em fornecimento de XMLs |

## Observações e Gotchas
- **Automação completa**: Com XMLs disponíveis, a emissão de CTRC é integralmente automatizada (sem digitação)
- **NR1/NR2 no SSWMobile**: Capturas dessas etiquetas junto com a chave DANFE tornam desnecessária a captura posterior pela opção 115
- **3 formas de obter XML**:
  1. Portal NF-e (requer CNPJ da transportadora no campo DANFE)
  2. Importação manual (opção 608)
  3. Empresas especializadas (relação disponível em opção 903/Outros)
- **Ganho de tempo**: Expedição pode emitir CT-e enquanto veículo está em trânsito, reduzindo tempo de permanência do veículo na unidade
- **Chave DANFE**: Possui 44 dígitos e pode ser copiada/colada diretamente do relatório
- **Captcha**: Dispensado quando XML está disponível, agilizando a emissão
- **Filtro por pendências**: Use filtro "CTRC emitido = Não" para visualizar apenas coletas pendentes de emissão
