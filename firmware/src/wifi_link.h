#pragma once

// ufdevice is UF's hidden network for registered devices. The password is public.
#define WIFI_SSID "ufdevice"
#define WIFI_PASSWORD "gogators"

// Prints progress on Serial. Returns true once an address is assigned.
// A true result still prints whether the internet check passed.
bool wifiConnect();
