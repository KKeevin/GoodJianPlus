/**
 * 通用工具函數
 */

// 顯示 Toast 通知
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.textContent = message;
    
    const colors = {
        'success': '#28a745',
        'error': '#dc3545',
        'warning': '#ffc107',
        'info': '#17a2b8'
    };
    
    toast.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 1060;
        transform: translateX(100%);
        transition: transform 0.3s ease;
        background: ${colors[type] || colors.info};
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => toast.style.transform = 'translateX(0)', 100);
    
    setTimeout(() => {
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// HTML 轉義函數
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 渲染評分星星
function renderRatingStars(container = document) {
    container.querySelectorAll('.stars[data-rating]').forEach(starsDiv => {
        const rating = parseFloat(starsDiv.dataset.rating);
        if (rating && rating > 0) {
            const fullStars = Math.floor(rating);
            const hasHalfStar = (rating - fullStars) >= 0.5;
            let starsHtml = '';
            
            for (let i = 1; i <= 5; i++) {
                if (i <= fullStars) {
                    starsHtml += '★';
                } else if (i === fullStars + 1 && hasHalfStar) {
                    starsHtml += '★';
                } else {
                    starsHtml += '☆';
                }
            }
            
            const placeholder = starsDiv.querySelector('.rating-stars-placeholder');
            if (placeholder) {
                placeholder.outerHTML = starsHtml;
            } else {
                starsDiv.innerHTML = starsHtml;
            }
        } else {
            const placeholder = starsDiv.querySelector('.rating-stars-placeholder');
            if (placeholder) {
                placeholder.outerHTML = '☆☆☆☆☆';
            } else {
                starsDiv.innerHTML = '☆☆☆☆☆';
            }
        }
    });
}

// 獲取 CSRF Token
function getCsrfToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
}

// 格式化數字（添加千分位）
function formatNumber(num) {
    return num.toLocaleString('zh-TW');
}

// 格式化價格（添加千位分隔符）
function formatPrice(price) {
    if (typeof price === 'string') {
        price = parseFloat(price.replace(/[^\d.-]/g, ''));
    }
    if (isNaN(price)) return 'NT$0';
    return 'NT$' + Math.round(price).toLocaleString('zh-TW');
}

// 格式化頁面中所有帶有 data-price 屬性的價格元素
function formatAllPrices(container = document) {
    // 查找所有帶有 data-price 屬性的元素
    container.querySelectorAll('[data-price]').forEach(priceEl => {
        const price = parseFloat(priceEl.dataset.price);
        if (!isNaN(price) && price >= 0) {
            const formattedPrice = Math.round(price).toLocaleString('zh-TW');
            // 檢查是否已經格式化過（包含逗號）
            const currentText = priceEl.textContent.trim();
            if (!currentText.includes(',')) {
                // 如果當前文本不包含逗號，說明還沒格式化
                if (currentText.startsWith('NT$')) {
                    priceEl.textContent = 'NT$' + formattedPrice;
                } else if (currentText.startsWith('NT')) {
                    priceEl.textContent = 'NT$' + formattedPrice;
                } else {
                    priceEl.textContent = 'NT$' + formattedPrice;
                }
            }
        }
    });
}

// 防抖函數
function debounce(func, wait) {
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

