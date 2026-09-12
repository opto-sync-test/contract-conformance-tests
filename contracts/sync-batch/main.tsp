import "@typespec/json-schema";
using TypeSpec.JsonSchema;

namespace OptoSyncBatch;

@id("SyncBatchV1")
model SyncBatchV1 {
  @minValue(1)
  @maxValue(1)
  version: integer;

  @minLength(1)
  @maxLength(128)
  collection: string;

  direction: "pull" | "push";

  @minValue(1)
  @maxValue(1000)
  batch_size: integer;

  @minLength(1)
  @maxLength(512)
  cursor?: string;

  include_tombstones: boolean;
}
