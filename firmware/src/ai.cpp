#include "ai.h"

#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

#include "ai_schema.h"

#if __has_include("gemini_key.h")
#include "gemini_key.h"
#else
#define GEMINI_API_KEY ""
#define GEMINI_MODEL "gemini-3.8-flash"
#endif

static const char AI_SYSTEM[] = R"SYS(You fill one Omni turn for a pocket e-ink device.

Modules already on the device are listed in registry. Each has an id.
checklist: items with label and checked. scoreboard: two sides with name and score.
progress: label, unit, value, goal, step. key_value: rows of label and value.

propose when no registry app covers the request. confirm is true. say is a short question. Invent a short id.
mutate when a registry app covers it. Use that app's id. append sets args.label. add sets args.amount. Other actions leave both args null.
say when the request is not one of these apps.

cursor starts at 0. Scores start at 0.)SYS";

static void stripNulls(JsonVariant value) {
  if (value.is<JsonObject>()) {
    JsonObject object = value.as<JsonObject>();
    String drop[24];
    int count = 0;
    for (JsonPair field : object) {
      if (field.value().isNull()) {
        if (count < 24) drop[count++] = field.key().c_str();
      } else {
        stripNulls(field.value());
      }
    }
    for (int i = 0; i < count; i++) object.remove(drop[i]);
  } else if (value.is<JsonArray>()) {
    for (JsonVariant item : value.as<JsonArray>()) stripNulls(item);
  }
}

static bool buildBody(const char* text, const char* registryJson, String& body) {
  JsonDocument user;
  user["text"] = text ? text : "";
  JsonDocument registry;
  if (deserializeJson(registry, registryJson && registryJson[0] ? registryJson : "[]")) {
    registry.to<JsonArray>();
  }
  user["registry"] = registry.as<JsonVariant>();

  String userText;
  serializeJson(user, userText);

  JsonDocument request;
  request["systemInstruction"]["parts"][0]["text"] = AI_SYSTEM;
  request["contents"][0]["role"] = "user";
  request["contents"][0]["parts"][0]["text"] = userText;
  request["generationConfig"]["responseMimeType"] = "application/json";
  request["generationConfig"]["responseJsonSchema"] = serialized(AI_SCHEMA);
  return serializeJson(request, body) > 0;
}

static bool readTurn(const String& reply, String& turnJson) {
  JsonDocument filter;
  filter["candidates"][0]["content"]["parts"][0]["text"] = true;
  filter["error"]["message"] = true;

  JsonDocument doc;
  if (deserializeJson(doc, reply, DeserializationOption::Filter(filter))) {
    Serial.println("ai: bad response");
    return false;
  }

  const char* message = doc["error"]["message"];
  if (message && message[0]) {
    Serial.printf("ai: %s\n", message);
    return false;
  }

  const char* text = doc["candidates"][0]["content"]["parts"][0]["text"];
  if (!text || !text[0]) {
    Serial.println("ai: empty reply");
    return false;
  }

  JsonDocument wrapped;
  if (deserializeJson(wrapped, text)) {
    Serial.println("ai: reply was not json");
    return false;
  }

  JsonVariant turn = wrapped.as<JsonVariant>();
  if (wrapped["turn"].is<JsonObject>()) turn = wrapped["turn"];
  stripNulls(turn);
  turnJson = "";
  serializeJson(turn, turnJson);
  return turnJson.length() > 0;
}

bool aiAsk(const char* text, const char* registryJson, String& turnJson) {
  if (GEMINI_API_KEY[0] == '\0') {
    Serial.println("ai: put GEMINI_API_KEY in src/gemini_key.h");
    return false;
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("ai: no wifi");
    return false;
  }

  String body;
  if (!buildBody(text, registryJson, body)) {
    Serial.println("ai: could not build the request");
    return false;
  }

  WiFiClientSecure client;
  client.setInsecure();
  client.setHandshakeTimeout(30);
  client.setTimeout(60);

  HTTPClient http;
  http.setTimeout(60000);
  http.setConnectTimeout(15000);
  const char* url =
      "https://aiplatform.googleapis.com/v1/publishers/google/models/" GEMINI_MODEL ":generateContent";
  if (!http.begin(client, url)) {
    Serial.println("ai: bad url");
    return false;
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("x-goog-api-key", GEMINI_API_KEY);

  int code = http.POST(reinterpret_cast<uint8_t*>(const_cast<char*>(body.c_str())), body.length());
  String reply = http.getString();
  if (code < 0) {
    Serial.printf("ai: %s\n", http.errorToString(code).c_str());
    http.end();
    return false;
  }
  http.end();
  if (code != 200) {
    Serial.printf("ai: http %d\n", code);
    if (reply.length()) Serial.println(reply);
    return false;
  }
  return readTurn(reply, turnJson);
}
