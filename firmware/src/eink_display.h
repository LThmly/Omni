#pragma once

#include <Arduino.h>

// ==============================================================================
// E-Ink Display Engine (Adafruit 6382 4.2" Tri-Color SSD1683 via ThinkInk)
// Portrait 300x400 Layout with Black / White / Red Tri-Color Primitives.
// ==============================================================================

void einkInit();

// Request a display refresh. Coalesces rapid navigation movements.
void einkRequestRefresh();

// Force an immediate refresh
void einkRefreshNow();

// Called in main loop to handle coalescing and painting
void einkUpdate();

// Returns true if the hardware panel is currently busy refreshing
bool einkIsBusy();
