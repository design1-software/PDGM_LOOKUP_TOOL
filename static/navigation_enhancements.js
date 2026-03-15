/**
 * Enhanced navigation with breadcrumbs and shortcuts
 */
class NavigationEnhancements {
    constructor() {
        this.initBreadcrumbs();
        this.bindShortcuts();
    }

    initBreadcrumbs() {
        const container = document.querySelector('.breadcrumb');
        if (!container) return;

        const pathParts = window.location.pathname.split('/').filter(Boolean);
        let path = '';
        const crumbs = pathParts.map((part, index) => {
            path += '/' + part;
            const label = part.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            if (index === pathParts.length - 1) {
                return `<span class="crumb current">${label}</span>`;
            }
            return `<a href="${path}" class="crumb">${label}</a>`;
        });
        container.innerHTML = '<a href="/" class="crumb">Home</a>' +
            (crumbs.length ? '<span class="separator">›</span>' + crumbs.join('<span class="separator">›</span>') : '');
    }

    bindShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (!e.altKey) return;
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                window.history.back();
            } else if (e.key.toLowerCase() === 'h') {
                e.preventDefault();
                window.location.href = '/';
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', () => new NavigationEnhancements());
