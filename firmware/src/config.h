#pragma once

#include <Arduino.h>

// ==============================================================================
// Omni Firmware Configuration
// ==============================================================================

// Display Dimensions (Adafruit 6382 4.2" Tri-color SSD1683)
#define DISPLAY_WIDTH          400
#define DISPLAY_HEIGHT         300
#define DISPLAY_ROTATION       1    // 1 = 300x400 Portrait; 0 = 400x300 Landscape

// Navigation Button / Thumbwheel Timings
#define NAV_DEBOUNCE_MS        25   // Debounce window in milliseconds
#define NAV_PTT_HOLD_MS        450  // Holding Center Push for >= 450ms triggers PTT
#define NAV_COALESCE_MS        250  // Coalesce rapid scrolls before refreshing E-Ink

// Wi-Fi Configuration
#ifndef WIFI_SSID
  #define WIFI_SSID            "ufdevice"
#endif
#ifndef WIFI_PASSWORD
  #define WIFI_PASSWORD        "gogators"
#endif

// Cloud / Gemini Configuration
#define CLOUD_TURN_URL         "http://10.0.0.1:8787/v1/turn"
#define DEFAULT_GEMINI_MODEL   "gemini-1.5-flash"

// Enable offline demonstration fallback when Wi-Fi is disconnected or no API key is provided
#define ENABLE_OFFLINE_DEMO    true

// Audio Recording Configuration
#define AUDIO_SAMPLE_RATE      16000
#define AUDIO_BITS_PER_SAMPLE  16
#define AUDIO_CHANNELS         1
#define AUDIO_MAX_SECONDS      10   // Max PTT recording duration in seconds
