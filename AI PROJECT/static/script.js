// ===== PARTICLE SYSTEM =====
function createParticles() {
  const container = document.getElementById('particles');
  const colors = ['#6c63ff', '#ff6584', '#43e97b', '#38f9d7', '#ffd700'];
  for (let i = 0; i < 35; i++) {
    const p = document.createElement('div');
    p.className = 'particle';
    p.style.left = Math.random() * 100 + 'vw';
    p.style.animationDuration = (5 + Math.random() * 8) + 's';
    p.style.animationDelay = (Math.random() * 10) + 's';
    p.style.background = colors[Math.floor(Math.random() * colors.length)];
    p.style.width = p.style.height = (2 + Math.random() * 3) + 'px';
    container.appendChild(p);
  }
}

// ===== FILE MANAGEMENT =====
let selectedFiles = [];

const dropZone    = document.getElementById('drop-zone');
const fileInput   = document.getElementById('file-input');
const fileList    = document.getElementById('file-list');

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  addFiles([...e.dataTransfer.files]);
});
fileInput.addEventListener('change', () => {
  addFiles([...fileInput.files]);
  fileInput.value = '';
});

function addFiles(files) {
  const allowed = ['pdf', 'docx', 'txt'];
  files.forEach(f => {
    const ext = f.name.split('.').pop().toLowerCase();
    if (!allowed.includes(ext)) return;
    if (selectedFiles.find(x => x.name === f.name && x.size === f.size)) return;
    selectedFiles.push(f);
  });
  renderFileList();
}

function removeFile(index) {
  selectedFiles.splice(index, 1);
  renderFileList();
}

function renderFileList() {
  fileList.innerHTML = '';
  const icons = { pdf: '📄', docx: '📝', txt: '📃' };
  selectedFiles.forEach((f, i) => {
    const ext = f.name.split('.').pop().toLowerCase();
    const size = f.size < 1024 * 1024
      ? (f.size / 1024).toFixed(1) + ' KB'
      : (f.size / 1024 / 1024).toFixed(1) + ' MB';
    const item = document.createElement('div');
    item.className = 'file-item';
    item.style.animationDelay = (i * 0.06) + 's';
    item.innerHTML = `
      <span class="file-icon">${icons[ext] || '📎'}</span>
      <span class="file-name">${escapeHtml(f.name)}</span>
      <span class="file-size">${size}</span>
      <button class="file-remove" onclick="removeFile(${i})" title="Remove">✕</button>
    `;
    fileList.appendChild(item);
  });
}

// ===== FORM SUBMIT =====
const form     = document.getElementById('rank-form');
const loader   = document.getElementById('loader');
const results  = document.getElementById('results-section');
const errorBox = document.getElementById('error-box');
const warnBox  = document.getElementById('warning-box');

form.addEventListener('submit', async e => {
  e.preventDefault();
  const jd = document.getElementById('job-description').value.trim();

  errorBox.classList.remove('show');
  warnBox.classList.remove('show');

  if (!jd) { showError('Please enter a job description.'); return; }
  if (selectedFiles.length === 0) { showError('Please upload at least one resume.'); return; }

  // Show loader, hide results
  loader.classList.add('active');
  results.style.display = 'none';
  document.getElementById('submit-btn').disabled = true;

  const formData = new FormData();
  formData.append('job_description', jd);
  selectedFiles.forEach(f => formData.append('resumes', f));

  try {
    const res  = await fetch('/rank', { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok) {
      showError(data.error || 'Something went wrong.');
      return;
    }

    if (data.errors && data.errors.length > 0) {
      warnBox.textContent = '⚠️ Some files had issues: ' + data.errors.join(' | ');
      warnBox.classList.add('show');
    }

    renderResults(data.results);
  } catch (err) {
    showError('Network error. Make sure the Flask server is running.');
  } finally {
    loader.classList.remove('active');
    document.getElementById('submit-btn').disabled = false;
  }
});

// ===== RENDER RESULTS =====
function renderResults(data) {
  const section  = document.getElementById('results-section');
  const list     = document.getElementById('results-list');
  const countEl  = document.getElementById('results-count');

  countEl.textContent = data.length + ' Resume' + (data.length !== 1 ? 's' : '') + ' Ranked';
  list.innerHTML = '';

  data.forEach((r, i) => {
    const rankClass = i === 0 ? 'rank-1' : i === 1 ? 'rank-2' : i === 2 ? 'rank-3' : 'rank-other';
    const rankEmoji = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : (i + 1);

    const allSkills = Object.values(r.skills).flat().slice(0, 14);
    const skillsHtml = allSkills.length
      ? allSkills.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join('')
      : '<span style="color:var(--muted);font-size:0.85rem">No recognisable skills found</span>';

    const missingHtml = r.missing_keywords.length
      ? r.missing_keywords.map(k => `<span class="missing-tag">${escapeHtml(k)}</span>`).join('')
      : '<span style="color:var(--accent);font-size:0.82rem">✓ Great keyword coverage!</span>';

    const card = document.createElement('div');
    card.className = `result-card ${rankClass}`;
    card.style.animationDelay = (i * 0.12) + 's';

    card.innerHTML = `
      ${i === 0 ? '<span class="crown">👑</span>' : ''}
      <div class="card-top">
        <div class="card-left">
          <div class="rank-badge">${rankEmoji}</div>
          <div class="card-meta">
            <h3>${escapeHtml(r.filename)}</h3>
            <span class="sub">${r.text_length} words extracted</span>
          </div>
        </div>
        <span class="match-badge badge-${r.badge_color}">${r.badge}</span>
      </div>

      <div class="scores-grid">
        <div class="score-item">
          <label>Composite Score <span>${r.composite_score}%</span></label>
          <div class="score-bar">
            <div class="score-fill composite" data-width="${r.composite_score}"></div>
          </div>
        </div>
        <div class="score-item">
          <label>JD Match Score <span>${r.match_score}%</span></label>
          <div class="score-bar">
            <div class="score-fill match" data-width="${r.match_score}"></div>
          </div>
        </div>
      </div>

      <div class="details-grid">
        <div class="detail-chip">
          <span class="icon">🎓</span>
          <strong>${r.education}</strong>
        </div>
        <div class="detail-chip">
          <span class="icon">💼</span>
          <strong>${r.experience_years > 0 ? r.experience_years + ' yrs exp' : 'Exp not found'}</strong>
        </div>
        <div class="detail-chip">
          <span class="icon">🛠️</span>
          <strong>${r.total_skills} skills matched</strong>
        </div>
        <div class="detail-chip">
          <span class="icon">📊</span>
          <strong>Rank #${r.rank}</strong>
        </div>
      </div>

      <div class="skills-section">
        <div class="skills-title">Matched Skills</div>
        <div class="skills-grid">${skillsHtml}</div>
      </div>

      <div class="missing-section">
        <div class="missing-title">Missing Keywords from JD</div>
        <div class="missing-grid">${missingHtml}</div>
      </div>
    `;
    list.appendChild(card);
  });

  section.style.display = 'block';

  // Animate score bars after render
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      document.querySelectorAll('.score-fill').forEach(el => {
        el.style.width = el.dataset.width + '%';
      });
    });
  });

  // Smooth scroll
  setTimeout(() => section.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
}

// ===== HELPERS =====
function showError(msg) {
  errorBox.textContent = '❌ ' + msg;
  errorBox.classList.add('show');
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ===== INIT =====
createParticles();
