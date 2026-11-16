import unittest

from deep_tests.contract_model import Command, IdempotencyConflict, ReferenceStore, generate_valid_trace, replay


class OptoSyncDomainHardeningTests(unittest.TestCase):
    def test_duplicate_offline_mutation_is_exactly_once(self) -> None:
        store = ReferenceStore()
        store.apply(Command("create", "note-42", "local-v1", "create-note-42"))
        mutation = Command("update", "note-42", "local-v2", "sync-note-42-v2")
        first = store.apply(mutation)
        revision = store.revision
        for _ in range(32):
            self.assertEqual(store.apply(mutation), first)
        self.assertEqual(store.revision, revision)

    def test_sync_idempotency_key_cannot_be_rebound_after_other_writes(self) -> None:
        store = ReferenceStore()
        store.apply(Command("create", "note-42", "local-v1", "stable-sync-key"))
        store.apply(Command("create", "note-99", "other", "create-note-99"))
        with self.assertRaises(IdempotencyConflict):
            store.apply(Command("update", "note-42", "remote-v3", "stable-sync-key"))

    def test_long_offline_replay_converges_across_duplicate_schedules(self) -> None:
        commands = generate_valid_trace(2026091401, steps=720)
        snapshots = {replay(commands, duplicate_every=n).snapshot() for n in (2, 4, 9, 17)}
        self.assertEqual(len(snapshots), 1)


if __name__ == "__main__":
    unittest.main()
