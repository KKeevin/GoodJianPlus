document.addEventListener('DOMContentLoaded', function() {
    const batchActionsToolbar = document.getElementById('batchActionsToolbar');
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const selectedCount = document.getElementById('selectedCount');
    const notificationCheckboxes = document.querySelectorAll('.notification-checkbox');
    
    // 更新選中數量
    function updateSelectedCount() {
        const checked = document.querySelectorAll('.notification-checkbox:checked');
        const count = checked.length;
        if (selectedCount) {
            selectedCount.innerHTML = '已選擇 <strong>' + count + '</strong> 項';
        }
        
        // 顯示/隱藏批量操作工具欄
        if (batchActionsToolbar) {
            if (count > 0) {
                batchActionsToolbar.style.display = 'flex';
            } else {
                batchActionsToolbar.style.display = 'none';
            }
        }
        
        // 更新全選狀態
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = count === notificationCheckboxes.length && notificationCheckboxes.length > 0;
            selectAllCheckbox.indeterminate = count > 0 && count < notificationCheckboxes.length;
        }
    }
    
    // 初始化選中數量
    updateSelectedCount();
    
    // 全選/取消全選
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            notificationCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            updateSelectedCount();
        });
    }
    
    // 單個複選框變化
    notificationCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateSelectedCount();
        });
    });
    
    // 批量標記為已讀
    const batchMarkReadBtn = document.getElementById('batchMarkReadBtn');
    if (batchMarkReadBtn) {
        batchMarkReadBtn.addEventListener('click', function() {
            const checked = document.querySelectorAll('.notification-checkbox:checked');
            if (checked.length === 0) {
                alert('請選擇要操作的通知');
                return;
            }
            
            const notificationIds = Array.from(checked).map(cb => cb.dataset.notificationId);
            performBatchAction('mark_read', notificationIds);
        });
    }
    
    // 批量標記為未讀
    const batchMarkUnreadBtn = document.getElementById('batchMarkUnreadBtn');
    if (batchMarkUnreadBtn) {
        batchMarkUnreadBtn.addEventListener('click', function() {
            const checked = document.querySelectorAll('.notification-checkbox:checked');
            if (checked.length === 0) {
                alert('請選擇要操作的通知');
                return;
            }
            
            const notificationIds = Array.from(checked).map(cb => cb.dataset.notificationId);
            performBatchAction('mark_unread', notificationIds);
        });
    }
    
    // 批量刪除
    const batchDeleteBtn = document.getElementById('batchDeleteBtn');
    if (batchDeleteBtn) {
        batchDeleteBtn.addEventListener('click', async function() {
            const checked = document.querySelectorAll('.notification-checkbox:checked');
            if (checked.length === 0) {
                alert('請選擇要操作的通知');
                return;
            }
            
            const confirmed = await confirmDialog('確定要刪除選中的 ' + checked.length + ' 則通知嗎？', '確認刪除', 'danger');
            if (!confirmed) return;
            
            const notificationIds = Array.from(checked).map(cb => cb.dataset.notificationId);
            performBatchAction('delete', notificationIds);
        });
    }
    
    // 執行批量操作
    function performBatchAction(action, notificationIds) {
        const formData = new URLSearchParams();
        formData.append('action', action);
        notificationIds.forEach(id => {
            formData.append('notification_ids', id);
        });
        
        fetch(window.NOTIFICATIONS_PAGE_CONFIG.batchActionUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': window.NOTIFICATIONS_PAGE_CONFIG.csrfToken
            },
            body: formData.toString()
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (action === 'delete') {
                    // 刪除操作：移除選中的項目
                    notificationIds.forEach(id => {
                        const item = document.querySelector(`.notification-item-page[data-notification-id="${id}"]`);
                        if (item) {
                            item.style.transition = 'opacity 0.3s';
                            item.style.opacity = '0';
                            setTimeout(() => {
                                item.remove();
                                checkEmptyList();
                            }, 300);
                        }
                    });
                } else {
                    // 標記已讀/未讀：更新UI並重新載入
                    location.reload();
                }
                
                // 重置選中狀態
                notificationCheckboxes.forEach(cb => cb.checked = false);
                updateSelectedCount();
                
                // 顯示成功訊息
                showToast(data.message, 'success');
            } else {
                showToast(data.message || '操作失敗', 'error');
            }
        })
        .catch(error => {
            console.error('Batch action failed:', error);
            showToast('操作失敗，請稍後再試', 'error');
        });
    }
    
    // 檢查列表是否為空
    function checkEmptyList() {
        const notificationList = document.querySelector('.notification-list-page');
        if (notificationList && notificationList.children.length === 0) {
            notificationList.innerHTML = '<div class="empty-notifications"><i class="bi bi-bell-slash"></i><p>目前沒有通知</p></div>';
        }
    }
    
    // 顯示Toast通知
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${type}`;
        toast.textContent = message;
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
            background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#17a2b8'};
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => toast.style.transform = 'translateX(0)', 100);
        
        setTimeout(() => {
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    // 標記全部為已讀
    const markAllReadPageBtn = document.getElementById('markAllReadPageBtn');
    if (markAllReadPageBtn) {
        markAllReadPageBtn.addEventListener('click', function() {
            fetch(window.NOTIFICATIONS_PAGE_CONFIG.markAllReadUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': window.NOTIFICATIONS_PAGE_CONFIG.csrfToken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                }
            })
            .catch(error => console.error('Mark all read failed:', error));
        });
    }

    // 標記已讀/未讀
    document.querySelectorAll('.btn-toggle-read-page').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const notificationId = this.dataset.notificationId;
            fetch(`/notifications/${notificationId}/toggle-read/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': window.NOTIFICATIONS_PAGE_CONFIG.csrfToken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const notificationItem = btn.closest('.notification-item-page');
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
                }
            })
            .catch(error => console.error('Toggle read failed:', error));
        });
    });

    // 刪除通知
    document.querySelectorAll('.btn-delete-page').forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.stopPropagation();
            const confirmed = await confirmDialog('確定要刪除此通知嗎？', '確認刪除', 'danger');
            if (!confirmed) return;
            
            const notificationId = this.dataset.notificationId;
            fetch(`/notifications/${notificationId}/delete/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': window.NOTIFICATIONS_PAGE_CONFIG.csrfToken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const notificationItem = btn.closest('.notification-item-page');
                    notificationItem.style.transition = 'opacity 0.3s';
                    notificationItem.style.opacity = '0';
                    setTimeout(() => {
                        notificationItem.remove();
                        const notificationList = document.querySelector('.notification-list-page');
                        if (notificationList && notificationList.children.length === 0) {
                            notificationList.innerHTML = '<div class="empty-notifications"><i class="bi bi-bell-slash"></i><p>目前沒有通知</p></div>';
                        }
                    }, 300);
                }
            })
            .catch(error => console.error('Delete notification failed:', error));
        });
    });
});

