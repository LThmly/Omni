#include "app_model.h"
#include <Preferences.h>
#include <algorithm>

AppModel gModel;

static Preferences sPrefs;

AppModel::AppModel()
  : mScreen(SCREEN_HOME),
    mAgentState(AGENT_IDLE),
    mSayLine("Ready when you are"),
    mCurrentAppId(""),
    mLauncherCursor(0),
    mHasProposal(false),
    mProposalTitle(""),
    mProposalQuestion(""),
    mProposalAppId(""),
    mProposalModule(""),
    mProposalSelection(0) {
}

void AppModel::init() {
  restoreFromStorage();
  if (mRegistry.empty()) {
    loadDefaults();
  }
}

void AppModel::loadDefaults() {
  mRegistry.clear();

  // 1. Shopping List (Checklist)
  App shopping;
  shopping.id = "shopping";
  shopping.title = "Shopping List";
  shopping.module = "checklist";
  shopping.cursor = 0;
  shopping.items.push_back({ "item_1", "Milk", false });
  shopping.items.push_back({ "item_2", "Eggs", false });
  shopping.items.push_back({ "item_3", "Coffee", true });
  mRegistry.push_back(shopping);

  // 2. Scoreboard (Ping Pong)
  App score;
  score.id = "scoreboard";
  score.title = "Ping Pong Score";
  score.module = "scoreboard";
  score.cursor = 0;
  score.sides.push_back({ "Me", 11 });
  score.sides.push_back({ "Alex", 9 });
  mRegistry.push_back(score);

  // 3. Hydration Tracker (Progress)
  App hydration;
  hydration.id = "hydration";
  hydration.title = "Hydration Tracker";
  hydration.module = "progress";
  hydration.cursor = 0;
  hydration.progressLabel = "Water";
  hydration.progressUnit = "oz";
  hydration.progressValue = 16.0f;
  hydration.progressGoal = 64.0f;
  hydration.progressStep = 8.0f;
  mRegistry.push_back(hydration);

  // 4. Notes
  App notes;
  notes.id = "notes";
  notes.title = "Notes";
  notes.module = "checklist";
  notes.cursor = 0;
  notes.items.push_back({ "note_1", "Buy Adafruit 6382", true });
  notes.items.push_back({ "note_2", "Check D19 thumbwheel pad", false });
  mRegistry.push_back(notes);

  mScreen = SCREEN_HOME;
  mCurrentAppId = "";
  mLauncherCursor = 0;
  mSayLine = "Ready when you are";
  mAgentState = AGENT_IDLE;
}

void AppModel::saveToStorage() {
  sPrefs.begin("omni_apps", false);
  sPrefs.putUInt("app_count", mRegistry.size());

  for (size_t i = 0; i < mRegistry.size(); i++) {
    const App& app = mRegistry[i];
    String prefix = "app_" + String(i) + "_";
    sPrefs.putString((prefix + "id").c_str(), app.id);
    sPrefs.putString((prefix + "title").c_str(), app.title);
    sPrefs.putString((prefix + "mod").c_str(), app.module);

    if (app.module == "checklist") {
      sPrefs.putUInt((prefix + "n_items").c_str(), app.items.size());
      for (size_t j = 0; j < app.items.size(); j++) {
        String itemPrefix = prefix + "it_" + String(j) + "_";
        sPrefs.putString((itemPrefix + "lbl").c_str(), app.items[j].label);
        sPrefs.putBool((itemPrefix + "chk").c_str(), app.items[j].checked);
      }
    } else if (app.module == "scoreboard") {
      sPrefs.putUInt((prefix + "n_sides").c_str(), app.sides.size());
      for (size_t j = 0; j < app.sides.size(); j++) {
        String sidePrefix = prefix + "sd_" + String(j) + "_";
        sPrefs.putString((sidePrefix + "name").c_str(), app.sides[j].name);
        sPrefs.putInt((sidePrefix + "score").c_str(), app.sides[j].score);
      }
    } else if (app.module == "progress") {
      sPrefs.putString((prefix + "lbl").c_str(), app.progressLabel);
      sPrefs.putString((prefix + "unit").c_str(), app.progressUnit);
      sPrefs.putFloat((prefix + "val").c_str(), app.progressValue);
      sPrefs.putFloat((prefix + "goal").c_str(), app.progressGoal);
      sPrefs.putFloat((prefix + "step").c_str(), app.progressStep);
    }
  }
  sPrefs.end();
}

void AppModel::restoreFromStorage() {
  sPrefs.begin("omni_apps", true);
  uint32_t count = sPrefs.getUInt("app_count", 0);
  if (count == 0 || count > 20) {
    sPrefs.end();
    return;
  }

  mRegistry.clear();
  for (uint32_t i = 0; i < count; i++) {
    App app;
    String prefix = "app_" + String(i) + "_";
    app.id = sPrefs.getString((prefix + "id").c_str(), "");
    app.title = sPrefs.getString((prefix + "title").c_str(), "");
    app.module = sPrefs.getString((prefix + "mod").c_str(), "checklist");
    app.cursor = 0;

    if (app.id.length() == 0) continue;

    if (app.module == "checklist") {
      uint32_t nItems = sPrefs.getUInt((prefix + "n_items").c_str(), 0);
      for (uint32_t j = 0; j < nItems && j < 30; j++) {
        String itemPrefix = prefix + "it_" + String(j) + "_";
        ChecklistItem it;
        it.id = "item_" + String(j);
        it.label = sPrefs.getString((itemPrefix + "lbl").c_str(), "");
        it.checked = sPrefs.getBool((itemPrefix + "chk").c_str(), false);
        app.items.push_back(it);
      }
    } else if (app.module == "scoreboard") {
      uint32_t nSides = sPrefs.getUInt((prefix + "n_sides").c_str(), 0);
      for (uint32_t j = 0; j < nSides && j < 4; j++) {
        String sidePrefix = prefix + "sd_" + String(j) + "_";
        ScoreSide sd;
        sd.name = sPrefs.getString((sidePrefix + "name").c_str(), "");
        sd.score = sPrefs.getInt((sidePrefix + "score").c_str(), 0);
        app.sides.push_back(sd);
      }
    } else if (app.module == "progress") {
      app.progressLabel = sPrefs.getString((prefix + "lbl").c_str(), "Goal");
      app.progressUnit = sPrefs.getString((prefix + "unit").c_str(), "pts");
      app.progressValue = sPrefs.getFloat((prefix + "val").c_str(), 0.0f);
      app.progressGoal = sPrefs.getFloat((prefix + "goal").c_str(), 100.0f);
      app.progressStep = sPrefs.getFloat((prefix + "step").c_str(), 10.0f);
    }
    mRegistry.push_back(app);
  }
  sPrefs.end();
}

App* AppModel::getApp(size_t index) {
  if (index < mRegistry.size()) {
    return &mRegistry[index];
  }
  return nullptr;
}

App* AppModel::getAppById(const String& id) {
  for (size_t i = 0; i < mRegistry.size(); i++) {
    if (mRegistry[i].id == id) {
      return &mRegistry[i];
    }
  }
  return nullptr;
}

App* AppModel::getCurrentApp() {
  if (mScreen != SCREEN_APP || mCurrentAppId.isEmpty()) {
    return nullptr;
  }
  return getAppById(mCurrentAppId);
}

void AppModel::openApp(const String& id) {
  App* app = getAppById(id);
  if (app != nullptr) {
    mCurrentAppId = id;
    mScreen = SCREEN_APP;
    app->cursor = 0;
  }
}

void AppModel::goHome() {
  mScreen = SCREEN_HOME;
  mCurrentAppId = "";
}

// ==============================================================================
// Navigation Button Event Handlers
// ==============================================================================

bool AppModel::handleNavUp() {
  if (mScreen == SCREEN_HOME) {
    if (!mRegistry.empty()) {
      int count = static_cast<int>(mRegistry.size());
      mLauncherCursor = (mLauncherCursor - 1 + count) % count;
      return true;
    }
  } else if (mScreen == SCREEN_PROPOSAL) {
    mProposalSelection = (mProposalSelection == 0) ? 1 : 0;
    return true;
  } else if (mScreen == SCREEN_APP) {
    App* app = getCurrentApp();
    if (!app) return false;

    // Cursor -1 is "< Back to Home"
    if (app->cursor > -1) {
      app->cursor--;
      return true;
    }
  }
  return false;
}

bool AppModel::handleNavDown() {
  if (mScreen == SCREEN_HOME) {
    if (!mRegistry.empty()) {
      int count = static_cast<int>(mRegistry.size());
      mLauncherCursor = (mLauncherCursor + 1) % count;
      return true;
    }
  } else if (mScreen == SCREEN_PROPOSAL) {
    mProposalSelection = (mProposalSelection == 0) ? 1 : 0;
    return true;
  } else if (mScreen == SCREEN_APP) {
    App* app = getCurrentApp();
    if (!app) return false;

    int maxCursor = 0;
    if (app->module == "checklist") {
      maxCursor = static_cast<int>(app->items.size()) - 1;
    } else if (app->module == "scoreboard") {
      maxCursor = static_cast<int>(app->sides.size()) - 1;
    } else if (app->module == "progress") {
      maxCursor = 1; // 0 = +step, 1 = +2*step
    }

    if (app->cursor < maxCursor) {
      app->cursor++;
      return true;
    }
  }
  return false;
}

bool AppModel::handleNavClick() {
  if (mScreen == SCREEN_HOME) {
    if (mLauncherCursor >= 0 && mLauncherCursor < static_cast<int>(mRegistry.size())) {
      openApp(mRegistry[mLauncherCursor].id);
      return true;
    }
  } else if (mScreen == SCREEN_PROPOSAL) {
    if (mProposalSelection == 0) {
      confirmProposal();
    } else {
      cancelProposal();
    }
    return true;
  } else if (mScreen == SCREEN_APP) {
    App* app = getCurrentApp();
    if (!app) return false;

    if (app->cursor == -1) {
      // Header Back button clicked
      goHome();
      return true;
    }

    if (app->module == "checklist") {
      if (app->cursor >= 0 && app->cursor < static_cast<int>(app->items.size())) {
        app->items[app->cursor].checked = !app->items[app->cursor].checked;
        saveToStorage();
        return true;
      }
    } else if (app->module == "scoreboard") {
      if (app->cursor >= 0 && app->cursor < static_cast<int>(app->sides.size())) {
        app->sides[app->cursor].score++;
        saveToStorage();
        return true;
      }
    } else if (app->module == "progress") {
      if (app->cursor == 0) {
        app->progressValue = min(app->progressGoal, app->progressValue + app->progressStep);
      } else if (app->cursor == 1) {
        app->progressValue = min(app->progressGoal, app->progressValue + (app->progressStep * 2));
      }
      saveToStorage();
      return true;
    }
  }
  return false;
}

// ==============================================================================
// Proposal Confirmation & Cancellation
// ==============================================================================

void AppModel::confirmProposal() {
  if (!mHasProposal) return;

  App newApp;
  newApp.id = mProposalAppId.isEmpty() ? ("app_" + String(millis())) : mProposalAppId;
  newApp.title = mProposalTitle.isEmpty() ? "New App" : mProposalTitle;
  newApp.module = mProposalModule.isEmpty() ? "checklist" : mProposalModule;
  newApp.cursor = 0;

  if (mProposedAppDoc.is<JsonObject>()) {
    JsonObject appObj = mProposedAppDoc.as<JsonObject>();
    if (appObj["state"].is<JsonObject>()) {
      JsonObject state = appObj["state"];
      if (newApp.module == "checklist" && state["items"].is<JsonArray>()) {
        for (JsonObject item : state["items"].as<JsonArray>()) {
          ChecklistItem it;
          it.id = item["id"].as<String>();
          it.label = item["label"].as<String>();
          it.checked = item["checked"].as<bool>();
          newApp.items.push_back(it);
        }
      } else if (newApp.module == "scoreboard" && state["sides"].is<JsonArray>()) {
        for (JsonObject side : state["sides"].as<JsonArray>()) {
          ScoreSide sd;
          sd.name = side["name"].as<String>();
          sd.score = side["score"].as<int>();
          newApp.sides.push_back(sd);
        }
      } else if (newApp.module == "progress") {
        newApp.progressLabel = state["label"] | "Goal";
        newApp.progressUnit = state["unit"] | "pts";
        newApp.progressValue = state["value"] | 0.0f;
        newApp.progressGoal = state["goal"] | 100.0f;
        newApp.progressStep = state["step"] | 10.0f;
      }
    }
  }

  // If no items were populated, provide a helpful default item
  if (newApp.module == "checklist" && newApp.items.empty()) {
    newApp.items.push_back({ "it_1", "First item", false });
  }

  // Update existing or add new
  bool replaced = false;
  for (size_t i = 0; i < mRegistry.size(); i++) {
    if (mRegistry[i].id == newApp.id) {
      mRegistry[i] = newApp;
      replaced = true;
      break;
    }
  }
  if (!replaced) {
    mRegistry.push_back(newApp);
  }

  saveToStorage();
  mHasProposal = false;
  mAgentState = AGENT_IDLE;
  openApp(newApp.id);
}

void AppModel::cancelProposal() {
  mHasProposal = false;
  mAgentState = AGENT_IDLE;
  goHome();
}

// ==============================================================================
// Turn Application (propose, mutate, say, navigate)
// ==============================================================================

bool AppModel::applyTurn(const JsonDocument& turnDoc) {
  const char* op = turnDoc["op"] | "";
  const char* say = turnDoc["say"] | "";

  if (say && say[0]) {
    mSayLine = say;
  }
  mAgentState = AGENT_RESPONDING;

  if (strcmp(op, "propose") == 0) {
    JsonObject app = turnDoc["app"];
    if (!app.isNull()) {
      mHasProposal = true;
      mProposalAppId = app["id"] | "new_app";
      mProposalTitle = app["title"] | "New App";
      mProposalModule = app["module"] | "checklist";
      mProposalQuestion = mSayLine.isEmpty() ? ("Create " + mProposalTitle + "?") : mSayLine;
      mProposalSelection = 0; // Default to Yes
      mProposedAppDoc.set(app);
      mScreen = SCREEN_PROPOSAL;
      return true;
    }
  } else if (strcmp(op, "mutate") == 0) {
    const char* appId = turnDoc["app_id"] | "";
    App* app = getAppById(appId);
    if (app) {
      JsonArray actions = turnDoc["actions"];
      for (JsonObject act : actions) {
        const char* actionName = act["action"] | "";
        JsonObject args = act["args"];

        if (strcmp(actionName, "toggle") == 0) {
          if (app->module == "checklist" && app->cursor >= 0 && app->cursor < static_cast<int>(app->items.size())) {
            app->items[app->cursor].checked = !app->items[app->cursor].checked;
          }
        } else if (strcmp(actionName, "append") == 0) {
          const char* label = args["label"] | act["value"] | "New item";
          ChecklistItem it;
          it.id = "item_" + String(millis());
          it.label = label;
          it.checked = false;
          app->items.push_back(it);
        } else if (strcmp(actionName, "inc") == 0 || strcmp(actionName, "increment") == 0) {
          if (app->module == "scoreboard" && app->cursor >= 0 && app->cursor < static_cast<int>(app->sides.size())) {
            app->sides[app->cursor].score++;
          }
        } else if (strcmp(actionName, "dec") == 0) {
          if (app->module == "scoreboard" && app->cursor >= 0 && app->cursor < static_cast<int>(app->sides.size())) {
            app->sides[app->cursor].score = max(0, app->sides[app->cursor].score - 1);
          }
        } else if (strcmp(actionName, "add") == 0) {
          float amount = args["amount"] | app->progressStep;
          app->progressValue = min(app->progressGoal, app->progressValue + amount);
        } else if (strcmp(actionName, "remove_checked") == 0) {
          std::vector<ChecklistItem> remaining;
          for (const auto& it : app->items) {
            if (!it.checked) remaining.push_back(it);
          }
          app->items = remaining;
          if (app->cursor >= static_cast<int>(app->items.size())) {
            app->cursor = max(0, static_cast<int>(app->items.size()) - 1);
          }
        }
      }
      saveToStorage();
      openApp(app->id);
      return true;
    }
  } else if (strcmp(op, "navigate") == 0) {
    const char* dest = turnDoc["destination"] | "agent";
    if (strcmp(dest, "agent") == 0 || strcmp(dest, "apps") == 0) {
      goHome();
    } else if (strcmp(dest, "app") == 0) {
      const char* targetId = turnDoc["app_id"] | "";
      openApp(targetId);
    } else {
      openApp(dest);
    }
    return true;
  }

  return true;
}
