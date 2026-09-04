/**
 * 商品列表頁面相關功能
 * 處理商品列表的篩選、排序、檢視模式切換、快速預覽等功能
 */

(function() {
    'use strict';

    // 渲染評分星星（使用 utils.js 中的函數，這裡只是包裝）
    function renderRatingStars() {
        if (typeof renderRatingStars === 'function') {
            window.renderRatingStars(document);
        }
    }

    // 渲染推薦商品評分星星
    function renderRecommendedProductStars() {
        document.querySelectorAll('.recommended-stars[data-rating]').forEach(starsDiv => {
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
                
                starsDiv.innerHTML = starsHtml;
            } else {
                starsDiv.innerHTML = '☆☆☆☆☆';
            }
        });
    }

    // 商品分類篩選功能
    function initCategoryFilter() {
        const categoryTabs = document.querySelectorAll('.tab-btn[data-category]');
        categoryTabs.forEach(tab => {
            tab.addEventListener('click', function() {
                const category = this.dataset.category;
                const url = new URL(window.location);
                if (category === 'all') {
                    url.searchParams.delete('category');
                } else {
                    url.searchParams.set('category', category);
                }
                url.searchParams.delete('page'); // 重置頁碼
                // 保留搜尋參數 q（如果存在）
                window.location.href = url.toString();
            });
        });
    }

    // 排序功能
    function initSortSelect() {
        const sortSelect = document.getElementById('sortSelect');
        if (sortSelect) {
            sortSelect.addEventListener('change', function() {
                const url = new URL(window.location);
                if (this.value === 'default') {
                    url.searchParams.delete('sort');
                } else {
                    url.searchParams.set('sort', this.value);
                }
                url.searchParams.delete('page'); // 重置頁碼
                window.location.href = url.toString();
            });
        }
    }

    // 檢視模式切換
    function initViewModeToggle() {
        const viewButtons = document.querySelectorAll('.view-btn');
        const productGrid = document.getElementById('productGrid');
        
        if (!viewButtons.length || !productGrid) return;
        
        viewButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                viewButtons.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                
                if (this.classList.contains('list-view')) {
                    productGrid.classList.add('list-layout');
                    localStorage.setItem('productViewMode', 'list');
                } else {
                    productGrid.classList.remove('list-layout');
                    localStorage.setItem('productViewMode', 'grid');
                }
            });
        });

        // 恢復檢視模式偏好
        const savedViewMode = localStorage.getItem('productViewMode');
        if (savedViewMode === 'list') {
            const listViewBtn = document.querySelector('.list-view');
            if (listViewBtn) {
                listViewBtn.click();
            }
        }
    }

    // 快速預覽功能
    function initQuickView() {
        const quickViewButtons = document.querySelectorAll('.quick-view-btn');
        quickViewButtons.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const productId = this.dataset.productId;
                const modal = new bootstrap.Modal(document.getElementById('quickViewModal'));
                const contentDiv = document.getElementById('quickViewContent');
                
                if (!contentDiv) return;
                
                // 顯示載入狀態
                contentDiv.innerHTML = '<div class="text-center p-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">載入中...</span></div><p class="mt-3">載入商品資訊中...</p></div>';
                modal.show();
                
                // 載入商品資訊
                fetch(`/product/${productId}/quick-view/`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            renderQuickView(data.product, contentDiv);
                        } else {
                            contentDiv.innerHTML = `<div class="alert alert-danger">${data.message || '載入失敗'}</div>`;
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        contentDiv.innerHTML = '<div class="alert alert-danger">載入失敗，請稍後再試</div>';
                    });
            });
        });
    }

    // 渲染快速預覽內容
    function renderQuickView(product, container) {
        const imagesHtml = product.images.map((img, index) => 
            `<img src="${img.url}" alt="${img.alt}" class="quick-view-img" data-index="${index}" style="width: 100%; max-height: 400px; object-fit: cover; border-radius: 8px; display: ${index === 0 ? 'block' : 'none'};">`
        ).join('');
        
        const priceHtml = product.original_price && product.original_price > product.price
            ? `<span class="text-muted text-decoration-line-through me-2">NT$${product.original_price.toLocaleString('zh-TW')}</span><span class="text-danger fw-bold fs-4">NT$${product.price.toLocaleString('zh-TW')}</span>`
            : `<span class="text-danger fw-bold fs-4">NT$${product.price.toLocaleString('zh-TW')}</span>`;
        
        const stockHtml = product.stock_quantity > 10
            ? '<span class="badge bg-success">現貨充足</span>'
            : product.stock_quantity > 0
            ? `<span class="badge bg-warning">僅剩 ${product.stock_quantity} 件</span>`
            : '<span class="badge bg-danger">暫時缺貨</span>';
        
        const ratingHtml = product.avg_rating > 0
            ? `<div class="mb-2"><span class="text-warning">${'★'.repeat(Math.round(product.avg_rating))}${'☆'.repeat(5 - Math.round(product.avg_rating))}</span> <small class="text-muted">(${product.review_count} 評價)</small></div>`
            : '<div class="mb-2"><small class="text-muted">尚無評價</small></div>';
        
        const wishlistBtnHtml = window.USER_AUTHENTICATED
            ? `<button class="btn btn-outline-danger btn-sm quick-view-wishlist-btn" data-product-id="${product.id}">
                <i class="bi bi-heart${product.is_favorited ? '-fill' : ''}"></i> ${product.is_favorited ? '已收藏' : '加入收藏'}
            </button>`
            : `<a href="/login/?next=/products/" class="btn btn-outline-danger btn-sm">登入收藏</a>`;
        
        container.innerHTML = `
            <div class="row" data-product-id="${product.id}">
                <div class="col-md-6">
                    <div class="quick-view-images position-relative">
                        ${imagesHtml}
                        ${product.images.length > 1 ? `
                        <div class="quick-view-thumbnails mt-2 d-flex gap-2" style="overflow-x: auto;">
                            ${product.images.map((img, index) => 
                                `<img src="${img.url}" alt="${img.alt}" class="quick-view-thumb" data-index="${index}" style="width: 60px; height: 60px; object-fit: cover; border-radius: 4px; cursor: pointer; border: 2px solid ${index === 0 ? '#28a745' : 'transparent'}; transition: border-color 0.3s;">`
                            ).join('')}
                        </div>
                        ` : ''}
                    </div>
                </div>
                <div class="col-md-6">
                    <h4 class="mb-3">${product.name}</h4>
                    ${ratingHtml}
                    <div class="mb-3">
                        <div class="d-flex align-items-center gap-2">
                            ${priceHtml}
                            ${product.discount_percentage > 0 ? `<span class="badge bg-danger">-${product.discount_percentage}%</span>` : ''}
                        </div>
                        <div class="mt-2">${stockHtml}</div>
                    </div>
                    <div class="mb-3">
                        <p class="text-muted">${product.short_description}</p>
                    </div>
                    <div class="mb-3">
                        <small class="text-muted">商品編號：${product.sku}</small><br>
                        ${product.brand ? `<small class="text-muted">品牌：${product.brand}</small><br>` : ''}
                        <small class="text-muted">分類：${product.category}</small>
                    </div>
                    <div class="d-flex gap-2 mb-3">
                        ${wishlistBtnHtml}
                        <a href="/product/${product.id}/" class="btn btn-outline-primary btn-sm">查看詳情</a>
                    </div>
                    ${product.available_quantity > 0 ? `
                    <div class="d-flex align-items-center gap-2 mb-3">
                        <label>數量：</label>
                        <div class="input-group" style="width: 150px;">
                            <button class="btn btn-outline-secondary quick-view-qty-minus" type="button">-</button>
                            <input type="number" id="quickViewQty" class="form-control text-center" value="1" min="1" max="${product.available_quantity}">
                            <button class="btn btn-outline-secondary quick-view-qty-plus" type="button">+</button>
                        </div>
                    </div>
                    ${product.cart_quantity > 0 ? `
                    <div class="alert alert-warning mb-3" style="padding: 8px; font-size: 0.85rem;">
                        <i class="bi bi-info-circle"></i> 購物車中已有 ${product.cart_quantity} 件，可再購買 ${product.available_quantity} 件
                    </div>
                    ` : ''}
                    <div class="d-grid gap-2">
                        <button class="btn btn-success quick-view-add-cart-btn" data-product-id="${product.id}">
                            <i class="bi bi-cart-plus"></i> 加入購物車
                        </button>
                        <button class="btn btn-danger quick-view-buy-now-btn" data-product-id="${product.id}">
                            <i class="bi bi-bag-check"></i> 立即購買
                        </button>
                    </div>
                    ` : product.cart_quantity > 0 ? `
                    <div class="alert alert-warning mb-3">
                        <i class="bi bi-exclamation-triangle"></i> 購物車中已有 ${product.cart_quantity} 件，已達庫存上限（總庫存：${product.stock_quantity} 件）
                    </div>
                    <button class="btn btn-secondary w-100 disabled" disabled style="opacity: 0.6; cursor: not-allowed;"><i class="bi bi-cart-x"></i> 已達購買上限</button>
                    ` : '<button class="btn btn-secondary w-100" disabled>暫時缺貨</button>'}
                </div>
            </div>
        `;
        
        // 綁定事件監聽器
        setupQuickViewEvents(container, product);
    }
    
    // 設置快速預覽事件
    function setupQuickViewEvents(container, product) {
        // 圖片縮略圖點擊事件
        container.querySelectorAll('.quick-view-thumb').forEach(thumb => {
            thumb.addEventListener('click', function() {
                const index = parseInt(this.dataset.index);
                switchQuickViewImage(index);
            });
        });
        
        // 數量加減按鈕
        const qtyInput = container.querySelector('#quickViewQty');
        const qtyMinus = container.querySelector('.quick-view-qty-minus');
        const qtyPlus = container.querySelector('.quick-view-qty-plus');
        
        if (qtyMinus) {
            qtyMinus.addEventListener('click', function() {
                const current = parseInt(qtyInput.value) || 1;
                const newValue = Math.max(1, current - 1);
                qtyInput.value = newValue;
            });
        }
        
        // 監聽數量輸入框變化
        if (qtyInput) {
            qtyInput.addEventListener('change', function() {
                const value = parseInt(this.value) || 1;
                const max = parseInt(this.max) || product.available_quantity;
                if (value > max) {
                    this.value = max;
                    if (typeof showToast === 'function') {
                        showToast(`最多只能購買 ${max} 件`, 'error');
                    }
                } else if (value < 1) {
                    this.value = 1;
                    if (typeof showToast === 'function') {
                        showToast('數量不能少於1', 'error');
                    }
                }
            });
        }
        
        if (qtyPlus) {
            qtyPlus.addEventListener('click', function() {
                const current = parseInt(qtyInput.value) || 1;
                const max = parseInt(qtyInput.max) || product.available_quantity;
                const newValue = Math.min(max, current + 1);
                qtyInput.value = newValue;
                if (newValue >= max && max > 0 && typeof showToast === 'function') {
                    showToast('已達可購買數量上限', 'info');
                }
            });
        }
        
        // 加入購物車按鈕
        const addCartBtn = container.querySelector('.quick-view-add-cart-btn');
        if (addCartBtn) {
            addCartBtn.addEventListener('click', function() {
                const productId = parseInt(this.dataset.productId);
                const quantity = parseInt(qtyInput.value) || 1;
                addToCartFromQuickView(productId, quantity);
            });
        }
        
        // 立即購買按鈕
        const buyNowBtn = container.querySelector('.quick-view-buy-now-btn');
        if (buyNowBtn) {
            buyNowBtn.addEventListener('click', function() {
                const productId = parseInt(this.dataset.productId);
                const quantity = parseInt(qtyInput.value) || 1;
                buyNowFromQuickView(productId, quantity);
            });
        }
        
        // 收藏按鈕
        const wishlistBtn = container.querySelector('.quick-view-wishlist-btn');
        if (wishlistBtn) {
            wishlistBtn.addEventListener('click', function() {
                const productId = parseInt(this.dataset.productId);
                toggleWishlistFromQuickView(productId, this);
            });
        }
    }
    
    // 切換快速預覽圖片
    function switchQuickViewImage(index) {
        const modal = document.getElementById('quickViewModal');
        if (!modal) return;
        
        const images = modal.querySelectorAll('.quick-view-img');
        const thumbs = modal.querySelectorAll('.quick-view-thumb');
        
        images.forEach((img, i) => {
            if (i === index) {
                img.style.display = 'block';
            } else {
                img.style.display = 'none';
            }
        });
        
        thumbs.forEach((thumb, i) => {
            if (i === index) {
                thumb.style.borderColor = '#28a745';
                thumb.style.borderWidth = '2px';
            } else {
                thumb.style.borderColor = 'transparent';
                thumb.style.borderWidth = '2px';
            }
        });
    }
    
    // 從快速預覽加入購物車
    function addToCartFromQuickView(productId, quantity) {
        const btn = document.querySelector('.quick-view-add-cart-btn');
        const qtyInput = document.getElementById('quickViewQty');
        const originalText = btn ? btn.innerHTML : '';
        
        // 驗證數量
        if (qtyInput) {
            const maxQuantity = parseInt(qtyInput.max) || 0;
            if (quantity > maxQuantity) {
                if (typeof showToast === 'function') {
                    showToast(`最多只能購買 ${maxQuantity} 件`, 'error');
                }
                qtyInput.value = Math.max(1, maxQuantity);
                return;
            }
        }
        
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="bi bi-hourglass-split"></i> 處理中...';
        }
        
        if (typeof addToCart === 'function') {
            addToCart(productId, quantity, {
                onSuccess: (data) => {
                    if (typeof showToast === 'function') {
                        showToast(data.message, 'success');
                    }
                    
                    // 更新可購買數量
                    if (data.available_quantity !== undefined) {
                        if (data.available_quantity <= 0) {
                            updateQuickViewToLimitReached(productId, data.cart_quantity, data.stock_quantity);
                        } else {
                            if (qtyInput) {
                                qtyInput.max = data.available_quantity;
                                if (parseInt(qtyInput.value) > data.available_quantity) {
                                    qtyInput.value = data.available_quantity;
                                }
                            }
                            // 更新顯示
                            updateQuickViewQuantityDisplay(data.cart_quantity, data.available_quantity, data.stock_quantity);
                        }
                    }
                    
                    // 更新頁面其它對應商品按鈕
                    if (data.available_quantity !== undefined && data.available_quantity <= 0) {
                        const targets = document.querySelectorAll(`button[data-product-id="${productId}"]`);
                        targets.forEach(b => {
                            if (!b.classList.contains('quick-view-wishlist-btn')) {
                                b.disabled = true;
                                b.classList.add('disabled');
                                b.style.opacity = '0.6';
                                b.style.cursor = 'not-allowed';
                                b.innerHTML = '<i class="bi bi-cart-x"></i> 已達購買上限';
                            }
                        });
                    }
                    
                    setTimeout(() => {
                        const modalElement = document.getElementById('quickViewModal');
                        if (modalElement) {
                            const modal = bootstrap.Modal.getInstance(modalElement);
                            if (modal) modal.hide();
                        }
                    }, 1000);
                },
                onError: (data) => {
                    if (typeof showToast === 'function') {
                        showToast((data && data.message) || '加入購物車失敗', 'error');
                    }
                    if (data && (data.available_quantity <= 0 || (data.message && data.message.includes('已達購買上限')))) {
                        updateQuickViewToLimitReached(productId, data.cart_quantity, data.stock_quantity);
                        const targets = document.querySelectorAll(`button[data-product-id="${productId}"]`);
                        targets.forEach(b => {
                            if (!b.classList.contains('quick-view-wishlist-btn')) {
                                b.disabled = true;
                                b.classList.add('disabled');
                                b.style.opacity = '0.6';
                                b.style.cursor = 'not-allowed';
                                b.innerHTML = '<i class="bi bi-cart-x"></i> 已達購買上限';
                            }
                        });
                    }
                }
            }).finally(() => {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = originalText;
                }
            });
        }
    }
    
    // 將快速預覽切換為已達購買上限狀態
    function updateQuickViewToLimitReached(productId, cartQuantity, stockQuantity) {
        const modal = document.getElementById('quickViewModal');
        if (!modal) return;
        
        const qtyDiv = modal.querySelector('.d-flex.align-items-center.gap-2.mb-3');
        const alertDiv = modal.querySelector('.alert');
        const btnDiv = modal.querySelector('.d-grid.gap-2');
        
        if (qtyDiv) qtyDiv.remove();
        if (alertDiv) alertDiv.remove();
        
        const cQty = cartQuantity || stockQuantity || 0;
        const sQty = stockQuantity || cQty || 0;
        
        const warningDiv = document.createElement('div');
        warningDiv.className = 'alert alert-warning mb-3';
        warningDiv.innerHTML = `<i class="bi bi-exclamation-triangle"></i> 購物車中已有 ${cQty} 件，已達庫存上限（總庫存：${sQty} 件）`;
        
        const limitBtn = document.createElement('button');
        limitBtn.className = 'btn btn-secondary w-100 disabled';
        limitBtn.disabled = true;
        limitBtn.style.opacity = '0.6';
        limitBtn.style.cursor = 'not-allowed';
        limitBtn.innerHTML = '<i class="bi bi-cart-x"></i> 已達購買上限';
        
        if (btnDiv) {
            btnDiv.replaceWith(limitBtn);
            limitBtn.parentNode.insertBefore(warningDiv, limitBtn);
        }
    }

    // 更新快速預覽的數量顯示
    function updateQuickViewQuantityDisplay(cartQuantity, availableQuantity, stockQuantity) {
        const modal = document.getElementById('quickViewModal');
        if (!modal) return;
        
        const alertDiv = modal.querySelector('.alert-warning');
        if (cartQuantity > 0) {
            if (alertDiv) {
                alertDiv.innerHTML = `<i class="bi bi-info-circle"></i> 購物車中已有 ${cartQuantity} 件，可再購買 ${availableQuantity} 件`;
            } else {
                const qtyDiv = modal.querySelector('.d-flex.align-items-center.gap-2.mb-3');
                if (qtyDiv && qtyDiv.nextElementSibling && !qtyDiv.nextElementSibling.classList.contains('alert')) {
                    const newAlert = document.createElement('div');
                    newAlert.className = 'alert alert-warning mb-3';
                    newAlert.style.cssText = 'padding: 8px; font-size: 0.85rem;';
                    newAlert.innerHTML = `<i class="bi bi-info-circle"></i> 購物車中已有 ${cartQuantity} 件，可再購買 ${availableQuantity} 件`;
                    qtyDiv.parentNode.insertBefore(newAlert, qtyDiv.nextSibling);
                }
            }
        }
    }
    
    // 從快速預覽立即購買
    function buyNowFromQuickView(productId, quantity) {
        const btn = document.querySelector('.quick-view-buy-now-btn');
        const originalText = btn ? btn.innerHTML : '';
        
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="bi bi-hourglass-split"></i> 處理中...';
        }
        
        if (typeof addToCart === 'function') {
            addToCart(productId, quantity, {
                onSuccess: () => {
                    window.location.href = '/cart/';
                },
                onError: (data) => {
                    if (typeof showToast === 'function') {
                        showToast((data && data.message) || '加入購物車失敗', 'error');
                    }
                    if (btn) {
                        btn.disabled = false;
                        btn.innerHTML = originalText;
                    }
                }
            });
        }
    }
    
    // 從快速預覽切換收藏
    function toggleWishlistFromQuickView(productId, btn) {
        const originalText = btn.innerHTML;
        
        btn.disabled = true;
        
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
                if (data.is_favorited) {
                    btn.innerHTML = '<i class="bi bi-heart-fill"></i> 已收藏';
                    btn.classList.add('active');
                } else {
                    btn.innerHTML = '<i class="bi bi-heart"></i> 加入收藏';
                    btn.classList.remove('active');
                }
                if (typeof showToast === 'function') {
                    showToast(data.message, 'success');
                }
            } else {
                if (data.requires_verification) {
                    if (typeof showToast === 'function') {
                        showToast(data.message, 'error');
                    }
                    setTimeout(() => {
                        window.location.href = data.verification_url || '/account/resend-verification-email/';
                    }, 1500);
                } else {
                    if (typeof showToast === 'function') {
                        showToast(data.message, 'error');
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (typeof showToast === 'function') {
                showToast('操作失敗，請稍後再試', 'error');
            }
        })
        .finally(() => {
            btn.disabled = false;
        });
    }

    // 搜尋框處理
    function initSearchInput() {
        const searchInput = document.getElementById('searchInput');
        if (!searchInput) return;
        
        // 自動聚焦（如果有搜尋關鍵字）
        if (searchInput.value) {
            searchInput.focus();
            searchInput.select();
        }
        
        // Enter 鍵提交
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.closest('form').submit();
            }
        });
    }

    // 綁定加入購物車按鈕
    function initAddToCartButtons() {
        document.querySelectorAll('.add-to-cart[data-product-id], .recommended-add-to-cart[data-product-id]').forEach(btn => {
            // 檢查是否已經綁定過（通過 data 屬性標記）
            if (btn.dataset.cartBound === 'true') {
                return; // 已經綁定過，跳過
            }
            
            // 標記為已綁定
            btn.dataset.cartBound = 'true';
            
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation(); // 防止事件冒泡
                
                // 如果按鈕已禁用，直接返回
                if (this.disabled) {
                    return;
                }
                
                const productId = parseInt(this.dataset.productId);
                if (!productId || isNaN(productId)) {
                    console.error('Invalid product ID:', this.dataset.productId);
                    return;
                }
                
                const originalText = this.innerHTML;
                const originalDisabled = this.disabled;
                
                // 更新按鈕狀態
                this.innerHTML = '<i class="bi bi-hourglass"></i>加入中...';
                this.disabled = true;
                
                if (typeof window.addToCart === 'function') {
                    // 使用 Promise 確保無論成功或失敗都能恢復按鈕狀態
                    window.addToCart(productId, 1, {
                        onSuccess: (data) => {
                            if (data.available_quantity !== undefined && data.available_quantity <= 0) {
                                // 當可購買數量 <= 0 時，直接設定為已達購買上限並禁用
                                const targets = document.querySelectorAll(`button[data-product-id="${productId}"]`);
                                targets.forEach(btn => {
                                    btn.disabled = true;
                                    btn.classList.add('disabled');
                                    btn.style.opacity = '0.6';
                                    btn.style.cursor = 'not-allowed';
                                    btn.innerHTML = '<i class="bi bi-cart-x"></i> 已達購買上限';
                                });
                            } else {
                                this.innerHTML = '<i class="bi bi-check"></i>已加入！';
                                this.classList.add('success');
                                setTimeout(() => {
                                    this.innerHTML = originalText;
                                    this.classList.remove('success');
                                    this.disabled = originalDisabled;
                                }, 2000);
                            }
                        },
                        onError: (data) => {
                            if (data && (data.available_quantity <= 0 || (data.message && data.message.includes('已達購買上限')))) {
                                const targets = document.querySelectorAll(`button[data-product-id="${productId}"]`);
                                targets.forEach(btn => {
                                    btn.disabled = true;
                                    btn.classList.add('disabled');
                                    btn.style.opacity = '0.6';
                                    btn.style.cursor = 'not-allowed';
                                    btn.innerHTML = '<i class="bi bi-cart-x"></i> 已達購買上限';
                                });
                            } else {
                                this.innerHTML = originalText;
                                this.disabled = originalDisabled;
                            }
                            if (typeof showToast === 'function') {
                                showToast((data && data.message) || '加入購物車失敗', 'error');
                            }
                        }
                    }).catch(error => {
                        // 捕獲任何未處理的錯誤
                        console.error('Add to cart error:', error);
                        this.innerHTML = originalText;
                        this.disabled = originalDisabled;
                        if (typeof showToast === 'function') {
                            showToast('加入購物車失敗，請稍後再試', 'error');
                        }
                    });
                } else {
                    console.error('addToCart function not found');
                    this.innerHTML = originalText;
                    this.disabled = originalDisabled;
                    if (typeof showToast === 'function') {
                        showToast('購物車功能初始化失敗，請重新整理頁面', 'error');
                    }
                }
            });
        });
    }

    // 綁定收藏按鈕
    function initWishlistButtons() {
        document.querySelectorAll('.wishlist-btn[data-product-id]').forEach(btn => {
            // 檢查是否已經綁定過（通過 data 屬性標記）
            if (btn.dataset.wishlistBound === 'true') {
                return; // 已經綁定過，跳過
            }
            
            // 標記為已綁定
            btn.dataset.wishlistBound = 'true';
            
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation(); // 防止事件冒泡
                
                const productId = parseInt(this.dataset.productId);
                if (!productId || isNaN(productId)) {
                    console.error('Invalid product ID:', this.dataset.productId);
                    return;
                }
                
                // 使用全局的 toggleWishlist 函數
                if (typeof window.toggleWishlist === 'function') {
                    window.toggleWishlist(productId);
                } else {
                    console.error('toggleWishlist function not found');
                    if (typeof showToast === 'function') {
                        showToast('收藏功能初始化失敗，請重新整理頁面', 'error');
                    }
                }
            });
        });
    }

    // 懶加載圖片
    function initLazyLoading() {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src || img.src;
                        img.classList.remove('lazy');
                        observer.unobserve(img);
                    }
                });
            });

            document.querySelectorAll('img[loading="lazy"]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }

    // 初始化所有功能
    function init() {
        // 渲染評分星星
        if (typeof renderRatingStars === 'function') {
            renderRatingStars();
        }
        renderRecommendedProductStars();
        
        // 格式化價格
        if (typeof formatAllPrices === 'function') {
            formatAllPrices();
        }
        
        // 初始化各功能
        initCategoryFilter();
        initSortSelect();
        initViewModeToggle();
        initQuickView();
        initSearchInput();
        initAddToCartButtons();
        initWishlistButtons();
        initLazyLoading();
    }

    // 當 DOM 載入完成後初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // 導出公共 API
    window.ProductsManager = {
        renderRatingStars: renderRatingStars,
        renderRecommendedProductStars: renderRecommendedProductStars,
        init: init
    };
})();

