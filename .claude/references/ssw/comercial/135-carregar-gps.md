# Opção 135 — Carregar GPS

> **Módulo**: Comercial
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14

## Função
Grava automaticamente no navegador GPS do motorista os pontos de entrega de um Manifesto ou Romaneio com coordenadas geográficas, otimizando o processo de inserção de rotas e facilitando a localização de endereços.

## Quando Usar
- Veículos com mais de 100 entregas por dia (inviável inserir manualmente no GPS)
- Necessidade de roteirizar entregas para menor distância total
- Facilitar localização de endereços pelo motorista via comandos de voz do GPS
- Preparar GPS do motorista após emissão de Romaneio ou Manifesto

## Pré-requisitos
- **GPS compatível**: Sistema IGO (navegadores FOSTON, AMIGO, GARMIN, BAK, etc.)
- **Manifesto ou Romaneio emitido**: Documento já gerado no SSW
- **Coordenadas geográficas**: Endereços devem ter latitude/longitude cadastradas
- **Porta USB**: Para conectar GPS ao computador
- **Google Maps**: Para localizar coordenadas (integração via "Apontar no mapa")

## Campos / Interface

### Tela Inicial
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Manifesto ou Romaneio | Sim | Número do Manifesto ou Romaneio para carregamento do GPS |

### Tela Seguinte
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| LATITUDE/LONGITUDE | Sim | Coordenadas geográficas do endereço da unidade (origem da rota) |
| APONTAR NO MAPA | - | Link abre Google Maps mostrando endereço da unidade |
| CARREGAR GPS | - | Link faz download do arquivo de coordenadas para importação no GPS |

### Lista de CTRCs (parte central)
| Campo | Descrição |
|-------|-----------|
| CTRCs do Romaneio/Manifesto | Lista de CTRCs com destino FEC (Carga Fechada) |
| Latitude/Longitude (por CTRC) | Permite alterar coordenadas de cada cliente |
| Apontar no mapa (por CTRC) | Atualiza latitude/longitude do cliente via Google Maps |

### Janela "Apontar no Mapa"
| Opção | Descrição |
|-------|-----------|
| LOCALIZAR | Busca por descrição do endereço (melhorar ou alterar texto para sucesso) |
| CLICANDO NO MAPA | Clicar diretamente no mapa com mouse para identificar coordenadas |

## Fluxo de Uso

### Gerar Arquivo de Coordenadas
1. Emitir Romaneio ou Manifesto previamente
2. Acessar opção 135
3. Informar número do Manifesto ou Romaneio
4. Clicar em **►** → sistema exibe dados do documento
5. Na tela seguinte, revisar/preencher coordenadas:
   - **LATITUDE/LONGITUDE** da unidade (obrigatório)
   - Clicar em **APONTAR NO MAPA** para confirmar localização da unidade
6. Para cada CTRC com destino FEC (parte central):
   - Revisar latitude/longitude do cliente
   - Se necessário, clicar em **Apontar no mapa** para corrigir coordenadas:
     - Opção 1: Usar botão **LOCALIZAR** com descrição do endereço (formato sugerido: "R DR JOSE DA SILVA, 99, SAO PAULO, SP")
     - Opção 2: Clicar diretamente no mapa com mouse
   - Fechar janela → coordenadas são atualizadas automaticamente
7. Verificar que todos os pontos necessários têm coordenadas (SSW alerta se houver faltantes)
8. Clicar em **Carregar GPS** → download do arquivo de coordenadas

### Carregar GPS Fisicamente
1. Conectar navegador GPS à porta USB do computador
2. **IMPORTANTE**: GPS deve estar fora do Sistema IGO (tela inicial após ligar)
3. Clicar em **Carregar GPS** novamente
4. Sistema localiza GPS conectado → janela de confirmação aparece
5. Clicar em **Carregar GPS** na janela → coordenadas são gravadas no GPS
6. Aguardar conclusão da gravação
7. Desconectar GPS do micro
8. Entregar GPS ao motorista para uso nas entregas

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| Emissão de Romaneios | Documentos de origem para geração de coordenadas |
| Emissão de Manifestos | Documentos de origem para geração de coordenadas |
| Google Maps | Integração via "Apontar no mapa" para localizar coordenadas |
| Sistema IGO | Sistema GPS compatível (navegadores FOSTON, AMIGO, GARMIN, BAK) |

## Observações e Gotchas
- **Compatibilidade**: Inicialmente disponível apenas para Sistema IGO (diversos navegadores compatíveis)
- **Coordenada definitiva**: Simples clique no mapa altera coordenadas permanentemente → **só clicar com certeza da localização**
- **Coordenada reutilizada**: Coordenadas localizadas são arquivadas pelo SSW para uso futuro por todos os usuários
- **Apenas pontos com coordenadas**: GPS só carrega pontos que tiverem latitude/longitude identificadas (SSW alerta mas permite carregar apenas identificados)
- **Carga fechada vs fracionada**: Manifesto para carga fracionada mostra apenas endereço da unidade destino; FEC mostra todos os CTRCs
- **Otimização de rota**: GPS cria rota para Manifesto ou rota/sequência de entregas para Romaneio com base nas coordenadas
- **Formato de endereço**: Para busca bem-sucedida, usar formato abreviado: "R DR JOSE DA SILVA, 99, SAO PAULO, SP"
- **Processo de tentativas**: Localização via descrição pode requerer ajustes no texto até aparecer ponto no mapa
- **Precisão**: Após localizar via descrição, pode-se clicar no mapa para dar mais precisão ao local do cliente
- **GPS fora do sistema**: Para carregar, GPS deve estar na tela inicial (fora do Sistema IGO)
- **Alto volume**: Funcionalidade essencial para veículos com mais de 100 entregas/dia
- **Comandos de voz**: GPS instrui motorista com comandos de voz, facilitando localização de endereços
