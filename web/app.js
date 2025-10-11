async function fetchConfig() {
  try {
    const res = await fetch('/config_public');
    if (!res.ok) return {};
    return await res.json();
  } catch {
    return {};
  }
}

function setLoading(loading) {
  const btn = document.getElementById('send');
  const spinner = document.getElementById('loading');
  btn.disabled = loading;
  spinner.classList.toggle('hidden', !loading);
}

async function ask(question) {
  const res = await fetch('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question })
  });
  if (!res.ok) {
    const text = await res.text().catch(() => 'エラーが発生しました');
    throw new Error(text || 'HTTP error ' + res.status);
  }
  return res.json();
}

(async function init() {
  const cfg = await fetchConfig();
  const form = document.getElementById('ask-form');
  const ta = document.getElementById('question');
  const result = document.getElementById('result');
  const answer = document.getElementById('answer');
  const fb = document.getElementById('fallback');
  const formLink = document.getElementById('formLink');
  if (cfg.google_form_url) formLink.href = cfg.google_form_url;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const q = (ta.value || '').trim();
    if (!q) return;
    setLoading(true);
    result.classList.add('hidden');
    fb.classList.add('hidden');
    answer.textContent = '';
    try {
      const data = await ask(q);
      answer.textContent = data.answer || '';
      result.classList.remove('hidden');
      if (data.fallback) fb.classList.remove('hidden');
    } catch (err) {
      answer.textContent = 'エラーが発生しました。時間をおいて再度お試しください。';
      result.classList.remove('hidden');
    } finally {
      setLoading(false);
    }
  });
})();

