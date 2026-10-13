/**
 * Expiry Date Formatter for MM-YYYY format
 * Handles automatic formatting and validation of expiry dates
 */

// Format expiry date input to MM-YYYY format
function formatExpiryDate(input) {
    const value = input.value.trim();
    let match = value.match(/^(\d{1,2})[-/](\d{4})$/);

    if (!match && /^\d{6}$/.test(value)) {
        match = [value, value.slice(0, 2), value.slice(2)];
    }

    if (!match && /^\d{4}$/.test(value)) {
        match = [value, value.slice(0, 2), `20${value.slice(2)}`];
    }

    if (!match) return;

    const month = Number(match[1]);
    const year = Number(match[2]);
    if (month >= 1 && month <= 12) {
        input.value = `${String(month).padStart(2, '0')}-${year}`;
    }
}

// Validate MM-YYYY format
function validateExpiryDate(value) {
    if (!value) return { valid: true, message: '' };
    
    const pattern = /^(0[1-9]|1[0-2])-\d{4}$/;
    if (!pattern.test(value)) {
        return {
            valid: false,
            message: 'Please enter expiry in MM-YYYY format (e.g., 12-2025)'
        };
    }
    
    const [month, year] = value.split('-').map(Number);
    
    if (month < 1 || month > 12) {
        return {
            valid: false,
            message: 'Invalid month. Use 01-12.'
        };
    }
    
    const currentYear = new Date().getFullYear();
    if (year < 2000 || year > currentYear + 50) {
        return {
            valid: false,
            message: `Invalid year. Use a year between 2000-${currentYear + 50}.`
        };
    }
    
    return { valid: true, message: '' };
}

// Initialize expiry date formatting for all expiry inputs
function initializeExpiryDateFormatting() {
    // Handle input formatting
    document.addEventListener('input', function(e) {
        if (e.target.classList.contains('expiry') || 
            e.target.name === 'product_expiry' ||
            e.target.id === 'product_expiry') {
            formatExpiryDate(e.target);
        }
    });
    
    // Handle validation on blur
    document.addEventListener('blur', function(e) {
        if (e.target.classList.contains('expiry') || 
            e.target.name === 'product_expiry' ||
            e.target.id === 'product_expiry') {
            formatExpiryDate(e.target);
            const validation = validateExpiryDate(e.target.value);
            if (!validation.valid) {
                e.target.setCustomValidity(validation.message);
                e.target.reportValidity();
            } else {
                e.target.setCustomValidity('');
            }
        }
    });
    
    // Handle Enter key for quick navigation
    document.addEventListener('keypress', function(e) {
        if ((e.target.classList.contains('expiry') || 
             e.target.name === 'product_expiry' ||
             e.target.id === 'product_expiry') && 
            e.key === 'Enter') {
            
            e.preventDefault();
            formatExpiryDate(e.target);
            
            // Move to next input
            const inputs = Array.from(document.querySelectorAll('input, select'));
            const currentIndex = inputs.indexOf(e.target);
            if (currentIndex < inputs.length - 1) {
                inputs[currentIndex + 1].focus();
            }
        }
    });
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeExpiryDateFormatting();
});

// Export functions for manual use
window.formatExpiryDate = formatExpiryDate;
window.validateExpiryDate = validateExpiryDate;
window.initializeExpiryDateFormatting = initializeExpiryDateFormatting;