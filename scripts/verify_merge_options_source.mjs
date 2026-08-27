#!/usr/bin/env node
import childProcess from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const sourceRoot = path.resolve(
  process.env.SYNCER_RS_DIR ?? process.argv[2] ?? path.join(root, '.source', 'syncer-rs'),
);
const sdkContract = JSON.parse(
  fs.readFileSync(path.join(root, 'contract', 'opto-sync-sdk-api.v1.json'), 'utf8'),
);
const source = sdkContract.mergeOptionsSchema;
const expected = {
  repository: 'opto-sync/syncer.rs',
  commit: 'bb71ac1b4b7d94dd7035e6cc7b76e5c10f284e98',
  path: 'schema/merge-options.schema.json',
  id: 'https://opto-sync.dev/schema/merge-options.schema.json',
  sha256: 'e9107667cee2868a922a70c9c48175c62b466fa728466c23bac766aebcbb2f2a',
  status: 'canonical',
  blockers: [],
};

if (JSON.stringify(source) !== JSON.stringify(expected)) {
  throw new Error('client SDK merge-options provenance differs from the immutable test contract');
}

function git(args) {
  return childProcess.execFileSync('git', args, {
    cwd: sourceRoot,
    encoding: 'utf8',
  }).trim();
}

const revision = git(['rev-parse', 'HEAD']);
if (revision !== source.commit) {
  throw new Error(`syncer.rs revision drift: expected=${source.commit} actual=${revision}`);
}
if (git(['status', '--porcelain=v1']) !== '') {
  throw new Error('syncer.rs source checkout is not clean');
}
const remote = git(['remote', 'get-url', 'origin']).replace(/\.git$/u, '');
if (!remote.endsWith('/opto-sync/syncer.rs') && !remote.endsWith(':opto-sync/syncer.rs')) {
  throw new Error(`syncer.rs origin drift: ${remote}`);
}

const schemaPath = path.resolve(sourceRoot, source.path);
const relativeSchemaPath = path.relative(sourceRoot, schemaPath);
if (relativeSchemaPath.startsWith('..') || path.isAbsolute(relativeSchemaPath)) {
  throw new Error(`merge-options schema escapes source checkout: ${source.path}`);
}
const schemaBytes = fs.readFileSync(schemaPath);
const digest = crypto.createHash('sha256').update(schemaBytes).digest('hex');
if (digest !== source.sha256) {
  throw new Error(`merge-options schema digest drift: expected=${source.sha256} actual=${digest}`);
}
const schema = JSON.parse(schemaBytes);
if (schema.$id !== source.id) {
  throw new Error(`merge-options schema $id drift: expected=${source.id} actual=${schema.$id}`);
}
if (schema.$schema !== 'https://json-schema.org/draft/2020-12/schema') {
  throw new Error(`merge-options schema draft drift: ${schema.$schema}`);
}
const expectedProperties = [
  'arrayMatchKeys',
  'arrayStrategy',
  'detectCircularRefs',
  'fwwKeys',
  'lwwKeys',
  'maxDepth',
  'resolveByTimestamp',
];
if (
  schema.additionalProperties !== false
  || JSON.stringify(Object.keys(schema.properties).sort()) !== JSON.stringify(expectedProperties)
  || schema.properties.detectCircularRefs?.type !== 'boolean'
  || schema.properties.detectCircularRefs?.default !== false
) {
  throw new Error('merge-options schema is not the closed canonical seven-key contract');
}

console.log(`verified ${source.repository}@${source.commit} ${source.path} sha256=${digest}`);
