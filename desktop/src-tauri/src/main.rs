#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, PhysicalSize};

#[tauri::command]
fn resize_window(app_handle: tauri::AppHandle, width: u32, height: u32) {
    if let Some(window) = app_handle.get_webview_window("main") {
        let _ = window.set_size(PhysicalSize::new(width, height));
    }
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![resize_window])
        .setup(|app| {
            if let Some(window) = app.get_webview_window("main") {
                // Ensure frameless transparent floating orb window stays on top
                let _ = window.set_always_on_top(true);
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Daisy desktop application");
}
