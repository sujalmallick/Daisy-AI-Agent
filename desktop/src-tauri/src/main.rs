#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{LogicalSize, Manager, PhysicalPosition, Position, window::Color};

#[tauri::command]
fn resize_window(app_handle: tauri::AppHandle, width: u32, height: u32) {
    if let Some(window) = app_handle.get_webview_window("main") {
        if let Ok(Some(monitor)) = window.current_monitor() {
            let scale_factor = monitor.scale_factor();
            let monitor_size = monitor.size();
            let monitor_pos = monitor.position();

            let phys_w = (width as f64 * scale_factor).round() as i32;
            let phys_h = (height as f64 * scale_factor).round() as i32;
            let margin = (16.0 * scale_factor).round() as i32;

            if let Ok(curr_pos) = window.outer_position() {
                let mut new_x = curr_pos.x;
                let mut new_y = curr_pos.y;

                let max_x = monitor_pos.x + monitor_size.width as i32 - phys_w - margin;
                let min_x = monitor_pos.x + margin;
                let max_y = monitor_pos.y + monitor_size.height as i32 - phys_h - margin;
                let min_y = monitor_pos.y + margin;

                if new_x > max_x {
                    new_x = max_x;
                }
                if new_x < min_x {
                    new_x = min_x;
                }
                if new_y > max_y {
                    new_y = max_y;
                }
                if new_y < min_y {
                    new_y = min_y;
                }

                if new_x != curr_pos.x || new_y != curr_pos.y {
                    let _ = window.set_position(Position::Physical(PhysicalPosition::new(new_x, new_y)));
                }
            }
        }
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
        let mut target_x = x;
        let mut target_y = y;

        if let Ok(Some(monitor)) = window.current_monitor() {
            let scale_factor = monitor.scale_factor();
            let monitor_size = monitor.size();
            let monitor_pos = monitor.position();
            let margin = (16.0 * scale_factor).round() as i32;

            if let Ok(size) = window.outer_size() {
                let max_x = monitor_pos.x + monitor_size.width as i32 - size.width as i32 - margin;
                let min_x = monitor_pos.x + margin;
                let max_y = monitor_pos.y + monitor_size.height as i32 - size.height as i32 - margin;
                let min_y = monitor_pos.y + margin;

                if target_x > max_x { target_x = max_x; }
                if target_x < min_x { target_x = min_x; }
                if target_y > max_y { target_y = max_y; }
                if target_y < min_y { target_y = min_y; }
            }
        }

        let _ = window.set_position(Position::Physical(PhysicalPosition::new(target_x, target_y)));
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
fn set_window_mode(app_handle: tauri::AppHandle, mode: String) {
    if let Some(window) = app_handle.get_webview_window("main") {
        if mode == "floating" {
            let _ = window.set_always_on_top(true);
            let _ = window.set_shadow(false);
            let _ = window.set_resizable(false);
        } else {
            let _ = window.set_always_on_top(false);
            let _ = window.set_shadow(true);
            let _ = window.set_resizable(true);
        }
    }
}

#[tauri::command]
fn close_window(app_handle: tauri::AppHandle) {
    if let Some(window) = app_handle.get_webview_window("main") {
        let _ = window.close();
    }
}

#[tauri::command]
fn exit_app(app_handle: tauri::AppHandle) {
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
            set_window_mode,
            minimize_window,
            close_window,
            exit_app
        ])
        .setup(|app| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_background_color(Some(Color(0, 0, 0, 0)));
                let _ = window.set_always_on_top(true);
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Daisy desktop application");
}
