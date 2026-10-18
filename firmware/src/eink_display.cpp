#include "eink_display.h"
#include <SPI.h>
#include <Adafruit_ThinkInk.h>
#include <algorithm>
#include "pins.h"
#include "config.h"
#include "app_model.h"
#include "nav_switch.h"
#include "wifi_link.h"

static ThinkInk_420_Tricolor_MFGNR sPanel(PIN_EPD_DC, PIN_EPD_RST, PIN_EPD_CS, -1, PIN_EPD_BUSY, &SPI);

static bool sNeedsRefresh = false;
static uint32_t sLastRefreshRequest = 0;
static bool sIsBusy = false;

bool einkIsBusy() {
  return digitalRead(PIN_EPD_BUSY) == HIGH;
}

void einkInit() {
  Serial.println("eink: initializing panel...");
  sPanel.begin(THINKINK_TRICOLOR);

  // Set up custom SPI routing: SCK on D8, MOSI on D10. D9 is BUSY input.
  SPI.end();
  SPI.begin(PIN_EPD_SCK, -1, PIN_EPD_MOSI, -1);
  pinMode(PIN_EPD_BUSY, INPUT);

  sPanel.setRotation(DISPLAY_ROTATION);
  Serial.printf("eink: display ready (%dx%d)\n", sPanel.width(), sPanel.height());

  einkRefreshNow();
}

void einkRequestRefresh() {
  sNeedsRefresh = true;
  sLastRefreshRequest = millis();
}

static void drawHeader() {
  int w = sPanel.width();
  sPanel.setTextColor(EPD_BLACK);
  sPanel.setTextSize(1);
  sPanel.setCursor(12, 10);
  sPanel.print("OMNI COMPANION");

  // Wi-Fi Status
  sPanel.setCursor(w - 75, 10);
  if (wifiIsConnected()) {
    sPanel.print("[WiFi OK]");
  } else {
    sPanel.setTextColor(EPD_RED);
    sPanel.print("[Offline]");
  }

  // Header separator line
  sPanel.drawLine(0, 24, w, 24, EPD_BLACK);
}

static void drawAgentCard() {
  int w = sPanel.width();
  AgentState state = gModel.getAgentState();
  const String& say = gModel.getSayLine();

  // Agent Card Frame
  sPanel.drawRoundRect(10, 32, w - 20, 68, 6, EPD_BLACK);

  // State Badge
  int badgeY = 38;
  if (state == AGENT_LISTENING || navIsPttActive()) {
    sPanel.fillRoundRect(16, badgeY, 96, 16, 4, EPD_RED);
    sPanel.setTextColor(EPD_WHITE);
    sPanel.setCursor(22, badgeY + 4);
    sPanel.print("* LISTENING");
  } else if (state == AGENT_THINKING) {
    sPanel.drawRoundRect(16, badgeY, 96, 16, 4, EPD_RED);
    sPanel.setTextColor(EPD_RED);
    sPanel.setCursor(20, badgeY + 4);
    sPanel.print("THINKING...");
  } else if (state == AGENT_RESPONDING) {
    sPanel.fillRoundRect(16, badgeY, 96, 16, 4, EPD_BLACK);
    sPanel.setTextColor(EPD_WHITE);
    sPanel.setCursor(20, badgeY + 4);
    sPanel.print("OMNI AGENT");
  } else {
    sPanel.drawRoundRect(16, badgeY, 80, 16, 4, EPD_BLACK);
    sPanel.setTextColor(EPD_BLACK);
    sPanel.setCursor(22, badgeY + 4);
    sPanel.print("OMNI READY");
  }

  // Say line / Speech text
  sPanel.setTextColor(EPD_BLACK);
  sPanel.setTextSize(1);
  sPanel.setCursor(16, 60);

  if (say.length() > 36) {
    String line1 = say.substring(0, 35);
    String line2 = say.substring(35, min((size_t)70, say.length()));
    sPanel.print(line1);
    sPanel.setCursor(16, 74);
    sPanel.print(line2);
  } else {
    sPanel.print(say.isEmpty() ? "Ready when you are" : say);
  }
}

static void drawHomeView() {
  int w = sPanel.width();
  sPanel.setTextColor(EPD_BLACK);
  sPanel.setTextSize(1);
  sPanel.setCursor(12, 112);
  sPanel.print("INSTALLED APPS (Rotate wheel, click to open)");

  sPanel.drawLine(10, 124, w - 10, 124, EPD_BLACK);

  int y = 132;
  int cursor = gModel.getLauncherCursor();
  size_t count = gModel.getAppCount();

  for (size_t i = 0; i < count && i < 6; i++) {
    App* app = gModel.getApp(i);
    if (!app) continue;

    bool isSelected = (static_cast<int>(i) == cursor);

    if (isSelected) {
      // Highlighted item with RED indicator box
      sPanel.fillRoundRect(10, y, w - 20, 36, 4, EPD_RED);
      sPanel.setTextColor(EPD_WHITE);

      sPanel.setCursor(18, y + 8);
      sPanel.print("> ");
      sPanel.print(app->title);

      sPanel.setCursor(28, y + 22);
      if (app->module == "checklist") {
        sPanel.printf("%d items", app->items.size());
      } else if (app->module == "scoreboard") {
        sPanel.printf("%s vs %s", app->sides.size() > 0 ? app->sides[0].name.c_str() : "A",
                                  app->sides.size() > 1 ? app->sides[1].name.c_str() : "B");
      } else if (app->module == "progress") {
        sPanel.printf("%.0f / %.0f %s", app->progressValue, app->progressGoal, app->progressUnit.c_str());
      }
    } else {
      sPanel.drawRoundRect(10, y, w - 20, 36, 4, EPD_BLACK);
      sPanel.setTextColor(EPD_BLACK);

      sPanel.setCursor(20, y + 8);
      sPanel.print(app->title);

      sPanel.setCursor(28, y + 22);
      if (app->module == "checklist") {
        sPanel.printf("%d items", app->items.size());
      } else if (app->module == "scoreboard") {
        sPanel.printf("%s vs %s", app->sides.size() > 0 ? app->sides[0].name.c_str() : "A",
                                  app->sides.size() > 1 ? app->sides[1].name.c_str() : "B");
      } else if (app->module == "progress") {
        sPanel.printf("%.0f / %.0f %s", app->progressValue, app->progressGoal, app->progressUnit.c_str());
      }
    }
    y += 40;
  }
}

static void drawAppView() {
  int w = sPanel.width();
  App* app = gModel.getCurrentApp();
  if (!app) return;

  // Header Back Button
  bool backSelected = (app->cursor == -1);
  if (backSelected) {
    sPanel.fillRoundRect(10, 108, 90, 20, 4, EPD_RED);
    sPanel.setTextColor(EPD_WHITE);
  } else {
    sPanel.drawRoundRect(10, 108, 90, 20, 4, EPD_BLACK);
    sPanel.setTextColor(EPD_BLACK);
  }
  sPanel.setCursor(16, 114);
  sPanel.print("< Back Home");

  // App Title
  sPanel.setTextColor(EPD_BLACK);
  sPanel.setTextSize(1);
  sPanel.setCursor(110, 114);
  sPanel.print(app->title);

  sPanel.drawLine(10, 132, w - 10, 132, EPD_BLACK);

  // App Contents by Module
  if (app->module == "checklist") {
    int y = 142;
    for (size_t i = 0; i < app->items.size() && i < 7; i++) {
      const ChecklistItem& item = app->items[i];
      bool isSelected = (static_cast<int>(i) == app->cursor);

      if (isSelected) {
        sPanel.fillRoundRect(10, y, w - 20, 28, 4, EPD_RED);
        sPanel.setTextColor(EPD_WHITE);
      } else {
        sPanel.drawRoundRect(10, y, w - 20, 28, 4, EPD_BLACK);
        sPanel.setTextColor(EPD_BLACK);
      }

      // Checkbox [ ] or [X]
      int cbX = 18;
      int cbY = y + 7;
      if (isSelected) {
        sPanel.drawRect(cbX, cbY, 14, 14, EPD_WHITE);
        if (item.checked) {
          sPanel.fillRect(cbX + 3, cbY + 3, 8, 8, EPD_WHITE);
        }
      } else {
        sPanel.drawRect(cbX, cbY, 14, 14, EPD_BLACK);
        if (item.checked) {
          sPanel.fillRect(cbX + 3, cbY + 3, 8, 8, EPD_RED);
        }
      }

      sPanel.setCursor(40, y + 10);
      sPanel.print(item.label);
      y += 32;
    }
  } else if (app->module == "scoreboard") {
    int y = 150;
    for (size_t i = 0; i < app->sides.size() && i < 2; i++) {
      bool isSelected = (static_cast<int>(i) == app->cursor);

      if (isSelected) {
        sPanel.fillRoundRect(16, y, w - 32, 60, 6, EPD_RED);
        sPanel.setTextColor(EPD_WHITE);
      } else {
        sPanel.drawRoundRect(16, y, w - 32, 60, 6, EPD_BLACK);
        sPanel.setTextColor(EPD_BLACK);
      }

      sPanel.setTextSize(1);
      sPanel.setCursor(30, y + 14);
      sPanel.print(app->sides[i].name);

      sPanel.setTextSize(2);
      sPanel.setCursor(w - 70, y + 20);
      sPanel.printf("%d", app->sides[i].score);

      y += 70;
    }

    sPanel.setTextSize(1);
    sPanel.setTextColor(EPD_BLACK);
    sPanel.setCursor(20, y + 10);
    sPanel.print("Click center button to increment score (+1)");
  } else if (app->module == "progress") {
    int y = 145;
    sPanel.setTextColor(EPD_BLACK);
    sPanel.setTextSize(1);
    sPanel.setCursor(20, y);
    sPanel.printf("%s: %.0f / %.0f %s", app->progressLabel.c_str(), app->progressValue, app->progressGoal, app->progressUnit.c_str());

    // Progress Bar Outline
    int barX = 20;
    int barY = y + 16;
    int barW = w - 40;
    int barH = 22;
    sPanel.drawRoundRect(barX, barY, barW, barH, 4, EPD_BLACK);

    // Progress Bar Fill
    float pct = (app->progressGoal > 0) ? (app->progressValue / app->progressGoal) : 0;
    if (pct > 1.0f) pct = 1.0f;
    int fillW = static_cast<int>((barW - 4) * pct);
    if (fillW > 0) {
      sPanel.fillRoundRect(barX + 2, barY + 2, fillW, barH - 4, 3, EPD_RED);
    }

    // Action Buttons
    int btnY = barY + 38;
    int btnW = (barW - 10) / 2;

    // Button 0 (+step)
    bool btn0Selected = (app->cursor == 0);
    if (btn0Selected) {
      sPanel.fillRoundRect(barX, btnY, btnW, 36, 4, EPD_RED);
      sPanel.setTextColor(EPD_WHITE);
    } else {
      sPanel.drawRoundRect(barX, btnY, btnW, 36, 4, EPD_BLACK);
      sPanel.setTextColor(EPD_BLACK);
    }
    sPanel.setCursor(barX + 14, btnY + 12);
    sPanel.printf("+%.0f %s", app->progressStep, app->progressUnit.c_str());

    // Button 1 (+2*step)
    bool btn1Selected = (app->cursor == 1);
    if (btn1Selected) {
      sPanel.fillRoundRect(barX + btnW + 10, btnY, btnW, 36, 4, EPD_RED);
      sPanel.setTextColor(EPD_WHITE);
    } else {
      sPanel.drawRoundRect(barX + btnW + 10, btnY, btnW, 36, 4, EPD_BLACK);
      sPanel.setTextColor(EPD_BLACK);
    }
    sPanel.setCursor(barX + btnW + 24, btnY + 12);
    sPanel.printf("+%.0f %s", app->progressStep * 2, app->progressUnit.c_str());
  }
}

static void drawProposalView() {
  int w = sPanel.width();
  sPanel.drawRoundRect(10, 110, w - 20, 240, 8, EPD_RED);

  sPanel.fillRoundRect(14, 114, w - 28, 26, 4, EPD_RED);
  sPanel.setTextColor(EPD_WHITE);
  sPanel.setTextSize(1);
  sPanel.setCursor(20, 122);
  sPanel.print("APP GENESIS PROPOSAL");

  sPanel.setTextColor(EPD_BLACK);
  sPanel.setCursor(20, 150);
  sPanel.print("Omni wants to create a new app:");

  sPanel.setTextSize(2);
  sPanel.setCursor(20, 170);
  sPanel.print(gModel.getProposalTitle());

  sPanel.setTextSize(1);
  sPanel.setCursor(20, 196);
  sPanel.print("Rotate thumbwheel to select choice:");

  int sel = gModel.getProposalSelection();

  // Choice 0: [ Yes, create it ]
  int btn0Y = 220;
  if (sel == 0) {
    sPanel.fillRoundRect(24, btn0Y, w - 48, 36, 6, EPD_RED);
    sPanel.setTextColor(EPD_WHITE);
  } else {
    sPanel.drawRoundRect(24, btn0Y, w - 48, 36, 6, EPD_BLACK);
    sPanel.setTextColor(EPD_BLACK);
  }
  sPanel.setTextSize(1);
  sPanel.setCursor(36, btn0Y + 12);
  sPanel.print("[ Yes, create it ]");

  // Choice 1: [ Cancel ]
  int btn1Y = 265;
  if (sel == 1) {
    sPanel.fillRoundRect(24, btn1Y, w - 48, 36, 6, EPD_RED);
    sPanel.setTextColor(EPD_WHITE);
  } else {
    sPanel.drawRoundRect(24, btn1Y, w - 48, 36, 6, EPD_BLACK);
    sPanel.setTextColor(EPD_BLACK);
  }
  sPanel.setCursor(36, btn1Y + 12);
  sPanel.print("[ Cancel ]");
}

static void drawFooter() {
  int w = sPanel.width();
  int h = sPanel.height();

  if (navIsPttActive()) {
    sPanel.fillRect(0, h - 24, w, 24, EPD_RED);
    sPanel.setTextColor(EPD_WHITE);
    sPanel.setTextSize(1);
    sPanel.setCursor(20, h - 16);
    sPanel.print("*** RECORDING VOICE (RELEASE TO SEND) ***");
  } else {
    sPanel.drawLine(0, h - 24, w, h - 24, EPD_BLACK);
    sPanel.setTextColor(EPD_BLACK);
    sPanel.setTextSize(1);
    sPanel.setCursor(20, h - 16);
    sPanel.print("Hold thumbwheel button to speak to Omni");
  }
}

static void einkPaint() {
  Serial.println("eink: painting frame...");
  sPanel.clearBuffer();

  drawHeader();
  drawAgentCard();

  ScreenType screen = gModel.getScreen();
  if (screen == SCREEN_HOME) {
    drawHomeView();
  } else if (screen == SCREEN_APP) {
    drawAppView();
  } else if (screen == SCREEN_PROPOSAL) {
    drawProposalView();
  }

  drawFooter();

  uint32_t start = millis();
  sPanel.display();
  uint32_t elapsed = millis() - start;
  Serial.printf("eink: refresh completed in %lu ms\n", static_cast<unsigned long>(elapsed));

  sNeedsRefresh = false;
}

void einkRefreshNow() {
  einkPaint();
}

void einkUpdate() {
  if (sNeedsRefresh) {
    if ((millis() - sLastRefreshRequest) >= NAV_COALESCE_MS) {
      if (!einkIsBusy()) {
        einkPaint();
      }
    }
  }
}
