/**
 * lista-checkboxes.js — Gerenciamento de checkboxes e selecao de pedidos
 * Extraido de lista_pedidos.html (linhas 1538-1702)
 */

function toggleAll(source) {
    const checkboxes = document.querySelectorAll('input[name="separacao_lote_ids"]:not([disabled])');
    for (let checkbox of checkboxes) {
        checkbox.checked = source.checked;
    }
    updateSelectedCount();
    updateCotarButton();
}

function updateSelectedCount() {
    const selectedCheckboxes = document.querySelectorAll('input[name="separacao_lote_ids"]:checked');
    const countElement = document.getElementById('selected-count');
    const count = selectedCheckboxes.length;

    if (countElement) {
        if (count > 0) {
            countElement.textContent = count + ' pedido(s) selecionado(s)';
            countElement.style.display = 'inline';
        } else {
            countElement.style.display = 'none';
        }
    }
}

function updateCotarButton() {
    const selectedCheckboxes = document.querySelectorAll('input[name="separacao_lote_ids"]:checked');
    const cotarButton = document.getElementById('btnCotarFrete');
    const cotacaoManualButton = document.getElementById('btnCotacaoManual');
    const embarqueFOBButton = document.getElementById('btnEmbarqueFOB');
    const verMapaButton = document.getElementById('btnVerMapa');
    const count = selectedCheckboxes.length;

    if (cotarButton) {
        if (count > 0) {
            cotarButton.disabled = false;
            cotarButton.innerHTML = '<i class="fas fa-calculator"></i> Cotar Frete (' + count + ')';
            cotarButton.classList.remove('btn-secondary');
            cotarButton.classList.add('btn-success');
        } else {
            cotarButton.disabled = true;
            cotarButton.innerHTML = '<i class="fas fa-calculator"></i> Cotar Frete';
            cotarButton.classList.remove('btn-success');
            cotarButton.classList.add('btn-secondary');
        }
    }

    if (cotacaoManualButton) {
        cotacaoManualButton.disabled = count === 0;
        if (count > 0) {
            cotacaoManualButton.innerHTML = '<i class="fas fa-edit"></i> Cotacao Manual (' + count + ')';
        } else {
            cotacaoManualButton.innerHTML = '<i class="fas fa-edit"></i> Cotacao Manual';
        }
    }

    if (embarqueFOBButton) {
        embarqueFOBButton.disabled = count === 0;
        if (count > 0) {
            embarqueFOBButton.innerHTML = '<i class="fas fa-ship"></i> Embarque FOB (' + count + ')';
        } else {
            embarqueFOBButton.innerHTML = '<i class="fas fa-ship"></i> Embarque FOB';
        }
    }

    if (verMapaButton) {
        verMapaButton.disabled = count === 0;
        if (count > 0) {
            verMapaButton.innerHTML = '<i class="fas fa-map-marked-alt"></i> Ver no Mapa (' + count + ')';
        } else {
            verMapaButton.innerHTML = '<i class="fas fa-map-marked-alt"></i> Ver no Mapa';
        }
    }
}

function abrirCotacaoManual() {
    const selectedCheckboxes = document.querySelectorAll('input[name="separacao_lote_ids"]:checked');

    if (selectedCheckboxes.length === 0) {
        alert('Por favor, selecione pelo menos um pedido para cotacao manual.');
        return false;
    }

    const pedidoIds = Array.from(selectedCheckboxes).map(cb => cb.value);

    const form = document.createElement('form');
    form.method = 'POST';
    form.action = window.PEDIDOS_URLS.cotacaoManual;

    const csrfToken = document.querySelector('input[name="csrf_token"]').value;
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrf_token';
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);

    pedidoIds.forEach(id => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'separacao_lote_ids';
        input.value = id;
        form.appendChild(input);
    });

    document.body.appendChild(form);
    form.submit();
}

document.addEventListener('DOMContentLoaded', function() {
    const individualCheckboxes = document.querySelectorAll('input[name="separacao_lote_ids"]');

    individualCheckboxes.forEach(function(checkbox) {
        checkbox.addEventListener('change', function() {
            updateSelectedCount();
            updateCotarButton();

            const selectAllCheckbox = document.querySelector('thead input[type="checkbox"]');
            const enabledCheckboxes = document.querySelectorAll('input[name="separacao_lote_ids"]:not([disabled])');
            const checkedCheckboxes = document.querySelectorAll('input[name="separacao_lote_ids"]:checked');

            if (selectAllCheckbox) {
                selectAllCheckbox.checked = enabledCheckboxes.length > 0 && checkedCheckboxes.length === enabledCheckboxes.length;
            }
        });
    });

    updateSelectedCount();
    updateCotarButton();

    const searchInput = document.getElementById('quick-search');
    if (searchInput) {
        searchInput.addEventListener('keyup', function() {
            const filter = this.value.toLowerCase();
            const rows = document.querySelectorAll('tbody tr');
            rows.forEach(function(row) {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            });
        });
    }
});
