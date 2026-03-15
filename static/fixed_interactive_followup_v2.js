/**
 * Interactive Follow-up Question System v2
 * Allows users to respond to follow-up questions and get AI feedback
 */

class InteractiveFollowup {
    constructor() {
        this.currentFollowupId = null;
        this.originalQuery = null;
        this.originalResult = null;
        this.isProcessing = false;
        
        this.init();
    }

    init() {
        // Watch for new follow-up questions being added to the DOM
        this.observeFollowupChanges();
        
        // Set up event delegation for dynamically created elements
        document.addEventListener('click', (e) => {
            if (e.target.matches('.followup-answer-btn')) {
                e.preventDefault();
                this.handleAnswerClick(e.target);
            } else if (e.target.matches('.followup-submit-btn')) {
                e.preventDefault();
                this.handleSubmitAnswer(e.target);
            } else if (e.target.matches('.followup-skip-btn')) {
                e.preventDefault();
                this.handleSkipFollowup(e.target);
            }
        });
    }

    observeFollowupChanges() {
        // Use MutationObserver to detect when follow-up questions are added
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // FIXED: Look for the actual class used in HTML: .followup
                        const followupElements = node.querySelectorAll ? 
                            node.querySelectorAll('.followup') : 
                            (node.classList && node.classList.contains('followup') ? [node] : []);
                        
                        followupElements.forEach((followupEl) => {
                            this.enhanceFollowupElement(followupEl);
                        });
                        
                        // Also check if the node itself is a followup element
                        if (node.classList && node.classList.contains('followup')) {
                            this.enhanceFollowupElement(node);
                        }
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Also enhance any existing follow-up elements on page load
        setTimeout(() => {
            document.querySelectorAll('.followup').forEach((followupEl) => {
                this.enhanceFollowupElement(followupEl);
            });
        }, 1000); // Wait 1 second for initial content to load
    }

    enhanceFollowupElement(followupEl) {
        // Skip if already enhanced
        if (followupEl.classList.contains('enhanced-followup')) {
            return;
        }

        const followupText = followupEl.textContent.trim();
        if (!followupText) return;

        console.log('Enhancing follow-up element:', followupText); // Debug log

        // Generate unique ID for this follow-up
        const followupId = 'followup_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        // Store original query and result context
        const responseContainer = followupEl.closest('.response-content');
        if (responseContainer) {
            const resultText = responseContainer.querySelector('.result-content pre');
            this.originalResult = resultText ? resultText.textContent : '';
        }

        // Get original query from the input field
        const queryInput = document.querySelector('input[placeholder*="diagnosis"], input[placeholder*="ICD-10"], input[placeholder*="symptom"]');
        this.originalQuery = queryInput ? queryInput.value : '';

        // Create enhanced follow-up interface
        followupEl.innerHTML = `
            <div class="followup-container" data-followup-id="${followupId}">
                <div class="followup-header">
                    <div class="followup-icon">
                        <svg width="20" height="20" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                    </div>
                    <div class="followup-title">Follow-up Question</div>
                </div>
                <div class="followup-question">
                    ${this.formatFollowupText(followupText)}
                </div>
                <div class="followup-actions">
                    <div class="quick-answers" id="quick-answers-${followupId}">
                        ${this.generateQuickAnswers(followupText)}
                    </div>
                    <div class="custom-answer-section">
                        <div class="answer-input-group">
                            <textarea 
                                id="answer-input-${followupId}" 
                                class="followup-answer-input" 
                                placeholder="Or provide your own detailed answer..."
                                rows="2"
                            ></textarea>
                            <div class="answer-buttons">
                                <button type="button" class="followup-submit-btn" data-followup-id="${followupId}">
                                    <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24">
                                        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                                    </svg>
                                    Get Refined Answer
                                </button>
                                <button type="button" class="followup-skip-btn" data-followup-id="${followupId}">
                                    Skip
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="followup-response" id="followup-response-${followupId}" style="display: none;">
                    <!-- AI response will be inserted here -->
                </div>
            </div>
        `;

        followupEl.classList.add('enhanced-followup');
    }

    formatFollowupText(text) {
        // Format the follow-up question text for better readability
        return text
            .replace(/\?/g, '?<br>')
            .replace(/\. /g, '.<br>')
            .replace(/<br>$/, ''); // Remove trailing <br>
    }

    generateQuickAnswers(followupText) {
        // Generate contextual quick answer buttons based on the question
        const quickAnswers = [];
        
        const lowerText = followupText.toLowerCase();
        
        if (lowerText.includes('comorbid') || lowerText.includes('condition')) {
            quickAnswers.push('Yes, multiple conditions present');
            quickAnswers.push('No, single primary condition');
            quickAnswers.push('Uncertain, need clarification');
        }
        
        if (lowerText.includes('acute') || lowerText.includes('exacerbation')) {
            quickAnswers.push('Acute episode');
            quickAnswers.push('Chronic management');
            quickAnswers.push('Post-acute care');
        }
        
        if (lowerText.includes('skilled') || lowerText.includes('nursing')) {
            quickAnswers.push('Skilled nursing required');
            quickAnswers.push('Therapy services needed');
            quickAnswers.push('Both nursing and therapy');
        }
        
        if (lowerText.includes('medication') || lowerText.includes('drug')) {
            quickAnswers.push('Complex medication regimen');
            quickAnswers.push('Standard medications');
            quickAnswers.push('No medication management');
        }
        
        // Default answers if no specific context detected
        if (quickAnswers.length === 0) {
            quickAnswers.push('Yes');
            quickAnswers.push('No');
            quickAnswers.push('Partially');
            quickAnswers.push('Need more information');
        }
        
        return quickAnswers.map(answer => 
            `<button type="button" class="followup-answer-btn" data-answer="${answer}">${answer}</button>`
        ).join('');
    }

    handleAnswerClick(button) {
        const answer = button.dataset.answer;
        const followupContainer = button.closest('.followup-container');
        const followupId = followupContainer.dataset.followupId;
        
        // Fill the textarea with the selected answer
        const textarea = document.getElementById(`answer-input-${followupId}`);
        if (textarea) {
            textarea.value = answer;
            textarea.focus();
        }
        
        // Highlight the selected button
        followupContainer.querySelectorAll('.followup-answer-btn').forEach(btn => {
            btn.classList.remove('selected');
        });
        button.classList.add('selected');
    }

    async handleSubmitAnswer(button) {
        if (this.isProcessing) return;
        
        const followupId = button.dataset.followupId;
        const textarea = document.getElementById(`answer-input-${followupId}`);
        const responseDiv = document.getElementById(`followup-response-${followupId}`);
        
        if (!textarea || !textarea.value.trim()) {
            alert('Please provide an answer before submitting.');
            return;
        }
        
        this.isProcessing = true;
        button.disabled = true;
        button.innerHTML = `
            <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24" class="animate-spin">
                <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
            </svg>
            Processing...
        `;
        
        try {
            const response = await fetch('/api/followup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    original_query: this.originalQuery,
                    original_result: this.originalResult,
                    followup_answer: textarea.value.trim(),
                    followup_id: followupId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                localStorage.setItem("lastFollowupAnswer", textarea.value.trim());
                responseDiv.innerHTML = `
                    <div class="followup-result">
                        <h4>Refined Analysis</h4>
                        <div class="refined-content">
                            <pre>${data.refined_result}</pre>
                        </div>
                    </div>
                `;
                responseDiv.style.display = 'block';
                
                // Scroll to the response
                responseDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                throw new Error(data.error || 'Unknown error occurred');
            }
            
        } catch (error) {
            console.error('Follow-up submission error:', error);
            responseDiv.innerHTML = `
                <div class="followup-error">
                    <p>Sorry, there was an error processing your follow-up question. Please try again.</p>
                    <p class="error-details">${error.message}</p>
                </div>
            `;
            responseDiv.style.display = 'block';
        } finally {
            this.isProcessing = false;
            button.disabled = false;
            button.innerHTML = `
                <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                </svg>
                Get Refined Answer
            `;
        }
    }

    handleSkipFollowup(button) {
        const followupContainer = button.closest('.followup-container');
        followupContainer.style.opacity = '0.5';
        followupContainer.style.pointerEvents = 'none';
        
        // Add a "skipped" indicator
        const header = followupContainer.querySelector('.followup-header');
        if (header) {
            header.innerHTML += ' <span class="skipped-indicator">(Skipped)</span>';
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing Interactive Follow-up System'); // Debug log
    window.interactiveFollowup = new InteractiveFollowup();
});

// Also initialize if DOM is already loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        console.log('Initializing Interactive Follow-up System (DOM ready)'); // Debug log
        window.interactiveFollowup = new InteractiveFollowup();
    });
} else {
    console.log('Initializing Interactive Follow-up System (immediate)'); // Debug log
    window.interactiveFollowup = new InteractiveFollowup();
}

