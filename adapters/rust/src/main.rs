use std::{collections::BTreeMap, env, fs, path::Path};

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

    println!("{}", serde_json::json!({"runtime": "rust", "decisions": decisions}));
}
