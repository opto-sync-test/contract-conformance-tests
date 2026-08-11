#!/usr/bin/env node
import childProcess from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const lock = JSON.parse(fs.readFileSync(path.join(root, 'contract', 'source-lock.json'), 'utf8'));
const sdkLock = JSON.parse(
  fs.readFileSync(path.join(root, 'contract', 'sdk-source-lock.json'), 'utf8'),
);
const args = new Set(process.argv.slice(2));
const prepare = args.has('--prepare');
const requireTelemetry = args.has('--require-telemetry');
const requested = process.argv
  .slice(2)
  .find((value) => value.startsWith('--languages='))
  ?.slice('--languages='.length)
  .split(',')
  .filter(Boolean) ?? ['rust', 'typescript', 'dart'];
const allowed = new Set(['rust', 'typescript', 'dart']);
if (requested.length === 0 || requested.some((runtime) => !allowed.has(runtime))) {
  throw new Error(`unsupported runtime selection: ${requested.join(',')}`);
}

const clientsRoot = path.resolve(
  process.env.OPTO_SYNC_CLIENTS_DIR ?? path.join(root, 'vendor', 'opto-sync-clients'),
);
const sourceSchema = path.join(clientsRoot, lock.source.path);
const vendoredSchema = path.join(root, 'contract', 'opto-sync-envelope.schema.json');

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function run(command, commandArgs, options = {}) {
  const result = childProcess.spawnSync(command, commandArgs, {
    cwd: options.cwd ?? root,
    env: { ...process.env, OPTO_SYNC_CLIENTS_DIR: clientsRoot, ...options.env },
    encoding: 'utf8',
    stdio: options.capture ? ['ignore', 'pipe', 'pipe'] : 'inherit',
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    const details = options.capture ? `\nstdout:\n${result.stdout}\nstderr:\n${result.stderr}` : '';
    throw new Error(`${command} exited ${result.status}${details}`);
  }
  return options.capture ? result.stdout.trim() : '';
}

function assertSourceContract() {
  if (!fs.existsSync(sourceSchema)) throw new Error(`missing source schema: ${sourceSchema}`);
  const actualDigest = sha256(sourceSchema);
  const mirrorDigest = sha256(vendoredSchema);
  if (actualDigest !== lock.source.sha256 || mirrorDigest !== lock.source.sha256) {
    throw new Error(
      `schema digest drift: locked=${lock.source.sha256} source=${actualDigest} mirror=${mirrorDigest}`,
    );
  }
  if (!fs.readFileSync(sourceSchema).equals(fs.readFileSync(vendoredSchema))) {
    throw new Error('vendored schema is not byte-for-byte identical to its authoritative source');
  }
  const schema = JSON.parse(fs.readFileSync(vendoredSchema, 'utf8'));
  if (schema.$id !== lock.source.id) throw new Error(`schema $id drift: ${schema.$id}`);

  if (sdkLock.source.revision !== lock.source.revision) {
    throw new Error(
      `SDK source revision drift: envelope=${lock.source.revision} sdk=${sdkLock.source.revision}`,
    );
  }
  for (const asset of sdkLock.assets) {
    const sourcePath = path.resolve(clientsRoot, asset.path);
    const mirrorPath = path.resolve(root, asset.mirror);
    if (path.relative(clientsRoot, sourcePath).startsWith('..')) {
      throw new Error(`SDK source asset escapes clients checkout: ${asset.path}`);
    }
    if (path.relative(path.join(root, 'contract'), mirrorPath).startsWith('..')) {
      throw new Error(`SDK mirror asset escapes contract directory: ${asset.mirror}`);
    }
    const sourceDigest = sha256(sourcePath);
    const mirrorDigest = sha256(mirrorPath);
    if (sourceDigest !== asset.sha256 || mirrorDigest !== asset.sha256) {
      throw new Error(
        `SDK asset digest drift for ${asset.path}: locked=${asset.sha256} source=${sourceDigest} mirror=${mirrorDigest}`,
      );
    }
    if (!fs.readFileSync(sourcePath).equals(fs.readFileSync(mirrorPath))) {
      throw new Error(`SDK mirror is not byte-for-byte identical to ${asset.path}`);
    }
    const document = JSON.parse(fs.readFileSync(mirrorPath, 'utf8'));
    if (document[asset.identityField] !== asset.identity) {
      throw new Error(`SDK asset identity drift for ${asset.path}`);
    }
  }

  if (process.env.OPTO_SYNC_ALLOW_UNPINNED_SOURCE !== '1') {
    const revision = run('git', ['rev-parse', 'HEAD'], { cwd: clientsRoot, capture: true });
    if (revision !== lock.source.revision) {
      throw new Error(`source revision drift: locked=${lock.source.revision} actual=${revision}`);
    }
    const status = run('git', ['status', '--porcelain=v1'], { cwd: clientsRoot, capture: true });
    if (status !== '') throw new Error('authoritative source checkout is not clean');
  }
}

function fixtureCorpus() {
  const fixtureRoot = path.join(clientsRoot, lock.fixtures.root);
  const corpus = [];
  for (const [category, accepted] of [['valid', true], ['invalid', false]]) {
    const directory = path.join(fixtureRoot, category);
    const entries = fs.readdirSync(directory)
      .filter((name) => name.endsWith('.json'))
      .sort();
    const expectedCount = lock.fixtures[`${category}Count`];
    if (entries.length !== expectedCount) {
      throw new Error(`${category} fixture count drift: locked=${expectedCount} actual=${entries.length}`);
    }
    for (const name of entries) {
      corpus.push({ key: `${category}/${name}`, accepted, path: path.join(directory, name) });
    }
  }
  return corpus;
}

function parseAdapterOutput(output, runtime, requiredField) {
  const lines = output.split(/\r?\n/).filter(Boolean);
  const report = JSON.parse(lines.at(-1));
  if (
    report.runtime !== runtime
    || typeof report[requiredField] !== 'object'
    || report[requiredField] === null
  ) {
    throw new Error(`${runtime} adapter emitted an invalid report`);
  }
  return report;
}

function runTypeScript(fixtures) {
  const cwd = path.join(clientsRoot, 'clients', 'ts');
  if (prepare) {
    run('npm', ['ci', '--ignore-scripts'], { cwd });
    run('npm', ['run', 'build'], { cwd });
    if (requireTelemetry) run(process.execPath, ['--test', 'test/telemetry.test.mjs'], { cwd });
  }
  const output = run(
    process.execPath,
    [path.join(root, 'adapters', 'typescript', 'check.mjs'), ...fixtures],
    { capture: true },
  );
  const report = parseAdapterOutput(output, 'typescript', 'decisions');
  if (requireTelemetry) {
    const telemetryOutput = run(
      process.execPath,
      [path.join(root, 'adapters', 'typescript', 'telemetry.mjs')],
      { capture: true },
    );
    report.telemetry = parseAdapterOutput(
      telemetryOutput,
      'typescript',
      'telemetry',
    ).telemetry;
  }
  return report;
}

function runDart(fixtures) {
  const cwd = path.join(clientsRoot, 'clients', 'dart');
  if (prepare) {
    run('dart', ['pub', 'get'], { cwd });
    if (requireTelemetry) run('dart', ['test', 'test/telemetry_test.dart'], { cwd });
  }
  const packageConfig = path.join(cwd, '.dart_tool', 'package_config.json');
  const output = run(
    'dart',
    [
      `--packages=${packageConfig}`,
      path.join(root, 'adapters', 'dart', 'check.dart'),
      ...fixtures,
    ],
    { capture: true },
  );
  const report = parseAdapterOutput(output, 'dart', 'decisions');
  if (requireTelemetry) {
    const telemetryOutput = run(
      'dart',
      [
        `--packages=${packageConfig}`,
        path.join(root, 'adapters', 'dart', 'telemetry.dart'),
      ],
      { capture: true },
    );
    report.telemetry = parseAdapterOutput(telemetryOutput, 'dart', 'telemetry').telemetry;
  }
  return report;
}

function tomlString(value) {
  return JSON.stringify(value.replaceAll('\\', '/'));
}

function runRust(fixtures) {
  if (prepare && requireTelemetry) {
    run(
      'cargo',
      [
        'test',
        '--quiet',
        '--manifest-path',
        path.join(clientsRoot, 'clients', 'rust', 'Cargo.toml'),
        '--no-default-features',
        'telemetry::tests',
      ],
    );
  }
  const manifestDirectory = fs.mkdtempSync(path.join(os.tmpdir(), 'opto-sync-contract-rust-'));
  const manifest = [
    '[package]',
    'name = "opto-sync-contract-adapter"',
    'version = "0.0.0"',
    'edition = "2021"',
    '',
    '[workspace]',
    '',
    '[dependencies]',
    `opto-sync-client = { path = ${tomlString(path.join(clientsRoot, 'clients', 'rust'))}, default-features = false }`,
    'serde_json = "1"',
    '',
    '[[bin]]',
    'name = "opto-sync-envelope-adapter"',
    `path = ${tomlString(path.join(root, 'adapters', 'rust', 'src', 'main.rs'))}`,
    '',
    '[[bin]]',
    'name = "opto-sync-telemetry-adapter"',
    `path = ${tomlString(path.join(root, 'adapters', 'rust', 'src', 'telemetry.rs'))}`,
    '',
  ].join('\n');
  const manifestPath = path.join(manifestDirectory, 'Cargo.toml');
  fs.writeFileSync(manifestPath, manifest);
  const output = run(
    'cargo',
    [
      'run',
      '--quiet',
      '--manifest-path',
      manifestPath,
      '--bin',
      'opto-sync-envelope-adapter',
      '--',
      ...fixtures,
    ],
    { capture: true },
  );
  const report = parseAdapterOutput(output, 'rust', 'decisions');
  if (requireTelemetry) {
    const telemetryOutput = run(
      'cargo',
      [
        'run',
        '--quiet',
        '--manifest-path',
        manifestPath,
        '--bin',
        'opto-sync-telemetry-adapter',
      ],
      { capture: true },
    );
    report.telemetry = parseAdapterOutput(telemetryOutput, 'rust', 'telemetry').telemetry;
  }
  return report;
}

assertSourceContract();
const corpus = fixtureCorpus();
const fixturePaths = corpus.map((entry) => entry.path);
const expected = Object.fromEntries(corpus.map((entry) => [entry.key, entry.accepted]));
const runners = { rust: runRust, typescript: runTypeScript, dart: runDart };
const reports = {};
const expectedTelemetry = {
  schemaVersion: 1,
  name: 'opto_sync.sync.cycle_succeeded',
  level: 'info',
  fields: {
    operation: 'protocolSyncCycle',
    checkpoint: '9',
    pushedMutations: 2,
    acknowledgedMutations: 2,
    pulledChanges: 1,
    installedSnapshots: 0,
    hasMorePending: false,
  },
};

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value !== null && typeof value === 'object') {
    return `{${Object.entries(value)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, entry]) => `${JSON.stringify(key)}:${canonicalJson(entry)}`)
      .join(',')}}`;
  }
  return JSON.stringify(value);
}

for (const runtime of requested) {
  reports[runtime] = runners[runtime](fixturePaths);
  for (const entry of corpus) {
    if (reports[runtime].decisions[entry.key] !== entry.accepted) {
      throw new Error(
        `${runtime} decision drift for ${entry.key}: expected=${entry.accepted} actual=${reports[runtime].decisions[entry.key]}`,
      );
    }
  }
  const unexpected = Object.keys(reports[runtime].decisions).filter((key) => !(key in expected));
  if (unexpected.length > 0) throw new Error(`${runtime} emitted unknown fixtures: ${unexpected.join(', ')}`);
  if (requireTelemetry) {
    if (canonicalJson(reports[runtime].telemetry) !== canonicalJson(expectedTelemetry)) {
      throw new Error(`${runtime} telemetry shape differs from the metadata-only contract`);
    }
    if (/payload|token|request|response|cookie|authorization/iu.test(canonicalJson(reports[runtime].telemetry))) {
      throw new Error(`${runtime} telemetry exposed a forbidden field`);
    }
  }
}

for (let index = 1; index < requested.length; index += 1) {
  const comparable = (report) => ({ decisions: report.decisions, telemetry: report.telemetry });
  const left = canonicalJson(comparable(reports[requested[0]]));
  const right = canonicalJson(comparable(reports[requested[index]]));
  if (left !== right) throw new Error(`${requested[0]} and ${requested[index]} decision matrices differ`);
}

console.log(
  `validated ${corpus.length} canonical envelope fixtures${requireTelemetry ? ' and metadata-only telemetry' : ''} across ${requested.join(', ')}; schema=${lock.source.sha256}`,
);
