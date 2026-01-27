/**
 * 🎯 CARTEIRA SERVICE LAYER
 * Centralização de lógica de negócio para o módulo de carteira
 * Data: 22/07/2025
 * 
 * Objetivo: Reduzir redundâncias e melhorar manutenibilidade
 */

const CarteiraService = {
    
    // Cache de dados com TTL (Time To Live)
    cache: {
        data: {},
        ttl: 5 * 60 * 1000, // 5 minutos
        
        set(key, value) {
            this.data[key] = {
                value: value,
                timestamp: Date.now()
            };
        },
        
        get(key) {
            const item = this.data[key];
            if (!item) return null;
            
            if (Date.now() - item.timestamp > this.ttl) {
                delete this.data[key];
                return null;
            }
            
            return item.value;
        },
        
        clear(pattern) {
            if (pattern) {
                Object.keys(this.data).forEach(key => {
                    if (key.includes(pattern)) {
                        delete this.data[key];
                    }
                });
            } else {
                this.data = {};
            }
        }
    },
    
    // 🔄 FUNÇÕES DE RECÁLCULO DE ESTOQUE (unificadas)
    async recalcularEstoque(itemId, dataExpedicao, callback) {
        try {
            const response = await fetch(`/carteira/api/item/${itemId}/recalcular-estoques`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ data_expedicao: dataExpedicao })
            });
            
            if (!response.ok) {
                throw new Error(`Erro ao recalcular estoques: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Limpar cache relacionado
            this.cache.clear(`estoque_${itemId}`);
            
            if (callback) {
                callback(data);
            }
            
            return data;
            
        } catch (error) {
            console.error('❌ Erro ao recalcular estoques:', error);
            throw error;
        }
    },
    
    // 📊 VALIDAÇÕES CENTRALIZADAS
    validacoes: {
        
        // Validar datas logísticas
        datasLogisticas(expedicao, agendamento) {
            if (!expedicao || !agendamento) return { valido: true };
            
            const dataExp = new Date(expedicao);
            const dataAgend = new Date(agendamento);
            
            if (dataExp > dataAgend) {
                return {
                    valido: false,
                    erro: 'Data de expedição não pode ser posterior ao agendamento'
                };
            }
            
            // Validar se não é data passada
            const hoje = new Date();
            hoje.setHours(0, 0, 0, 0);
            
            if (dataExp < hoje) {
                return {
                    valido: false,
                    erro: 'Data de expedição não pode ser no passado'
                };
            }
            
            return { valido: true };
        },
        
        // Validar quantidade
        quantidade(qtdNova, qtdMax) {
            const qtd = parseFloat(qtdNova) || 0;
            const max = parseFloat(qtdMax) || 0;
            
            if (qtd < 0) {
                return {
                    valido: false,
                    erro: 'Quantidade não pode ser negativa'
                };
            }
            
            if (qtd > max) {
                return {
                    valido: false,
                    erro: `Quantidade máxima permitida: ${max}`
                };
            }
            
            return { valido: true };
        },
        
        // Validar lead time para supply chain
        leadTime(dataExpedicao, codProduto) {
            // TODO: Implementar validação de lead time baseado no produto
            // Por enquanto, validação básica de 2 dias úteis
            const hoje = new Date();
            const dataExp = new Date(dataExpedicao);
            const diffDias = Math.ceil((dataExp - hoje) / (1000 * 60 * 60 * 24));
            
            if (diffDias < 2) {
                return {
                    valido: false,
                    erro: 'Lead time mínimo de 2 dias úteis'
                };
            }
            
            return { valido: true };
        }
    },
    
    // 🔄 TOGGLE GENÉRICO (unificado)
    toggleCheckboxes(containerSelector, masterCheckbox = null) {
        const container = document.querySelector(containerSelector);
        if (!container) return;
        
        const checkboxes = container.querySelectorAll('input[type="checkbox"]:not(:disabled)');
        
        if (masterCheckbox) {
            checkboxes.forEach(cb => {
                if (cb !== masterCheckbox) {
                    cb.checked = masterCheckbox.checked;
                }
            });
        } else {
            // Toggle individual
            checkboxes.forEach(cb => cb.checked = !cb.checked);
        }
        
        // Disparar evento change para atualizar contadores
        checkboxes.forEach(cb => {
            const event = new Event('change', { bubbles: true });
            cb.dispatchEvent(event);
        });
    },
    
    // 📦 CARREGAMENTO DE DADOS COM CACHE
    async carregarDados(url, opcoes = {}) {
        const cacheKey = opcoes.cacheKey || url;
        
        // Verificar cache primeiro
        if (!opcoes.forceRefresh) {
            const cached = this.cache.get(cacheKey);
            if (cached) {
                console.log(`📦 Dados do cache: ${cacheKey}`);
                return cached;
            }
        }
        
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...opcoes.headers
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Armazenar no cache
            if (opcoes.useCache !== false) {
                this.cache.set(cacheKey, data);
            }
            
            return data;
            
        } catch (error) {
            console.error(`❌ Erro ao carregar dados de ${url}:`, error);
            throw error;
        }
    },
    
    // 💾 SALVAMENTO COM FEEDBACK
    async salvarAlteracao(url, dados, opcoes = {}) {
        const feedback = opcoes.feedback !== false;
        let elementoFeedback = null;
        
        if (feedback && opcoes.elemento) {
            elementoFeedback = opcoes.elemento;
            elementoFeedback.classList.add('salvando');
        }
        
        try {
            const response = await fetch(url, {
                method: opcoes.method || 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...opcoes.headers
                },
                body: JSON.stringify(dados)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            // Feedback visual de sucesso
            if (elementoFeedback) {
                elementoFeedback.classList.remove('salvando');
                elementoFeedback.classList.add('salvo');
                setTimeout(() => {
                    elementoFeedback.classList.remove('salvo');
                }, 2000);
            }
            
            // Limpar cache relacionado
            if (opcoes.clearCache) {
                this.cache.clear(opcoes.clearCache);
            }
            
            return result;
            
        } catch (error) {
            console.error(`❌ Erro ao salvar:`, error);
            
            // Feedback visual de erro
            if (elementoFeedback) {
                elementoFeedback.classList.remove('salvando');
                elementoFeedback.classList.add('erro');
                setTimeout(() => {
                    elementoFeedback.classList.remove('erro');
                }, 3000);
            }
            
            throw error;
        }
    },
    
    // 📊 CÁLCULOS CENTRALIZADOS
    calculos: {
        
        // Calcular totais de itens selecionados
        totaisItens(checkboxSelector) {
            const checkboxes = document.querySelectorAll(`${checkboxSelector}:checked`);
            let totalQtd = 0;
            let totalValor = 0;
            let totalPeso = 0;
            let totalPallets = 0;
            
            checkboxes.forEach(checkbox => {
                const row = checkbox.closest('tr');
                if (!row) return;
                
                // Buscar inputs de quantidade
                const qtdInput = row.querySelector('input[type="number"]');
                const qtd = parseFloat(qtdInput?.value || 0);
                
                // Buscar dados do row
                const preco = parseFloat(row.dataset.preco || 0);
                const pesoUnit = parseFloat(row.dataset.pesoUnit || 0);
                const palletUnit = parseFloat(row.dataset.palletUnit || 0);
                
                totalQtd += qtd;
                totalValor += qtd * preco;
                totalPeso += qtd * pesoUnit;
                totalPallets += qtd * palletUnit;
            });
            
            return {
                quantidade: totalQtd,
                valor: totalValor,
                peso: totalPeso,
                pallets: totalPallets,
                itens: checkboxes.length
            };
        },
        
        // Calcular proporção para divisão
        proporcaoDivisao(qtdUtilizada, qtdOriginal) {
            if (!qtdOriginal || qtdOriginal === 0) return 0;
            return qtdUtilizada / qtdOriginal;
        }
    },
    
    // 🔔 NOTIFICAÇÕES MELHORADAS
    notificar(mensagem, tipo = 'info', duracao = 3000) {
        // Por enquanto, usar console + futura implementação de toast
        const prefixo = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        };
        
        console.log(`${prefixo[tipo] || ''} ${mensagem}`);
        
        // TODO: Implementar sistema de toast notifications
        // Por enquanto, fallback para alert apenas em erros críticos
        if (tipo === 'error' && !window.suppressAlerts) {
            alert(mensagem);
        }
    },
    
    // 🔍 FUNÇÕES DE BUSCA E FILTRO
    filtros: {
        
        // Filtrar itens por status de estoque
        porStatusEstoque(itens, status) {
            return itens.filter(item => {
                switch (status) {
                    case 'disponivel':
                        return item.estoque_d0 >= item.qtd_saldo_produto_pedido;
                    case 'parcial':
                        return item.estoque_d0 > 0 && item.estoque_d0 < item.qtd_saldo_produto_pedido;
                    case 'indisponivel':
                        return item.estoque_d0 === 0;
                    default:
                        return true;
                }
            });
        },
        
        // Filtrar por data de expedição
        porDataExpedicao(itens, dataInicio, dataFim) {
            return itens.filter(item => {
                if (!item.expedicao) return false;
                const dataItem = new Date(item.expedicao);
                return dataItem >= dataInicio && dataItem <= dataFim;
            });
        }
    },
    
    // 🎯 HELPERS ÚTEIS
    helpers: {
        
        // Formatar data para input
        formatarDataInput(data) {
            if (!data) return '';
            const d = new Date(data);
            return d.toISOString().split('T')[0];
        },
        
        // Formatar data para exibição
        formatarDataExibicao(data) {
            if (!data) return '';
            const d = new Date(data);
            return d.toLocaleDateString('pt-BR');
        },
        
        // Formatar moeda
        formatarMoeda(valor) {
            return new Intl.NumberFormat('pt-BR', {
                style: 'currency',
                currency: 'BRL'
            }).format(valor || 0);
        },
        
        // Debounce para otimizar chamadas
        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }
    }
};

// Tornar disponível globalmente
window.CarteiraService = CarteiraService;

// Adicionar estilos para feedback visual
// Using CSS custom properties for theme-aware colors
const style = document.createElement('style');
style.textContent = `
    .salvando {
        background-color: var(--semantic-warning-subtle, hsla(45 100% 50% / 0.15)) !important;
        transition: background-color 0.3s;
    }

    .salvo {
        background-color: var(--semantic-success-subtle, hsla(145 30% 50% / 0.15)) !important;
        transition: background-color 0.3s;
    }

    .erro {
        background-color: var(--semantic-danger-subtle, hsla(0 30% 50% / 0.15)) !important;
        transition: background-color 0.3s;
    }
`;
document.head.appendChild(style);

console.log('✅ CarteiraService carregado com sucesso');