// static/js/app.js
document.addEventListener('DOMContentLoaded', () => {
    // --- Element Selectors ---
    const analysisForm = document.getElementById('analysis-form');
    const runAnalysisBtn = document.getElementById('run-analysis-btn');
    const resultsContainer = document.getElementById('results-container');
    const pdfDownloadSection = document.getElementById('pdf-download-section');
    const preparePdfBtn = document.getElementById('prepare-pdf-btn');
    const pdfExportModal = new bootstrap.Modal(document.getElementById('pdfExportModal'));
    const pdfChecklist = document.getElementById('pdf-export-checklist');
    const confirmPdfDownloadBtn = document.getElementById('confirm-pdf-download-btn');

    // --- Helper Functions ---
    function toggleLoading(button, isLoading, loadingText = '') {
        // ... (this function can remain the same)
    }

    function escapeHTML(str) {
        // ... (this function can remain the same)
    }

    // NEW: Function to format the JSON verdict from the backend
    function formatModelVerdict(verdictData) {
        if (!verdictData || typeof verdictData !== 'object') {
            return '<div class="alert alert-warning p-2">Could not load model verdict.</div>';
        }
        const verdict = escapeHTML(verdictData.verdict || 'N/A');
        const justification = escapeHTML(verdictData.justification || 'No justification provided.');
        const sources = (verdictData.sources || []).map(s => `<li><a href="${s}" target="_blank" rel="noopener noreferrer">${s}</a></li>`).join('');

        return `
            <p class="mb-1"><strong>Verdict:</strong> <span class="badge bg-primary">${verdict}</span></p>
            <p class="mb-1"><strong>Justification:</strong> ${justification}</p>
            ${sources ? `<p class="mb-1"><strong>Sources:</strong></p><ul class="source-list">${sources}</ul>` : ''}
        `;
    }

    // REFACTORED: To use claim_id and trigger subsequent calls automatically
    function displayClaimsStructure(claims, claim_ids) {
        resultsContainer.innerHTML = ''; // Clear previous results
        claims.forEach((claimText, index) => {
            const claimId = claim_ids[index];
            const claimCardId = `claim-card-${claimId}`;

            const claimHtml = `
              <div class="claim-card" id="${claimCardId}">
                <h5>Claim ${index + 1}</h5>
                <p class="claim-text mb-3">${escapeHTML(claimText)}</p>

                <strong>Model Verdict:</strong>
                <div id="model-verdict-${claimId}" class="verdict-box model-verdict-box mb-3 p-2">
                    <div class="spinner-border spinner-border-sm" role="status"></div>
                    <span class="text-muted"> Automatically fetching details...</span>
                </div>

                <strong>Suggested Research Questions:</strong>
                <ul id="questions-list-${claimId}" class="question-list list-group list-group-flush mb-3"></ul>
                <hr>

                <strong>External Verification (CrossRef & CORE):</strong>
                <div id="external-verdict-${claimId}" class="verdict-box mb-2 p-2">
                    <div class="spinner-border spinner-border-sm" role="status"></div>
                    <span class="text-muted"> Automatically verifying...</span>
                </div>
                <ul id="external-sources-${claimId}" class="source-list list-unstyled ps-3 mb-3"></ul>
              </div>
            `;
            resultsContainer.innerHTML += claimHtml;

            // --- NEW: Automatically trigger next steps ---
            getModelDetails(claimId);
            verifyExternal(claimId);
        });
    }

    // --- API Call Functions (Refactored) ---
    async function getModelDetails(claimId) {
        const verdictContainer = document.getElementById(`model-verdict-${claimId}`);
        const questionsList = document.getElementById(`questions-list-${claimId}`);
        try {
            const response = await fetch('/api/get-claim-details', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ claim_id: claimId })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error);

            verdictContainer.innerHTML = formatModelVerdict(data.model_verdict_json);
            // ... (populate questions list logic) ...

        } catch (error) {
            verdictContainer.innerHTML = `<div class="alert alert-danger p-2">Error: ${error.message}</div>`;
        }
    }

    async function verifyExternal(claimId) {
        // ... (This function now takes claimId and updates the UI similarly) ...
    }

    async function generateReport(claimId, questionIdx, reportContainerId, button) {
        // ... (This function now needs to use claimId instead of claimIdx) ...
    }

    // --- Event Listeners ---
    analysisForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        // ... (get form data) ...
        toggleLoading(runAnalysisBtn, true, 'Analyzing...');
        try {
            const response = await fetch('/api/analyze', { /* ... */ });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error);

            if (data.claims.length === 0) {
                resultsContainer.innerHTML = '<div class="alert alert-info mt-4">No explicit claims found.</div>';
                return;
            }
            // Pass both claims text and their new database IDs
            displayClaimsStructure(data.claims, data.claim_ids);
            pdfDownloadSection.classList.remove('d-none');

        } catch (error) {
            resultsContainer.innerHTML = `<div class="alert alert-danger mt-4">Error: ${error.message}</div>`;
        } finally {
            toggleLoading(runAnalysisBtn, false, 'Run Analysis');
        }
    });

    preparePdfBtn.addEventListener('click', () => {
        pdfChecklist.innerHTML = ''; // Clear previous
        const generatedReports = document.querySelectorAll('.report-box[data-claim-id]');

        if (generatedReports.length === 0) {
            pdfChecklist.innerHTML = '<p>No reports have been generated yet. Please generate at least one report before exporting.</p>';
        } else {
            generatedReports.forEach(report => {
                const claimId = report.dataset.claimId;
                const questionText = report.dataset.questionText;
                pdfChecklist.innerHTML += `
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" value="${claimId}" id="check-report-${claimId}" checked>
                        <label class="form-check-label" for="check-report-${claimId}">
                            <strong>Claim:</strong> ${escapeHTML(report.closest('.claim-card').querySelector('.claim-text').textContent)}<br>
                            <small class="text-muted"><strong>Question:</strong> ${escapeHTML(questionText)}</small>
                        </label>
                    </div>
                    <hr>
                `;
            });
        }
        pdfExportModal.show();
    });

    confirmPdfDownloadBtn.addEventListener('click', () => {
        const selectedIds = Array.from(pdfChecklist.querySelectorAll('input:checked')).map(input => input.value);
        if (selectedIds.length > 0) {
            const downloadUrl = `/export-pdf?reports=${selectedIds.join(',')}`;
            window.open(downloadUrl, '_blank');
            pdfExportModal.hide();
        } else {
            alert('Please select at least one report to download.');
        }
    });

    // ... (other event listeners for report generation, etc.) ...
});

