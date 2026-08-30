/**
 * 覆蓋面板管理系統
 * 統一管理搜尋面板、通知面板、會員面板等覆蓋層
 */

(function() {
    'use strict';

    const OverlayManager = {
        currentPanel: null,
        
        init: function() {
            // 綁定所有觸發按鈕
            document.querySelectorAll('[data-panel]').forEach(trigger => {
                trigger.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const panelId = trigger.getAttribute('data-panel');
                    this.toggle(panelId, trigger);
                });
            });
            
            // 綁定所有關閉按鈕
            document.querySelectorAll('.overlay-close-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const panelId = btn.getAttribute('data-panel');
                    this.close(panelId);
                });
            });
            
            // 點擊外部關閉（僅桌面版）
            document.addEventListener('click', (e) => {
                if (window.innerWidth > 768 && this.currentPanel) {
                    const panel = document.getElementById(this.currentPanel);
                    const trigger = document.querySelector(`[data-panel="${this.currentPanel}"]`);
                    if (panel && trigger && 
                        !panel.contains(e.target) && 
                        !trigger.contains(e.target)) {
                        this.close(this.currentPanel);
                    }
                }
            });
            
            // ESC鍵關閉
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.currentPanel) {
                    this.close(this.currentPanel);
                }
            });

            // 通知面板特殊處理
            const notificationPanel = document.getElementById('notificationPanel');
            if (notificationPanel) {
                const observer = new MutationObserver(() => {
                    if (notificationPanel.classList.contains('active')) {
                        if (window.NotificationManager && typeof window.NotificationManager.loadList === 'function') {
                            window.NotificationManager.loadList();
                        }
                    }
                });
                observer.observe(notificationPanel, { attributes: true, attributeFilter: ['class'] });
            }
        },
        
        toggle: function(panelId, trigger) {
            const panel = document.getElementById(panelId);
            if (!panel) return;
            
            if (panel.classList.contains('active')) {
                this.close(panelId);
            } else {
                this.open(panelId, trigger);
            }
        },
        
        open: function(panelId, trigger) {
            // 關閉當前打開的面板
            if (this.currentPanel && this.currentPanel !== panelId) {
                this.close(this.currentPanel);
            }
            
            const panel = document.getElementById(panelId);
            if (!panel) return;
            
            panel.classList.add('active');
            this.currentPanel = panelId;
            
            // 移動端添加body類
            if (window.innerWidth <= 768) {
                document.body.classList.add('overlay-open');
            }
            
            // 搜尋面板自動聚焦
            if (panelId === 'searchPanel') {
                const input = document.getElementById('headerSearchInput');
                if (input) {
                    setTimeout(() => input.focus(), 150);
                }
            }
        },
        
        close: function(panelId) {
            const panel = document.getElementById(panelId);
            if (!panel) return;
            
            panel.classList.remove('active');
            if (this.currentPanel === panelId) {
                this.currentPanel = null;
            }
            
            document.body.classList.remove('overlay-open');
        }
    };
    
    // 導出到全局
    window.OverlayManager = OverlayManager;
    
    // 初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => OverlayManager.init());
    } else {
        OverlayManager.init();
    }
})();

