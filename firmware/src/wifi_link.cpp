#include "wifi_link.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <lwip/dns.h>
#include "config.h"

static volatile int sLastDisconnectReason = 0;

static void onWifiEvent(WiFiEvent_t event, WiFiEventInfo_t info) {
  if (event == ARDUINO_EVENT_WIFI_STA_DISCONNECTED) {
    sLastDisconnectReason = info.wifi_sta_disconnected.reason;
  }
}

bool wifiIsConnected() {
  return (WiFi.status() == WL_CONNECTED);
}

void wifiCheckInternet() {
  if (!wifiIsConnected()) return;

  HTTPClient http;
  http.setTimeout(5000);
  http.begin("http://connectivitycheck.gstatic.com/generate_204");
  int code = http.GET();
  Serial.printf("wifi: connectivity check -> %d\n", code);
  http.end();
}

bool wifiConnect() {
  if (String(WIFI_SSID).isEmpty()) {
    Serial.println("wifi: SSID is empty");
    return false;
  }

  WiFi.persistent(false);
  WiFi.onEvent(onWifiEvent);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setScanMethod(WIFI_ALL_CHANNEL_SCAN);

  Serial.printf("wifi: MAC %s\n", WiFi.macAddress().c_str());
  Serial.printf("wifi: joining '%s'...\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - start < 15000)) {
    delay(250);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("wifi: connected! IP: %s\n", WiFi.localIP().toString().c_str());
    wifiCheckInternet();
    return true;
  }

  Serial.printf("wifi: connection timed out (reason: %d)\n", sLastDisconnectReason);
  return false;
}
