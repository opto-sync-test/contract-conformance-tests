import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { withTemporaryRustWorkspace } from '../scripts/temporary_rust_workspace.mjs';

function withTestRoot(callback) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'opto-sync-contract-test-'));
  try {
    callback(root);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

test('temporary Rust workspace is removed after success', () => {
  withTestRoot((temporaryRoot) => {
    let workspace;
    const result = withTemporaryRustWorkspace((directory) => {
      workspace = directory;
      fs.mkdirSync(path.join(directory, 'target', 'debug'), { recursive: true });
      fs.writeFileSync(path.join(directory, 'target', 'debug', 'adapter'), 'synthetic build');
      return 'complete';
    }, { temporaryRoot });

    assert.equal(result, 'complete');
    assert.equal(fs.existsSync(workspace), false);
  });
});

test('temporary Rust workspace is removed after failure', () => {
  withTestRoot((temporaryRoot) => {
    let workspace;
    assert.throws(
      () => withTemporaryRustWorkspace((directory) => {
        workspace = directory;
        fs.mkdirSync(path.join(directory, 'target'), { recursive: true });
        fs.writeFileSync(path.join(directory, 'target', 'partial-build'), 'synthetic build');
        throw new Error('synthetic adapter failure');
      }, { temporaryRoot }),
      /synthetic adapter failure/,
    );
    assert.equal(fs.existsSync(workspace), false);
  });
});
