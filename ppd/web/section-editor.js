/** Section-based resume editor — structured v2 schema */

const SectionEditor = (() => {
  let resume = defaultResume();
  let visibleSections = [];
  let visibleSkillCategories = [];
  let onChangeCallback = null;
  let previewTimer = null;

  function defaultResume() {
    return {
      personal: {
        name: 'Your Name', title: '', location: '', phone: '', email: '',
        github: '', linkedin: '', portfolio: '',
      },
      summary: { text: '' },
      experience: [],
      projects: [],
      skills: { frontend: [], backend: [], database: [], cloud_tools: [], other: [] },
      education: [],
      certifications: [],
      custom_sections: [],
    };
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function el(tag, cls, html) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }

  function field(label, id, value, type = 'text') {
    return `<label class="sec-field"><span>${esc(label)}</span>
      <input type="${type}" data-field="${esc(id)}" value="${esc(value || '')}"/></label>`;
  }

  function textareaField(label, id, value) {
    return `<label class="sec-field"><span>${esc(label)}</span>
      <textarea data-field="${esc(id)}" rows="4">${esc(value || '')}</textarea></label>`;
  }

  function bulletsField(label, items) {
    const text = (items || []).join('\n');
    return `<label class="sec-field"><span>${esc(label)}</span>
      <textarea data-bullets rows="5" placeholder="One bullet per line">${esc(text)}</textarea></label>`;
  }

  function listToBullets(text) {
    return text.split('\n').map((l) => l.replace(/^[\s•\-*]+/, '').trim()).filter(Boolean);
  }

  function skillsToText(arr) {
    return (arr || []).join(', ');
  }

  function textToSkills(text) {
    return text.split(/[,;\n/·|]+/).map((s) => s.trim()).filter(Boolean);
  }

  function sectionCard(title, bodyHtml, open = true) {
    const card = el('details', 'sec-card');
    card.open = open;
    card.innerHTML = `<summary class="sec-head"><span>${esc(title)}</span><span class="sec-badge">SAVED</span></summary>
      <div class="sec-body">${bodyHtml}</div>`;
    return card;
  }

  function bindFields(container, obj, prefix = '') {
    container.querySelectorAll('[data-field]').forEach((inp) => {
      const key = inp.dataset.field;
      inp.addEventListener('input', () => {
        const parts = key.split('.');
        let target = obj;
        for (let i = 0; i < parts.length - 1; i++) target = target[parts[i]];
        target[parts[parts.length - 1]] = inp.value;
        markUnsaved(container.closest('.sec-card'));
        scheduleChange();
      });
    });
    container.querySelectorAll('[data-bullets]').forEach((ta) => {
      ta.addEventListener('input', () => {
        const holder = ta.closest('[data-bullets-target]');
        if (holder) {
          const idx = Number(holder.dataset.idx);
          const section = holder.dataset.section;
          if (section === 'experience') resume.experience[idx].bullets = listToBullets(ta.value);
          else if (section === 'projects') resume.projects[idx].bullets = listToBullets(ta.value);
        } else if (ta.dataset.skillsKey) {
          resume.skills[ta.dataset.skillsKey] = textToSkills(ta.value);
        } else if (ta.dataset.cert) {
          resume.certifications = listToBullets(ta.value);
        }
        markUnsaved(container.closest('.sec-card'));
        scheduleChange();
      });
    });
  }

  function markUnsaved(card) {
    if (!card) return;
    const badge = card.querySelector('.sec-badge');
    if (badge) { badge.textContent = 'UNSAVED'; badge.className = 'sec-badge unsaved'; }
    const sync = document.getElementById('sync-badge');
    if (sync) { sync.textContent = 'UNSAVED'; sync.className = 'badge-unsaved'; }
  }

  function markSaved(card) {
    if (!card) return;
    const badge = card.querySelector('.sec-badge');
    if (badge) { badge.textContent = 'SAVED'; badge.className = 'sec-badge'; }
  }

  function scheduleChange() {
    clearTimeout(previewTimer);
    previewTimer = setTimeout(() => {
      if (onChangeCallback) onChangeCallback(getDocument());
    }, 800);
  }

  function renderPersonal() {
    const p = resume.personal;
    const fieldDefs = [
      ['Full Name', 'name', 'text'],
      ['Professional Title', 'title', 'text'],
      ['Location', 'location', 'text'],
      ['Phone', 'phone', 'text'],
      ['Email', 'email', 'email'],
      ['GitHub', 'github', 'text'],
      ['LinkedIn', 'linkedin', 'text'],
      ['Portfolio', 'portfolio', 'text'],
    ];
    const body = fieldDefs
      .filter(([, key], idx) => idx === 0 || Boolean(p[key]))
      .map(([label, id, type]) => field(label, id, p[id], type))
      .join('');
    const card = sectionCard('Personal Information', body, true);
    bindFields(card, resume.personal);
    return card;
  }

  function renderSummary() {
    const card = sectionCard('Professional Summary', textareaField('Summary', 'text', resume.summary.text));
    bindFields(card, resume.summary);
    return card;
  }

  function renderExperience() {
    const wrap = el('div');
    resume.experience.forEach((job, i) => {
      const block = el('div', 'sec-sub');
      block.innerHTML = `<div class="sec-sub-head">Experience ${i + 1}
        <button type="button" class="sec-del" data-del-exp="${i}">Remove</button></div>
        ${field('Job Title', 'title', job.title)}
        ${field('Company', 'company', job.company)}
        ${field('Location', 'location', job.location)}
        ${field('Employment Type', 'employment_type', job.employment_type)}
        ${field('Start Date', 'start_date', job.start_date)}
        ${field('End Date', 'end_date', job.end_date)}
        <div data-bullets-target data-section="experience" data-idx="${i}">
          ${bulletsField('Bullet Points', job.bullets)}</div>`;
      block.querySelectorAll('[data-field]').forEach((inp) => {
        inp.addEventListener('input', () => {
          resume.experience[i][inp.dataset.field] = inp.value;
          markUnsaved(wrap.closest('.sec-card'));
          scheduleChange();
        });
      });
      bindFields(block, job);
      block.querySelector(`[data-del-exp="${i}"]`).onclick = () => {
        resume.experience.splice(i, 1);
        rerender();
        scheduleChange();
      };
      wrap.appendChild(block);
    });
    const addBtn = el('button', 'sec-add', '+ Add Work Experience');
    addBtn.type = 'button';
    addBtn.onclick = () => {
      resume.experience.push({
        title: '', company: '', location: '', employment_type: '',
        start_date: '', end_date: 'present', bullets: [],
      });
      rerender();
      scheduleChange();
    };
    wrap.appendChild(addBtn);
    const card = sectionCard('Work Experience', '');
    card.querySelector('.sec-body').appendChild(wrap);
    return card;
  }

  function renderProjects() {
    const wrap = el('div');
    resume.projects.forEach((proj, i) => {
      const block = el('div', 'sec-sub');
      block.innerHTML = `<div class="sec-sub-head">Project ${i + 1}
        <button type="button" class="sec-del" data-del-proj="${i}">Remove</button></div>
        ${field('Project Name', 'name', proj.name)}
        ${field('Technologies (comma-separated)', 'technologies', skillsToText(proj.technologies))}
        ${textareaField('Description', 'description', proj.description)}
        <div data-bullets-target data-section="projects" data-idx="${i}">
          ${bulletsField('Bullet Points', proj.bullets)}</div>`;
      block.querySelectorAll('[data-field]').forEach((inp) => {
        inp.addEventListener('input', () => {
          if (inp.dataset.field === 'technologies') {
            resume.projects[i].technologies = textToSkills(inp.value);
          } else {
            resume.projects[i][inp.dataset.field] = inp.value;
          }
          markUnsaved(wrap.closest('.sec-card'));
          scheduleChange();
        });
      });
      bindFields(block, proj);
      block.querySelector(`[data-del-proj="${i}"]`).onclick = () => {
        resume.projects.splice(i, 1);
        rerender();
        scheduleChange();
      };
      wrap.appendChild(block);
    });
    const addBtn = el('button', 'sec-add', '+ Add Project');
    addBtn.type = 'button';
    addBtn.onclick = () => {
      resume.projects.push({ name: '', technologies: [], description: '', bullets: [] });
      rerender();
      scheduleChange();
    };
    wrap.appendChild(addBtn);
    const card = sectionCard('Projects', '');
    card.querySelector('.sec-body').appendChild(wrap);
    return card;
  }

  function renderSkills() {
    const sk = resume.skills;
    const keys = visibleSkillCategories.length
      ? visibleSkillCategories
      : ['frontend', 'backend', 'database', 'cloud_tools', 'other'].filter((k) => (sk[k] || []).length);
    if (!keys.length) return null;
    const body = keys.map((key) => {
      const label = key === 'cloud_tools' ? 'Cloud & Tools' : key.charAt(0).toUpperCase() + key.slice(1);
      return `<label class="sec-field"><span>${label}</span>
        <textarea data-skills-key="${key}" rows="2" placeholder="Comma-separated">${esc(skillsToText(sk[key]))}</textarea></label>`;
    }).join('');
    const card = sectionCard('Skills', body);
    bindFields(card, sk);
    return card;
  }

  function renderEducation() {
    const wrap = el('div');
    resume.education.forEach((edu, i) => {
      const block = el('div', 'sec-sub');
      block.innerHTML = `<div class="sec-sub-head">Education ${i + 1}
        <button type="button" class="sec-del" data-del-edu="${i}">Remove</button></div>
        ${field('Degree', 'degree', edu.degree)}
        ${field('Field', 'field', edu.field)}
        ${field('Institution', 'institution', edu.institution)}
        ${field('Location', 'location', edu.location)}
        ${field('Graduation', 'graduation', edu.graduation)}
        ${field('GPA', 'gpa', edu.gpa)}`;
      block.querySelectorAll('[data-field]').forEach((inp) => {
        inp.addEventListener('input', () => {
          resume.education[i][inp.dataset.field] = inp.value;
          markUnsaved(wrap.closest('.sec-card'));
          scheduleChange();
        });
      });
      block.querySelector(`[data-del-edu="${i}"]`).onclick = () => {
        resume.education.splice(i, 1);
        rerender();
        scheduleChange();
      };
      wrap.appendChild(block);
    });
    const addBtn = el('button', 'sec-add', '+ Add Education');
    addBtn.type = 'button';
    addBtn.onclick = () => {
      resume.education.push({ degree: '', field: '', institution: '', location: '', graduation: '', gpa: '' });
      rerender();
      scheduleChange();
    };
    wrap.appendChild(addBtn);
    const card = sectionCard('Education', '');
    card.querySelector('.sec-body').appendChild(wrap);
    return card;
  }

  function renderCertifications() {
    const body = `<label class="sec-field"><span>Certifications (one per line)</span>
      <textarea data-cert rows="4">${esc((resume.certifications || []).join('\n'))}</textarea></label>`;
    const card = sectionCard('Certifications', body);
    bindFields(card, resume);
    return card;
  }

  function renderCustomSections() {
    const wrap = el('div');
    resume.custom_sections.forEach((sec, i) => {
      const block = el('div', 'sec-sub');
      block.innerHTML = `<div class="sec-sub-head">${esc(sec.title || `Section ${i + 1}`)}
        <button type="button" class="sec-del" data-del-custom="${i}">Remove</button></div>
        ${field('Section Title', 'title', sec.title)}
        <label class="sec-field"><span>Items (one per line)</span>
          <textarea data-custom-items="${i}" rows="4">${esc((sec.items || []).join('\n'))}</textarea></label>`;
      block.querySelector('[data-field]').addEventListener('input', (e) => {
        resume.custom_sections[i].title = e.target.value;
        markUnsaved(wrap.closest('.sec-card'));
        scheduleChange();
      });
      block.querySelector(`[data-custom-items="${i}"]`).addEventListener('input', (e) => {
        resume.custom_sections[i].items = listToBullets(e.target.value);
        markUnsaved(wrap.closest('.sec-card'));
        scheduleChange();
      });
      block.querySelector(`[data-del-custom="${i}"]`).onclick = () => {
        resume.custom_sections.splice(i, 1);
        rerender();
        scheduleChange();
      };
      wrap.appendChild(block);
    });
    const addBtn = el('button', 'sec-add', '+ Add Custom Section');
    addBtn.type = 'button';
    addBtn.onclick = () => {
      resume.custom_sections.push({ title: 'Awards', items: [] });
      rerender();
      scheduleChange();
    };
    wrap.appendChild(addBtn);
    const card = sectionCard('Custom Sections', '');
    card.querySelector('.sec-body').appendChild(wrap);
    return card;
  }

  function rerender() {
    const root = document.getElementById('section-editor');
    if (!root) return;
    root.innerHTML = '';

    if (!visibleSections.length) {
      root.innerHTML = '<div class="sec-empty"><p>Upload a resume PDF to load sections from your document.</p></div>';
      return;
    }

    const builders = {
      personal: renderPersonal,
      summary: renderSummary,
      experience: renderExperience,
      projects: renderProjects,
      skills: renderSkills,
      education: renderEducation,
      certifications: renderCertifications,
      custom_sections: renderCustomSections,
    };

    visibleSections.forEach((key) => {
      const build = builders[key];
      if (!build) return;
      const card = build();
      if (card) root.appendChild(card);
    });
  }

  function loadFromStructured(data) {
    if (!data || !data.resume) {
      resume = defaultResume();
      visibleSections = [];
      visibleSkillCategories = [];
    } else {
      resume = { ...defaultResume(), ...data.resume };
      resume.personal = { ...defaultResume().personal, ...(data.resume.personal || {}) };
      resume.summary = { text: '', ...(data.resume.summary || {}) };
      resume.skills = { ...defaultResume().skills, ...(data.resume.skills || {}) };
      resume.experience = (data.resume.experience || []).map((e) => ({ ...e }));
      resume.projects = (data.resume.projects || []).map((p) => ({ ...p }));
      resume.education = (data.resume.education || []).map((e) => ({ ...e }));
      resume.certifications = [...(data.resume.certifications || [])];
      resume.custom_sections = (data.resume.custom_sections || []).map((s) => ({ ...s }));
      visibleSections = [...(data.resume.visible_sections || [])];
      visibleSkillCategories = [...(data.resume.visible_skill_categories || [])];
    }
    rerender();
  }

  function clear() {
    loadFromStructured(null);
  }

  function getDocument() {
    const doc = JSON.parse(JSON.stringify(resume));
    doc.visible_sections = visibleSections;
    doc.visible_skill_categories = visibleSkillCategories;
    return { resume: doc };
  }

  function setOnChange(fn) {
    onChangeCallback = fn;
  }

  function markAllSaved() {
    document.querySelectorAll('.sec-badge').forEach((b) => {
      b.textContent = 'SAVED';
      b.className = 'sec-badge';
    });
  }

  return { loadFromStructured, getDocument, setOnChange, rerender, markAllSaved, defaultResume, clear };
})();

window.SectionEditor = SectionEditor;
