#pragma once

#include <Arduino.h>

// ==============================================================================
// I2S MEMS Microphone Driver (Adafruit 6049 ICS-43434)
// Records 16-bit 16kHz mono audio into PSRAM buffer during Push-to-Talk.
// ==============================================================================

void micInit();
void micStartRecording();
void micUpdateRecording();
void micStopRecording();

bool micIsRecording();
size_t micGetRecordedBytes();
const uint8_t* micGetRecordedBuffer();
