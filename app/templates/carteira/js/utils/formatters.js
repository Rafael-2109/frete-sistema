/**
 * 📊 MÓDULO CENTRALIZADO DE FORMATAÇÃO
 * Centraliza todas as funções de formatação para evitar redundância
 * e garantir consistência em toda a aplicação
 */

(function(window) {
    'use strict';

    const Formatters = {
        /**
         * Formata valor monetário em Real Brasileiro
         * @param {number} valor - Valor a ser formatado
         * @returns {string} Valor formatado como moeda
         */
        moeda: function(valor) {
            if (!valor && valor !== 0) return 'R$ 0,00';
            return new Intl.NumberFormat('pt-BR', {
                style: 'currency',
                currency: 'BRL'
            }).format(valor);
        },

        /**
         * Formata peso em quilogramas
         * @param {number} peso - Peso em kg
         * @returns {string} Peso formatado
         */
        peso: function(peso) {
            if (!peso && peso !== 0) return '0 kg';
            // Usar 1 casa decimal para pesos
            return `${parseFloat(peso).toFixed(1).replace('.', ',')} kg`;
        },

        /**
         * Formata quantidade de pallets
         * @param {number} pallet - Quantidade de pallets
         * @returns {string} Pallets formatados
         */
        pallet: function(pallet) {
            if (!pallet && pallet !== 0) return '0 plt';
            // Usar 2 casas decimais para pallets
            return `${parseFloat(pallet).toFixed(2).replace('.', ',')} plt`;
        },

        /**
         * Formata quantidade inteira com separador de milhar
         * @param {number} qtd - Quantidade
         * @returns {string} Quantidade formatada
         */
        quantidade: function(qtd) {
            if (!qtd && qtd !== 0) return '0';
            // Quantidade inteira com separador de milhar
            return Math.floor(qtd).toLocaleString('pt-BR');
        },

        /**
         * Formata data para formato brasileiro dd/mm/yyyy
         * @param {string|Date} data - Data em qualquer formato
         * @returns {string|null} Data formatada ou null
         */
        data: function(data) {
            if (!data) return null;
            
            // Se já está no formato dd/mm/yyyy, retornar como está
            if (typeof data === 'string' && data.match(/^\d{2}\/\d{2}\/\d{4}$/)) {
                return data;
            }
            
            // Se está no formato yyyy-mm-dd
            if (typeof data === 'string' && data.match(/^\d{4}-\d{2}-\d{2}$/)) {
                const [ano, mes, dia] = data.split('-');
                return `${dia}/${mes}/${ano}`;
            }
            
            // Se é string ISO com hora, pegar apenas a data
            if (typeof data === 'string' && data.includes('T')) {
                const dataStr = data.split('T')[0];
                const [ano, mes, dia] = dataStr.split('-');
                return `${dia}/${mes}/${ano}`;
            }
            
            // Se é um objeto Date ou string de data
            try {
                const dateObj = new Date(data);
                if (!isNaN(dateObj.getTime())) {
                    const dia = String(dateObj.getDate()).padStart(2, '0');
                    const mes = String(dateObj.getMonth() + 1).padStart(2, '0');
                    const ano = dateObj.getFullYear();
                    return `${dia}/${mes}/${ano}`;
                }
            } catch (e) {
                console.warn('Erro ao formatar data:', e);
            }
            
            return null;
        },

        /**
         * Formata número com casas decimais específicas
         * @param {number} valor - Valor a formatar
         * @param {number} decimais - Número de casas decimais
         * @returns {string} Número formatado
         */
        numero: function(valor, decimais = 2) {
            if (!valor && valor !== 0) return '0';
            return valor.toLocaleString('pt-BR', {
                minimumFractionDigits: decimais,
                maximumFractionDigits: decimais
            });
        },

        /**
         * Formata porcentagem
         * @param {number} valor - Valor decimal (0.15 = 15%)
         * @param {number} decimais - Número de casas decimais
         * @returns {string} Porcentagem formatada
         */
        porcentagem: function(valor, decimais = 1) {
            if (!valor && valor !== 0) return '0%';
            return `${(valor * 100).toFixed(decimais).replace('.', ',')}%`;
        },

        /**
         * Formata CNPJ
         * @param {string} cnpj - CNPJ sem formatação
         * @returns {string} CNPJ formatado
         */
        cnpj: function(cnpj) {
            if (!cnpj) return '';
            // Remove caracteres não numéricos
            cnpj = cnpj.replace(/\D/g, '');
            // Formata: XX.XXX.XXX/XXXX-XX
            if (cnpj.length === 14) {
                return cnpj.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
            }
            return cnpj;
        },

        /**
         * Formata CEP
         * @param {string} cep - CEP sem formatação
         * @returns {string} CEP formatado
         */
        cep: function(cep) {
            if (!cep) return '';
            // Remove caracteres não numéricos
            cep = cep.replace(/\D/g, '');
            // Formata: XXXXX-XXX
            if (cep.length === 8) {
                return cep.replace(/(\d{5})(\d{3})/, '$1-$2');
            }
            return cep;
        },

        /**
         * Formata telefone
         * @param {string} telefone - Telefone sem formatação
         * @returns {string} Telefone formatado
         */
        telefone: function(telefone) {
            if (!telefone) return '';
            // Remove caracteres não numéricos
            telefone = telefone.replace(/\D/g, '');
            // Formata celular: (XX) XXXXX-XXXX
            if (telefone.length === 11) {
                return telefone.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
            }
            // Formata fixo: (XX) XXXX-XXXX
            if (telefone.length === 10) {
                return telefone.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
            }
            return telefone;
        }
    };

    // Manter compatibilidade com implementações antigas
    // Isso permite migração gradual sem quebrar código existente
    const CompatibilityWrapper = {
        formatarMoeda: Formatters.moeda,
        formatarPeso: Formatters.peso,
        formatarPallet: Formatters.pallet,
        formatarQuantidade: Formatters.quantidade,
        formatarData: Formatters.data,
        formatarNumero: Formatters.numero,
        formatarPorcentagem: Formatters.porcentagem,
        formatarCNPJ: Formatters.cnpj,
        formatarCEP: Formatters.cep,
        formatarTelefone: Formatters.telefone
    };

    // Exportar para uso global
    window.Formatters = Formatters;
    window.FormattersCompat = CompatibilityWrapper;

    // Para debug e testes
    console.log('✅ Módulo de Formatação carregado: window.Formatters disponível');

})(window);