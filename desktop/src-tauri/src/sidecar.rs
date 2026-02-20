use tauri::AppHandle;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandChild;

/// Manages the lifecycle of the bundled OpenLedger server sidecar.
///
/// The sidecar binary is placed in the Tauri `externalBin` directory and is
/// named following the Tauri triple convention, e.g.:
///
///   binaries/openledger-server-x86_64-pc-windows-msvc.exe
///
/// When `spawn()` is called the manager starts the process and polls the
/// server's `/health` endpoint until it responds (up to 30 seconds).
pub struct SidecarManager {
    child: Option<CommandChild>,
}

impl SidecarManager {
    /// Create a new, idle manager.
    pub fn new() -> Self {
        Self { child: None }
    }

    /// Spawn the sidecar binary and wait until the server is healthy.
    ///
    /// # Arguments
    /// * `app_handle` — Tauri application handle (for shell access).
    /// * `port` — The port the sidecar server will listen on (default 8000).
    ///
    /// # Errors
    /// Returns an error string if the binary cannot be started or if the
    /// health check does not pass within 30 seconds.
    pub async fn spawn(&mut self, app_handle: &AppHandle, port: u16) -> Result<(), String> {
        if self.child.is_some() {
            return Err("Sidecar is already running".into());
        }

        let (mut _rx, child) = app_handle
            .shell()
            .sidecar("openledger-server")
            .map_err(|e| format!("Failed to create sidecar command: {e}"))?
            .args(["--port", &port.to_string()])
            .spawn()
            .map_err(|e| format!("Failed to spawn sidecar: {e}"))?;

        self.child = Some(child);

        // Poll /health until the server is ready (max 30 s, 500 ms interval).
        let url = format!("http://127.0.0.1:{port}/health");
        let client = reqwest::Client::new();
        let deadline = tokio::time::Instant::now() + std::time::Duration::from_secs(30);

        loop {
            if tokio::time::Instant::now() >= deadline {
                // Clean up the process we just started.
                self.stop();
                return Err("Sidecar server did not become healthy within 30 seconds".into());
            }

            match client
                .get(&url)
                .timeout(std::time::Duration::from_secs(2))
                .send()
                .await
            {
                Ok(resp) if resp.status().is_success() => {
                    return Ok(());
                }
                _ => {
                    tokio::time::sleep(std::time::Duration::from_millis(500)).await;
                }
            }
        }
    }

    /// Kill the sidecar process if it is running.
    pub fn stop(&mut self) {
        if let Some(child) = self.child.take() {
            let _ = child.kill();
        }
    }

    /// Returns `true` if the sidecar process handle is present.
    pub fn is_running(&self) -> bool {
        self.child.is_some()
    }
}

impl Drop for SidecarManager {
    fn drop(&mut self) {
        self.stop();
    }
}
