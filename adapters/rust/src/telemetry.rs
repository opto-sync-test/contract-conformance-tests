fn main() {
    let telemetry = opto_sync_client::telemetry::create_telemetry_event(
        "opto_sync.sync.cycle_succeeded",
        opto_sync_client::telemetry::TelemetryLevel::Info,
        opto_sync_client::telemetry::TelemetryFields {
            operation: Some("protocolSyncCycle".to_string()),
            checkpoint: Some("9".to_string()),
            pushed_mutations: Some(2),
            acknowledged_mutations: Some(2),
            pulled_changes: Some(1),
            installed_snapshots: Some(0),
            has_more_pending: Some(false),
            ..opto_sync_client::telemetry::TelemetryFields::default()
        },
    )
    .expect("canonical telemetry event must be valid");

    println!(
        "{}",
        serde_json::json!({"runtime": "rust", "telemetry": telemetry})
    );
}
