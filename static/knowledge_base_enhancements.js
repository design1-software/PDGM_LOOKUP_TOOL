/**
 * Knowledge Base Editor Enhancements for PDGM Lookup Tool
 * Adds rich text editing, external link management, and improved UX
 */

class KnowledgeBaseEditor {
    constructor() {
        this.externalLinks = [];
        this.linkCounter = 0;
        this.init();
    }

    init() {
        // Check if we're on the KB creation page
        const kbForm = document.querySelector('form[action*="kb"]');
        const contentTextarea = document.querySelector('#content, textarea[name="content"]');
        
        if (kbForm && contentTextarea) {
            this.enhanceEditor(kbForm, contentTextarea);
        }
    }

    enhanceEditor(form, textarea) {
        // Create enhanced editor container
        const editorContainer = this.createEditorContainer(textarea);
        
        // Replace textarea with enhanced editor
        textarea.parentNode.insertBefore(editorContainer, textarea);
        textarea.style.display = 'none';
        
        // Setup event handlers
        this.setupEventHandlers(form, textarea);
        
        // Initialize external links section
        this.initializeExternalLinksSection(form);
    }

    createEditorContainer(textarea) {
        const container = document.createElement('div');
        container.className = 'kb-editor-container';
        
        container.innerHTML = `
            <div class="editor-toolbar">
                <div class="toolbar-group">
                    <button type="button" class="toolbar-btn" data-action="bold" title="Bold">
                        <strong>B</strong>
                    </button>
                    <button type="button" class="toolbar-btn" data-action="italic" title="Italic">
                        <em>I</em>
                    </button>
                    <button type="button" class="toolbar-btn" data-action="underline" title="Underline">
                        <u>U</u>
                    </button>
                </div>
                
                <div class="toolbar-group">
                    <button type="button" class="toolbar-btn" data-action="heading" title="Heading">
                        H1
                    </button>
                    <button type="button" class="toolbar-btn" data-action="list" title="Bullet List">
                        •
                    </button>
                    <button type="button" class="toolbar-btn" data-action="link" title="Insert Link">
                        🔗
                    </button>
                </div>
                
                <div class="toolbar-group">
                    <button type="button" class="toolbar-btn" data-action="code" title="Code Block">
                        &lt;/&gt;
                    </button>
                    <button type="button" class="toolbar-btn" data-action="quote" title="Quote">
                        "
                    </button>
                </div>
                
                <div class="toolbar-group">
                    <button type="button" class="toolbar-btn" data-action="preview" title="Preview">
                        👁
                    </button>
                    <button type="button" class="toolbar-btn" data-action="help" title="Help">
                        ?
                    </button>
                </div>
            </div>
            
            <div class="editor-content">
                <div class="editor-tabs">
                    <button type="button" class="tab-btn active" data-tab="edit">Edit</button>
                    <button type="button" class="tab-btn" data-tab="preview">Preview</button>
                </div>
                
                <div class="tab-content">
                    <div class="tab-pane active" id="edit-pane">
                        <textarea class="enhanced-textarea" placeholder="Write your article content here. Use markdown syntax for formatting.

Examples:
# Heading 1
## Heading 2
**Bold text**
*Italic text*
[Link text](URL)
- Bullet point
> Quote

You can also use the toolbar buttons above for formatting.">${textarea.value}</textarea>
                        <div class="editor-status">
                            <span class="word-count">0 words</span>
                            <span class="char-count">0 characters</span>
                        </div>
                    </div>
                    
                    <div class="tab-pane" id="preview-pane">
                        <div class="preview-content">
                            <p class="preview-placeholder">Switch to preview mode to see how your article will look.</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="editor-help" style="display: none;">
                <h4>Markdown Quick Reference</h4>
                <div class="help-grid">
                    <div class="help-item">
                        <strong># Heading 1</strong>
                        <span>Large heading</span>
                    </div>
                    <div class="help-item">
                        <strong>## Heading 2</strong>
                        <span>Medium heading</span>
                    </div>
                    <div class="help-item">
                        <strong>**Bold**</strong>
                        <span>Bold text</span>
                    </div>
                    <div class="help-item">
                        <strong>*Italic*</strong>
                        <span>Italic text</span>
                    </div>
                    <div class="help-item">
                        <strong>[Link](URL)</strong>
                        <span>Create link</span>
                    </div>
                    <div class="help-item">
                        <strong>- Item</strong>
                        <span>Bullet list</span>
                    </div>
                    <div class="help-item">
                        <strong>\`code\`</strong>
                        <span>Inline code</span>
                    </div>
                    <div class="help-item">
                        <strong>> Quote</strong>
                        <span>Blockquote</span>
                    </div>
                </div>
            </div>
        `;
        
        return container;
    }

    setupEventHandlers(form, originalTextarea) {
        const container = document.querySelector('.kb-editor-container');
        const enhancedTextarea = container.querySelector('.enhanced-textarea');
        
        // Sync content with original textarea
        enhancedTextarea.addEventListener('input', () => {
            originalTextarea.value = enhancedTextarea.value;
            this.updateWordCount(enhancedTextarea);
            this.updatePreview(enhancedTextarea.value);
        });
        
        // Toolbar button handlers
        container.addEventListener('click', (e) => {
            if (e.target.classList.contains('toolbar-btn')) {
                e.preventDefault();
                const action = e.target.dataset.action;
                this.handleToolbarAction(action, enhancedTextarea);
            }
            
            if (e.target.classList.contains('tab-btn')) {
                e.preventDefault();
                this.switchTab(e.target.dataset.tab);
            }
        });
        
        // Initialize word count
        this.updateWordCount(enhancedTextarea);
        
        // Auto-save functionality
        let autoSaveTimeout;
        enhancedTextarea.addEventListener('input', () => {
            clearTimeout(autoSaveTimeout);
            autoSaveTimeout = setTimeout(() => {
                this.autoSave(form);
            }, 2000);
        });
    }

    handleToolbarAction(action, textarea) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const selectedText = textarea.value.substring(start, end);
        let replacement = '';
        
        switch (action) {
            case 'bold':
                replacement = `**${selectedText || 'bold text'}**`;
                break;
            case 'italic':
                replacement = `*${selectedText || 'italic text'}*`;
                break;
            case 'underline':
                replacement = `<u>${selectedText || 'underlined text'}</u>`;
                break;
            case 'heading':
                replacement = `## ${selectedText || 'Heading'}`;
                break;
            case 'list':
                replacement = `- ${selectedText || 'List item'}`;
                break;
            case 'link':
                this.insertLink(textarea, start, end, selectedText);
                return;
            case 'code':
                if (selectedText.includes('\n')) {
                    replacement = `\`\`\`\n${selectedText || 'code block'}\n\`\`\``;
                } else {
                    replacement = `\`${selectedText || 'code'}\``;
                }
                break;
            case 'quote':
                replacement = `> ${selectedText || 'Quote text'}`;
                break;
            case 'preview':
                this.switchTab('preview');
                return;
            case 'help':
                this.toggleHelp();
                return;
        }
        
        this.insertText(textarea, start, end, replacement);
    }

    insertLink(textarea, start, end, selectedText) {
        const linkText = selectedText || 'Link text';
        const url = prompt('Enter the URL:', 'https://');
        
        if (url) {
            const replacement = `[${linkText}](${url})`;
            this.insertText(textarea, start, end, replacement);
        }
    }

    insertText(textarea, start, end, replacement) {
        const before = textarea.value.substring(0, start);
        const after = textarea.value.substring(end);
        
        textarea.value = before + replacement + after;
        textarea.focus();
        
        // Set cursor position
        const newPosition = start + replacement.length;
        textarea.setSelectionRange(newPosition, newPosition);
        
        // Trigger input event to update preview and word count
        textarea.dispatchEvent(new Event('input'));
    }

    switchTab(tabName) {
        const tabs = document.querySelectorAll('.tab-btn');
        const panes = document.querySelectorAll('.tab-pane');
        
        tabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });
        
        panes.forEach(pane => {
            pane.classList.toggle('active', pane.id === `${tabName}-pane`);
        });
        
        if (tabName === 'preview') {
            const textarea = document.querySelector('.enhanced-textarea');
            this.updatePreview(textarea.value);
        }
    }

    updatePreview(content) {
        const previewContent = document.querySelector('.preview-content');
        if (!previewContent) return;
        
        if (!content.trim()) {
            previewContent.innerHTML = '<p class="preview-placeholder">Switch to preview mode to see how your article will look.</p>';
            return;
        }
        
        // Simple markdown to HTML conversion
        let html = content
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/gim, '<em>$1</em>')
            .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" target="_blank">$1</a>')
            .replace(/`([^`]+)`/gim, '<code>$1</code>')
            .replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>')
            .replace(/^- (.*$)/gim, '<li>$1</li>')
            .replace(/\n/gim, '<br>');
        
        // Wrap consecutive <li> elements in <ul>
        html = html.replace(/(<li>.*?<\/li>)(<br>)*(?=<li>|$)/gim, (match, li) => {
            return li.replace(/<br>/g, '');
        });
        html = html.replace(/(<li>.*?<\/li>)+/gim, '<ul>$&</ul>');
        
        previewContent.innerHTML = html;
    }

    updateWordCount(textarea) {
        const content = textarea.value;
        const words = content.trim() ? content.trim().split(/\s+/).length : 0;
        const chars = content.length;
        
        const wordCount = document.querySelector('.word-count');
        const charCount = document.querySelector('.char-count');
        
        if (wordCount) wordCount.textContent = `${words} words`;
        if (charCount) charCount.textContent = `${chars} characters`;
    }

    toggleHelp() {
        const helpSection = document.querySelector('.editor-help');
        const isVisible = helpSection.style.display !== 'none';
        helpSection.style.display = isVisible ? 'none' : 'block';
    }

    initializeExternalLinksSection(form) {
        // Find or create external links section
        let linksSection = document.querySelector('.external-links-section');
        
        if (!linksSection) {
            linksSection = document.createElement('div');
            linksSection.className = 'external-links-section';
            linksSection.innerHTML = `
                <h3>External Links</h3>
                <p class="section-description">Add external links that will be displayed at the end of your article.</p>
                <div class="links-container">
                    <!-- Links will be added here -->
                </div>
                <button type="button" class="add-link-btn">+ Add External Link</button>
            `;
            
            // Insert before form buttons
            const formButtons = form.querySelector('.form-actions, button[type="submit"]');
            if (formButtons) {
                form.insertBefore(linksSection, formButtons.parentNode || formButtons);
            } else {
                form.appendChild(linksSection);
            }
        }
        
        // Setup event handlers
        linksSection.addEventListener('click', (e) => {
            if (e.target.classList.contains('add-link-btn')) {
                e.preventDefault();
                this.addExternalLink();
            }
            
            if (e.target.classList.contains('remove-link-btn')) {
                e.preventDefault();
                this.removeExternalLink(e.target.closest('.link-item'));
            }
        });
        
        // Load existing links if any
        this.loadExistingLinks();
    }

    addExternalLink(title = '', url = '', description = '') {
        const linksContainer = document.querySelector('.links-container');
        const linkId = `link_${this.linkCounter++}`;
        
        const linkItem = document.createElement('div');
        linkItem.className = 'link-item';
        linkItem.dataset.linkId = linkId;
        
        linkItem.innerHTML = `
            <div class="link-header">
                <h4>External Link ${this.linkCounter}</h4>
                <button type="button" class="remove-link-btn" title="Remove Link">×</button>
            </div>
            <div class="link-fields">
                <div class="field-group">
                    <label for="${linkId}_title">Link Title *</label>
                    <input type="text" id="${linkId}_title" name="external_links[${linkId}][title]" 
                           value="${title}" placeholder="e.g., CMS PDGM Guidelines" required>
                </div>
                <div class="field-group">
                    <label for="${linkId}_url">URL *</label>
                    <input type="url" id="${linkId}_url" name="external_links[${linkId}][url]" 
                           value="${url}" placeholder="https://example.com" required>
                </div>
                <div class="field-group">
                    <label for="${linkId}_description">Description</label>
                    <textarea id="${linkId}_description" name="external_links[${linkId}][description]" 
                              rows="2" placeholder="Brief description of what this link contains">${description}</textarea>
                </div>
            </div>
        `;
        
        linksContainer.appendChild(linkItem);
        
        // Focus on title field
        linkItem.querySelector('input[type="text"]').focus();
        
        // Add to internal tracking
        this.externalLinks.push({
            id: linkId,
            title: title,
            url: url,
            description: description
        });
    }

    removeExternalLink(linkItem) {
        const linkId = linkItem.dataset.linkId;
        
        // Remove from internal tracking
        this.externalLinks = this.externalLinks.filter(link => link.id !== linkId);
        
        // Remove from DOM
        linkItem.remove();
        
        // Update numbering
        this.updateLinkNumbering();
    }

    updateLinkNumbering() {
        const linkItems = document.querySelectorAll('.link-item');
        linkItems.forEach((item, index) => {
            const header = item.querySelector('.link-header h4');
            header.textContent = `External Link ${index + 1}`;
        });
    }

    loadExistingLinks() {
        // Check if there's existing external links data
        const existingLinksField = document.querySelector('input[name="external_links"]');
        if (existingLinksField && existingLinksField.value) {
            try {
                const links = JSON.parse(existingLinksField.value);
                links.forEach(link => {
                    this.addExternalLink(link.title, link.url, link.description);
                });
            } catch (e) {
                console.warn('Could not parse existing external links data');
            }
        }
    }

    autoSave(form) {
        // Simple auto-save to localStorage
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        localStorage.setItem('kb_article_draft', JSON.stringify(data));
        
        // Show auto-save indicator
        this.showAutoSaveIndicator();
    }

    showAutoSaveIndicator() {
        let indicator = document.querySelector('.autosave-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'autosave-indicator';
            document.querySelector('.kb-editor-container').appendChild(indicator);
        }
        
        indicator.textContent = 'Draft saved';
        indicator.style.display = 'block';
        
        setTimeout(() => {
            indicator.style.display = 'none';
        }, 2000);
    }

    // Public method to get external links data
    getExternalLinksData() {
        return this.externalLinks;
    }

    // Public method to validate form
    validateForm() {
        const errors = [];
        
        // Check required fields
        const title = document.querySelector('#title, input[name="title"]');
        const content = document.querySelector('.enhanced-textarea');
        
        if (!title || !title.value.trim()) {
            errors.push('Article title is required');
        }
        
        if (!content || !content.value.trim()) {
            errors.push('Article content is required');
        }
        
        // Validate external links
        const linkItems = document.querySelectorAll('.link-item');
        linkItems.forEach((item, index) => {
            const titleField = item.querySelector('input[type="text"]');
            const urlField = item.querySelector('input[type="url"]');
            
            if (titleField.value.trim() && !urlField.value.trim()) {
                errors.push(`External Link ${index + 1}: URL is required when title is provided`);
            }
            
            if (urlField.value.trim() && !this.isValidUrl(urlField.value)) {
                errors.push(`External Link ${index + 1}: Please enter a valid URL`);
            }
        });
        
        return errors;
    }

    isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.kbEditor = new KnowledgeBaseEditor();
});

// Fallback for pages that load content dynamically
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        if (!window.kbEditor) {
            window.kbEditor = new KnowledgeBaseEditor();
        }
    });
} else {
    if (!window.kbEditor) {
        window.kbEditor = new KnowledgeBaseEditor();
    }
}

