/* EDUagent — minimal JS for form handling, SSE progress, chat, and feedback. */

document.addEventListener('DOMContentLoaded', function () {

    // ── File Upload (Index Page) ────────────────────────────────────────
    var uploadZone = document.getElementById('upload-zone');
    var fileInput = document.getElementById('file-input');
    var fileList = document.getElementById('file-list');
    var ingestForm = document.getElementById('ingest-form');
    var ingestBtn = document.getElementById('ingest-btn');
    var ingestStatus = document.getElementById('ingest-status');
    var selectedFiles = [];

    if (uploadZone && fileInput) {
        uploadZone.addEventListener('click', function () { fileInput.click(); });
        uploadZone.addEventListener('dragover', function (e) {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });
        uploadZone.addEventListener('dragleave', function () {
            uploadZone.classList.remove('dragover');
        });
        uploadZone.addEventListener('drop', function (e) {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            addFiles(e.dataTransfer.files);
        });
        fileInput.addEventListener('change', function () {
            addFiles(fileInput.files);
        });
    }

    function addFiles(files) {
        for (var i = 0; i < files.length; i++) {
            selectedFiles.push(files[i]);
        }
        renderFileList();
    }

    function renderFileList() {
        if (!fileList) return;
        fileList.innerHTML = '';
        selectedFiles.forEach(function (f, idx) {
            var div = document.createElement('div');
            div.className = 'file-item';
            div.innerHTML = '<span class="file-name">' + escHtml(f.name) + '</span>' +
                '<button class="file-remove" data-idx="' + idx + '">&times;</button>';
            fileList.appendChild(div);
        });
        fileList.querySelectorAll('.file-remove').forEach(function (btn) {
            btn.addEventListener('click', function () {
                selectedFiles.splice(parseInt(this.dataset.idx), 1);
                renderFileList();
            });
        });
        if (ingestBtn) ingestBtn.disabled = selectedFiles.length === 0;
    }

    if (ingestForm) {
        ingestForm.addEventListener('submit', function (e) {
            e.preventDefault();
            if (selectedFiles.length === 0) return;

            var fd = new FormData();
            selectedFiles.forEach(function (f) { fd.append('files', f); });

            ingestBtn.disabled = true;
            ingestBtn.textContent = 'Analyzing...';
            showStatus(ingestStatus, 'Uploading and analyzing your materials...', 'loading');

            fetch('/api/ingest', { method: 'POST', body: fd })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.error) {
                        showStatus(ingestStatus, data.error, 'error');
                        ingestBtn.disabled = false;
                        ingestBtn.textContent = 'Extract Teaching Persona';
                    } else {
                        showStatus(ingestStatus,
                            'Persona extracted! Style: ' + (data.persona.teaching_style || '') +
                            ', Tone: ' + (data.persona.tone || '') +
                            '. Redirecting...', 'success');
                        setTimeout(function () { window.location.href = '/dashboard'; }, 1500);
                    }
                })
                .catch(function (err) {
                    showStatus(ingestStatus, 'Upload failed: ' + err, 'error');
                    ingestBtn.disabled = false;
                    ingestBtn.textContent = 'Extract Teaching Persona';
                });
        });
    }

    // ── Generation (Generate Page) ──────────────────────────────────────
    var genForm = document.getElementById('generate-form');
    var genBtn = document.getElementById('gen-btn');
    var progressPanel = document.getElementById('progress-panel');
    var progressLog = document.getElementById('progress-log');
    var progressDone = document.getElementById('progress-done');

    if (genForm) {
        genForm.addEventListener('submit', function (e) {
            e.preventDefault();
            var topic = document.getElementById('topic').value;
            var gradeLevel = document.getElementById('grade_level').value;
            var subject = document.getElementById('subject').value;
            var durationWeeks = parseInt(document.getElementById('duration_weeks').value);
            var includeHomework = document.getElementById('include_homework').checked;

            if (!topic) return;

            genBtn.disabled = true;
            genBtn.textContent = 'Generating...';
            progressPanel.hidden = false;
            progressLog.innerHTML = '';
            progressDone.hidden = true;

            var body = JSON.stringify({
                topic: topic,
                grade_level: gradeLevel,
                subject: subject,
                duration_weeks: durationWeeks,
                include_homework: includeHomework
            });

            fetch('/api/full', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: body
            }).then(function (response) {
                var reader = response.body.getReader();
                var decoder = new TextDecoder();
                var buffer = '';

                function read() {
                    reader.read().then(function (result) {
                        if (result.done) {
                            progressDone.hidden = false;
                            genBtn.disabled = false;
                            genBtn.textContent = 'Generate Full Unit';
                            return;
                        }
                        buffer += decoder.decode(result.value, { stream: true });
                        var lines = buffer.split('\n');
                        buffer = lines.pop();

                        lines.forEach(function (line) {
                            if (line.startsWith('data:')) {
                                try {
                                    var payload = JSON.parse(line.slice(5).trim());
                                    addLogEntry(payload);
                                } catch (e) { /* skip malformed */ }
                            }
                        });
                        read();
                    });
                }
                read();
            }).catch(function (err) {
                addLogEntry({ status: 'error', message: 'Connection failed: ' + err });
                genBtn.disabled = false;
                genBtn.textContent = 'Generate Full Unit';
            });
        });
    }

    function addLogEntry(payload) {
        if (!progressLog) return;
        var div = document.createElement('div');
        div.className = 'log-entry ' + (payload.status || '');
        var text = '';
        if (payload.step === 'unit') {
            text = payload.status === 'done'
                ? 'Unit plan created: ' + (payload.title || '') + ' (' + (payload.lesson_count || 0) + ' lessons)'
                : payload.message || 'Working on unit plan...';
        } else if (payload.step === 'lesson') {
            text = payload.status === 'done'
                ? 'Lesson ' + payload.lesson_number + ': ' + (payload.title || '') + ' done'
                : 'Generating lesson ' + (payload.lesson_number || '') + ': ' + (payload.topic || '');
        } else if (payload.step === 'materials') {
            text = payload.status === 'done'
                ? 'Materials generated for lesson'
                : 'Generating materials...';
        } else if (payload.error) {
            text = 'Error: ' + payload.error;
        } else if (payload.unit_id) {
            text = 'All done! Unit ID: ' + payload.unit_id;
            div.className = 'log-entry done';
        } else {
            text = payload.message || JSON.stringify(payload);
        }
        div.textContent = text;
        progressLog.appendChild(div);
        progressLog.scrollTop = progressLog.scrollHeight;
    }

    // ── Star Rating ─────────────────────────────────────────────────────
    var starRating = document.getElementById('star-rating');
    var ratingValue = document.getElementById('rating-value');

    if (starRating) {
        var stars = starRating.querySelectorAll('.star');
        stars.forEach(function (star) {
            star.addEventListener('click', function () {
                var val = parseInt(this.dataset.value);
                ratingValue.value = val;
                stars.forEach(function (s) {
                    s.classList.toggle('active', parseInt(s.dataset.value) <= val);
                    s.textContent = parseInt(s.dataset.value) <= val ? '\u2605' : '\u2606';
                });
            });
            star.addEventListener('mouseenter', function () {
                var val = parseInt(this.dataset.value);
                stars.forEach(function (s) {
                    s.textContent = parseInt(s.dataset.value) <= val ? '\u2605' : '\u2606';
                });
            });
        });
        if (starRating) {
            starRating.addEventListener('mouseleave', function () {
                var val = parseInt(ratingValue.value);
                stars.forEach(function (s) {
                    s.textContent = parseInt(s.dataset.value) <= val ? '\u2605' : '\u2606';
                });
            });
        }
    }

    // ── Feedback Form ───────────────────────────────────────────────────
    var feedbackForm = document.getElementById('feedback-form');
    var feedbackStatus = document.getElementById('feedback-status');

    if (feedbackForm) {
        feedbackForm.addEventListener('submit', function (e) {
            e.preventDefault();
            var fd = new FormData(feedbackForm);
            var rating = parseInt(fd.get('rating'));
            if (!rating || rating < 1) {
                showStatus(feedbackStatus, 'Please select a rating.', 'error');
                return;
            }
            var body = {
                lesson_id: fd.get('lesson_id'),
                rating: rating,
                notes: fd.get('notes') || ''
            };
            fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) {
                    showStatus(feedbackStatus, data.error, 'error');
                } else {
                    showStatus(feedbackStatus, 'Thank you for your feedback!', 'success');
                }
            })
            .catch(function (err) {
                showStatus(feedbackStatus, 'Failed: ' + err, 'error');
            });
        });
    }

    // ── Chat ────────────────────────────────────────────────────────────
    var chatForm = document.getElementById('chat-form');
    var chatMessages = document.getElementById('chat-messages');
    var chatInput = document.getElementById('chat-input');

    if (chatForm) {
        chatForm.addEventListener('submit', function (e) {
            e.preventDefault();
            var question = chatInput.value.trim();
            if (!question) return;

            var lessonId = chatForm.querySelector('[name=lesson_id]').value;
            appendChat('user', question);
            chatInput.value = '';

            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lesson_id: lessonId, question: question })
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) {
                    appendChat('assistant', 'Error: ' + data.error);
                } else {
                    appendChat('assistant', data.response);
                }
            })
            .catch(function (err) {
                appendChat('assistant', 'Connection error: ' + err);
            });
        });
    }

    function appendChat(role, text) {
        if (!chatMessages) return;
        var div = document.createElement('div');
        div.className = 'chat-msg ' + role;
        div.textContent = text;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // ── Helpers ──────────────────────────────────────────────────────────
    function showStatus(el, msg, type) {
        if (!el) return;
        el.hidden = false;
        el.textContent = msg;
        el.className = 'status-box ' + type;
    }

    function escHtml(s) {
        var d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }
});
