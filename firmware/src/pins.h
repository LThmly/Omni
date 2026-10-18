#pragma once

#include <Arduino.h>

// ==============================================================================
// Hardware Pinout for Seeed Studio XIAO ESP32S3 Plus
// See context/hardware.md for complete details.
// ==============================================================================

// E-Ink Display (Adafruit 6382 4.2" Tri-color SSD1683 via Adafruit 4224 Friend)
#define PIN_EPD_CS    D0  // GPIO1  - Chip Select
#define PIN_EPD_DC    D1  // GPIO2  - Data / Command
#define PIN_EPD_RST   D2  // GPIO3  - Reset (Strapping pin)
#define PIN_EPD_BUSY  D9  // GPIO8  - Busy indicator (Hardware MISO pad used as GPIO)
#define PIN_EPD_SCK   D8  // GPIO7  - SPI Clock
#define PIN_EPD_MOSI  D10 // GPIO9  - SPI MOSI (Strapping pin)

// Navigation Switch (Same Sky TS43-135255-10-BK-200-SMT-TR)
// Common pin is wired to GND; input pins use internal pullups (INPUT_PULLUP).
#define PIN_NAV_UP    D4  // GPIO5  - Up rotation/detent contact
#define PIN_NAV_DOWN  D3  // GPIO4  - Down rotation/detent contact

// Center Push Contact: Underside/edge pad D19 / GPIO11
#if defined(D19)
  #define PIN_NAV_PUSH D19
#else
  #define PIN_NAV_PUSH 11 // GPIO11
#endif

// I2S MEMS Microphone (Adafruit 6049 - ICS-43434)
#define PIN_I2S_WS    D5  // GPIO6  - Word Select / LRCLK
#define PIN_I2S_SCK   D6  // GPIO43 - Bit Clock / BCLK
#define PIN_I2S_SD    D7  // GPIO44 - Serial Data / DOUT

// Onboard User LED
#ifndef PIN_LED
  #if defined(LED_BUILTIN)
    #define PIN_LED LED_BUILTIN
  #else
    #define PIN_LED 21
  #endif
#endif
