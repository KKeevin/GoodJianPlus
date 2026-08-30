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
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => toast.style.transform = 'translateX(0)', 100);
    
    setTimeout(() => {
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 保存表單原始值的變數
let originalFormData = null;

// 目標設定編輯
function editGoal() {
    const goalForm = document.getElementById('goalForm');
    const goalDisplay = document.getElementById('goalDisplay');
    if (goalForm && goalDisplay) {
        // 如果目標體重為空，自動填入目前體重
        const currentWeightInput = goalForm.querySelector('input[name="current_weight"]');
        const targetWeightInput = goalForm.querySelector('input[name="target_weight"]');
        if (currentWeightInput && targetWeightInput && !targetWeightInput.value && currentWeightInput.value) {
            targetWeightInput.value = currentWeightInput.value;
        }
        
        // 保存表單的原始值
        originalFormData = {};
        const formInputs = goalForm.querySelectorAll('input, select, textarea');
        formInputs.forEach(input => {
            if (input.name) {
                if (input.type === 'checkbox' || input.type === 'radio') {
                    originalFormData[input.name] = input.checked;
                } else {
                    originalFormData[input.name] = input.value;
                }
            }
        });
        
        goalForm.style.display = 'block';
        goalDisplay.style.display = 'none';
        
        // 確保按鈕狀態正確（重置按鈕）
        const submitBtn = goalForm.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-check-circle"></i> 儲存';
        }
    }
}

function cancelEditGoal() {
    const goalForm = document.getElementById('goalForm');
    const goalDisplay = document.getElementById('goalDisplay');
    if (goalForm && goalDisplay) {
        // 恢復表單到原始值
        if (originalFormData) {
            const formInputs = goalForm.querySelectorAll('input, select, textarea');
            formInputs.forEach(input => {
                if (input.name && originalFormData.hasOwnProperty(input.name)) {
                    if (input.type === 'checkbox' || input.type === 'radio') {
                        input.checked = originalFormData[input.name];
                    } else {
                        input.value = originalFormData[input.name];
                    }
                }
            });
        }
        
        goalForm.style.display = 'none';
        goalDisplay.style.display = 'block';
        
        // 重置按鈕狀態
        const submitBtn = goalForm.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-check-circle"></i> 儲存';
        }
    }
}

// 更新目標
document.getElementById('goalForm')?.addEventListener('submit', function(e) {
    e.preventDefault();
    const form = this;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerHTML;
    
    // 顯示載入狀態
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> 儲存中...';
    
    const formData = new FormData(form);
    
    fetch(window.GOALS_CONFIG.updateGoalUrl, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': window.GOALS_CONFIG.csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        // 無論成功或失敗，都要恢復按鈕狀態
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
        
                if (data.success) {
                    showToast('目標設定已更新', 'success');
                    // 更新顯示區域
                    updateGoalDisplay(data.goal);
                    // 清除保存的原始值（因為已經成功保存）
                    originalFormData = null;
                    // 切換回顯示模式
                    cancelEditGoal();
                } else {
                    showToast(data.message || '更新失敗', 'error');
                }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('更新失敗，請稍後再試', 'error');
        // 確保按鈕狀態恢復
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
    });
});

// 更新目標顯示區域
function updateGoalDisplay(goalData) {
    const goalDisplay = document.getElementById('goalDisplay');
    if (!goalDisplay) return;
    
    // 更新基本統計
    const statItems = goalDisplay.querySelectorAll('.stat-item');
    if (statItems.length >= 4) {
        statItems[0].querySelector('.stat-value').textContent = goalData.goal_type_display || '未設定';
        statItems[1].querySelector('.stat-value').textContent = goalData.current_weight ? parseFloat(goalData.current_weight).toFixed(1) + ' kg' : '未設定';
        statItems[2].querySelector('.stat-value').textContent = goalData.target_weight ? parseFloat(goalData.target_weight).toFixed(1) + ' kg' : '未設定';
        statItems[3].querySelector('.stat-value').textContent = goalData.activity_level_display || '未設定';
    }
    
    // 更新計算結果
    if (goalData.bmr) {
        let calculationResults = goalDisplay.querySelector('.calculation-results');
        if (!calculationResults) {
            // 如果不存在，創建計算結果區域
            const goalStats = goalDisplay.querySelector('.goal-stats');
            calculationResults = document.createElement('div');
            calculationResults.className = 'calculation-results';
            calculationResults.style.marginTop = '30px';
            calculationResults.style.paddingTop = '30px';
            calculationResults.style.borderTop = '2px solid #eee';
            goalDisplay.appendChild(calculationResults);
        }
        
        calculationResults.innerHTML = `
            <h3>計算結果</h3>
            <div class="result-grid">
                <div class="result-item">
                    <div class="result-label">基礎代謝率（BMR）</div>
                    <div class="result-value">${Math.round(goalData.bmr)} 大卡</div>
                </div>
                <div class="result-item">
                    <div class="result-label">總每日能量消耗（TDEE）</div>
                    <div class="result-value">${Math.round(goalData.tdee)} 大卡</div>
                </div>
            </div>
            ${goalData.target_calories ? `
            <div class="nutrition-targets" style="margin-top: 30px;">
                <h4>每日營養目標</h4>
                <div class="target-grid">
                    <div class="target-item">
                        <div class="target-label">目標熱量</div>
                        <div class="target-value">${Math.round(goalData.target_calories)} 大卡</div>
                    </div>
                    <div class="target-item">
                        <div class="target-label">蛋白質</div>
                        <div class="target-value">${goalData.target_protein ? goalData.target_protein.toFixed(1) : '0'} g</div>
                    </div>
                    <div class="target-item">
                        <div class="target-label">碳水化合物</div>
                        <div class="target-value">${goalData.target_carbs ? goalData.target_carbs.toFixed(1) : '0'} g</div>
                    </div>
                    <div class="target-item">
                        <div class="target-label">脂肪</div>
                        <div class="target-value">${goalData.target_fat ? goalData.target_fat.toFixed(1) : '0'} g</div>
                    </div>
                </div>
            </div>
            ` : ''}
        `;
    }
    
    // 更新身體組成目標
    if (goalData.current_muscle_percentage || goalData.target_muscle_percentage || 
        goalData.current_fat_percentage || goalData.target_fat_percentage ||
        goalData.current_bone_percentage || goalData.target_bone_percentage ||
        goalData.current_water_percentage || goalData.target_water_percentage) {
        
        let bodyCompositionSection = goalDisplay.querySelector('.body-composition-section');
        if (!bodyCompositionSection) {
            bodyCompositionSection = document.createElement('div');
            bodyCompositionSection.className = 'body-composition-section';
            bodyCompositionSection.style.marginTop = '30px';
            bodyCompositionSection.style.paddingTop = '30px';
            bodyCompositionSection.style.borderTop = '2px solid #eee';
            const calculationResults = goalDisplay.querySelector('.calculation-results');
            if (calculationResults) {
                calculationResults.insertAdjacentElement('afterend', bodyCompositionSection);
            } else {
                goalDisplay.appendChild(bodyCompositionSection);
            }
        }
        
        let compositionGrid = bodyCompositionSection.querySelector('.composition-grid');
        if (!compositionGrid) {
            bodyCompositionSection.innerHTML = '<h3 style="color: #2D5B69; margin-bottom: 20px;">身體組成目標</h3>';
            compositionGrid = document.createElement('div');
            compositionGrid.className = 'composition-grid';
            compositionGrid.style.cssText = 'display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;';
            bodyCompositionSection.appendChild(compositionGrid);
        }
        
        compositionGrid.innerHTML = '';
        
        // 肌肉比例
        if (goalData.current_muscle_percentage || goalData.target_muscle_percentage) {
            const muscleChange = goalData.current_muscle_percentage && goalData.target_muscle_percentage 
                ? (goalData.target_muscle_percentage - goalData.current_muscle_percentage).toFixed(1) 
                : null;
            compositionGrid.innerHTML += `
                <div class="composition-item" style="padding: 20px; background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); border-radius: 12px; border-left: 4px solid #4CAF50;">
                    <div class="composition-label" style="font-size: 0.9rem; color: #666; margin-bottom: 8px;">肌肉比例</div>
                    <div class="composition-current" style="font-size: 1.2rem; font-weight: 600; color: #2D5B69;">
                        目前: ${goalData.current_muscle_percentage || '未設定'}${goalData.current_muscle_percentage ? '%' : ''}
                        ${goalData.current_muscle_weight ? `<span style="font-size: 0.9rem; color: #666; margin-left: 8px;">(${parseFloat(goalData.current_muscle_weight).toFixed(1)} kg)</span>` : ''}
                    </div>
                    <div class="composition-target" style="font-size: 1.2rem; font-weight: 600; color: #4CAF50; margin-top: 5px;">
                        目標: ${goalData.target_muscle_percentage || '未設定'}${goalData.target_muscle_percentage ? '%' : ''}
                        ${goalData.target_muscle_weight ? `<span style="font-size: 0.9rem; color: #666; margin-left: 8px;">(${parseFloat(goalData.target_muscle_weight).toFixed(1)} kg)</span>` : ''}
                    </div>
                    ${muscleChange ? `
                    <div class="composition-change" style="font-size: 0.85rem; color: #666; margin-top: 8px;">
                        ${parseFloat(muscleChange) > 0 ? 
                            `<span style="color: #4CAF50;">↑ 提升 ${Math.abs(muscleChange)}%</span>` : 
                            parseFloat(muscleChange) < 0 ? 
                            `<span style="color: #f44336;">↓ 降低 ${Math.abs(muscleChange)}%</span>` : 
                            '<span>維持</span>'}
                    </div>
                    ` : ''}
                </div>
            `;
        }
        
        // 脂肪比例
        if (goalData.current_fat_percentage || goalData.target_fat_percentage) {
            const fatChange = goalData.current_fat_percentage && goalData.target_fat_percentage 
                ? (goalData.target_fat_percentage - goalData.current_fat_percentage).toFixed(1) 
                : null;
            compositionGrid.innerHTML += `
                <div class="composition-item" style="padding: 20px; background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); border-radius: 12px; border-left: 4px solid #ff9800;">
                    <div class="composition-label" style="font-size: 0.9rem; color: #666; margin-bottom: 8px;">脂肪比例</div>
                    <div class="composition-current" style="font-size: 1.2rem; font-weight: 600; color: #2D5B69;">
                        目前: ${goalData.current_fat_percentage || '未設定'}${goalData.current_fat_percentage ? '%' : ''}
                        ${goalData.current_fat_weight ? `<span style="font-size: 0.9rem; color: #666; margin-left: 8px;">(${parseFloat(goalData.current_fat_weight).toFixed(1)} kg)</span>` : ''}
                    </div>
                    <div class="composition-target" style="font-size: 1.2rem; font-weight: 600; color: #ff9800; margin-top: 5px;">
                        目標: ${goalData.target_fat_percentage || '未設定'}${goalData.target_fat_percentage ? '%' : ''}
                        ${goalData.target_fat_weight ? `<span style="font-size: 0.9rem; color: #666; margin-left: 8px;">(${parseFloat(goalData.target_fat_weight).toFixed(1)} kg)</span>` : ''}
                    </div>
                    ${fatChange ? `
                    <div class="composition-change" style="font-size: 0.85rem; color: #666; margin-top: 8px;">
                        ${parseFloat(fatChange) < 0 ? 
                            `<span style="color: #4CAF50;">↓ 降低 ${Math.abs(fatChange)}%</span>` : 
                            parseFloat(fatChange) > 0 ? 
                            `<span style="color: #f44336;">↑ 增加 ${Math.abs(fatChange)}%</span>` : 
                            '<span>維持</span>'}
                    </div>
                    ` : ''}
                </div>
            `;
        }
        
        // 骨骼比例
        if (goalData.current_bone_percentage || goalData.target_bone_percentage) {
            const boneChange = goalData.current_bone_percentage && goalData.target_bone_percentage 
                ? (goalData.target_bone_percentage - goalData.current_bone_percentage).toFixed(1) 
                : null;
            compositionGrid.innerHTML += `
                <div class="composition-item" style="padding: 20px; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-radius: 12px; border-left: 4px solid #2196f3;">
                    <div class="composition-label" style="font-size: 0.9rem; color: #666; margin-bottom: 8px;">骨骼比例</div>
                    <div class="composition-current" style="font-size: 1.2rem; font-weight: 600; color: #2D5B69;">
                        目前: ${goalData.current_bone_percentage || '未設定'}${goalData.current_bone_percentage ? '%' : ''}
                        ${goalData.current_bone_weight ? `<span style="font-size: 0.9rem; color: #666; margin-left: 8px;">(${parseFloat(goalData.current_bone_weight).toFixed(1)} kg)</span>` : ''}
                    </div>
                    <div class="composition-target" style="font-size: 1.2rem; font-weight: 600; color: #2196f3; margin-top: 5px;">
                        目標: ${goalData.target_bone_percentage || '未設定'}${goalData.target_bone_percentage ? '%' : ''}
                        ${goalData.target_bone_weight ? `<span style="font-size: 0.9rem; color: #666; margin-left: 8px;">(${parseFloat(goalData.target_bone_weight).toFixed(1)} kg)</span>` : ''}
                    </div>
                    ${boneChange ? `
                    <div class="composition-change" style="font-size: 0.85rem; color: #666; margin-top: 8px;">
                        ${parseFloat(boneChange) > 0 ? 
                            `<span style="color: #4CAF50;">↑ 提升 ${Math.abs(boneChange)}%</span>` : 
                            parseFloat(boneChange) < 0 ? 
                            `<span style="color: #f44336;">↓ 降低 ${Math.abs(boneChange)}%</span>` : 
                            '<span>維持</span>'}
                    </div>
                    ` : ''}
                </div>
            `;
        }
        
        // 水分比例
        if (goalData.current_water_percentage || goalData.target_water_percentage) {
            const waterChange = goalData.current_water_percentage && goalData.target_water_percentage 
                ? (goalData.target_water_percentage - goalData.current_water_percentage).toFixed(1) 
                : null;
            compositionGrid.innerHTML += `
                <div class="composition-item" style="padding: 20px; background: linear-gradient(135deg, #e0f2f1 0%, #b2dfdb 100%); border-radius: 12px; border-left: 4px solid #009688;">
                    <div class="composition-label" style="font-size: 0.9rem; color: #666; margin-bottom: 8px;">水分比例</div>
                    <div class="composition-current" style="font-size: 1.2rem; font-weight: 600; color: #2D5B69;">
                        目前: ${goalData.current_water_percentage || '未設定'}${goalData.current_water_percentage ? '%' : ''}
                        ${goalData.current_water_weight ? `<span style="font-size: 0.9rem; color: #666; margin-left: 8px;">(${parseFloat(goalData.current_water_weight).toFixed(1)} kg)</span>` : ''}
                    </div>
                    <div class="composition-target" style="font-size: 1.2rem; font-weight: 600; color: #009688; margin-top: 5px;">
                        目標: ${goalData.target_water_percentage || '未設定'}${goalData.target_water_percentage ? '%' : ''}
                        ${goalData.target_water_weight ? `<span style="font-size: 0.9rem; color: #666; margin-left: 8px;">(${parseFloat(goalData.target_water_weight).toFixed(1)} kg)</span>` : ''}
                    </div>
                    ${waterChange ? `
                    <div class="composition-change" style="font-size: 0.85rem; color: #666; margin-top: 8px;">
                        ${parseFloat(waterChange) > 0 ? 
                            `<span style="color: #4CAF50;">↑ 提升 ${Math.abs(waterChange)}%</span>` : 
                            parseFloat(waterChange) < 0 ? 
                            `<span style="color: #f44336;">↓ 降低 ${Math.abs(waterChange)}%</span>` : 
                            '<span>維持</span>'}
                    </div>
                    ` : ''}
                </div>
            `;
        }
    }
}

// 食物搜尋
let searchTimeout;
document.getElementById('foodSearchInput')?.addEventListener('input', function() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        searchFoods();
    }, 300);
});

document.getElementById('foodCategoryFilter')?.addEventListener('change', function() {
    searchFoods();
});

function searchFoods() {
    const query = document.getElementById('foodSearchInput').value;
    const category = document.getElementById('foodCategoryFilter').value;
    const resultsDiv = document.getElementById('foodSearchResults');
    
    let url = window.GOALS_CONFIG.foodSearchApiUrl + '?q=' + encodeURIComponent(query);
    if (category) {
        url += '&category=' + encodeURIComponent(category);
    }
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayFoodResults(data.foods);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            resultsDiv.innerHTML = '<div class="alert alert-danger">搜尋失敗</div>';
        });
}

function displayFoodResults(foods) {
    const resultsDiv = document.getElementById('foodSearchResults');
    if (foods.length === 0) {
        resultsDiv.innerHTML = '<div class="empty-state"><p>找不到相關食物</p></div>';
        return;
    }
    
    let html = '<div class="food-list">';
    foods.forEach(food => {
        html += `
            <div class="food-item" onclick="selectFood(${food.id}, '${food.name}', ${food.calories}, ${food.protein}, ${food.carbs}, ${food.fat})">
                <div class="food-name">${food.name}</div>
                <div class="food-info">
                    <span>${food.serving_size}</span> · 
                    <span>${food.calories} 大卡</span> · 
                    <span>蛋白質 ${food.protein}g</span>
                </div>
            </div>
        `;
    });
    html += '</div>';
    resultsDiv.innerHTML = html;
}

let selectedFood = null;
function selectFood(foodId, foodName, calories, protein, carbs, fat) {
    selectedFood = { id: foodId, name: foodName, calories, protein, carbs, fat };
    showAddFoodQuantityModal();
}

function showAddFoodQuantityModal() {
    // 創建數量輸入模態框
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'addFoodQuantityModal';
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">添加 ${selectedFood.name}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="addFoodForm">
                        <input type="hidden" name="food_id" value="${selectedFood.id}">
                        <div class="form-group">
                            <label>數量（份）</label>
                            <input type="number" name="quantity" class="form-control" value="1" step="0.1" min="0.1" required>
                        </div>
                        <div class="form-group">
                            <label>餐點類型</label>
                            <select name="meal_type" class="form-control" required>
                                <option value="breakfast">早餐</option>
                                <option value="lunch">午餐</option>
                                <option value="dinner">晚餐</option>
                                <option value="snack">點心</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>備註</label>
                            <textarea name="notes" class="form-control" rows="2"></textarea>
                        </div>
                        <div class="form-actions">
                            <button type="submit" class="btn btn-primary">添加</button>
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
    
    modal.addEventListener('hidden.bs.modal', function() {
        modal.remove();
    });
    
    document.getElementById('addFoodForm')?.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        
        // 獲取當前選擇的日期（如果沒有選擇，則使用今天）
        const datePicker = document.getElementById('nutritionDatePicker');
        const selectedDate = datePicker ? datePicker.value : null;
        if (selectedDate) {
            formData.append('logged_date', selectedDate);
        }
        
        fetch(window.GOALS_CONFIG.addNutritionLogUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': window.GOALS_CONFIG.csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log('Add nutrition log response:', data); // 調試用
            if (data.success) {
                showToast('食物已添加', 'success');
                bsModal.hide();
                // 更新營養攝取數據（使用當前選擇的日期）
                if (data.today_totals && data.logs) {
                    updateNutritionDisplay(data);
                    // 保持當前選擇的日期不變，重新載入該日期的數據
                    const datePicker = document.getElementById('nutritionDatePicker');
                    const selectedDate = datePicker ? datePicker.value : null;
                    if (selectedDate) {
                        // 重新載入該日期的數據以確保顯示正確
                        loadNutritionByDate(selectedDate);
                    }
                } else {
                    console.error('Missing data in response:', data);
                    setTimeout(() => location.reload(), 500);
                }
            } else {
                showToast(data.message || '添加失敗', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('添加失敗，請稍後再試', 'error');
        });
    });
}

// 載入指定日期的營養記錄
function loadNutritionByDate(dateStr) {
    if (!dateStr) {
        resetNutritionDate();
        return;
    }
    
    const selectedDate = new Date(dateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    selectedDate.setHours(0, 0, 0, 0);
    
    // 更新標題
    const dateTitle = document.getElementById('nutritionDateTitle');
    const logsTitle = document.getElementById('nutritionLogsTitle');
    
    if (selectedDate.getTime() === today.getTime()) {
        dateTitle.textContent = '今日營養攝取';
        logsTitle.textContent = '今日飲食記錄';
    } else {
        const dateFormatted = selectedDate.toLocaleDateString('zh-TW', { year: 'numeric', month: 'long', day: 'numeric' });
        dateTitle.textContent = dateFormatted + ' 營養攝取';
        logsTitle.textContent = dateFormatted + ' 飲食記錄';
    }
    
    // 載入數據
    fetch(window.GOALS_CONFIG.nutritionLogApiUrl + '?date=' + dateStr)
        .then(response => response.json())
        .then(data => {
            console.log('Nutrition log API response:', data); // 調試用
            if (data.success) {
                // 將 totals 轉換為 today_totals 以保持一致性
                if (data.totals && !data.today_totals) {
                    data.today_totals = data.totals;
                }
                updateNutritionDisplay(data);
            } else {
                showToast('載入失敗', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('載入失敗，請稍後再試', 'error');
        });
}

// 重置到今天的日期
function resetNutritionDate() {
    // 使用本地時間而不是UTC時間
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const today = `${year}-${month}-${day}`;
    
    document.getElementById('nutritionDatePicker').value = today;
    loadNutritionByDate(today);
}

// 更新營養顯示
function updateNutritionDisplay(data) {
    console.log('updateNutritionDisplay called with data:', data); // 調試用
    
    // 更新總計數據 - 支持 today_totals 和 totals（來自 nutrition_log_api）
    const totals = data.today_totals || data.totals;
    // 獲取每日目標 - 優先使用 data.targets，否則使用當前目標設定
    const targets = data.targets || (window.GOALS_CONFIG && window.GOALS_CONFIG.defaultTargets) || {
        calories: 0,
        protein: 0,
        carbs: 0,
        fat: 0
    };
    
    if (totals) {
        console.log('Updating totals:', totals); // 調試用
        console.log('Using targets:', targets); // 調試用
        
        // 更新熱量
        const caloriesCurrent = document.getElementById('nutritionCaloriesCurrent');
        const caloriesTarget = document.getElementById('nutritionCaloriesTarget');
        const caloriesProgress = document.getElementById('nutritionCaloriesProgress');
        
        if (caloriesCurrent) {
            caloriesCurrent.textContent = Math.round(totals.calories || 0);
        }
        if (caloriesTarget && targets.calories) {
            caloriesTarget.textContent = `/ ${Math.round(targets.calories)} 大卡`;
        }
        if (caloriesProgress && targets.calories && targets.calories > 0) {
            const percentage = Math.min((totals.calories / targets.calories) * 100, 100);
            caloriesProgress.style.width = percentage + '%';
        }
        
        // 更新蛋白質
        const proteinCurrent = document.getElementById('nutritionProteinCurrent');
        const proteinTarget = document.getElementById('nutritionProteinTarget');
        const proteinProgress = document.getElementById('nutritionProteinProgress');
        
        if (proteinCurrent) {
            proteinCurrent.textContent = (totals.protein || 0).toFixed(1);
        }
        if (proteinTarget && targets.protein) {
            proteinTarget.textContent = `/ ${parseFloat(targets.protein).toFixed(1)} g`;
        }
        if (proteinProgress && targets.protein && targets.protein > 0) {
            const percentage = Math.min((totals.protein / targets.protein) * 100, 100);
            proteinProgress.style.width = percentage + '%';
        }
        
        // 更新碳水化合物
        const carbsCurrent = document.getElementById('nutritionCarbsCurrent');
        const carbsTarget = document.getElementById('nutritionCarbsTarget');
        const carbsProgress = document.getElementById('nutritionCarbsProgress');
        
        if (carbsCurrent) {
            carbsCurrent.textContent = (totals.carbs || 0).toFixed(1);
        }
        if (carbsTarget && targets.carbs) {
            carbsTarget.textContent = `/ ${parseFloat(targets.carbs).toFixed(1)} g`;
        }
        if (carbsProgress && targets.carbs && targets.carbs > 0) {
            const percentage = Math.min((totals.carbs / targets.carbs) * 100, 100);
            carbsProgress.style.width = percentage + '%';
        }
        
        // 更新脂肪
        const fatCurrent = document.getElementById('nutritionFatCurrent');
        const fatTarget = document.getElementById('nutritionFatTarget');
        const fatProgress = document.getElementById('nutritionFatProgress');
        
        if (fatCurrent) {
            fatCurrent.textContent = (totals.fat || 0).toFixed(1);
        }
        if (fatTarget && targets.fat) {
            fatTarget.textContent = `/ ${parseFloat(targets.fat).toFixed(1)} g`;
        }
        if (fatProgress && targets.fat && targets.fat > 0) {
            const percentage = Math.min((totals.fat / targets.fat) * 100, 100);
            fatProgress.style.width = percentage + '%';
        }
    } else {
        console.error('No totals data found:', data);
    }
    
    // 更新記錄列表
    if (data.logs && Array.isArray(data.logs)) {
        const logsList = document.getElementById('nutritionLogsList');
        if (logsList) {
            if (data.logs.length === 0) {
                logsList.innerHTML = `
                    <div class="empty-state">
                        <i class="bi bi-inbox"></i>
                        <p>今天還沒有記錄任何食物</p>
                    </div>
                `;
            } else {
                logsList.innerHTML = data.logs.map(log => {
                    const mealTypeDisplay = log.meal_type_display || log.meal_type || '';
                    const mealTypeValue = log.meal_type || '';
                    const foodNameEscaped = (log.food_name || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
                    const notesEscaped = (log.notes || '').replace(/'/g, "\\'").replace(/"/g, '&quot;').replace(/\n/g, '\\n');
                    return `
                    <div class="log-item" data-log-id="${log.id}">
                        <div class="log-info">
                            <div class="log-food">${log.food_name}</div>
                            <div class="log-details">
                                <span>${log.quantity} 份</span> · 
                                <span>${mealTypeDisplay}</span> · 
                                <span>${Math.round(log.calories)} 大卡</span>
                            </div>
                        </div>
                        <div class="log-actions">
                            <button class="btn btn-sm btn-primary" onclick="editNutritionLog(${log.id}, '${foodNameEscaped}', ${log.quantity}, '${mealTypeValue}', '${notesEscaped}')" title="編輯">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deleteNutritionLog(${log.id})" title="刪除">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                `;
                }).join('');
            }
        }
    }
}

function showAddFoodModal() {
    const modal = new bootstrap.Modal(document.getElementById('addFoodModal'));
    modal.show();
    searchFoods(); // 初始載入
}

function showAddWeightModal() {
    const modal = new bootstrap.Modal(document.getElementById('addWeightModal'));
    modal.show();
    
    const goal = (window.GOALS_CONFIG && window.GOALS_CONFIG.goalPrefill) || {};
    
    // 預填體重
    const weightInput = document.getElementById('weightInput');
    if (weightInput && goal.current_weight) {
        weightInput.value = parseFloat(goal.current_weight).toFixed(1);
    }
    
    // 預填身高（只讀，來自目標設定）
    const heightInput = document.getElementById('heightInput');
    if (heightInput && goal.height) {
        heightInput.value = parseFloat(goal.height).toFixed(1);
    }
    
    // 預填肌肉比例
    const musclePercentageInput = document.getElementById('musclePercentageInput');
    if (musclePercentageInput && goal.current_muscle_percentage) {
        musclePercentageInput.value = parseFloat(goal.current_muscle_percentage).toFixed(1);
    }
    
    // 預填脂肪比例
    const fatPercentageInput = document.getElementById('fatPercentageInput');
    if (fatPercentageInput && goal.current_fat_percentage) {
        fatPercentageInput.value = parseFloat(goal.current_fat_percentage).toFixed(1);
    }
    
    // 預填體脂率（與脂肪比例相同）
    const bodyFatInput = document.getElementById('bodyFatInput');
    if (bodyFatInput && goal.current_fat_percentage) {
        bodyFatInput.value = parseFloat(goal.current_fat_percentage).toFixed(1);
    }
    
    // 預填骨骼比例
    const bonePercentageInput = document.getElementById('bonePercentageInput');
    if (bonePercentageInput && goal.current_bone_percentage) {
        bonePercentageInput.value = parseFloat(goal.current_bone_percentage).toFixed(1);
    }
    
    // 預填水分比例
    const waterPercentageInput = document.getElementById('waterPercentageInput');
    if (waterPercentageInput && goal.current_water_percentage) {
        waterPercentageInput.value = parseFloat(goal.current_water_percentage).toFixed(1);
    }
    
    // 計算並預填肌肉量（目前體重 x 肌肉比例%數）
    const muscleMassInput = document.getElementById('muscleMassInput');
    if (muscleMassInput && goal.current_weight && goal.current_muscle_percentage) {
        const muscleMass = (goal.current_weight * goal.current_muscle_percentage / 100).toFixed(1);
        muscleMassInput.value = muscleMass;
    }
    
    // 當體重或肌肉比例改變時，自動計算肌肉量
    if (weightInput && musclePercentageInput && muscleMassInput) {
        function calculateMuscleMass() {
            const weight = parseFloat(weightInput.value) || 0;
            const musclePercentage = parseFloat(musclePercentageInput.value) || 0;
            if (weight > 0 && musclePercentage > 0) {
                const muscleMass = (weight * musclePercentage / 100).toFixed(1);
                muscleMassInput.value = muscleMass;
            } else if (!weight || !musclePercentage) {
                muscleMassInput.value = '';
            }
        }
        
        // 移除舊的事件監聽器（如果有的話）
        weightInput.removeEventListener('input', calculateMuscleMass);
        musclePercentageInput.removeEventListener('input', calculateMuscleMass);
        
        // 添加新的事件監聽器
        weightInput.addEventListener('input', calculateMuscleMass);
        musclePercentageInput.addEventListener('input', calculateMuscleMass);
    }
}

// 添加體重記錄
document.getElementById('weightLogForm')?.addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData(this);
    
    fetch(window.GOALS_CONFIG.addWeightLogUrl, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': window.GOALS_CONFIG.csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('體重記錄已添加', 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('addWeightModal'));
            modal.hide();
            setTimeout(() => location.reload(), 500);
        } else {
            showToast(data.message || '添加失敗', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('添加失敗，請稍後再試', 'error');
    });
});

// 編輯營養記錄
function editNutritionLog(logId, foodName, quantity, mealType, notes) {
    // 創建編輯模態框
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'editNutritionLogModal';
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">編輯記錄 - ${foodName}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="editNutritionLogForm">
                        <input type="hidden" name="log_id" value="${logId}">
                        <div class="form-group">
                            <label>數量（份）*</label>
                            <input type="number" name="quantity" id="editQuantity" class="form-control" step="0.1" min="0.1" value="${quantity}" required>
                        </div>
                        <div class="form-group">
                            <label>餐點類型*</label>
                            <select name="meal_type" id="editMealType" class="form-control" required>
                                <option value="breakfast" ${mealType === 'breakfast' || mealType === '早餐' ? 'selected' : ''}>早餐</option>
                                <option value="lunch" ${mealType === 'lunch' || mealType === '午餐' ? 'selected' : ''}>午餐</option>
                                <option value="dinner" ${mealType === 'dinner' || mealType === '晚餐' ? 'selected' : ''}>晚餐</option>
                                <option value="snack" ${mealType === 'snack' || mealType === '點心' ? 'selected' : ''}>點心</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>備註</label>
                            <textarea name="notes" id="editNotes" class="form-control" rows="2">${notes || ''}</textarea>
                        </div>
                        <div class="form-actions" style="margin-top: 20px; display: flex; gap: 10px; justify-content: flex-end;">
                            <button type="submit" class="btn btn-primary">儲存</button>
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
    
    modal.addEventListener('hidden.bs.modal', function() {
        modal.remove();
    });
    
    // 處理表單提交
    document.getElementById('editNutritionLogForm')?.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        
        fetch(window.GOALS_CONFIG.updateNutritionLogUrlTemplate.replace('0', logId), {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': window.GOALS_CONFIG.csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('記錄已更新', 'success');
                bsModal.hide();
                // 重新載入當前選擇的日期
                const selectedDate = document.getElementById('nutritionDatePicker').value;
                if (selectedDate) {
                    loadNutritionByDate(selectedDate);
                } else {
                    // 更新顯示
                    updateNutritionDisplay(data);
                }
            } else {
                showToast(data.message || '更新失敗', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('更新失敗，請稍後再試', 'error');
        });
    });
}

// 刪除營養記錄
async function deleteNutritionLog(logId) {
    const confirmed = await confirmDialog('確定要刪除此飲食記錄嗎？', '確認刪除', 'danger');
    if (!confirmed) return;
    
    fetch(window.GOALS_CONFIG.deleteNutritionLogUrlTemplate.replace('0', logId), {
        method: 'POST',
        headers: {
            'X-CSRFToken': window.GOALS_CONFIG.csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('記錄已刪除', 'success');
            // 重新載入當前選擇的日期
            const selectedDate = document.getElementById('nutritionDatePicker').value;
            if (selectedDate) {
                loadNutritionByDate(selectedDate);
            } else {
                // 更新顯示
                updateNutritionDisplay(data);
            }
        } else {
            showToast(data.message || '刪除失敗', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('刪除失敗，請稍後再試', 'error');
    });
}

// 初始化日期選擇器為今天
document.addEventListener('DOMContentLoaded', function() {
    // 使用本地時間而不是UTC時間
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const today = `${year}-${month}-${day}`;
    
    const datePicker = document.getElementById('nutritionDatePicker');
    if (datePicker) {
        datePicker.value = today;
        datePicker.max = today; // 不允許選擇未來的日期
    }
});

// 體重圖表
let weightChart = null;
let currentWeightOffset = 0;

// 載入體重記錄並更新圖表
function loadWeightLogs(offset = 0) {
    fetch(window.GOALS_CONFIG.weightLogApiUrl + '?offset=' + offset)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentWeightOffset = data.offset;
                
                // 更新按鈕顯示
                const btnOlder = document.getElementById('btnOlderWeight');
                const btnNewer = document.getElementById('btnNewerWeight');
                const infoSpan = document.getElementById('weightLogInfo');
                
                if (btnOlder) btnOlder.style.display = data.has_older ? 'block' : 'none';
                if (btnNewer) btnNewer.style.display = data.has_newer ? 'block' : 'none';
                
                // 更新資訊顯示
                if (infoSpan && data.weight_logs.length > 0) {
                    const start = data.offset + 1;
                    const end = data.offset + data.weight_logs.length;
                    infoSpan.textContent = `顯示第 ${start}-${end} 筆記錄（共 ${data.total_count} 筆）`;
                }
                
                // 更新圖表
                updateWeightChart(data.weight_logs);
            } else {
                if (typeof showToast === 'function') {
                    showToast('載入失敗，請稍後再試', 'error');
                }
            }
        })
        .catch(error => {
            console.error('Error loading weight logs:', error);
            if (typeof showToast === 'function') {
                showToast('載入失敗，請稍後再試', 'error');
            }
        });
}

// 載入更舊的記錄（往左）
function loadOlderWeightLogs() {
    loadWeightLogs(currentWeightOffset + 10);
}

// 載入更新的記錄（往右）
function loadNewerWeightLogs() {
    const newOffset = Math.max(0, currentWeightOffset - 10);
    loadWeightLogs(newOffset);
}

// 更新體重圖表
function updateWeightChart(weightLogs) {
    const ctx = document.getElementById('weightChart');
    if (!ctx) return;
    
    if (weightLogs.length === 0) {
        // 如果沒有記錄，顯示空圖表
        if (weightChart) {
            weightChart.destroy();
            weightChart = null;
        }
        return;
    }
    
    // 準備數據（從舊到新，最新在右邊）
    const labels = weightLogs.map(log => log.recorded_at_short);
    const data = weightLogs.map(log => log.weight);
    const weightLogsData = weightLogs.map(log => ({
        date: log.recorded_at_date,
        datetime: log.recorded_at,
        weight: log.weight
    }));
    
    const chartData = {
        labels: labels,
        datasets: [{
            label: '體重 (kg)',
            data: data,
            borderColor: '#4CAF50',
            backgroundColor: 'rgba(76, 175, 80, 0.1)',
            tension: 0.4,
            pointRadius: 4,
            pointHoverRadius: 6
        }]
    };
    
    if (weightChart) {
        // 更新現有圖表
        weightChart.data = chartData;
        weightChart.data.weightLogsData = weightLogsData; // 存儲用於 tooltip
        weightChart.update();
    } else {
        // 創建新圖表
        weightChart = new Chart(ctx, {
            type: 'line',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                const index = context[0].dataIndex;
                                const logs = weightChart.data.weightLogsData || weightLogsData;
                                return logs[index] ? logs[index].datetime : '';
                            },
                            label: function(context) {
                                return '體重: ' + context.parsed.y.toFixed(1) + ' kg';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: '體重 (kg)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: '日期'
                        }
                    }
                }
            }
        });
        // 存儲數據用於 tooltip
        weightChart.data.weightLogsData = weightLogsData;
    }
}

// 初始化：載入最新10筆記錄
document.addEventListener('DOMContentLoaded', function() {
    loadWeightLogs(0);
});

