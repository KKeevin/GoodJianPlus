/**
 * 購物車相關功能
 */

// 更新購物車數量顯示
function updateCartCount() {
    const cartCountUrl = window.CART_CONFIG?.cartCountUrl || '/api/cart/count/';
    
    fetch(cartCountUrl)
        .then(response => response.json())
        .then(data => {
            const count = data.count || 0;
            
            // 更新 header 中的購物車數量
            const cartCount = document.getElementById('cartCount');
            if (cartCount) {
                cartCount.textContent = count;
                cartCount.style.display = (count > 0) ? 'inline' : 'none';
            }
            
            // 更新懸浮購物車按鈕
            const floatingCartBtn = document.getElementById('floatingCartBtn');
            const floatingCartCount = document.getElementById('floatingCartCount');
            
            if (floatingCartBtn && floatingCartCount) {
                // 檢查是否在購物車頁面
                const isCartPage = window.location.pathname.includes('/cart/');
                
                if (isCartPage) {
                    // 在購物車頁面時隱藏懸浮按鈕
                    floatingCartBtn.classList.add('hidden');
                } else if (count > 0) {
                    // 顯示懸浮按鈕
                    floatingCartBtn.classList.remove('hidden');
                    floatingCartCount.textContent = count;
                    floatingCartCount.style.display = 'flex';
                } else {
                    // 購物車為空時隱藏懸浮按鈕
                    floatingCartBtn.classList.add('hidden');
                    floatingCartCount.textContent = '0';
                    floatingCartCount.style.display = 'none';
                }
            }
        })
        .catch(error => {
            console.error('Cart count update failed:', error);
        });
}

// 加入購物車
function addToCart(productId, quantity = 1, options = {}) {
    const addToCartUrl = window.CART_CONFIG?.addToCartUrl || '/api/cart/add/';
    const csrfToken = window.CART_CONFIG?.csrfToken || getCsrfToken();
    
    return fetch(addToCartUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken
        },
        body: `product_id=${productId}&quantity=${quantity}`
    })
    .then(response => {
        // 檢查響應狀態
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            updateCartCount();
            if (options.onSuccess) {
                try {
                    options.onSuccess(data);
                } catch (error) {
                    console.error('onSuccess callback error:', error);
                }
            } else {
                if (typeof showToast === 'function') {
                    showToast(data.message || '已加入購物車', 'success');
                }
            }
        } else {
            if (options.onError) {
                try {
                    options.onError(data);
                } catch (error) {
                    console.error('onError callback error:', error);
                }
            } else {
                if (typeof showToast === 'function') {
                    showToast(data.message || '加入失敗', 'error');
                }
            }
        }
        return data;
    })
    .catch(error => {
        console.error('Add to cart error:', error);
        const errorData = {
            success: false,
            message: error.message || '加入購物車失敗，請稍後再試'
        };
        
        if (options.onError) {
            try {
                options.onError(errorData);
            } catch (callbackError) {
                console.error('onError callback error:', callbackError);
            }
        } else {
            if (typeof showToast === 'function') {
                showToast(errorData.message, 'error');
            }
        }
        
        // 返回錯誤數據而不是拋出錯誤，這樣調用者可以處理
        return errorData;
    });
}

// 更新購物車商品數量
function updateCartItem(itemId, quantity) {
    const updateUrl = window.CART_CONFIG?.updateUrl || '/api/cart/update/';
    const csrfToken = window.CART_CONFIG?.csrfToken || getCsrfToken();
    
    return fetch(updateUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken
        },
        body: `item_id=${itemId}&quantity=${quantity}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateCartCount();
            if (window.updateCartTotals) {
                window.updateCartTotals();
            }
        }
        return data;
    })
    .catch(error => {
        console.error('Error:', error);
        throw error;
    });
}

// 從購物車移除商品
async function removeCartItem(itemId) {
    const removeUrl = window.CART_CONFIG?.removeUrl || '/api/cart/remove/';
    const csrfToken = window.CART_CONFIG?.csrfToken || getCsrfToken();
    
    if (window.confirmDialog) {
        const confirmed = await confirmDialog('確定要移除此商品嗎？', '確認移除', 'default');
        if (!confirmed) return null;
    }
    
    return fetch(removeUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken
        },
        body: `item_id=${itemId}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateCartCount();
            if (window.updateCartTotals) {
                window.updateCartTotals();
            }
        }
        return data;
    })
    .catch(error => {
        console.error('Error:', error);
        throw error;
    });
}

// 更新商品數量（增減按鈕）
function updateQuantity(itemId, change) {
    const qtyInput = document.getElementById(`qty-${itemId}`);
    if (!qtyInput) return;
    
    const currentQty = parseInt(qtyInput.value) || 1;
    const maxQty = parseInt(qtyInput.max) || 0;
    
    let newQuantity;
    if (change > 0) {
        newQuantity = currentQty + 1;
    } else {
        newQuantity = currentQty - 1;
    }
    
    // 檢查邊界
    if (newQuantity < 1) {
        if (typeof showToast === 'function') {
            showToast('數量不能少於1', 'error');
        }
        return;
    }
    
    if (newQuantity > maxQty && maxQty > 0) {
        if (typeof showToast === 'function') {
            showToast(`庫存不足，最多只能購買 ${maxQty} 件`, 'error');
        }
        return;
    }
    
    // 更新輸入框顯示
    qtyInput.value = newQuantity;
    
    // 發送更新請求
    sendUpdateRequest(itemId, newQuantity);
}

// 更新商品數量（輸入框直接修改）
function updateQuantityFromInput(itemId, newQuantity) {
    newQuantity = parseInt(newQuantity);
    
    if (isNaN(newQuantity) || newQuantity < 1) {
        if (typeof showToast === 'function') {
            showToast('請輸入有效的數量', 'error');
        }
        location.reload();
        return;
    }
    
    const qtyInput = document.getElementById(`qty-${itemId}`);
    if (!qtyInput) return;
    
    const maxQty = parseInt(qtyInput.max) || 0;
    
    if (newQuantity > maxQty && maxQty > 0) {
        if (typeof showToast === 'function') {
            showToast(`庫存不足，最多只能購買 ${maxQty} 件`, 'error');
        }
        qtyInput.value = maxQty;
        newQuantity = maxQty;
    }
    
    sendUpdateRequest(itemId, newQuantity);
}

// 發送更新數量的請求
function sendUpdateRequest(itemId, newQuantity) {
    const qtyInput = document.getElementById(`qty-${itemId}`);
    if (!qtyInput) return;
    
    const originalValue = qtyInput.value;
    qtyInput.disabled = true;
    
    const updateUrl = window.CART_CONFIG?.updateUrl || '/api/cart/update/';
    const csrfToken = window.CART_CONFIG?.csrfToken || getCsrfToken();
    
    fetch(updateUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken
        },
        body: `item_id=${itemId}&quantity=${newQuantity}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 更新小計顯示
            const subtotalElement = document.getElementById(`subtotal-${itemId}`);
            if (subtotalElement) {
                if (typeof formatPrice === 'function') {
                    subtotalElement.textContent = formatPrice(data.subtotal);
                } else {
                    subtotalElement.textContent = `NT$${data.subtotal.toLocaleString('zh-TW')}`;
                }
                subtotalElement.dataset.price = data.subtotal;
            }
            
            // 更新總計
            if (typeof updateCartTotals === 'function') {
                updateCartTotals();
            }
            
            // 更新購物車數量顯示
            updateCartCount();
            
            if (typeof showToast === 'function') {
                showToast('數量已更新', 'success');
            }
        } else {
            // 恢復原本的數量
            qtyInput.value = originalValue;
            if (typeof showToast === 'function') {
                showToast(data.message, 'error');
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        qtyInput.value = originalValue;
        if (typeof showToast === 'function') {
            showToast('更新失敗，請稍後再試', 'error');
        }
    })
    .finally(() => {
        qtyInput.disabled = false;
    });
}

// 從購物車移除商品（購物車頁面專用）
async function removeFromCart(itemId) {
    if (window.confirmDialog) {
        const confirmed = await confirmDialog('確定要移除此商品嗎？', '確認移除', 'default');
        if (!confirmed) return;
    }
    
    const removeUrl = window.CART_CONFIG?.removeUrl || '/api/cart/remove/';
    const csrfToken = window.CART_CONFIG?.csrfToken || getCsrfToken();
    
    fetch(removeUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken
        },
        body: `item_id=${itemId}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 移除商品項目
            const itemElement = document.querySelector(`[data-item-id="${itemId}"]`);
            if (itemElement) {
                itemElement.style.opacity = '0';
                itemElement.style.transform = 'translateX(-100%)';
                setTimeout(() => {
                    itemElement.remove();
                    
                    // 更新總計
                    if (typeof updateCartTotals === 'function') {
                        updateCartTotals();
                    }
                    
                    // 更新購物車數量顯示
                    updateCartCount();
                    
                    // 如果購物車空了，重新載入頁面
                    if (data.cart_empty) {
                        setTimeout(() => location.reload(), 500);
                    }
                }, 300);
            }
            
            if (typeof showToast === 'function') {
                showToast(data.message, 'success');
            }
        } else {
            if (typeof showToast === 'function') {
                showToast(data.message, 'error');
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        if (typeof showToast === 'function') {
            showToast('移除失敗，請稍後再試', 'error');
        }
    });
}

// 更新購物車總計（購物車頁面專用）
function updateCartTotals() {
    const totalsUrl = window.CART_CONFIG?.totalsUrl || '/cart/totals/';
    
    fetch(totalsUrl)
        .then(response => response.json())
        .then(data => {
            const itemsTotalElement = document.getElementById('itemsTotal');
            const totalAmountElement = document.getElementById('totalAmount');
            const shippingFeeElement = document.getElementById('shippingFee');
            
            if (itemsTotalElement) {
                if (typeof formatPrice === 'function') {
                    itemsTotalElement.textContent = formatPrice(data.subtotal);
                } else {
                    itemsTotalElement.textContent = `NT$${data.subtotal.toLocaleString('zh-TW')}`;
                }
                itemsTotalElement.dataset.price = data.subtotal;
            }
            
            if (totalAmountElement) {
                if (typeof formatPrice === 'function') {
                    totalAmountElement.textContent = formatPrice(data.total);
                } else {
                    totalAmountElement.textContent = `NT$${data.total.toLocaleString('zh-TW')}`;
                }
                totalAmountElement.dataset.price = data.total;
            }
            
            if (shippingFeeElement) {
                if (data.shipping_fee > 0) {
                    if (typeof formatPrice === 'function') {
                        shippingFeeElement.textContent = formatPrice(data.shipping_fee);
                    } else {
                        shippingFeeElement.textContent = `NT$${data.shipping_fee.toLocaleString('zh-TW')}`;
                    }
                } else {
                    shippingFeeElement.textContent = '免運費';
                }
            }
            
            // 更新免運費提醒
            const freeShippingNotice = document.querySelector('.free-shipping-notice');
            const freeShippingThreshold = window.CART_CONFIG?.freeShippingThreshold || 1000;
            if (data.subtotal >= freeShippingThreshold) {
                if (freeShippingNotice) {
                    freeShippingNotice.style.display = 'none';
                }
            } else {
                if (freeShippingNotice) {
                    freeShippingNotice.style.display = 'flex';
                    const remaining = freeShippingThreshold - data.subtotal;
                    if (typeof formatPrice === 'function') {
                        freeShippingNotice.innerHTML = `<i class="bi bi-truck"></i> 還差 ${formatPrice(remaining)} 即可享免運費`;
                    } else {
                        freeShippingNotice.innerHTML = `<i class="bi bi-truck"></i> 還差 NT$${remaining.toLocaleString('zh-TW')} 即可享免運費`;
                    }
                }
            }
            
            // 格式化價格
            if (typeof formatAllPrices === 'function') {
                formatAllPrices();
            }
        })
        .catch(error => {
            console.error('Error updating totals:', error);
        });
}

// 前往結帳
function proceedToCheckout() {
    window.location.href = '/checkout/';
}

// 渲染購物車項目 HTML
function renderCartItemHTML(cartItem) {
    // 安全地轉義 HTML
    const escapeHtmlFunc = typeof escapeHtml === 'function' ? escapeHtml : (text) => {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };
    
    const stockWarning = cartItem.stock_quantity < 10 
        ? `<p class="stock-warning">庫存僅剩 ${cartItem.stock_quantity} 件</p>` 
        : '';
    
    const priceFormatted = typeof formatPrice === 'function' 
        ? formatPrice(cartItem.product_price) 
        : `NT$${cartItem.product_price.toLocaleString('zh-TW')}`;
    
    const subtotalFormatted = typeof formatPrice === 'function' 
        ? formatPrice(cartItem.subtotal) 
        : `NT$${cartItem.subtotal.toLocaleString('zh-TW')}`;
    
    return `
        <div class="cart-item" data-item-id="${cartItem.id}">
            <div class="col-product">
                <div class="product-info">
                    <div class="product-image">
                        <img src="${cartItem.product_image_url}" alt="${escapeHtmlFunc(cartItem.product_name)}">
                    </div>
                    <div class="product-details">
                        <h3><a href="/product/${cartItem.product_id}/">${escapeHtmlFunc(cartItem.product_name)}</a></h3>
                        <p class="product-sku">商品編號：${escapeHtmlFunc(cartItem.product_sku)}</p>
                        ${stockWarning}
                    </div>
                </div>
            </div>
            
            <div class="col-price">
                <span class="price" data-price="${cartItem.product_price}">${priceFormatted}</span>
            </div>
            
            <div class="col-quantity">
                <div class="quantity-controls">
                    <button class="qty-btn minus" onclick="updateQuantity(${cartItem.id}, -1)">-</button>
                    <input type="number" class="qty-input" value="${cartItem.quantity}" min="1" max="${cartItem.stock_quantity}" 
                           id="qty-${cartItem.id}" onchange="updateQuantityFromInput(${cartItem.id}, this.value)">
                    <button class="qty-btn plus" onclick="updateQuantity(${cartItem.id}, 1)">+</button>
                </div>
            </div>
            
            <div class="col-subtotal">
                <span class="subtotal" id="subtotal-${cartItem.id}" data-price="${cartItem.subtotal}">${subtotalFormatted}</span>
            </div>
            
            <div class="col-action">
                <button class="remove-btn" onclick="removeFromCart(${cartItem.id})">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        </div>
    `;
}

// 從推薦商品加入購物車（購物車頁面專用）
function addToCartFromRecommended(productId) {
    // 查找對應的按鈕（通過 onclick 屬性或 data 屬性）
    const btn = document.querySelector(`button.recommended-add-cart-btn[onclick*="${productId}"]`) ||
                document.querySelector(`button.recommended-add-cart-btn[data-product-id="${productId}"]`);
    const originalText = btn ? btn.innerHTML : '';
    
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-hourglass"></i>加入中...';
    }
    
    // 使用全局的 addToCart 函數
    if (typeof window.addToCart === 'function') {
        window.addToCart(productId, 1, {
            onSuccess: (data) => {
                if (btn) {
                    btn.innerHTML = '<i class="bi bi-check"></i>已加入！';
                    btn.classList.add('success');
                    setTimeout(() => {
                        btn.innerHTML = originalText;
                        btn.classList.remove('success');
                        btn.disabled = false;
                    }, 2000);
                }
                
                // 如果返回了購物車項目信息，動態更新購物車列表
                if (data.cart_item) {
                    updateCartListWithNewItem(data.cart_item);
                }
            },
            onError: (data) => {
                if (btn) {
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }
            }
        });
    } else {
        console.error('addToCart function not found');
        if (btn) {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
        if (typeof showToast === 'function') {
            showToast('購物車功能初始化失敗，請重新整理頁面', 'error');
        }
    }
}

// 使用新項目更新購物車列表
function updateCartListWithNewItem(cartItem) {
    // 處理空購物車情況
    const emptyCartDiv = document.querySelector('.empty-cart');
    const cartContent = document.querySelector('.cart-content');
    
    if (emptyCartDiv && emptyCartDiv.style.display !== 'none') {
        // 隱藏空購物車提示
        emptyCartDiv.style.display = 'none';
        
        // 顯示購物車內容區域（如果存在）
        if (cartContent) {
            cartContent.style.display = 'block';
        } else {
            // 如果購物車內容區域不存在，需要創建它
            const cartSection = document.querySelector('.cart-section .container');
            if (cartSection) {
                const newCartContent = document.createElement('div');
                newCartContent.className = 'cart-content';
                newCartContent.innerHTML = `
                    <div class="cart-items">
                        <div class="cart-table-header">
                            <div class="col-product">商品</div>
                            <div class="col-price">單價</div>
                            <div class="col-quantity">數量</div>
                            <div class="col-subtotal">小計</div>
                            <div class="col-action">操作</div>
                        </div>
                    </div>
                    <div class="cart-summary">
                        <div class="summary-card">
                            <h3>訂單摘要</h3>
                            <div class="summary-row">
                                <span>商品小計</span>
                                <span id="itemsTotal" data-price="0">NT$0</span>
                            </div>
                            <div class="summary-row">
                                <span>運費</span>
                                <span id="shippingFee">NT$100</span>
                            </div>
                            <hr>
                            <div class="summary-row total-row">
                                <span>總計</span>
                                <span id="totalAmount" data-price="0">NT$0</span>
                            </div>
                            <div class="checkout-actions">
                                <button class="btn-checkout" onclick="proceedToCheckout()">
                                    <i class="bi bi-credit-card"></i>
                                    <span>前往結帳</span>
                                </button>
                                <a href="/products/" class="btn-secondary">
                                    <i class="bi bi-arrow-left"></i>
                                    <span>繼續購物</span>
                                </a>
                            </div>
                        </div>
                    </div>
                `;
                emptyCartDiv.insertAdjacentElement('beforebegin', newCartContent);
            }
        }
    }
    
    const cartItemsContainer = document.querySelector('.cart-items');
    if (!cartItemsContainer) return;
    
    // 檢查商品是否已存在於購物車中
    const existingItem = cartItemsContainer.querySelector(`[data-item-id="${cartItem.id}"]`);
    
    if (existingItem) {
        // 如果商品已存在，更新數量和小計
        const qtyInput = existingItem.querySelector(`#qty-${cartItem.id}`);
        const subtotalElement = existingItem.querySelector(`#subtotal-${cartItem.id}`);
        
        if (qtyInput) {
            qtyInput.value = cartItem.quantity;
            qtyInput.max = cartItem.stock_quantity;
        }
        
        if (subtotalElement) {
            if (typeof formatPrice === 'function') {
                subtotalElement.textContent = formatPrice(cartItem.subtotal);
            } else {
                subtotalElement.textContent = `NT$${cartItem.subtotal.toLocaleString('zh-TW')}`;
            }
            subtotalElement.dataset.price = cartItem.subtotal;
        }
        
        // 更新庫存警告
        const stockWarning = existingItem.querySelector('.stock-warning');
        if (cartItem.stock_quantity < 10) {
            if (stockWarning) {
                stockWarning.textContent = `庫存僅剩 ${cartItem.stock_quantity} 件`;
            } else {
                const productDetails = existingItem.querySelector('.product-details');
                if (productDetails) {
                    const warning = document.createElement('p');
                    warning.className = 'stock-warning';
                    warning.textContent = `庫存僅剩 ${cartItem.stock_quantity} 件`;
                    productDetails.appendChild(warning);
                }
            }
        } else if (stockWarning) {
            stockWarning.remove();
        }
        
        // 添加動畫效果
        existingItem.style.animation = 'none';
        setTimeout(() => {
            existingItem.style.animation = 'pulse 0.5s ease';
        }, 10);
    } else {
        // 如果商品不存在，插入新項目
        const cartTableHeader = cartItemsContainer.querySelector('.cart-table-header');
        if (cartTableHeader) {
            // 在表頭後插入新項目
            const newItemHTML = renderCartItemHTML(cartItem);
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = newItemHTML;
            const newItem = tempDiv.firstElementChild;
            
            // 添加淡入動畫
            newItem.style.opacity = '0';
            newItem.style.transform = 'translateY(-20px)';
            cartTableHeader.insertAdjacentElement('afterend', newItem);
            
            // 觸發動畫
            setTimeout(() => {
                newItem.style.transition = 'all 0.3s ease';
                newItem.style.opacity = '1';
                newItem.style.transform = 'translateY(0)';
            }, 10);
        }
    }
    
    // 更新總計
    if (typeof updateCartTotals === 'function') {
        updateCartTotals();
    }
    
    // 更新購物車數量顯示
    updateCartCount();
}

// 導出到全局
window.updateCartCount = updateCartCount;
window.addToCart = addToCart;
window.updateCartItem = updateCartItem;
window.removeCartItem = removeCartItem;
window.updateQuantity = updateQuantity;
window.updateQuantityFromInput = updateQuantityFromInput;
window.removeFromCart = removeFromCart;
window.updateCartTotals = updateCartTotals;
window.proceedToCheckout = proceedToCheckout;
window.addToCartFromRecommended = addToCartFromRecommended;

