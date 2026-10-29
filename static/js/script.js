/**
 * static/js/script.js
 * Handles: form validation, drag-drop upload, image previews,
 *          AJAX submission, loading animation, result display, toast notifications.
 */

'use strict';

// ─── DOM references ───────────────────────────────────────────
const form          = document.getElementById('videoForm');
const submitBtn     = document.getElementById('submitBtn');
const btnText       = document.getElementById('btnText');
const uploadZone    = document.getElementById('uploadZone');
const imageInput    = document.getElementById('images');
const previewGrid   = document.getElementById('previewGrid');
const loadingOverlay= document.getElementById('loadingOverlay');
const loadingStep   = document.getElementById('loadingStep');
const loadingBar    = document.getElementById('loadingBar');
const resultPanel   = document.getElementById('resultPanel');
const videoPlayer   = document.getElementById('videoPlayer');
const downloadBtn   = document.getElementById('downloadBtn');
const resultMeta    = document.getElementById('resultMeta');
const scriptInfo    = document.getElementById('scriptInfo');
const toastContainer= document.getElementById('toastContainer');
const generateAgainBtn = document.getElementById('generateAnotherBtn');

let selectedFiles = [];

// ─── Loading steps animation ──────────────────────────────────
const LOADING_STEPS = [
  { text: 'Validating property details…',    pct: 10 },
  { text: 'Generating promotional script…', pct: 25 },
  { text: 'Processing uploaded images…',    pct: 40 },
  { text: 'Building video scenes…',         pct: 60 },
  { text: 'Adding text overlays…',          pct: 72 },
  { text: 'Applying transitions…',          pct: 82 },
  { text: 'Encoding MP4 video…',            pct: 93 },
  { text: 'Finalising your video…',         pct: 98 },
];

let stepInterval = null;

function startLoadingAnimation() {
  loadingOverlay.classList.add('active');
  loadingOverlay.setAttribute('aria-hidden', 'false');
  let idx = 0;
  setStep(LOADING_STEPS[0]);
  stepInterval = setInterval(() => {
    idx = Math.min(idx + 1, LOADING_STEPS.length - 1);
    setStep(LOADING_STEPS[idx]);
  }, 2800);
}

function setStep(step) {
  loadingStep.textContent = step.text;
  loadingBar.style.width = step.pct + '%';
}

function stopLoadingAnimation(success) {
  clearInterval(stepInterval);
  loadingBar.style.width = success ? '100%' : '0%';
  setTimeout(() => {
    loadingOverlay.classList.remove('active');
    loadingOverlay.setAttribute('aria-hidden', 'true');
    loadingBar.style.width = '0%';
  }, 500);
}

// ─── Toast notifications ──────────────────────────────────────
function showToast(title, message, type = 'error') {
  const icons = { error: '⚠️', success: '✅' };
  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.innerHTML = `
    <span class="toast__icon">${icons[type] || '💬'}</span>
    <div class="toast__body">
      <div class="toast__title">${escapeHtml(title)}</div>
      ${message ? `<div class="toast__msg">${escapeHtml(message)}</div>` : ''}
    </div>
  `;
  toastContainer.appendChild(toast);
  setTimeout(() => toast.remove(), 6000);
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

// ─── Form field validation ────────────────────────────────────
function validateField(id, errorId, message) {
  const el = document.getElementById(id);
  const errEl = document.getElementById(errorId);
  if (!el) return true;
  const val = el.value.trim();
  if (!val) {
    el.classList.add('is-error');
    if (errEl) errEl.textContent = message;
    return false;
  }
  el.classList.remove('is-error');
  if (errEl) errEl.textContent = '';
  return true;
}

function clearFieldError(id, errorId) {
  const el = document.getElementById(id);
  const errEl = document.getElementById(errorId);
  if (el) el.classList.remove('is-error');
  if (errEl) errEl.textContent = '';
}

function validateForm() {
  let ok = true;
  ok = validateField('property_name', 'err_property_name', 'Property name is required.') && ok;
  ok = validateField('property_type', 'err_property_type', 'Please select a property type.') && ok;
  ok = validateField('location',      'err_location',      'Location is required.') && ok;
  ok = validateField('price',         'err_price',         'Price is required.') && ok;
  ok = validateField('contact',       'err_contact',       'Contact / CTA is required.') && ok;

  // Images
  const imgErr = document.getElementById('err_images');
  if (selectedFiles.length < 4) {
    if (imgErr) imgErr.textContent = `Please upload at least 4 images. (${selectedFiles.length} selected)`;
    ok = false;
  } else if (selectedFiles.length > 8) {
    if (imgErr) imgErr.textContent = `Maximum 8 images allowed. (${selectedFiles.length} selected)`;
    ok = false;
  } else {
    if (imgErr) imgErr.textContent = '';
  }

  return ok;
}

// ─── Image preview ────────────────────────────────────────────
const ALLOWED_TYPES = ['image/jpeg','image/png','image/webp','image/bmp'];
const ALLOWED_EXTS  = ['.jpg','.jpeg','.png','.webp','.bmp'];

function isAllowedImage(file) {
  const ext = file.name.toLowerCase().split('.').pop();
  return ALLOWED_TYPES.includes(file.type) || ALLOWED_EXTS.includes('.' + ext);
}

function buildPreview(files) {
  previewGrid.innerHTML = '';
  files.forEach((file, i) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const thumb = document.createElement('div');
      thumb.className = 'preview-thumb';
      thumb.innerHTML = `
        <img src="${e.target.result}" alt="Preview ${i+1}" />
        <span class="preview-thumb__badge">${i+1}</span>
      `;
      previewGrid.appendChild(thumb);
    };
    reader.readAsDataURL(file);
  });
}

function handleFiles(files) {
  const valid = [];
  const rejected = [];

  Array.from(files).forEach(f => {
    if (!isAllowedImage(f)) {
      rejected.push(f.name);
    } else {
      valid.push(f);
    }
  });

  if (rejected.length) {
    showToast('Unsupported Files Skipped', rejected.join(', '), 'error');
  }

  selectedFiles = valid.slice(0, 8); // cap at 8

  const imgErr = document.getElementById('err_images');
  if (selectedFiles.length > 0) {
    uploadZone.querySelector('.upload-zone__text').innerHTML =
      `<strong>${selectedFiles.length} image${selectedFiles.length > 1 ? 's' : ''} selected</strong>`;
    if (imgErr) imgErr.textContent = '';
    buildPreview(selectedFiles);
  }

  if (selectedFiles.length < 4) {
    if (imgErr) imgErr.textContent = `At least 4 images required. (${selectedFiles.length} selected)`;
  } else if (valid.length > 8) {
    showToast('Too Many Images', 'Only the first 8 images were kept.', 'error');
  }
}

// ─── Drag & drop ──────────────────────────────────────────────
uploadZone.addEventListener('dragover', e => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  handleFiles(e.dataTransfer.files);
});

imageInput.addEventListener('change', () => handleFiles(imageInput.files));

// Allow keyboard activation of upload zone
uploadZone.addEventListener('keydown', e => {
  if (e.key === 'Enter' || e.key === ' ') imageInput.click();
});

// ─── Clear errors on input ────────────────────────────────────
['property_name','property_type','location','price','contact'].forEach(id => {
  const el = document.getElementById(id);
  if (el) el.addEventListener('input', () => clearFieldError(id, `err_${id}`));
});

// ─── Form submit ──────────────────────────────────────────────
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!validateForm()) return;

  // Build FormData
  const fd = new FormData();
  fd.append('property_name',  document.getElementById('property_name').value.trim());
  fd.append('property_type',  document.getElementById('property_type').value.trim());
  fd.append('location',       document.getElementById('location').value.trim());
  fd.append('price',          document.getElementById('price').value.trim());
  fd.append('features',       document.getElementById('features').value.trim());
  fd.append('contact',        document.getElementById('contact').value.trim());
  fd.append('add_voiceover',  document.getElementById('add_voiceover').checked ? 'true' : 'false');

  selectedFiles.forEach(f => fd.append('images', f));

  // UI: loading state
  submitBtn.disabled = true;
  btnText.textContent = 'Generating…';
  resultPanel.style.display = 'none';
  startLoadingAnimation();

  try {
    const res = await fetch('/generate', { method: 'POST', body: fd });
    const data = await res.json();

    stopLoadingAnimation(data.success);

    if (data.success) {
      showResult(data);
      showToast('Video Ready!', data.message || 'Your video has been generated.', 'success');
    } else {
      const msgs = (data.errors || ['Unknown error.']).join('\n');
      showToast('Generation Failed', msgs, 'error');
      // Show field-level errors if known
      if (data.errors) {
        data.errors.forEach(msg => {
          if (msg.includes('images') || msg.includes('Images')) {
            const el = document.getElementById('err_images');
            if (el) el.textContent = msg;
          }
        });
      }
    }
  } catch (err) {
    stopLoadingAnimation(false);
    showToast('Network Error', 'Could not reach the server. Please try again.', 'error');
    console.error('Fetch error:', err);
  } finally {
    submitBtn.disabled = false;
    btnText.textContent = 'Generate Video';
  }
});

// ─── Show result ──────────────────────────────────────────────
function showResult(data) {
  const fname = data.video_filename;
  const previewUrl  = `/preview/${fname}`;
  const downloadUrl = `/download/${fname}`;

  videoPlayer.src = previewUrl;
  videoPlayer.load();
  downloadBtn.href = downloadUrl;
  downloadBtn.download = fname;

  resultMeta.textContent =
    `${data.scene_count} scenes · Script: ${data.script_source === 'gemini' ? '🤖 AI Generated' : '📄 Template'} · Ready to share`;

  scriptInfo.innerHTML = `
    <strong>Script source:</strong> ${data.script_source === 'gemini' ? 'Google Gemini AI' : 'Template-based (no API key)'}<br/>
    <strong>Filename:</strong> ${escapeHtml(fname)}<br/>
    <strong>Format:</strong> MP4, H.264, 1280×720, 24 FPS
  `;

  resultPanel.style.display = 'block';
  resultPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ─── Generate another ─────────────────────────────────────────
generateAgainBtn.addEventListener('click', () => {
  resultPanel.style.display = 'none';
  videoPlayer.pause();
  videoPlayer.src = '';
  form.reset();
  selectedFiles = [];
  previewGrid.innerHTML = '';
  uploadZone.querySelector('.upload-zone__text').innerHTML =
    '<strong>Click to upload</strong> or drag &amp; drop';
  window.scrollTo({ top: 0, behavior: 'smooth' });
});
