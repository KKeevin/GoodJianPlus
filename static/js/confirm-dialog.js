/**
 * 自訂確認對話框
 * 提供美觀的確認對話框，替代原生 confirm()
 */

(function() {
    'use strict';

    /**
     * 顯示確認對話框
     * @param {string} message - 顯示的訊息
     * @param {string} title - 對話框標題（可選，預設為「確認操作」）
     * @param {string} icon - 圖示類別（可選，預設為「bi-question-circle」）
     * @param {string} type - 按鈕類型：'default'（確認/取消）或 'danger'（刪除/取消）
     * @param {string} confirmText - 確認按鈕文字（可選）
     * @param {string} cancelText - 取消按鈕文字（可選）
     * @returns {Promise<boolean>} - 返回 Promise，確認為 true，取消為 false
     */
    function showConfirmDialog(message, title = '確認操作', icon = 'bi-question-circle', type = 'default', confirmText = '確認', cancelText = '取消') {
        return new Promise((resolve) => {
            // 創建遮罩層
            const overlay = document.createElement('div');
            overlay.className = 'confirm-dialog-overlay';
            
            // 創建對話框
            const dialog = document.createElement('div');
            dialog.className = 'confirm-dialog';
            
            // 確定按鈕樣式類別
            const confirmBtnClass = type === 'danger' ? 'confirm-dialog-btn-danger' : 'confirm-dialog-btn-confirm';
            const confirmIcon = type === 'danger' ? 'bi-trash' : 'bi-check-circle';
            
            // 對話框 HTML
            dialog.innerHTML = `
                <div class="confirm-dialog-header">
                    <div class="confirm-dialog-icon">
                        <i class="bi ${icon}"></i>
                    </div>
                    <h3 class="confirm-dialog-title">${title}</h3>
                </div>
                <div class="confirm-dialog-body">
                    <p class="confirm-dialog-message">${message}</p>
                </div>
                <div class="confirm-dialog-footer">
                    <button class="confirm-dialog-btn confirm-dialog-btn-cancel" type="button">
                        <i class="bi bi-x-circle"></i>
                        <span>${cancelText}</span>
                    </button>
                    <button class="confirm-dialog-btn ${confirmBtnClass}" type="button">
                        <i class="bi ${confirmIcon}"></i>
                        <span>${confirmText}</span>
                    </button>
                </div>
            `;
            
            overlay.appendChild(dialog);
            document.body.appendChild(overlay);
            
            // 確認按鈕事件
            const confirmBtn = dialog.querySelector(`.${confirmBtnClass}`);
            confirmBtn.addEventListener('click', () => {
                closeDialog(true);
            });
            
            // 取消按鈕事件
            const cancelBtn = dialog.querySelector('.confirm-dialog-btn-cancel');
            cancelBtn.addEventListener('click', () => {
                closeDialog(false);
            });
            
            // ESC 鍵關閉
            const handleEsc = (e) => {
                if (e.key === 'Escape') {
                    closeDialog(false);
                }
            };
            document.addEventListener('keydown', handleEsc);
            
            // 關閉對話框函數
            function closeDialog(result) {
                overlay.classList.add('closing');
                dialog.classList.add('closing');
                
                setTimeout(() => {
                    if (overlay.parentNode) {
                        document.body.removeChild(overlay);
                    }
                    document.removeEventListener('keydown', handleEsc);
                    resolve(result);
                }, 200);
            }
            
            // 聚焦確認按鈕
            setTimeout(() => {
                confirmBtn.focus();
            }, 100);
        });
    }
    
    /**
     * 便捷函數：替換原生 confirm()
     * 使用方式：if (await confirmDialog('確定要刪除嗎？')) { ... }
     */
    window.confirmDialog = function(message, title, type = 'default') {
        if (type === 'danger') {
            return showConfirmDialog(message, title || '確認刪除', 'bi-exclamation-triangle', 'danger', '刪除', '取消');
        }
        return showConfirmDialog(message, title || '確認操作', 'bi-question-circle', 'default', '確認', '取消');
    };
})();

