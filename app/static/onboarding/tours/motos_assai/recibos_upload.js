window.OnboardingEngine.register({
  id: 'motos_assai.recibos_upload',
  titulo: 'Subir recibo Motochefe',
  adminOnly: true,
  autoStartRoute: '/motos-assai/recibos/upload',
  steps: [
    { element: '#upload-recibo',         title: 'PDF ou XLSX',                  description: 'Recibo emitido pela equipe Motochefe (Haroldo SP, etc.). Lista os chassis que vao chegar fisicamente.' },
    { element: '#preview-chassis',       title: 'Preview dos chassis extraidos', description: 'Confirme que o numero total bate. Limiar de confianca 80% — abaixo disso aciona LLM.' },
    { element: '#btn-salvar-recibo',     title: 'Salvar como AGUARDANDO',       description: 'Status RECEBIDO_AGUARDANDO_CONFERENCIA. Operadores comecam a conferir via wizard QR.' }
  ]
});
