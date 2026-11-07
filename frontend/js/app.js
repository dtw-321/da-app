/* DTAnalitycs Web Studio — Vue 3 (CDN, Composition API), tanpa build step. */
const { createApp, ref, reactive, computed, onMounted, watch } = Vue;

const API = '/api/workflow';
const NODE_W = 176, NODE_H = 96, CANVAS_SIZE = 4000;
const CATEGORY_LABEL = { sources: 'Data Sources', transforms: 'Transformations', exports: 'Exports' };
const STORAGE_KEY = 'dtanalitycs-studio-graph';

createApp({
  setup() {
    const specs = ref([]), nodes = ref([]), connections = ref([]);
    const selectedId = ref(null), results = ref({}), nodeStatus = ref({}), logs = ref([]);
    const running = ref(false), search = ref(''), scale = ref(1), showLogs = ref(true);
    const workflowId = ref(null), workflowName = ref('Untitled Workflow');
    const linking = ref(null), pointer = reactive({ x: 0, y: 0 }), toast = ref(null);
    const preview = reactive({ open: false, title: '', columns: [], rows: [], total: 0, truncated: false });
    const pythonModal = reactive({ open: false, code: '' });
    const openModal = reactive({ open: false, items: [] });
    let drag = null, toastTimer = null;

    /* ---------------- helpers ---------------- */
    const notify = (message, type = 'info') => {
      toast.value = { message, type };
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => (toast.value = null), 3200);
    };
    const api = async (path, options = {}) => {
      const res = await fetch(API + path, options);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText);
      return data;
    };
    const postJson = (path, body) => api(path, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    });
    const canvasPoint = (evt) => {
      const rect = document.getElementById('canvas').getBoundingClientRect();
      return { x: (evt.clientX - rect.left) / scale.value, y: (evt.clientY - rect.top) / scale.value };
    };
    const payload = (targetNodeId = null) => ({
      workflowId: workflowId.value, workflowName: workflowName.value,
      nodes: nodes.value, connections: connections.value, targetNodeId
    });

    /* ---------------- computed ---------------- */
    const selectedNode = computed(() => nodes.value.find(n => n.id === selectedId.value) || null);
    const selectedSchema = computed(() => {
      if (!selectedNode.value) return [];
      const spec = specs.value.find(s => s.type === selectedNode.value.type);
      return spec ? spec.config_schema : [];
    });
    const categories = computed(() => {
      const keyword = search.value.toLowerCase();
      const groups = [];
      Object.keys(CATEGORY_LABEL).forEach(key => {
        const items = specs.value.filter(s => s.category === key &&
          (s.title.toLowerCase().includes(keyword) || s.type.includes(keyword)));
        if (items.length) groups.push({ name: key, label: CATEGORY_LABEL[key], items });
      });
      return groups;
    });
    const outPoint = (n) => ({ x: n.x + NODE_W / 2, y: n.y + NODE_H });
    const inPoint = (n) => ({ x: n.x + NODE_W / 2, y: n.y });
    const bezier = (a, b) => {
      const dy = Math.max(40, Math.abs(b.y - a.y) / 2);
      return `M ${a.x} ${a.y} C ${a.x} ${a.y + dy}, ${b.x} ${b.y - dy}, ${b.x} ${b.y}`;
    };
    const pathFor = (conn) => {
      const from = nodes.value.find(n => n.id === conn.fromNodeId);
      const to = nodes.value.find(n => n.id === conn.toNodeId);
      return from && to ? bezier(outPoint(from), inPoint(to)) : '';
    };
    const tempPath = computed(() => {
      const from = nodes.value.find(n => n.id === linking.value);
      return from ? bezier(outPoint(from), pointer) : '';
    });

    /* ---------------- graph editing ---------------- */
    const addNode = (spec, x, y) => {
      const config = {};
      (spec.config_schema || []).forEach(f => { config[f.name] = f.default !== undefined ? f.default : ''; });
      const node = {
        id: 'n_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
        type: spec.type, title: spec.title, x: Math.max(0, x), y: Math.max(0, y), config
      };
      nodes.value.push(node);
      selectedId.value = node.id;
    };
    const onCatalogDragStart = (evt, spec) => evt.dataTransfer.setData('text/plain', spec.type);
    const onCanvasDrop = (evt) => {
      const spec = specs.value.find(s => s.type === evt.dataTransfer.getData('text/plain'));
      if (!spec) return;
      const p = canvasPoint(evt);
      addNode(spec, p.x - NODE_W / 2, p.y - 20);
    };
    const addNodeCenter = (spec) => addNode(spec, 120 + Math.random() * 200, 80 + Math.random() * 200);

    const onNodeMouseDown = (evt, node) => {
      selectedId.value = node.id;
      const p = canvasPoint(evt);
      drag = { id: node.id, dx: p.x - node.x, dy: p.y - node.y };
    };
    const onCanvasMouseDown = () => { selectedId.value = null; linking.value = null; };
    const onMouseMove = (evt) => {
      if (!drag && !linking.value) return;
      const p = canvasPoint(evt);
      pointer.x = p.x; pointer.y = p.y;
      if (drag) {
        const node = nodes.value.find(n => n.id === drag.id);
        if (node) { node.x = Math.max(0, p.x - drag.dx); node.y = Math.max(0, p.y - drag.dy); }
      }
    };
    const onMouseUp = () => { drag = null; };

    const createsCycle = (fromId, toId) => {
      const stack = [toId], seen = new Set();
      while (stack.length) {
        const cur = stack.pop();
        if (cur === fromId) return true;
        if (seen.has(cur)) continue;
        seen.add(cur);
        connections.value.filter(c => c.fromNodeId === cur).forEach(c => stack.push(c.toNodeId));
      }
      return false;
    };
    const onPortOut = (node) => { linking.value = node.id; };
    const onPortIn = (node) => {
      const from = linking.value;
      linking.value = null;
      if (!from || from === node.id) return;
      if (connections.value.some(c => c.fromNodeId === from && c.toNodeId === node.id)) return notify('Koneksi sudah ada', 'error');
      if (createsCycle(from, node.id)) return notify('Koneksi ditolak: membentuk siklus', 'error');
      const usedPorts = connections.value.filter(c => c.toNodeId === node.id).map(c => c.toPort || 0);
      const toPort = usedPorts.length ? Math.max(...usedPorts) + 1 : 0;
      connections.value.push({ fromNodeId: from, toNodeId: node.id, fromPort: 0, toPort });
    };
    const removeConnection = (index) => connections.value.splice(index, 1);
    const removeNode = (id) => {
      nodes.value = nodes.value.filter(n => n.id !== id);
      connections.value = connections.value.filter(c => c.fromNodeId !== id && c.toNodeId !== id);
      if (selectedId.value === id) selectedId.value = null;
    };
    const clearCanvas = () => {
      if (!confirm('Kosongkan canvas?')) return;
      nodes.value = []; connections.value = []; results.value = {}; nodeStatus.value = {};
      logs.value = []; selectedId.value = null; workflowId.value = null;
    };

    /* ---------------- execution ---------------- */
    const run = async (targetNodeId = null) => {
      if (running.value) return null;
      if (!nodes.value.length) { notify('Canvas masih kosong', 'error'); return null; }
      running.value = true;
      try {
        const data = await postJson('/run', payload(targetNodeId));
        results.value = data.outputs || {};
        nodeStatus.value = data.nodeStatus || {};
        logs.value = data.logs || [];
        showLogs.value = true;
        notify(data.status === 'success' ? `Selesai dalam ${data.durationMs} ms` : 'Eksekusi selesai dengan error',
          data.status === 'success' ? 'success' : 'error');
        return data;
      } catch (err) {
        notify(err.message, 'error');
        logs.value = [{ level: 'error', message: err.message }];
        return null;
      } finally { running.value = false; }
    };
    const openPreview = (id) => {
      const out = results.value[id];
      const node = nodes.value.find(n => n.id === id);
      if (!out) return notify('Node belum dieksekusi', 'error');
      Object.assign(preview, {
        open: true, title: node ? node.title : id, columns: out.columns || [],
        rows: out.data || [], total: out.totalRows || 0, truncated: !!out.truncated
      });
    };
    const viewNode = async (id) => { if (!results.value[id]) await run(id); openPreview(id); };
    const hasFile = (id) => !!(results.value[id] && (results.value[id].files || []).length);
    const downloadNode = (id) => {
      const files = (results.value[id] || {}).files || [];
      if (files.length) window.open(files[0].url, '_blank');
    };
    const statusOf = (id) => (nodeStatus.value[id] || {}).status || 'idle';
    const nodeClass = (n) => [statusOf(n.id), { selected: selectedId.value === n.id }];
    const fmt = (v) => (v === null || v === undefined ? '—' : (typeof v === 'object' ? JSON.stringify(v) : v));

    /* ---------------- persistence ---------------- */
    const saveWorkflow = async () => {
      try {
        const data = await postJson('/save', payload());
        workflowId.value = data.id;
        notify('Workflow tersimpan', 'success');
      } catch (err) { notify(err.message, 'error'); }
    };
    const openList = async () => {
      try { openModal.items = await api('/list'); openModal.open = true; }
      catch (err) { notify(err.message, 'error'); }
    };
    const loadWorkflow = async (id) => {
      try {
        const data = await api('/load/' + id);
        nodes.value = (data.graph_data || {}).nodes || [];
        connections.value = (data.graph_data || {}).connections || [];
        workflowName.value = data.name; workflowId.value = data.id;
        results.value = {}; nodeStatus.value = {}; openModal.open = false;
        notify('Workflow dimuat', 'success');
      } catch (err) { notify(err.message, 'error'); }
    };
    const exportJson = () => {
      const blob = new Blob([JSON.stringify(payload(), null, 2)], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = (workflowName.value || 'workflow').replace(/\s+/g, '_') + '.json';
      a.click(); URL.revokeObjectURL(a.href);
    };
    const importJson = (evt) => {
      const file = evt.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const data = JSON.parse(reader.result);
          if (!Array.isArray(data.nodes)) throw new Error('Format JSON tidak valid');
          nodes.value = data.nodes; connections.value = data.connections || [];
          workflowName.value = data.workflowName || 'Imported Workflow';
          results.value = {}; nodeStatus.value = {};
          notify('Workflow diimport', 'success');
        } catch (err) { notify(err.message, 'error'); }
      };
      reader.readAsText(file);
      evt.target.value = '';
    };
    const generatePython = async () => {
      try {
        const data = await postJson('/generate-python', payload());
        pythonModal.code = data.code; pythonModal.open = true;
      } catch (err) { notify(err.message, 'error'); }
    };
    const copyPython = () => {
      navigator.clipboard.writeText(pythonModal.code).then(() => notify('Script disalin', 'success'));
    };
    const onUpload = async (evt, field) => {
      const file = evt.target.files[0];
      if (!file || !selectedNode.value) return;
      const form = new FormData();
      form.append('file', file);
      try {
        const res = await fetch(API + '/upload', { method: 'POST', body: form });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Upload gagal');
        selectedNode.value.config[field.target || 'filePath'] = data.filePath;
        notify('File terupload: ' + data.fileName, 'success');
      } catch (err) { notify(err.message, 'error'); }
      evt.target.value = '';
    };

    /* ---------------- lifecycle ---------------- */
    onMounted(async () => {
      try { specs.value = await api('/specs'); }
      catch (err) { notify('Gagal memuat katalog node: ' + err.message, 'error'); }
      const cached = localStorage.getItem(STORAGE_KEY);
      if (cached) {
        try {
          const data = JSON.parse(cached);
          nodes.value = data.nodes || []; connections.value = data.connections || [];
          workflowName.value = data.workflowName || 'Untitled Workflow';
        } catch (e) { /* abaikan cache rusak */ }
      }
      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('mouseup', onMouseUp);
      window.addEventListener('keydown', (evt) => {
        const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName);
        if (evt.key === 'Escape') { linking.value = null; preview.open = false; pythonModal.open = false; openModal.open = false; }
        if (evt.key === 'Delete' && !typing && selectedId.value) removeNode(selectedId.value);
        if ((evt.ctrlKey || evt.metaKey) && evt.key.toLowerCase() === 's') { evt.preventDefault(); saveWorkflow(); }
      });
    });
    watch([nodes, connections, workflowName], () => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload()));
    }, { deep: true });

    return {
      specs, nodes, connections, selectedId, selectedNode, selectedSchema, results, nodeStatus, logs,
      running, search, scale, showLogs, workflowName, workflowId, linking, pointer, toast, preview,
      pythonModal, openModal, categories, tempPath, canvasSize: CANVAS_SIZE,
      onCatalogDragStart, onCanvasDrop, addNodeCenter, onNodeMouseDown, onCanvasMouseDown,
      onPortOut, onPortIn, removeNode, removeConnection, clearCanvas, pathFor, nodeClass, statusOf,
      run, viewNode, hasFile, downloadNode, fmt, saveWorkflow, openList, loadWorkflow,
      exportJson, importJson, generatePython, copyPython, onUpload
    };
  }
}).mount('#app');
