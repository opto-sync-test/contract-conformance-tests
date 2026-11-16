import "@typespec/json-schema";
using TypeSpec.JsonSchema;

namespace OptoSyncSingleton;

@id("SingletonPolicyV1")
model SingletonPolicyV1 {
  mode: "strict";
  enabled: boolean;
}
