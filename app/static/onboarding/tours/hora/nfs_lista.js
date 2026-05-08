window.OnboardingEngine.register({
  id: 'hora.nfs_lista',
  titulo: 'NFs de Entrada (Motochefe → HORA)',
  requirePerm: { modulo: 'nfs', acao: 'ver' },
  autoStartRoute: '/hora/nfs',
  steps: [
    { element: '#filtros-nfs', title: 'Filtros', description: 'Numero, emissor, loja destino, periodo, vinculo. Use para achar NFs pendentes de recebimento.' },
    { element: '#btn-upload-nf', title: 'Upload de NF', description: 'Suba PDF DANFE da Motochefe. Parser extrai chassi, modelo e cor automaticamente.' },
    { element: '#tabela-nfs', title: 'Lista de NFs', description: 'Cada linha = 1 NF parseada. Status mostra se ja foi vinculada a um recebimento.' }
  ]
});
