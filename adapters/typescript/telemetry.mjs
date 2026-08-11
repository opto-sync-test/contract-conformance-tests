import path from 'node:path';
import { pathToFileURL } from 'node:url';

const clientsRoot = process.env.OPTO_SYNC_CLIENTS_DIR;
if (!clientsRoot) throw new Error('OPTO_SYNC_CLIENTS_DIR is required');

const { createProtocolSyncTelemetryRecord } = await import(pathToFileURL(path.join(
  clientsRoot,
  'clients',
  'ts',
  'dist',
  'esm',
  'observability.js',
)));
const { emitProtocolSyncTelemetry } = await import(pathToFileURL(path.join(
  clientsRoot,
  'clients',
  'ts',
  'dist',
  'esm',
  'telemetry.js',
)));
const input = {
  runtime: 'typescript',
  kind: 'state.changed',
  status: 'idle',
  timestamp: '2026-08-11T17:53:28.151Z',
  requestId: 'sync-cycle-42',
};
const telemetry = createProtocolSyncTelemetryRecord(input);
let emitted;
await emitProtocolSyncTelemetry((record) => { emitted = record; }, input);
if (JSON.stringify(emitted) !== JSON.stringify(telemetry)) {
  throw new Error('TypeScript fail-open sink changed the canonical record');
}

process.stdout.write(`${JSON.stringify({ runtime: 'typescript', telemetry })}\n`);
