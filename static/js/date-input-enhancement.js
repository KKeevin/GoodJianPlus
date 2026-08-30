/**
 * 日期輸入框增強功能
 * 讓整個 input 框都可以點擊來打開日期選擇器
 * 優化手機和平板版的觸控體驗
 */

(function() {
    'use strict';
    
    /**
     * 打開日期選擇器（兼容多種方法）
     */
    function openDatePicker(input) {
        // 方法 1：使用 showPicker API（現代瀏覽器，包括移動瀏覽器）
        if (input.showPicker && typeof input.showPicker === 'function') {
            try {
                input.showPicker();
                return true;
            } catch (err) {
                // showPicker 可能因為安全限制失敗，繼續嘗試其他方法
            }
        }
        
        // 方法 2：直接觸發 focus（某些瀏覽器會自動打開）
        try {
            input.focus();
            // 對於觸控設備，立即觸發 click 事件
            if ('ontouchstart' in window) {
                const clickEvent = new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: window
                });
                input.dispatchEvent(clickEvent);
            }
            return true;
        } catch (err) {
            // 忽略錯誤
        }
        
        return false;
    }
    
    /**
     * 增強單個日期輸入框
     */
    function enhanceDateInput(input) {
        // 避免重複增強
        if (input.dataset.dateEnhanced === 'true') {
            return;
        }
        
        // 標記為已增強
        input.dataset.dateEnhanced = 'true';
        input.classList.add('date-input-enhanced');
        
        // 設置樣式
        input.style.cursor = 'pointer';
        input.style.touchAction = 'manipulation'; // 優化觸控響應
        input.style.pointerEvents = 'auto';
        input.style.zIndex = '1';
        input.style.position = 'relative';
        
        // 用於追蹤觸控狀態
        let touchStartTime = 0;
        let touchStartY = 0;
        let touchStartX = 0;
        let isTouchDevice = 'ontouchstart' in window;
        let hasOpenedPicker = false; // 防止重複打開
        let touchTimeout = null; // 用於清除延遲觸發
        
        // 點擊事件（桌面和移動設備都支援）
        input.addEventListener('click', function(e) {
            // 如果已經通過觸控打開，則忽略 click 事件
            if (hasOpenedPicker) {
                hasOpenedPicker = false;
                return;
            }
            e.stopPropagation();
            // 立即執行
            hasOpenedPicker = openDatePicker(this);
        }, { passive: true, capture: false });
        
        // 觸控開始事件（移動設備）- 立即準備觸發
        input.addEventListener('touchstart', function(e) {
            touchStartTime = Date.now();
            touchStartY = e.touches[0].clientY;
            touchStartX = e.touches[0].clientX;
            hasOpenedPicker = false; // 重置標記
            
            // 清除之前的延遲觸發
            if (touchTimeout) {
                clearTimeout(touchTimeout);
                touchTimeout = null;
            }
            
            // 立即嘗試打開（如果瀏覽器支援）
            // 對於某些瀏覽器，在 touchstart 時就可以觸發
            if (this.showPicker && typeof this.showPicker === 'function') {
                try {
                    // 使用極短延遲，讓瀏覽器有時間處理 touchstart
                    touchTimeout = setTimeout(() => {
                        if (!hasOpenedPicker) {
                            hasOpenedPicker = openDatePicker(this);
                        }
                    }, 10); // 極短延遲，幾乎感覺不到
                } catch (err) {
                    // 忽略錯誤，等待 touchend
                }
            }
        }, { passive: true, capture: false });
        
        // 觸控結束事件（移動設備）- 立即響應
        input.addEventListener('touchend', function(e) {
            const touchEndTime = Date.now();
            const touchDuration = touchEndTime - touchStartTime;
            const touchEndY = e.changedTouches[0].clientY;
            const touchEndX = e.changedTouches[0].clientX;
            const touchDistanceY = Math.abs(touchEndY - touchStartY);
            const touchDistanceX = Math.abs(touchEndX - touchStartX);
            const touchDistance = Math.max(touchDistanceY, touchDistanceX);
            
            // 清除 touchstart 的延遲觸發
            if (touchTimeout) {
                clearTimeout(touchTimeout);
                touchTimeout = null;
            }
            
            // 快速點擊（< 300ms）且移動距離小（< 25px）時立即打開
            // 進一步放寬條件，讓觸控更容易觸發
            if (touchDuration < 300 && touchDistance < 25 && !hasOpenedPicker) {
                e.preventDefault();
                e.stopPropagation();
                // 立即執行，不延遲
                hasOpenedPicker = openDatePicker(this);
            }
        }, { passive: false, capture: false });
        
        // 觸控取消事件（處理意外取消）
        input.addEventListener('touchcancel', function(e) {
            if (touchTimeout) {
                clearTimeout(touchTimeout);
                touchTimeout = null;
            }
            hasOpenedPicker = false;
        }, { passive: true, capture: false });
        
        // 焦點事件（某些瀏覽器在獲得焦點時會自動打開）
        input.addEventListener('focus', function(e) {
            // 對於觸控設備，如果還沒打開，則嘗試打開
            if (isTouchDevice && !hasOpenedPicker) {
                // 使用 requestAnimationFrame 確保在下一幀執行，但幾乎無延遲
                requestAnimationFrame(() => {
                    if (document.activeElement === this && !hasOpenedPicker) {
                        hasOpenedPicker = openDatePicker(this);
                    }
                });
            }
        }, { passive: true, capture: false });
    }
    
    /**
     * 初始化所有日期輸入框
     */
    function initDateInputs() {
        const dateInputs = document.querySelectorAll('input[type="date"]');
        dateInputs.forEach(enhanceDateInput);
    }
    
    /**
     * 為動態添加的日期輸入框也添加增強功能
     */
    function observeNewDateInputs() {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) { // Element node
                        // 檢查新添加的節點是否是日期輸入框
                        if (node.tagName === 'INPUT' && node.type === 'date') {
                            enhanceDateInput(node);
                        }
                        // 檢查新添加的節點內部是否有日期輸入框
                        if (node.querySelectorAll) {
                            const dateInputs = node.querySelectorAll('input[type="date"]');
                            dateInputs.forEach(enhanceDateInput);
                        }
                    }
                });
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
    /**
     * 初始化函數
     */
    function init() {
        initDateInputs();
        observeNewDateInputs();
    }
    
    // 當 DOM 載入完成後初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // DOM 已經載入完成，立即執行
        setTimeout(init, 0);
    }
    
    // 導出函數供外部使用
    window.DateInputEnhancement = {
        init: initDateInputs,
        enhance: enhanceDateInput,
        openPicker: openDatePicker
    };
})();

