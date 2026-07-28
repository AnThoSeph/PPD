/** PPD Web UI — production bridge to Python backend */

const $ = (id) => document.getElementById(id);

let currentTemplate = 'creative';
let debounceTimer = null;
let backendReady = false;
let bootStarted = false;

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function getApi() {
  return window.pywebview && window.pywebview.api;
}

let eventsReady = false;

function ensureEvents() {
  if (eventsReady) return;
  try {
    initEvents();
  } catch (err) {
    console.error('initEvents failed:', err);
  }
  eventsReady = true;
}

async function call(method, ...args) {
  const api = getApi();
  if (!api) {
    throw new Error('Backend not connected yet — wait a few seconds or restart the app.');
  }
  if (typeof api[method] !== 'function') {
    throw new Error(`"${method}" is unavailable — close the app fully and restart to load updates.`);
  }
  const result = api[method](...args);
  if (result && typeof result.then === 'function') {
    return await result;
  }
  return result;
}

function setStatus(msg) {
  $('status-bar').textContent = msg;
}

function toast(msg, isError = false, ms = 4000) {
  const el = $('toast');
  el.textContent = msg;
  el.classList.toggle('error', isError);
  el.classList.remove('hidden');
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.add('hidden'), ms);
}

function showLoading(msg = 'Working…') {
  const overlay = $('loading-overlay');
  const msgEl = $('loading-message');
  if (msgEl) msgEl.textContent = msg;
  overlay.classList.remove('hidden');
}

function hideLoading() {
  $('loading-overlay').classList.add('hidden');
}

function setLoadingMessage(msg) {
  const el = $('loading-message');
  if (el) el.textContent = msg;
}

function getYaml() {
  const editor = $('yaml-editor');
  if (editor && editor.value.trim()) return editor.value;
  return null;
}

function getResumeDoc() {
  if (window.SectionEditor) return SectionEditor.getDocument();
  return null;
}

async function getYamlForApi() {
  const doc = getResumeDoc();
  if (doc && doc.resume) {
    try {
      const r = await call('save_structured_resume', doc);
      if (r.ok && r.yaml) return r.yaml;
    } catch (_) {}
  }
  return getYaml() || '';
}

function setYaml(text) {
  const editor = $('yaml-editor');
  editor.value = text || '';
  editor.scrollTop = 0;
  updateLineNumbers();
  updateStats();
  syncEditorHeight();
}

function updateLineNumbers() {
  const editor = $('yaml-editor');
  if (!editor) return;
  const lineCount = Math.max(1, editor.value.split('\n').length);
  const nums = [];
  for (let i = 1; i <= lineCount; i++) nums.push(String(i));
  $('line-numbers').textContent = nums.join('\n');
  $('line-numbers').scrollTop = editor.scrollTop;
}

function syncEditorHeight() {
  const editor = $('yaml-editor');
  const wrap = editor && editor.parentElement;
  if (wrap) editor.style.height = wrap.clientHeight + 'px';
}

function updateStats(stats) {
  if (stats) {
    $('editor-stats').textContent = `Lines: ${stats.lines}, Chars: ${stats.chars}`;
  } else {
    const t = getYaml();
    $('editor-stats').textContent = `Lines: ${t.split('\n').length}, Chars: ${t.length}`;
  }
}

function updateScores(ats, label, skill) {
  $('ats-score').textContent = `${ats || 0}%`;
  $('ats-label').textContent = label || '—';
  $('skill-match').textContent = `Skill Match: ${skill || 0}%`;
}

function updatePreview(dataUrl, allPages) {
  const pagesEl = $('preview-pages');
  const img = $('preview-img');
  const ph = $('preview-placeholder');
  const urls = (allPages && allPages.length) ? allPages : (dataUrl ? [dataUrl] : []);

  pagesEl.innerHTML = '';
  if (urls.length) {
    urls.forEach((url, idx) => {
      const wrap = document.createElement('div');
      wrap.style.width = '100%';
      wrap.style.display = 'flex';
      wrap.style.flexDirection = 'column';
      wrap.style.alignItems = 'center';
      const pageImg = document.createElement('img');
      pageImg.src = url;
      pageImg.alt = `Resume page ${idx + 1}`;
      wrap.appendChild(pageImg);
      if (urls.length > 1) {
        const label = document.createElement('div');
        label.id = idx === 0 ? 'preview-page-label' : '';
        label.className = 'preview-page-label';
        label.textContent = `Page ${idx + 1} of ${urls.length}`;
        wrap.appendChild(label);
      }
      pagesEl.appendChild(wrap);
    });
    pagesEl.classList.remove('hidden');
    img.classList.add('hidden');
    ph.classList.add('hidden');
  } else {
    pagesEl.classList.add('hidden');
    img.classList.add('hidden');
    ph.classList.remove('hidden');
  }
}

function setPreviewModeNote(mode, filename, templateId, templateName) {
  const note = $('preview-mode-note');
  const title = $('preview-template-title');
  if (!note) return;
  if (mode === 'live') {
    if (templateId === 'source') {
      if (title) title.textContent = 'Your Upload';
      note.textContent = 'Default template — matches your uploaded PDF layout. Edits update live from structured data.';
    } else {
      if (title) title.textContent = 'Live Preview';
      note.textContent = `Rendering with ${templateName || templateId || 'selected'} template. Your content stays the same — only the layout changes.`;
    }
    note.classList.remove('hidden');
  } else if (mode === 'original') {
    if (title) title.textContent = 'Uploaded PDF Snapshot';
    note.textContent = filename
      ? `Static image of ${filename}. Select a template above for live editing.`
      : 'Static snapshot of your upload.';
    note.classList.remove('hidden');
  } else {
    note.classList.add('hidden');
  }
}

function templateBadge(t) {
  if (t.category === 'upload') return '<span class="template-card-badge upload">Default</span>';
  if (t.tag) return `<span class="template-card-badge tag">${esc(t.tag)}</span>`;
  if (t.ats_friendly) return '<span class="template-card-badge">ATS</span>';
  return '<span class="template-card-badge visual">Visual</span>';
}

function renderTemplateCard(t, selectedId, onClick) {
  const card = document.createElement('button');
  card.type = 'button';
  card.className = 'template-card' + (t.id === selectedId ? ' active' : '');
  card.innerHTML = `
    <div class="template-card-head">
      <span class="template-card-name">${esc(t.name)}</span>
      ${templateBadge(t)}
    </div>
    <div class="template-card-desc">${esc(t.description)}</div>`;
  card.onclick = () => onClick(t.id);
  return card;
}

function renderTemplatePicker(templates, selectedId) {
  const picker = $('template-picker');
  if (!picker) return;
  picker.innerHTML = '';
  (templates || []).forEach((t) => {
    picker.appendChild(renderTemplateCard(t, selectedId, applyTemplate));
  });
}

function renderTemplatesGallery(templates, selectedId) {
  const gallery = $('templates-gallery');
  if (!gallery) return;
  gallery.innerHTML = '';
  (templates || []).forEach((t) => {
    gallery.appendChild(renderTemplateCard(t, selectedId, applyTemplate));
  });
}

async function applyTemplate(templateId) {
  showLoading('Applying template…');
  try {
    const r = await call('set_preview_template', templateId);
    if (!r.ok) { toast(r.message, true); return; }
    const templates = r.templates || (await call('get_templates')).templates;
    renderTemplatePicker(templates, r.preview_template_id || templateId);
    renderTemplatesGallery(templates, r.preview_template_id || templateId);
    const t = (templates || []).find((x) => x.id === (r.preview_template_id || templateId));
    applyState({ ...r, _preserve_yaml: true });
    toast(t ? `Template: ${t.name}` : 'Template applied');
  } catch (e) {
    toast(e.message, true);
  } finally {
    hideLoading();
  }
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function addChatBubble(text, isUser = false) {
  const div = document.createElement('div');
  div.className = `chat-bubble ${isUser ? 'user' : 'ai'}`;
  div.textContent = text;
  $('chat-messages').appendChild(div);
  $('chat-messages').scrollTop = $('chat-messages').scrollHeight;
}

function renderSuggestions(suggestions) {
  const c = $('suggestions-container');
  c.innerHTML = '';
  if (!suggestions || !suggestions.length) return;
  suggestions.forEach((s) => {
    const btn = document.createElement('button');
    btn.className = 'suggestion-btn';
    btn.textContent = s.label;
    btn.onclick = () => applySuggestion(s.id);
    c.appendChild(btn);
  });
}

function applyState(state) {
  if (!state) return;
  if (state.structured && window.SectionEditor) {
    SectionEditor.loadFromStructured(state.structured);
  }
  if (!state._preserve_yaml && state.yaml !== undefined) setYaml(state.yaml);
  if (state.user_name) {
    $('user-name').textContent = state.user_name;
    $('user-avatar').textContent = state.user_name[0].toUpperCase();
  }
  if (state.user_title) $('user-title').textContent = state.user_title;
  if (state.ats_score !== undefined) updateScores(state.ats_score, state.ats_label, state.skill_match);
  if (state.preview_image || state.preview_images) {
    updatePreview(state.preview_image, state.preview_images);
  }
  if (state.preview_mode) {
    const t = (state.templates || []).find((x) => x.id === state.preview_template_id);
    setPreviewModeNote(state.preview_mode, state.source_filename, state.preview_template_id, t?.name);
  }
  if (state.templates) {
    renderTemplatePicker(state.templates, state.preview_template_id);
    renderTemplatesGallery(state.templates, state.preview_template_id);
  } else if (state.preview_template_id) {
    renderTemplatePicker([], state.preview_template_id);
  }
  if (state.stats) updateStats(state.stats);
  if (state.sync_status) {
    $('sync-badge').textContent = state.sync_status;
    $('sync-badge').className = state.sync_status === 'SYNCED' ? 'badge-sync' : 'badge-unsaved';
    if (state.sync_status === 'SYNCED' && window.SectionEditor) SectionEditor.markAllSaved();
  }
  if (state.assistant_message && state._with_chat) addChatBubble(state.assistant_message);
  if (state.suggestions) renderSuggestions(state.suggestions);
  if (state.message) toast(state.message, !state.ok);
}

async function applySuggestion(actionId) {
  showLoading('Applying suggestion…');
  try {
    const r = await call('apply_suggestion', await getYamlForApi(), actionId);
    if (!r.ok) { toast(r.message, true, 6000); return; }
    applyState(r);
    toast('Suggestion applied');
  } catch (e) {
    toast(e.message, true, 6000);
  } finally {
    hideLoading();
  }
}

async function loadInitial() {
  const state = await call('get_initial_state');
  if (!state.ok && state.message) toast(state.message, true);
  $('chat-messages').innerHTML = '';
  applyState({ ...state, _with_chat: true });
  setStatus('Ready — click Upload PDF/Image to import your resume');
}

async function saveResume() {
  showLoading('Saving…');
  try {
    const doc = getResumeDoc();
    const r = doc
      ? await call('save_structured_resume', doc)
      : await call('save_yaml', getYaml() || '');
    if (!r.ok) { toast(r.message, true, 6000); return; }
    if (r.yaml) setYaml(r.yaml);
    applyState({ ...r, _preserve_yaml: true });
    toast('Resume saved');
  } catch (e) {
    toast(e.message, true, 6000);
  } finally {
    hideLoading();
  }
}

async function saveYaml() {
  return saveResume();
}

async function updatePreviewFromEditor() {
  showLoading('Updating preview from your edits…');
  try {
    const doc = getResumeDoc();
    const r = doc
      ? await call('save_and_preview', doc)
      : await call('update_preview', getYaml() || '');
    if (r.ok) {
      if (r.yaml) setYaml(r.yaml);
      applyState({ ...r, _preserve_yaml: true });
      setStatus('Preview updated');
      toast(r.message || 'Preview updated');
    } else {
      toast(r.message, true, 8000);
    }
  } catch (e) {
    toast('Preview update failed: ' + e.message, true, 6000);
  } finally {
    hideLoading();
  }
}

async function exportPdf() {
  showLoading('Building PDF…');
  try {
    const doc = getResumeDoc();
    if (doc) await call('save_structured_resume', doc);
    const content = doc ? (await call('get_structured_resume')).yaml : getYaml();
    const api = getApi();
    const method = api && typeof api.export_pdf_save_as === 'function'
      ? 'export_pdf_save_as'
      : 'build_pdf';
    const r = await call(method, content || '');
    if (r.cancelled) {
      toast('Export cancelled');
      return;
    }
    if (!r.ok) { toast(r.message, true, 8000); setStatus('Export failed'); return; }
    applyState({ ...r, _preserve_yaml: true });
    toast(r.message || 'PDF saved');
    setStatus(`Saved: ${r.path || 'output/resume.pdf'}`);
  } catch (e) {
    toast(e.message, true, 8000);
  } finally {
    hideLoading();
  }
}

async function exportWithTemplate() {
  showLoading('Building PDF with selected template…');
  try {
    const r = await call('build_pdf', await getYamlForApi(), currentTemplate);
    if (!r.ok) { toast(r.message, true, 8000); return; }
    toast(r.message, false, 8000);
    setStatus('Template PDF saved to output/resume-template.pdf');
  } catch (e) {
    toast(e.message, true, 8000);
  } finally {
    hideLoading();
  }
}

async function uploadAndProcess() {
  showLoading('Select your resume file…');
  try {
    const r = await call('upload_and_process');
    if (r.cancelled) { hideLoading(); return; }
    if (!r.ok) { toast(r.message, true, 10000); setStatus('Import failed'); hideLoading(); return; }
    $('chat-messages').innerHTML = '';
    applyState({ ...r, _with_chat: true });
    setStatus(`Imported ${r.raw_lines || 0} text lines from PDF`);
    toast(`Success! ${r.message}`, false, 6000);
  } catch (e) {
    toast(e.message, true, 10000);
    setStatus('Error: ' + e.message);
  } finally {
    hideLoading();
  }
}

async function extractContent() {
  showLoading('Extracting text from uploaded file…');
  try {
    const r = await call('extract_content');
    if (!r.ok) { toast(r.message, true, 6000); return; }
    $('chat-messages').innerHTML = '';
    applyState({ ...r, _with_chat: true });
    toast(r.message, false, 5000);
  } catch (e) {
    toast(e.message, true, 6000);
  } finally {
    hideLoading();
  }
}

async function uploadTemplate() {
  showLoading('Select a .typ template file…');
  try {
    const r = await call('pick_and_upload_template');
    if (r.cancelled) { hideLoading(); return; }
    if (!r.ok) { toast(r.message, true, 6000); hideLoading(); return; }
    if (r.templates) {
      renderTemplatePicker(r.templates, r.template_id);
      renderTemplatesGallery(r.templates, r.template_id);
    }
    toast(`Template "${r.template_id}" uploaded successfully`, false, 4000);
  } catch (e) {
    toast(e.message, true, 6000);
  } finally {
    hideLoading();
  }
}

async function loadSkillGap() {
  try {
    const r = await call('get_skill_gap', await getYamlForApi());
    if (!r.ok) return;
    $('skill-gap-rec').textContent = r.recommendation;
    $('skill-matched').innerHTML = (r.matched_skills || [])
      .map((s) => `<li class="skill-ok">✓ ${esc(s)}</li>`).join('') || '<li>No skills detected yet</li>';
    $('skill-missing').innerHTML = (r.missing_skills || [])
      .map((s) => `<li class="skill-miss">• ${esc(s)}</li>`).join('') || '<li>None — good coverage</li>';
  } catch (e) {
    toast(e.message, true);
  }
}

async function loadJobs() {
  if (window.JobTracker) return JobTracker.load();
}

function setActiveTemplate(t) {
  currentTemplate = t;
  document.querySelectorAll('.template-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.template === t);
  });
  call('set_template', t).catch(() => {});
}

function switchView(view) {
  ['editor', 'skillgap', 'jobs', 'templates'].forEach((v) => {
    $(`view-${v}`).classList.toggle('hidden', v !== view);
  });
  document.querySelectorAll('.nav-btn[data-view]').forEach((b) => {
    b.classList.toggle('active', b.dataset.view === view);
  });
  if (view === 'skillgap') loadSkillGap();
  if (view === 'jobs' && window.JobTracker) JobTracker.onViewOpen();
  if (view === 'templates') loadTemplatesView();
}

async function loadTemplatesView() {
  try {
    const r = await call('get_templates');
    if (r.ok) renderTemplatesGallery(r.templates, r.selected);
  } catch (e) {
    toast(e.message, true);
  }
}

async function sendChat() {
  const input = $('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  addChatBubble(msg, true);
  input.value = '';
  try {
    const r = await call('send_chat', await getYamlForApi(), msg);
    if (r.reply) addChatBubble(r.reply);
  } catch (e) {
    addChatBubble('Error: ' + e.message);
  }
}

function setAiPanelCollapsed(collapsed) {
  const grid = $('editor-grid');
  const toggle = $('btn-toggle-ai');
  if (!grid) return;
  grid.classList.toggle('ai-collapsed', collapsed);
  if (toggle) toggle.classList.toggle('active', !collapsed);
  try { localStorage.setItem('ppd-ai-collapsed', collapsed ? '1' : '0'); } catch (_) {}
}

function initAiPanelToggle() {
  const collapseBtn = $('btn-collapse-ai');
  const headerToggle = $('btn-toggle-ai');
  let collapsed = true;
  try {
    const stored = localStorage.getItem('ppd-ai-collapsed');
    if (stored !== null) collapsed = stored === '1';
  } catch (_) {}
  setAiPanelCollapsed(collapsed);
  if (collapseBtn) collapseBtn.onclick = () => setAiPanelCollapsed(true);
  if (headerToggle) headerToggle.onclick = () => {
    const grid = $('editor-grid');
    setAiPanelCollapsed(!grid || !grid.classList.contains('ai-collapsed'));
  };
}

function initEvents() {
  if (window.SectionEditor) {
    SectionEditor.setOnChange(async (doc) => {
      try {
        const r = await call('save_and_preview', doc);
        if (r.ok) {
          if (r.yaml) setYaml(r.yaml);
          applyState({ ...r, _preserve_yaml: true });
        }
      } catch (_) {}
    });
    SectionEditor.clear();
  }

  initAiPanelToggle();

  const yamlEditor = $('yaml-editor');
  if (yamlEditor) {
    yamlEditor.addEventListener('input', () => {
      updateLineNumbers();
      updateStats();
      $('sync-badge').textContent = 'UNSAVED';
      $('sync-badge').className = 'badge-unsaved';
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(async () => {
        try {
          const a = await call('get_assistant', getYaml() || '');
          if (a) updateScores(a.ats_score, a.ats_label, a.skill_match);
        } catch (_) {}
      }, 600);
    });
    yamlEditor.addEventListener('scroll', () => {
      $('line-numbers').scrollTop = yamlEditor.scrollTop;
    });
  }

  $('btn-toggle-yaml').onclick = () => {
    $('yaml-panel').classList.toggle('hidden');
  };

  window.addEventListener('resize', syncEditorHeight);
  syncEditorHeight();

  $('btn-upload').onclick = uploadAndProcess;
  $('btn-extract').onclick = extractContent;
  $('btn-save').onclick = saveResume;
  $('btn-export').onclick = exportPdf;
  const validateBtn = $('btn-validate');
  if (validateBtn) {
    validateBtn.onclick = async () => {
      try {
        const r = await call('validate_yaml', await getYamlForApi());
        toast(r.message, !r.ok, 5000);
      } catch (e) { toast(e.message, true); }
    };
  }
  $('btn-refresh-preview').onclick = () => updatePreviewFromEditor();
  $('btn-open-pdf').onclick = async () => {
    try {
      const r = await call('open_pdf');
      if (!r.ok) toast(r.message, true);
    } catch (e) { toast(e.message, true); }
  };
  $('btn-analyze').onclick = async () => {
    showLoading('Analyzing design…');
    try {
      const r = await call('analyze_design');
      toast(r.ok ? r.message : r.message, !r.ok, 8000);
    } catch (e) { toast(e.message, true); }
    hideLoading();
  };
  $('btn-analyze-design').onclick = () => $('btn-analyze').click();
  const uploadTmplBtn = $('btn-upload-template');
  if (uploadTmplBtn) uploadTmplBtn.onclick = uploadTemplate;
  const uploadTmplQuick = $('btn-upload-template-quick');
  if (uploadTmplQuick) uploadTmplQuick.onclick = uploadTemplate;

  $('chat-send').onclick = sendChat;
  $('chat-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
  });

  document.querySelectorAll('.nav-btn[data-view]').forEach((btn) => {
    btn.onclick = () => switchView(btn.dataset.view);
  });

  if (window.JobTracker) JobTracker.init();

  $('search-input').addEventListener('keydown', async (e) => {
    if (e.key === 'Enter') {
      try {
        const r = await call('search_yaml', await getYamlForApi(), e.target.value);
        toast(r.count ? `Found on lines: ${r.matches.join(', ')}` : 'No matches');
      } catch (err) { toast(err.message, true); }
    }
  });

  $('btn-dark').onclick = () => document.documentElement.classList.toggle('dark');

  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 's') { e.preventDefault(); saveResume(); }
    if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); exportPdf(); }
  });
}

async function boot() {
  ensureEvents();

  if (window.__ppdBootConnected) {
    hideLoading();
    return;
  }
  if (bootStarted) return;
  bootStarted = true;

  setLoadingMessage('Starting PPD engine…');
  showLoading('Starting PPD engine…');

  try {
    for (let i = 0; i < 300; i++) {
      try {
        const api = getApi();
        if (api && typeof api.ping === 'function') {
          const pong = await call('ping');
          if (pong && pong.ok) {
            setLoadingMessage('Loading your workspace…');
            backendReady = true;
            window.__ppdBootConnected = true;
            try {
              await loadInitial();
            } catch (err) {
              toast('Startup error: ' + err.message, true, 8000);
            }
            hideLoading();
            setStatus('Connected — upload your resume PDF to begin');
            bootStarted = false;
            return;
          }
        }
      } catch (_) {}
      if (i === 8) setLoadingMessage('Waiting for Python backend…');
      await sleep(100);
    }
  } finally {
    bootStarted = false;
    hideLoading();
    if (!window.__ppdBootConnected) {
      toast('Backend not connected. Close the app fully and run run-app.bat again.', true, 12000);
      setStatus('Backend offline — buttons will show errors until connected');
    }
  }
}

// ---------------------------------------------------------------------------
// Fullscreen preview
// ---------------------------------------------------------------------------
let isFullscreen = false;

function openFullscreen() {
  const overlay = $('preview-fullscreen');
  const fsPages = $('fs-pages');
  const previewPages = $('preview-pages');
  if (!overlay || !fsPages) return;

  fsPages.innerHTML = '';
  const imgs = previewPages.querySelectorAll('img');
  if (imgs.length) {
    imgs.forEach((img, idx) => {
      const clone = img.cloneNode(true);
      const wrap = document.createElement('div');
      wrap.style.width = '100%';
      wrap.style.display = 'flex';
      wrap.style.flexDirection = 'column';
      wrap.style.alignItems = 'center';
      wrap.appendChild(clone);
      if (imgs.length > 1) {
        const label = document.createElement('div');
        label.className = 'preview-page-label';
        label.textContent = `Page ${idx + 1} of ${imgs.length}`;
        wrap.appendChild(label);
      }
      fsPages.appendChild(wrap);
    });
  } else {
    const msg = document.createElement('p');
    msg.style.color = 'rgba(255,255,255,0.5)';
    msg.style.fontSize = '14px';
    msg.textContent = 'No preview available — upload a resume first.';
    fsPages.appendChild(msg);
  }

  overlay.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
  isFullscreen = true;
}

function closeFullscreen() {
  const overlay = $('preview-fullscreen');
  if (!overlay) return;
  overlay.classList.add('hidden');
  document.body.style.overflow = '';
  isFullscreen = false;
}

function toggleFullscreen() {
  if (isFullscreen) closeFullscreen();
  else openFullscreen();
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && isFullscreen) closeFullscreen();
});

document.addEventListener('click', (e) => {
  if (e.target.id === 'fs-backdrop') closeFullscreen();
});

$('btn-fullscreen').onclick = toggleFullscreen;
$('fs-close').onclick = closeFullscreen;

window.addEventListener('pywebviewready', () => boot());
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => boot());
} else {
  boot();
}
