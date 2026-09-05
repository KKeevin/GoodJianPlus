(function () {
    'use strict';

    var storageKey = 'jazzmin-theme-mode';
    var legacyStorageKey = 'goodjian-admin-theme-mode';
    var modes = ['light', 'dark'];

    function getMode() {
        var savedMode = window.localStorage.getItem(storageKey);
        if (!savedMode) {
            savedMode = window.localStorage.getItem(legacyStorageKey);
        }
        return modes.indexOf(savedMode) !== -1 ? savedMode : 'light';
    }

    function updateButton(button, mode) {
        var isDark = mode === 'dark';
        button.innerHTML = isDark
            ? '<i class="fas fa-sun" aria-hidden="true"></i>'
            : '<i class="fas fa-moon" aria-hidden="true"></i>';
        button.setAttribute('aria-label', isDark ? '切換明亮模式' : '切換深色模式');
        button.setAttribute('title', isDark ? '切換明亮模式' : '切換深色模式');
    }

    function applyMode(button, mode) {
        document.documentElement.setAttribute('data-bs-theme', mode);
        window.localStorage.setItem(storageKey, mode);
        window.localStorage.setItem(legacyStorageKey, mode);
        updateButton(button, mode);
        document.documentElement.classList.add('goodjian-theme-ready');
    }

    function init() {
        var navigation = document.querySelector('.navbar-nav.ms-auto');
        if (!navigation || document.getElementById('goodjian-theme-toggle')) {
            document.documentElement.classList.add('goodjian-theme-ready');
            return;
        }

        var item = document.createElement('li');
        item.className = 'nav-item';
        var button = document.createElement('button');
        button.type = 'button';
        button.id = 'goodjian-theme-toggle';
        button.className = 'nav-link btn';
        button.addEventListener('click', function () {
            applyMode(button, document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark');
        });
        item.appendChild(button);
        var accountMenu = document.getElementById('jazzy-usermenu');
        var accountItem = accountMenu ? accountMenu.closest('.nav-item') : null;
        if (accountItem) {
            navigation.insertBefore(item, accountItem);
        } else {
            navigation.appendChild(item);
        }

        var frontendLink = Array.prototype.find.call(
            document.querySelectorAll('a.nav-link'),
            function (link) {
                return link.textContent.trim() === '瀏覽前台';
            }
        );
        var frontendItem = frontendLink ? frontendLink.closest('.nav-item') : null;
        if (frontendItem) {
            frontendLink.classList.add('goodjian-frontend-link');
            navigation.insertBefore(frontendItem, item);
        }

        var userMenu = document.getElementById('jazzy-usermenu');
        var recentLink = userMenu ? Array.prototype.find.call(
            userMenu.querySelectorAll('a.dropdown-item'),
            function (link) {
                return link.textContent.trim() === '最近的動作';
            }
        ) : null;
        if (userMenu && recentLink) {
            var recentDivider = recentLink.previousElementSibling;
            if (recentDivider && recentDivider.classList.contains('dropdown-divider')) {
                recentDivider.remove();
            }
            var firstDivider = userMenu.querySelector('.dropdown-divider');
            userMenu.insertBefore(recentLink, firstDivider || userMenu.firstElementChild);
        }
        applyMode(button, getMode());
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
