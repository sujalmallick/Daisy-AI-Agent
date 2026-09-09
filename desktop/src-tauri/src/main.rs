#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{LogicalSize, Manager, PhysicalPosition, Position};

#[tauri::command]
fn resize_window(app_handle: tauri::AppHandle, width: u32, height: u32) {
    if let Some(window) = app_handle.get_webview_window("main") {
        let _ = window.set_size(LogicalSize::new(width as f64, height as f64));
    }
}

#[tauri::command]
fn get_window_position(app_handle: tauri::AppHandle) -> Result<(i32, i32), String> {
    if let Some(window) = app_handle.get_webview_window("main") {
        let pos = window.outer_position().map_err(|e| e.to_string())?;
        Ok((pos.x, pos.y))
    } else {
        Err("Window not found".into())
    }
}

#[tauri::command]
fn set_window_position(app_handle: tauri::AppHandle, x: i32, y: i32) -> Result<(), String> {
    if let Some(window) = app_handle.get_webview_window("main") {
        let _ = window.set_position(Position::Physical(PhysicalPosition::new(x, y)));
        Ok(())
    } else {
        Err("Window not found".into())
    }
}

#[tauri::command]
fn set_always_on_top(app_handle: tauri::AppHandle, always_on_top: bool) {
    if let Some(window) = app_handle.get_webview_window("main") {
        let _ = window.set_always_on_top(always_on_top);
    }
}

#[tauri::command]
fn minimize_window(app_handle: tauri::AppHandle) {
    if let Some(window) = app_handle.get_webview_window("main") {
        let _ = window.minimize();
    }
}

#[tauri::command]
fn close_window(app_handle: tauri::AppHandle) {
    if let Some(window) = app_handle.get_webview_window("main") {
        let _ = window.close();
    }
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            resize_window,
            get_window_position,
            set_window_position,
            set_always_on_top,
            minimize_window,
            close_window
        ])
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
