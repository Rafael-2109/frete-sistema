# Opção 220 — Emissão de Manifestos e Romaneios com Sorter

> **Módulo**: Comercial / Operacional
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função
Integra o sistema SSW com equipamento sorter (separador automático) para gerar Placas Provisórias e emitir Manifestos e Romaneios de Entregas de forma automatizada, com opção de montagem de paletes e gaiolas.

## Quando Usar
- Para automatizar separação de volumes com equipamento sorter
- Para gerar Placas Provisórias automaticamente conforme volumes são processados
- Para emitir manifestos e romaneios de forma rápida e automatizada
- Para montar paletes e gaiolas durante o processo de separação

## Pré-requisitos
- Equipamento sorter instalado e configurado
- Login do sorter (opção 925) cadastrado com a unidade onde está instalado
- API do sorter configurada ([WebAPI](https://ssw.inf.br/ajuda/sorter.html))
- Login iniciado com palavra "SORTER" para não misturar com opção 020
- Volumes identificados com etiqueta de código de barras (SSWBar ou cliente)
- Máscara de código de barras configurada (opção 388)
- Gaiolas cadastradas (opção 021) para montagem opcional
- Microcomputadores instalados em bancadas (mesma unidade do sorter)

## Campos / Interface
### Tela de Monitoração
| Coluna | Descrição |
|--------|-----------|
| T (1) | Tipo: "T" = Transferência (opção 020), "E" = Entrega (opção 035) |
| Placa (2) | Placa Provisória no formato XXX9999 (XXX = rampa/sigla unidade ou setor) |
| Última NR (3) | Último volume (NR) que passou pela rampa |
| Qtde CTRCs (4) | Quantidade de CTRCs que desceram na rampa para a Placa |
| Qtde volumes (5) | Quantidade de volumes que desceram na rampa para a Placa |
| Mercadorias R$ (6) | Valor total da mercadoria que desceu na rampa |
| Peso Kg (7) | Peso real da mercadoria que desceu na rampa |
| Concluir (8) | Link para concluir a Placa Provisória (inicia nova sequencial) |
| Etiqueta (9) | Link para vincular Placa em palete/gaiola e imprimir etiqueta |

### Outros Recursos
| Recurso | Descrição |
|---------|-----------|
| Concluir operação (11) | Conclui todas as Placas Provisórias (todas as rampas) - usar ao final do dia |
| NRs sem Placa Provisória (12) | Relaciona volumes das últimas 24h sem Placa retornada pelo sorter |

## Fluxo de Uso
1. **Preparação**:
   - Logar opção 220 com mesmo login do sorter
   - Volumes identificados com etiqueta são colocados na esteira
2. **Processamento automático pelo sorter**:
   - Sorter lê código de barras do volume
   - API informa unidade destino e setor de entrega
   - Sorter derruba volume na rampa correspondente
   - API inclui volume em Placa Provisória (formato XXX9999)
3. **Monitoração** (Tela opção 220):
   - Acompanhar geração das Placas nas rampas
   - Visualizar quantidade de CTRCs, volumes, peso e valor
4. **Conclusão de Placa**:
   - Via tela: clicar em "Concluir" (8) na linha da Placa
   - Via botão físico: acionar WebAPI do sorter
   - Sistema inicia nova Placa sequencial (mantém XXX, avança 9999)
5. **Montagem de palete/gaiola** (opcional):
   - Antes da conclusão: clicar em "Etiqueta" (9) para vincular e imprimir
   - Após conclusão: reimprimir usando link na linha ou via (10) capturando 2 volumes
6. **Emissão de Manifesto/Romaneio**:
   - Se XXX = unidade: Placa aparece na opção 020 (Manifesto)
   - Se XXX = setor: Placa aparece na opção 035 (Romaneio)
7. **Final do dia**:
   - Clicar em "Concluir operação" (11) para fechar todas as Placas

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 020 | Emissão de Manifestos (recebe Placas com XXX = unidade) |
| 035 | Emissão de Romaneios (recebe Placas com XXX = setor) |
| 021 | Cadastro de gaiolas (necessário para montagem) |
| 025 | Saída de veículos (pode liberar com pré-CTRCs sem autorização) |
| 091 | CTRCs segregados (sorter envia para área de rejeito) |
| 101 | Ocorrências SSWBar/sorter (rastreabilidade) |
| 388 | Configuração de máscara de código de barras |
| 903 | Configuração: Autorização com pré-CTRC |
| 925 | Cadastro de login do sorter |

## Observações e Gotchas
- **Login obrigatório**: Opção 220 DEVE usar o mesmo login do sorter (configurado na API)
- **Palavra-chave SORTER**: Login deve iniciar com "SORTER" para não misturar com opção 020
- **Unidade do login**: Deve ser a mesma da instalação física do sorter (descarga e manifestos nesta unidade)
- **Formato da Placa**: XXX9999 onde XXX = sigla unidade ou setor, 9999 = sequencial
- **Placa não reaproveitada**: Após conclusão, placa (sigla+número) não é reutilizada
- **Conclusão**: Pode ser feita pela tela (link 8) ou por botão físico no sorter (aciona WebAPI)
- **Destino de palete/gaiola**: Sempre o mesmo da Placa Provisória (definido pelo primeiro volume)
- **Impressão de etiqueta**:
  - Antes da conclusão: via link "Etiqueta" (9) na linha
  - Após conclusão: via link na linha ou capturando 2 volumes do palete (10)
  - Impressora móvel: Zebra ZQ630 RFID recomendada (configurar como padrão)
- **CTRCs segregados**: Sorter envia automaticamente para área de rejeito (opção 091)
- **Pré-CTRCs sem autorização**: Configure opção 903 para permitir saída de veículos com alguns CTRCs ainda sem autorização SEFAZ (processo rápido do sorter)
- **Funções SSWBar**: Sorter executa descarregamento e carregamento (disponível em opção 101/SSWBar/sorter)
- **NRs sem Placa (12)**: Útil para identificar volumes que passaram pelo sorter mas não receberam Placa (2ª perna)
- **Máscara de código**: Configure opção 388 para reconhecer diferentes formatos de etiqueta
- **Última 24h**: Relatório de NRs sem Placa considera apenas últimas 24 horas
