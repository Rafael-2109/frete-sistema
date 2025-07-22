
/**
 * Mostra badge de status da confirmação do agendamento
 */
function mostrarBadgeConfirmacao(confirmado) {
    const badge = document.getElementById('badge-status-agenda');
    
    if (confirmado) {
        badge.textContent = '✅ Confirmado';
        badge.className = 'badge bg-success ms-2';
        badge.style.display = 'inline';
    } else {
        badge.textContent = '⏳ Pendente';
        badge.className = 'badge bg-warning ms-2';
        badge.style.display = 'inline';
    }
}
