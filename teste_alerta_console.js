// Teste para executar no console do navegador
// Copie e cole este código no console quando estiver em /pedidos/lista_pedidos.html

console.log('=== TESTE DE ALERTAS ===');

// 1. Verificar se o container existe
const container = document.getElementById('alertasContainer');
if (container) {
    console.log('✅ Container encontrado:', container);
} else {
    console.log('❌ Container NÃO encontrado!');
}

// 2. Fazer a chamada manualmente
console.log('Fazendo chamada para API...');
fetch('/api/alertas-separacao/card-html')
    .then(response => {
        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers.get('content-type'));
        
        if (response.status === 401) {
            console.log('❌ Não autorizado - faça login primeiro!');
            return null;
        }
        
        if (response.status === 204) {
            console.log('⚠️ Sem alertas (204 No Content)');
            return '';
        }
        
        return response.text();
    })
    .then(html => {
        if (html === null) return;
        
        console.log('HTML recebido:', html ? html.length + ' caracteres' : 'vazio');
        
        if (html && html.length > 0) {
            console.log('✅ Inserindo HTML no container...');
            if (container) {
                container.innerHTML = html;
                console.log('✅ HTML inserido com sucesso!');
                
                // Verificar se ficou visível
                const alertDiv = container.querySelector('.alert');
                if (alertDiv) {
                    console.log('✅ Alert visível:', alertDiv.offsetHeight > 0 ? 'SIM' : 'NÃO');
                }
            } else {
                console.log('❌ Container não existe para inserir HTML!');
            }
        } else {
            console.log('⚠️ HTML vazio ou sem conteúdo');
        }
    })
    .catch(error => {
        console.error('❌ ERRO:', error);
    });

console.log('=== FIM DO TESTE ===');