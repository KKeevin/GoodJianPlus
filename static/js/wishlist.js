/**
 * 收藏列表頁面相關功能
 * 處理收藏商品的切換、移除等功能
 */

(function() {
    'use strict';

    // 切換收藏狀態
    function toggleWishlist(productId) {
        const toggleWishlistUrl = window.WISHLIST_CONFIG?.toggleUrl || '/api/wishlist/toggle/';
        const csrfToken = window.CART_CONFIG?.csrfToken || getCsrfToken();
        
        fetch(toggleWishlistUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `product_id=${productId}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 更新所有相關按鈕的狀態
                updateWishlistButtons(productId, data.is_favorited);
                
                // 只在收藏頁面移除商品卡片（不在商品清單頁移除）
                if (!data.is_favorited && isWishlistPage()) {
                    removeProductCard(productId);
                }
                
                if (typeof showToast === 'function') {
                    showToast(data.message, 'success');
                }
            } else {
                handleWishlistError(data);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (typeof showToast === 'function') {
                showToast('操作失敗，請稍後再試', 'error');
            }
        });
    }

    // 更新收藏按鈕狀態
    function updateWishlistButtons(productId, isFavorited) {
        const buttons = document.querySelectorAll(
            `.wishlist-btn[data-product-id="${productId}"], ` +
            `.wishlist-remove-btn[data-product-id="${productId}"]`
        );
        
        buttons.forEach(btn => {
            // 更新 active 類（控制顏色）
            if (isFavorited) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
            
            // 更新圖標（僅限 wishlist-btn，移除按鈕保持原樣）
            if (!btn.classList.contains('wishlist-remove-btn')) {
                const icon = btn.querySelector('i');
                if (icon) {
                    icon.className = isFavorited ? 'bi bi-heart-fill' : 'bi bi-heart';
                }
            }
        });
    }

    // 檢查是否在收藏頁面
    function isWishlistPage() {
        return window.location.pathname.includes('/wishlist/') || 
               document.querySelector('.account-page-section .account-page-header h1')?.textContent.includes('我的收藏');
    }

    // 移除商品卡片（僅在收藏頁面使用）
    function removeProductCard(productId) {
        const productCard = document.querySelector(`.product-card[data-product-id="${productId}"]`);
        
        if (productCard) {
            productCard.style.transition = 'opacity 0.3s, transform 0.3s';
            productCard.style.opacity = '0';
            productCard.style.transform = 'translateX(-100%)';
            
            setTimeout(() => {
                productCard.remove();
                
                // 檢查是否還有商品
                const productGrid = document.querySelector('.product-grid');
                if (productGrid) {
                    const remainingCards = productGrid.querySelectorAll('.product-card');
                    if (remainingCards.length === 0) {
                        setTimeout(() => location.reload(), 100);
                    }
                }
            }, 300);
        }
    }

    // 處理錯誤
    function handleWishlistError(data) {
        if (data.requires_verification) {
            if (typeof showToast === 'function') {
                showToast(data.message, 'error');
            }
            setTimeout(() => {
                window.location.href = data.verification_url || '/account/resend-verification-email/';
            }, 2000);
        } else {
            if (typeof showToast === 'function') {
                showToast(data.message, 'error');
            }
        }
    }

    // 初始化按鈕狀態（確保初始狀態正確）
    function initButtonStates() {
        document.querySelectorAll('.wishlist-btn[data-product-id]').forEach(btn => {
            const icon = btn.querySelector('i');
            if (icon && btn.classList.contains('active')) {
                // 如果按鈕有 active 類，確保圖標是 heart-fill
                if (!icon.classList.contains('bi-heart-fill')) {
                    icon.className = 'bi bi-heart-fill';
                }
            } else if (icon && !btn.classList.contains('active')) {
                // 如果按鈕沒有 active 類，確保圖標是 heart
                if (!icon.classList.contains('bi-heart')) {
                    icon.className = 'bi bi-heart';
                }
            }
        });
    }

    // 初始化
    function init() {
        // 初始化按鈕狀態
        initButtonStates();
        
        // 綁定所有收藏按鈕（包括 wishlist-btn 和 wishlist-remove-btn）
        document.querySelectorAll('.wishlist-btn[data-product-id], .wishlist-remove-btn[data-product-id]').forEach(btn => {
            // 如果按鈕已經有 onclick 屬性，不需要重複綁定
            if (!btn.getAttribute('onclick')) {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    const productId = parseInt(this.dataset.productId);
                    if (productId) {
                        toggleWishlist(productId);
                    }
                });
            }
        });
        
        // 格式化價格
        if (typeof formatAllPrices === 'function') {
            formatAllPrices();
        }
        
        // 渲染評分星星
        if (typeof renderRatingStars === 'function') {
            renderRatingStars();
        }
    }

    // 導出到全局
    window.toggleWishlist = toggleWishlist;

    // 當 DOM 載入完成後初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

