import 'dart:convert';
import 'dart:io';

import 'package:opto_sync_client/telemetry.dart' as telemetry_api;

void main() {
  final telemetry = telemetry_api.createTelemetryEvent(
    'opto_sync.sync.cycle_succeeded',
    telemetry_api.TelemetryLevel.info,
    const telemetry_api.TelemetryFields(
      operation: 'protocolSyncCycle',
      checkpoint: '9',
      pushedMutations: 2,
      acknowledgedMutations: 2,
      pulledChanges: 1,
      installedSnapshots: 0,
      hasMorePending: false,
    ),
  );
  stdout.writeln(
    jsonEncode({'runtime': 'dart', 'telemetry': telemetry.toJson()}),
  );
}
