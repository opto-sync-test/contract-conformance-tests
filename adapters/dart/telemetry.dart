import 'dart:convert';
import 'dart:io';

import 'package:opto_sync_client/opto_sync_client.dart' as telemetry_api;

Future<void> main() async {
  final input = telemetry_api.ProtocolSyncTelemetryInput(
    runtime: telemetry_api.ProtocolSyncTelemetryRuntime.dart,
    kind: telemetry_api.ProtocolSyncTelemetryKind.stateChanged,
    status: telemetry_api.ProtocolSyncStatus.idle,
    timestamp: DateTime.parse('2026-08-11T17:53:28.151Z'),
    requestId: 'sync-cycle-42',
  );
  final telemetry = telemetry_api.createProtocolSyncTelemetryRecord(input);
  Map<String, Object>? emitted;
  await telemetry_api.emitProtocolSyncTelemetry(
    (record) {
      emitted = record;
    },
    input,
  );
  if (jsonEncode(emitted) != jsonEncode(telemetry)) {
    throw StateError('Dart fail-open sink changed the canonical record');
  }
  stdout.writeln(jsonEncode({'runtime': 'dart', 'telemetry': telemetry}));
}
