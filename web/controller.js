// Сохранение конфигурации
function saveConfig() {
  const repo = document.getElementById('repo').value.trim();
  const token = document.getElementById('token').value.trim();
  
  if (!repo || !token) {
    showStatus('⚠️ Fill both fields', 'error');
    return;
  }
  
  localStorage.setItem('blueskyBotRepo', repo);
  localStorage.setItem('blueskyBotToken', token);
  showStatus('✅ Config saved!', 'success');
}

// Загрузка конфигурации при старте
window.onload = () => {
  document.getElementById('repo').value = localStorage.getItem('blueskyBotRepo') || '';
};

// Показ статуса
function showStatus(text, type = 'info') {
  const statusEl = document.getElementById('status');
  statusEl.textContent = text;
  statusEl.className = type;
}

// Запуск workflow
async function runWorkflow() {
  const repo = localStorage.getItem('blueskyBotRepo');
  const token = localStorage.getItem('blueskyBotToken');
  
  if (!repo || !token) {
    showStatus('❌ Config missing! Fill and save first.', 'error');
    return;
  }

  document.getElementById('runBtn').disabled = true;
  showStatus('Starting workflow...', 'info');

  try {
    const response = await fetch(`https://api.github.com/repos/${repo}/actions/workflows/bluesky-bot.yml/dispatches`, {
      method: 'POST',
      headers: {
        'Authorization': `token ${token}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ref: 'main' })
    });

    if (response.ok) {
      showStatus('✅ Workflow started! Check GitHub Actions.', 'success');
    } else {
      const error = await response.text();
      showStatus(`❌ Failed: ${error}`, 'error');
    }
  } catch (err) {
    showStatus(`❌ Network error: ${err.message}`, 'error');
  } finally {
    document.getElementById('runBtn').disabled = false;
  }
}

// Пауза/возобновление через файл .paused
async function togglePause(pause) {
  const repo = localStorage.getItem('blueskyBotRepo');
  const token = localStorage.getItem('blueskyBotToken');
  
  if (!repo || !token) {
    showStatus('❌ Config missing!', 'error');
    return;
  }

  const btn = pause ? document.getElementById('pauseBtn') : document.getElementById('resumeBtn');
  btn.disabled = true;
  showStatus(pause ? 'Pausing...' : 'Resuming...', 'info');

  try {
    // Получаем SHA текущего main
    const branchRes = await fetch(`https://api.github.com/repos/${repo}/git/ref/heads/main`, {
      headers: { 'Authorization': `token ${token}` }
    });
    const branchData = await branchRes.json();
    const baseSha = branchData.object.sha;

    if (pause) {
      // Создаем коммит с .paused
      const blobRes = await fetch(`https://api.github.com/repos/${repo}/git/blobs`, {
        method: 'POST',
        headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: "paused", encoding: "utf-8" })
      });
      const blobData = await blobRes.json();

      const treeRes = await fetch(`https://api.github.com/repos/${repo}/git/trees`, {
        method: 'POST',
        headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_tree: null,
          tree: [{ path: ".paused", mode: "100644", type: "blob", sha: blobData.sha }]
        })
      });
      const treeData = await treeRes.json();

      const commitRes = await fetch(`https://api.github.com/repos/${repo}/git/commits`, {
        method: 'POST',
        headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: "[skip] Pause bot",
          tree: treeData.sha,
          parents: [baseSha]
        })
      });
      const commitData = await commitRes.json();

      await fetch(`https://api.github.com/repos/${repo}/git/refs/heads/main`, {
        method: 'PATCH',
        headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ sha: commitData.sha })
      });

      showStatus('⏸️ Bot paused! Actions will skip until resumed.', 'success');
    } else {
      // Удаляем .paused — создаем коммит без него
      const treeRes = await fetch(`https://api.github.com/repos/${repo}/git/trees/${baseSha}`);
      const treeData = await treeRes.json();
      
      // Фильтруем дерево без .paused
      const newTree = treeData.tree.filter(item => item.path !== '.paused');
      
      const newTreeRes = await fetch(`https://api.github.com/repos/${repo}/git/trees`, {
        method: 'POST',
        headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ tree: newTree, base_tree: null })
      });
      const newTreeData = await newTreeRes.json();

      const commitRes = await fetch(`https://api.github.com/repos/${repo}/git/commits`, {
        method: 'POST',
        headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: "[skip] Resume bot",
          tree: newTreeData.sha,
          parents: [baseSha]
        })
      });
      const commitData = await commitRes.json();

      await fetch(`https://api.github.com/repos/${repo}/git/refs/heads/main`, {
        method: 'PATCH',
        headers: { 'Authorization': `token ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ sha: commitData.sha })
      });

      showStatus('▶️ Bot resumed! Next scheduled run will work.', 'success');
    }
  } catch (err) {
    console.error(err);
    showStatus(`❌ Error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
  }
}
