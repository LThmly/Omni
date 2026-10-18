#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include <vector>

// ==============================================================================
// App & Screen Model
// Translates logic.py and contract/runtime.py for the ESP32 E-Ink shell.
// ==============================================================================

enum ScreenType {
  SCREEN_HOME = 0,     // Main Agent View: Agent bar + App launcher
  SCREEN_APP,          // Active App View
  SCREEN_PROPOSAL,     // App Genesis Confirmation Dialog
  SCREEN_SETTINGS      // Settings & Hardware Diagnostics
};

enum AgentState {
  AGENT_IDLE = 0,
  AGENT_LISTENING,
  AGENT_THINKING,
  AGENT_RESPONDING
};

// Checklist Item
struct ChecklistItem {
  String id;
  String label;
  bool checked;
};

// Scoreboard Side
struct ScoreSide {
  String name;
  int score;
};

// Application Data Model
struct App {
  String id;
  String title;
  String module;       // "checklist", "scoreboard", "progress", "composed"
  
  // Checklist State
  std::vector<ChecklistItem> items;
  
  // Scoreboard State
  std::vector<ScoreSide> sides;
  
  // Progress State
  String progressLabel;
  String progressUnit;
  float progressValue;
  float progressGoal;
  float progressStep;
  
  // Generic / Composed State (Raw JSON state for flexible component bindings)
  String rawJson;

  // Active Navigation Cursor within this app (-1 = Back to Home header)
  int cursor;
};

class AppModel {
public:
  AppModel();

  void init();
  void loadDefaults();
  void saveToStorage();
  void restoreFromStorage();

  // Screen & Navigation
  ScreenType getScreen() const { return mScreen; }
  void setScreen(ScreenType s) { mScreen = s; }
  
  AgentState getAgentState() const { return mAgentState; }
  void setAgentState(AgentState state) { mAgentState = state; }
  
  const String& getSayLine() const { return mSayLine; }
  void setSayLine(const String& say) { mSayLine = say; }

  // App Registry Access
  size_t getAppCount() const { return mRegistry.size(); }
  App* getApp(size_t index);
  App* getAppById(const String& id);
  App* getCurrentApp();

  // Launcher Cursor
  int getLauncherCursor() const { return mLauncherCursor; }

  // Proposal State
  bool hasProposal() const { return mHasProposal; }
  const String& getProposalTitle() const { return mProposalTitle; }
  const String& getProposalQuestion() const { return mProposalQuestion; }
  int getProposalSelection() const { return mProposalSelection; } // 0 = Yes, 1 = Cancel

  // Navigation Button Handlers
  bool handleNavUp();
  bool handleNavDown();
  bool handleNavClick();

  // Network Turn Application (propose, mutate, say, navigate)
  bool applyTurn(const JsonDocument& turnDoc);

  // Proposal Confirmation / Dismissal
  void confirmProposal();
  void cancelProposal();

  // Navigation Helpers
  void openApp(const String& id);
  void goHome();

private:
  ScreenType mScreen;
  AgentState mAgentState;
  String mSayLine;
  String mCurrentAppId;
  int mLauncherCursor;

  // Proposal Storage
  bool mHasProposal;
  String mProposalTitle;
  String mProposalQuestion;
  String mProposalAppId;
  String mProposalModule;
  int mProposalSelection;
  JsonDocument mProposedAppDoc;

  std::vector<App> mRegistry;
};

extern AppModel gModel;
