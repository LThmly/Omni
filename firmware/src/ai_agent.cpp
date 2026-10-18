#include "ai_agent.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include "config.h"
#include "app_model.h"
#include "eink_display.h"
#include "wifi_link.h"

static int sDemoCycleIndex = 0;

void aiInit() {
  sDemoCycleIndex = 0;
}

void aiExecuteOfflineDemo() {
  Serial.printf("ai: executing offline demo turn (cycle step %d)...\n", sDemoCycleIndex);
  JsonDocument doc;

  switch (sDemoCycleIndex) {
    case 0: {
      // Propose Shopping List
      doc["op"] = "propose";
      doc["say"] = "You don't have a shopping list yet. Make one?";
      JsonObject app = doc["app"].to<JsonObject>();
      app["id"] = "shopping";
      app["title"] = "Shopping List";
      app["module"] = "checklist";
      JsonObject state = app["state"].to<JsonObject>();
      JsonArray items = state["items"].to<JsonArray>();
      JsonObject item1 = items.add<JsonObject>();
      item1["id"] = "item_milk";
      item1["label"] = "Milk";
      item1["checked"] = false;
      break;
    }
    case 1: {
      // Mutate Shopping List: Add Eggs
      doc["op"] = "mutate";
      doc["app_id"] = "shopping";
      doc["say"] = "Added eggs to your shopping list.";
      JsonArray actions = doc["actions"].to<JsonArray>();
      JsonObject act = actions.add<JsonObject>();
      act["action"] = "append";
      JsonObject args = act["args"].to<JsonObject>();
      args["label"] = "Eggs";
      break;
    }
    case 2: {
      // Propose Ping Pong Scoreboard
      doc["op"] = "propose";
      doc["say"] = "Want me to track ping pong scores?";
      JsonObject app = doc["app"].to<JsonObject>();
      app["id"] = "scoreboard";
      app["title"] = "Ping Pong Score";
      app["module"] = "scoreboard";
      JsonObject state = app["state"].to<JsonObject>();
      JsonArray sides = state["sides"].to<JsonArray>();
      JsonObject side1 = sides.add<JsonObject>();
      side1["name"] = "Me";
      side1["score"] = 0;
      JsonObject side2 = sides.add<JsonObject>();
      side2["name"] = "Alex";
      side2["score"] = 0;
      break;
    }
    case 3: {
      // Propose Hydration Tracker
      doc["op"] = "propose";
      doc["say"] = "Tracking 64 ounces daily goal.";
      JsonObject app = doc["app"].to<JsonObject>();
      app["id"] = "hydration";
      app["title"] = "Hydration Tracker";
      app["module"] = "progress";
      JsonObject state = app["state"].to<JsonObject>();
      state["label"] = "Water";
      state["unit"] = "oz";
      state["value"] = 16.0f;
      state["goal"] = 64.0f;
      state["step"] = 8.0f;
      break;
    }
    default: {
      // Say turn
      doc["op"] = "say";
      doc["say"] = "Ready for your next request!";
      break;
    }
  }

  sDemoCycleIndex = (sDemoCycleIndex + 1) % 4;

  gModel.applyTurn(doc);
  einkRequestRefresh();
}

void aiProcessTurn(const char* explicitText) {
  gModel.setAgentState(AGENT_THINKING);
  einkRequestRefresh();

  // If Wi-Fi is disconnected or offline demo is forced, run offline cycle
  if (!wifiIsConnected() || ENABLE_OFFLINE_DEMO) {
    delay(400); // Simulate network thinking time
    aiExecuteOfflineDemo();
    return;
  }

  // If online, dispatch HTTP request to cloud turn endpoint
  Serial.printf("ai: posting turn to %s...\n", CLOUD_TURN_URL);
  HTTPClient http;
  http.begin(CLOUD_TURN_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(12000);

  JsonDocument requestDoc;
  requestDoc["text"] = explicitText ? explicitText : "Add milk to my shopping list";
  
  // Attach current registry
  JsonArray reg = requestDoc["registry"].to<JsonArray>();
  for (size_t i = 0; i < gModel.getAppCount(); i++) {
    App* a = gModel.getApp(i);
    if (a) {
      JsonObject item = reg.add<JsonObject>();
      item["id"] = a->id;
      item["title"] = a->title;
      item["module"] = a->module;
    }
  }

  String requestBody;
  serializeJson(requestDoc, requestBody);

  int httpCode = http.POST(requestBody);
  if (httpCode == 200) {
    String response = http.getString();
    JsonDocument replyDoc;
    DeserializationError err = deserializeJson(replyDoc, response);
    if (!err) {
      gModel.applyTurn(replyDoc);
      einkRequestRefresh();
      http.end();
      return;
    }
  }

  Serial.printf("ai: HTTP error %d or JSON parse failed. Falling back to demo...\n", httpCode);
  http.end();
  aiExecuteOfflineDemo();
}
