use serde::Serialize;

/// Platform metadata for the frontend to populate `device_info` on API keys.
#[derive(Debug, Serialize)]
pub struct PlatformInfo {
    pub os: String,
    pub arch: String,
    pub hostname: String,
}

/// Calls `GET {url}/health` and returns the response body (expected to
/// contain the server version or status string).
///
/// Invoked from the frontend via `invoke("check_server_health", { url })`.
#[tauri::command]
pub async fn check_server_health(url: String) -> Result<String, String> {
    let endpoint = format!("{}/health", url.trim_end_matches('/'));

    let response = reqwest::Client::new()
        .get(&endpoint)
        .timeout(std::time::Duration::from_secs(5))
        .send()
        .await
        .map_err(|e| format!("Connection failed: {e}"))?;

    if !response.status().is_success() {
        return Err(format!("Server returned status {}", response.status()));
    }

    response
        .text()
        .await
        .map_err(|e| format!("Failed to read response body: {e}"))
}

/// Returns platform details so the frontend can populate the `device_info`
/// field when registering API keys.
///
/// Invoked from the frontend via `invoke("get_platform_info")`.
#[tauri::command]
pub fn get_platform_info() -> PlatformInfo {
    PlatformInfo {
        os: std::env::consts::OS.to_string(),
        arch: std::env::consts::ARCH.to_string(),
        hostname: get_hostname(),
    }
}

/// Simple flag so the React frontend can detect whether it is running inside
/// the Tauri desktop shell or in a regular browser tab.
///
/// Invoked from the frontend via `invoke("is_desktop_app")`.
#[tauri::command]
pub fn is_desktop_app() -> bool {
    true
}

/// Cross-platform hostname lookup without an extra crate dependency.
fn get_hostname() -> String {
    // Try COMPUTERNAME (Windows) then HOSTNAME (Unix), falling back to
    // the Rust gethostname-style approach via libc / winapi if needed.
    if let Ok(name) = std::env::var("COMPUTERNAME") {
        return name;
    }
    if let Ok(name) = std::env::var("HOSTNAME") {
        return name;
    }
    "unknown".to_string()
}
