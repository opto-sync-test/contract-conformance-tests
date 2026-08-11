import 'dart:convert';
import 'dart:io';

import 'package:opto_sync_client/schema.dart' as schema;
import 'package:opto_sync_client/opto_sync_client.dart' as client;

void main(List<String> arguments) {
  final decisions = <String, bool>{};
  for (final fixturePath in arguments) {
    final file = File(fixturePath);
    final category = file.parent.uri.pathSegments
        .where((part) => part.isNotEmpty)
        .last;
    final key = '$category/${file.uri.pathSegments.last}';
    try {
      schema.parseEnvelope(file.readAsStringSync());
      decisions[key] = true;
    } catch (_) {
      decisions[key] = false;
    }
  }
  const parts = client.HlcParts(
    millis: 1721822400000,
    counter: 255,
    nodeId: '9f3a2b',
  );
  final formatted = client.formatHlc(parts);
  final parsed = client.parseHlc(formatted)!;
  final hlc = <String, Object>{
    'formatted': formatted,
    'parsed': <String, Object>{
      'millis': parsed.millis,
      'counter': parsed.counter,
      'nodeId': parsed.nodeId,
    },
    'compared': client.compareHlc(
      formatted,
      '1721822400001-0000-9f3a2b',
    ).sign,
  };
  stdout.writeln(
    jsonEncode({'runtime': 'dart', 'decisions': decisions, 'hlc': hlc}),
  );
}
