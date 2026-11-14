const MiB = 1024 ** 2;
const memory = navigator.deviceMemory || 4;
const mobile = /Android|iPhone|iPad/i.test(navigator.userAgent);
export const conversionLimit = (memory <= 2 || mobile ? 64 : memory <= 4 ? 128 : 192) * MiB;
const downloadLimit = (memory <= 2 || mobile ? 96 : 256) * MiB;

export const formats = {
  mp4: { type: 'video/mp4', video: ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p'],
         audio: ['-c:a', 'aac', '-b:a', '160k'], options: ['-movflags', '+faststart'] },
  webm: { type: 'video/webm', video: ['-c:v', 'libvpx', '-deadline', 'realtime', '-cpu-used', '5', '-crf', '24', '-b:v', '1M', '-pix_fmt', 'yuv420p'],
          audio: ['-c:a', 'libvorbis', '-b:a', '128k'], options: [] },
  mp3: { type: 'audio/mpeg', audio: ['-c:a', 'libmp3lame'] },
  m4a: { type: 'audio/mp4', audio: ['-c:a', 'aac'] },
  wav: { type: 'audio/wav', audio: ['-c:a', 'pcm_s16le'] },
};

const mediaExtensions = new Set(['mp4', 'm4v', 'webm', 'mov', 'mkv', 'avi', 'mp3', 'm4a', 'aac', 'wav', 'ogg', 'ogv', 'opus', 'flac']);
const mimeExtensions = {
  'video/mp4': 'mp4', 'video/webm': 'webm', 'video/quicktime': 'mov', 'video/x-matroska': 'mkv',
  'video/x-msvideo': 'avi', 'video/ogg': 'ogv', 'audio/mpeg': 'mp3', 'audio/mp4': 'm4a',
  'audio/aac': 'aac', 'audio/wav': 'wav', 'audio/x-wav': 'wav', 'audio/webm': 'webm',
  'audio/ogg': 'ogg', 'application/ogg': 'ogg', 'audio/flac': 'flac', 'audio/opus': 'opus',
};

export class MediaError extends Error {
  constructor(key, values = {}) {
    super(key);
    this.key = key;
    this.values = values;
  }
}

export function asMB(bytes) {
  return bytes / MiB;
}

function platform(url) {
  const host = url.hostname;
  const match = (domain) => host === domain || host.endsWith('.' + domain);
  if (match('youtube.com') || match('youtu.be') || match('youtube-nocookie.com')) return 'YouTube';
  if (match('tiktok.com') || match('tiktokv.com')) return 'TikTok';
  if (match('instagram.com') || match('instagr.am')) return 'Instagram';
  if (match('facebook.com') || match('fb.com') || match('fb.watch')) return 'Facebook';
  return null;
}

export function parseLink(value) {
  let url;
  try {
    url = new URL(value.trim());
  } catch {
    throw new MediaError('badUrl');
  }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw new MediaError('badUrl');
  const site = platform(url);
  if (site) throw new MediaError('platform', { site });
  if (location.protocol === 'https:' && url.protocol !== 'https:') throw new MediaError('insecureUrl');
  return url;
}

function filenameFrom(response) {
  const disposition = response.headers.get('Content-Disposition') || '';
  const encoded = disposition.match(/filename\*\s*=\s*UTF-8'[^']*'([^;]+)/i)?.[1];
  const plain = disposition.match(/filename\s*=\s*(?:"([^"]+)"|([^;]+))/i);
  const path = new URL(response.url).pathname.split('/').pop();
  try {
    return encoded ? decodeURIComponent(encoded) : plain?.[1] || plain?.[2] || decodeURIComponent(path);
  } catch {
    return plain?.[1] || plain?.[2] || path;
  }
}

function safeFilename(name) {
  return name.replace(/[\u0000-\u001f\u007f\u202a-\u202e\u2066-\u2069<>:"/\\|?*]/g, '_')
    .trim().replace(/^[. ]+|[. ]+$/g, '');
}

function downloadName(name, extension) {
  const base = safeFilename(name.replace(/\.[^.]+$/, '')).slice(0, 120) || 'videodock';
  return base + '.' + extension;
}

// Detect common media containers when a server responds with a generic MIME type.
function sniff(bytes) {
  const ascii = (start, end) => String.fromCharCode(...bytes.subarray(start, end));
  if (ascii(4, 8) === 'ftyp') return ascii(8, 12).startsWith('qt') ? 'mov' : ascii(8, 12) === 'M4A ' ? 'm4a' : 'mp4';
  if (ascii(0, 4) === 'RIFF') {
    if (ascii(8, 12) === 'WAVE') return 'wav';
    if (ascii(8, 12) === 'AVI ') return 'avi';
  }
  if (bytes[0] === 0x1a && bytes[1] === 0x45 && bytes[2] === 0xdf && bytes[3] === 0xa3) {
    return ascii(0, Math.min(64, bytes.length)).includes('webm') ? 'webm' : 'mkv';
  }
  if (ascii(0, 4) === 'OggS') {
    const header = ascii(0, Math.min(64, bytes.length));
    if (header.includes('OpusHead')) return 'opus';
    return header.includes('theora') ? 'ogv' : 'ogg';
  }
  if (ascii(0, 4) === 'fLaC') return 'flac';
  if (ascii(0, 3) === 'ID3') return 'mp3';
  if (bytes[0] === 0xff && (bytes[1] & 0xf6) === 0xf0) return 'aac';
  if (bytes[0] === 0xff && (bytes[1] & 0xe6) >= 0xe2) return 'mp3';
  return null;
}

export async function downloadMedia(url, controller, onProgress) {
  let reader;
  let timer;
  let timedOut = false;
  function resetTimer() {
    clearTimeout(timer);
    timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, 30_000);
  }
  try {
    resetTimer();
    const response = await fetch(url, { signal: controller.signal, mode: 'cors', credentials: 'omit', referrerPolicy: 'no-referrer' });
    const finalSite = platform(new URL(response.url));
    if (finalSite) throw new MediaError('platform', { site: finalSite });
    if (!response.ok) throw new MediaError('httpError', { code: response.status });
    const type = (response.headers.get('Content-Type') || '').split(';')[0].trim().toLowerCase();
    // Manifests and HTML pages are not standalone media files.
    if (type && !/^(video|audio)\//.test(type) &&
        !['application/octet-stream', 'binary/octet-stream', 'application/ogg', 'application/mp4'].includes(type)) {
      throw new MediaError('notMedia');
    }
    if (/mpegurl|dash\+xml/i.test(type)) throw new MediaError('notMedia');
    const total = Number(response.headers.get('Content-Length')) || 0;
    if (total > downloadLimit) throw new MediaError('downloadLimit', { size: asMB(downloadLimit) });
    if (!response.body) throw new MediaError('notMedia');

    const name = filenameFrom(response);
    const declaredExtension = name.split('.').pop().toLowerCase();
    const chunks = [];
    const firstBytes = new Uint8Array(64);
    let headerSize = 0;
    let size = 0;
    let extension = mimeExtensions[type];
    reader = response.body.getReader();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      resetTimer();
      size += value.byteLength;
      if (size > downloadLimit) throw new MediaError('downloadLimit', { size: asMB(downloadLimit) });
      if (headerSize < firstBytes.length) {
        const prefix = value.subarray(0, firstBytes.length - headerSize);
        firstBytes.set(prefix, headerSize);
        headerSize += prefix.length;
        if (headerSize === firstBytes.length && !extension) extension = sniff(firstBytes);
        if (headerSize === firstBytes.length && !extension && !/^(video|audio)\//.test(type)) {
          throw new MediaError('notMedia');
        }
      }
      chunks.push(value);
      onProgress(size, total);
    }
    extension ||= sniff(firstBytes.subarray(0, headerSize));
    if (!extension && /^(video|audio)\//.test(type) && mediaExtensions.has(declaredExtension)) extension = declaredExtension;
    if (!size || !extension) throw new MediaError('notMedia');
    return { blob: new Blob(chunks, { type: type || 'application/octet-stream' }), name: downloadName(name, extension) };
  } catch (error) {
    if (timedOut) throw new MediaError('requestTimeout');
    if (error instanceof MediaError || controller.signal.aborted) throw error;
    if (error instanceof RangeError) throw new MediaError('noMemory');
    throw new MediaError('blocked');
  } finally {
    clearTimeout(timer);
    if (reader) {
      await reader.cancel().catch(() => {});
      reader.releaseLock();
    }
    // Cancel an unread response as well, such as an HTTP error or an oversize file.
    controller.abort();
  }
}

export function parseTimes(rawStart, rawEnd) {
  function parse(value) {
    const normalized = value.trim().replace(',', '.');
    if (!normalized) return null;
    if (!/^\d+(?::\d{1,2}){0,2}(?:\.\d{1,3})?$/.test(normalized)) throw new MediaError('badTime');
    const parts = normalized.split(':').map(Number);
    const seconds = parts.reduce((sum, part) => sum * 60 + part, 0);
    if (parts.slice(1).some((part) => part >= 60) || !Number.isFinite(seconds)) throw new MediaError('badTime');
    return seconds;
  }
  const start = parse(rawStart) ?? 0;
  const end = parse(rawEnd);
  if (end !== null && end <= start) throw new MediaError('badRange');
  return { start, end };
}

function readLocalFile(file, signal) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    const abort = () => reader.abort();
    signal.addEventListener('abort', abort, { once: true });
    reader.onloadend = () => signal.removeEventListener('abort', abort);
    reader.onload = () => resolve(new Uint8Array(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.onabort = () => reject(signal.reason);
    reader.readAsArrayBuffer(file);
  });
}

export async function convertMedia(file, extension, quality, range, signal, update) {
  if (typeof WebAssembly === 'undefined' || typeof Worker === 'undefined') throw new MediaError('unsupportedBrowser');
  if (!file?.size) throw new MediaError('notFile');
  if (file.size > conversionLimit) throw new MediaError('tooLarge', { size: asMB(conversionLimit) });

  const format = formats[extension];
  let ffmpeg;
  let stage = 'loadingCore';
  let expectedDuration;
  let diagnostic = '';
  let timer;
  const stop = () => ffmpeg?.terminate();
  signal.addEventListener('abort', stop, { once: true });
  try {
    update(stage);
    const { FFmpeg } = await import('./ffmpeg/index.js');
    signal.throwIfAborted();
    ffmpeg = new FFmpeg();
    ffmpeg.on('log', ({ message }) => { diagnostic = (diagnostic + '\n' + message).slice(-3500); });
    ffmpeg.on('progress', ({ time }) => {
      if (stage === 'converting' && expectedDuration > 0 && time >= 0) {
        update(stage, Math.min(.99, time / 1_000_000 / expectedDuration));
      }
    });
    const asset = (name) => new URL('./ffmpeg/core/' + name, import.meta.url).href;
    await Promise.race([
      ffmpeg.load({ coreURL: asset('ffmpeg-core.js'), wasmURL: asset('ffmpeg-core.wasm') }),
      new Promise((_, reject) => { timer = setTimeout(() => reject(new MediaError('loadFailed')), 120_000); }),
    ]);
    clearTimeout(timer);
    signal.throwIfAborted();

    stage = 'reading';
    update(stage);
    await ffmpeg.writeFile('input.media', await readLocalFile(file, signal));
    await ffmpeg.ffprobe(['-v', 'error', '-protocol_whitelist', 'file',
      '-show_entries', 'format=duration:stream=index,codec_type:stream_disposition=attached_pic',
      '-of', 'json', '-o', 'probe.json', 'input.media']);
    const metadata = JSON.parse(await ffmpeg.readFile('probe.json', 'utf8'));
    if (!metadata.streams?.length) throw new MediaError('unreadable');
    const video = metadata.streams.find((stream) => stream.codec_type === 'video' && !stream.disposition?.attached_pic);
    const audio = metadata.streams.find((stream) => stream.codec_type === 'audio');
    if (format.video && !video) throw new MediaError('noVideo');
    if (!format.video && !audio) throw new MediaError('noAudio');
    const { start, end } = range;
    const duration = Number(metadata.format?.duration);
    if (duration > 0 && (start >= duration || (end !== null && end > duration + .05))) throw new MediaError('timeOutside');
    expectedDuration = (end ?? duration) - start;

    const output = 'result.' + extension;
    const args = ['-hide_banner', '-loglevel', 'warning', '-protocol_whitelist', 'file', '-threads', '1',
      '-i', 'input.media', '-map_metadata', '-1', '-map_chapters', '-1', '-threads', '1'];
    if (start) args.push('-ss', String(start));
    if (end !== null) args.push('-t', String(end - start));
    if (format.video) {
      args.push('-map', '0:' + video.index, ...format.video);
      const edge = quality === 'original' ? '' : "if(gt(iw,ih),min(ih," + quality + "),min(iw," + quality + "))";
      const scale = edge ? "scale='if(gt(iw,ih),-2," + edge + ")':'if(gt(iw,ih)," + edge + ",-2)'," : '';
      args.push('-vf', scale + 'pad=ceil(iw/2)*2:ceil(ih/2)*2', ...format.options);
    }
    if (audio) args.push('-map', '0:' + audio.index, ...format.audio);
    if (!format.video && extension !== 'wav') args.push('-b:a', quality + 'k');
    // Leave room for the input, FFmpeg's memory and a copy of the output.
    const maxOutput = conversionLimit + MiB;
    args.push('-fs', String(maxOutput), output);

    stage = 'converting';
    update(stage, 0);
    if (await ffmpeg.exec(args) !== 0) throw new Error('FFmpeg failed');
    update('saving');
    const data = await ffmpeg.readFile(output);
    if (data.byteLength >= conversionLimit) throw new MediaError('tooLarge', { size: asMB(conversionLimit) });
    if (!data.byteLength) throw new MediaError('convertFailed');
    return { blob: new Blob([data], { type: format.type }), name: downloadName(file.name, extension) };
  } catch (error) {
    if (signal.aborted) throw signal.reason;
    if (error instanceof MediaError) throw error;
    if (/out of memory|cannot (?:allocate|enlarge) memory|allocation failed|Array buffer allocation/i.test(diagnostic + '\n' + error)) {
      throw new MediaError('noMemory');
    }
    throw new MediaError(stage === 'loadingCore' ? 'loadFailed' : stage === 'reading' ? 'unreadable' : 'convertFailed');
  } finally {
    clearTimeout(timer);
    signal.removeEventListener('abort', stop);
    stop();
  }
}
