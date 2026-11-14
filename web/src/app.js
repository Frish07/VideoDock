import { messages } from './messages.js';
import { asMB, conversionLimit, convertMedia, downloadMedia, formats, MediaError, parseLink, parseTimes } from './media.js';

const byId = (id) => document.getElementById(id);
const key = 'videodock-web-settings';
let settings;
try {
  settings = JSON.parse(localStorage.getItem(key)) || {};
} catch {
  settings = {};
}
if (typeof settings !== 'object' || Array.isArray(settings)) settings = {};
const supportedLanguage = (value) => value === 'ru' || value === 'en';
let language = supportedLanguage(settings.language) ? settings.language :
  /^ru(?:-|$)/i.test(navigator.language) ? 'ru' : 'en';

function saveSettings(changes) {
  Object.assign(settings, changes);
  try {
    localStorage.setItem(key, JSON.stringify(settings));
  } catch {
    // The current settings still work when browser storage is unavailable.
  }
}

function t(name, values = {}) {
  const number = new Intl.NumberFormat(language, { maximumFractionDigits: 2 });
  return messages[language][name].replace(/\{(\w+)\}/g,
    (_, key) => typeof values[key] === 'number' ? number.format(values[key]) : values[key]);
}

const fileInput = byId('file-input');
const fileName = byId('file-name');
const fileLimit = byId('file-limit');
const dropZone = byId('drop-zone');
const formatSelect = byId('format');
const qualitySelect = byId('quality');
let selectedFile;
let active;
const panels = Object.fromEntries(['download', 'convert'].map((name) => [name, {
  name, submit: byId(name + '-submit'), cancel: byId(name + '-cancel'),
  feedback: byId(name + '-feedback'), status: byId(name + '-status'),
  progress: byId(name + '-progress'), save: byId(name + '-save'),
}]));

function qualityOptions(format) {
  if (formats[format].video) {
    return [
      { value: 'original', label: 'original' },
      ...[1080, 720, 480, 360].map((size) => ({ value: String(size), label: 'maxResolution', values: { size } })),
    ];
  }
  if (format === 'wav') return [{ value: 'pcm', label: 'lossless' }];
  return [128, 192, 256, 320].map((rate) => ({ value: String(rate), label: 'kbps', values: { rate } }));
}

function updateQuality(value) {
  const format = formatSelect.value;
  const options = qualityOptions(format);
  qualitySelect.replaceChildren(...options.map(({ value, label, values }) => new Option(t(label, values), value)));
  qualitySelect.value = options.some((option) => option.value === value) ?
    value : format === 'wav' ? 'pcm' : formats[format].video ? 'original' : '192';
  qualitySelect.disabled = options.length === 1;
}

function savedQuality() {
  return formats[formatSelect.value].video ? settings.videoQuality : settings.audioQuality;
}

function showStatus(panel, name, values = {}, kind = '') {
  panel.message = name ? { name, values } : null;
  panel.status.textContent = name ? t(name, values) : '';
  panel.feedback.hidden = !name;
  panel.feedback.dataset.kind = kind;
}

function progress(panel, value) {
  panel.progress.hidden = value === null;
  if (value === undefined || value === null) panel.progress.removeAttribute('value');
  else panel.progress.value = Math.min(1, Math.max(0, value));
}

function clearResult(panel) {
  if (panel.objectURL) URL.revokeObjectURL(panel.objectURL);
  panel.objectURL = null;
  panel.save.removeAttribute('href');
  panel.save.hidden = true;
}

function setResult(panel, { blob, name }) {
  clearResult(panel);
  panel.objectURL = URL.createObjectURL(blob);
  panel.save.href = panel.objectURL;
  panel.save.download = name;
  panel.save.hidden = false;
}

function updateFileLimit() {
  const limit = t('fileLimit', { size: asMB(conversionLimit) });
  fileLimit.textContent = selectedFile?.size > conversionLimit / 2 && selectedFile.size <= conversionLimit ?
    t('largeFile') + ' ' + limit : limit;
}

function translatePage() {
  document.documentElement.lang = language;
  for (const node of document.querySelectorAll('[data-text]')) node.textContent = t(node.dataset.text);
  for (const node of document.querySelectorAll('[data-aria]')) node.setAttribute('aria-label', t(node.dataset.aria));
  for (const node of document.querySelectorAll('[data-placeholder]')) node.placeholder = t(node.dataset.placeholder);
  for (const node of document.querySelectorAll('[data-attr-label]')) node.label = t(node.dataset.attrLabel);
  for (const button of document.querySelectorAll('[data-language]')) {
    button.setAttribute('aria-pressed', String(button.dataset.language === language));
  }
  document.querySelector('meta[name="description"]').content = t('introCopy');
  updateQuality(qualitySelect.value || savedQuality());
  updateFileLimit();
  for (const panel of Object.values(panels)) {
    if (panel.message) panel.status.textContent = t(panel.message.name, panel.message.values);
  }
}

function setActive(operation) {
  active = operation;
  for (const panel of Object.values(panels)) {
    panel.submit.disabled = Boolean(active);
    panel.cancel.hidden = active?.panel !== panel;
  }
  byId('source-url').readOnly = active?.panel === panels.download;
  byId('convert-settings').disabled = active?.panel === panels.convert;
}

async function run(panel, perform) {
  if (active) return;
  const operation = { panel, controller: new AbortController(), canceled: false };
  setActive(operation);
  // Keep at most one large result in memory.
  for (const item of Object.values(panels)) {
    if (item.objectURL) showStatus(item, null);
    clearResult(item);
  }
  showStatus(panel, null);
  progress(panel, null);
  byId('download-desktop').hidden = true;
  try {
    await perform(operation.controller);
  } catch (error) {
    const failure = error instanceof MediaError ? error : new MediaError(panel === panels.download ? 'blocked' : 'convertFailed');
    if (operation.canceled) showStatus(panel, 'canceled');
    else {
      showStatus(panel, failure.key, failure.values, 'error');
      if (panel === panels.download && ['platform', 'blocked', 'notMedia', 'httpError'].includes(failure.key)) {
        byId('download-desktop').hidden = false;
      }
    }
  } finally {
    progress(panel, null);
    setActive(null);
  }
}

for (const panel of Object.values(panels)) {
  panel.cancel.addEventListener('click', () => {
    if (active?.panel === panel) {
      active.canceled = true;
      active.controller.abort();
    }
  });
}

for (const button of document.querySelectorAll('[data-language]')) {
  button.addEventListener('click', () => {
    language = button.dataset.language;
    saveSettings({ language });
    translatePage();
  });
}

if (Object.hasOwn(formats, settings.format)) formatSelect.value = settings.format;
formatSelect.addEventListener('change', () => {
  saveSettings({ format: formatSelect.value });
  updateQuality(savedQuality());
});
qualitySelect.addEventListener('change', () => {
  const property = formats[formatSelect.value].video ? 'videoQuality' : 'audioQuality';
  saveSettings({ [property]: qualitySelect.value });
});

byId('download-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const panel = panels.download;
  run(panel, async (controller) => {
    const url = parseLink(byId('source-url').value);
    showStatus(panel, 'checking');
    progress(panel, undefined);
    let lastUpdate = 0;
    const result = await downloadMedia(url, controller, (size, total) => {
      if (Date.now() - lastUpdate < 100) return;
      lastUpdate = Date.now();
      showStatus(panel, total ? 'downloading' : 'downloadingUnknown', { loaded: asMB(size), total: asMB(total) });
      progress(panel, total ? size / total : undefined);
    });
    setResult(panel, result);
    showStatus(panel, 'downloaded', { size: asMB(result.blob.size) }, 'success');
    panel.save.click();
  });
});

function setFile(file) {
  if (active?.panel === panels.convert) return;
  selectedFile = file;
  fileName.textContent = file?.name || '';
  fileName.hidden = !file;
  updateFileLimit();
  clearResult(panels.convert);
  if (file?.size > conversionLimit) {
    showStatus(panels.convert, 'tooLarge', { size: asMB(conversionLimit) }, 'error');
  } else {
    showStatus(panels.convert, null);
  }
}

fileInput.addEventListener('change', () => {
  if (fileInput.files.length) {
    setFile(fileInput.files[0]);
    fileInput.value = '';
  }
});
for (const type of ['dragenter', 'dragover', 'dragleave', 'drop']) {
  dropZone.addEventListener(type, (event) => {
    event.preventDefault();
    dropZone.classList.toggle('dragging', ['dragenter', 'dragover'].includes(type) && active?.panel !== panels.convert);
    if (type === 'drop' && event.dataTransfer.files.length) setFile(event.dataTransfer.files[0]);
  });
}

byId('convert-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const panel = panels.convert;
  run(panel, async (controller) => {
    const range = parseTimes(byId('start').value, byId('end').value);
    let previousStage;
    const result = await convertMedia(selectedFile, formatSelect.value, qualitySelect.value, range,
      controller.signal, (stage, amount) => {
        if (stage !== previousStage) {
          showStatus(panel, stage);
          previousStage = stage;
        }
        progress(panel, amount);
      });
    setResult(panel, result);
    showStatus(panel, 'converted', { name: result.name, size: asMB(result.blob.size) }, 'success');
  });
});

window.addEventListener('pagehide', (event) => {
  if (!event.persisted) {
    active?.controller.abort();
    for (const panel of Object.values(panels)) clearResult(panel);
  }
});

translatePage();
