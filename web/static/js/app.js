// Shared client for every Santa page: fetch helper, theme, auth-on-demand
// modal, toasts, guest preferences, and the job card used by Home and Saved.
// Pages are guest-first: anything that needs an account calls
// `requireAccount()` at the moment of the action instead of redirecting.

const SANTA = window.SANTA || { auth: false, name: '', email: '' };

// ---------------------------------------------------------------- icons
const ICON = {
  bookmark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12v18l-6-4-6 4z"/></svg>',
  share: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.6 13.5 6.8 4M15.4 6.5l-6.8 4"/></svg>',
  arrow: '<svg class="arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
  gem: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 3h12l4 6-10 12L2 9z" opacity=".9"/></svg>',
  calendar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M8 3v4M16 3v4M3 10h18"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>',
  more: '<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg>',
  external: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17 17 7M8 7h9v9"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 5 5L20 7"/></svg>',
  circle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="8"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  alert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg>',
  sparkle: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8zM19 15l.9 2.6L22.5 18.5l-2.6.9L19 22l-.9-2.6-2.6-.9 2.6-.9z"/></svg>',
  chevron: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>',
  lock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>',
  close: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>',
};

// ---------------------------------------------------------------- fetch
async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    ...options,
  });
  if (response.status === 401) {
    // Session expired mid-visit: flip back to guest mode rather than bouncing
    // the visitor to a login page.
    SANTA.auth = false;
    return { ok: false, status: 401, data: null };
  }
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  return { ok: response.ok, status: response.status, data };
}

function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// ---------------------------------------------------------------- storage
function store(key, value) {
  try {
    if (value === undefined) return JSON.parse(localStorage.getItem(key) || 'null');
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(value));
  } catch (error) { /* private mode — run without persistence */ }
  return null;
}

// ---------------------------------------------------------------- theme
(function initTheme() {
  const root = document.documentElement;
  document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
    const sync = () => button.setAttribute('aria-label', root.dataset.theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme');
    sync();
    button.addEventListener('click', () => {
      const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
      root.dataset.theme = next;
      try { localStorage.setItem('santa-theme', next); } catch (error) { /* ignore */ }
      document.querySelectorAll('[data-theme-toggle]').forEach((b) => b.setAttribute('aria-label', next === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'));
    });
  });
})();

// ---------------------------------------------------------------- reveal
const revealObserver = 'IntersectionObserver' in window
  ? new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-in');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { rootMargin: '0px 0px -40px 0px' })
  : null;

function reveal(root = document) {
  root.querySelectorAll('.reveal:not(.is-in)').forEach((el, index) => {
    if (!el.style.getPropertyValue('--i')) el.style.setProperty('--i', String(index % 8));
    if (revealObserver) revealObserver.observe(el);
    else el.classList.add('is-in');
  });
}
document.addEventListener('DOMContentLoaded', () => reveal());

const siteHeader = document.querySelector('.site-header');
if (siteHeader) {
  const onScroll = () => siteHeader.classList.toggle('is-scrolled', window.scrollY > 8);
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

// ---------------------------------------------------------------- toast
function toast(message, action) {
  let host = document.querySelector('.toasts');
  if (!host) {
    host = document.createElement('div');
    host.className = 'toasts';
    host.setAttribute('role', 'status');
    host.setAttribute('aria-live', 'polite');
    document.body.appendChild(host);
  }
  const el = document.createElement('div');
  el.className = 'toast';
  el.innerHTML = `<span>${escapeHTML(message)}</span>`;
  const dismiss = () => {
    el.classList.add('is-leaving');
    setTimeout(() => el.remove(), 260);
  };
  if (action) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = action.label;
    button.addEventListener('click', () => { dismiss(); action.run(); });
    el.appendChild(button);
  }
  host.appendChild(el);
  setTimeout(dismiss, action ? 7000 : 3200);
}

// ---------------------------------------------------------------- guest prefs
// A guest's onboarding choices live in localStorage and filter the public
// feed client-side; they're pushed to the account the moment one is created.
const LOCAL_PREFS_KEY = 'santa-guest-prefs';

function emptyPrefs() {
  return { name: '', skills: [], locations: [], work_modes: [], listing_types: [], minimum_stipend: null, github_username: '', channels: [] };
}

function localPrefs() {
  return { ...emptyPrefs(), ...(store(LOCAL_PREFS_KEY) || {}) };
}

function saveLocalPrefs(prefs) {
  store(LOCAL_PREFS_KEY, { ...localPrefs(), ...prefs });
}

async function loadPrefs() {
  if (!SANTA.auth) return localPrefs();
  const result = await fetchJSON('/preferences');
  if (!result.ok) return localPrefs();
  return { ...emptyPrefs(), ...result.data };
}

function hasPrefs(prefs) {
  return Boolean(prefs && ['skills', 'locations', 'work_modes', 'listing_types'].some((k) => (prefs[k] || []).length) || (prefs && prefs.minimum_stipend));
}

async function pushLocalPrefsToAccount() {
  const local = localPrefs();
  const body = {};
  if (local.name) body.name = local.name;
  if (local.skills.length) body.skills = local.skills;
  if (local.locations.length) body.locations = local.locations;
  if (local.work_modes.length) body.work_modes = local.work_modes;
  if (local.listing_types.length) body.listing_types = local.listing_types;
  if (local.minimum_stipend) body.minimum_stipend = local.minimum_stipend;
  if (local.github_username) body.github_username = local.github_username;
  if (local.channels.length) body.channels = local.channels;
  if (Object.keys(body).length) await fetchJSON('/preferences', { method: 'PUT', body: JSON.stringify(body) });
}

// ---------------------------------------------------------------- auth modal
// Resolves true once the visitor is signed in (immediately if already), false
// if they close it. Callers then carry on with the action that needed it.
function requireAccount(reason) {
  if (SANTA.auth) return Promise.resolve(true);
  return new Promise((resolve) => openAuthModal(reason, resolve));
}

function openAuthModal(reason, done) {
  const overlay = document.createElement('div');
  overlay.className = 'overlay';
  overlay.innerHTML = `
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="auth-title">
      <button type="button" class="icon-btn modal-close" aria-label="Close">${ICON.close}</button>
      <img class="mascot mascot-float" src="/static/assets/santa-mascot.svg" alt="">
      <h2 id="auth-title">Let's keep this safe for you</h2>
      <p class="lead">${escapeHTML(reason || 'Create a free account so Santa can remember this for you.')}</p>
      <div class="seg" role="tablist">
        <button type="button" class="is-on" data-mode="signup">Create account</button>
        <button type="button" data-mode="login">Log in</button>
      </div>
      <form class="form" novalidate>
        <label class="field" data-only="signup">Your name <span class="field-hint">so Santa knows what to call you — optional</span>
          <input class="input" name="name" autocomplete="given-name" placeholder="Aarav">
        </label>
        <label class="field">Email
          <input class="input" type="email" name="email" required autocomplete="email" placeholder="you@college.edu">
        </label>
        <label class="field">Password
          <input class="input" type="password" name="password" required minlength="8" autocomplete="new-password" placeholder="At least 8 characters">
        </label>
        <p class="form-error" hidden></p>
        <button type="submit" class="btn btn-primary btn-block">Create account &amp; continue</button>
        <button type="button" class="btn btn-ghost btn-block" data-skip>Not now</button>
      </form>
    </div>`;
  document.body.appendChild(overlay);
  document.body.style.overflow = 'hidden';
  const form = overlay.querySelector('form');
  const errorEl = overlay.querySelector('.form-error');
  const submit = form.querySelector('[type=submit]');
  let mode = 'signup';

  const close = (result) => {
    document.body.style.overflow = '';
    overlay.remove();
    document.removeEventListener('keydown', onKey);
    done(result);
  };
  const onKey = (event) => { if (event.key === 'Escape') close(false); };
  document.addEventListener('keydown', onKey);
  overlay.addEventListener('click', (event) => { if (event.target === overlay) close(false); });
  overlay.querySelector('.modal-close').addEventListener('click', () => close(false));
  overlay.querySelector('[data-skip]').addEventListener('click', () => close(false));

  overlay.querySelectorAll('[data-mode]').forEach((button) => {
    button.addEventListener('click', () => {
      mode = button.dataset.mode;
      overlay.querySelectorAll('[data-mode]').forEach((b) => b.classList.toggle('is-on', b === button));
      overlay.querySelector('[data-only=signup]').hidden = mode !== 'signup';
      form.password.autocomplete = mode === 'signup' ? 'new-password' : 'current-password';
      submit.textContent = mode === 'signup' ? 'Create account & continue' : 'Log in & continue';
      errorEl.hidden = true;
    });
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    errorEl.hidden = true;
    submit.disabled = true;
    const ok = await authenticate(mode, form.email.value, form.password.value, form.name.value);
    submit.disabled = false;
    if (ok === true) {
      close(true);
      toast(mode === 'signup' ? 'Welcome aboard — Santa has your back now.' : `Welcome back${SANTA.name ? ', ' + SANTA.name : ''}!`);
      return;
    }
    errorEl.textContent = ok;
    errorEl.hidden = false;
  });
  setTimeout(() => form.querySelector(mode === 'signup' ? '[name=name]' : '[name=email]').focus(), 50);
}

// Returns true on success, or an error message string.
async function authenticate(mode, email, password, name) {
  const body = { email, password };
  if (mode === 'signup') body.name = name || localPrefs().name || '';
  const result = await fetchJSON(mode === 'signup' ? '/auth/signup' : '/auth/login', { method: 'POST', body: JSON.stringify(body) });
  if (!result.ok) return (result.data && result.data.error) || 'Something went wrong — try again.';
  SANTA.auth = true;
  SANTA.name = result.data.name || '';
  SANTA.email = result.data.email;
  if (mode === 'signup') await pushLocalPrefsToAccount();
  updateShellUser();
  window.dispatchEvent(new CustomEvent('santa:auth'));
  return true;
}

function updateShellUser() {
  document.querySelectorAll('[data-user-name]').forEach((el) => { el.textContent = SANTA.auth ? (SANTA.name || 'You') : 'Guest'; });
  document.querySelectorAll('[data-user-sub]').forEach((el) => { el.textContent = SANTA.auth ? SANTA.email : 'Browsing freely'; });
  document.querySelectorAll('[data-user-initial]').forEach((el) => { el.textContent = initialOf(SANTA.auth ? (SANTA.name || SANTA.email) : 'G'); });
  document.querySelectorAll('[data-auth-only]').forEach((el) => { el.hidden = !SANTA.auth; });
  document.querySelectorAll('[data-guest-only]').forEach((el) => { el.hidden = SANTA.auth; });
}

document.querySelectorAll('[data-signin]').forEach((button) => {
  button.addEventListener('click', () => requireAccount('Log in or create an account — your saved jobs and alerts follow you everywhere.'));
});
document.querySelectorAll('[data-logout]').forEach((button) => {
  button.addEventListener('click', async () => {
    await fetch('/auth/logout', { method: 'POST' });
    window.location.href = '/';
  });
});

// ---------------------------------------------------------------- job helpers
const STATUS_META = {
  saved: { label: 'Saved', color: '#8a85a8' },
  applied: { label: 'Applied', color: '#6d5bd0' },
  interviewing: { label: 'Interviewing', color: '#d68714' },
  offer: { label: 'Offer', color: '#16865c' },
  rejected: { label: 'Not this time', color: '#d23c44' },
  withdrawn: { label: 'Withdrawn', color: '#8a85a8' },
};
const YEAR_LABELS = { '1st': '1st year', '2nd': '2nd year', '3rd': '3rd year', final: 'Final year' };
const PAY_LABELS = { per_hour: 'Per hour', per_task: 'Per task' };

function initialOf(text) {
  return (String(text || '?').trim()[0] || '?').toUpperCase();
}

// Deterministic per-company gradient so the same company always looks the same.
function avatarStyle(company) {
  let hash = 0;
  for (const ch of String(company)) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  const h1 = hash % 360;
  const h2 = (h1 + 40) % 360;
  return `--a1:hsl(${h1} 72% 52%);--a2:hsl(${h2} 78% 58%)`;
}

function logoTile(company, size = '') {
  return `<span class="logo-tile ${size}" style="${avatarStyle(company)}" aria-hidden="true"><span>${escapeHTML(initialOf(company))}</span></span>`;
}

function jobTags(job) {
  const tags = [];
  if (job.listing_type) tags.push(['accent', job.listing_type === 'internship' ? 'Internship' : 'Job']);
  if (job.work_mode) tags.push(['', job.work_mode[0].toUpperCase() + job.work_mode.slice(1)]);
  if (job.duration_months) tags.push(['', `${job.duration_months} month${job.duration_months === 1 ? '' : 's'}`]);
  if (job.target_year && job.target_year !== 'any') tags.push(['', YEAR_LABELS[job.target_year] || job.target_year]);
  if (job.pay_type && PAY_LABELS[job.pay_type]) tags.push(['', PAY_LABELS[job.pay_type]]);
  return tags;
}

function payText(job) {
  if (job.salary_raw) return job.salary_raw;
  if (job.salary_numeric) return `₹${job.salary_numeric.toLocaleString('en-IN')} / month`;
  return '';
}

function deadlineInfo(deadlineAt) {
  if (!deadlineAt) return null;
  const ms = new Date(deadlineAt) - Date.now();
  if (ms <= 0) return null;
  const days = Math.floor(ms / 86400000);
  const hours = Math.floor((ms % 86400000) / 3600000);
  return { days, hours, urgent: days < 3, text: days > 0 ? `${days}d ${hours}h left` : `${hours}h left` };
}

function timeAgo(iso) {
  if (!iso) return '';
  const days = Math.floor((Date.now() - new Date(iso)) / 86400000);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return `${days} days ago`;
  return `${Math.floor(days / 30)} mo ago`;
}

const norm = (s) => String(s).trim().toLowerCase();

// Display names for the canonical (lowercase) skill vocabulary.
const SKILL_LABELS = { sql: 'SQL', 'node.js': 'Node.js', 'c++': 'C++', javascript: 'JavaScript', typescript: 'TypeScript', 'machine learning': 'Machine Learning', 'data analysis': 'Data Analysis' };
function prettySkill(skill) {
  const key = norm(skill);
  return SKILL_LABELS[key] || String(skill).replace(/\b[a-z]/g, (c) => c.toUpperCase());
}

// Mirrors analysis/locations.py — keep the two alias tables in sync.
const LOCATION_ALIASES = {
  bengaluru: 'bangalore', 'bangalore urban': 'bangalore', gurugram: 'gurgaon', 'new delhi': 'delhi',
  'delhi ncr': 'delhi', ncr: 'delhi', bombay: 'mumbai', 'navi mumbai': 'mumbai', madras: 'chennai',
  calcutta: 'kolkata', poona: 'pune', secunderabad: 'hyderabad', 'greater noida': 'noida',
  'work from home': 'remote', wfh: 'remote', anywhere: 'remote', worldwide: 'remote', remote: 'remote',
};

function canonicalLocation(name) {
  let key = norm(name).replace(/\s+/g, ' ');
  key = key.replace(/^remote ?- ?/, '');
  return LOCATION_ALIASES[key] || key;
}

function locationMatches(desired, jobLocation, workMode) {
  const wanted = new Set((desired || []).filter((p) => p.trim()).map(canonicalLocation));
  if (!wanted.size) return true;
  const places = new Set(String(jobLocation || '').split(/[,/|;]|\s+(?:and|or|&)\s+/i).filter((p) => p.trim()).map(canonicalLocation));
  if (workMode === 'remote') places.add('remote');
  return [...wanted].some((p) => places.has(p));
}

// Mirrors matching/matcher.py's weights so a guest's local score reads the
// same as a signed-in user's server score.
function computeFit(job, prefs) {
  const wanted = new Set((prefs.skills || []).map(norm).filter(Boolean));
  const jobSkills = [...new Set((job.skills || []).map(norm).filter(Boolean))];
  const matched = jobSkills.filter((s) => wanted.has(s));
  const missing = jobSkills.filter((s) => !wanted.has(s));
  if (!hasPrefs(prefs)) return { score: null, passes: true, matched, missing, reasons: [] };
  let score = 0;
  const reasons = [];
  if (matched.length) {
    score += 0.6 * (matched.length / wanted.size) * (matched.length / jobSkills.length);
    reasons.push(`Uses your ${matched.slice(0, 3).map(prettySkill).join(', ')}`);
  }
  const locationOk = locationMatches(prefs.locations, job.location, job.work_mode);
  if (locationOk) {
    score += 0.25;
    if ((prefs.locations || []).some((p) => p.trim())) reasons.push(`In ${job.location}`);
  }
  const stipendOk = !prefs.minimum_stipend || job.salary_numeric == null || job.salary_numeric >= prefs.minimum_stipend;
  if (stipendOk) {
    score += 0.15;
    if (prefs.minimum_stipend && job.salary_numeric != null) reasons.push('Meets your stipend');
  }
  // Hard filters, as in matching/matcher.py: unclassified postings pass.
  const kindOk = (!(prefs.work_modes || []).length || !job.work_mode || prefs.work_modes.includes(job.work_mode))
    && (!(prefs.listing_types || []).length || !job.listing_type || prefs.listing_types.includes(job.listing_type));
  const passes = kindOk && score > 0 && (!wanted.size || matched.length > 0) && locationOk && stipendOk;
  return { score: Math.round(score * 100), passes, matched, missing, reasons };
}

function readableReason(reason) {
  if (reason.startsWith('skills: ')) return `Uses your ${reason.slice(8).split(', ').map(prettySkill).join(', ')}`;
  if (reason.startsWith('location: ')) return `In ${reason.slice(10)}`;
  if (reason === 'stipend meets minimum') return 'Meets your stipend';
  return reason;
}

// ---------------------------------------------------------------- job actions
async function trackJob(jobId, status) {
  const created = await fetchJSON('/applications', { method: 'POST', body: JSON.stringify({ job_id: jobId, status }) });
  if (!created.ok) return null;
  if (created.data.status !== status) {
    const updated = await fetchJSON(`/applications/${created.data.id}`, { method: 'PATCH', body: JSON.stringify({ status }) });
    return updated.ok ? updated.data : null;
  }
  return created.data;
}

// Stop tracking a job. Undo re-creates it at the same status (its status
// history restarts, which is the honest record of what happened).
async function untrackJob(job, onChange) {
  // POST is get-or-create: for an existing application it just returns it.
  const existing = await fetchJSON('/applications', { method: 'POST', body: JSON.stringify({ job_id: job.id, status: 'saved' }) });
  if (!existing.ok) return;
  const previous = existing.data.status;
  const removed = await fetchJSON(`/applications/${existing.data.id}`, { method: 'DELETE' });
  if (!removed.ok) { toast('Couldn’t remove that — try again.'); return; }
  onChange(null);
  toast(previous === 'saved' ? 'Removed from your saved jobs.' : 'No longer tracking this one.', {
    label: 'Undo',
    run: async () => { const back = await trackJob(job.id, previous); if (back) onChange(back.status); },
  });
}

// The bookmark is a toggle: save, or un-save when it's only saved. Anything
// further along (applied, interviewing…) asks first — that's real progress.
async function saveJob(job, onChange, currentStatus) {
  if (!(await requireAccount('Create a free account to save jobs — Santa will remind you before they close.'))) return;
  if (currentStatus === 'saved') { untrackJob(job, onChange); return; }
  if (currentStatus) {
    toast(`You're tracking this as “${STATUS_META[currentStatus].label}”.`, { label: 'Stop tracking', run: () => untrackJob(job, onChange) });
    return;
  }
  const result = await trackJob(job.id, 'saved');
  if (result) {
    onChange(result.status);
    toast(result.status === 'saved' ? 'Saved — Santa will nudge you before the deadline.' : `Already tracking this as “${STATUS_META[result.status].label}”.`, {
      label: 'View', run: () => { window.location.href = '/app/applications'; },
    });
  }
}

async function applyToJob(job, onChange) {
  // Opening synchronously keeps it inside the click gesture (no popup blocker)
  // for signed-in users; guests sign in first, then get an explicit link.
  if (SANTA.auth) window.open(job.link, '_blank', 'noopener');
  else if (await requireAccount('Create a free account so Santa can track this application and follow up for you.')) {
    toast('All set — opening the posting.', { label: 'Open', run: () => window.open(job.link, '_blank', 'noopener') });
  } else return;
  setTimeout(() => {
    toast('Did you finish applying? I’ll track it for you.', {
      label: 'Yes, mark applied',
      run: async () => {
        const result = await trackJob(job.id, 'applied');
        if (result) { onChange('applied'); toast('Marked as applied. I’ll keep an eye out for replies.'); }
      },
    });
  }, SANTA.auth ? 1200 : 4000);
}

async function shareJob(job) {
  const url = `${window.location.origin}/app/jobs/${job.id}`;
  const data = { title: `${job.title} at ${job.company}`, text: `Found this on Santa: ${job.title} at ${job.company}`, url };
  try {
    if (navigator.share) { await navigator.share(data); return; }
    await navigator.clipboard.writeText(url);
    toast('Link copied — share it with a friend.');
  } catch (error) { /* share sheet dismissed */ }
}

// onPick receives a status key, or null for "Remove from tracker".
function openStatusMenu(anchor, current, onPick) {
  document.querySelectorAll('.menu-panel').forEach((m) => m.remove());
  const panel = document.createElement('div');
  panel.className = 'menu-panel';
  panel.setAttribute('role', 'menu');
  panel.innerHTML = Object.entries(STATUS_META).map(([key, meta]) => (
    `<button type="button" role="menuitem" data-status="${key}" class="${key === current ? 'is-current' : ''}"><i class="dot" style="--dot:${meta.color}"></i>${meta.label}${key === current ? ' ✓' : ''}</button>`
  )).join('') + (current ? `<hr><button type="button" role="menuitem" data-status="" style="color:var(--bad)">${ICON.close.replace('<svg', '<svg width="14" height="14"')}Remove from tracker</button>` : '');
  // Fixed to the viewport (not inside the card) so scroll containers like
  // the board can't clip it; opens below the button, or above if no room.
  document.body.appendChild(panel);
  const rect = anchor.getBoundingClientRect();
  const width = Math.max(200, panel.offsetWidth);
  panel.style.position = 'fixed';
  panel.style.left = `${Math.min(Math.max(8, rect.right - width), window.innerWidth - width - 8)}px`;
  const below = window.innerHeight - rect.bottom;
  if (below >= panel.offsetHeight + 12 || below > rect.top) {
    panel.style.top = `${rect.bottom + 6}px`;
    panel.style.transformOrigin = 'top right';
  } else {
    panel.style.top = `${rect.top - panel.offsetHeight - 6}px`;
    panel.style.transformOrigin = 'bottom right';
  }
  panel.style.bottom = 'auto';
  panel.style.right = 'auto';
  const onScroll = () => close();
  // Capture phase: pages scroll inside panels, not the window.
  window.addEventListener('scroll', onScroll, { passive: true, once: true, capture: true });
  const close = (event) => {
    if (event && event.target && panel.contains(event.target)) return;
    panel.remove();
    window.removeEventListener('scroll', onScroll, { capture: true });
    document.removeEventListener('click', close, true);
  };
  setTimeout(() => document.addEventListener('click', close, true));
  panel.querySelectorAll('[data-status]').forEach((button) => {
    button.addEventListener('click', () => { panel.remove(); document.removeEventListener('click', close, true); onPick(button.dataset.status || null); });
  });
}

async function changeStatus(job, anchor, current, onChange) {
  if (!(await requireAccount('Create a free account to track where each application stands.'))) return;
  openStatusMenu(anchor, current, async (status) => {
    if (status === null) { untrackJob(job, onChange); return; }
    const result = await trackJob(job.id, status);
    if (result) { onChange(status); toast(`Moved to ${STATUS_META[status].label}.`); }
  });
}

async function loadBrief(job, target, button) {
  if (!target.hidden) { target.hidden = true; return; }
  if (!(await requireAccount('Create a free account to get Santa’s AI company briefs.'))) return;
  const label = button.textContent;
  button.disabled = true;
  button.textContent = 'Reading up…';
  const result = await fetchJSON(`/jobs/${job.id}/brief`);
  button.disabled = false;
  button.textContent = label;
  target.textContent = result.ok ? result.data.content
    : result.status === 503 ? result.data.error
    : 'Santa couldn’t read up on this company right now — try again in a bit.';
  target.hidden = false;
}

// ---------------------------------------------------------------- job card
function renderJobCard(item, prefs) {
  const job = item.job;
  const fit = computeFit(job, prefs);
  const score = item.score ?? fit.score;
  const reasons = item.reasons ? item.reasons.map(readableReason) : fit.reasons;
  const deadline = deadlineInfo(job.deadline_at);
  const pay = payText(job);
  const status = item.application_status;
  const card = document.createElement('article');
  card.className = 'card card-hover job-card reveal';
  card.dataset.jobId = job.id;
  card.tabIndex = 0;
  card.setAttribute('aria-label', `${job.title} at ${job.company}`);
  const why = reasons.length
    ? `<div class="why"><b>Why this fits you</b><ul>${reasons.slice(0, 3).map((r) => `<li>${ICON.check}${escapeHTML(r)}</li>`).join('')}</ul></div>`
    : (job.skills || []).length ? `<div class="why"><b>Skills</b><ul><li>${job.skills.slice(0, 6).map((k) => escapeHTML(prettySkill(k))).join(' · ')}</li></ul></div>` : '<div class="why"></div>';
  const matchPill = score != null && score > 0 ? `<span class="match-pill ${score >= 70 ? '' : 'mid'}">${ICON.gem}${score}% Match</span>` : '';
  card.innerHTML = `
    <div class="job-head">
      ${logoTile(job.company)}
      <div class="job-title">
        <h3>${escapeHTML(job.title)}</h3>
        <p>${escapeHTML(job.company)}<span class="sep">•</span>${escapeHTML(job.location)}${job.posted_at ? `<span class="sep">•</span><span class="muted">${timeAgo(job.posted_at)}</span>` : ''}</p>
      </div>
      <div class="job-side">
        ${matchPill}
        <button type="button" class="icon-btn icon-btn-sm" data-act="share" aria-label="Share" title="Share">${ICON.share}</button>
        <button type="button" class="icon-btn icon-btn-sm ${status ? 'is-on' : ''}" data-act="save" aria-pressed="${Boolean(status)}" aria-label="${status === 'saved' ? 'Remove from saved' : status ? 'Tracking' : 'Save'}" title="${status === 'saved' ? 'Saved — tap to remove' : status ? STATUS_META[status].label : 'Save for later'}">${ICON.bookmark}</button>
      </div>
    </div>
    ${jobTags(job).length ? `<div class="job-tags">${jobTags(job).map(([tone, t]) => `<span class="tag ${tone ? 'tag-' + tone : ''}">${escapeHTML(t)}</span>`).join('')}</div>` : ''}
    <div class="job-facts">
      ${pay ? `<span class="job-pay">${escapeHTML(pay)}</span>` : ''}
      ${(job.quality_flags || []).includes('reposted') ? `<span class="tag tag-bad" title="Santa saw this posting disappear and come back — it may be kept alive by relisting">${ICON.alert} Repost detected</span>` : ''}
      ${matchPill ? matchPill.replace('class="match-pill', 'class="match-pill mobile-match') : ''}
      <span class="facts-end">${deadline ? `<span class="deadline ${deadline.urgent ? 'urgent' : ''}">${ICON.clock} Apply in ${deadline.text}</span>` : ''}</span>
    </div>
    <p class="company-brief" hidden></p>
    <div class="job-foot">
      ${why}
      <div class="job-actions">
        <span class="menu"><button type="button" class="btn btn-ghost btn-sm" data-act="status" aria-label="Track status">${status ? `<i class="dot" style="--dot:${STATUS_META[status].color}"></i>${STATUS_META[status].label}` : 'Track'} ${ICON.chevron}</button></span>
        <button type="button" class="btn btn-secondary btn-sm" data-act="brief">Company Info</button>
        <button type="button" class="btn btn-primary btn-sm" data-act="apply">Apply ${ICON.arrow}</button>
      </div>
    </div>`;

  const update = (next) => {
    item.application_status = next;
    const fresh = renderJobCard(item, prefs);
    fresh.classList.add('is-in');
    // Look the card up again: an async callback (e.g. Undo) may fire after
    // this card was already replaced by a newer render.
    (document.querySelector(`.job-card[data-job-id="${job.id}"]`) || card).replaceWith(fresh);
    window.dispatchEvent(new CustomEvent('santa:tracked', { detail: { jobId: job.id, status: next } }));
  };
  card.addEventListener('click', (event) => {
    const act = event.target.closest('[data-act]');
    if (!act) {
      if (!event.target.closest('a, .menu-panel')) window.location.href = `/app/jobs/${job.id}`;
      return;
    }
    event.stopPropagation();
    const action = act.dataset.act;
    if (action === 'save') saveJob(job, update, status);
    if (action === 'apply') applyToJob(job, update);
    if (action === 'share') shareJob(job);
    if (action === 'status') changeStatus(job, act, status, update);
    if (action === 'brief') loadBrief(job, card.querySelector('.company-brief'), act);
  });
  card.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && event.target === card) window.location.href = `/app/jobs/${job.id}`;
  });
  return card;
}

// Two-level pages: the sticky list panel must be exactly one pane tall.
(function syncPaneHeight() {
  const pane = document.querySelector('.main.two-level');
  if (!pane) return;
  const set = () => pane.style.setProperty('--pane-h', `${pane.clientHeight}px`);
  set();
  if ('ResizeObserver' in window) new ResizeObserver(set).observe(pane);
  else window.addEventListener('resize', set);
})();

updateShellUser();
