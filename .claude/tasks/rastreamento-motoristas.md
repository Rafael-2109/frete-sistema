# MISSÃO: Sistema Completo de Rastreamento de Motoristas Android

## CONTEXTO
- Sistema de gestão de frete Flask/Python
- JÁ EXISTE implementação parcial - EXPLORE primeiro
- Backend Flask deve ser usado/expandido
- Integração com Odoo para gravar dados nas NFs

## FASE 1: EXPLORAÇÃO (NÃO PULE)

Antes de implementar, explore e documente:
- Glob: **/rastreamento/**, **/tracking/**, **/motorista/**
- Grep: rastreamento, tracking, motorista, QR, qrcode
- Modelos: Embarque, EmbarqueItem, Separacao, DespesaExtra
- Routes existentes de embarque/motorista/monitoramento
- Use TodoWrite para documentar o que existe vs o que falta

## FASE 2: REQUISITOS

### 2.1 App Mobile Android

Tecnologia: Escolha a melhor (React Native/Expo, Flutter, PWA) considerando câmera, GPS background, notificações.

Fluxo:
1. Tela inicial: Escanear QR Code do embarque
2. Ao ler QR: Iniciar GPS, associar motorista ao embarque
3. GPS monitora localização vs endereços dos clientes
4. Quando motorista chegar (~200m): Ativar tela de entrega

Tela de Entrega:
- Botão 'Contactar Monitoramento' → Comentário nas NFs
- Botão 'Finalizar Entrega' → Questionário

Questionário:
1. NFs {nf_1}, {nf_2}... foram entregues?
   - SIM: Foto canhoto + gravar finalização
   - NÃO: Registrar não entregue
2. Houve devolução?
   - SIM: Ler código barras NFD OU campo manual → Gravar NFD
3. Houve pagamento descarga?
   - SIM: Campo valor + foto → DespesaExtra
4. Houve devolução pallet?
   - SIM: Select quantidade
   - NÃO: Vale pallet? (foto) / Canhoto NF pallet? (registrar)

Após finalizar:
- Se tem NF pendente: Manter rastreamento
- Se não tem: Agradecer e finalizar

### 2.2 Backend Flask

Endpoints necessários:
- POST /api/rastreamento/iniciar
- POST /api/rastreamento/localizacao
- GET /api/rastreamento/{session_id}/verificar-proximidade
- POST /api/rastreamento/comentario
- POST /api/rastreamento/finalizar-entrega
- POST /api/rastreamento/finalizar
- GET /api/rastreamento/ativos
- GET /api/rastreamento/dificuldades

### 2.3 Tela Monitoramento Web

Em app/templates/rastreamento/monitoramento.html:
- Mapa com motoristas rastreados
- Lista: motorista, clientes, NFs pendentes, última saída
- Botão 'Entregas com Dificuldade ({n})' - motoristas >40min no cliente
- Ao finalizar entrega, zerar atraso

### 2.4 Integração Odoo

- Gravar comentários em NFs
- Gravar finalização monitoramento
- Registrar NFD vinculada
- Criar DespesaExtra

## FASE 3: IMPLEMENTAÇÃO

Ordem: Modelos → Endpoints → Tela web → App mobile → Odoo → Testes

## FASE 4: VERIFICAÇÃO

[ ] QR Code lido corretamente
[ ] GPS background funciona
[ ] Proximidade detectada
[ ] Questionário completo funciona
[ ] Fotos capturadas e salvas
[ ] Dados gravados no Odoo
[ ] DespesaExtra criada
[ ] Monitoramento tempo real
[ ] Alerta >40min funciona
[ ] Fluxo completo funciona

## REGRAS

- NÃO INVENTAR - Buscar primeiro
- CÓDIGO COMPLETO - Sem TODOs
- TESTAR sempre que possível
- DOCUMENTAR no CLAUDE.md

Quando TUDO estiver pronto e testado: <promise>RASTREAMENTO COMPLETO</promise>
