// Save user configuration to browser storage
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

// Load saved configuration on page load
window.onload = () => {
  document.getElementById('repo').value = localStorage.getItem('blueskyBotRepo') || '';
};

// Display status message with styling
function showStatus(text, type = 'info') {
  const statusEl = document.getElementById('status');
  statusEl.textContent = text;
  statusEl.className = type;
}

// Trigger GitHub Actions workflow manually
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

// Pause/resume bot by creating/deleting .paused file
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
    // Get current main branch SHA
    const branchRes = await fetch(`https://api.github.com/repos/${repo}/git/ref/heads/main`, {
      headers: { 'Authorization': `token ${token}` }
    });
    const branchData = await branchRes.json();
    const baseSha = branchData.object.sha;

    if (pause) {
      // Create .paused file commit
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
      // Remove .paused file by creating new commit without it
      const treeRes = await fetch(`https://api.github.com/repos/${repo}/git/trees/${baseSha}`);
      const treeData = await treeRes.json();
      
      // Filter out .paused from tree
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
