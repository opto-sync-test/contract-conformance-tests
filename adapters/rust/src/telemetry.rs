fn main() {
    fn input() -> opto_sync_client::ProtocolSyncTelemetryInput<'static> {
        opto_sync_client::ProtocolSyncTelemetryInput {
            runtime: opto_sync_client::ProtocolSyncTelemetryRuntime::Rust,
            kind: opto_sync_client::ProtocolSyncTelemetryKind::StateChanged,
            status: opto_sync_client::ProtocolSyncTelemetryStatus::Idle,
            consecutive_failures: 0,
            timestamp: "2026-08-11T17:53:28.151Z",
            next_retry_at: None,
            cycle: None,
            error_code: None,
            request_id: Some("sync-cycle-42"),
            trace_id: None,
            span_id: None,
            trace_flags: None,
            trace_state: None,
        }
    }

    let telemetry = opto_sync_client::create_protocol_sync_telemetry_record(input())
    .expect("canonical Ores/OpenTelemetry record must be valid");
    let emitted = std::sync::Mutex::new(None);
    let sink = |record: &opto_sync_client::OresOpenTelemetryLogRecord| {
        *emitted.lock().expect("telemetry capture lock") = Some(record.clone());
        Ok::<(), String>(())
    };
    opto_sync_client::emit_protocol_sync_telemetry(Some(&sink), input());
    assert_eq!(
        emitted.lock().expect("telemetry capture lock").as_ref(),
        Some(&telemetry),
        "Rust fail-open sink changed the canonical record",
    );

    println!(
        "{}",
        serde_json::json!({"runtime": "rust", "telemetry": telemetry})
    );
}
