window.OnboardingEngine.register({
  id: 'hora.devolucao_venda',
  titulo: 'Registrar devolucao de venda',
  requirePerm: { modulo: 'devolucoes_venda', acao: 'criar' },
  autoStartRoute: '/hora/devolucoes-venda/novo',
  steps: [
    { element: '#campo-venda-origem',    title: 'Venda original',         description: 'Busque pelo numero do pedido ou chave da NFe. Sistema lista os chassis que podem voltar.' },
    { element: '#secao-itens-devolvidos', title: 'Marque o que voltou',   description: 'Pode ser devolucao parcial. Cada chassi marcado emite evento DEVOLVIDA e volta ao estoque DISPONIVEL.' },
    { element: '#campo-motivo',          title: 'Motivo da devolucao',    description: 'Obrigatorio. Aparece na auditoria e pode subsidiar politica comercial futura.' },
    { element: '#btn-salvar-devolucao',  title: 'Confirmar devolucao',    description: 'Emite eventos, atualiza estoque e marca a venda como parcialmente/totalmente devolvida.' }
  ]
});
