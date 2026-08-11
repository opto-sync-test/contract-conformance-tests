import 'dart:convert';
import 'dart:io';

import 'package:opto_sync_client/schema.dart' as schema;

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
  stdout.writeln(jsonEncode({'runtime': 'dart', 'decisions': decisions}));
}
