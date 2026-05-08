window.OnboardingEngine.register({
  id: 'motos_assai.recibos_lista',
  titulo: 'Recibos da Motochefe',
  autoStartRoute: '/motos-assai/recibos',
  steps: [
    { element: '#filtros-recibos-assai', title: 'Filtros', description: 'Status, equipe, periodo. Encontre recibos pendentes de conferencia.' },
    { element: '#btn-upload-recibo-assai', title: 'Subir novo recibo', description: 'PDF/XLSX recibo Motochefe. Parser extrai chassis automaticamente.', adminOnly: true },
    { element: '#tabela-recibos-assai', title: 'Lista de recibos', description: 'AGUARDANDO_CONFERENCIA, EM_CONFERENCIA, CONCLUIDO, COM_DIVERGENCIA.' }
  ]
});
