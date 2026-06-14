/** Job application tracker — local persistence via Python API */

const JobTracker = (() => {
  const STATUS_LABELS = {
    wishlist: 'Wishlist',
    applied: 'Applied',
    screening: 'Screening',
    interview: 'Interview',
    offer: 'Offer',
    rejected: 'Rejected',
    withdrawn: 'Withdrawn',
  };

  const STATUS_CLASS = {
    wishlist: 'status-wishlist',
    applied: 'status-applied',
    screening: 'status-screening',
    interview: 'status-interview',
    offer: 'status-offer',
    rejected: 'status-rejected',
    withdrawn: 'status-withdrawn',
  };

  let jobs = [];
  let stats = {};
  let templates = [];
  let editingId = null;

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function todayISO() {
    return new Date().toISOString().slice(0, 10);
  }

  function formatDate(iso) {
    if (!iso) return '—';
    try {
      const d = new Date(iso + 'T12:00:00');
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    } catch (_) {
      return iso;
    }
  }

  function isFollowUpDue(job) {
    const fu = job.follow_up_date;
    if (!fu || ['offer', 'rejected', 'withdrawn'].includes(job.status)) return false;
    return fu <= todayISO();
  }

  function filterAndSort(list) {
    const q = ($('jobs-search')?.value || '').trim().toLowerCase();
    const statusFilter = $('jobs-filter-status')?.value || '';
    const sort = $('jobs-sort')?.value || 'updated_desc';

    let out = list.slice();
    if statusFilter) out = out.filter((j) => j.status === statusFilter);
    if (q) {
      out = out.filter((j) => {
        const hay = [
          j.company, j.role, j.location, j.notes, j.source,
          j.contact_name, j.contact_email, j.salary_range,
        ].join(' ').toLowerCase();
        return hay.includes(q);
      });
    }

    out.sort((a, b) => {
      switch (sort) {
        case 'applied_asc':
          return (a.date_applied || '').localeCompare(b.date_applied || '');
        case 'applied_desc':
          return (b.date_applied || '').localeCompare(a.date_applied || '');
        case 'follow_up':
          if (isFollowUpDue(a) !== isFollowUpDue(b)) return isFollowUpDue(b) - isFollowUpDue(a);
          return (a.follow_up_date || '9999').localeCompare(b.follow_up_date || '9999');
        case 'company':
          return (a.company || '').localeCompare(b.company || '', undefined, { sensitivity: 'base' });
        case 'updated_desc':
        default:
          return (b.updated_at || b.date_applied || '').localeCompare(a.updated_at || a.date_applied || '');
      }
    });
    return out;
  }

  function renderStats() {
    const el = $('jobs-stats');
    if (!el) return;
    const s = stats || {};
    el.innerHTML = `
      <div class="jobs-stat"><span class="jobs-stat-num">${s.total || 0}</span><span class="jobs-stat-label">Total</span></div>
      <div class="jobs-stat"><span class="jobs-stat-num">${s.active || 0}</span><span class="jobs-stat-label">Active</span></div>
      <div class="jobs-stat"><span class="jobs-stat-num">${s.interview || 0}</span><span class="jobs-stat-label">Interviews</span></div>
      <div class="jobs-stat jobs-stat-good"><span class="jobs-stat-num">${s.offer || 0}</span><span class="jobs-stat-label">Offers</span></div>
      <div class="jobs-stat ${s.follow_up_due ? 'jobs-stat-warn' : ''}"><span class="jobs-stat-num">${s.follow_up_due || 0}</span><span class="jobs-stat-label">Follow-ups due</span></div>
    `;
  }

  function renderJobCard(job) {
    const statusClass = STATUS_CLASS[job.status] || 'status-applied';
    const followDue = isFollowUpDue(job);
    const priorityDot = job.priority === 'high'
      ? '<span class="job-priority job-priority-high" title="High priority">!</span>'
      : job.priority === 'low'
        ? '<span class="job-priority job-priority-low" title="Low priority">·</span>'
        : '';

    const meta = [
      job.location ? esc(job.location) : '',
      `Applied ${formatDate(job.date_applied)}`,
      job.source ? esc(job.source) : '',
      job.salary_range ? esc(job.salary_range) : '',
    ].filter(Boolean).join(' · ');

    const urlBtn = job.job_url
      ? `<a class="job-link" href="${esc(job.job_url)}" target="_blank" rel="noopener" title="Open posting">↗ Posting</a>`
      : '';

    const contact = job.contact_name || job.contact_email
      ? `<span class="job-contact">${esc(job.contact_name)}${job.contact_name && job.contact_email ? ' · ' : ''}${esc(job.contact_email)}</span>`
      : '';

    const resumeTag = job.resume_template
      ? `<span class="job-tag">📄 ${esc(job.resume_template)}</span>`
      : '';

    const notes = job.notes
      ? `<p class="job-notes-preview">${esc(job.notes.length > 140 ? job.notes.slice(0, 140) + '…' : job.notes)}</p>`
      : '';

    const followBadge = followDue
      ? `<span class="job-follow-badge">Follow up ${job.follow_up_date === todayISO() ? 'today' : 'overdue'}</span>`
      : job.follow_up_date
        ? `<span class="job-follow-muted">Follow-up ${formatDate(job.follow_up_date)}</span>`
        : '';

    const statusOptions = Object.entries(STATUS_LABELS)
      .map(([val, label]) => `<option value="${val}" ${job.status === val ? 'selected' : ''}>${label}</option>`)
      .join('');

    return `
      <article class="job-card ${job.status === 'rejected' || job.status === 'withdrawn' ? 'job-card-muted' : ''}" data-id="${esc(job.id)}">
        <div class="job-card-top">
          <div class="job-card-title">
            ${priorityDot}
            <strong>${esc(job.company)}</strong>
            <span class="job-role">${esc(job.role)}</span>
          </div>
          <div class="job-card-actions">
            <select class="job-status-select ${statusClass}" data-action="status" aria-label="Change status">
              ${statusOptions}
            </select>
            <button type="button" class="job-icon-btn" data-action="edit" title="Edit">✎</button>
            <button type="button" class="job-icon-btn job-icon-danger" data-action="delete" title="Delete">🗑</button>
          </div>
        </div>
        <div class="job-card-meta">${meta || '—'}</div>
        <div class="job-card-tags">
          ${followBadge}
          ${resumeTag}
          ${contact}
          ${urlBtn}
        </div>
        ${notes}
      </article>
    `;
  }

  function renderList() {
    const el = $('jobs-list');
    if (!el) return;
    const visible = filterAndSort(jobs);
    if (!visible.length) {
      const emptyMsg = jobs.length
        ? 'No applications match your filters.'
        : 'No applications yet — add your first one to start tracking.';
      el.innerHTML = `<div class="jobs-empty">${emptyMsg}</div>`;
      return;
    }
    el.innerHTML = visible.map(renderJobCard).join('');
  }

  function render() {
    renderStats();
    renderList();
  }

  async function apiCall(method, ...args) {
    if (typeof window.call === 'function') return window.call(method, ...args);
    const api = window.pywebview && window.pywebview.api;
    if (!api || typeof api[method] !== 'function') throw new Error('Backend not ready');
    const result = api[method](...args);
    return result && typeof result.then === 'function' ? await result : result;
  }

  async function loadTemplates() {
    try {
      const r = await apiCall('get_templates');
      templates = (r.ok && r.templates) ? r.templates : [];
    } catch (_) {
      templates = [];
    }
    const sel = $('job-resume-template');
    if (!sel) return;
    const current = sel.value;
    sel.innerHTML = '<option value="">Current default</option>'
      + templates.map((t) => {
        const label = t.name || t.label || t.id;
        return `<option value="${esc(label)}">${esc(label)}</option>`;
      }).join('');
    if (current) sel.value = current;
  }

  async function load() {
    try {
      const r = await apiCall('get_jobs');
      jobs = r.jobs || [];
      stats = r.stats || {};
      render();
    } catch (e) {
      if (typeof window.toast === 'function') window.toast(e.message, true);
    }
  }

  function resetForm() {
    editingId = null;
    $('job-id').value = '';
    $('job-form').reset();
    $('job-date-applied').value = todayISO();
    $('job-priority').value = 'medium';
    $('job-status').value = 'applied';
    $('job-modal-title').textContent = 'Add Application';
    $('job-delete-btn').classList.add('hidden');
  }

  function fillForm(job) {
    editingId = job.id;
    $('job-id').value = job.id;
    $('job-company').value = job.company || '';
    $('job-role').value = job.role || '';
    $('job-status').value = job.status || 'applied';
    $('job-priority').value = job.priority || 'medium';
    $('job-date-applied').value = job.date_applied || todayISO();
    $('job-follow-up').value = job.follow_up_date || '';
    $('job-location').value = job.location || '';
    $('job-url').value = job.job_url || '';
    $('job-salary').value = job.salary_range || '';
    $('job-source').value = job.source || '';
    $('job-contact-name').value = job.contact_name || '';
    $('job-contact-email').value = job.contact_email || '';
    $('job-resume-template').value = job.resume_template || '';
    $('job-notes').value = job.notes || '';
    $('job-modal-title').textContent = 'Edit Application';
    $('job-delete-btn').classList.remove('hidden');
  }

  function readForm() {
    return {
      id: $('job-id').value || undefined,
      company: $('job-company').value.trim(),
      role: $('job-role').value.trim(),
      status: $('job-status').value,
      priority: $('job-priority').value,
      date_applied: $('job-date-applied').value || todayISO(),
      follow_up_date: $('job-follow-up').value || '',
      location: $('job-location').value.trim(),
      job_url: $('job-url').value.trim(),
      salary_range: $('job-salary').value.trim(),
      source: $('job-source').value,
      contact_name: $('job-contact-name').value.trim(),
      contact_email: $('job-contact-email').value.trim(),
      resume_template: $('job-resume-template').value,
      notes: $('job-notes').value.trim(),
    };
  }

  function openModal(job) {
    resetForm();
    if (job) fillForm(job);
    $('job-modal').classList.remove('hidden');
    $('job-company').focus();
  }

  function closeModal() {
    $('job-modal').classList.add('hidden');
    resetForm();
  }

  async function saveForm(e) {
    e.preventDefault();
    const payload = readForm();
    if (!payload.company || !payload.role) {
      if (typeof window.toast === 'function') window.toast('Company and role are required', true);
      return;
    }
    try {
      const r = editingId
        ? await apiCall('update_job', editingId, payload)
        : await apiCall('add_job', payload);
      if (!r.ok) {
        if (typeof window.toast === 'function') window.toast(r.message || 'Save failed', true);
        return;
      }
      jobs = r.jobs || jobs;
      stats = r.stats || stats;
      closeModal();
      render();
      if (typeof window.toast === 'function') window.toast(editingId ? 'Application updated' : 'Application added');
    } catch (err) {
      if (typeof window.toast === 'function') window.toast(err.message, true);
    }
  }

  async function deleteJob(id) {
    if (!confirm('Delete this application?')) return;
    try {
      const r = await apiCall('delete_job', id);
      if (!r.ok) {
        if (typeof window.toast === 'function') window.toast(r.message || 'Delete failed', true);
        return;
      }
      jobs = r.jobs || [];
      stats = r.stats || stats;
      closeModal();
      render();
      if (typeof window.toast === 'function') window.toast('Application deleted');
    } catch (err) {
      if (typeof window.toast === 'function') window.toast(err.message, true);
    }
  }

  async function updateStatus(id, status) {
    try {
      const r = await apiCall('update_job', id, { status });
      if (!r.ok) return;
      jobs = r.jobs || jobs;
      stats = r.stats || stats;
      render();
    } catch (_) {}
  }

  function onListClick(e) {
    const card = e.target.closest('.job-card');
    if (!card) return;
    const id = card.dataset.id;
    const job = jobs.find((j) => j.id === id);
    if (!job) return;

    const actionEl = e.target.closest('[data-action]');
    if (!actionEl) return;

    const action = actionEl.dataset.action;
    if (action === 'edit') {
      openModal(job);
      return;
    }
    if (action === 'delete') {
      deleteJob(id);
      return;
    }
    if (action === 'status' && actionEl.tagName === 'SELECT') {
      updateStatus(id, actionEl.value);
    }
  }

  function init() {
    $('btn-add-job-open')?.addEventListener('click', () => openModal(null));
    $('job-modal-close')?.addEventListener('click', closeModal);
    $('job-modal-backdrop')?.addEventListener('click', closeModal);
    $('job-cancel-btn')?.addEventListener('click', closeModal);
    $('job-form')?.addEventListener('submit', saveForm);
    $('job-delete-btn')?.addEventListener('click', () => {
      if (editingId) deleteJob(editingId);
    });
    $('jobs-list')?.addEventListener('click', onListClick);
    $('jobs-list')?.addEventListener('change', onListClick);
    $('jobs-search')?.addEventListener('input', renderList);
    $('jobs-filter-status')?.addEventListener('change', renderList);
    $('jobs-sort')?.addEventListener('change', renderList);

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !$('job-modal')?.classList.contains('hidden')) closeModal();
    });
  }

  async function onViewOpen() {
    await loadTemplates();
    await load();
  }

  return { init, onViewOpen, load };
})();

window.JobTracker = JobTracker;
