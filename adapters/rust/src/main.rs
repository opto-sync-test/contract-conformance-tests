use std::{cmp::Ordering, collections::BTreeMap, env, fs, path::Path};

fn fixture_key(path: &Path) -> String {
    let category = path
        .parent()
        .and_then(Path::file_name)
        .and_then(|value| value.to_str())
        .expect("fixture category must be UTF-8");
    let name = path
        .file_name()
        .and_then(|value| value.to_str())
        .expect("fixture name must be UTF-8");
    format!("{category}/{name}")
}

fn main() {
    let mut decisions = BTreeMap::new();
    for fixture in env::args().skip(1) {
        let path = Path::new(&fixture);
        let contents = fs::read_to_string(path).expect("fixture must be readable UTF-8 JSON");
        decisions.insert(
            fixture_key(path),
            opto_sync_client::schema::parse_envelope(&contents).is_ok(),
        );
    }

    let parts = opto_sync_client::HlcParts {
        millis: 1_721_822_400_000,
        counter: 255,
        node_id: "9f3a2b".to_string(),
    };
    let formatted = opto_sync_client::format_hlc(&parts);
    let parsed = opto_sync_client::parse_hlc(&formatted).expect("formatted HLC must parse");
    let compared = match opto_sync_client::compare_hlc(
        &formatted,
        "1721822400001-0000-9f3a2b",
    ) {
        Ordering::Less => -1,
        Ordering::Equal => 0,
        Ordering::Greater => 1,
    };
    let hlc = serde_json::json!({
        "formatted": formatted,
        "parsed": {
            "millis": parsed.millis,
            "counter": parsed.counter,
            "nodeId": parsed.node_id,
        },
        "compared": compared,
    });

    println!(
        "{}",
        serde_json::json!({"runtime": "rust", "decisions": decisions, "hlc": hlc})
    );
}
