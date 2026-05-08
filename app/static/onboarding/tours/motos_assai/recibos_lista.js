window.OnboardingEngine.register({
  id: 'motos_assai.recibos_lista',
  titulo: 'Recibos da Motochefe',
  autoStartRoute: '/motos-assai/recibos',
  steps: [
    { element: '#filtros-recibos-assai', title: 'Filtros', description: 'Status, equipe, periodo. Encontre recibos pendentes de conferencia.' },
    { element: '#tabela-recibos-assai', title: 'Lista de recibos', description: '<strong>AGUARDANDO_CONFERENCIA</strong>, <strong>EM_CONFERENCIA</strong>, <strong>CONCLUIDO</strong>, <strong>COM_DIVERGENCIA</strong>. Clique em # para conferir os chassis no wizard.' },
    { element: '#tabela-recibos-assai', title: 'Como cadastrar um novo recibo?', description: '<strong>Importante:</strong> recibo nao e criado por aqui. Cada recibo pertence a 1 PO Motochefe. Va em <strong>POs Motochefe</strong>, abra o PO e clique em <strong>Importar Recibo Motochefe</strong>.', adminOnly: true }
  ]
});
