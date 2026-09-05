/**
 * 個人資料頁面相關功能
 * 處理密碼變更、標籤頁切換等功能
 */

(function() {
    'use strict';

    // 切換標籤頁
    function switchTab(event, tabName, updateHistory = true) {
        const targetTab = document.getElementById(`${tabName}-tab`);
        const tab = document.getElementById(`tab-${tabName}`);
        if (!targetTab || !tab) return;
        if (event) event.preventDefault();
        document.querySelectorAll('.account-nav [role="tab"]').forEach(button => {
            const active = button === tab;
            button.classList.toggle('active', active);
            button.setAttribute('aria-selected', String(active));
            button.tabIndex = active ? 0 : -1;
        });
        document.querySelectorAll('.account-panels > [role="tabpanel"]').forEach(panel => {
            panel.hidden = panel !== targetTab;
            panel.classList.toggle('active', panel === targetTab);
        });
        if (updateHistory) {
            const url = new URL(window.location.href);
            url.pathname = tab.pathname;
            url.search = tab.search;
            url.hash = '';
            history.pushState({}, '', url);
        }
    }

    function initAccountTabs() {
        const tabs = [...document.querySelectorAll('.account-nav [role="tab"]')];
        if (!tabs.length) return;
        tabs.forEach(tab => { tab.tabIndex = tab.classList.contains('active') ? 0 : -1; });
        document.querySelectorAll('[data-account-tab]').forEach(link => {
            link.addEventListener('click', event => {
                if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
                switchTab(event, link.dataset.accountTab);
                if (!link.closest('.account-nav')) document.getElementById(`tab-${link.dataset.accountTab}`).focus();
            });
        });
        tabs.forEach((tab, index) => tab.addEventListener('keydown', event => {
            let next;
            if (['ArrowRight', 'ArrowDown'].includes(event.key)) next = (index + 1) % tabs.length;
            if (['ArrowLeft', 'ArrowUp'].includes(event.key)) next = (index + tabs.length - 1) % tabs.length;
            if (event.key === 'Home') next = 0;
            if (event.key === 'End') next = tabs.length - 1;
            if (next !== undefined) {
                switchTab(event, tabs[next].dataset.accountTab);
                tabs[next].focus();
            }
        }));
        window.addEventListener('popstate', () => {
            const name = new URL(window.location.href).searchParams.get('tab') || 'info';
            switchTab(null, document.getElementById(`tab-${name}`) ? name : 'info', false);
        });
    }

    // 打開密碼變更模態視窗
    function openChangePasswordModal() {
        const modal = document.getElementById('changePasswordModal');
        if (!modal) return;
        
        modal.style.display = 'flex';
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
        
        // 確保所有元素都存在
        const form = document.getElementById('changePasswordForm');
        if (form) {
            form.reset();
            
            // 確保 errorDiv 存在
            let errorDiv = document.getElementById('passwordChangeError');
            if (!errorDiv) {
                errorDiv = document.createElement('div');
                errorDiv.id = 'passwordChangeError';
                errorDiv.className = 'alert alert-danger';
                errorDiv.style.cssText = 'display: none; margin-top: 15px;';
                form.appendChild(errorDiv);
            } else {
                errorDiv.style.display = 'none';
            }
            
            // 重置密碼顯示狀態
            ['old_password', 'new_password_modal', 'confirm_password_modal'].forEach(id => {
                const input = document.getElementById(id);
                if (input) input.type = 'password';
            });
            ['oldPasswordIcon', 'newPasswordModalIcon', 'confirmPasswordModalIcon'].forEach(id => {
                const icon = document.getElementById(id);
                if (icon) icon.className = 'bi bi-eye';
            });
        }
    }

    // 關閉密碼變更模態視窗
    function closeChangePasswordModal(event) {
        // 如果點擊的是模態視窗外部，才關閉
        if (event && event.target.id === 'changePasswordModal') {
            const modal = document.getElementById('changePasswordModal');
            if (modal) {
                modal.style.display = 'none';
                modal.classList.remove('show');
                document.body.style.overflow = '';
                const form = document.getElementById('changePasswordForm');
                if (form) form.reset();
                const errorDiv = document.getElementById('passwordChangeError');
                if (errorDiv) errorDiv.style.display = 'none';
            }
        } else if (!event) {
            // 直接調用關閉函數（點擊關閉按鈕或取消按鈕）
            const modal = document.getElementById('changePasswordModal');
            if (modal) {
                modal.style.display = 'none';
                modal.classList.remove('show');
                document.body.style.overflow = '';
                const form = document.getElementById('changePasswordForm');
                if (form) form.reset();
                const errorDiv = document.getElementById('passwordChangeError');
                if (errorDiv) errorDiv.style.display = 'none';
            }
        }
    }

    // 切換密碼顯示/隱藏
    function togglePassword(inputId, iconId) {
        const passwordInput = document.getElementById(inputId);
        const passwordIcon = document.getElementById(iconId);
        
        if (passwordInput && passwordIcon) {
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                passwordIcon.className = 'bi bi-eye-slash';
            } else {
                passwordInput.type = 'password';
                passwordIcon.className = 'bi bi-eye';
            }
        }
    }

    // 提交密碼變更
    function submitChangePassword(event) {
        // 防止事件冒泡
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        
        // 確保模態視窗已經顯示
        const modal = document.getElementById('changePasswordModal');
        if (!modal || modal.style.display === 'none' || !modal.classList.contains('show')) {
            console.error('模態視窗未顯示');
            if (typeof showToast === 'function') {
                showToast('請先打開重設密碼視窗', 'error');
            }
            return;
        }
        
        const form = document.getElementById('changePasswordForm');
        if (!form) {
            console.error('找不到表單元素 changePasswordForm');
            if (typeof showToast === 'function') {
                showToast('表單初始化錯誤：找不到表單，請重新整理頁面後再試', 'error');
            }
            return;
        }
        
        // 使用多種方式查找元素
        const oldPassword = document.getElementById('old_password') || form.querySelector('#old_password');
        const newPassword = document.getElementById('new_password_modal') || form.querySelector('#new_password_modal');
        const confirmPassword = document.getElementById('confirm_password_modal') || form.querySelector('#confirm_password_modal');
        let errorDiv = document.getElementById('passwordChangeError') || form.querySelector('#passwordChangeError');
        
        // 如果找不到 errorDiv，動態創建它
        if (!errorDiv && form) {
            errorDiv = document.createElement('div');
            errorDiv.id = 'passwordChangeError';
            errorDiv.className = 'alert alert-danger';
            errorDiv.style.cssText = 'display: none; margin-top: 15px;';
            form.appendChild(errorDiv);
        }
        
        const submitBtn = document.getElementById('submitChangePasswordBtn') || document.querySelector('#changePasswordModal .modal-footer .btn-primary');
        
        // 詳細檢查每個元素
        const missingElements = [];
        if (!oldPassword) missingElements.push('old_password');
        if (!newPassword) missingElements.push('new_password_modal');
        if (!confirmPassword) missingElements.push('confirm_password_modal');
        if (!errorDiv) missingElements.push('passwordChangeError');
        
        if (missingElements.length > 0) {
            console.error('找不到必要的表單元素:', missingElements);
            if (typeof showToast === 'function') {
                showToast('表單初始化錯誤：找不到以下元素 - ' + missingElements.join(', ') + '。請重新整理頁面後再試', 'error');
            }
            return;
        }
        
        const oldPasswordValue = oldPassword.value.trim();
        const newPasswordValue = newPassword.value.trim();
        const confirmPasswordValue = confirmPassword.value.trim();
        
        // 清空之前的錯誤
        errorDiv.style.display = 'none';
        errorDiv.textContent = '';
        errorDiv.className = 'alert alert-danger';
        
        // 驗證輸入
        if (!oldPasswordValue || !newPasswordValue || !confirmPasswordValue) {
            errorDiv.textContent = '請填寫完整資訊';
            errorDiv.style.display = 'block';
            return;
        }
        
        if (newPasswordValue.length < 8) {
            errorDiv.textContent = '新密碼長度至少需要 8 個字元';
            errorDiv.style.display = 'block';
            return;
        }
        
        if (newPasswordValue !== confirmPasswordValue) {
            errorDiv.textContent = '兩次輸入的新密碼不一致';
            errorDiv.style.display = 'block';
            return;
        }
        
        // 禁用按鈕並顯示載入狀態
        let originalBtnText = '';
        if (submitBtn) {
            originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="bi bi-arrow-repeat spin-icon"></i> 處理中...';
        }
        
        // 獲取 CSRF token
        let csrfToken = '';
        const csrfTokenElement = form.querySelector('[name=csrfmiddlewaretoken]') || document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfTokenElement && csrfTokenElement.value) {
            csrfToken = csrfTokenElement.value;
        } else if (typeof getCsrfToken === 'function') {
            csrfToken = getCsrfToken();
        }
        
        if (!csrfToken || csrfToken.trim() === '') {
            console.error('找不到 CSRF token');
            errorDiv.textContent = '系統錯誤：找不到安全令牌，請重新整理頁面後再試';
            errorDiv.style.display = 'block';
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            }
            return;
        }
        
        // 發送 AJAX 請求
        // URL 應該在模板中通過 data 屬性或全局變數提供
        const changePasswordUrl = (document.querySelector('[data-change-password-url]')?.dataset.changePasswordUrl) || 
                                   (window.PROFILE_CONFIG?.changePasswordUrl) || 
                                   '/profile/change-password/';
        
        fetch(changePasswordUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `old_password=${encodeURIComponent(oldPasswordValue)}&new_password=${encodeURIComponent(newPasswordValue)}&confirm_password=${encodeURIComponent(confirmPasswordValue)}`
        })
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => {
                    try {
                        const data = JSON.parse(text);
                        throw new Error(data.message || `HTTP ${response.status}: ${response.statusText}`);
                    } catch (e) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // 成功：顯示成功訊息並關閉模態視窗
                errorDiv.className = 'alert alert-success';
                errorDiv.style.cssText = 'display: block; padding: 12px 16px; border-radius: 8px; margin-top: 15px; background: #d4edda; color: #155724; border: 1px solid #c3e6cb;';
                errorDiv.innerHTML = `<i class="bi bi-check-circle-fill"></i> ${data.message}`;
                
                setTimeout(() => {
                    closeChangePasswordModal();
                    // 重新載入頁面以確保狀態更新
                    window.location.reload();
                }, 1500);
            } else {
                // 失敗：顯示錯誤訊息
                errorDiv.className = 'alert alert-danger';
                errorDiv.style.cssText = 'display: block; padding: 12px 16px; border-radius: 8px; margin-top: 15px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
                errorDiv.innerHTML = `<i class="bi bi-exclamation-triangle-fill"></i> ${data.message || '變更密碼失敗'}`;
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnText;
                }
            }
        })
        .catch(error => {
            console.error('請求錯誤:', error);
            errorDiv.className = 'alert alert-danger';
            errorDiv.style.cssText = 'display: block; padding: 12px 16px; border-radius: 8px; margin-top: 15px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
            errorDiv.innerHTML = `<i class="bi bi-exclamation-triangle-fill"></i> ${error.message || '處理過程中發生錯誤，請稍後再試'}`;
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            }
        });
    }

    // 設定密碼（僅限沒有密碼的用戶）
    function submitSetPassword() {
        const form = document.getElementById('setPasswordForm');
        const newPasswordInput = document.getElementById('new_password_set');
        const confirmPasswordInput = document.getElementById('confirm_password_set');
        const errorDiv = document.getElementById('setPasswordError');
        const submitBtn = document.getElementById('setPasswordBtn');
        
        if (!form || !newPasswordInput || !confirmPasswordInput) return;
        
        const newPassword = newPasswordInput.value.trim();
        const confirmPassword = confirmPasswordInput.value.trim();
        
        // 清除之前的錯誤訊息
        errorDiv.style.display = 'none';
        errorDiv.textContent = '';
        
        // 驗證輸入
        if (!newPassword) {
            errorDiv.textContent = '請輸入密碼';
            errorDiv.style.display = 'block';
            return;
        }
        
        if (newPassword.length < 8) {
            errorDiv.textContent = '密碼長度至少需要8個字元';
            errorDiv.style.display = 'block';
            return;
        }
        
        if (newPassword !== confirmPassword) {
            errorDiv.textContent = '兩次輸入的密碼不一致';
            errorDiv.style.display = 'block';
            return;
        }
        
        // 禁用按鈕並顯示載入狀態
        const originalBtnText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="bi bi-arrow-repeat spin-icon"></i> 處理中...';
        
        // 獲取 CSRF token
        let csrfToken = '';
        const csrfTokenElement = form.querySelector('[name=csrfmiddlewaretoken]') || document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfTokenElement && csrfTokenElement.value) {
            csrfToken = csrfTokenElement.value;
        } else if (typeof getCsrfToken === 'function') {
            csrfToken = getCsrfToken();
        }
        
        if (!csrfToken || csrfToken.trim() === '') {
            errorDiv.textContent = '系統錯誤：找不到安全令牌，請重新整理頁面後再試';
            errorDiv.style.display = 'block';
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
            return;
        }
        
        // 發送 AJAX 請求
        const setPasswordUrl = (document.querySelector('[data-set-password-url]')?.dataset.setPasswordUrl) || 
                                (window.PROFILE_CONFIG?.setPasswordUrl) || 
                                '/profile/set-password/';
        
        fetch(setPasswordUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `new_password=${encodeURIComponent(newPassword)}&confirm_password=${encodeURIComponent(confirmPassword)}`
        })
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => {
                    try {
                        const data = JSON.parse(text);
                        throw new Error(data.message || `HTTP ${response.status}: ${response.statusText}`);
                    } catch (e) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // 成功：顯示成功訊息並重新載入頁面
                errorDiv.className = 'alert alert-success';
                errorDiv.style.cssText = 'display: block; padding: 12px 16px; border-radius: 8px; margin-bottom: 15px; background: #d4edda; color: #155724; border: 1px solid #c3e6cb;';
                errorDiv.innerHTML = `<i class="bi bi-check-circle-fill"></i> ${data.message}`;
                
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                // 失敗：顯示錯誤訊息
                errorDiv.className = 'alert alert-danger';
                errorDiv.style.cssText = 'display: block; padding: 12px 16px; border-radius: 8px; margin-bottom: 15px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
                errorDiv.innerHTML = `<i class="bi bi-exclamation-triangle-fill"></i> ${data.message || '設定密碼失敗'}`;
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            }
        })
        .catch(error => {
            console.error('請求錯誤:', error);
            errorDiv.className = 'alert alert-danger';
            errorDiv.style.cssText = 'display: block; padding: 12px 16px; border-radius: 8px; margin-bottom: 15px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;';
            errorDiv.innerHTML = `<i class="bi bi-exclamation-triangle-fill"></i> ${error.message || '處理過程中發生錯誤，請稍後再試'}`;
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
        });
    }
    
    // 顯示密碼設定表單
    function showSetPasswordForm() {
        const formContainer = document.getElementById('setPasswordFormContainer');
        const showBtn = document.getElementById('showSetPasswordBtn');
        if (formContainer) {
            formContainer.style.display = 'block';
            // 平滑滾動到表單位置
            formContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
        if (showBtn) {
            showBtn.style.display = 'none';
        }
    }
    
    // 隱藏密碼設定表單
    function hideSetPasswordForm() {
        const formContainer = document.getElementById('setPasswordFormContainer');
        const showBtn = document.getElementById('showSetPasswordBtn');
        const form = document.getElementById('setPasswordForm');
        const errorDiv = document.getElementById('setPasswordError');
        
        if (formContainer) {
            formContainer.style.display = 'none';
        }
        if (showBtn) {
            showBtn.style.display = 'block';
        }
        if (form) {
            form.reset();
        }
        if (errorDiv) {
            errorDiv.style.display = 'none';
            errorDiv.textContent = '';
        }
    }
    
    // 將函數暴露到全局作用域
    window.submitSetPassword = submitSetPassword;
    window.showSetPasswordForm = showSetPasswordForm;
    window.hideSetPasswordForm = hideSetPasswordForm;

    // 發送手機驗證碼
    function sendPhoneVerificationCode() {
        const phoneInput = document.getElementById('phone-input');
        const sendBtn = document.getElementById('send-phone-code-btn');
        const verificationInput = document.getElementById('phone-verification-input');
        
        if (!phoneInput || !sendBtn) return;
        
        const phone = phoneInput.value.trim();
        
        // 驗證手機號碼格式
        if (!phone || !/^09\d{8}$/.test(phone)) {
            if (typeof showToast === 'function') {
                showToast('請輸入正確的手機號碼格式（09xxxxxxxx）', 'error');
            } else {
                alert('請輸入正確的手機號碼格式（09xxxxxxxx）');
            }
            return;
        }
        
        // 禁用按鈕並顯示載入狀態
        const originalBtnText = sendBtn.innerHTML;
        sendBtn.disabled = true;
        sendBtn.innerHTML = '<i class="bi bi-arrow-repeat spin-icon"></i> 發送中...';
        
        // 獲取 CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        
        fetch('/api/phone/send-code/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `phone=${encodeURIComponent(phone)}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 顯示驗證碼輸入框
                if (verificationInput) {
                    verificationInput.style.display = 'block';
                }
                if (typeof showToast === 'function') {
                    showToast(data.message || '驗證碼已發送', 'success');
                } else {
                    alert(data.message || '驗證碼已發送');
                }
            } else {
                if (typeof showToast === 'function') {
                    showToast(data.message || '發送失敗，請稍後再試', 'error');
                } else {
                    alert(data.message || '發送失敗，請稍後再試');
                }
                sendBtn.disabled = false;
                sendBtn.innerHTML = originalBtnText;
            }
        })
        .catch(error => {
            console.error('發送驗證碼錯誤:', error);
            if (typeof showToast === 'function') {
                showToast('發送過程中發生錯誤，請稍後再試', 'error');
            } else {
                alert('發送過程中發生錯誤，請稍後再試');
            }
            sendBtn.disabled = false;
            sendBtn.innerHTML = originalBtnText;
        });
    }
    
    // 驗證手機號碼
    function verifyPhone() {
        const phoneInput = document.getElementById('phone-input');
        const codeInput = document.getElementById('phone-verification-code');
        const verifyBtn = document.getElementById('verify-phone-btn');
        
        if (!phoneInput || !codeInput || !verifyBtn) return;
        
        const phone = phoneInput.value.trim();
        const code = codeInput.value.trim();
        
        // 驗證輸入
        if (!phone || !/^09\d{8}$/.test(phone)) {
            if (typeof showToast === 'function') {
                showToast('請輸入正確的手機號碼格式', 'error');
            } else {
                alert('請輸入正確的手機號碼格式');
            }
            return;
        }
        
        if (!code || code.length !== 6 || !/^\d{6}$/.test(code)) {
            if (typeof showToast === 'function') {
                showToast('請輸入6位數驗證碼', 'error');
            } else {
                alert('請輸入6位數驗證碼');
            }
            return;
        }
        
        // 禁用按鈕並顯示載入狀態
        const originalBtnText = verifyBtn.innerHTML;
        verifyBtn.disabled = true;
        verifyBtn.innerHTML = '<i class="bi bi-arrow-repeat spin-icon"></i> 驗證中...';
        
        // 獲取 CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        
        fetch('/api/phone/verify-in-profile/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `phone=${encodeURIComponent(phone)}&verification_code=${encodeURIComponent(code)}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (typeof showToast === 'function') {
                    showToast(data.message || '手機號碼驗證成功！', 'success');
                } else {
                    alert(data.message || '手機號碼驗證成功！');
                }
                // 重新載入頁面以更新驗證狀態
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                if (typeof showToast === 'function') {
                    showToast(data.message || '驗證失敗，請稍後再試', 'error');
                } else {
                    alert(data.message || '驗證失敗，請稍後再試');
                }
                verifyBtn.disabled = false;
                verifyBtn.innerHTML = originalBtnText;
            }
        })
        .catch(error => {
            console.error('驗證錯誤:', error);
            if (typeof showToast === 'function') {
                showToast('驗證過程中發生錯誤，請稍後再試', 'error');
            } else {
                alert('驗證過程中發生錯誤，請稍後再試');
            }
            verifyBtn.disabled = false;
            verifyBtn.innerHTML = originalBtnText;
        });
    }
    
    // 初始化
    function init() {
        // 初始化標籤頁滾動
        initAccountTabs();
        
        // 格式化價格
        if (typeof formatAllPrices === 'function') {
            formatAllPrices();
        }
        
        // 綁定手機驗證相關事件
        const sendPhoneCodeBtn = document.getElementById('send-phone-code-btn');
        const verifyPhoneBtn = document.getElementById('verify-phone-btn');
        const phoneCodeInput = document.getElementById('phone-verification-code');
        
        if (sendPhoneCodeBtn) {
            sendPhoneCodeBtn.addEventListener('click', sendPhoneVerificationCode);
        }
        
        if (verifyPhoneBtn) {
            verifyPhoneBtn.addEventListener('click', verifyPhone);
        }
        
        if (phoneCodeInput) {
            phoneCodeInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    verifyPhone();
                }
            });
        }
        
        // ESC 鍵關閉模態視窗
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                const modal = document.getElementById('changePasswordModal');
                if (modal && modal.classList.contains('show')) {
                    closeChangePasswordModal();
                }
            }
        });
    }

    // 啟用手機號碼編輯
    function enablePhoneEdit() {
        const phoneInput = document.getElementById('phone-input');
        const phoneEditHint = document.getElementById('phone-edit-hint');
        
        if (phoneInput && phoneEditHint) {
            phoneInput.disabled = false;
            phoneInput.removeAttribute('readonly');
            
            // 隱藏整個 form-help-text div
            const formHelpText = phoneEditHint.closest('.form-help-text');
            if (formHelpText) {
                formHelpText.style.display = 'none';
            }
            
            // 隱藏 phone-verification-section
            const phoneVerificationSection = document.querySelector('.phone-verification-section');
            if (phoneVerificationSection) {
                phoneVerificationSection.style.display = 'none';
            }
            
            // 添加提示訊息
            const formGroup = phoneInput.closest('.form-group');
            if (formGroup) {
                let editNotice = formGroup.querySelector('.phone-edit-notice');
                if (!editNotice) {
                    editNotice = document.createElement('small');
                    editNotice.className = 'form-text phone-edit-notice';
                    editNotice.style.cssText = 'display: block; margin-top: 5px; color: #667eea;';
                    editNotice.innerHTML = '<i class="bi bi-info-circle"></i> 手機號碼已啟用編輯，修改後請保存並重新驗證';
                    formGroup.appendChild(editNotice);
                }
            }
        }
    }
    
    // 導出到全局
    window.switchTab = switchTab;
    window.openChangePasswordModal = openChangePasswordModal;
    window.closeChangePasswordModal = closeChangePasswordModal;
    window.togglePassword = togglePassword;
    window.submitChangePassword = submitChangePassword;
    window.enablePhoneEdit = enablePhoneEdit;

    // 當 DOM 載入完成後初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
