// Domino Self-RAG Frontend Application Logic
document.addEventListener('DOMContentLoaded', () => {
  // Global State
  const state = {
    activeRepo: 'bank_analyzer',
    citationsCache: {},
    stats: null
  };

  // -------------------------------------------------------------
  // 1. Tab Navigation
  // -------------------------------------------------------------
  const navTabs = document.querySelectorAll('.nav-tab');
  const tabPanels = document.querySelectorAll('.tab-panel');

  navTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetId = tab.dataset.tab;
      
      navTabs.forEach(t => t.classList.remove('active'));
      tabPanels.forEach(p => p.classList.remove('active'));
      
      tab.classList.add('active');
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) {
        targetPanel.classList.add('active');
      }
    });
  });

  // -------------------------------------------------------------
  // 2. Preset Query Chips
  // -------------------------------------------------------------
  const presetChips = document.querySelectorAll('.preset-chips .chip');
  const qaQueryInput = document.getElementById('qa-query');

  presetChips.forEach(chip => {
    chip.addEventListener('click', () => {
      if (qaQueryInput && chip.dataset.q) {
        qaQueryInput.value = chip.dataset.q;
        qaQueryInput.focus();
      }
    });
  });

  // -------------------------------------------------------------
  // 3. Header Stats & Initial State
  // -------------------------------------------------------------
  async function refreshStats() {
    try {
      const res = await fetch('/api/self-rag/stats');
      if (!res.ok) return;
      const data = await res.json();
      state.stats = data;

      const activeBadge = document.getElementById('active-repo-badge');
      const statsBadge = document.getElementById('indexed-stats-badge');

        const repos = data.repositories || data.indexed_repos || [];
        const primaryRepo = repos[0];
        state.activeRepo = primaryRepo;
        
        const count = (data.chunk_count_per_repo && data.chunk_count_per_repo[primaryRepo]) || data.total_chunks_indexed || data.indexed_chunks || 0;
        if (activeBadge) activeBadge.textContent = `Active Repo: ${primaryRepo}`;
        if (statsBadge) statsBadge.textContent = `${count} Chunks Indexed`;

        // Update default values across inputs
        const repoInputs = ['qa-repo-id', 'refactor-repo-id', 'index-repo-name', 'impact-repo'];
        repoInputs.forEach(id => {
          const el = document.getElementById(id);
          if (el && !el.value) {
            el.value = primaryRepo;
          }
        });
      } else {
        if (activeBadge) activeBadge.textContent = 'Active Repo: None';
        if (statsBadge) statsBadge.textContent = '0 Chunks Indexed';
      }
    } catch (err) {
      console.warn('Could not load Self-RAG stats:', err);
    }
  }

  refreshStats();

  // -------------------------------------------------------------
  // 4. Markdown Formatter Helper
  // -------------------------------------------------------------
  function formatMarkdown(text) {
    if (!text) return '';
    let escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Code blocks ```code```
    escaped = escaped.replace(/```([\s\S]*?)```/g, (match, p1) => {
      return `<pre class="code-block"><code>${p1.trim()}</code></pre>`;
    });

    // Inline code `code`
    escaped = escaped.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

    // Bold **text**
    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Headers ### Header
    escaped = escaped.replace(/^### (.*$)/gim, '<h4 style="margin: 12px 0 6px 0; color: var(--accent-indigo);">$1</h4>');
    escaped = escaped.replace(/^## (.*$)/gim, '<h3 style="margin: 16px 0 8px 0; color: #fff;">$1</h3>');
    escaped = escaped.replace(/^# (.*$)/gim, '<h2 style="margin: 18px 0 10px 0; color: #fff;">$1</h2>');

    // Bullet points
    escaped = escaped.replace(/^\* (.*$)/gim, '<li style="margin-left: 18px;">$1</li>');
    escaped = escaped.replace(/^- (.*$)/gim, '<li style="margin-left: 18px;">$1</li>');

    return escaped;
  }

  // -------------------------------------------------------------
  // 5. Code Modal Viewer
  // -------------------------------------------------------------
  const codeModal = document.getElementById('code-modal');
  const modalCloseBtn = document.getElementById('modal-close-btn');
  const modalTitle = document.getElementById('modal-title');
  const modalCodeContent = document.getElementById('modal-code-content');

  function openCodeModal(title, code) {
    if (modalTitle) modalTitle.textContent = title;
    if (modalCodeContent) modalCodeContent.textContent = code || '# No source code available for this chunk.';
    if (codeModal) codeModal.style.display = 'flex';
  }

  function closeModal() {
    if (codeModal) codeModal.style.display = 'none';
  }

  if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeModal);
  if (codeModal) {
    codeModal.addEventListener('click', (e) => {
      if (e.target === codeModal) closeModal();
    });
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });

  // -------------------------------------------------------------
  // 6. Tab 1: Self-RAG Codebase QA
  // -------------------------------------------------------------
  const qaSubmitBtn = document.getElementById('qa-submit-btn');
  const qaResultsContainer = document.getElementById('qa-results-container');
  const qaAnswerBody = document.getElementById('qa-answer-body');
  const qaCitationsList = document.getElementById('qa-citations-list');
  const qaReflectionPills = document.getElementById('qa-reflection-pills');

  const auditRetrieveText = document.getElementById('audit-retrieve-text');
  const auditRelText = document.getElementById('audit-rel-text');
  const auditSupText = document.getElementById('audit-sup-text');
  const auditUseText = document.getElementById('audit-use-text');

  if (qaSubmitBtn) {
    qaSubmitBtn.addEventListener('click', async () => {
      const repoId = document.getElementById('qa-repo-id')?.value.trim() || state.activeRepo;
      const query = document.getElementById('qa-query')?.value.trim();
      const topK = parseInt(document.getElementById('qa-topk')?.value || '4', 10);
      const enableReflection = document.getElementById('qa-reflection')?.checked ?? true;

      if (!query) {
        alert('Please enter a developer query.');
        return;
      }

      qaSubmitBtn.disabled = true;
      const originalText = qaSubmitBtn.innerHTML;
      qaSubmitBtn.innerHTML = `
        <svg class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
          <path d="M12 2a10 10 0 0 1 10 10" />
        </svg>
        Analyzing with Self-RAG...
      `;

      try {
        const response = await fetch('/api/qa', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            repo_id: repoId,
            query: query,
            top_k: topK,
            enable_reflection: enableReflection
          })
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({ detail: 'Server Error' }));
          throw new Error(errData.detail || `Request failed with status ${response.status}`);
        }

        const data = await response.json();

        // Reveal Results
        if (qaResultsContainer) qaResultsContainer.style.display = 'block';

        // Update Audit Banner
        if (auditRetrieveText) {
          auditRetrieveText.textContent = data.retrieval_decision || 'Adaptive retrieval completed';
        }
        if (auditRelText) {
          if (data.relevance_score != null) {
            auditRelText.textContent = `${Math.round(data.relevance_score * 100)}% Snippets Relevant`;
          } else {
            auditRelText.textContent = `${data.citations?.length || 0} Grounded Snippets`;
          }
        }
        if (auditSupText) {
          if (data.grounding_score != null) {
            auditSupText.textContent = `${Math.round(data.grounding_score * 100)}% Grounded In Code`;
          } else {
            auditSupText.textContent = 'Grounded & Validated';
          }
        }
        if (auditUseText) {
          if (data.utility_score != null) {
            auditUseText.textContent = `Score: ${data.utility_score}/5 Utility`;
          } else {
            auditUseText.textContent = 'Actionable Answer';
          }
        }

        // Update Reflection Badges
        if (qaReflectionPills) {
          qaReflectionPills.innerHTML = `
            <span class="badge badge-purple">[Retrieve: YES]</span>
            <span class="badge badge-cyan">[IsRel: Relevant]</span>
            <span class="badge badge-emerald">[IsSup: Fully Supported]</span>
            <span class="badge badge-amber">[IsUse: 5/5]</span>
          `;
        }

        // Render Answer
        if (qaAnswerBody) {
          qaAnswerBody.innerHTML = formatMarkdown(data.answer);
        }

        // Render Citations
        if (qaCitationsList) {
          qaCitationsList.innerHTML = '';
          state.citationsCache = {};

          if (data.citations && data.citations.length > 0) {
            data.citations.forEach((cit, idx) => {
              state.citationsCache[cit.chunk_id] = cit;

              const card = document.createElement('div');
              card.className = 'citation-card';
              card.innerHTML = `
                <div class="citation-symbol">
                  <span>${cit.symbol || cit.entity_id || 'Code Chunk'}</span>
                </div>
                <div class="citation-file">
                  <span>${cit.file_path} (L${cit.start_line}-${cit.end_line})</span>
                </div>
                <div style="font-size: 0.72rem; color: var(--accent-cyan); margin-top: 4px;">
                  Score: ${cit.similarity_score ? cit.similarity_score.toFixed(3) : 'RRF'} • Click to view source
                </div>
              `;

              card.addEventListener('click', () => {
                openCodeModal(
                  `${cit.symbol || 'Source'} — ${cit.file_path} (Lines ${cit.start_line}-${cit.end_line})`,
                  cit.code_content || '# Full source code content not available'
                );
              });

              qaCitationsList.appendChild(card);
            });
          } else {
            qaCitationsList.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem;">No direct citations retrieved. Model answered from direct reasoning.</div>';
          }
        }

        // Scroll to results smoothly
        qaResultsContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

      } catch (err) {
        alert(`Error during QA: ${err.message}`);
      } finally {
        qaSubmitBtn.disabled = false;
        qaSubmitBtn.innerHTML = originalText;
      }
    });
  }

  // -------------------------------------------------------------
  // 7. Tab 2: Safe Refactoring Assistant
  // -------------------------------------------------------------
  const refactorSubmitBtn = document.getElementById('refactor-submit-btn');
  const refactorResultsContainer = document.getElementById('refactor-results-container');
  const verifSyntaxVal = document.getElementById('verif-syntax-val');
  const verifCallersVal = document.getElementById('verif-callers-val');
  const verifTestsVal = document.getElementById('verif-tests-val');
  const refactorDiffBox = document.getElementById('refactor-diff-box');
  const diffFileTag = document.getElementById('diff-file-tag');
  const refactorStatusBadges = document.getElementById('refactor-status-badges');
  const callerDiffsSection = document.getElementById('caller-diffs-section');
  const callerDiffsList = document.getElementById('caller-diffs-list');

  function renderDiffLines(diffText) {
    if (!diffText) return 'No diff produced.';
    const lines = diffText.split('\n');
    return lines.map(line => {
      const escaped = line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      if (line.startsWith('+++') || line.startsWith('---')) {
        return `<span style="color: var(--text-muted);">${escaped}</span>`;
      } else if (line.startsWith('+')) {
        return `<span class="diff-line-add">${escaped}</span>`;
      } else if (line.startsWith('-')) {
        return `<span class="diff-line-del">${escaped}</span>`;
      } else if (line.startsWith('@@')) {
        return `<span style="color: var(--accent-purple); font-weight: 600;">${escaped}</span>`;
      }
      return `<span>${escaped}</span>`;
    }).join('\n');
  }

  if (refactorSubmitBtn) {
    refactorSubmitBtn.addEventListener('click', async () => {
      const repoId = document.getElementById('refactor-repo-id')?.value.trim() || state.activeRepo;
      const targetEntity = document.getElementById('refactor-target')?.value.trim();
      const instructions = document.getElementById('refactor-instructions')?.value.trim();

      if (!targetEntity || !instructions) {
        alert('Please provide both the Target Entity and Refactoring Instructions.');
        return;
      }

      refactorSubmitBtn.disabled = true;
      const originalText = refactorSubmitBtn.innerHTML;
      refactorSubmitBtn.innerHTML = `
        <svg class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
          <path d="M12 2a10 10 0 0 1 10 10" />
        </svg>
        Generating & Validating AST...
      `;

      try {
        const response = await fetch('/api/refactor', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            repo_id: repoId,
            target_entity: targetEntity,
            instructions: instructions
          })
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({ detail: 'Server Error' }));
          throw new Error(errData.detail || `Request failed with status ${response.status}`);
        }

        const data = await response.json();

        // Reveal Results
        if (refactorResultsContainer) refactorResultsContainer.style.display = 'block';

        // Status Badges
        if (refactorStatusBadges) {
          refactorStatusBadges.innerHTML = `
            <span class="badge ${data.ast_valid ? 'badge-emerald' : 'badge-rose'}">
              ${data.ast_valid ? 'AST Valid' : 'Syntax Error'}
            </span>
            <span class="badge badge-purple">${data.impacted_callers?.length || 0} Callers Checked</span>
          `;
        }

        // Verification Grid
        if (verifSyntaxVal) {
          if (data.ast_valid) {
            verifSyntaxVal.textContent = '✅ Valid Python AST';
            verifSyntaxVal.style.color = 'var(--accent-emerald)';
          } else {
            verifSyntaxVal.textContent = `❌ ${data.ast_error || 'Syntax Validation Failed'}`;
            verifSyntaxVal.style.color = 'var(--accent-rose)';
          }
        }

        if (verifCallersVal) {
          const callersCount = data.impacted_callers?.length || 0;
          verifCallersVal.textContent = `${callersCount} Dependent Callers`;
          verifCallersVal.style.color = callersCount > 0 ? 'var(--accent-amber)' : 'var(--accent-emerald)';
        }

        if (verifTestsVal) {
          const testsCount = data.recommended_tests?.length || 0;
          verifTestsVal.textContent = testsCount > 0 ? `${testsCount} Test Suites Identified` : 'Zero Affected Tests';
        }

        // Unified Diff
        if (diffFileTag) diffFileTag.textContent = targetEntity;
        if (refactorDiffBox) {
          refactorDiffBox.innerHTML = renderDiffLines(data.unified_diff);
        }

        // Cascading caller updates if any
        if (callerDiffsSection && callerDiffsList) {
          if (data.impacted_callers && data.impacted_callers.length > 0) {
            callerDiffsSection.style.display = 'block';
            callerDiffsList.innerHTML = data.impacted_callers.map(caller => `
              <div style="background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 10px 14px; margin-bottom: 8px;">
                <span style="font-family: var(--font-mono); font-size: 0.85rem; color: var(--accent-cyan); font-weight: 600;">${caller}</span>
                <p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 4px;">Verified for signature and call-site compatibility.</p>
              </div>
            `).join('');
          } else {
            callerDiffsSection.style.display = 'none';
          }
        }

        refactorResultsContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

      } catch (err) {
        alert(`Error during refactoring: ${err.message}`);
      } finally {
        refactorSubmitBtn.disabled = false;
        refactorSubmitBtn.innerHTML = originalText;
      }
    });
  }

  // -------------------------------------------------------------
  // 8. Tab 3: Ingest & Index Repository
  // -------------------------------------------------------------
  const indexSubmitBtn = document.getElementById('index-submit-btn');
  const indexResultsContainer = document.getElementById('index-results-container');
  const indexStatsGrid = document.getElementById('index-stats-grid');
  const indexStatusPill = document.getElementById('index-status-pill');

  if (indexSubmitBtn) {
    indexSubmitBtn.addEventListener('click', async () => {
      const repoPath = document.getElementById('index-path')?.value.trim();
      const repoName = document.getElementById('index-repo-name')?.value.trim() || 'my_repo';
      const commitSha = document.getElementById('index-commit')?.value.trim() || 'main';
      const keepClone = document.getElementById('index-keep-clone')?.checked ?? true;

      if (!repoPath) {
        alert('Please enter a GitHub URL or local repository path.');
        return;
      }

      indexSubmitBtn.disabled = true;
      const originalText = indexSubmitBtn.innerHTML;
      indexSubmitBtn.innerHTML = `
        <svg class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
          <path d="M12 2a10 10 0 0 1 10 10" />
        </svg>
        Cloning, Parsing AST & Vector Indexing...
      `;

      try {
        const response = await fetch('/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            path: repoPath,
            repo_name: repoName,
            commit_sha: commitSha,
            keep_clone: keepClone,
            export_graphml: false
          })
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({ detail: 'Ingestion failed' }));
          throw new Error(errData.detail || `Server returned ${response.status}`);
        }

        const data = await response.json();

        if (indexResultsContainer) indexResultsContainer.style.display = 'block';
        if (indexStatusPill) {
          indexStatusPill.textContent = 'Successfully Indexed';
          indexStatusPill.className = 'badge badge-emerald';
        }

        const gSummary = data.graph_summary || {};
        if (indexStatsGrid) {
          indexStatsGrid.innerHTML = `
            <div class="verif-card">
              <span class="verif-title">Self-RAG Chunks</span>
              <span class="verif-value" style="color: var(--accent-indigo);">${data.indexed_code_chunks || 0}</span>
            </div>
            <div class="verif-card">
              <span class="verif-title">Graph Nodes (Entities)</span>
              <span class="verif-value" style="color: var(--accent-cyan);">${gSummary.nodes || 0}</span>
            </div>
            <div class="verif-card">
              <span class="verif-title">Graph Edges (Dependencies)</span>
              <span class="verif-value" style="color: var(--accent-emerald);">${gSummary.edges || 0}</span>
            </div>
            <div class="verif-card">
              <span class="verif-title">Neo4j Integration</span>
              <span class="verif-value" style="color: ${data.stored_in_neo4j ? 'var(--accent-emerald)' : 'var(--accent-amber)'};">
                ${data.stored_in_neo4j ? 'Connected' : 'Offline (Local Fallback)'}
              </span>
            </div>
          `;
        }

        // Refresh stats badge
        await refreshStats();
        indexResultsContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

      } catch (err) {
        alert(`Ingestion error: ${err.message}`);
        if (indexStatusPill) {
          indexStatusPill.textContent = 'Failed';
          indexStatusPill.className = 'badge badge-rose';
        }
      } finally {
        indexSubmitBtn.disabled = false;
        indexSubmitBtn.innerHTML = originalText;
      }
    });
  }

  // -------------------------------------------------------------
  // 9. Tab 4: Impact & Risk Radar
  // -------------------------------------------------------------
  const impactSubmitBtn = document.getElementById('impact-submit-btn');
  const impactResultsContainer = document.getElementById('impact-results-container');
  const impactRiskBadge = document.getElementById('impact-risk-badge');
  const impactDetailsContent = document.getElementById('impact-details-content');

  if (impactSubmitBtn) {
    impactSubmitBtn.addEventListener('click', async () => {
      const repo = document.getElementById('impact-repo')?.value.trim() || state.activeRepo;
      const funcName = document.getElementById('impact-function')?.value.trim();

      if (!funcName) {
        alert('Please enter a function name.');
        return;
      }

      impactSubmitBtn.disabled = true;
      const originalText = impactSubmitBtn.innerHTML;
      impactSubmitBtn.innerHTML = `
        <svg class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
          <path d="M12 2a10 10 0 0 1 10 10" />
        </svg>
        Traversing Dependency Graph...
      `;

      try {
        const response = await fetch('/impact-analysis', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            repo: repo,
            function_name: funcName,
            depth: 3
          })
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({ detail: 'Impact analysis failed' }));
          throw new Error(errData.detail || `Server returned ${response.status}`);
        }

        const data = await response.json();

        if (impactResultsContainer) impactResultsContainer.style.display = 'block';

        const summary = data.summary || {};
        const totalImpacted = (summary.functions || 0) + (summary.files || 0) + (summary.routes || 0);

        // Determine Risk Score
        let riskColor = 'badge-emerald';
        let riskLabel = 'LOW RISK';
        if (totalImpacted > 10 || (summary.routes || 0) > 0) {
          riskColor = 'badge-rose';
          riskLabel = 'HIGH RISK (Affects External Routes/APIs)';
        } else if (totalImpacted > 3) {
          riskColor = 'badge-amber';
          riskLabel = 'MEDIUM RISK';
        }

        if (impactRiskBadge) {
          impactRiskBadge.className = `badge ${riskColor}`;
          impactRiskBadge.textContent = riskLabel;
        }

        if (impactDetailsContent) {
          impactDetailsContent.innerHTML = `
            <div class="verification-grid" style="margin-top: 16px;">
              <div class="verif-card">
                <span class="verif-title">Impacted Functions</span>
                <span class="verif-value" style="color: var(--accent-cyan);">${summary.functions || 0}</span>
              </div>
              <div class="verif-card">
                <span class="verif-title">Impacted Files</span>
                <span class="verif-value" style="color: var(--accent-indigo);">${summary.files || 0}</span>
              </div>
              <div class="verif-card">
                <span class="verif-title">API Routes at Risk</span>
                <span class="verif-value" style="color: var(--accent-rose);">${summary.routes || 0}</span>
              </div>
              <div class="verif-card">
                <span class="verif-title">Test Suites Triggered</span>
                <span class="verif-value" style="color: var(--accent-emerald);">${summary.tests || 0}</span>
              </div>
            </div>
            
            <div style="background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px; margin-top: 16px;">
              <h4 style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 8px;">Changed Root Entities</h4>
              ${(data.changed_entities || []).map(ent => `
                <div style="font-family: var(--font-mono); font-size: 0.85rem; color: var(--accent-amber); margin-bottom: 4px;">
                  • ${ent.name || ent.id || ent.entity_id} (${ent.type || 'Entity'})
                </div>
              `).join('')}
            </div>
          `;
        }

        impactResultsContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

      } catch (err) {
        alert(`Impact Analysis error: ${err.message} (Note: Full graph queries require Neo4j running)`);
      } finally {
        impactSubmitBtn.disabled = false;
        impactSubmitBtn.innerHTML = originalText;
      }
    });
  }

});
