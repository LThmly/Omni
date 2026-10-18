#include <Arduino.h>
#include <rom/rtc.h>
#include "pins.h"
#include "config.h"
#include "nav_switch.h"
#include "app_model.h"
#include "eink_display.h"
#include "audio_mic.h"
#include "wifi_link.h"
#include "ai_agent.h"

static uint32_t sLastHeartbeat = 0;
static bool sLedState = false;

static void checkStrappingPinsAtBoot() {
  pinMode(PIN_EPD_RST, INPUT);
  pinMode(PIN_EPD_MOSI, INPUT);
  int d2_boot = digitalRead(PIN_EPD_RST);
  int d10_boot = digitalRead(PIN_EPD_MOSI);

  Serial.println("\n==========================================");
  Serial.println("  Omni ESP32-S3 E-Ink Companion Firmware  ");
  Serial.println("==========================================");
  Serial.printf("Reset reason: %d\n", rtc_get_reset_reason(0));
  Serial.printf("D2 (GPIO3 - RST) boot level:  %s\n", d2_boot ? "HIGH (Safe)" : "LOW (Warning)");
  Serial.printf("D10 (GPIO9 - MOSI) boot level: %s\n", d10_boot ? "HIGH (Safe)" : "LOW (Warning)");
  if (psramFound()) {
    Serial.printf("PSRAM available: %d KB\n", ESP.getPsramSize() / 1024);
  } else {
    Serial.println("PSRAM: Not detected");
  }
  Serial.println("==========================================\n");
}

static void processSerialCommands() {
  if (!Serial.available()) return;

  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.isEmpty()) return;

  Serial.printf("[CLI] Command: '%s'\n", line.c_str());

  if (line == "up" || line == "u") {
    navInjectEvent(NAV_EVENT_UP);
  } else if (line == "down" || line == "d") {
    navInjectEvent(NAV_EVENT_DOWN);
  } else if (line == "click" || line == "c") {
    navInjectEvent(NAV_EVENT_CLICK);
  } else if (line == "ptt") {
    navInjectEvent(NAV_EVENT_PTT_START);
  } else if (line == "rel" || line == "release") {
    navInjectEvent(NAV_EVENT_PTT_END);
  } else if (line == "home" || line == "h") {
    gModel.goHome();
    einkRequestRefresh();
  } else if (line == "demo") {
    aiExecuteOfflineDemo();
  } else if (line.startsWith("turn ")) {
    String text = line.substring(5);
    aiProcessTurn(text.c_str());
  } else if (line == "status") {
    Serial.printf("Heap Free: %u bytes, PSRAM Free: %u bytes\n", ESP.getFreeHeap(), ESP.getFreePsram());
    Serial.printf("Current Screen: %d, App ID: '%s'\n", gModel.getScreen(), gModel.getCurrentApp() ? gModel.getCurrentApp()->id.c_str() : "none");
    Serial.printf("Wi-Fi Connected: %s (IP: %s)\n", wifiIsConnected() ? "YES" : "NO", WiFi.localIP().toString().c_str());
  } else if (line == "reset") {
    gModel.loadDefaults();
    gModel.saveToStorage();
    einkRequestRefresh();
    Serial.println("Reset apps to defaults");
  } else {
    Serial.println("Available commands: up, down, click, ptt, rel, home, demo, turn <text>, status, reset");
  }
}

void setup() {
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_LED, HIGH); // XIAO user LED is active-low

  Serial.begin(115200);
  uint32_t startWait = millis();
  while (!Serial && (millis() - startWait < 2500)) {
    delay(10);
  }

  checkStrappingPinsAtBoot();

  Serial.println("main: initializing navigation button switch...");
  navInit();

  Serial.println("main: initializing app model & storage...");
  gModel.init();

  Serial.println("main: initializing I2S microphone...");
  micInit();

  Serial.println("main: initializing E-Ink display...");
  einkInit();

  Serial.println("main: connecting to Wi-Fi...");
  wifiConnect();

  Serial.println("main: initializing AI agent subsystem...");
  aiInit();

  Serial.println("main: system ready. Turn thumbwheel or hold center button to speak.\n");
}

void loop() {
  // 1. Sample navigation thumbwheel switch
  navUpdate();

  // 2. Poll and dispatch navigation events
  NavEvent evt;
  while (navPollEvent(evt)) {
    Serial.printf("nav: event -> %s\n", navEventToString(evt));

    switch (evt) {
      case NAV_EVENT_UP:
        if (gModel.handleNavUp()) {
          einkRequestRefresh();
        }
        break;

      case NAV_EVENT_DOWN:
        if (gModel.handleNavDown()) {
          einkRequestRefresh();
        }
        break;

      case NAV_EVENT_CLICK:
        if (gModel.handleNavClick()) {
          einkRequestRefresh();
        }
        break;

      case NAV_EVENT_PTT_START:
        gModel.setAgentState(AGENT_LISTENING);
        micStartRecording();
        einkRequestRefresh();
        break;

      case NAV_EVENT_PTT_END:
        micStopRecording();
        gModel.setAgentState(AGENT_THINKING);
        einkRequestRefresh();
        aiProcessTurn();
        break;

      default:
        break;
    }
  }

  // 3. Audio stream capture while PTT active
  if (micIsRecording()) {
    micUpdateRecording();
  }

  // 4. Update and paint E-Ink display with coalescing
  einkUpdate();

  // 5. Interactive Serial CLI
  processSerialCommands();

  // 6. Heartbeat LED (blinks slowly when idle, fast when recording)
  uint32_t now = millis();
  uint32_t blinkInterval = navIsPttActive() ? 100 : 750;
  if (now - sLastHeartbeat >= blinkInterval) {
    sLastHeartbeat = now;
    sLedState = !sLedState;
    digitalWrite(PIN_LED, sLedState ? LOW : HIGH);
  }

  delay(2);
}
