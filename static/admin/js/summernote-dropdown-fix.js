/**
 * Summernote 下拉選單修復腳本
 * 修復 iframe 模式下下拉選單不顯示的問題
 * 
 * @version 2.0
 * @optimized 2025
 */

(function() {
    'use strict';
    
    // 配置常數
    var CONFIG = {
        IFRAME_SELECTOR: 'iframe[src*="summernote/editor"]',
        TOOLBAR_SELECTOR: '.note-toolbar',
        BTN_GROUP_SELECTOR: '.note-btn-group',
        DROPDOWN_SELECTOR: '.note-dropdown-menu, .dropdown-menu',
        DROPDOWN_BTN_SELECTOR: 'button[data-toggle="dropdown"], button.dropdown-toggle, .dropdown-toggle',
        MAX_WAIT_COUNT: 20,
        WAIT_INTERVAL: 50,
        PROCESSING_TIMEOUT: 100,
        INIT_DELAY: 100,
        FALLBACK_DELAY: 300
    };
    
    // CSS 樣式（單次注入）
    var DROPDOWN_FIX_CSS = `
        body, html { overflow: visible !important; }
        .note-editor.note-frame { overflow: visible !important; }
        .note-editor.note-frame .note-toolbar { 
            overflow: visible !important; 
            position: relative !important; 
        }
        .note-btn-group { 
            position: relative !important; 
            overflow: visible !important; 
        }
        .note-dropdown-menu {
            position: absolute !important;
            top: 100% !important;
            left: 0 !important;
            z-index: 99999 !important;
            overflow: visible !important;
            transform: none !important;
            clip: auto !important;
            clip-path: none !important;
        }
        .note-btn-group.show .note-dropdown-menu,
        .note-dropdown-menu.show {
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            z-index: 99999 !important;
            position: absolute !important;
        }
        .note-btn-group.show { 
            z-index: 99998 !important; 
            position: relative !important; 
        }
    `;
    
    // 工具函數
    var Utils = {
        /**
         * 獲取 iframe 文檔
         */
        getIframeDoc: function(iframe) {
            try {
                return iframe.contentDocument || iframe.contentWindow.document;
            } catch(e) {
                return null;
            }
        },
        
        /**
         * 檢查元素是否可見
         */
        isElementVisible: function(element, iframeDoc) {
            if (!element || !iframeDoc) return false;
            
            try {
                var style = iframeDoc.defaultView.getComputedStyle(element);
                return style.display !== 'none' && 
                       style.visibility !== 'hidden' &&
                       style.opacity !== '0';
            } catch(e) {
                return false;
            }
        },
        
        /**
         * 檢查下拉選單是否打開
         */
        isDropdownOpen: function(btnGroup, dropdown, iframeDoc) {
            if (!btnGroup || !dropdown) return false;
            
            var hasShowClass = btnGroup.classList.contains('show') ||
                              dropdown.classList.contains('show');
            var hasAriaExpanded = btnGroup.getAttribute('aria-expanded') === 'true';
            var isVisible = Utils.isElementVisible(dropdown, iframeDoc);
            
            return hasShowClass || hasAriaExpanded || isVisible;
        },
        
        /**
         * 設置元素樣式（批量）
         */
        setStyles: function(element, styles) {
            if (!element) return;
            
            Object.keys(styles).forEach(function(prop) {
                element.style.setProperty(prop, styles[prop], 'important');
            });
        },
        
        /**
         * 查找下拉選單元素
         */
        findDropdown: function(btnGroup) {
            return btnGroup.querySelector(CONFIG.DROPDOWN_SELECTOR);
        },
        
        /**
         * 查找下拉按鈕
         */
        findDropdownButton: function(btnGroup, target) {
            var btn = btnGroup.querySelector(CONFIG.DROPDOWN_BTN_SELECTOR);
            if (!btn && target && target.tagName === 'BUTTON') {
                btn = target;
            }
            return btn;
        }
    };
    
    /**
     * 下拉選單管理器
     */
    var DropdownManager = {
        processingBtnGroups: new Set(),
        
        /**
         * 標記為正在處理
         */
        markProcessing: function(btnGroup) {
            this.processingBtnGroups.add(btnGroup);
        },
        
        /**
         * 取消處理標記
         */
        unmarkProcessing: function(btnGroup) {
            var self = this;
            setTimeout(function() {
                self.processingBtnGroups.delete(btnGroup);
            }, CONFIG.PROCESSING_TIMEOUT);
        },
        
        /**
         * 檢查是否正在處理
         */
        isProcessing: function(btnGroup) {
            return this.processingBtnGroups.has(btnGroup);
        },
        
        /**
         * 關閉下拉選單
         */
        close: function(btnGroup, dropdown, btn) {
            // 移除所有樣式屬性，讓 CSS 控制
            dropdown.style.removeProperty('display');
            dropdown.style.removeProperty('visibility');
            dropdown.style.removeProperty('opacity');
            dropdown.style.removeProperty('z-index');
            
            // 移除類名
            btnGroup.classList.remove('show', 'open');
            dropdown.classList.remove('show');
            
            // 更新屬性
            btnGroup.setAttribute('aria-expanded', 'false');
            
            if (btn) {
                btn.setAttribute('aria-expanded', 'false');
            }
            
            // 強制隱藏（最後一步）
            setTimeout(function() {
                Utils.setStyles(dropdown, {
                    'display': 'none',
                    'visibility': 'hidden',
                    'opacity': '0'
                });
            }, 50);
        },
        
        /**
         * 打開下拉選單
         */
        open: function(btnGroup, dropdown, btn, iframeDoc) {
            // 先設置類名和屬性（讓 CSS 生效）
            btnGroup.classList.add('show', 'open');
            dropdown.classList.add('show');
            btnGroup.setAttribute('aria-expanded', 'true');
            
            if (btn) {
                btn.setAttribute('aria-expanded', 'true');
            }
            
            // 然後強制設置樣式
            var dropdownStyles = {
                'display': 'block',
                'visibility': 'visible',
                'opacity': '1',
                'z-index': '99999',
                'position': 'absolute',
                'top': '100%',
                'left': '0',
                'overflow': 'visible',
                'transform': 'none',
                'clip': 'auto',
                'clip-path': 'none',
                'pointer-events': 'auto',
                'margin-top': '1px'
            };
            
            Utils.setStyles(dropdown, dropdownStyles);
            
            // 設置按鈕組樣式
            var btnGroupStyles = {
                'z-index': '99998',
                'position': 'relative',
                'overflow': 'visible'
            };
            
            Utils.setStyles(btnGroup, btnGroupStyles);
            
            // 確保父容器不限制
            var toolbar = btnGroup.closest('.note-toolbar');
            if (toolbar) {
                Utils.setStyles(toolbar, {
                    'overflow': 'visible',
                    'position': 'relative'
                });
            }
            
            var editor = btnGroup.closest('.note-editor');
            if (editor) {
                Utils.setStyles(editor, {
                    'overflow': 'visible'
                });
            }
            
            // 確保 iframe body 不限制
            if (iframeDoc && iframeDoc.body) {
                iframeDoc.body.style.overflow = 'visible';
            }
        },
        
        /**
         * 切換下拉選單狀態
         */
        toggle: function(btnGroup, iframeDoc, e) {
            // 防止重複處理
            if (this.isProcessing(btnGroup)) {
                return;
            }
            
            var dropdown = Utils.findDropdown(btnGroup);
            if (!dropdown) return;
            
            var target = e.target;
            var btn = Utils.findDropdownButton(btnGroup, target);
            
            // 檢查是否點擊了下拉選單內部
            if (dropdown.contains(target)) {
                return; // 點擊選單項，不處理
            }
            
            // 檢查是否點擊了按鈕
            if (!btn || (!btn.contains(target) && target !== btn)) {
                // 如果點擊的不是按鈕，關閉所有下拉選單
                var allBtnGroups = iframeDoc.querySelectorAll(CONFIG.BTN_GROUP_SELECTOR);
                allBtnGroups.forEach(function(group) {
                    var menu = Utils.findDropdown(group);
                    if (menu && Utils.isDropdownOpen(group, menu, iframeDoc)) {
                        DropdownManager.close(group, menu, null);
                    }
                });
                return;
            }
            
            // 標記為正在處理
            this.markProcessing(btnGroup);
            
            // 先關閉其他打開的下拉選單
            var allBtnGroups = iframeDoc.querySelectorAll(CONFIG.BTN_GROUP_SELECTOR);
            var self = this;
            allBtnGroups.forEach(function(group) {
                if (group !== btnGroup) {
                    var menu = Utils.findDropdown(group);
                    if (menu && Utils.isDropdownOpen(group, menu, iframeDoc)) {
                        self.close(group, menu, null);
                    }
                }
            });
            
            // 檢查當前狀態
            var isOpen = Utils.isDropdownOpen(btnGroup, dropdown, iframeDoc);
            
            // 使用 setTimeout 確保狀態檢查準確
            setTimeout(function() {
                if (isOpen) {
                    DropdownManager.close(btnGroup, dropdown, btn);
                } else {
                    DropdownManager.open(btnGroup, dropdown, btn, iframeDoc);
                }
                
                // 取消處理標記
                DropdownManager.unmarkProcessing(btnGroup);
            }, 10);
            
            // 阻止事件傳播
            e.stopPropagation();
            e.preventDefault();
        }
    };
    
    /**
     * iframe 修復器
     */
    var IframeFixer = {
        /**
         * 注入 CSS 樣式
         */
        injectCSS: function(iframeDoc) {
            if (iframeDoc.getElementById('summernote-dropdown-fix-style')) {
                return;
            }
            
            var style = iframeDoc.createElement('style');
            style.id = 'summernote-dropdown-fix-style';
            style.textContent = DROPDOWN_FIX_CSS;
            
            if (iframeDoc.head) {
                iframeDoc.head.appendChild(style);
            }
        },
        
        /**
         * 設置事件監聽器
         */
        setupEventListeners: function(iframeDoc, iframeBody) {
            var self = this;
            
            // 主要點擊事件處理（捕獲階段，優先執行）
            iframeBody.addEventListener('click', function(e) {
                var target = e.target;
                var btnGroup = target.closest(CONFIG.BTN_GROUP_SELECTOR);
                
                if (btnGroup) {
                    DropdownManager.toggle(btnGroup, iframeDoc, e);
                } else {
                    // 點擊外部區域，關閉所有下拉選單
                    var allBtnGroups = iframeDoc.querySelectorAll(CONFIG.BTN_GROUP_SELECTOR);
                    allBtnGroups.forEach(function(group) {
                        var dropdown = Utils.findDropdown(group);
                        if (dropdown && Utils.isDropdownOpen(group, dropdown, iframeDoc)) {
                            DropdownManager.close(group, dropdown, null);
                        }
                    });
                }
            }, true);
            
            // 處理下拉選單項點擊
            iframeBody.addEventListener('click', function(e) {
                var target = e.target;
                var dropdown = target.closest(CONFIG.DROPDOWN_SELECTOR);
                
                if (dropdown) {
                    // 點擊選單項後關閉下拉選單
                    var btnGroup = dropdown.closest(CONFIG.BTN_GROUP_SELECTOR);
                    if (btnGroup) {
                        var btn = Utils.findDropdownButton(btnGroup, null);
                        setTimeout(function() {
                            DropdownManager.close(btnGroup, dropdown, btn);
                        }, 100);
                    }
                }
            }, false);
        },
        
        /**
         * 等待 Summernote 載入
         */
        waitForSummernote: function(iframeDoc, callback) {
            var waitCount = 0;
            
            function check() {
                var toolbar = iframeDoc.querySelector(CONFIG.TOOLBAR_SELECTOR);
                
                if (toolbar || waitCount >= CONFIG.MAX_WAIT_COUNT) {
                    callback();
                } else {
                    waitCount++;
                    setTimeout(check, CONFIG.WAIT_INTERVAL);
                }
            }
            
            check();
        },
        
        /**
         * 修復 iframe
         */
        fix: function(iframe) {
            try {
                var iframeDoc = Utils.getIframeDoc(iframe);
                if (!iframeDoc || !iframeDoc.body) return;
                
                var iframeBody = iframeDoc.body;
                
                // 修復 overflow
                iframeBody.style.overflow = 'visible';
                if (iframeDoc.documentElement) {
                    iframeDoc.documentElement.style.overflow = 'visible';
                }
                
                // 等待 Summernote 載入
                this.waitForSummernote(iframeDoc, function() {
                    IframeFixer.injectCSS(iframeDoc);
                    IframeFixer.setupEventListeners(iframeDoc, iframeBody);
                });
                
            } catch(e) {
                // 忽略跨域錯誤
            }
        }
    };
    
    /**
     * 初始化器
     */
    var Initializer = {
        /**
         * 設置 iframe 修復
         */
        setupIframeFix: function(iframe) {
            if (iframe.dataset.fixed) return;
            iframe.dataset.fixed = 'true';
            
            // 如果 iframe 已載入
            if (iframe.contentDocument && iframe.contentDocument.readyState === 'complete') {
                setTimeout(function() {
                    IframeFixer.fix(iframe);
                }, CONFIG.INIT_DELAY);
            } else {
                iframe.addEventListener('load', function() {
                    setTimeout(function() {
                        IframeFixer.fix(iframe);
                    }, CONFIG.INIT_DELAY);
                });
            }
            
            // 備用：立即嘗試
            setTimeout(function() {
                try {
                    var iframeDoc = Utils.getIframeDoc(iframe);
                    if (iframeDoc && iframeDoc.body) {
                        IframeFixer.fix(iframe);
                    }
                } catch(e) {}
            }, CONFIG.FALLBACK_DELAY);
        },
        
        /**
         * 初始化
         */
        init: function() {
            var iframes = document.querySelectorAll(CONFIG.IFRAME_SELECTOR);
            iframes.forEach(this.setupIframeFix.bind(this));
            
            // 監聽新添加的 iframe
            var observer = new MutationObserver(function() {
                var newIframes = document.querySelectorAll(CONFIG.IFRAME_SELECTOR);
                newIframes.forEach(function(iframe) {
                    if (!iframe.dataset.fixed) {
                        Initializer.setupIframeFix(iframe);
                    }
                });
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        }
    };
    
    // 啟動
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', Initializer.init.bind(Initializer));
    } else {
        Initializer.init();
    }
    
    // 延遲初始化以確保 Summernote 已載入
    setTimeout(Initializer.init.bind(Initializer), CONFIG.FALLBACK_DELAY);
})();
