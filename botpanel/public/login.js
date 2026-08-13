const form = document.getElementById('login-form');
const errorEl = document.getElementById('login-error');

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  errorEl.hidden = true;
  const password = document.getElementById('password').value;

  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    const data = await res.json();
    if (data.ok) {
      window.location.href = '/';
    } else {
      errorEl.textContent = data.error || 'Sign in failed.';
      errorEl.hidden = false;
    }
  } catch (err) {
    errorEl.textContent = 'Could not reach the panel server.';
    errorEl.hidden = false;
  }
});
