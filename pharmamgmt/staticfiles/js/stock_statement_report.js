/**
 * Stock Statement Report JavaScript
 * Handles interactive features, AJAX requests, and UI enhancements
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeStockReport();
});

function initializeStockReport() {
    // Initialize search functionality
    initializeSearch();
    
    // Initialize keyboard shortcuts
    initializeKeyboardShortcuts();
    
    // Initialize tooltips
    initializeTooltips();
    
    // Auto-save filter preferences
    loadFilterPreferences();
    
    console.log('Stock Statement Report initialized');
}

function initializeSearch() {
    const searchInput = document.getElementById('search');
    if (searchInput) {
        // Prevent auto-submit on input - user must click Apply Filters button
        // This prevents page reload while typing
        searchInput.addEventListener('keydown', function(e) {
            // Prevent Enter key from submitting form
            if (e.key === 'Enter') {
                e.preventDefault();
            }
        });
    }
}

function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + F: Focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
            e.preventDefault();
            const searchInput = document.getElementById('search');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
        
        // Ctrl/Cmd + P: Print report
        if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
            e.preventDefault();
            printReport();
        }
        
        // Ctrl/Cmd + Q: Export PDF
        if ((e.ctrlKey || e.metaKey) && e.key === 'q') {
            e.preventDefault();
            const pdfLink = document.querySelector('a[href*="export_stock_statement_pdf"]');
            if (pdfLink) {
                window.open(pdfLink.href, '_blank');
            } else {
                exportReport('pdf');
            }
        }
        
        // Ctrl/Cmd + E: Export Excel
        if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
            e.preventDefault();
            exportReport('excel');
        }
        
        // Escape: Close modals
        if (e.key === 'Escape') {
            closeBatchModal();
        }
    });
}

function initializeTooltips() {
    // Add tooltips to action buttons
    const actionButtons = document.querySelectorAll('.btn-action');
    actionButtons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            const title = this.getAttribute('title');
            if (title) {
                showTooltip(this, title);
            }
        });
        
        button.addEventListener('mouseleave', function() {
            hideTooltip();
        });
    });
}

function showTooltip(element, text) {
    // Remove existing tooltip
    hideTooltip();
    
    const tooltip = document.createElement('div');
    tooltip.className = 'custom-tooltip';
    tooltip.textContent = text;
    tooltip.style.cssText = `
        position: absolute;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        z-index: 1000;
        pointer-events: none;
        white-space: nowrap;
    `;
    
    document.body.appendChild(tooltip);
    
    const rect = element.getBoundingClientRect();
    tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = (rect.top - tooltip.offsetHeight - 5) + 'px';
}

function hideTooltip() {
    const tooltip = document.querySelector('.custom-tooltip');
    if (tooltip) {
        tooltip.remove();
    }
}

function clearFilters() {
    // Clear all form inputs
    const form = document.getElementById('filtersForm');
    const inputs = form.querySelectorAll('input, select');
    
    inputs.forEach(input => {
        if (input.type === 'text' || input.type === 'date') {
            input.value = '';
        } else if (input.type === 'select-one') {
            input.selectedIndex = 0;
        }
    });
    
    // Submit form to apply cleared filters
    form.submit();
}

function exportReport(format) {
    showLoading();
    
    // Get current URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    urlParams.set('export', format);
    
    // Create download URL
    const exportUrl = window.location.pathname + '?' + urlParams.toString();
    
    if (format === 'pdf') {
        showNotification('Downloading PDF...', 'info');
        
        fetch(exportUrl)
            .then(response => response.blob())
            .then(blob => {
                // Create download link
                const downloadUrl = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = downloadUrl;
                link.download = `stock_statement_${new Date().toISOString().slice(0, 10)}.pdf`;
                link.click();
                
                showNotification('PDF downloaded successfully!', 'success');
                
                // Auto open after download
                setTimeout(() => {
                    window.open(downloadUrl, '_blank');
                    window.URL.revokeObjectURL(downloadUrl);
                }, 1000);
                
                hideLoading();
            })
            .catch(error => {
                console.error('Export error:', error);
                showNotification('Opening PDF in new tab...', 'info');
                // Fallback to direct open
                window.open(exportUrl, '_blank');
                hideLoading();
            });
        
    } else if (format === 'excel') {
        showNotification('Generating Excel file...', 'info');
        
        window.location.href = exportUrl;
        
        setTimeout(() => {
            showNotification('Excel file downloaded', 'success');
            hideLoading();
        }, 1500);
    }
}

function printReport() {
    // Add print footer with timestamp
    const printFooter = document.createElement('div');
    printFooter.className = 'print-footer';
    printFooter.innerHTML = `
        <strong>Report Generated:</strong> ${new Date().toLocaleString('en-IN', { 
            day: '2-digit', 
            month: '2-digit', 
            year: 'numeric', 
            hour: '2-digit', 
            minute: '2-digit' 
        })} | 
        <strong>System:</strong> Pharma Management System
    `;
    
    document.querySelector('.stock-statement-container').appendChild(printFooter);
    
    // Print
    setTimeout(() => {
        window.print();
        // Remove footer after print
        setTimeout(() => printFooter.remove(), 500);
    }, 100);
}

function viewBatchDetails(productId) {
    showLoading();
    
    fetch(`/reports/stock-statement/batch-details/${productId}/`, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            displayBatchDetails(data);
        } else {
            showNotification(data.error || 'Failed to load batch details', 'error');
        }
    })
    .catch(error => {
        console.error('Batch details error:', error);
        showNotification('Failed to load batch details. Please try again.', 'error');
    })
    .finally(() => {
        hideLoading();
    });
}

function displayBatchDetails(data) {
    const modalBody = document.getElementById('batchModalBody');
    
    let html = `
        <div class="batch-details">
            <div class="product-header">
                <h4>${data.product_name}</h4>
                <p class="product-company">${data.product_company}</p>
            </div>
            
            <div class="batch-table-container">
                <table class="batch-table">
                    <thead>
                        <tr>
                            <th>Batch No</th>
                            <th>Expiry</th>
                            <th>Stock</th>
                            <th>Purchased</th>
                            <th>Sold</th>
                            <th>Returns</th>
                            <th>MRP</th>
                            <th>Rate A</th>
                            <th>Rate B</th>
                            <th>Rate C</th>
                        </tr>
                    </thead>
                    <tbody>
    `;
    
    if (data.batches && data.batches.length > 0) {
        data.batches.forEach(batch => {
            html += `
                <tr>
                    <td class="batch-no">${batch.batch_no || 'N/A'}</td>
                    <td class="expiry">${batch.expiry || 'N/A'}</td>
                    <td class="stock ${batch.stock <= 0 ? 'zero' : batch.stock < 10 ? 'low' : 'normal'}">
                        ${batch.stock}
                    </td>
                    <td class="purchased">${batch.purchased}</td>
                    <td class="sold">${batch.sold}</td>
                    <td class="returns">
                        <span class="return-in">+${batch.sales_returns}</span>
                        <span class="return-out">-${batch.purchase_returns}</span>
                    </td>
                    <td class="mrp">₹${parseFloat(batch.mrp || 0).toFixed(2)}</td>
                    <td class="rate">₹${parseFloat(batch.rate_A || 0).toFixed(2)}</td>
                    <td class="rate">₹${parseFloat(batch.rate_B || 0).toFixed(2)}</td>
                    <td class="rate">₹${parseFloat(batch.rate_C || 0).toFixed(2)}</td>
                </tr>
            `;
        });
    } else {
        html += `
            <tr>
                <td colspan="10" class="no-batches">
                    <div class="no-data-message">
                        <i class="fas fa-box-open"></i>
                        <p>No batch information available</p>
                    </div>
                </td>
            </tr>
        `;
    }
    
    html += `
                    </tbody>
                </table>
            </div>
        </div>
        
        <style>
            .batch-details {
                font-family: inherit;
            }
            
            .product-header {
                margin-bottom: 1rem;
                padding-bottom: 1rem;
                border-bottom: 1px solid var(--border-color);
            }
            
            .product-header h4 {
                margin: 0 0 0.5rem 0;
                color: var(--text-primary);
                font-size: 1.1rem;
            }
            
            .product-company {
                margin: 0;
                color: var(--text-secondary);
                font-size: 0.9rem;
            }
            
            .batch-table-container {
                overflow-x: auto;
            }
            
            .batch-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.85rem;
            }
            
            .batch-table th {
                background-color: var(--bg-tertiary);
                color: var(--text-primary);
                font-weight: 600;
                padding: 0.75rem 0.5rem;
                text-align: left;
                border-bottom: 2px solid var(--border-color);
                white-space: nowrap;
            }
            
            .batch-table td {
                padding: 0.75rem 0.5rem;
                border-bottom: 1px solid var(--border-light);
                vertical-align: middle;
            }
            
            .batch-table tr:hover {
                background-color: var(--bg-secondary);
            }
            
            .batch-no {
                font-weight: 600;
                color: var(--text-primary);
            }
            
            .stock.zero {
                color: var(--danger-color);
                font-weight: 600;
            }
            
            .stock.low {
                color: var(--warning-color);
                font-weight: 600;
            }
            
            .stock.normal {
                color: var(--success-color);
                font-weight: 600;
            }
            
            .returns {
                display: flex;
                gap: 0.5rem;
                font-size: 0.8rem;
            }
            
            .return-in {
                color: var(--success-color);
            }
            
            .return-out {
                color: var(--danger-color);
            }
            
            .no-batches {
                text-align: center;
                padding: 2rem;
            }
            
            .no-batches .no-data-message i {
                font-size: 2rem;
                color: var(--text-muted);
                margin-bottom: 0.5rem;
            }
            
            .no-batches .no-data-message p {
                color: var(--text-muted);
                margin: 0;
            }
        </style>
    `;
    
    modalBody.innerHTML = html;
    document.getElementById('batchModal').style.display = 'block';
}

function closeBatchModal() {
    document.getElementById('batchModal').style.display = 'none';
}

function viewProductDetail(productId) {
    // Navigate to product detail page
    window.open(`/products/${productId}/`, '_blank');
}

function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => notification.remove());
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas fa-${getNotificationIcon(type)}"></i>
            <span>${message}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        max-width: 400px;
        background: ${getNotificationColor(type)};
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        animation: slideInRight 0.3s ease;
    `;
    
    // Add to document
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }
    }, 5000);
}

function getNotificationIcon(type) {
    const icons = {
        success: 'check-circle',
        error: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    return icons[type] || icons.info;
}

function getNotificationColor(type) {
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#06b6d4'
    };
    return colors[type] || colors.info;
}

function saveFilterPreferences() {
    const form = document.getElementById('filtersForm');
    const formData = new FormData(form);
    const preferences = {};
    
    for (let [key, value] of formData.entries()) {
        preferences[key] = value;
    }
    
    localStorage.setItem('stockReportFilters', JSON.stringify(preferences));
}

function loadFilterPreferences() {
    try {
        const saved = localStorage.getItem('stockReportFilters');
        if (saved) {
            const preferences = JSON.parse(saved);
            
            Object.keys(preferences).forEach(key => {
                const element = document.querySelector(`[name="${key}"]`);
                if (element && !element.value) {
                    element.value = preferences[key];
                }
            });
        }
    } catch (error) {
        console.warn('Failed to load filter preferences:', error);
    }
}

// Save preferences when form changes
document.addEventListener('change', function(e) {
    if (e.target.closest('#filtersForm')) {
        saveFilterPreferences();
    }
});

// Close modal when clicking outside
document.addEventListener('click', function(e) {
    const modal = document.getElementById('batchModal');
    if (e.target === modal) {
        closeBatchModal();
    }
});

// Add CSS animations
const animationStyles = `
    <style>
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
        
        .notification-content {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        
        .notification-close {
            background: none;
            border: none;
            color: white;
            cursor: pointer;
            padding: 0.25rem;
            border-radius: 0.25rem;
            margin-left: auto;
        }
        
        .notification-close:hover {
            background: rgba(255, 255, 255, 0.2);
        }
    </style>
`;

document.head.insertAdjacentHTML('beforeend', animationStyles);