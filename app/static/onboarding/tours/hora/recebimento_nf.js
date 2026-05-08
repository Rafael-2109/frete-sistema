window.OnboardingEngine.register({
  id: 'hora.recebimento_nf',
  titulo: 'Como receber NF da Motochefe',
  requirePerm: { modulo: 'recebimentos', acao: 'criar' },
  autoStartRoute: '/hora/recebimentos/novo',
  steps: [
    {
      element: '#nf-upload-area',
      title: 'Suba o PDF da NF',
      description: 'Arraste o DANFE recebido da Motochefe. <strong>Aceita so PDF</strong>. O parser extrai chassi, modelo e cor automaticamente.'
    },
    {
      element: '#campo-loja-destino',
      title: 'Loja que vai receber',
      description: 'Escolha qual loja fisica esta recebendo. Define o estoque destino dos chassis.'
    },
    {
      element: '#btn-parsear',
      title: 'Parsear DANFE',
      description: 'Roda o parser. Se a NF estiver legivel, lista todos os chassis em ~5s. Se vier ruim, fallback LLM (Haiku 4.5) entra em acao.'
    },
    {
      element: '#tabela-itens-extraidos',
      title: 'Confira o que veio',
      description: 'Cada linha = 1 chassi declarado. Voce ainda vai conferir fisicamente cada um. <strong>Divergencias entre NF e fisico viram evento MOTO_FALTANDO.</strong>'
    },
    {
      element: '#btn-iniciar-conferencia',
      title: 'Iniciar conferencia',
      description: 'Salva o registro e abre o wizard de conferencia (chassi-por-chassi com QR ou digitacao manual).'
    }
  ]
});
