import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const clientsRoot = process.env.OPTO_SYNC_CLIENTS_DIR;
if (!clientsRoot) {
  throw new Error('OPTO_SYNC_CLIENTS_DIR is required');
}

const modulePath = path.join(
  clientsRoot,
  'clients',
  'ts',
  'dist',
  'esm',
  'schema',
  'ingest.js',
);
const { parseEnvelope } = await import(pathToFileURL(modulePath));
const { compareHlc, formatHlc, parseHlc } = await import(pathToFileURL(path.join(
  clientsRoot,
  'clients',
  'ts',
  'dist',
  'esm',
  'clock.js',
)));
const decisions = {};

for (const fixturePath of process.argv.slice(2)) {
  const key = `${path.basename(path.dirname(fixturePath))}/${path.basename(fixturePath)}`;
  try {
    await parseEnvelope(fs.readFileSync(fixturePath, 'utf8'));
    decisions[key] = true;
  } catch {
    decisions[key] = false;
  }
}

const formatted = formatHlc({ millis: 1721822400000, counter: 255, nodeId: '9f3a2b' });
const hlc = {
  formatted,
  parsed: parseHlc(formatted),
  compared: compareHlc(formatted, '1721822400001-0000-9f3a2b'),
};

process.stdout.write(`${JSON.stringify({ runtime: 'typescript', decisions, hlc })}\n`);
