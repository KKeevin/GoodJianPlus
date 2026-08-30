/**
 * 圖片瀏覽視窗 (Lightbox) 功能
 * 支持多個實例，通過配置不同的 ID 來使用
 */

(function() {
    'use strict';

    // Lightbox 實例管理
    const lightboxInstances = {};

    /**
     * 創建或獲取 Lightbox 實例
     * @param {Object} config - 配置對象
     * @param {string} config.id - Lightbox 容器的 ID（必需）
     * @param {string} config.imageId - 圖片元素的 ID（必需）
     * @param {string} config.captionId - 標題元素的 ID（可選）
     * @param {string} config.currentId - 當前索引顯示元素的 ID（可選）
     * @param {string} config.totalId - 總數顯示元素的 ID（可選）
     * @param {Array} config.images - 圖片數組（可選，可在初始化時設置）
     */
    function createLightboxInstance(config) {
        const {
            id,
            imageId,
            captionId = null,
            currentId = null,
            totalId = null,
            images = []
        } = config;

        if (!id || !imageId) {
            console.error('Lightbox: id 和 imageId 是必需的');
            return null;
        }

        // 如果實例已存在，返回現有實例
        if (lightboxInstances[id]) {
            return lightboxInstances[id];
        }

        const instance = {
            id: id,
            imageId: imageId,
            captionId: captionId,
            currentId: currentId,
            totalId: totalId,
            images: images,
            currentIndex: 0
        };

        // 初始化實例
        initInstance(instance);

        // 存儲實例
        lightboxInstances[id] = instance;

        return instance;
    }

    /**
     * 初始化 Lightbox 實例
     */
    function initInstance(instance) {
        const lightbox = document.getElementById(instance.id);
        if (!lightbox) {
            console.warn(`Lightbox: 找不到 ID 為 "${instance.id}" 的元素`);
            return;
        }

        // 綁定關閉事件
        const closeBtn = lightbox.querySelector('.lightbox-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                closeLightbox(instance.id);
            });
        }

        // 綁定背景點擊關閉
        lightbox.addEventListener('click', (e) => {
            if (e.target === lightbox) {
                closeLightbox(instance.id);
            }
        });

        // 綁定上一張/下一張按鈕
        const prevBtn = lightbox.querySelector('.lightbox-prev');
        const nextBtn = lightbox.querySelector('.lightbox-next');
        
        if (prevBtn) {
            prevBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                changeLightboxImage(instance.id, -1);
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                changeLightboxImage(instance.id, 1);
            });
        }
    }

    /**
     * 初始化 Lightbox（向後兼容舊版本）
     * @param {Array} images - 圖片數組
     * @param {Object} config - 可選配置（用於自定義 ID）
     */
    function initLightbox(images, config = {}) {
        const defaultConfig = {
            id: 'imageLightbox',
            imageId: 'lightboxImage',
            captionId: 'lightboxCaption',
            currentId: 'lightboxCurrent',
            totalId: 'lightboxTotal',
            images: images || []
        };

        const finalConfig = { ...defaultConfig, ...config };
        return createLightboxInstance(finalConfig);
    }

    /**
     * 打開 Lightbox
     * @param {string} lightboxId - Lightbox 實例 ID
     * @param {number} index - 要顯示的圖片索引
     */
    function openLightbox(lightboxId, index) {
        const instance = lightboxInstances[lightboxId];
        if (!instance) {
            console.warn(`Lightbox: 找不到 ID 為 "${lightboxId}" 的實例`);
            return;
        }

        if (!instance.images || instance.images.length === 0) {
            console.warn(`Lightbox: 實例 "${lightboxId}" 沒有圖片數據`);
            return;
        }

        // 確保索引有效
        if (index < 0) {
            index = 0;
        } else if (index >= instance.images.length) {
            index = instance.images.length - 1;
        }

        instance.currentIndex = index;

        const lightbox = document.getElementById(instance.id);
        const lightboxImage = document.getElementById(instance.imageId);
        const lightboxCaption = instance.captionId ? document.getElementById(instance.captionId) : null;
        const lightboxCurrent = instance.currentId ? document.getElementById(instance.currentId) : null;
        const lightboxTotal = instance.totalId ? document.getElementById(instance.totalId) : null;

        if (!lightbox || !lightboxImage) {
            console.warn(`Lightbox: 找不到必要的 DOM 元素`);
            return;
        }

        const imageData = instance.images[index];

        // 設置圖片
        lightboxImage.src = imageData.url || '';
        lightboxImage.alt = imageData.alt || '';

        // 設置標題（如果存在）
        if (lightboxCaption) {
            if (imageData.caption) {
                lightboxCaption.textContent = imageData.caption;
                lightboxCaption.style.display = 'block';
            } else {
                lightboxCaption.style.display = 'none';
            }
        }

        // 設置計數器
        if (lightboxCurrent) {
            lightboxCurrent.textContent = index + 1;
        }

        if (lightboxTotal) {
            lightboxTotal.textContent = instance.images.length;
        }

        // 顯示 Lightbox
        lightbox.style.display = 'flex';
        document.body.style.overflow = 'hidden';

        // 綁定鍵盤事件（如果還沒有綁定）
        if (!document._lightboxKeyboardBound) {
            document.addEventListener('keydown', handleLightboxKeyboard);
            document._lightboxKeyboardBound = true;
        }
    }

    /**
     * 關閉 Lightbox
     * @param {string} lightboxId - Lightbox 實例 ID
     */
    function closeLightbox(lightboxId) {
        const instance = lightboxInstances[lightboxId];
        if (!instance) {
            // 嘗試直接通過 ID 查找
            const lightbox = document.getElementById(lightboxId);
            if (lightbox) {
                lightbox.style.display = 'none';
                document.body.style.overflow = '';
            }
            return;
        }

        const lightbox = document.getElementById(instance.id);
        if (lightbox) {
            lightbox.style.display = 'none';
            document.body.style.overflow = '';
        }
    }

    /**
     * 切換圖片
     * @param {string} lightboxId - Lightbox 實例 ID
     * @param {number} direction - 方向（-1 為上一張，1 為下一張）
     */
    function changeLightboxImage(lightboxId, direction) {
        const instance = lightboxInstances[lightboxId];
        if (!instance) return;

        instance.currentIndex += direction;

        // 循環切換
        if (instance.currentIndex < 0) {
            instance.currentIndex = instance.images.length - 1;
        } else if (instance.currentIndex >= instance.images.length) {
            instance.currentIndex = 0;
        }

        openLightbox(lightboxId, instance.currentIndex);
    }

    /**
     * 鍵盤控制
     */
    function handleLightboxKeyboard(e) {
        // 查找當前打開的 Lightbox
        const openLightbox = document.querySelector('.image-lightbox[style*="flex"]');
        if (!openLightbox) return;

        const lightboxId = openLightbox.id;
        const instance = lightboxInstances[lightboxId];
        
        if (!instance) {
            // 向後兼容：使用舊的全局函數
            if (window.changeLightboxImage && window.closeImageLightbox) {
                if (e.key === 'ArrowLeft') {
                    window.changeLightboxImage(-1);
                } else if (e.key === 'ArrowRight') {
                    window.changeLightboxImage(1);
                } else if (e.key === 'Escape') {
                    window.closeImageLightbox();
                }
            }
            return;
        }

        if (e.key === 'ArrowLeft') {
            changeLightboxImage(lightboxId, -1);
        } else if (e.key === 'ArrowRight') {
            changeLightboxImage(lightboxId, 1);
        } else if (e.key === 'Escape') {
            closeLightbox(lightboxId);
        }
    }

    // 向後兼容：導出舊的全局函數
    window.initLightbox = initLightbox;
    window.openImageLightbox = function(index) {
        openLightbox('imageLightbox', index);
    };
    window.closeImageLightbox = function(event) {
        if (event) {
            event.stopPropagation();
        }
        closeLightbox('imageLightbox');
    };
    window.changeLightboxImage = function(direction, event) {
        if (event) {
            event.stopPropagation();
        }
        changeLightboxImage('imageLightbox', direction);
    };

    // 導出新的 API
    window.Lightbox = {
        create: createLightboxInstance,
        open: openLightbox,
        close: closeLightbox,
        change: changeLightboxImage,
        init: initLightbox
    };
})();
