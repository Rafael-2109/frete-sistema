
document.addEventListener('click', function(e) {
  if (e.target.matches('.btn-remover')) {
    const linha = e.target.closest('tr');
    const itemId = e.target.getAttribute('data-item-id');

    // Função para obter token CSRF do <meta name="csrf-token">
    function getCSRFToken() {
      const meta = document.querySelector('meta[name="csrf-token"]');
      return meta ? meta.getAttribute('content') : '';
    }

    // Se não há ID, é um item ainda não salvo no banco; basta remover do DOM
    if (!itemId) {
      if (confirm('Excluir este item não salvo?')) {
        linha.remove();
      }
      return;
    }

    // Caso haja ID, confirmar exclusão e enviar requisição POST
    if (confirm('Excluir definitivamente esse item?')) {
      const csrfToken = getCSRFToken();

      fetch(`/embarques/excluir_item/${itemId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        // Opcional: incluir também no body, se preferir
        body: JSON.stringify({ csrf_token: csrfToken })
      })
      .then(response => response.json())
      .then(data => {
        if (data.status === 'success') {
          linha.remove();
        } else {
          alert('Erro ao excluir item: ' + data.message);
        }
      })
      .catch(error => {
        console.error('Erro ao excluir item:', error);
        alert('Falha na conexão ao tentar excluir o item.');
      });
    }
  }
});
