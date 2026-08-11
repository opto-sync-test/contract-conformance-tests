import path from 'node:path';
import { pathToFileURL } from 'node:url';

const clientsRoot = process.env.OPTO_SYNC_CLIENTS_DIR;
if (!clientsRoot) throw new Error('OPTO_SYNC_CLIENTS_DIR is required');

const { createTelemetryEvent } = await import(pathToFileURL(path.join(
  clientsRoot,
  'clients',
  'ts',
  'dist',
  'esm',
  'telemetry.js',
)));
const telemetry = createTelemetryEvent('opto_sync.sync.cycle_succeeded', 'info', {
  operation: 'protocolSyncCycle',
  checkpoint: '9',
  pushedMutations: 2,
  acknowledgedMutations: 2,
  pulledChanges: 1,
  installedSnapshots: 0,
  hasMorePending: false,
});

process.stdout.write(`${JSON.stringify({ runtime: 'typescript', telemetry })}\n`);
