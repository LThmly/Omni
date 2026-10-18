#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

// ==============================================================================
// AI Agent Pipeline
// Dispatches turn requests to Gemini / Cloud or executes the offline demo cycle.
// ==============================================================================

void aiInit();

// Trigger a voice / text turn request
void aiProcessTurn(const char* explicitText = nullptr);

// Offline demonstration step
void aiExecuteOfflineDemo();
