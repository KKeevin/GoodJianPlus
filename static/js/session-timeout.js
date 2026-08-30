/**
 * 登入逾時管理
 * 當用戶15分鐘未進行任何操作時，自動登出並顯示逾時視窗
 */

(function() {
    'use strict';
    
    // 配置
    const CONFIG = {
        TIMEOUT_MINUTES: 15,  // 逾時時間（分鐘）
        CHECK_INTERVAL: 60000,  // 檢查間隔（毫秒，1分鐘）
        WARNING_TIME: 60000,  // 警告時間（毫秒，1分鐘前提醒）
        ACTIVITY_EVENTS: ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'],
    };
    
    // 狀態
    let lastActivityTime = Date.now();
    let timeoutTimer = null;
    let warningTimer = null;
    let checkInterval = null;
    let isModalShown = false;
    let isLoggedIn = false;
    
    /**
     * 初始化
     */
    function init() {
        // 檢查是否已登入
        checkLoginStatus();
        
        // 如果未登入，不需要監聽
        if (!isLoggedIn) {
            return;
        }
        
        // 設置活動監聽器
        setupActivityListeners();
        
        // 開始檢查逾時
        startTimeoutCheck();
        
        // 定期檢查登入狀態
        checkInterval = setInterval(checkLoginStatus, CONFIG.CHECK_INTERVAL);
    }
    
    /**
     * 檢查登入狀態
     */
    function checkLoginStatus() {
        // 檢查頁面中是否有登入相關的元素
        const loginLink = document.querySelector('a[href*="login"]');
        const logoutLink = document.querySelector('a[href*="logout"]');
        const userMenu = document.querySelector('.user-menu, .header-icon[title*="會員"]');
        
        // 如果有登出連結或用戶選單，表示已登入
        isLoggedIn = !!(logoutLink || (userMenu && !loginLink));
        
        // 如果已登入，更新活動時間
        if (isLoggedIn) {
            updateActivityTime();
        }
    }
    
    /**
     * 設置活動監聽器
     */
    function setupActivityListeners() {
        CONFIG.ACTIVITY_EVENTS.forEach(function(eventType) {
            document.addEventListener(eventType, handleActivity, true);
        });
        
        // 監聽頁面可見性變化
        document.addEventListener('visibilitychange', function() {
            if (!document.hidden && isLoggedIn) {
                updateActivityTime();
            }
        });
    }
    
    /**
     * 處理用戶活動
     */
    function handleActivity() {
        if (isLoggedIn && !isModalShown) {
            updateActivityTime();
        }
    }
    
    /**
     * 更新活動時間
     */
    function updateActivityTime() {
        lastActivityTime = Date.now();
        resetTimers();
    }
    
    /**
     * 重置計時器
     */
    function resetTimers() {
        clearTimeout(timeoutTimer);
        clearTimeout(warningTimer);
        startTimeoutCheck();
    }
    
    /**
     * 開始檢查逾時
     */
    function startTimeoutCheck() {
        if (!isLoggedIn || isModalShown) {
            return;
        }
        
        const timeoutMs = CONFIG.TIMEOUT_MINUTES * 60 * 1000;
        const elapsed = Date.now() - lastActivityTime;
        const remaining = timeoutMs - elapsed;
        
        if (remaining <= 0) {
            // 已經逾時
            showTimeoutModal();
        } else {
            // 設置逾時計時器
            timeoutTimer = setTimeout(function() {
                showTimeoutModal();
            }, remaining);
            
            // 設置警告計時器（提前1分鐘提醒）
            if (remaining > CONFIG.WARNING_TIME) {
                warningTimer = setTimeout(function() {
                    showWarning();
                }, remaining - CONFIG.WARNING_TIME);
            }
        }
    }
    
    /**
     * 顯示警告（可選功能）
     */
    function showWarning() {
        // 可以在這裡添加警告提示
        // 例如：顯示一個小的提示框
    }
    
    /**
     * 顯示逾時視窗
     */
    function showTimeoutModal() {
        if (isModalShown) {
            return;
        }
        
        isModalShown = true;
        
        // 創建視窗 HTML
        const modalHTML = `
            <div class="session-timeout-overlay" id="sessionTimeoutOverlay">
                <div class="session-timeout-modal">
                    <div class="session-timeout-icon">
                        <i class="bi bi-clock-history"></i>
                    </div>
                    <h2 class="session-timeout-title">登入逾時</h2>
                    <p class="session-timeout-message">
                        您已超過 15 分鐘未進行任何操作，為了您的帳號安全，系統已自動將您登出。
                        <br><br>
                        請選擇是否要重新登入？
                    </p>
                    <div class="session-timeout-actions">
                        <button class="session-timeout-btn session-timeout-btn-login" id="sessionTimeoutLoginBtn">
                            <i class="bi bi-box-arrow-in-right"></i> 重新登入
                        </button>
                        <button class="session-timeout-btn session-timeout-btn-stay" id="sessionTimeoutStayBtn">
                            <i class="bi bi-x-circle"></i> 保持登出
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // 添加到頁面
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // 設置按鈕事件
        const loginBtn = document.getElementById('sessionTimeoutLoginBtn');
        const stayBtn = document.getElementById('sessionTimeoutStayBtn');
        const overlay = document.getElementById('sessionTimeoutOverlay');
        
        // 重新登入按鈕
        loginBtn.addEventListener('click', function() {
            // 重定向到登入頁面，並保留當前頁面作為 next 參數
            const currentUrl = window.location.pathname + window.location.search;
            window.location.href = '/login/?next=' + encodeURIComponent(currentUrl);
        });
        
        // 保持登出按鈕
        stayBtn.addEventListener('click', function() {
            closeTimeoutModal();
        });
        
        // 點擊背景關閉（可選）
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) {
                closeTimeoutModal();
            }
        });
        
        // 阻止背景滾動
        document.body.style.overflow = 'hidden';
    }
    
    /**
     * 關閉逾時視窗
     */
    function closeTimeoutModal() {
        const overlay = document.getElementById('sessionTimeoutOverlay');
        if (overlay) {
            overlay.style.animation = 'fadeOut 0.3s ease-in-out';
            setTimeout(function() {
                overlay.remove();
                document.body.style.overflow = '';
                isModalShown = false;
            }, 300);
        }
    }
    
    /**
     * 清理
     */
    function cleanup() {
        clearTimeout(timeoutTimer);
        clearTimeout(warningTimer);
        if (checkInterval) {
            clearInterval(checkInterval);
        }
        CONFIG.ACTIVITY_EVENTS.forEach(function(eventType) {
            document.removeEventListener(eventType, handleActivity, true);
        });
    }
    
    // 頁面卸載時清理
    window.addEventListener('beforeunload', cleanup);
    
    // 當 DOM 載入完成後初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // 導出給外部使用（如果需要）
    window.SessionTimeout = {
        updateActivity: updateActivityTime,
        reset: resetTimers,
        closeModal: closeTimeoutModal
    };
})();

