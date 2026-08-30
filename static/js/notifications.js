/**
 * 通知相關功能
 * 處理通知的顯示、更新、標記已讀等功能
 */

(function() {
    'use strict';

    // 通知相關變數
    let lastNotificationId = null;
    let notificationCheckInterval = null;

    // 獲取已顯示過的通知ID列表（從 localStorage）
    function getSeenNotificationIds() {
        try {
            const seen = localStorage.getItem('seenNotificationIds');
            return seen ? JSON.parse(seen) : [];
        } catch (e) {
            return [];
        }
    }
    
    // 保存已顯示過的通知ID
    function markNotificationAsSeen(notificationId) {
        try {
            const seen = getSeenNotificationIds();
            if (!seen.includes(notificationId)) {
                seen.push(notificationId);
                // 只保留最近100個，避免 localStorage 過大
                if (seen.length > 100) {
                    seen.shift();
                }
                localStorage.setItem('seenNotificationIds', JSON.stringify(seen));
            }
        } catch (e) {
            console.error('Failed to save seen notification:', e);
        }
    }
    
    // 檢查通知是否已經被用戶完整看到過
    function hasNotificationBeenSeen(notificationId) {
        const seen = getSeenNotificationIds();
        return seen.includes(notificationId);
    }

    // 更新通知數量顯示
    function updateNotificationCount() {
        const notificationCountUrl = window.NOTIFICATION_CONFIG?.countUrl || '/api/notifications/unread-count/';
        
        fetch(notificationCountUrl)
            .then(response => response.json())
            .then(data => {
                const notificationCount = document.getElementById('notificationCount');
                if (notificationCount) {
                    if (data.success && data.unread_count > 0) {
                        notificationCount.textContent = data.unread_count > 99 ? '99+' : data.unread_count;
                        notificationCount.style.display = 'inline';
                    } else {
                        notificationCount.textContent = '0';
                        notificationCount.style.display = 'none';
                    }
                }
            })
            .catch(error => {
                console.error('Notification count update failed:', error);
                const notificationCount = document.getElementById('notificationCount');
                if (notificationCount) {
                    notificationCount.style.display = 'none';
                }
            });
    }
    
    // 檢查新通知並彈出
    function checkNewNotifications() {
        const notificationApiUrl = window.NOTIFICATION_CONFIG?.apiUrl || '/api/notifications/';
        
        fetch(notificationApiUrl)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.notifications.length > 0) {
                    // 找到最新的未讀通知
                    const unreadNotifications = data.notifications.filter(n => !n.is_read);
                    if (unreadNotifications.length > 0) {
                        // 過濾掉已經被用戶完整看到過的通知
                        const unseenNotifications = unreadNotifications.filter(n => !hasNotificationBeenSeen(n.id));
                        
                        if (unseenNotifications.length > 0) {
                            const latestUnseen = unseenNotifications[0];
                            
                            // 如果是新通知（不是當前正在顯示的）
                            if (latestUnseen.id !== lastNotificationId) {
                                lastNotificationId = latestUnseen.id;
                                showNotificationToast(latestUnseen);
                            }
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Check new notifications failed:', error);
            });
    }
    
    // 顯示通知彈出
    function showNotificationToast(notification) {
        const container = document.getElementById('notificationToastContainer');
        if (!container) {
            return;
        }
        
        // 創建通知元素
        const toast = document.createElement('div');
        toast.className = `notification-toast type-${notification.type} ${notification.is_read ? '' : 'unread'}`;
        toast.dataset.notificationId = notification.id;
        
        // 通知類型圖標
        const typeIcon = {
            'order': 'bi-box',
            'promotion': 'bi-tag',
            'system': 'bi-info-circle',
            'review': 'bi-star',
            'cart': 'bi-cart',
            'wishlist': 'bi-heart',
            'goal': 'bi-trophy',
            'stock': 'bi-box-seam'
        }[notification.type] || 'bi-bell';
        
        // 通知詳情 URL
        const detailUrl = `/notifications/${notification.id}/`;
        
        // 設置點擊事件 - 點擊後標記為已看過並跳轉
        toast.addEventListener('click', function() {
            markNotificationAsSeen(notification.id);
            window.location.href = detailUrl;
        });
        
        // 構建 HTML
        toast.innerHTML = `
            <div class="notification-toast-icon">
                <i class="bi ${typeIcon}"></i>
            </div>
            <div class="notification-toast-content">
                <div class="notification-toast-title">${escapeHtml(notification.title)}</div>
                <div class="notification-toast-message">${escapeHtml(notification.message)}</div>
                <div class="notification-toast-time">${notification.time_ago}</div>
            </div>
            <button class="notification-toast-close" onclick="event.stopPropagation(); window.NotificationManager.closeToast(this);" aria-label="關閉">
                <i class="bi bi-x"></i>
            </button>
            <div class="notification-toast-progress"></div>
        `;
        
        // 添加到容器
        container.appendChild(toast);
        
        // 追蹤通知狀態
        let isFullyDisplayed = false;
        let hasUserInteracted = false;
        let displayStartTime = Date.now();
        const minDisplayTime = 2000; // 至少顯示2秒才算完整顯示
        
        // 監聽動畫完成事件，確認通知已完整顯示
        toast.addEventListener('animationend', function() {
            isFullyDisplayed = true;
        }, { once: true });
        
        // 自動消失（5秒後）- 完整顯示並至少顯示2秒後才標記為已看過
        const autoCloseTimer = setTimeout(() => {
            const displayDuration = Date.now() - displayStartTime;
            if (isFullyDisplayed && !hasUserInteracted && displayDuration >= minDisplayTime) {
                // 通知完整顯示並自動消失，標記為已看過
                markNotificationAsSeen(notification.id);
                toast.dataset.autoMarkedAsSeen = 'true';
            }
            window.NotificationManager.closeToast(toast.querySelector('.notification-toast-close'), false);
        }, 5000);
        
        // 保存計時器以便手動關閉時清除
        toast.dataset.autoCloseTimer = autoCloseTimer;
        toast.dataset.notificationId = notification.id;
        toast.dataset.displayStartTime = displayStartTime;
        
        // 頁面卸載時檢查：如果通知還沒完整顯示足夠時間，不標記為已看過
        window.addEventListener('beforeunload', function() {
            const displayDuration = Date.now() - displayStartTime;
            if (!isFullyDisplayed || displayDuration < minDisplayTime) {
                // 通知還沒完整顯示，不標記為已看過，下次還會顯示
                return;
            }
        }, { once: true });
        
        // 更新通知數量
        updateNotificationCount();
    }
    
    // 關閉通知彈出
    function closeNotificationToast(closeBtn, isUserAction = true) {
        const toast = closeBtn ? closeBtn.closest('.notification-toast') : null;
        if (!toast) return;
        
        const notificationId = toast.dataset.notificationId;
        
        // 如果用戶手動關閉，標記為已看過
        if (notificationId && isUserAction) {
            markNotificationAsSeen(parseInt(notificationId));
        }
        // 如果是自動關閉，標記邏輯已經在 setTimeout 中處理了（通過 autoMarkedAsSeen 標記）
        
        // 清除自動關閉計時器
        if (toast.dataset.autoCloseTimer) {
            clearTimeout(parseInt(toast.dataset.autoCloseTimer));
        }
        
        // 添加關閉動畫
        toast.classList.add('closing');
        
        // 動畫結束後移除
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }

    // 載入通知列表
    function loadNotifications() {
        const notificationList = document.getElementById('notificationList');
        if (!notificationList) return;
        
        const notificationApiUrl = window.NOTIFICATION_CONFIG?.apiUrl || '/api/notifications/';
        
        notificationList.innerHTML = '<div class="notification-loading"><i class="bi bi-hourglass-split"></i> 載入中...</div>';
        
        fetch(notificationApiUrl)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (data.notifications.length === 0) {
                        notificationList.innerHTML = '<div class="notification-empty"><i class="bi bi-bell-slash"></i><p>目前沒有通知</p></div>';
                    } else {
                        let html = '';
                        data.notifications.forEach(notification => {
                            const readClass = notification.is_read ? 'read' : 'unread';
                            const typeIcon = {
                                'order': 'bi-box',
                                'promotion': 'bi-tag',
                                'system': 'bi-info-circle',
                                'review': 'bi-star',
                                'cart': 'bi-cart',
                                'wishlist': 'bi-heart',
                                'goal': 'bi-trophy',
                                'stock': 'bi-box-seam'
                            }[notification.type] || 'bi-bell';
                            
                            const detailUrl = '/notifications/' + notification.id + '/';
                            html += '<div class="notification-item ' + readClass + '" data-notification-id="' + notification.id + '">';
                            html += '<div class="notification-content" onclick="window.location.href=\'' + detailUrl + '\'">';
                            html += '<div class="notification-icon-wrapper">';
                            html += '<i class="bi ' + typeIcon + '"></i>';
                            html += '</div>';
                            html += '<div class="notification-text">';
                            html += '<div class="notification-title">' + notification.title + '</div>';
                            html += '<div class="notification-message">' + notification.message + '</div>';
                            html += '<div class="notification-time">' + notification.time_ago + '</div>';
                            html += '</div>';
                            html += '</div>';
                            html += '<div class="notification-actions">';
                            html += '<button class="btn-toggle-read" data-notification-id="' + notification.id + '" title="' + (notification.is_read ? '標記為未讀' : '標記為已讀') + '">';
                            html += '<i class="bi ' + (notification.is_read ? 'bi-envelope' : 'bi-envelope-open') + '"></i>';
                            html += '</button>';
                            html += '<button class="btn-delete-notification" data-notification-id="' + notification.id + '" title="刪除">';
                            html += '<i class="bi bi-trash"></i>';
                            html += '</button>';
                            html += '</div>';
                            html += '</div>';
                        });
                        notificationList.innerHTML = html;
                        
                        // 綁定事件
                        bindNotificationEvents();
                    }
                }
            })
            .catch(error => {
                console.error('Load notifications failed:', error);
                notificationList.innerHTML = '<div class="notification-error"><i class="bi bi-exclamation-triangle"></i><p>載入失敗</p></div>';
            });
    }

    // 綁定通知事件
    function bindNotificationEvents() {
        // 標記已讀/未讀
        document.querySelectorAll('.btn-toggle-read').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const notificationId = this.dataset.notificationId;
                toggleNotificationRead(notificationId, this);
            });
        });

        // 刪除通知
        document.querySelectorAll('.btn-delete-notification').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const notificationId = this.dataset.notificationId;
                deleteNotification(notificationId, this);
            });
        });
    }

    // 切換通知已讀/未讀狀態
    function toggleNotificationRead(notificationId, btn) {
        fetch(`/notifications/${notificationId}/toggle-read/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': window.CART_CONFIG?.csrfToken || getCsrfToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const notificationItem = btn.closest('.notification-item');
                if (data.is_read) {
                    notificationItem.classList.remove('unread');
                    notificationItem.classList.add('read');
                    btn.querySelector('i').className = 'bi bi-envelope';
                    btn.title = '標記為未讀';
                } else {
                    notificationItem.classList.remove('read');
                    notificationItem.classList.add('unread');
                    btn.querySelector('i').className = 'bi bi-envelope-open';
                    btn.title = '標記為已讀';
                }
                updateNotificationCount();
            }
        })
        .catch(error => console.error('Toggle read failed:', error));
    }

    // 刪除通知
    async function deleteNotification(notificationId, btn) {
        if (window.confirmDialog) {
            const confirmed = await confirmDialog('確定要刪除此通知嗎？', '確認刪除', 'danger');
            if (!confirmed) return;
        }
        
        fetch(`/notifications/${notificationId}/delete/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': window.CART_CONFIG?.csrfToken || getCsrfToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const notificationItem = btn.closest('.notification-item');
                notificationItem.style.transition = 'opacity 0.3s';
                notificationItem.style.opacity = '0';
                setTimeout(() => {
                    notificationItem.remove();
                    const notificationList = document.getElementById('notificationList');
                    if (notificationList && notificationList.children.length === 0) {
                        notificationList.innerHTML = '<div class="notification-empty"><i class="bi bi-bell-slash"></i><p>目前沒有通知</p></div>';
                    }
                }, 300);
                updateNotificationCount();
            }
        })
        .catch(error => console.error('Delete notification failed:', error));
    }

    // 標記全部為已讀
    function markAllNotificationsRead() {
        const markAllReadUrl = window.NOTIFICATION_CONFIG?.markAllReadUrl || '/api/notifications/mark-all-read/';
        
        fetch(markAllReadUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': window.CART_CONFIG?.csrfToken || getCsrfToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.querySelectorAll('.notification-item').forEach(item => {
                    item.classList.remove('unread');
                    item.classList.add('read');
                    const btn = item.querySelector('.btn-toggle-read');
                    if (btn) {
                        btn.querySelector('i').className = 'bi bi-envelope';
                        btn.title = '標記為未讀';
                    }
                });
                updateNotificationCount();
            }
        })
        .catch(error => console.error('Mark all read failed:', error));
    }

    // 初始化通知系統
    function initNotifications() {
        // 綁定標記全部為已讀按鈕
        const markAllReadBtn = document.getElementById('markAllReadBtn');
        if (markAllReadBtn) {
            markAllReadBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                markAllNotificationsRead();
            });
        }

        // 初始化通知數量
        updateNotificationCount();

        // 初始化最新通知 ID（避免頁面載入時彈出已有通知）
        const notificationApiUrl = window.NOTIFICATION_CONFIG?.apiUrl || '/api/notifications/';
        fetch(notificationApiUrl)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.notifications.length > 0) {
                    // 找到未讀且未被用戶完整看到過的通知
                    const unreadNotifications = data.notifications.filter(n => !n.is_read);
                    const unseenNotifications = unreadNotifications.filter(n => !hasNotificationBeenSeen(n.id));
                    
                    if (unseenNotifications.length > 0) {
                        // 立即顯示最新的未讀且未看過的通知
                        setTimeout(() => {
                            showNotificationToast(unseenNotifications[0]);
                            lastNotificationId = unseenNotifications[0].id;
                        }, 1000); // 延遲1秒顯示，讓頁面先載入完成
                    } else if (unreadNotifications.length > 0) {
                        // 如果有未讀通知但都已經看過，記錄ID但不顯示
                        lastNotificationId = unreadNotifications[0].id;
                    } else {
                        // 如果沒有未讀通知，記錄最新通知ID
                        lastNotificationId = data.notifications[0].id;
                    }
                }
            })
            .catch(error => console.error('Init notification ID failed:', error));

        // 定期檢查新通知（每30秒）
        notificationCheckInterval = setInterval(checkNewNotifications, 30000);
        
        // 頁面可見性改變時檢查（用戶切換回頁面時）
        document.addEventListener('visibilitychange', function() {
            if (!document.hidden) {
                checkNewNotifications();
                updateNotificationCount();
            }
        });
        
        // 頁面卸載時清除定時器
        window.addEventListener('beforeunload', function() {
            if (notificationCheckInterval) {
                clearInterval(notificationCheckInterval);
            }
        });
    }

    // 導出公共 API
    window.NotificationManager = {
        updateCount: updateNotificationCount,
        checkNew: checkNewNotifications,
        showToast: showNotificationToast,
        closeToast: closeNotificationToast,
        loadList: loadNotifications,
        init: initNotifications,
        markAllRead: markAllNotificationsRead
    };

    // 測試功能
    window.testNotification = function() {
        const testId = Math.floor(Math.random() * 1000000) + 1000000;
        const testNotif = {
            id: testId,
            type: 'system',
            title: '測試通知',
            message: '這是一個測試通知，用於驗證通知彈出功能是否正常工作。',
            time_ago: '剛剛',
            is_read: false
        };
        showNotificationToast(testNotif);
    };

    window.clearSeenNotifications = function() {
        localStorage.removeItem('seenNotificationIds');
    };

    // 當 DOM 載入完成後初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initNotifications);
    } else {
        initNotifications();
    }
})();

