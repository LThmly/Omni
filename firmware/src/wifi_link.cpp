#include "wifi_link.h"

#include <HTTPClient.h>
#include <WiFi.h>
#include <lwip/dns.h>

static volatile int lastDisconnectReason = 0;

static void onWifiEvent(WiFiEvent_t event, WiFiEventInfo_t info) {
  if (event == ARDUINO_EVENT_WIFI_STA_DISCONNECTED) {
    lastDisconnectReason = info.wifi_sta_disconnected.reason;
  }
}

static const char* disconnectReasonText(int reason) {
  switch (reason) {
    case 201: return "no access point found";
    case 202: return "authentication rejected";
    case 203: return "association rejected";
    case 15:
    case 204: return "handshake failed";
    default: return "see reason number";
  }
}

static const char* wifiStatusText(wl_status_t status) {
  switch (status) {
    case WL_IDLE_STATUS: return "joined, waiting for an address";
    case WL_NO_SSID_AVAIL: return "network not found";
    case WL_CONNECTED: return "connected";
    case WL_CONNECT_FAILED: return "connection failed";
    case WL_CONNECTION_LOST: return "connection lost";
    case WL_DISCONNECTED: return "disconnected";
    default: return "starting";
  }
}

static void setDns(IPAddress primary, IPAddress secondary) {
  ip_addr_t dns;
  dns.type = IPADDR_TYPE_V4;
  dns.u_addr.ip4.addr = static_cast<uint32_t>(primary);
  dns_setserver(0, &dns);
  dns.u_addr.ip4.addr = static_cast<uint32_t>(secondary);
  dns_setserver(1, &dns);
  Serial.printf("dns: using %s, %s\n", primary.toString().c_str(), secondary.toString().c_str());
}

static bool lookupGoogle(IPAddress& ip) {
  if (!WiFi.hostByName("google.com", ip)) {
    Serial.println("dns: google.com failed");
    return false;
  }
  Serial.print("dns: google.com ");
  Serial.println(ip);
  return true;
}

static void checkInternet() {
  Serial.printf("wifi: gateway %s dns %s\n",
                WiFi.gatewayIP().toString().c_str(),
                WiFi.dnsIP().toString().c_str());

  IPAddress ip;
  bool resolved = lookupGoogle(ip);
  if (!resolved) {
    // Campus DHCP sometimes hands out an address and no resolver.
    setDns(IPAddress(128, 227, 30, 254), IPAddress(8, 6, 245, 30));
    resolved = lookupGoogle(ip);
  }
  if (!resolved) {
    setDns(IPAddress(8, 8, 8, 8), IPAddress(1, 1, 1, 1));
    resolved = lookupGoogle(ip);
  }
  if (!resolved) {
    return;
  }

  HTTPClient http;
  http.setTimeout(8000);
  http.begin("http://connectivitycheck.gstatic.com/generate_204");
  int code = http.GET();
  Serial.printf("http: generate_204 -> %d\n", code);
  http.end();
}

bool wifiConnect() {
  if (WIFI_SSID[0] == '\0') {
    Serial.println("wifi: WIFI_SSID is empty");
    return false;
  }

  WiFi.persistent(false);
  WiFi.onEvent(onWifiEvent);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  // Hidden networks are missed by the default scan, which only reads beacons.
  WiFi.setScanMethod(WIFI_ALL_CHANNEL_SCAN);

  Serial.printf("wifi: mac %s\n", WiFi.macAddress().c_str());
  Serial.printf("wifi: joining %s\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  uint32_t start = millis();
  wl_status_t shown = WL_NO_SHIELD;
  while (WiFi.status() != WL_CONNECTED && millis() - start < 45000) {
    wl_status_t now = WiFi.status();
    if (now != shown) {
      Serial.printf("\nwifi: %s\n", wifiStatusText(now));
      shown = now;
    }
    delay(250);
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("wifi: ");
    Serial.println(WiFi.localIP());
    checkInternet();
    return true;
  }
  if (WiFi.status() == WL_IDLE_STATUS) {
    Serial.printf("wifi: joined %s, but no IP address arrived\n", WIFI_SSID);
    return false;
  }
  Serial.printf("wifi: failed, status %d (%s), reason %d (%s)\n",
                WiFi.status(), wifiStatusText(WiFi.status()),
                lastDisconnectReason, disconnectReasonText(lastDisconnectReason));
  return false;
}
