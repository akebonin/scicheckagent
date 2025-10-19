<!DOCTYPE html>
<html lang="en">
<head>
    <script type="text/javascript">
        var _iub = _iub || [];
        _iub.csConfiguration = {"siteId":4149829,"cookiePolicyId":82404675,"lang":"en","storage":{"useSiteId":true}};
    </script>
    <script type="text/javascript" src="https://cs.iubenda.com/autoblocking/4149829.js"></script>
    <script type="text/javascript" src="//cdn.iubenda.com/cs/tcf/stub-v2.js"></script>
    <script type="text/javascript" src="//cdn.iubenda.com/cs/tcf/safe-tcf-v2.js"></script>
    <script type="text/javascript" src="//cdn.iubenda.com/cs/gpp/stub.js"></script>
    <script type="text/javascript" src="//cdn.iubenda.com/cs/iubenda_cs.js" charset="UTF-8" async></script>

    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SciCheck AI Agent</title>

    <script async src="https://www.googletagmanager.com/gtag/js?id=G-H5SNSXX9K0"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', 'G-H5SNSXX9K0');
    </script>

    <link rel="manifest" href="/static/manifest.json">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>

    <style>
        body {
            background-color: #f8f9fa;
            color: #212529;
            font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        }

        .container {
            max-width: 900px;
            padding-top: 20px;
            padding-bottom: 50px;
        }

        .header {
            text-align: center;
            margin: 40px 0;
            color: #0d6efd;
        }

        .header img {
            width: 60px;
            height: 60px;
            margin-right: 15px;
            vertical-align: middle;
        }

        .header h2 {
            display: inline;
            vertical-align: middle;
            font-weight: 700;
        }

        .control-card, .claim-card {
            background-color: #ffffff;
            padding: 2.5rem;
            border-radius: 15px;
            margin-bottom: 25px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.08);
            border: 1px solid #e0e0e0;
        }

        .form-label {
            font-weight: 600;
            color: #343a40;
            margin-bottom: 8px;
        }

        .form-control, .form-select {
            border-radius: 8px;
            padding: 0.75rem 1rem;
            border: 1px solid #ced4da;
        }

        .form-control:focus, .form-select:focus {
            border-color: #86b7fe;
            box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
        }

        .btn-primary {
            background-color: #0d6efd;
            border-color: #0d6efd;
            font-weight: 600;
            padding: 0.8rem 1.5rem;
            border-radius: 8px;
            transition: background-color 0.2s, border-color 0.2s;
        }

        .btn-primary:hover {
            background-color: #0b5ed7;
            border-color: #0a58ca;
        }

        .btn-secondary {
            background-color: #6c757d;
            border-color: #6c757d;
            color: #fff;
            font-weight: 500;
            border-radius: 8px;
        }

        .btn-secondary:hover {
            background-color: #5c636a;
            border-color: #565e64;
        }

        .btn-success {
            background-color: #28a745;
            border-color: #28a745;
            font-weight: 600;
            padding: 0.8rem 1.5rem;
            border-radius: 8px;
            transition: background-color 0.2s, border-color 0.2s;
        }

        .btn-success:hover {
            background-color: #218838;
            border-color: #1e7e34;
        }

        .btn-info {
            background-color: #0dcaf0;
            border-color: #0dcaf0;
        }

        .spinner-border {
            width: 1.2rem;
            height: 1.2rem;
            margin-right: 8px;
        }

        .claim-card h5 {
            font-weight: 700;
            color: #0d6efd;
            margin-bottom: 1rem;
            font-size: 1.5rem;
        }

        .claim-card p {
            font-size: 1.05rem;
            line-height: 1.6;
        }

        .verdict-box, .report-box {
            background-color: #e9ecef;
            padding: 18px;
            border-radius: 10px;
            border: 1px solid #dee2e6;
            white-space: pre-wrap;
            font-family: 'Roboto Mono', 'Courier New', monospace;
            font-size: 0.95rem;
            line-height: 1.5;
            color: #343a40;
            overflow-wrap: break-word;
        }

        .report-box {
            background-color: #e8f5ff;
            border-color: #cce7ff;
            margin-top: 15px;
        }

        .report-placeholder {
            min-height: 50px;
            padding-left: 15px;
        }

        .question-list li {
            background-color: #f8f9fa;
            border-color: #e9ecef;
            margin-bottom: 10px;
            border-radius: 8px;
            padding: 15px 20px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: space-between;
            flex-wrap: wrap;
        }

        .question-list li span {
            flex-grow: 1;
            margin-right: 15px;
            font-size: 1rem;
            line-height: 1.5;
            margin-bottom: 10px;
            width: 100%;
        }

        .question-list li button {
            flex-shrink: 0;
            margin-top: 5px;
        }

        .source-list li {
            word-break: break-all;
            margin-bottom: 5px;
            font-size: 0.9rem;
        }

        .source-list a {
            color: #0d6efd;
            text-decoration: none;
        }

        .source-list a:hover {
            text-decoration: underline;
        }

        .footer {
            margin-top: 5rem;
            padding: 2rem 0;
            border-top: 1px solid #dee2e6;
            font-size: 0.9rem;
            color: #6c757d;
        }

        .alert-danger {
            background-color: #f8d7da;
            color: #721c24;
            border-color: #f5c6cb;
        }

        .alert-info {
            background-color: #d1ecf1;
            color: #0c5460;
            border-color: #bee5eb;
        }

        .d-grid button {
            height: 55px;
        }

        .form-check-input.form-switch {
            width: 3em;
            height: 1.5em;
            margin-left: 0.5em;
            vertical-align: middle;
            background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='-4 -4 8 8'%3e%3ccircle r='3' fill='rgba%280, 0, 0, 0.25%29'/%3e%3c/svg%3e");
            background-position: left center;
            border-radius: 1.5em;
            transition: background-position .15s ease-in-out;
        }

        .form-check-input.form-switch:checked {
            background-position: right center;
            background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='-4 -4 8 8'%3e%3ccircle r='3' fill='%23fff'/%3e%3c/svg%3e");
        }

        .form-check-input.form-switch:focus {
            box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
        }

        .form-check-label {
            vertical-align: middle;
            margin-left: 0.5rem;
        }

        .report-checkbox {
            margin-right: 8px;
        }

        .pdf-selection-section {
            background-color: #e8f5e8;
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid #c3e6c3;
        }

        .pdf-selection-list {
            max-height: 300px;
            overflow-y: auto;
            margin-top: 15px;
        }

        .file-upload-group {
            border: 2px dashed #dee2e6;
            border-radius: 8px;
            padding: 2rem;
            text-align: center;
            background-color: #f8f9fa;
            transition: all 0.3s ease;
        }

        .file-upload-group:hover {
            border-color: #0d6efd;
            background-color: #e7f1ff;
        }

        .file-upload-group.dragover {
            border-color: #0d6efd;
            background-color: #d4e6ff;
        }

        .upload-icon {
            font-size: 3rem;
            color: #6c757d;
            margin-bottom: 1rem;
        }

        .file-input-hidden {
            display: none;
        }

        .preview-image {
            max-width: 100%;
            max-height: 200px;
            margin-top: 1rem;
            border-radius: 8px;
        }

        .table {
            width: 100%;
            margin: 10px 0;
        }

        .table-bordered {
            border: 1px solid #dee2e6;
        }

        .table-sm {
            font-size: 0.9rem;
        }

        /* Modal styles for report selection */
        .report-selection-list {
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 15px;
        }
        .report-selection-item {
            padding: 10px;
            border-bottom: 1px solid #f8f9fa;
        }
        .report-selection-item:last-child {
            border-bottom: none;
        }
    </style>
</head>

<body>
    <div class="container">
        <header class="header">
            <img src="https://raw.githubusercontent.com/akebonin/scicheckagent/refs/heads/main/logo.png" alt="SciCheck Logo">
            <h2>SciCheck AI Agent</h2>
        </header>

        <div class="control-card">
            <form id="analysis-form">
                <div class="mb-3">
                    <label for="inputMethod" class="form-label">Input method</label>
                    <select id="inputMethod" class="form-select">
                        <option value="paste">Paste Text</option>
                        <option value="url">Provide URL</option>
                        <option value="image">Upload Image</option>
                        <option value="video">Upload Video</option>
                        <option value="video-url">Video URL</option>
                    </select>
                </div>

                <div id="paste-input-group" class="mb-3">
                    <label for="textInput" class="form-label">Paste article or post content</label>
                    <textarea id="textInput" rows="7" class="form-control" placeholder="Paste content here...">{{ prefill_claim }}</textarea>
                </div>

                <div id="url-input-group" class="mb-3 d-none">
                    <label for="urlInput" class="form-label">Enter article URL</label>
                    <div class="input-group">
                        <input id="urlInput" type="text" class="form-control" placeholder="https://example.com">
                        <button id="fetch-article-btn" class="btn btn-secondary" type="button">
                            <span class="spinner-border spinner-border-sm d-none" role="status" aria-hidden="true"></span>
                            Fetch Article
                        </button>
                    </div>
                </div>

                <div id="image-input-group" class="mb-3 d-none">
                    <label class="form-label">Upload Image with Text</label>
                    <div class="file-upload-group" id="image-upload-area">
                        <div class="upload-icon">🖼️</div>
                        <h5>Drop image here or click to browse</h5>
                        <p class="text-muted">Supports JPG, PNG, GIF (Max 10MB)</p>
                        <input type="file" id="imageInput" class="file-input-hidden" accept="image/*">
                        <button type="button" class="btn btn-outline-primary" onclick="document.getElementById('imageInput').click()">
                            Choose Image
                        </button>
                        <div id="image-preview" class="mt-3"></div>
                    </div>
                    <button id="process-image-btn" class="btn btn-info mt-2 w-100" type="button" disabled>
                        <span class="spinner-border spinner-border-sm d-none" role="status" aria-hidden="true"></span>
                        Extract Text from Image
                    </button>
                </div>

                <div id="video-input-group" class="mb-3 d-none">
                    <label class="form-label">Upload Video</label>
                    <div class="file-upload-group" id="video-upload-area">
                        <div class="upload-icon">📹</div>
                        <h5>Drop video here or click to browse</h5>
                        <p class="text-muted">Supports MP4, AVI, MOV (Max 50MB)</p>
                        <input type="file" id="videoInput" class="file-input-hidden" accept="video/*">
                        <button type="button" class="btn btn-outline-primary" onclick="document.getElementById('videoInput').click()">
                            Choose Video
                        </button>
                    </div>
                    <button id="process-video-btn" class="btn btn-info mt-2 w-100" type="button" disabled>
                        <span class="spinner-border spinner-border-sm d-none" role="status" aria-hidden="true"></span>
                        Transcribe Video
                    </button>
                </div>

                <div id="video-url-input-group" class="mb-3 d-none">
                    <label for="videoUrlInput" class="form-label">Enter Video URL</label>
                    <div class="input-group">
                        <input id="videoUrlInput" type="text" class="form-control" placeholder="https://youtube.com/watch?v=... or https://vimeo.com/...">
                        <button id="transcribe-video-url-btn" class="btn btn-secondary" type="button">
                            <span class="spinner-border spinner-border-sm d-none" role="status" aria-hidden="true"></span>
                            Transcribe Video
                        </button>
                    </div>
                </div>

                <div class="mb-4">
                    <label for="promptMode" class="form-label">Analysis focus</label>
                    <select id="promptMode" class="form-select">
                        <option>General Analysis of Testable Claims</option>
                        <option>Specific Focus on Scientific Claims</option>
                        <option>Technology-Focused Extraction</option>
                    </select>
                </div>

                <div class="mb-4 form-check form-switch">
                    <input class="form-check-input" type="checkbox" id="usePapersToggle" checked>
                    <label class="form-check-label" for="usePapersToggle">📜 Supplement with Crossref + CORE + PubMed data</label>
                </div>

                <div class="d-grid">
                    <button id="run-analysis-btn" class="btn btn-primary btn-lg" type="submit">
                        <span class="spinner-border spinner-border-sm d-none" role="status" aria-hidden="true"></span>
                        Run Analysis
                    </button>
                </div>
            </form>
        </div>

        <div id="results-container"></div>

        <!-- Always visible download button -->
        <div id="pdf-download-section" class="text-center mt-5">
            <button id="download-pdf-btn" class="btn btn-success btn-lg">
                <span class="spinner-border spinner-border-sm d-none" role="status" aria-hidden="true"></span>
                Download Analysis Report (PDF)
            </button>
        </div>

        <footer class="text-center text-muted footer">
            Built by <a href="https://alizgravenil.wixsite.com/alisgravenil" target="_blank" rel="noopener noreferrer">Alis Grave Nil</a>
        </footer>
    </div>

    <!-- Report Selection Modal -->
    <div class="modal fade" id="reportSelectionModal" tabindex="-1" aria-labelledby="reportSelectionModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="reportSelectionModalLabel">Select Reports for PDF</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <button id="select-all-reports-modal" class="btn btn-outline-primary btn-sm">Select All</button>
                        <button id="deselect-all-reports-modal" class="btn btn-outline-secondary btn-sm">Deselect All</button>
                    </div>
                    <div id="report-selection-list" class="report-selection-list">
                        <!-- Dynamic content will be inserted here -->
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button id="generate-pdf-from-modal" class="btn btn-success">
                        <span class="spinner-border spinner-border-sm d-none" role="status" aria-hidden="true"></span>
                        Generate PDF
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const inputMethodSelect = document.getElementById('inputMethod');
            const pasteInputGroup = document.getElementById('paste-input-group');
            const urlInputGroup = document.getElementById('url-input-group');
            const imageInputGroup = document.getElementById('image-input-group');
            const videoInputGroup = document.getElementById('video-input-group');
            const videoUrlInputGroup = document.getElementById('video-url-input-group');
            const textInput = document.getElementById('textInput');
            const urlInput = document.getElementById('urlInput');
            const imageInput = document.getElementById('imageInput');
            const videoInput = document.getElementById('videoInput');
            const videoUrlInput = document.getElementById('videoUrlInput');
            const fetchArticleBtn = document.getElementById('fetch-article-btn');
            const processImageBtn = document.getElementById('process-image-btn');
            const processVideoBtn = document.getElementById('process-video-btn');
            const transcribeVideoUrlBtn = document.getElementById('transcribe-video-url-btn');
            const analysisForm = document.getElementById('analysis-form');
            const runAnalysisBtn = document.getElementById('run-analysis-btn');
            const resultsContainer = document.getElementById('results-container');
            const pdfDownloadSection = document.getElementById('pdf-download-section');
            const downloadPdfBtn = document.getElementById('download-pdf-btn');
            const promptModeSelect = document.getElementById('promptMode');
            const usePapersToggle = document.getElementById('usePapersToggle');
            const imageUploadArea = document.getElementById('image-upload-area');
            const videoUploadArea = document.getElementById('video-upload-area');
            const imagePreview = document.getElementById('image-preview');

            let generatedReports = [];
            let currentImageFile = null;
            let currentVideoFile = null;

            // UI/Display Functions
            function toggleLoading(button, isLoading, loadingText = '', progress = '') {
                const spinner = button.querySelector('.spinner-border');
                const originalText = button.dataset.originalText || button.textContent.trim();

                if (!button.dataset.originalText) {
                    button.dataset.originalText = originalText;
                }

                if (isLoading) {
                    button.disabled = true;
                    if(spinner) spinner.classList.remove('d-none');
                    const progressText = progress ? ` (${progress})` : '';
                    // Target the text node to prevent replacing the spinner element
                    const textNode = Array.from(button.childNodes).find(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0);
                    if(textNode) textNode.textContent = ` ${loadingText}${progressText}`;
                } else {
                    button.disabled = false;
                    if(spinner) spinner.classList.add('d-none');
                    const textNode = Array.from(button.childNodes).find(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0);
                    if(textNode) textNode.textContent = ` ${originalText}`;
                }
            }

            function escapeHTML(str) {
                if (typeof str !== 'string') return str;
                return str.replace(/[&<>"']/g, function(match) {
                    return {
                        '&': '&amp;',
                        '<': '&lt;',
                        '>': '&gt;',
                        '"': '&quot;',
                        "'": '&#39;'
                    }[match];
                });
            }

            function convertMarkdownTablesToHTML(text) {
                // Match markdown tables - they start with |, have a header, separator line, and data rows
                const tableRegex = /(\|.*\|\s*\n\|[-:\s|]+\|\s*\n(?:\|.*\|\s*\n)*)/g;

                return text.replace(tableRegex, (tableMatch) => {
                    const lines = tableMatch.trim().split('\n').filter(line => line.trim().startsWith('|'));

                    if (lines.length < 2) return tableMatch; // Not a valid table

                    let htmlTable = '<table class="table table-bordered table-sm mt-2 mb-3" style="font-size: 0.9rem;">';

                    lines.forEach((line, index) => {
                        const cells = line.split('|').slice(1, -1).map(cell => cell.trim());

                        if (index === 0) {
                            // Header row
                            htmlTable += '<thead><tr>';
                            cells.forEach(cell => {
                                htmlTable += `<th style="padding: 4px 8px; border: 1px solid #dee2e6;">${cell}</th>`;
                            });
                            htmlTable += '</tr></thead><tbody>';
                        } else if (index === 1 && cells.every(cell => cell.replace(/[-:\s]/g, '') === '')) {
                            // Separator line - skip it
                            return;
                        } else {
                            // Data row
                            htmlTable += '<tr>';
                            cells.forEach(cell => {
                                // Check if this might be a header row (if first row was actually separator)
                                const isHeader = index === 1 && lines[0].replace(/[-:\s|]/g, '') === '';
                                if (isHeader) {
                                    htmlTable += `<th style="padding: 4px 8px; border: 1px solid #dee2e6;">${cell}</th>`;
                                } else {
                                    htmlTable += `<td style="padding: 4px 8px; border: 1px solid #dee2e6;">${cell}</td>`;
                                }
                            });
                            htmlTable += '</tr>';
                        }
                    });

                    htmlTable += '</tbody></table>';
                    return htmlTable;
                });
            }

            function formatTextWithMarkdownAndLinks(text) {
                // First normalize Unicode characters
                let normalizedText = text.normalize('NFKD');

                // Replace common problematic characters
                normalizedText = normalizedText.replace(/[–—]/g, '-'); // en-dash and em-dash to hyphen
                normalizedText = normalizedText.replace(/[ââ]/g, '-'); // encoded dashes
                normalizedText = normalizedText.replace(/[â]/g, "'"); // right single quote
                normalizedText = normalizedText.replace(/[ââ]/g, '"'); // quotes
                normalizedText = normalizedText.replace(/[¯]/g, ' '); // macron to space
                normalizedText = normalizedText.replace(/[­]/g, ''); // soft hyphen removal

                // Replace Greek letters with their text equivalents
                normalizedText = normalizedText.replace(/Î²/g, 'beta');
                normalizedText = normalizedText.replace(/Î±/g, 'alpha');
                normalizedText = normalizedText.replace(/Î³/g, 'gamma');

                let formattedText = escapeHTML(normalizedText);

                // PROCESS TABLES BEFORE OTHER MARKDOWN
                formattedText = convertMarkdownTablesToHTML(formattedText);

                // Rest of your existing markdown processing...
                formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                formattedText = formattedText.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
                formattedText = formattedText.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
                formattedText = formattedText.replace(/\n/g, '<br>');

                return formattedText;
            }

            function setupFileUploadDragAndDrop(uploadArea, fileInput, onFileSelect) {
                // Prevent default drag behaviors
                ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                    uploadArea.addEventListener(eventName, preventDefaults, false);
                    document.body.addEventListener(eventName, preventDefaults, false);
                });

                // Highlight drop area when item is dragged over it
                ['dragenter', 'dragover'].forEach(eventName => {
                    uploadArea.addEventListener(eventName, highlight, false);
                });

                ['dragleave', 'drop'].forEach(eventName => {
                    uploadArea.addEventListener(eventName, unhighlight, false);
                });

                // Handle dropped files
                uploadArea.addEventListener('drop', handleDrop, false);

                function preventDefaults(e) {
                    e.preventDefault();
                    e.stopPropagation();
                }

                function highlight() {
                    uploadArea.classList.add('dragover');
                }

                function unhighlight() {
                    uploadArea.classList.remove('dragover');
                }

                function handleDrop(e) {
                    const dt = e.dataTransfer;
                    const files = dt.files;
                    fileInput.files = files;
                    onFileSelect(files[0]);
                }

                // Handle file input change
                fileInput.addEventListener('change', (e) => {
                    if (e.target.files.length > 0) {
                        onFileSelect(e.target.files[0]);
                    }
                });
            }

            function handleImageSelect(file) {
                if (file && file.type.startsWith('image/')) {
                    currentImageFile = file;
                    processImageBtn.disabled = false;

                    // Show preview
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        imagePreview.innerHTML = `<img src="${e.target.result}" class="preview-image" alt="Image preview">`;
                    };
                    reader.readAsDataURL(file);
                } else {
                    alert('Please select a valid image file (JPG, PNG, GIF)');
                    currentImageFile = null;
                    processImageBtn.disabled = true;
                    imagePreview.innerHTML = '';
                }
            }

            function handleVideoSelect(file) {
                if (file && file.type.startsWith('video/')) {
                    currentVideoFile = file;
                    processVideoBtn.disabled = false;
                } else {
                    alert('Please select a valid video file (MP4, AVI, MOV)');
                    currentVideoFile = null;
                    processVideoBtn.disabled = true;
                }
            }

            async function processImage() {
                if (!currentImageFile) {
                    alert('Please select an image first');
                    return;
                }

                toggleLoading(processImageBtn, true, 'Processing image...');
                const formData = new FormData();
                formData.append('image', currentImageFile);

                try {
                    const response = await fetch('/api/process-image', {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();
                    if (!response.ok) {
                        throw new Error(data.error || 'Failed to process image');
                    }

                    // Set the extracted text in the textarea and switch to paste mode
                    textInput.value = data.extracted_text;
                    inputMethodSelect.value = 'paste';
                    inputMethodSelect.dispatchEvent(new Event('change'));
                    alert('Text successfully extracted from image! Ready for analysis.');
                } catch (error) {
                    alert(`Error processing image: ${error.message}`);
                } finally {
                    toggleLoading(processImageBtn, false);
                }
            }


            function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result);
        reader.onerror = error => reject(error);
    });
                }

            async function processVideo() {
    if (!currentVideoFile) {
        alert('Please select a video first');
        return;
    }
    
    toggleLoading(processVideoBtn, true, 'Processing video...');
    
    try {
        // Convert video to audio first using the browser
        const audioBlob = await extractAudioFromVideo(currentVideoFile);
        const base64Audio = await fileToBase64(audioBlob);
        
        // Use your Vercel proxy URL - replace with your actual Vercel URL
        const vercelProxyUrl = 'https://whisper-proxy-beryl.vercel.app/api/transcribe';
        
        const response = await fetch(vercelProxyUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ audioData: base64Audio })
        });
        
        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to transcribe video');
        }
        
        textInput.value = data.transcription;
        inputMethodSelect.value = 'paste';
        inputMethodSelect.dispatchEvent(new Event('change'));
        alert('Video transcribed successfully! Ready for analysis.');
    } catch (error) {
        console.error('Video processing error:', error);
        alert(`Error processing video: ${error.message}`);
    } finally {
        toggleLoading(processVideoBtn, false);
    }
            }

            async function transcribeVideoUrl() {
    const videoUrl = videoUrlInput.value.trim();
    if (!videoUrl) {
        alert('Please enter a video URL');
        return;
    }
    
    if (!videoUrl.match(/^https?:\/\/[^\s/$.?#].[^\s]*$/)) {
        alert('Invalid URL format. Please use a valid URL starting with http:// or https://.');
        return;
    }
    
    toggleLoading(transcribeVideoUrlBtn, true, 'Transcribing...');
    
    try {
        // Use your Vercel proxy URL - replace with your actual Vercel URL
        const vercelProxyUrl = 'https://whisper-proxy-beryl.vercel.app/api/transcribe';
        
        const response = await fetch(vercelProxyUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ audioUrl: videoUrl })
        });
        
        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to transcribe video URL');
        }
        
        textInput.value = data.transcription;
        inputMethodSelect.value = 'paste';
        inputMethodSelect.dispatchEvent(new Event('change'));
        alert('Video URL transcribed successfully!');
    } catch (error) {
        console.error('Video URL transcription error:', error);
        alert(`Error transcribing video URL: ${error.message}`);
    } finally {
        toggleLoading(transcribeVideoUrlBtn, false);
    }
        }

            function extractAudioFromVideo(videoFile) {
    return new Promise((resolve, reject) => {
        const video = document.createElement('video');
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        video.src = URL.createObjectURL(videoFile);
        video.crossOrigin = 'anonymous';
        
        video.onloadedmetadata = () => {
            const source = audioContext.createMediaElementSource(video);
            const destination = audioContext.createMediaStreamDestination();
            
            source.connect(destination);
            
            video.play().then(() => {
                // For now, we'll send the video file directly to the proxy
                // The proxy will handle audio extraction
                URL.revokeObjectURL(video.src);
                resolve(videoFile);
            }).catch(reject);
        };
        
        video.onerror = reject;
    });
            }
            
            function displayClaimsStructure(claims) {
                claims.forEach((claimText, index) => {
                    const claimId = `claim-${index}`;
                    const claimHtml = `
                        <div class="claim-card" id="${claimId}">
                            <h5>Claim ${index + 1}</h5>
                            <p class="claim-text mb-3">${escapeHTML(claimText)}</p>
                            <strong>Model Verdict:</strong>
                            <div id="model-verdict-${claimId}" class="verdict-box model-verdict-box mb-3" style="min-height: 50px;">
                                <span class="text-muted">Loading model verdict...</span>
                            </div>
                            <strong>Suggested Research Questions:</strong>
                            <ul id="questions-list-${claimId}" class="question-list list-group list-group-flush mb-3">
                                <li class="list-group-item">
                                    <span class="text-muted">Loading questions...</span>
                                </li>
                            </ul>
                            <hr>
                            <strong>External Verification (CrossRef, CORE & PubMed):</strong>
                            <div id="external-verdict-${claimId}" class="verdict-box mb-2" style="min-height: 50px;">
                                ${usePapersToggle.checked ? '<span class="text-muted">Loading external verification...</span>' : 'External verification is toggled off.'}
                            </div>
                            <ul id="external-sources-${claimId}" class="source-list list-unstyled ps-3 mb-3"></ul>
                        </div>
                    `;
                    resultsContainer.innerHTML += claimHtml;
                });

                // Auto-load details for all claims
                autoLoadClaimDetails(claims);
            }

            async function autoLoadClaimDetails(claims) {
                const promises = claims.map(async (claim, index) => {
                    const claimId = `claim-${index}`;
                    const verdictContainerId = `model-verdict-${claimId}`;
                    const questionsContainerId = `questions-list-${claimId}`;
                    const externalVerdictContainerId = `external-verdict-${claimId}`;
                    const externalSourcesContainerId = `external-sources-${claimId}`;

                    try {
                        // Load model details
                        await getModelDetails(index, verdictContainerId, questionsContainerId, null, true);

                        // Load external verification if enabled
                        if (usePapersToggle.checked) {
                            await verifyExternal(index, externalVerdictContainerId, externalSourcesContainerId, null, true);
                        }
                    } catch (error) {
                        console.error(`Error loading details for claim ${index}:`, error);
                    }
                });

                for (let i = 0; i < claims.length; i++) {
                    toggleLoading(runAnalysisBtn, true, 'Analyzing', `Claim ${i + 1} of ${claims.length}`);
                    await promises[i];
                }

                toggleLoading(runAnalysisBtn, false);
            }

            async function getModelDetails(claimIdx, verdictContainerId, questionsContainerId, button, autoLoad = false) {
                const verdictContainer = document.getElementById(verdictContainerId);
                const questionsList = document.getElementById(questionsContainerId);

                if (!autoLoad && button) {
                    toggleLoading(button, true, "Loading details...");
                }

                try {
                    const response = await fetch('/api/get-claim-details', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ claim_idx: claimIdx })
                    });

                    if (!response.ok) {
                        const errorData = await response.text(); // Get raw text to see if it's HTML
                        throw new Error(errorData || `Failed to get claim details: ${response.status}`);
                    }

                    const data = await response.json();
                    const formattedVerdict = formatTextWithMarkdownAndLinks(data.model_verdict);

                    verdictContainer.innerHTML = formattedVerdict;
                    questionsList.innerHTML = '';

                    if (data.questions && data.questions.length > 0) {
                        data.questions.forEach((q, q_idx) => {
                            const listItem = document.createElement('li');
                            listItem.className = 'list-group-item';
                            listItem.innerHTML = `
                                <span class="d-block mb-2"><b>Q${q_idx + 1}:</b> ${escapeHTML(q)}</span>
                                <button class="btn btn-primary btn-sm generate-report-btn"
                                    data-claim-idx="${claimIdx}"
                                    data-question-idx="${q_idx}"
                                    data-report-container-id="report-claim-${claimIdx}-${q_idx}">
                                    Generate Report
                                </button>
                                <div id="report-claim-${claimIdx}-${q_idx}" class="report-placeholder mt-2 w-100"></div>
                            `;
                            questionsList.appendChild(listItem);

                            const reportId = `claim-${claimIdx}-question-${q_idx}`;
                            if (!generatedReports.find(r => r.id === reportId)) {
                                generatedReports.push({
                                    id: reportId,
                                    claimIdx: claimIdx,
                                    questionIdx: q_idx,
                                    claimText: document.querySelector(`#claim-${claimIdx} .claim-text`).textContent,
                                    questionText: q
                                });
                            }
                        });
                    } else {
                        questionsList.innerHTML = '<li class="list-group-item">No research questions generated.</li>';
                    }
                } catch (error) {
                    verdictContainer.innerHTML = `<div class="alert alert-danger p-2 mt-2">Error: ${error.message}</div>`;
                    questionsList.innerHTML = `<li class="list-group-item text-danger">Could not load questions: ${error.message}</li>`;
                } finally {
                    if (!autoLoad && button) {
                        toggleLoading(button, false);
                    }
                }
            }

            async function verifyExternal(claimIdx, verdictContainerId, sourcesContainerId, button, autoLoad = false) {
                const verdictContainer = document.getElementById(verdictContainerId);
                const sourcesContainer = document.getElementById(sourcesContainerId);

                if (!autoLoad && button) {
                    toggleLoading(button, true, "Verifying...");
                }

                verdictContainer.innerHTML = '<span class="text-muted">Verifying...</span>';
                sourcesContainer.innerHTML = '';

                try {
                    const response = await fetch('/api/verify-external', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ claim_idx: claimIdx })
                    });

                    const data = await response.json();
                    if (!response.ok) {
                        throw new Error(data.error || 'External verification failed: ${response.status}');
                    }

                    verdictContainer.innerHTML = formatTextWithMarkdownAndLinks(data.verdict);

                    if (data.sources && data.sources.length > 0) {
                        sourcesContainer.innerHTML = data.sources
                            .map(s => `<li>📄 <a href="${s.url}" target="_blank" rel="noopener noreferrer">${escapeHTML(s.title)}</a></li>`)
                            .join('');
                    } else {
                        sourcesContainer.innerHTML = `<li>No external sources found.</li>`;
                    }
                } catch (error) {
                    verdictContainer.innerHTML = `<div class="alert alert-warning p-2 mt-2">Error: ${error.message}</div>`;
                    sourcesContainer.innerHTML = `<li>Could not fetch sources.</li>`;
                } finally {
                    if (!autoLoad && button) {
                        toggleLoading(button, false);
                    }
                }
            }

            async function generateReport(claimIdx, questionIdx, reportContainerId, button) {
                const reportContainer = document.getElementById(reportContainerId);
                reportContainer.innerHTML = '<div class="report-box text-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div> Generating report...</div>';

                if (button) {
                    button.disabled = true;
                    button.innerHTML = 'Generating...';
                }

                try {
                    const response = await fetch('/api/generate-report', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ claim_idx: claimIdx, question_idx: questionIdx })
                    });

                    if (!response.ok) {
                        let errText;
                        try { errText = await response.json(); errText = errText.error || JSON.stringify(errText); } catch(e){ errText = await response.text(); }
                        throw new Error(errText || `Failed to start report generation: ${response.status}`);
                    }

                    reportContainer.innerHTML = '<div class="report-box"></div>';
                    const reportBox = reportContainer.querySelector('.report-box');
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let fullContent = '';
                    let sawAnyChunk = false;

                    while (true) {
                        const { value, done } = await reader.read();
                        if (done) break;
                        sawAnyChunk = true;

                        const chunk = decoder.decode(value, { stream: true });
                        const parts = chunk.split(/\n\n/);
                        for (const part of parts) {
                            const line = part.trim();
                            if (!line) continue;

                            if (line.startsWith('data: ')) {
                                const dataPart = line.substring(6).trim();
                                if (dataPart === '[DONE]') {
                                    reportBox.innerHTML = formatTextWithMarkdownAndLinks(fullContent);
                                    break;
                                }
                                try {
                                    const jsonData = JSON.parse(dataPart);
                                    if (jsonData.content) {
                                        fullContent += jsonData.content;
                                        reportBox.innerHTML = formatTextWithMarkdownAndLinks(fullContent);
                                    }
                                    if (jsonData.error) {
                                        reportBox.innerHTML += `<br><strong class="text-danger">Error: ${escapeHTML(jsonData.error)}</strong>`;
                                    }
                                } catch (e) {
                                    fullContent += dataPart;
                                    reportBox.innerHTML = formatTextWithMarkdownAndLinks(fullContent);
                                }
                            } else {
                                try {
                                    const jsonData = JSON.parse(line);
                                    if (jsonData.content) {
                                        fullContent += jsonData.content;
                                        reportBox.innerHTML = formatTextWithMarkdownAndLinks(fullContent);
                                    }
                                    if (jsonData.error) {
                                        reportBox.innerHTML += `<br><strong class="text-danger">Error: ${escapeHTML(jsonData.error)}</strong>`;
                                    }
                                } catch (e) {
                                    fullContent += line;
                                    reportBox.innerHTML = formatTextWithMarkdownAndLinks(fullContent);
                                }
                            }
                        }
                    }

                    if (fullContent && fullContent.trim().length > 0) {
                        reportBox.innerHTML = formatTextWithMarkdownAndLinks(fullContent);

                        const reportId = `claim-${claimIdx}-question-${questionIdx}`;
                        if (!generatedReports.find(r => r.id === reportId)) {
                            const claimElement = document.querySelector(`#claim-${claimIdx} .claim-text`);
                            const questionElement = document.querySelector(`#questions-list-claim-${claimIdx} li:nth-child(${questionIdx + 1}) span`);
                            generatedReports.push({
                                id: reportId,
                                claimIdx: claimIdx,
                                questionIdx: questionIdx,
                                claimText: claimElement ? claimElement.textContent : `Claim ${claimIdx + 1}`,
                                questionText: questionElement ? questionElement.textContent.replace(`Q${questionIdx + 1}:`, '').trim() : `Question ${questionIdx + 1}`
                            });
                        }
                    } else {
                        reportBox.innerHTML = '<div class="alert alert-warning p-2">No report content returned.</div>';
                    }
                } catch (error) {
                    console.error('Report generation error:', error);
                    reportContainer.innerHTML = `<div class="alert alert-danger">${escapeHTML(error.message)}</div>`;
                } finally {
                    if (button) {
                        button.disabled = false;
                        button.innerHTML = 'Generate Report';
                    }
                }
            }

            // NEW PDF DOWNLOAD FUNCTIONS
            async function openReportSelectionModal() {
                try {
                    toggleLoading(downloadPdfBtn, true, 'Loading available reports...');

                    const response = await fetch('/api/available-reports');

                    if (!response.ok) {
                        throw new Error('Failed to load available reports');
                    }

                    const availableReports = await response.json();

                    if (!availableReports || availableReports.length === 0) {
                        alert('No reports available for download. Please generate some analysis first.');
                        return;
                    }

                    populateReportSelectionModal(availableReports);

                    const modal = new bootstrap.Modal(document.getElementById('reportSelectionModal'));
                    modal.show();

                } catch (error) {
                    console.error('Error opening report selection modal:', error);
                    alert(`Error: ${error.message}`);
                } finally {
                    toggleLoading(downloadPdfBtn, false);
                }
            }

            function populateReportSelectionModal(availableReports) {
                const selectionList = document.getElementById('report-selection-list');

                if (!availableReports || availableReports.length === 0) {
                    selectionList.innerHTML = '<p class="text-muted">No reports available for download.</p>';
                    return;
                }

                let html = '';
                availableReports.forEach((report, index) => {
                    html += `
                    <div class="report-selection-item">
                        <div class="form-check">
                            <input class="form-check-input report-selection-checkbox" type="checkbox"
                                id="modal-report-${index}" value="${report.id}" checked>
                            <label class="form-check-label" for="modal-report-${index}">
                                <strong>${report.type}</strong><br>
                                <small class="text-muted">${report.description}</small>
                            </label>
                        </div>
                    </div>
                    `;
                });

                selectionList.innerHTML = html;

                setupSelectionModalEvents();
            }

            function setupSelectionModalEvents() {
                const selectAllBtn = document.getElementById('select-all-reports-modal');
                const deselectAllBtn = document.getElementById('deselect-all-reports-modal');
                const generatePdfBtn = document.getElementById('generate-pdf-from-modal');

                selectAllBtn.replaceWith(selectAllBtn.cloneNode(true));
                deselectAllBtn.replaceWith(deselectAllBtn.cloneNode(true));
                generatePdfBtn.replaceWith(generatePdfBtn.cloneNode(true));

                const freshSelectAllBtn = document.getElementById('select-all-reports-modal');
                const freshDeselectAllBtn = document.getElementById('deselect-all-reports-modal');
                const freshGeneratePdfBtn = document.getElementById('generate-pdf-from-modal');

                freshSelectAllBtn.addEventListener('click', () => {
                    document.querySelectorAll('.report-selection-checkbox').forEach(checkbox => {
                        checkbox.checked = true;
                    });
                });

                freshDeselectAllBtn.addEventListener('click', () => {
                    document.querySelectorAll('.report-selection-checkbox').forEach(checkbox => {
                        checkbox.checked = false;
                    });
                });

                freshGeneratePdfBtn.addEventListener('click', generatePdfFromSelections);
            }

            async function generatePdfFromSelections() {
                const generatePdfBtn = document.getElementById('generate-pdf-from-modal');
                const checkboxes = document.querySelectorAll('.report-selection-checkbox:checked');

                if (checkboxes.length === 0) {
                    alert('Please select at least one report to include in the PDF.');
                    return;
                }

                const selectedReportIds = Array.from(checkboxes).map(checkbox => checkbox.value);

                try {
                    toggleLoading(generatePdfBtn, true, 'Generating PDF...');

                    const response = await fetch('/export-pdf', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            selected_reports: selectedReportIds,
                            summary_contents: []
                        })
                    });

                    if (!response.ok) {
                        const errorText = await response.text();
                        throw new Error(errorText || 'Failed to generate PDF');
                    }

                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'SciCheck_AI_Report.pdf';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);

                    const modal = bootstrap.Modal.getInstance(document.getElementById('reportSelectionModal'));
                    modal.hide();

                } catch (error) {
                    console.error('Error generating PDF:', error);
                    alert(`Error generating PDF: ${error.message}`);
                } finally {
                    toggleLoading(generatePdfBtn, false);
                }
            }

            // Event Listeners
            inputMethodSelect.addEventListener('change', (event) => {
                const method = inputMethodSelect.value;

                [pasteInputGroup, urlInputGroup, imageInputGroup, videoInputGroup, videoUrlInputGroup]
                    .forEach(el => el.classList.add('d-none'));

                const groupMap = {
                    'paste': pasteInputGroup,
                    'url': urlInputGroup,
                    'image': imageInputGroup,
                    'video': videoInputGroup,
                    'video-url': videoUrlInputGroup
                };

                if(groupMap[method]) groupMap[method].classList.remove('d-none');
            });

            setupFileUploadDragAndDrop(imageUploadArea, imageInput, handleImageSelect);
            setupFileUploadDragAndDrop(videoUploadArea, videoInput, handleVideoSelect);

            processImageBtn.addEventListener('click', processImage);
            processVideoBtn.addEventListener('click', processVideo);
            transcribeVideoUrlBtn.addEventListener('click', transcribeVideoUrl);

            fetchArticleBtn.addEventListener('click', async () => {
                let url = urlInput.value.trim();
                if (!url) {
                    alert('Please enter a valid URL.');
                    return;
                }

                if (!url.match(/^https?:\/\/[^\s/$.?#].[^\s]*$/)) {
                    alert('Invalid URL format. Please use a valid URL starting with http:// or https://.');
                    return;
                }

                toggleLoading(fetchArticleBtn, true, 'Fetching...');

                try {
                    const response = await fetch('/api/extract-article', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url: url }),
                    });

                    const data = await response.json();
                    if (!response.ok) {
                        throw new Error(data.error || 'Failed to fetch article.');
                    }

                    if (!data.article_text || typeof data.article_text !== 'string') {
                        alert('No content was extracted. Please paste the text manually.');
                        return;
                    }

                    textInput.value = data.article_text;
                    inputMethodSelect.value = 'paste';
                    inputMethodSelect.dispatchEvent(new Event('change'));
                    alert('Article content has been fetched and pasted into the text area.');
                } catch (error) {
                    console.error('Fetch error:', error);
                    alert(`Error fetching article: ${error.message}`);
                } finally {
                    toggleLoading(fetchArticleBtn, false);
                }
            });

            analysisForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const articleText = textInput.value.trim();

                if (!articleText) {
                    alert('Article text is empty. Please paste content or use one of the input methods.');
                    return;
                }

                toggleLoading(runAnalysisBtn, true, 'Analyzing...');
                resultsContainer.innerHTML = '';
                generatedReports = [];

                try {
                    const response = await fetch('/api/analyze', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            text: articleText,
                            mode: promptModeSelect.value,
                            usePapers: usePapersToggle.checked
                        }),
                    });

                    const data = await response.json();
                    if (!response.ok) {
                        const errorMessage = data.error || `Failed to analyze text: ${response.status}`;
                        throw new Error(errorMessage);
                    }

                    if (data.claims.length === 0) {
                        resultsContainer.innerHTML = '<div class="alert alert-info mt-4">No explicit claims found in the provided text.</div>';
                        toggleLoading(runAnalysisBtn, false);
                        return;
                    }

                    displayClaimsStructure(data.claims);
                } catch (error) {
                    resultsContainer.innerHTML = `<div class="alert alert-danger mt-4">Error during analysis: ${error.message}</div>`;
                    toggleLoading(runAnalysisBtn, false);
                }
            });

            downloadPdfBtn.addEventListener('click', openReportSelectionModal);

            resultsContainer.addEventListener('click', async (e) => {
                const targetBtn = e.target.closest('.generate-report-btn');
                if (targetBtn) {
                    const { claimIdx, questionIdx, reportContainerId } = targetBtn.dataset;
                    generateReport(parseInt(claimIdx), parseInt(questionIdx), reportContainerId, targetBtn);
                }
            });
        });

        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/static/service-worker.js')
                    .then(registration => {
                        console.log('Service Worker registered:', registration);
                    })
                    .catch(error => {
                        console.error('Service Worker registration failed:', error);
                    });
            });
        }
    </script>
</body>
</html>
