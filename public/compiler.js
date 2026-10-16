(() => {
  const source = document.getElementById('source');
  const gutter = document.getElementById('gutter');
  const status = document.getElementById('status');
  const example = document.getElementById('example');
  const optimize = document.getElementById('optimize');
  const compileButton = document.getElementById('compile');
  const shortcut = document.getElementById('shortcut');
  const panel = document.getElementById('panel');
  const panelNote = document.getElementById('panel-note');
  const download = document.getElementById('download');
  const tabs = Array.from(document.querySelectorAll('[role="tab"]'));

  const PHASE_NAMES = {
    request: 'Request',
    lexer: 'Lexer',
    parser: 'Parser',
    semantic: 'Semantic analysis',
    optimizer: 'Optimizer',
    tac: 'Three-address code',
    codegen: 'LLVM code generation',
  };

  const isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
  shortcut.textContent = isMac ? '⌘ Enter' : 'Ctrl+Enter';

  let result = null;
  let activeStage = 'llvm';
  let request = null;
  let debounce = null;
  let errorLine = null;
  let tabInserts = true;

  // ---- Editor ----

  function renderGutter() {
    const count = source.value.split('\n').length;
    const lines = [];
    for (let i = 1; i <= count; i++) {
      lines.push(i === errorLine ? `<span class="marked">${i}</span>` : `<span>${i}</span>`);
    }
    gutter.innerHTML = lines.join('');
    gutter.scrollTop = source.scrollTop;
  }

  source.addEventListener('scroll', () => { gutter.scrollTop = source.scrollTop; });

  source.addEventListener('input', () => {
    errorLine = null;
    renderGutter();
    panel.classList.add('stale');
    clearTimeout(debounce);
    debounce = setTimeout(compile, 600);
  });

  source.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      compile();
      return;
    }
    // Tab indents, so Escape hands the Tab key back to page navigation
    if (event.key === 'Escape') {
      tabInserts = false;
      return;
    }
    if (event.key === 'Tab' && tabInserts && !event.shiftKey) {
      event.preventDefault();
      const start = source.selectionStart;
      source.setRangeText('    ', start, source.selectionEnd, 'end');
      source.dispatchEvent(new Event('input'));
    }
  });

  source.addEventListener('focus', () => { tabInserts = true; });

  // ---- Compiling ----

  async function compile() {
    clearTimeout(debounce);
    if (request) request.abort();
    const controller = new AbortController();
    request = controller;
    compileButton.disabled = true;
    panel.classList.add('stale');
    const started = performance.now();

    try {
      const response = await fetch('/api/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: source.value, optimize: optimize.checked }),
        signal: controller.signal,
      });
      const data = await response.json().catch(() => null);
      if (!data) throw new Error(`The compiler service answered with status ${response.status}.`);
      result = data;
      showStatus(data, Math.round(performance.now() - started));
    } catch (error) {
      if (error.name === 'AbortError') return;
      result = null;
      errorLine = null;
      status.className = 'status error';
      status.innerHTML = '<strong>Couldn’t reach the compiler.</strong> Check your connection and compile again.';
    } finally {
      if (request === controller) {
        request = null;
        compileButton.disabled = false;
        panel.classList.remove('stale');
        renderGutter();
        renderPanel();
      }
    }
  }

  function showStatus(data, ms) {
    if (data.ok) {
      errorLine = null;
      status.className = 'status';
      status.textContent = `Compiled in ${ms} ms.`;
      return;
    }
    const { phase, message, line, internal } = data.error;
    errorLine = line;
    status.className = 'status error';
    status.textContent = '';
    const heading = document.createElement('strong');
    const detail = document.createElement('span');
    detail.className = 'detail';
    // The heading already names the line
    detail.textContent = message.replace(/ (at|on) line \d+$/, '');
    if (internal) {
      heading.textContent = `The compiler crashed during ${PHASE_NAMES[phase].toLowerCase()}.`;
      detail.textContent = `This is a bug in the compiler, not in your program. ${message}`;
    } else if (phase === 'request') {
      heading.textContent = 'The program couldn’t be sent.';
    } else {
      heading.textContent = line ? `${PHASE_NAMES[phase]} error on line ${line}` : `${PHASE_NAMES[phase]} error`;
    }
    status.append(heading, detail);
  }

  // ---- Output panels ----

  const escapeHtml = (text) => String(text)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  function renderTokens(tokens) {
    const width = Math.max(...tokens.map((t) => t.type.length));
    return tokens.map((t) => {
      const position = `${t.line}:${t.column}`.padEnd(8);
      const value = t.type === 'EOF' ? '<span class="dim">end of input</span>' : escapeHtml(t.value);
      return `<span class="dim">${position}</span><span class="tok-type">${t.type.padEnd(width + 2)}</span>${value}`;
    }).join('\n');
  }

  function describeNode(node) {
    switch (node.node) {
      case 'FunctionDecl':
        return `FunctionDecl ${node.return_type} ${node.name}(${node.params.map((p) => p.join(' ')).join(', ')})`;
      case 'VarDecl': return `VarDecl ${node.var_type} ${node.name}`;
      case 'ArrayDecl': return `ArrayDecl ${node.var_type} ${node.name}[${node.size ?? ''}]`; // [] when the list gives the size
      case 'InitList': return `InitList {${node.items.length}}`;
      case 'Designated': return `Designated ${node.designators.map(([kind, d]) => kind === 'field' ? '.' + d : '[' + (d.value ?? '…') + ']').join('')} =`;
      case 'BinOp': return `BinOp ${node.op}`;
      case 'UnaryOp': return `UnaryOp ${node.op}`;
      case 'Number': return `Number ${node.value}`;
      case 'Var': return `Var ${node.name}`;
      case 'ArrayAccess': return `ArrayAccess ${node.name}`;
      case 'AssignStmt': return `AssignStmt ${node.name} ${node.op || ''}=`;
      case 'ArrayAssignStmt': return `ArrayAssignStmt ${node.name}[] ${node.op || ''}=`;
      case 'FuncCall': return `FuncCall ${node.name}`;
      case 'StructDecl': return `StructDecl ${node.name} { ${node.fields.map((f) => f.join(' ')).join('; ')} }`;
      case 'Member': return `Member ${node.arrow ? '->' : '.'}${node.field}`;
      case 'Index': return 'Index []';
      case 'LValueAssignStmt': return `LValueAssignStmt ${node.op || ''}=`;
      case 'LValueIncDec': return `LValueIncDec ${node.prefix ? node.op + 'x' : 'x' + node.op}`;
      case 'Deref': return 'Deref *';
      case 'AddressOf': return 'AddressOf &';
      case 'DerefAssignStmt': return `DerefAssignStmt *ptr ${node.op || ''}=`;
      case 'SwitchCase': return node.value === null ? 'default' : 'case';
      case 'IncDec': return `IncDec ${node.prefix ? node.op + node.name : node.name + node.op}`;
      default: return node.node;
    }
  }

  const isNode = (value) => value && typeof value === 'object' && !Array.isArray(value) && 'node' in value;
  // Lists whose items read naturally without a field label
  const UNLABELLED_LISTS = new Set(['declarations', 'statements', 'cases']);

  function childrenOf(node) {
    const children = [];
    for (const [field, value] of Object.entries(node)) {
      if (isNode(value)) {
        children.push({ label: field, node: value });
      } else if (Array.isArray(value) && value.some(isNode)) {
        const label = UNLABELLED_LISTS.has(field) ? null : field.replace(/s$/, '');
        value.forEach((item) => children.push({ label, node: item }));
      }
    }
    return children;
  }

  function renderTree(node, prefix = '', connector = '', label = null) {
    const text = (label ? `<span class="dim">${label}:</span> ` : '') + escapeHtml(describeNode(node));
    const lines = [`<span class="dim">${prefix}${connector}</span>${text}`];
    const childPrefix = prefix + (connector === '├── ' ? '│   ' : connector ? '    ' : '');
    const children = childrenOf(node);
    children.forEach((child, i) => {
      const last = i === children.length - 1;
      lines.push(renderTree(child.node, childPrefix, last ? '└── ' : '├── ', child.label));
    });
    return lines.join('\n');
  }

  const STAGE_LABELS = {
    tokens: 'tokens',
    ast: 'syntax tree',
    tac: 'three-address code',
    llvm: 'LLVM IR',
  };

  function renderPanel() {
    download.hidden = true;
    if (!result) {
      panelNote.textContent = '';
      panel.innerHTML = '<p class="empty">Compiling…</p>';
      return;
    }

    const stage = result.stages[activeStage];
    if (stage === undefined) {
      panelNote.textContent = '';
      const where = result.error && PHASE_NAMES[result.error.phase];
      panel.innerHTML = `<p class="empty">No ${STAGE_LABELS[activeStage]} yet: compilation stopped in the ${escapeHtml((where || 'compiler').toLowerCase())} phase. Fix the error on the left and it will compile again.</p>`;
      return;
    }

    let html;
    if (activeStage === 'tokens') {
      panelNote.textContent = `${stage.length - 1} tokens, with line:column positions`;
      html = renderTokens(stage);
    } else if (activeStage === 'ast') {
      panelNote.textContent = 'As parsed, before optimization';
      html = renderTree(stage);
    } else if (activeStage === 'tac') {
      panelNote.textContent = optimize.checked ? 'After folding constants and removing dead code' : 'Without optimization';
      html = escapeHtml(stage) || '<span class="dim">No functions to translate.</span>';
    } else {
      panelNote.textContent = 'Build it with: clang output.ll -o program';
      html = escapeHtml(stage);
      download.hidden = false;
    }
    panel.innerHTML = `<pre class="listing">${html}</pre>`;
  }

  // ---- Tabs ----

  function selectTab(tab, focus) {
    tabs.forEach((t) => {
      const selected = t === tab;
      t.setAttribute('aria-selected', String(selected));
      t.tabIndex = selected ? 0 : -1;
    });
    panel.setAttribute('aria-labelledby', tab.id);
    activeStage = tab.dataset.stage;
    if (focus) tab.focus();
    renderPanel();
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectTab(tab, false));
    tab.addEventListener('keydown', (event) => {
      const moves = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: tabs.length - 1 };
      if (!(event.key in moves)) return;
      event.preventDefault();
      selectTab(tabs[(moves[event.key] + tabs.length) % tabs.length], true);
    });
  });

  // ---- Controls ----

  download.addEventListener('click', () => {
    const blob = new Blob([result.stages.llvm], { type: 'text/plain' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'output.ll';
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  });

  compileButton.addEventListener('click', compile);
  optimize.addEventListener('change', compile);

  async function loadExample(name) {
    try {
      const response = await fetch(`/examples/${name}`);
      if (!response.ok) throw new Error(String(response.status));
      source.value = await response.text();
    } catch {
      source.value = 'int main() {\n    return 0;\n}\n';
    }
    source.scrollTop = 0;
    errorLine = null;
    renderGutter();
    compile();
  }

  example.addEventListener('change', () => loadExample(example.value));

  renderGutter();
  renderPanel();
  loadExample(example.value);
})();
