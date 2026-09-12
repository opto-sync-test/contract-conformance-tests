import "@typespec/json-schema";
using TypeSpec.JsonSchema;

namespace OptoSyncPolicy;

@id("SyncPolicyV1")
model SyncPolicyV1 {
  @minValue(1)
  @maxValue(1)
  version: integer;

  @minLength(1)
  @maxLength(128)
  collection: string;

  @minValue(1)
  @maxValue(1000)
  max_batch: integer;

  @minValue(0)
  @maxValue(10)
  retry_limit: integer;

  offline_capable: boolean;
}
