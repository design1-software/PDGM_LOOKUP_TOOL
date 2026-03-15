// Enhanced Loading Indicators and Progress Feedback for PDGM Tool

// Progress tracking for documentation generation
class DocumentationProgress {
    constructor() {
        this.steps = [
            { id: 'analyzing', text: 'Analyzing diagnosis and PDGM group...', duration: 1000 },
            { id: 'building', text: 'Building enhanced OASIS prompt...', duration: 2000 },
            { id: 'generating', text: 'Generating clinical documentation...', duration: 4000 },
            { id: 'formatting', text: 'Formatting and validating content...', duration: 1000 }
        ];
        this.currentStep = 0;
        this.progressInterval = null;
    }

    start(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        // Create progress UI
        container.innerHTML = `
            <div class="modal-loading">
                <div class="loading-spinner-large"></div>
                <div class="modal-loading-text">Preparing your documentation...</div>
                <div class="progress-steps" id="progress-steps">
                    ${this.steps.map((step, index) => `
                        <div class="progress-step ${index === 0 ? 'active' : 'pending'}" id="step-${step.id}">
                            <div class="progress-step-icon">${index + 1}</div>
                            <span>${step.text}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        // Start progress simulation
        this.simulateProgress();
    }

    simulateProgress() {
        this.currentStep = 0;
        this.updateStep(0, 'active');

        this.progressInterval = setInterval(() => {
            if (this.currentStep < this.steps.length - 1) {
                // Complete current step
                this.updateStep(this.currentStep, 'completed');
                
                // Move to next step
                this.currentStep++;
                this.updateStep(this.currentStep, 'active');
            }
        }, this.steps[this.currentStep]?.duration || 2000);
    }

    updateStep(stepIndex, status) {
        const stepElement = document.getElementById(`step-${this.steps[stepIndex].id}`);
        if (stepElement) {
            stepElement.className = `progress-step ${status}`;
            
            if (status === 'completed') {
                const icon = stepElement.querySelector('.progress-step-icon');
                icon.innerHTML = '✓';
            }
        }
    }

    complete(containerId, content) {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }

        // Complete all steps
        this.steps.forEach((step, index) => {
            this.updateStep(index, 'completed');
        });

        // Show success message briefly, then content
        const container = document.getElementById(containerId);
        if (container) {
            setTimeout(() => {
                container.innerHTML = content;
            }, 500);
        }
    }

    error(containerId, errorMessage) {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }

        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="error-message">
                    <strong>Error:</strong> ${errorMessage}
                    <button onclick="closeRoadmapModal(); closeAssessmentModal();" style="margin-left: 10px; padding: 4px 8px; background: #dc2626; color: white; border: none; border-radius: 4px; cursor: pointer;">Close</button>
                </div>
            `;
        }
    }
}

// Enhanced button loading states
function setButtonLoading(buttonElement, isLoading) {
    if (!buttonElement) return;

    if (isLoading) {
        buttonElement.classList.add('btn-loading');
        buttonElement.disabled = true;
        buttonElement.dataset.originalText = buttonElement.innerHTML;
        
        // Add spinner to button text
        const spinner = '<span class="loading-spinner"></span>';
        buttonElement.innerHTML = spinner + buttonElement.textContent;
    } else {
        buttonElement.classList.remove('btn-loading');
        buttonElement.disabled = false;
        if (buttonElement.dataset.originalText) {
            buttonElement.innerHTML = buttonElement.dataset.originalText;
        }
    }
}

// Enhanced showRoadmap function with loading indicators
async function showRoadmapEnhanced() {
    if (!currentResults) return;

    const pdgmGroup = extractPdgmGroup(currentResults.response);
    const select = document.getElementById('discipline-select');
    const disciplines = Array.from(select.selectedOptions).map(o => o.value);
    
    // Get button element
    const roadmapButton = event.target;
    
    // Show modal immediately with loading state
    const modal = document.getElementById('roadmap-modal');
    modal.style.display = 'block';
    
    // Start progress tracking
    const progress = new DocumentationProgress();
    progress.start('roadmap-body');
    
    // Set button loading state
    setButtonLoading(roadmapButton, true);
    
    try {
        const startTime = Date.now();
        
        const resp = await fetch('/api/roadmap', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                diagnosis: currentQuery,
                pdgm_group: pdgmGroup,
                disciplines: disciplines
            })
        });
        
        const data = await resp.json();
        
        // Ensure minimum loading time for better UX
        const minLoadTime = 2000;
        const elapsed = Date.now() - startTime;
        const remainingTime = Math.max(0, minLoadTime - elapsed);
        
        setTimeout(() => {
            if (data.success) {
                const content = `
                    <div class="success-message">Documentation roadmap generated successfully!</div>
                    <div class="roadmap-content">${data.roadmap}</div>
                    <div class="roadmap-actions">
                        <button onclick="copyRoadmap()" class="btn-export">📋 Copy</button>
                        <button onclick="printRoadmap()" class="btn-export">🖨️ Print</button>
                    </div>
                `;
                progress.complete('roadmap-body', content);
            } else {
                progress.error('roadmap-body', data.error || 'Failed to generate roadmap. Please try again.');
            }
            
            // Remove button loading state
            setButtonLoading(roadmapButton, false);
        }, remainingTime);
        
    } catch (error) {
        console.error('Roadmap generation error:', error);
        progress.error('roadmap-body', 'Network error. Please check your connection and try again.');
        setButtonLoading(roadmapButton, false);
    }
}

// Enhanced showAssessment function with loading indicators
async function showAssessmentEnhanced() {
    if (!currentResults) return;

    const pdgmGroup = extractPdgmGroup(currentResults.response);
    const select = document.getElementById('discipline-select');
    const disciplines = Array.from(select.selectedOptions).map(o => o.value);
    
    // Get button element
    const assessmentButton = event.target;
    
    // Show modal immediately with loading state
    const modal = document.getElementById('assessment-modal');
    modal.style.display = 'block';
    
    // Start progress tracking
    const progress = new DocumentationProgress();
    progress.start('assessment-body');
    
    // Set button loading state
    setButtonLoading(assessmentButton, true);
    
    try {
        const startTime = Date.now();
        
        const resp = await fetch('/api/assessment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                diagnosis: currentQuery,
                pdgm_group: pdgmGroup,
                disciplines: disciplines
            })
        });
        
        const data = await resp.json();
        
        // Ensure minimum loading time for better UX
        const minLoadTime = 2000;
        const elapsed = Date.now() - startTime;
        const remainingTime = Math.max(0, minLoadTime - elapsed);
        
        setTimeout(() => {
            if (data.success) {
                const content = `
                    <div class="success-message">Sample OASIS assessment generated successfully!</div>
                    <div class="roadmap-content">${data.assessment}</div>
                    <div class="roadmap-actions">
                        <button onclick="copyAssessment()" class="btn-export">📋 Copy</button>
                        <button onclick="printAssessment()" class="btn-export">🖨️ Print</button>
                    </div>
                `;
                progress.complete('assessment-body', content);
            } else {
                progress.error('assessment-body', data.error || 'Failed to generate assessment. Please try again.');
            }
            
            // Remove button loading state
            setButtonLoading(assessmentButton, false);
        }, remainingTime);
        
    } catch (error) {
        console.error('Assessment generation error:', error);
        progress.error('assessment-body', 'Network error. Please check your connection and try again.');
        setButtonLoading(assessmentButton, false);
    }
}

// Enhanced copy functions with feedback
function copyRoadmapEnhanced() {
    const content = document.querySelector('#roadmap-body .roadmap-content');
    const text = content ? content.innerText : document.getElementById('roadmap-body').innerText;
    
    navigator.clipboard.writeText(text).then(() => {
        showToast('Roadmap copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Copy failed. Please try selecting and copying manually.', 'error');
    });
}

function copyAssessmentEnhanced() {
    const content = document.querySelector('#assessment-body .roadmap-content');
    const text = content ? content.innerText : document.getElementById('assessment-body').innerText;
    
    navigator.clipboard.writeText(text).then(() => {
        showToast('Assessment copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Copy failed. Please try selecting and copying manually.', 'error');
    });
}

// Toast notification system
function showToast(message, type = 'info') {
    // Remove existing toast
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()" style="margin-left: 10px; background: none; border: none; color: inherit; cursor: pointer; font-size: 16px;">&times;</button>
    `;
    
    // Add toast styles
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 16px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        animation: slideInRight 0.3s ease-out;
        max-width: 300px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    
    // Set background color based on type
    const colors = {
        success: '#059669',
        error: '#dc2626',
        info: '#2563eb',
        warning: '#d97706'
    };
    toast.style.backgroundColor = colors[type] || colors.info;
    
    // Add to page
    document.body.appendChild(toast);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => toast.remove(), 300);
        }
    }, 3000);
}

// Add CSS for toast animations
const toastStyles = document.createElement('style');
toastStyles.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(toastStyles);

// Initialize enhanced functions when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Replace original functions with enhanced versions
    window.showRoadmap = showRoadmapEnhanced;
    window.showAssessment = showAssessmentEnhanced;
    window.copyRoadmap = copyRoadmapEnhanced;
    window.copyAssessment = copyAssessmentEnhanced;
    
    console.log('Enhanced loading indicators initialized');
});

