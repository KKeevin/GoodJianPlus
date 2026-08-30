/**
 * 手機版選單滾動控制
 * 當手機版選單打開時，禁用背景頁面滾動
 */

document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.getElementById('menu-toggle');
    
    if (!menuToggle) return;
    
    /**
     * 關閉選單並恢復滾動
     */
    function closeMenuAndRestoreScroll() {
        const scrollY = document.body.style.top;
        menuToggle.checked = false;
        document.body.classList.remove('menu-open');
        document.body.style.top = '';
        // 恢復滾動位置
        if (scrollY) {
            window.scrollTo(0, parseInt(scrollY || '0') * -1);
        }
    }
    
    // 監聽選單 checkbox 的變化
    menuToggle.addEventListener('change', function() {
        if (this.checked) {
            // 選單打開時，禁用背景滾動
            document.body.classList.add('menu-open');
            // 記錄當前滾動位置
            const scrollY = window.scrollY;
            document.body.style.top = `-${scrollY}px`;
        } else {
            // 選單關閉時，恢復背景滾動
            const scrollY = document.body.style.top;
            document.body.classList.remove('menu-open');
            document.body.style.top = '';
            // 恢復滾動位置
            if (scrollY) {
                window.scrollTo(0, parseInt(scrollY || '0') * -1);
            }
        }
    });
    
    // 當點擊選單內的連結時，自動關閉選單並恢復滾動
    const navLinks = document.querySelectorAll('.nav-and-icons a');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (menuToggle.checked) {
                closeMenuAndRestoreScroll();
            }
        });
    });
    
    // 當點擊選單外部區域時，關閉選單（可選功能）
    // 注意：這需要確保選單有遮罩層，否則可能會影響其他功能
    document.addEventListener('click', function(e) {
        // 如果選單是打開的，且點擊的不是選單本身或選單按鈕
        if (menuToggle.checked && 
            !e.target.closest('.nav-and-icons') && 
            !e.target.closest('.menu-icon') &&
            !e.target.closest('#menu-toggle')) {
            // 可以選擇是否啟用此功能
            // closeMenuAndRestoreScroll();
        }
    });
});

