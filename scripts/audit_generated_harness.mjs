#!/usr/bin/env node
import childProcess from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const repositories = process.argv.slice(2).map((entry) => path.resolve(entry));
if (repositories.length === 0) {
  throw new Error('usage: node scripts/audit_generated_harness.mjs <generated-repository> [...]');
}

function git(repository, args) {
  return childProcess.execFileSync('git', args, { cwd: repository, encoding: 'utf8' }).trim();
}

function sourceName(url) {
  const match = url.match(/github\.com[/:]([^/]+\/[^/]+?)(?:\.git)?$/);
  return match?.[1];
}

const failures = [];
for (const repository of repositories) {
  const pinsPath = path.join(repository, 'source-pins.json');
  if (!fs.existsSync(pinsPath)) {
    failures.push(`${repository}: source-pins.json is missing`);
    continue;
  }
  const pins = JSON.parse(fs.readFileSync(pinsPath, 'utf8')).sources ?? {};
  const modulesPath = path.join(repository, '.gitmodules');
  if (!fs.existsSync(modulesPath)) {
    console.log(`${path.basename(repository)}: no gitlink lane; ${Object.keys(pins).length} immutable source pin(s)`);
    continue;
  }

  const pathEntries = git(repository, [
    'config',
    '-f',
    '.gitmodules',
    '--get-regexp',
    '^submodule\\..*\\.path$',
  ]).split(/\r?\n/).filter(Boolean);
  for (const entry of pathEntries) {
    const separator = entry.indexOf(' ');
    const key = entry.slice(0, separator);
    const gitlinkPath = entry.slice(separator + 1);
    const section = key.slice(0, -'.path'.length);
    const url = git(repository, ['config', '-f', '.gitmodules', '--get', `${section}.url`]);
    const fullName = sourceName(url);
    const tree = git(repository, ['ls-tree', 'HEAD', '--', gitlinkPath]);
    const match = tree.match(/^160000 commit ([0-9a-f]{40})\t/);
    if (!fullName || !match) {
      failures.push(`${path.basename(repository)}: cannot resolve ${gitlinkPath} to a GitHub source gitlink`);
      continue;
    }
    const pinned = pins[fullName]?.sha;
    if (pinned !== match[1]) {
      failures.push(
        `${path.basename(repository)}: ${fullName} source-pins.json=${pinned ?? '<missing>'} gitlink=${match[1]}`,
      );
    }
  }
}

if (failures.length > 0) {
  console.error('generated harness immutable-source disagreement:');
  for (const failure of failures) console.error(`  - ${failure}`);
  process.exit(1);
}
console.log(`validated immutable source pins for ${repositories.length} generated harness(es)`);
