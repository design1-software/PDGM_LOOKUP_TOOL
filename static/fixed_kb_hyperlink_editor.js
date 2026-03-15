/**
 * Knowledge Base Hyperlink Editor - FIXED VERSION
 * Provides controlled hyperlink editing for KB articles
 */

class KBHyperlinkEditor {
    constructor() {
        this.isInitialized = false;
        this.selectedText = '';
        this.selectedRange = null;
        this.linkCategories = [
            'CMS Guidelines',
            'Medicare Documentation',
            'Regulatory References',
            'Internal Procedures',
            'External Resources',
            'Training Materials'
        ];
        
        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initializeEditor());
        } else {
            this.initializeEditor();
        }
    }

    initializeEditor() {
        // Look for KB editor content textarea using robust selector logic
        const selectors = ['#content', 'textarea[name="content"]', '.kb-content-editor'];
        let contentTextarea = null;
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el) {
                contentTextarea = el;
                break;
            }
        }

        if (!contentTextarea) {
            // Try again after a short delay in case the element is dynamically created
            setTimeout(() => this.initializeEditor(), 1000);
            return;
        }


        const existingToolbar = document.getElementById('add-link-btn');

        if (existingToolbar) {
            // Toolbar already in markup - just wire up events
            this.setupHyperlinkTools(contentTextarea, existingToolbar.closest('.kb-hyperlink-toolbar'));
        } else {
            this.setupHyperlinkTools(contentTextarea);
        }

        this.isInitialized = true;
        console.log('KB Hyperlink Editor initialized');
    }

    setupHyperlinkTools(textarea, toolbar = null) {
        // If toolbar isn't provided, create and insert it
        if (!toolbar) {
            toolbar = this.createHyperlinkToolbar();

            // Prefer inserting into the Link Management section if present
            const target = document.getElementById('hyperlink-toolbar-target');
            if (target) {
                target.appendChild(toolbar);
            } else {
                // Fallback to placing before the textarea
                textarea.parentNode.insertBefore(toolbar, textarea);
            }

        }
        
        // Add selection event listeners
        textarea.addEventListener('mouseup', () => this.handleTextSelection(textarea));
        textarea.addEventListener('keyup', () => this.handleTextSelection(textarea));
        textarea.addEventListener('select', () => this.handleTextSelection(textarea));
        document.addEventListener('selectionchange', () => {
            if (document.activeElement === textarea) {
                this.handleTextSelection(textarea);
            }
        });

        
        // Add toolbar button event listeners
        this.setupToolbarEvents(textarea);
    }

    createHyperlinkToolbar() {
        const toolbar = document.createElement('div');
        toolbar.className = 'kb-hyperlink-toolbar';
        toolbar.innerHTML = `
            <div class="toolbar-section">
                <label class="toolbar-label">Hyperlink Tools:</label>
                <button type="button" class="toolbar-btn" id="add-link-btn" disabled>
                    🔗 Add Link
                </button>
                <button type="button" class="toolbar-btn" id="remove-link-btn" disabled>
                    🚫 Remove Link
                </button>
                <button type="button" class="toolbar-btn" id="preview-links-btn">
                    👁️ Preview Links
                </button>
            </div>
            <div class="selection-info" id="selection-info" style="display: none;">
                <span class="selected-text-preview"></span>
            </div>
        `;
        
        return toolbar;
    }

    setupToolbarEvents(textarea) {
        const addLinkBtn = document.getElementById('add-link-btn');
        const removeLinkBtn = document.getElementById('remove-link-btn');
        const previewLinksBtn = document.getElementById('preview-links-btn');

        // Capture selection before focus moves away
        addLinkBtn.addEventListener('mousedown', () => this.handleTextSelection(textarea));
        removeLinkBtn.addEventListener('mousedown', () => this.handleTextSelection(textarea));

        addLinkBtn.addEventListener('click', () => this.showLinkDialog(textarea));
        removeLinkBtn.addEventListener('click', () => this.removeLink(textarea));
        previewLinksBtn.addEventListener('click', () => this.previewLinks(textarea));
    }

    handleTextSelection(textarea) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        
        if (start !== end) {
            this.selectedText = textarea.value.substring(start, end);
            this.selectedRange = { start, end };
            
            // Update UI
            this.updateSelectionUI();
            document.getElementById('add-link-btn').disabled = false;
            
            // Check if selection is already a link
            const isLink = this.isSelectionALink(textarea.value, start, end);
            document.getElementById('remove-link-btn').disabled = !isLink;
        } else {
            this.selectedText = '';
            this.selectedRange = null;
            this.updateSelectionUI();
            document.getElementById('add-link-btn').disabled = true;
            document.getElementById('remove-link-btn').disabled = true;
        }
    }

    updateSelectionUI() {
        const selectionInfo = document.getElementById('selection-info');
        const preview = selectionInfo.querySelector('.selected-text-preview');
        
        if (this.selectedText) {
            preview.textContent = `Selected: "${this.selectedText.substring(0, 50)}${this.selectedText.length > 50 ? '...' : ''}"`;
            selectionInfo.style.display = 'block';
        } else {
            selectionInfo.style.display = 'none';
        }
    }

    isSelectionALink(content, start, end) {
        // Check if the selected text is already wrapped in markdown link syntax
        const beforeSelection = content.substring(Math.max(0, start - 100), start);
        const afterSelection = content.substring(end, Math.min(content.length, end + 100));
        
        // Look for markdown link pattern: [text](url)
        const linkPattern = /\[([^\]]*)\]\(([^)]*)\)/;
        const surroundingText = beforeSelection + content.substring(start, end) + afterSelection;
        
        return linkPattern.test(surroundingText);
    }

    showLinkDialog(textarea) {
        if (!this.selectedText) {
            alert('Please select text first');
            return;
        }

        // Create modal dialog
        const modal = this.createLinkModal();
        document.body.appendChild(modal);
        
        // Focus on URL input
        const urlInput = modal.querySelector('#link-url');
        urlInput.focus();
        
        // Setup modal events
        this.setupModalEvents(modal, textarea);
    }

    createLinkModal() {
        const modal = document.createElement('div');
        modal.className = 'kb-link-modal';
        modal.innerHTML = `
            <div class="modal-overlay"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Add Hyperlink</h3>
                    <button type="button" class="modal-close">×</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label for="link-text">Link Text:</label>
                        <input type="text" id="link-text" value="${this.selectedText}" readonly>
                    </div>
                    <div class="form-group">
                        <label for="link-url">URL:</label>
                        <input type="url" id="link-url" placeholder="https://example.com" required>
                    </div>
                    <div class="form-group">
                        <label for="link-category">Category:</label>
                        <select id="link-category">
                            ${this.linkCategories.map(cat => `<option value="${cat}">${cat}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="link-description">Description (optional):</label>
                        <input type="text" id="link-description" placeholder="Brief description of the link">
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="link-external" checked>
                            Open in new tab
                        </label>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-primary" id="save-link-btn">Add Link</button>
                    <button type="button" class="btn btn-secondary" id="cancel-link-btn">Cancel</button>
                </div>
            </div>
        `;
        
        return modal;
    }

    setupModalEvents(modal, textarea) {
        const closeBtn = modal.querySelector('.modal-close');
        const cancelBtn = modal.querySelector('#cancel-link-btn');
        const saveBtn = modal.querySelector('#save-link-btn');
        const overlay = modal.querySelector('.modal-overlay');
        
        // Close events
        [closeBtn, cancelBtn, overlay].forEach(element => {
            element.addEventListener('click', () => {
                modal.remove();
            });
        });
        
        // Save event
        saveBtn.addEventListener('click', () => {
            this.saveLinkToTextarea(modal, textarea);
        });
        
        // Enter key to save
        modal.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.target.id === 'link-url') {
                e.preventDefault();
                this.saveLinkToTextarea(modal, textarea);
            }
            if (e.key === 'Escape') {
                modal.remove();
            }
        });
    }

    saveLinkToTextarea(modal, textarea) {
        const url = modal.querySelector('#link-url').value.trim();
        const category = modal.querySelector('#link-category').value;
        const description = modal.querySelector('#link-description').value.trim();
        const external = modal.querySelector('#link-external').checked;
        
        if (!url) {
            alert('Please enter a URL');
            return;
        }
        
        // Validate URL
        if (!this.isValidUrl(url)) {
            alert('Please enter a valid URL');
            return;
        }
        
        // Create markdown link
        let linkMarkdown = `[${this.selectedText}](${url})`;
        
        // Add title attribute if description provided
        if (description) {
            linkMarkdown = `[${this.selectedText}](${url} "${description}")`;
        }
        
        // Replace selected text with link
        const content = textarea.value;
        const newContent = content.substring(0, this.selectedRange.start) + 
                          linkMarkdown + 
                          content.substring(this.selectedRange.end);
        
        textarea.value = newContent;
        
        // Update cursor position
        const newCursorPos = this.selectedRange.start + linkMarkdown.length;
        textarea.setSelectionRange(newCursorPos, newCursorPos);
        
        // Focus back on textarea
        textarea.focus();
        
        // Close modal
        modal.remove();
        
        // Reset selection
        this.selectedText = '';
        this.selectedRange = null;
        this.updateSelectionUI();
        
        // Show success message
        this.showMessage('Link added successfully!', 'success');
    }

    removeLink(textarea) {
        if (!this.selectedRange) {
            alert('Please select a link to remove');
            return;
        }
        
        const content = textarea.value;
        const start = this.selectedRange.start;
        const end = this.selectedRange.end;
        
        // Find the full link markdown around the selection
        const linkPattern = /\[([^\]]*)\]\(([^)]*)\)/g;
        let match;
        let linkStart = -1;
        let linkEnd = -1;
        let linkText = '';
        
        while ((match = linkPattern.exec(content)) !== null) {
            if (match.index <= start && match.index + match[0].length >= end) {
                linkStart = match.index;
                linkEnd = match.index + match[0].length;
                linkText = match[1];
                break;
            }
        }
        
        if (linkStart !== -1) {
            // Replace link with just the text
            const newContent = content.substring(0, linkStart) + 
                              linkText + 
                              content.substring(linkEnd);
            
            textarea.value = newContent;
            
            // Update cursor position
            textarea.setSelectionRange(linkStart, linkStart + linkText.length);
            textarea.focus();
            
            this.showMessage('Link removed successfully!', 'success');
        } else {
            alert('No link found in selection');
        }
    }

    previewLinks(textarea) {
        const content = textarea.value;
        const linkPattern = /\[([^\]]*)\]\(([^)]*)\)/g;
        const links = [];
        let match;
        
        while ((match = linkPattern.exec(content)) !== null) {
            links.push({
                text: match[1],
                url: match[2],
                position: match.index
            });
        }
        
        if (links.length === 0) {
            alert('No links found in the content');
            return;
        }
        
        // Create preview modal
        const modal = this.createPreviewModal(links);
        document.body.appendChild(modal);
        
        // Setup close events
        const closeBtn = modal.querySelector('.modal-close');
        const overlay = modal.querySelector('.modal-overlay');
        
        [closeBtn, overlay].forEach(element => {
            element.addEventListener('click', () => {
                modal.remove();
            });
        });
    }

    createPreviewModal(links) {
        const modal = document.createElement('div');
        modal.className = 'kb-link-modal';
        modal.innerHTML = `
            <div class="modal-overlay"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Link Preview (${links.length} links found)</h3>
                    <button type="button" class="modal-close">×</button>
                </div>
                <div class="modal-body">
                    <div class="links-list">
                        ${links.map((link, index) => `
                            <div class="link-item">
                                <div class="link-text">${link.text}</div>
                                <div class="link-url">
                                    <a href="${link.url}" target="_blank" rel="noopener">${link.url}</a>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
        
        return modal;
    }

    isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }

    showMessage(message, type = 'info') {
        // Create temporary message element
        const messageEl = document.createElement('div');
        messageEl.className = `kb-message kb-message-${type}`;
        messageEl.textContent = message;
        
        // Add to page
        document.body.appendChild(messageEl);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.remove();
            }
        }, 3000);
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        console.log('Initializing KB Hyperlink Editor');
        window.kbHyperlinkEditor = new KBHyperlinkEditor();
    });
} else {
    console.log('Initializing KB Hyperlink Editor (immediate)');
    window.kbHyperlinkEditor = new KBHyperlinkEditor();
}


