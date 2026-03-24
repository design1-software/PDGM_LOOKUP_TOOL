/**
 * Universal Navigation System for PDGM Lookup Tool
 * Adds consistent Back/Home navigation to all pages
 */

class PDGMNavigation {
    constructor() {
        this.navigationHistory = [];
        this.currentPage = window.location.pathname;
        this.init();
    }

    init() {
        this.recordPageVisit();
        this.createNavigationBar();
        this.setupNavigationHandlers();
    }

    recordPageVisit() {
        const currentUrl = window.location.href;
        const currentTitle = document.title;
        
        // Don't record duplicate consecutive visits
        if (this.navigationHistory.length === 0 || 
            this.navigationHistory[this.navigationHistory.length - 1].url !== currentUrl) {
            
            this.navigationHistory.push({
                url: currentUrl,
                title: currentTitle,
                timestamp: Date.now()
            });
            
            // Keep only last 10 pages
            if (this.navigationHistory.length > 10) {
                this.navigationHistory.shift();
            }
            
            // Store in sessionStorage for persistence
            sessionStorage.setItem('pdgm_nav_history', JSON.stringify(this.navigationHistory));
        }
    }

    createNavigationBar() {
        // Check if navigation already exists
        if (document.getElementById('pdgm-universal-nav')) {
            return;
        }

        const navBar = document.createElement('div');
        navBar.id = 'pdgm-universal-nav';
        navBar.className = 'pdgm-universal-nav';
        
        navBar.innerHTML = `
            <div class="nav-container">
                <div class="nav-left">
                    <button type="button" class="nav-button back-button" onclick="pdgmNav.goBack()" title="Go Back">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="m15 18-6-6 6-6"/>
                        </svg>
                        Back
                    </button>
                    <button type="button" class="nav-button home-button" onclick="pdgmNav.goHome()" title="Go to Home">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                            <polyline points="9,22 9,12 15,12 15,22"/>
                        </svg>
                        Home
                    </button>
                </div>
                
                <div class="nav-center">
                    <div class="breadcrumb-container">
                        <span class="breadcrumb-item">
                            <a href="/" class="breadcrumb-link">PDGM Tool</a>
                        </span>
                        <span class="breadcrumb-separator">›</span>
                        <span class="breadcrumb-item current-page">
                            ${this.getCurrentPageName()}
                        </span>
                    </div>
                </div>
                
                <div class="nav-right">
                    <button type="button" class="nav-button menu-button" onclick="pdgmNav.toggleMenu()" title="Menu">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="3" y1="6" x2="21" y2="6"/>
                            <line x1="3" y1="12" x2="21" y2="12"/>
                            <line x1="3" y1="18" x2="21" y2="18"/>
                        </svg>
                    </button>
                </div>
            </div>
            
            <div class="nav-menu" id="pdgm-nav-menu" style="display: none;">
                <div class="menu-section">
                    <h4>Quick Access</h4>
                    <a href="/" class="menu-item">
                        <span class="menu-icon">🏠</span>
                        Home / PDGM Lookup
                    </a>
                </div>

                <div class="menu-section">
                    <h4>Recent Pages</h4>
                    <div id="recent-pages-list">
                        ${this.getRecentPagesHTML()}
                    </div>
                </div>
            </div>
        `;

        // Insert navigation at the top of the page
        const body = document.body;
        const firstChild = body.firstChild;
        body.insertBefore(navBar, firstChild);

        // Adjust page content to account for navigation
        this.adjustPageLayout();
    }

    getCurrentPageName() {
        const path = window.location.pathname;
        const pageNames = {
            '/': 'PDGM Lookup',
            '/batch': 'Batch Processing',
            '/batch/upload': 'Batch Upload',
            '/batch/results': 'Batch Results',
            '/support': 'Support Center',
            '/support/knowledge-base': 'Knowledge Base',
            '/support/create-ticket': 'Create Ticket',
            '/auth/login': 'Login',
            '/auth/register': 'Register',
            '/auth/profile': 'Profile',
            '/auth/upgrade': 'Upgrade',
            '/admin/dashboard': 'Admin Dashboard',
            '/admin/kb/create': 'Create Article',
            '/admin/analytics': 'Analytics'
        };

        return pageNames[path] || this.extractPageNameFromTitle() || 'PDGM Tool';
    }

    extractPageNameFromTitle() {
        const title = document.title;
        if (title.includes(' - ')) {
            return title.split(' - ')[0];
        }
        return title.replace('PDGM Lookup Tool', '').trim();
    }

    getRecentPagesHTML() {
        const history = this.getNavigationHistory();
        const recent = history.slice(-5).reverse(); // Last 5 pages, most recent first
        
        if (recent.length <= 1) {
            return '<div class="menu-item disabled">No recent pages</div>';
        }

        return recent.slice(1).map(page => { // Skip current page
            const pageName = this.extractPageNameFromUrl(page.url);
            return `
                <a href="${page.url}" class="menu-item recent-page">
                    <span class="menu-icon">📄</span>
                    ${pageName}
                </a>
            `;
        }).join('');
    }

    extractPageNameFromUrl(url) {
        const path = new URL(url).pathname;
        const pageNames = {
            '/': 'PDGM Lookup',
            '/batch': 'Batch Processing',
            '/support': 'Support Center',
            '/auth/profile': 'Profile'
        };
        return pageNames[path] || path.split('/').pop() || 'Page';
    }

    setupNavigationHandlers() {
        // Handle browser back/forward buttons
        window.addEventListener('popstate', (event) => {
            this.recordPageVisit();
            this.updateBreadcrumb();
        });

        // Close menu when clicking outside
        document.addEventListener('click', (event) => {
            const menu = document.getElementById('pdgm-nav-menu');
            const menuButton = event.target.closest('.menu-button');
            
            if (!menuButton && !event.target.closest('.nav-menu')) {
                menu.style.display = 'none';
            }
        });

        // Handle keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            if (event.altKey) {
                switch (event.key) {
                    case 'ArrowLeft':
                        event.preventDefault();
                        this.goBack();
                        break;
                    case 'h':
                        event.preventDefault();
                        this.goHome();
                        break;
                }
            }
        });
    }

    adjustPageLayout() {
        // Add top margin to prevent content from being hidden behind navigation
        const existingStyle = document.getElementById('pdgm-nav-style');
        if (!existingStyle) {
            const style = document.createElement('style');
            style.id = 'pdgm-nav-style';
            style.textContent = `
                body {
                    padding-top: 60px !important;
                }
                
                @media (max-width: 768px) {
                    body {
                        padding-top: 70px !important;
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }

    goBack() {
        const history = this.getNavigationHistory();
        
        if (history.length > 1) {
            // Go to previous page in our history
            const previousPage = history[history.length - 2];
            window.location.href = previousPage.url;
        } else {
            // Fallback to browser history
            if (window.history.length > 1) {
                window.history.back();
            } else {
                this.goHome();
            }
        }
    }

    goHome() {
        window.location.href = '/';
    }

    toggleMenu() {
        const menu = document.getElementById('pdgm-nav-menu');
        const isVisible = menu.style.display !== 'none';
        menu.style.display = isVisible ? 'none' : 'block';
        
        if (!isVisible) {
            // Update recent pages when menu is opened
            const recentPagesList = document.getElementById('recent-pages-list');
            recentPagesList.innerHTML = this.getRecentPagesHTML();
        }
    }

    updateBreadcrumb() {
        const breadcrumbCurrent = document.querySelector('.current-page');
        if (breadcrumbCurrent) {
            breadcrumbCurrent.textContent = this.getCurrentPageName();
        }
    }

    getNavigationHistory() {
        try {
            const stored = sessionStorage.getItem('pdgm_nav_history');
            return stored ? JSON.parse(stored) : this.navigationHistory;
        } catch (e) {
            return this.navigationHistory;
        }
    }

    // Public method to manually add navigation entry
    addNavigationEntry(url, title) {
        this.navigationHistory.push({
            url: url,
            title: title,
            timestamp: Date.now()
        });
        
        sessionStorage.setItem('pdgm_nav_history', JSON.stringify(this.navigationHistory));
    }

    // Public method to clear navigation history
    clearHistory() {
        this.navigationHistory = [];
        sessionStorage.removeItem('pdgm_nav_history');
    }
}

// Initialize navigation when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.pdgmNav = new PDGMNavigation();
});

// Fallback for pages that load content dynamically
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        if (!window.pdgmNav) {
            window.pdgmNav = new PDGMNavigation();
        }
    });
} else {
    if (!window.pdgmNav) {
        window.pdgmNav = new PDGMNavigation();
    }
}

