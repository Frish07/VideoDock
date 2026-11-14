import { cp, lstat, mkdir, realpath, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = new URL('./', import.meta.url);
const dist = new URL('dist/', root);
const existing = await lstat(dist).catch((error) => {
  if (error.code !== 'ENOENT') throw error;
  return null;
});
if (existing && (!existing.isDirectory() || existing.isSymbolicLink() ||
    await realpath(dist) !== join(await realpath(root), 'dist'))) {
  throw new Error('Expected a local web/dist directory');
}
await rm(dist, { recursive: true, force: true });
await mkdir(new URL('ffmpeg/core/', dist), { recursive: true });

for (const file of ['index.html', 'styles.css', 'app.js', 'messages.js', 'media.js', 'videodock.ico']) {
  const source = file === 'videodock.ico' ? '../assets/videodock.ico' : `src/${file}`;
  await cp(new URL(source, root), new URL(file, dist));
}

for (const [source, destination] of [
  ['ffmpeg/dist/esm', 'ffmpeg'],
  ['core/dist/esm', 'ffmpeg/core'],
]) {
  await cp(new URL(`node_modules/@ffmpeg/${source}/`, root), new URL(`${destination}/`, dist), {
    recursive: true,
    filter: (path) => !/\.(map|ts)$/.test(path),
  });
}

await writeFile(new URL('.nojekyll', dist), '');
await cp(new URL('THIRD_PARTY_NOTICES.txt', root), new URL('THIRD_PARTY_NOTICES.txt', dist));
console.log(`Static site: ${fileURLToPath(dist)}`);
