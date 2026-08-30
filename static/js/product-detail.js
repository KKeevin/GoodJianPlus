/**
 * 商品詳細頁面相關功能
 * 處理商品詳情頁的圖片切換、數量選擇、加入購物車、評價等功能
 */

(function() {
    'use strict';

    // 商品圖片數據
    let productImages = [];
    let currentImageIndex = 0;

    // 輔助函數：提取文件名（去除查詢參數）
    function getFileName(url) {
        if (!url) return '';
        return url.split('/').pop().split('?')[0];
    }

    // 輔助函數：比較兩個 URL 是否指向同一張圖片
    function isSameImage(url1, url2) {
        if (!url1 || !url2) return false;
        // 完整 URL 匹配
        if (url1 === url2) return true;
        // 文件名匹配
        if (getFileName(url1) === getFileName(url2)) return true;
        // 包含匹配（處理路徑差異）
        const fileName1 = getFileName(url1);
        const fileName2 = getFileName(url2);
        return url1.includes(fileName2) || url2.includes(fileName1);
    }

    // 輔助函數：從 productImages 中查找圖片索引
    function findImageIndex(imageUrl) {
        if (!imageUrl || !productImages || productImages.length === 0) return -1;
        
        for (let i = 0; i < productImages.length; i++) {
            if (productImages[i] && isSameImage(productImages[i].url, imageUrl)) {
                return i;
            }
        }
        return -1;
    }

    // 切換主圖片
    function changeMainImage(url, element, imageIndex) {
        const mainImage = document.getElementById('mainImage');
        if (mainImage) {
            mainImage.src = url;
            if (imageIndex !== undefined && imageIndex !== null) {
                const index = parseInt(imageIndex);
                if (!isNaN(index)) {
                    mainImage.dataset.imageIndex = index;
                    currentImageIndex = index;
                    
                    // 確保 productImages 數組已初始化
                    if (!productImages || productImages.length === 0) {
                        initProductImages();
                    }
                    
                    // 更新 productImages 數組中對應索引的 URL
                    if (productImages && productImages.length > index) {
                        productImages[index].url = url;
                        if (mainImage.alt) {
                            productImages[index].alt = mainImage.alt;
                        }
                    }
                }
            }
        }
        document.querySelectorAll('.thumbnail').forEach(thumb => thumb.classList.remove('active'));
        if (element) {
            element.classList.add('active');
        }
    }

    // 初始化商品圖片數據
    function initProductImages() {
        const thumbnails = document.querySelectorAll('.thumbnail');
        const mainImage = document.getElementById('mainImage');
        
        productImages = [];
        
        // 如果有縮略圖，從縮略圖獲取所有圖片（包括主圖片對應的）
        if (thumbnails.length > 0) {
            thumbnails.forEach((thumb, index) => {
                productImages.push({
                    url: thumb.src,
                    alt: thumb.alt || ''
                });
            });
        } else if (mainImage) {
            // 如果沒有縮略圖，只有主圖片
            productImages.push({
                url: mainImage.src,
                alt: mainImage.alt || ''
            });
        }
        
        // 確保主圖片也在數組中（如果主圖片不在縮略圖列表中）
        // 檢查主圖片的 URL 是否已經在 productImages 中
        if (mainImage) {
            const mainImageUrl = mainImage.src;
            const mainImageIndex = parseInt(mainImage.dataset.imageIndex || '0');
            
            // 如果主圖片的索引超出範圍，或者主圖片的 URL 與對應索引的 URL 不一致
            if (mainImageIndex >= 0 && mainImageIndex < productImages.length) {
                // 確保該索引的 URL 與主圖片一致
                if (productImages[mainImageIndex].url !== mainImageUrl) {
                    // 更新該索引的 URL
                    productImages[mainImageIndex].url = mainImageUrl;
                    productImages[mainImageIndex].alt = mainImage.alt || '';
                }
            } else if (mainImageIndex >= productImages.length) {
                // 如果索引超出範圍，擴展數組
                while (productImages.length <= mainImageIndex) {
                    productImages.push({ url: '', alt: '' });
                }
                productImages[mainImageIndex] = {
                    url: mainImageUrl,
                    alt: mainImage.alt || ''
                };
            }
        }
        
        // 初始化 lightbox（使用統一的 Lightbox API）
        if (typeof window.Lightbox !== 'undefined') {
            window.Lightbox.create({
                id: 'productImageLightbox',
                imageId: 'productLightboxImage',
                currentId: 'productLightboxCurrent',
                totalId: 'productLightboxTotal',
                images: productImages
            });
        } else if (typeof initLightbox === 'function') {
            // 向後兼容
            initLightbox(productImages, {
                id: 'productImageLightbox',
                imageId: 'productLightboxImage',
                currentId: 'productLightboxCurrent',
                totalId: 'productLightboxTotal'
            });
        }
    }

    // 打開商品圖片 Lightbox
    function openProductImageLightbox(index) {
        // 確保圖片數據已初始化
        if (!productImages || productImages.length === 0) {
            initProductImages();
        }
        
        if (!productImages || productImages.length === 0) return;
        
        // 確定要顯示的圖片索引
        let targetIndex;
        if (index !== undefined && index !== null) {
            targetIndex = parseInt(index);
        } else {
            // 從主圖片的 data-image-index 獲取
            const mainImage = document.getElementById('mainImage');
            targetIndex = mainImage ? parseInt(mainImage.dataset.imageIndex || '0') : 0;
        }
        
        // 確保索引在有效範圍內
        if (isNaN(targetIndex) || targetIndex < 0) {
            targetIndex = 0;
        } else if (targetIndex >= productImages.length) {
            targetIndex = productImages.length - 1;
        }
        
        // 使用統一的 Lightbox API
        if (typeof window.Lightbox !== 'undefined') {
            window.Lightbox.open('productImageLightbox', targetIndex);
        } else {
            // 向後兼容：手動設置
            const lightbox = document.getElementById('productImageLightbox');
            const lightboxImage = document.getElementById('productLightboxImage');
            const lightboxCurrent = document.getElementById('productLightboxCurrent');
            const lightboxTotal = document.getElementById('productLightboxTotal');
            
            if (lightbox && lightboxImage && productImages[targetIndex]) {
                lightboxImage.src = productImages[targetIndex].url;
                lightboxImage.alt = productImages[targetIndex].alt || '';
                
                if (lightboxCurrent) {
                    lightboxCurrent.textContent = targetIndex + 1;
                }
                
                if (lightboxTotal) {
                    lightboxTotal.textContent = productImages.length;
                }
                
                lightbox.style.display = 'flex';
                document.body.style.overflow = 'hidden';
            }
        }
    }

    // 關閉商品圖片 Lightbox
    function closeProductImageLightbox(event) {
        if (event) {
            event.stopPropagation();
        }
        
        if (typeof window.Lightbox !== 'undefined') {
            window.Lightbox.close('productImageLightbox');
        } else {
            // 向後兼容
            const lightbox = document.getElementById('productImageLightbox');
            if (lightbox) {
                lightbox.style.display = 'none';
                document.body.style.overflow = '';
            }
        }
    }

    // 切換商品圖片 Lightbox
    function changeProductLightboxImage(direction, event) {
        if (event) {
            event.stopPropagation();
        }
        
        if (typeof window.Lightbox !== 'undefined') {
            window.Lightbox.change('productImageLightbox', direction);
        } else {
            // 向後兼容
            currentImageIndex += direction;
            
            if (currentImageIndex < 0) {
                currentImageIndex = productImages.length - 1;
            } else if (currentImageIndex >= productImages.length) {
                currentImageIndex = 0;
            }
            
            openProductImageLightbox(currentImageIndex);
        }
    }

    // 初始化放大鏡效果
    function initImageMagnifier() {
        const mainImageWrapper = document.querySelector('.main-image-wrapper');
        const mainImage = document.getElementById('mainImage');
        
        if (!mainImageWrapper || !mainImage) return;
        
        // 等待圖片載入完成
        let imageLoaded = false;
        let naturalWidth = 0;
        let naturalHeight = 0;
        let displayWidth = 0;
        let displayHeight = 0;
        
        const loadImageData = function() {
            if (mainImage.complete && mainImage.naturalWidth > 0) {
                naturalWidth = mainImage.naturalWidth;
                naturalHeight = mainImage.naturalHeight;
                
                // 獲取實際顯示尺寸（考慮 object-fit: contain）
                const rect = mainImage.getBoundingClientRect();
                displayWidth = rect.width;
                displayHeight = rect.height;
                
                // 計算實際圖片在容器中的位置（因為 object-fit: contain，圖片可能不會填滿整個容器）
                const imageAspect = naturalWidth / naturalHeight;
                const containerAspect = displayWidth / displayHeight;
                
                let actualImageWidth, actualImageHeight, offsetX, offsetY;
                
                if (imageAspect > containerAspect) {
                    // 圖片較寬，以寬度為準
                    actualImageWidth = displayWidth;
                    actualImageHeight = displayWidth / imageAspect;
                    offsetX = 0;
                    offsetY = (displayHeight - actualImageHeight) / 2;
                } else {
                    // 圖片較高，以高度為準
                    actualImageWidth = displayHeight * imageAspect;
                    actualImageHeight = displayHeight;
                    offsetX = (displayWidth - actualImageWidth) / 2;
                    offsetY = 0;
                }
                
                // 存儲計算結果
                mainImage._magnifierData = {
                    naturalWidth: naturalWidth,
                    naturalHeight: naturalHeight,
                    displayWidth: displayWidth,
                    displayHeight: displayHeight,
                    actualImageWidth: actualImageWidth,
                    actualImageHeight: actualImageHeight,
                    offsetX: offsetX,
                    offsetY: offsetY,
                    imageUrl: mainImage.src
                };
                
                imageLoaded = true;
            }
        };
        
        if (mainImage.complete) {
            loadImageData();
        } else {
            mainImage.addEventListener('load', loadImageData);
            mainImage.addEventListener('error', function() {
                console.warn('圖片載入失敗，無法使用放大鏡功能');
            });
        }
        
        // 放大倍數（顯示原始大小圖片的倍數）
        const zoomLevel = 2;
        
        mainImageWrapper.addEventListener('mousemove', function(e) {
            if (!imageLoaded || !mainImage._magnifierData) return;
            
            const rect = this.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;
            
            const data = mainImage._magnifierData;
            
            // 計算滑鼠在實際圖片上的位置（考慮 offset）
            const relativeX = mouseX - data.offsetX;
            const relativeY = mouseY - data.offsetY;
            
            // 檢查滑鼠是否在圖片範圍內
            if (relativeX < 0 || relativeX > data.actualImageWidth || 
                relativeY < 0 || relativeY > data.actualImageHeight) {
                // 滑鼠在圖片外，恢復顯示原始圖片
                mainImageWrapper.style.setProperty('--magnifier-image', 'none');
                return;
            }
            
            // 計算在原始圖片上的位置（比例）
            const percentX = relativeX / data.actualImageWidth;
            const percentY = relativeY / data.actualImageHeight;
            
            // 計算原始圖片上的坐標
            const originalX = percentX * data.naturalWidth;
            const originalY = percentY * data.naturalHeight;
            
            // 計算容器中心位置
            const containerCenterX = rect.width / 2;
            const containerCenterY = rect.height / 2;
            
            // 計算在放大後的圖片中，容器中心應該對應的位置
            // 容器顯示的是原始圖片的 zoomLevel 倍大小
            const scaledOriginalX = originalX * zoomLevel;
            const scaledOriginalY = originalY * zoomLevel;
            
            // 計算背景位置：讓容器中心對齊到原始圖片的對應位置
            const bgPositionX = containerCenterX - scaledOriginalX;
            const bgPositionY = containerCenterY - scaledOriginalY;
            
            // 設置容器的背景圖片（顯示原始大小的圖片）
            const bgSize = `${data.naturalWidth * zoomLevel}px ${data.naturalHeight * zoomLevel}px`;
            const bgPosition = `${bgPositionX}px ${bgPositionY}px`;
            
            mainImageWrapper.style.setProperty('--magnifier-image', `url("${data.imageUrl}")`);
            mainImageWrapper.style.setProperty('--magnifier-bg-size', bgSize);
            mainImageWrapper.style.setProperty('--magnifier-bg-position', bgPosition);
        });
        
        mainImageWrapper.addEventListener('mouseleave', function() {
            // 恢復顯示原始圖片
            mainImageWrapper.style.setProperty('--magnifier-image', 'none');
        });
        
        // 點擊打開 lightbox
        mainImageWrapper.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // 確保圖片數據已初始化
            if (!productImages || productImages.length === 0) {
                initProductImages();
            }
            
            if (!productImages || productImages.length === 0) {
                return;
            }
            
            // 獲取當前主圖片的 URL
            const currentImageUrl = mainImage.src;
            
            // 優先使用 data-image-index，但需要驗證它是否正確
            let imageIndex = parseInt(mainImage.dataset.imageIndex);
            
            // 驗證 data-image-index 是否正確
            if (!isNaN(imageIndex) && imageIndex >= 0 && imageIndex < productImages.length) {
                const indexedImageUrl = productImages[imageIndex].url;
                // 如果索引對應的 URL 與當前圖片 URL 不一致，重新查找
                if (!isSameImage(indexedImageUrl, currentImageUrl)) {
                    imageIndex = -1;
                }
            } else {
                imageIndex = -1;
            }
            
            // 如果 data-image-index 無效，從 URL 匹配
            if (imageIndex === -1) {
                imageIndex = findImageIndex(currentImageUrl);
            }
            
            // 如果還是找不到，使用 0
            if (imageIndex === -1 || imageIndex < 0 || imageIndex >= productImages.length) {
                imageIndex = 0;
            }
            
            // 打開 Lightbox
            openProductImageLightbox(imageIndex);
        });
        
        // 當圖片切換時，重新載入圖片數據
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'attributes' && mutation.attributeName === 'src') {
                    imageLoaded = false;
                    setTimeout(loadImageData, 100); // 等待新圖片載入
                }
            });
        });
        
        observer.observe(mainImage, { attributes: true });
        
        // 縮略圖點擊也應該更新索引（模板中已有 onclick，這裡只是確保索引同步）
        document.querySelectorAll('.thumbnail').forEach((thumb, index) => {
            // 確保 data-image-index 屬性存在
            if (!thumb.dataset.imageIndex) {
                thumb.dataset.imageIndex = index;
            }
        });
    }

    // 處理 Lightbox 鍵盤事件
    function handleProductLightboxKeyboard(e) {
        const lightbox = document.getElementById('productImageLightbox');
        if (lightbox && lightbox.style.display === 'flex') {
            if (e.key === 'ArrowLeft') {
                changeProductLightboxImage(-1);
            } else if (e.key === 'ArrowRight') {
                changeProductLightboxImage(1);
            } else if (e.key === 'Escape') {
                closeProductImageLightbox();
            }
        }
    }

    // 改變商品數量
    function changeQuantity(delta) {
        const input = document.getElementById('productQuantity');
        if (!input) return;
        
        const current = parseInt(input.value) || 1;
        const max = parseInt(input.getAttribute('max')) || parseInt(input.max) || 0;
        const newValue = Math.max(1, Math.min(max, current + delta));
        input.value = newValue;
        
        // 如果達到上限，顯示提示
        if (newValue >= max && max > 0 && typeof showToast === 'function') {
            showToast('已達可購買數量上限', 'info');
        }
    }

    // 加入購物車
    function addToCart(productId) {
        const input = document.getElementById('productQuantity');
        if (!input) {
            if (typeof showToast === 'function') {
                showToast('無法找到數量輸入框', 'error');
            }
            return;
        }
        
        const quantity = parseInt(input.value) || 1;
        const maxQuantity = parseInt(input.getAttribute('max')) || parseInt(input.max) || 0;
        
        if (maxQuantity <= 0) {
            if (typeof showToast === 'function') {
                showToast('商品暫時缺貨或已達購買上限', 'error');
            }
            return;
        }
        
        if (quantity > maxQuantity) {
            if (typeof showToast === 'function') {
                showToast(`最多只能購買 ${maxQuantity} 件`, 'error');
            }
            input.value = maxQuantity;
            return;
        }
        
        if (quantity < 1) {
            if (typeof showToast === 'function') {
                showToast('數量不能少於1', 'error');
            }
            input.value = 1;
            return;
        }
        
        if (typeof addToCart === 'function' && window.addToCart) {
            window.addToCart(productId, quantity);
        } else {
            // 使用 fetch 直接調用
            const addToCartUrl = window.CART_CONFIG?.addToCartUrl || '/api/cart/add/';
            const csrfToken = window.CART_CONFIG?.csrfToken || getCsrfToken();
            
            fetch(addToCartUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken
                },
                body: `product_id=${productId}&quantity=${quantity}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (typeof showToast === 'function') {
                        showToast(data.message, 'success');
                    }
                    if (typeof updateCartCount === 'function') {
                        updateCartCount();
                    }
                    // 更新可購買數量顯示
                    const cartQuantity = data.cart_quantity || 0;
                    const availableQuantity = data.available_quantity !== undefined ? data.available_quantity : (data.stock_quantity || 0);
                    const stockQuantity = data.stock_quantity || 0;
                    
                    if (availableQuantity !== undefined) {
                        input.max = availableQuantity;
                        // 重置數量為預設值 1
                        input.value = 1;
                        updateAvailableQuantityDisplay(cartQuantity, availableQuantity, stockQuantity);
                        
                        // 如果可購買數量為 0，禁用按鈕
                        if (availableQuantity <= 0) {
                            disableAddToCartButtons(cartQuantity);
                        }
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
                    showToast('加入購物車失敗，請稍後再試', 'error');
                }
            });
        }
    }

    // 立即購買
    function buyNow(productId) {
        const input = document.getElementById('productQuantity');
        if (!input) {
            if (typeof showToast === 'function') {
                showToast('無法找到數量輸入框', 'error');
            }
            return;
        }
        
        const quantity = parseInt(input.value) || 1;
        const maxQuantity = parseInt(input.getAttribute('max')) || parseInt(input.max) || 0;
        
        if (maxQuantity <= 0) {
            if (typeof showToast === 'function') {
                showToast('商品暫時缺貨或已達購買上限', 'error');
            }
            return;
        }
        
        if (quantity > maxQuantity) {
            if (typeof showToast === 'function') {
                showToast(`最多只能購買 ${maxQuantity} 件`, 'error');
            }
            input.value = maxQuantity;
            return;
        }
        
        if (quantity < 1) {
            if (typeof showToast === 'function') {
                showToast('數量不能少於1', 'error');
            }
            input.value = 1;
            return;
        }
        
        const addToCartUrl = window.CART_CONFIG?.addToCartUrl || '/api/cart/add/';
        const csrfToken = window.CART_CONFIG?.csrfToken || getCsrfToken();
        
        fetch(addToCartUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `product_id=${productId}&quantity=${quantity}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.href = '/cart/';
            } else {
                if (typeof showToast === 'function') {
                    showToast(data.message, 'error');
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (typeof showToast === 'function') {
                showToast('操作失敗，請稍後再試', 'error');
            }
        });
    }

    // 切換收藏
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
                const btn = document.querySelector('.wishlist-btn');
                if (btn) {
                    btn.classList.toggle('active', data.is_favorited);
                    const icon = btn.querySelector('i');
                    if (icon) {
                        icon.className = data.is_favorited ? 'bi bi-heart-fill' : 'bi bi-heart';
                    }
                    // 更新按鈕文字
                    const text = btn.querySelector('.wishlist-btn-text');
                    if (text) {
                        text.textContent = data.is_favorited ? '已收藏' : '加入收藏';
                    }
                    // 更新 title 屬性
                    btn.title = data.is_favorited ? '已收藏' : '加入收藏';
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
                    }, 2000);
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
        });
    }

    // 切換標籤頁
    function switchTab(tabName, event) {
        // 移除所有活動狀態
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        
        // 添加活動狀態到點擊的按鈕
        if (event && event.target) {
            event.target.classList.add('active');
        } else {
            // 如果沒有 event，通過 tabName 找到對應的按鈕
            document.querySelectorAll('.tab-btn').forEach(btn => {
                if (btn.textContent.includes(tabName === 'description' ? '描述' : tabName === 'specs' ? '規格' : '評價')) {
                    btn.classList.add('active');
                }
            });
        }
        
        // 顯示對應的內容
        const targetTab = document.getElementById(tabName + '-tab');
        if (targetTab) {
            targetTab.classList.add('active');
        }
    }

    // 設置評分
    function setRating(rating) {
        const ratingInput = document.getElementById('ratingValue');
        if (ratingInput) {
            ratingInput.value = rating;
        }
        const stars = document.querySelectorAll('.rating-star');
        stars.forEach((star, index) => {
            if (index < rating) {
                star.style.color = '#ffc107';
                star.classList.add('active');
            } else {
                star.style.color = '#ddd';
                star.classList.remove('active');
            }
        });
    }

    // 提交評價
    function submitReview(event, productId) {
        if (event) {
            event.preventDefault();
        }
        
        const formData = new FormData(event.target);
        formData.append('product_id', productId);
        
        const submitReviewUrl = window.REVIEW_CONFIG?.submitUrl || '/product/review/submit/';
        const csrfToken = window.CART_CONFIG?.csrfToken || getCsrfToken();
        
        fetch(submitReviewUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (typeof showToast === 'function') {
                    showToast('評價已提交，感謝您的回饋！', 'success');
                }
                if (event && event.target) {
                    event.target.reset();
                }
                setTimeout(() => location.reload(), 1500);
            } else {
                if (typeof showToast === 'function') {
                    showToast(data.message || '提交失敗，請稍後再試', 'error');
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (typeof showToast === 'function') {
                showToast('提交失敗，請稍後再試', 'error');
            }
        });
    }

    // 刪除評價
    function deleteUserReview(reviewId) {
        if (!window.confirmDialog) {
            if (!confirm('確定要刪除此評價嗎？刪除後無法復原。')) {
                return;
            }
        } else {
            confirmDialog('確定要刪除此評價嗎？刪除後無法復原。', '確認刪除', 'danger').then(confirmed => {
                if (!confirmed) return;
                performDeleteReview(reviewId);
            });
            return;
        }
        performDeleteReview(reviewId);
    }

    function performDeleteReview(reviewId) {
        const deleteReviewUrl = window.REVIEW_CONFIG?.deleteUrl || '/product/review/delete/';
        const csrfToken = window.CART_CONFIG?.csrfToken || getCsrfToken();
        
        fetch(deleteReviewUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `review_id=${reviewId}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (typeof showToast === 'function') {
                    showToast(data.message, 'success');
                }
                setTimeout(() => location.reload(), 1500);
            } else {
                if (typeof showToast === 'function') {
                    showToast(data.message, 'error');
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (typeof showToast === 'function') {
                showToast('刪除失敗，請稍後再試', 'error');
            }
        });
    }

    // 更新可購買數量顯示
    function updateAvailableQuantityDisplay(cartQuantity, availableQuantity, stockQuantity) {
        const displayDiv = document.querySelector('.quantity-selector > div:last-child');
        if (displayDiv) {
            // 使用傳入的總庫存數量，如果沒有則從原始 HTML 中獲取
            let totalStock = stockQuantity;
            if (!totalStock) {
                const totalStockMatch = displayDiv.textContent.match(/總庫存[：:]\s*(\d+)/);
                totalStock = totalStockMatch ? totalStockMatch[1] : '';
            }
            
            if (cartQuantity > 0) {
                displayDiv.innerHTML = `
                    <span style="color: #ffc107;">購物車中已有：${cartQuantity} 件</span><br>
                    <span>可購買：${availableQuantity} 件</span>
                    <span style="color: #666;">（總庫存：${totalStock} 件）</span>
                `;
            } else {
                displayDiv.innerHTML = `
                    <span>可購買：${availableQuantity} 件</span>
                    <span style="color: #666;">（總庫存：${totalStock} 件）</span>
                `;
            }
        }
    }

    // 禁用加入購物車按鈕
    function disableAddToCartButtons(cartQuantity) {
        const addCartBtn = document.querySelector('.btn-add-cart');
        const buyNowBtn = document.querySelector('.btn-buy-now');
        const actionButtons = document.querySelector('.action-buttons');
        
        if (addCartBtn) {
            addCartBtn.disabled = true;
            addCartBtn.style.opacity = '0.6';
            addCartBtn.style.cursor = 'not-allowed';
            addCartBtn.innerHTML = '<i class="bi bi-cart-x"></i> 已達購買上限';
            addCartBtn.onclick = null; // 移除點擊事件
        }
        
        if (buyNowBtn) {
            buyNowBtn.disabled = true;
            buyNowBtn.style.opacity = '0.6';
            buyNowBtn.style.cursor = 'not-allowed';
            buyNowBtn.onclick = null; // 移除點擊事件
        }
        
        // 檢查是否已經有警告訊息，如果沒有則添加
        if (actionButtons && !actionButtons.querySelector('.alert-warning')) {
            const warningDiv = document.createElement('div');
            warningDiv.className = 'alert alert-warning';
            warningDiv.style.cssText = 'margin-top: 10px; padding: 10px; font-size: 0.9rem;';
            if (cartQuantity > 0) {
                warningDiv.textContent = `購物車中已有 ${cartQuantity} 件，已達庫存上限`;
            } else {
                warningDiv.textContent = '暫時缺貨';
            }
            actionButtons.appendChild(warningDiv);
        }
    }

    // 將函數暴露到全局作用域
    window.disableAddToCartButtons = disableAddToCartButtons;

    // 初始化評分顯示
    function initRatingDisplay() {
        const ratingValue = document.getElementById('ratingValue');
        if (ratingValue && ratingValue.value) {
            setRating(parseInt(ratingValue.value));
        }
        
        // 渲染主商品的評分星星
        const productRatingStars = document.getElementById('productRatingStars');
        if (productRatingStars && typeof renderRatingStars === 'function') {
            renderRatingStars(document);
        }
        
        // 渲染相關商品的評分星星
        if (typeof renderRatingStars === 'function') {
            renderRatingStars(document);
        }
    }

    // 初始化
    function init() {
        initRatingDisplay();
        initProductImages();
        initImageMagnifier();
        
        // 綁定鍵盤事件
        document.addEventListener('keydown', handleProductLightboxKeyboard);
        
        // 格式化價格
        if (typeof formatAllPrices === 'function') {
            formatAllPrices();
        }
    }

    // 導出到全局
    window.ProductDetailManager = {
        changeMainImage: changeMainImage,
        changeQuantity: changeQuantity,
        addToCart: addToCart,
        buyNow: buyNow,
        toggleWishlist: toggleWishlist,
        switchTab: switchTab,
        setRating: setRating,
        submitReview: submitReview,
        deleteUserReview: deleteUserReview
    };
    
    window.openProductImageLightbox = openProductImageLightbox;
    window.closeProductImageLightbox = closeProductImageLightbox;
    window.changeProductLightboxImage = changeProductLightboxImage;
    window.toggleWishlist = toggleWishlist;

    // 當 DOM 載入完成後初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

