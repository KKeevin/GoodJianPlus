/**
 * 通用互動效果和動畫
 * 用於多個頁面的通用功能
 */

(function() {
    'use strict';

    // 產品卡片 hover 效果
    function initProductCardHover() {
        const productCards = document.querySelectorAll('.product-card');
        productCards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.boxShadow = '0 8px 25px rgba(0,0,0,0.15)';
            });
            card.addEventListener('mouseleave', function() {
                this.style.boxShadow = '0 4px 15px rgba(0,0,0,0.1)';
            });
        });
    }

    // Newsletter 表單提交
    function initNewsletterForm() {
        const newsletterForm = document.querySelector('.newsletter-form');
        if (newsletterForm) {
            newsletterForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const email = this.querySelector('.newsletter-input').value;
                if (email) {
                    if (typeof showToast === 'function') {
                        showToast('感謝您的訂閱！', 'success');
                    } else {
                        alert('感謝您的訂閱！');
                    }
                    this.querySelector('.newsletter-input').value = '';
                }
            });
        }
    }

    // 滾動動畫
    function initScrollAnimations() {
        if (!('IntersectionObserver' in window)) return;

        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, observerOptions);

        // 觀察需要動畫的元素
        const animatedElements = document.querySelectorAll('.feature-item, .category-card');
        animatedElements.forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(30px)';
            el.style.transition = 'all 0.6s ease';
            observer.observe(el);
        });
    }

    // 初始化所有通用功能
    function init() {
        initProductCardHover();
        initNewsletterForm();
        initScrollAnimations();
    }

    // 當 DOM 載入完成後初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

