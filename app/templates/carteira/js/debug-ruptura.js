/**
 * DEBUG: Script para diagnosticar problemas com ruptura-estoque.js
 */

console.log('🔍 DEBUG RUPTURA - Iniciando diagnóstico...');

// Verificar se o DOM está carregado
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOM carregado');
    
    // Aguardar um pouco para garantir que tudo carregou
    setTimeout(function() {
        console.log('\n=== VERIFICANDO ELEMENTOS ===');
        
        // 1. Verificar tabela
        const tabela = document.getElementById('tabela-carteira');
        if (tabela) {
            console.log('✅ Tabela encontrada: #tabela-carteira');
        } else {
            console.error('❌ Tabela NÃO encontrada: #tabela-carteira');
        }
        
        // 2. Verificar linhas com classe pedido-row
        const pedidoRows = document.querySelectorAll('tr.pedido-row');
        console.log(`📊 Linhas .pedido-row encontradas: ${pedidoRows.length}`);
        
        // 3. Verificar data-pedido
        const rowsComDataPedido = document.querySelectorAll('tr[data-pedido]');
        console.log(`📊 Linhas com data-pedido: ${rowsComDataPedido.length}`);
        
        // 4. Verificar colunas entrega-obs
        const colunasEntregaObs = document.querySelectorAll('.coluna-entrega-obs');
        console.log(`📊 Colunas .coluna-entrega-obs: ${colunasEntregaObs.length}`);
        
        // 5. Verificar se RupturaEstoqueManager foi criado
        if (window.rupturaManager) {
            console.log('✅ window.rupturaManager existe');
        } else {
            console.error('❌ window.rupturaManager NÃO existe');
        }
        
        // 6. Verificar se separacaoManager existe
        if (window.separacaoManager) {
            console.log('✅ window.separacaoManager existe');
            if (window.separacaoManager.applyTargets) {
                console.log('✅ separacaoManager.applyTargets existe');
            } else {
                console.error('❌ separacaoManager.applyTargets NÃO existe');
            }
        } else {
            console.error('❌ window.separacaoManager NÃO existe');
        }
        
        // 7. Listar primeiros 3 pedidos encontrados
        console.log('\n=== PRIMEIROS PEDIDOS ===');
        pedidoRows.forEach((row, index) => {
            if (index < 3) {
                const numPedido = row.dataset.pedido;
                const celulaObs = row.querySelector('.coluna-entrega-obs');
                console.log(`Pedido ${index + 1}:`);
                console.log(`  - Número: ${numPedido || 'SEM DATA-PEDIDO'}`);
                console.log(`  - Célula Obs: ${celulaObs ? 'ENCONTRADA' : 'NÃO ENCONTRADA'}`);
                
                // Verificar se já tem botão
                const btnExistente = row.querySelector('.btn-analisar-ruptura');
                console.log(`  - Botão ruptura: ${btnExistente ? 'JÁ EXISTE' : 'NÃO EXISTE'}`);
            }
        });
        
        // 8. Tentar adicionar botão manualmente no primeiro pedido
        console.log('\n=== TESTE MANUAL ===');
        if (pedidoRows.length > 0) {
            const primeiraRow = pedidoRows[0];
            const numPedido = primeiraRow.dataset.pedido;
            const celulaObs = primeiraRow.querySelector('.coluna-entrega-obs');
            
            if (numPedido && celulaObs && !primeiraRow.querySelector('.btn-analisar-ruptura')) {
                console.log(`Adicionando botão de teste no pedido ${numPedido}...`);
                
                const btnContainer = document.createElement('div');
                btnContainer.className = 'mt-2';
                btnContainer.innerHTML = `
                    <button class="btn btn-sm btn-outline-danger" 
                            onclick="alert('Botão de teste funcionando! Pedido: ${numPedido}')"
                            title="BOTÃO DE TESTE">
                        <i class="fas fa-bug me-1"></i>
                        TESTE RUPTURA
                    </button>
                `;
                
                celulaObs.appendChild(btnContainer);
                console.log('✅ Botão de teste adicionado com sucesso!');
            } else {
                console.log('❌ Não foi possível adicionar botão de teste');
                console.log(`  - numPedido: ${numPedido}`);
                console.log(`  - celulaObs: ${celulaObs ? 'existe' : 'não existe'}`);
            }
        }
        
        // 9. Verificar se o script ruptura-estoque.js foi carregado
        console.log('\n=== SCRIPTS CARREGADOS ===');
        const scripts = Array.from(document.scripts);
        const temRuptura = scripts.some(s => s.textContent.includes('RupturaEstoqueManager'));
        console.log(`Script ruptura-estoque.js: ${temRuptura ? 'CARREGADO' : 'NÃO CARREGADO'}`);
        
        console.log('\n🔍 DEBUG COMPLETO - Verifique os resultados acima');
        
    }, 2000); // Aguardar 2 segundos para garantir
});