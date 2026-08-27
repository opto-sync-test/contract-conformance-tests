import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

export function withTemporaryRustWorkspace(callback, options = {}) {
  if (typeof callback !== 'function') {
    throw new TypeError('temporary Rust workspace callback must be a function');
  }

  const temporaryRoot = path.resolve(options.temporaryRoot ?? os.tmpdir());
  const workspace = fs.mkdtempSync(path.join(temporaryRoot, 'opto-sync-contract-rust-'));
  try {
    return callback(workspace);
  } finally {
    fs.rmSync(workspace, {
      recursive: true,
      force: true,
      maxRetries: 3,
      retryDelay: 50,
    });
  }
}
