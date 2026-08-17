// Shared JSON fetch helper: every authenticated page needs the same
// "redirect to login on 401" handling, previously copy-pasted per template.
async function fetchJSON(url, options) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    ...options,
  });
  if (response.status === 401) {
    window.location.href = '/login';
    return null;
  }
  const data = response.status === 204 ? null : await response.json();
  return { ok: response.ok, status: response.status, data };
}

const logoutBtn = document.getElementById('logout-btn');
if (logoutBtn) {
  logoutBtn.addEventListener('click', async () => {
    await fetch('/auth/logout', { method: 'POST' });
    window.location.href = '/';
  });
}

// The initial theme is already stamped by the inline script in <head>
// (before first paint); this just makes the toggle button change it.
const THEME_STORAGE_KEY = 'santa-theme';
const themeToggle = document.getElementById('theme-toggle');
if (themeToggle) {
  const root = document.documentElement;
  const syncLabel = () => {
    const isDark = root.getAttribute('data-theme') === 'dark';
    themeToggle.setAttribute('aria-label', isDark ? 'Switch to light theme' : 'Switch to dark theme');
  };
  syncLabel();
  themeToggle.addEventListener('click', () => {
    const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    localStorage.setItem(THEME_STORAGE_KEY, next);
    syncLabel();
  });
}
