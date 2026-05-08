window.OnboardingEngine.register({
  id: 'motos_assai.recibos_upload',
  titulo: 'Subir recibo Motochefe',
  adminOnly: true,
  autoStartRoute: '/motos-assai/compras/*/recibos/upload',
  steps: [
    { element: '#upload-recibo',         title: 'PDF ou XLSX deste PO',         description: 'Voce esta subindo o recibo da Motochefe vinculado ao PO mostrado no topo. Cada recibo pertence a 1 PO especifico (chave: compra_id).' },
    { element: '#btn-salvar-recibo',     title: 'Importar',                     description: 'Parser deterministico extrai os chassis. Se confianca < 80%, aciona LLM (Haiku → Sonnet). O recibo nasce em <strong>RECEBIDO_AGUARDANDO_CONFERENCIA</strong> e fica disponivel para o operador conferir via wizard QR.' }
  ]
});
