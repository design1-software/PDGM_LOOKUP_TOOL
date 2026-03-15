/**
 * Enhanced Query Progress Meter for PDGM Lookup Tool
 * Provides detailed progress feedback, cancellation, and timeout handling
 */

class PDGMQueryProgress {
    constructor() {
        this.currentRequest = null;
        this.progressStages = [
            { name: 'Validating Input', duration: 500 },
            { name: 'Processing Diagnosis', duration: 2000 },
            { name: 'Mapping ICD-10 Code', duration: 1500 },
            { name: 'Determining PDGM Group', duration: 1000 },
            { name: 'Finalizing Results', duration: 500 }
        ];
        this.currentStage = 0;
        this.startTime = null;
        this.timeoutId = null;
        this.progressInterval = null;
        this.init();
    }

    init() {
        // Only enhance if the original form exists
        const form = document.querySelector('form');
        let askButton = document.querySelector('button[type="submit"], .ask-button');
        if (!askButton) {
            const buttons = document.querySelectorAll('button');
            askButton = Array.from(buttons).find(btn => btn.textContent.trim().toUpperCase() === 'ASK ME');
        }
        
        if (form && askButton) {
            this.enhanceForm(form, askButton);
        }
    }

    enhanceForm(form, askButton) {
        // Store original submit handler
        this.originalSubmitHandler = form.onsubmit;
        
        // Add enhanced progress UI after the form
        this.createProgressUI(form);
        
        // Enhance form submission
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSubmit(form);
        });
    }

    createProgressUI(form) {
        const progressContainer = document.createElement('div');
        progressContainer.id = 'enhanced-progress-container';
        progressContainer.className = 'enhanced-progress-container';
        progressContainer.style.display = 'none';
        
        progressContainer.innerHTML = `
            <div class="progress-header">
                <h3>Processing Your Query</h3>
                <button type="button" class="cancel-button" onclick="pdgmProgress.cancelQuery()">
                    Cancel
                </button>
            </div>
            
            <div class="progress-stages">
                ${this.progressStages.map((stage, index) => `
                    <div class="progress-stage" data-stage="${index}">
                        <div class="stage-indicator">
                            <div class="stage-number">${index + 1}</div>
                            <div class="stage-spinner"></div>
                            <div class="stage-checkmark">✓</div>
                        </div>
                        <div class="stage-label">${stage.name}</div>
                    </div>
                `).join('')}
            </div>
            
            <div class="progress-bar-container">
                <div class="progress-bar">
                    <div class="progress-fill"></div>
                </div>
                <div class="progress-text">
                    <span class="current-stage-text">Preparing...</span>
                    <span class="time-elapsed">0s</span>
                </div>
            </div>
            
            <div class="progress-details">
                <div class="estimated-time">Estimated time: <span>5-8 seconds</span></div>
                <div class="query-preview">Query: <span class="query-text"></span></div>
            </div>
        `;
        
        form.parentNode.insertBefore(progressContainer, form.nextSibling);
    }

    async handleSubmit(form) {
        const formData = new FormData(form);
        const diagnosis = formData.get('diagnosis') || formData.get('query') || '';
        
        if (!diagnosis.trim()) {
            alert('Please enter a diagnosis or symptom to analyze.');
            return;
        }

        this.startProgress(diagnosis);
        
        try {
            // Call original submit logic or make API request
            const result = await this.makeAPIRequest(formData);
            this.completeProgress(result);
        } catch (error) {
            this.handleError(error);
        }
    }

    startProgress(diagnosis) {
        this.startTime = Date.now();
        this.currentStage = 0;
        
        // Show progress container
        const container = document.getElementById('enhanced-progress-container');
        container.style.display = 'block';
        
        // Update query preview
        container.querySelector('.query-text').textContent = diagnosis;
        
        // Hide original loading indicator if it exists
        const originalLoading = document.querySelector('.loading-indicator, .spinner');
        if (originalLoading) {
            originalLoading.style.display = 'none';
        }
        
        // Start progress animation
        this.animateProgress();
        
        // Set timeout for long-running queries
        this.timeoutId = setTimeout(() => {
            this.handleTimeout();
        }, 30000); // 30 second timeout
    }

    animateProgress() {
        this.progressInterval = setInterval(() => {
            this.updateProgressDisplay();
        }, 100);
        
        // Advance through stages
        this.advanceStages();
    }

    async advanceStages() {
        for (let i = 0; i < this.progressStages.length; i++) {
            if (this.currentRequest && this.currentRequest.aborted) {
                break;
            }
            
            this.currentStage = i;
            this.updateStageDisplay(i);
            
            // Wait for stage duration
            await new Promise(resolve => setTimeout(resolve, this.progressStages[i].duration));
            
            // Mark stage as complete
            this.completeStage(i);
        }
    }

    updateProgressDisplay() {
        const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
        const container = document.getElementById('enhanced-progress-container');
        
        if (container) {
            container.querySelector('.time-elapsed').textContent = `${elapsed}s`;
            container.querySelector('.current-stage-text').textContent = 
                this.progressStages[this.currentStage]?.name || 'Processing...';
            
            // Update progress bar
            const progress = Math.min(((this.currentStage + 1) / this.progressStages.length) * 100, 95);
            container.querySelector('.progress-fill').style.width = `${progress}%`;
        }
    }

    updateStageDisplay(stageIndex) {
        const stageElement = document.querySelector(`[data-stage="${stageIndex}"]`);
        if (stageElement) {
            stageElement.classList.add('active');
            stageElement.querySelector('.stage-spinner').style.display = 'block';
        }
    }

    completeStage(stageIndex) {
        const stageElement = document.querySelector(`[data-stage="${stageIndex}"]`);
        if (stageElement) {
            stageElement.classList.remove('active');
            stageElement.classList.add('completed');
            stageElement.querySelector('.stage-spinner').style.display = 'none';
            stageElement.querySelector('.stage-checkmark').style.display = 'block';
        }
    }

    async makeAPIRequest(formData) {
        // Create AbortController for cancellation
        const controller = new AbortController();
        this.currentRequest = controller;
        
        const response = await fetch('/api/lookup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                diagnosis: formData.get('diagnosis') || formData.get('query'),
                zip_code: formData.get('zip_code') || ''
            }),
            signal: controller.signal
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }

    completeProgress(result) {
        clearTimeout(this.timeoutId);
        clearInterval(this.progressInterval);
        
        // Complete all stages
        for (let i = 0; i < this.progressStages.length; i++) {
            this.completeStage(i);
        }
        
        // Update progress bar to 100%
        const container = document.getElementById('enhanced-progress-container');
        container.querySelector('.progress-fill').style.width = '100%';
        container.querySelector('.current-stage-text').textContent = 'Complete!';
        
        // Hide progress after a moment and show results
        setTimeout(() => {
            container.style.display = 'none';
            this.displayResults(result);
        }, 1000);
    }

    displayResults(result) {
        // Create or update results display
        let resultsContainer = document.getElementById('query-results');
        if (!resultsContainer) {
            resultsContainer = document.createElement('div');
            resultsContainer.id = 'query-results';
            resultsContainer.className = 'query-results';
            document.querySelector('form').parentNode.appendChild(resultsContainer);
        }
        
        resultsContainer.innerHTML = `
            <div class="results-header">
                <h3>PDGM Analysis Complete</h3>
                <button type="button" onclick="this.parentNode.parentNode.style.display='none'">×</button>
            </div>
            <div class="results-content">
                ${this.formatResults(result)}
            </div>
            <div class="results-actions">
                <button type="button" onclick="pdgmProgress.newQuery()">New Query</button>
                <button type="button" onclick="pdgmProgress.exportResults()">Export Results</button>
            </div>
        `;
        
        resultsContainer.style.display = 'block';
    }

    formatResults(result) {
        if (result.error) {
            return `<div class="error-message">${result.error}</div>`;
        }
        
        return `
            <div class="result-item">
                <label>PDGM Group:</label>
                <span class="result-value">${result.pdgm_group || 'Not determined'}</span>
            </div>
            <div class="result-item">
                <label>ICD-10 Code:</label>
                <span class="result-value">${result.icd_code || 'Not specified'}</span>
            </div>
            <div class="result-item">
                <label>Description:</label>
                <span class="result-value">${result.description || 'No description available'}</span>
            </div>
            ${result.follow_up_questions ? `
                <div class="follow-up-section">
                    <h4>Follow-up Questions:</h4>
                    <div class="follow-up-questions">
                        ${result.follow_up_questions.map(q => `
                            <div class="follow-up-question">
                                <p>${q.question}</p>
                                <div class="question-actions">
                                    <button onclick="pdgmProgress.answerQuestion('${q.id}', 'yes')">Yes</button>
                                    <button onclick="pdgmProgress.answerQuestion('${q.id}', 'no')">No</button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        `;
    }

    handleError(error) {
        clearTimeout(this.timeoutId);
        clearInterval(this.progressInterval);
        
        const container = document.getElementById('enhanced-progress-container');
        container.innerHTML = `
            <div class="error-container">
                <h3>Query Failed</h3>
                <p class="error-message">${error.message || 'An unexpected error occurred'}</p>
                <div class="error-actions">
                    <button onclick="pdgmProgress.retryQuery()">Retry</button>
                    <button onclick="pdgmProgress.newQuery()">New Query</button>
                </div>
            </div>
        `;
    }

    handleTimeout() {
        const container = document.getElementById('enhanced-progress-container');
        container.innerHTML = `
            <div class="timeout-container">
                <h3>Query Taking Longer Than Expected</h3>
                <p>Your query is still processing. This may take a few more moments.</p>
                <div class="timeout-actions">
                    <button onclick="pdgmProgress.continueWaiting()">Continue Waiting</button>
                    <button onclick="pdgmProgress.cancelQuery()">Cancel</button>
                </div>
            </div>
        `;
    }

    cancelQuery() {
        if (this.currentRequest) {
            this.currentRequest.abort();
        }
        
        clearTimeout(this.timeoutId);
        clearInterval(this.progressInterval);
        
        const container = document.getElementById('enhanced-progress-container');
        container.style.display = 'none';
        
        // Show original form
        document.querySelector('form').style.display = 'block';
    }

    newQuery() {
        this.cancelQuery();
        document.querySelector('form input[type="text"]').value = '';
        document.querySelector('form input[type="text"]').focus();
        
        // Hide results
        const results = document.getElementById('query-results');
        if (results) {
            results.style.display = 'none';
        }
    }

    retryQuery() {
        const form = document.querySelector('form');
        this.handleSubmit(form);
    }

    continueWaiting() {
        // Extend timeout by another 30 seconds
        this.timeoutId = setTimeout(() => {
            this.handleTimeout();
        }, 30000);
        
        // Restore progress display
        this.startProgress(document.querySelector('.query-text').textContent);
    }

    answerQuestion(questionId, answer) {
        // Handle follow-up question responses
        console.log(`Question ${questionId} answered: ${answer}`);
        // This would typically make another API call with the answer
    }

    exportResults() {
        // Export functionality
        const results = document.getElementById('query-results');
        const text = results.textContent;
        
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'pdgm-results.txt';
        a.click();
        URL.revokeObjectURL(url);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.pdgmProgress = new PDGMQueryProgress();
});

// Fallback for pages that load content dynamically
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        if (!window.pdgmProgress) {
            window.pdgmProgress = new PDGMQueryProgress();
        }
    });
} else {
    if (!window.pdgmProgress) {
        window.pdgmProgress = new PDGMQueryProgress();
    }
}

