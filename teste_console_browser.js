// COLE ESTE CÓDIGO NO CONSOLE DO NAVEGADOR (F12)
// Com o modal de separações aberto

console.log("========== TESTE DOS BOTÕES DO PORTAL ==========");

// 1. Verificar se o objeto existe
if (window.modalSeparacoes) {
    console.log("✅ Modal de Separações carregado");
    
    // 2. Verificar se tem separações
    if (window.modalSeparacoes.separacoes && window.modalSeparacoes.separacoes.length > 0) {
        console.log(`✅ ${window.modalSeparacoes.separacoes.length} separações encontradas`);
        
        // 3. Verificar dados das separações
        window.modalSeparacoes.separacoes.forEach((sep, index) => {
            console.log(`\n📦 Separação ${index + 1}:`);
            console.log(`   Lote ID: ${sep.separacao_lote_id}`);
            console.log(`   Status: ${sep.status}`);
            console.log(`   Protocolo Portal: ${sep.protocolo_portal || '❌ NÃO EXISTE'}`);
            
            // Verificar se o campo existe
            if ('protocolo_portal' in sep) {
                console.log("   ✅ Campo protocolo_portal EXISTE no objeto");
            } else {
                console.log("   ❌ Campo protocolo_portal NÃO EXISTE no objeto");
            }
        });
        
        // 4. Verificar se os botões foram renderizados
        const botoesAgendar = document.querySelectorAll('button[onclick*="agendarNoPortal"]');
        const botoesVerificar = document.querySelectorAll('button[onclick*="verificarPortal"]');
        
        console.log(`\n🔘 Botões encontrados no DOM:`);
        console.log(`   Botões "Agendar no Portal": ${botoesAgendar.length}`);
        console.log(`   Botões "Verificar Portal": ${botoesVerificar.length}`);
        
        if (botoesAgendar.length === 0 && botoesVerificar.length === 0) {
            console.log("   ❌ NENHUM BOTÃO FOI RENDERIZADO!");
            console.log("   📝 Possíveis causas:");
            console.log("      1. O JavaScript não foi atualizado (limpe o cache com Ctrl+F5)");
            console.log("      2. Erro na renderização (verifique erros no console)");
            console.log("      3. Template não atualizado");
        } else {
            console.log("   ✅ BOTÕES RENDERIZADOS COM SUCESSO!");
        }
        
        // 5. Testar se as funções existem
        console.log(`\n⚙️ Funções do Portal:`);
        if (typeof window.modalSeparacoes.agendarNoPortal === 'function') {
            console.log("   ✅ Função agendarNoPortal existe");
        } else {
            console.log("   ❌ Função agendarNoPortal NÃO existe");
        }
        
        if (typeof window.modalSeparacoes.verificarPortal === 'function') {
            console.log("   ✅ Função verificarPortal existe");
        } else {
            console.log("   ❌ Função verificarPortal NÃO existe");
        }
        
    } else {
        console.log("❌ Nenhuma separação carregada");
        console.log("   Tente fechar e abrir o modal novamente");
    }
} else {
    console.log("❌ Modal de Separações NÃO está carregado");
    console.log("   Possíveis causas:");
    console.log("   1. A página não foi recarregada após as mudanças");
    console.log("   2. Erro no JavaScript (verifique a aba Console)");
    console.log("   3. Cache do navegador (pressione Ctrl+F5)");
}

console.log("\n========== FIM DO TESTE ==========");
console.log("Se os botões não aparecem, envie este log!");