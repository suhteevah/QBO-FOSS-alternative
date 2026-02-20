mod commands;
mod sidecar;
mod tray;

use tauri::Manager;
use tokio::sync::Mutex;

/// Shared application state accessible from Tauri commands.
pub struct AppState {
    pub sidecar: Mutex<sidecar::SidecarManager>,
}

/// Spawns the bundled Python backend sidecar on localhost:8000.
///
/// Invoked from the frontend via `invoke("spawn_local_server")`.
#[tauri::command]
async fn spawn_local_server(
    app_handle: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    let mut mgr = state.sidecar.lock().await;
    if mgr.is_running() {
        return Ok(()); // Already running — no-op
    }
    mgr.spawn(&app_handle, 8000).await
}

/// Stops the sidecar if it is running.
///
/// Invoked from the frontend via `invoke("stop_local_server")`.
#[tauri::command]
async fn stop_local_server(state: tauri::State<'_, AppState>) -> Result<(), String> {
    let mut mgr = state.sidecar.lock().await;
    mgr.stop();
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_os::init())
        .manage(AppState {
            sidecar: Mutex::new(sidecar::SidecarManager::new()),
        })
        .invoke_handler(tauri::generate_handler![
            commands::check_server_health,
            commands::get_platform_info,
            commands::is_desktop_app,
            spawn_local_server,
            stop_local_server,
        ])
        .setup(|app| {
            // Set up the system tray.
            tray::setup_tray(app)?;

            Ok(())
        })
        .on_window_event(|window, event| {
            // Minimize to tray instead of quitting when the user clicks the
            // window close button.  The app only truly exits via the tray
            // menu "Quit" item.
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running OpenLedger Desktop");
}
