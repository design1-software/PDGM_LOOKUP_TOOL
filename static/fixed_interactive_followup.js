/**
 * Interactive Follow-up Question System - CORRECTED VERSION
 * Fixed to match the exact API structure expected by the Flask server
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
                        // Look for the actual class used in HTML: .followup
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
        }, 1000);
    }

    enhanceFollowupElement(followupEl) {
        // Skip if already enhanced
        if (followupEl.classList.contains('enhanced-followup')) {
            return;
        }

        const followupText = followupEl.textContent.trim();
        if (!followupText) return;

        console.log('Enhancing follow-up element:', followupText);

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
                    <div class="followup-icon">🔍</div>
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
                                    ⭐ Get Refined Answer
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
            .replace(/<br>$/, '');
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
        
        // Default answers if no specific context detected
        if (quickAnswers.length === 0) {
            quickAnswers.push('Yes, multiple conditions present');
            quickAnswers.push('No, single primary condition');
            quickAnswers.push('Uncertain, need clarification');
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
        button.innerHTML = '⏳ Processing...';
        
        try {
            // CORRECTED: Match exact API structure from Flask app.py
            const requestData = {
                original_query: this.originalQuery || 'E11.65',
                original_result: this.originalResult || 'Type 2 diabetes mellitus with hyperglycemia',
                followup_answer: textarea.value.trim()
            };
            
            console.log('Sending follow-up request:', requestData);
            
            const response = await fetch('/api/followup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin', // Include session cookies for @login_required
                body: JSON.stringify(requestData)
            });
            
            console.log('Response status:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Server error response:', errorText);
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Response data:', data);
            
            if (data.success) {
                responseDiv.innerHTML = `
                    <div class="followup-result">
                        <h4>✅ Refined Analysis</h4>
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
                    <p>❌ Sorry, there was an error processing your follow-up question. Please try again.</p>
                    <p class="error-details">${error.message}</p>
                </div>
            `;
            responseDiv.style.display = 'block';
        } finally {
            this.isProcessing = false;
            button.disabled = false;
            button.innerHTML = '⭐ Get Refined Answer';
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
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        console.log('Initializing Interactive Follow-up System (DOM ready)');
        window.interactiveFollowup = new InteractiveFollowup();
    });
} else {
    console.log('Initializing Interactive Follow-up System (immediate)');
    window.interactiveFollowup = new InteractiveFollowup();
}

