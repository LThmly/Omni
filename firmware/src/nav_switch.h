#pragma once

#include <Arduino.h>

// ==============================================================================
// Navigation Switch (Same Sky TS43-135255-10-BK-200-SMT-TR)
// 3-way thumbwheel: Up detent, Down detent, and Center Push (Click & PTT Hold).
// ==============================================================================

enum NavEvent {
  NAV_EVENT_NONE = 0,
  NAV_EVENT_UP,         // Up detent / rotation step
  NAV_EVENT_DOWN,       // Down detent / rotation step
  NAV_EVENT_CLICK,      // Short press of Center Push (< NAV_PTT_HOLD_MS)
  NAV_EVENT_PTT_START,  // Center Push held >= NAV_PTT_HOLD_MS (PTT active)
  NAV_EVENT_PTT_END     // Center Push released after PTT hold
};

// Convert event enum to human-readable string
const char* navEventToString(NavEvent evt);

// Initialize pins and debouncing state
void navInit();

// Sample pins, debounce, and update event queue (call frequently in loop)
void navUpdate();

// Poll the next event from the queue. Returns true if an event was retrieved.
bool navPollEvent(NavEvent& outEvent);

// Returns true if Push-To-Talk is currently held down
bool navIsPttActive();

// Inject an event programmatically (useful for Serial CLI testing)
void navInjectEvent(NavEvent evt);
