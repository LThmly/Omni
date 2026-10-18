#include "nav_switch.h"
#include "pins.h"
#include "config.h"

// Ring buffer for navigation events
static const uint8_t EVENT_QUEUE_SIZE = 16;
static NavEvent sEventQueue[EVENT_QUEUE_SIZE];
static uint8_t sQueueHead = 0;
static uint8_t sQueueTail = 0;

static void queueEvent(NavEvent evt) {
  uint8_t nextHead = (sQueueHead + 1) % EVENT_QUEUE_SIZE;
  if (nextHead != sQueueTail) {
    sEventQueue[sQueueHead] = evt;
    sQueueHead = nextHead;
  }
}

// Debounce state for Up and Down pins
struct ButtonState {
  uint8_t pin;
  bool lastReading;
  bool debouncedState;
  uint32_t lastDebounceTime;
};

static ButtonState sBtnUp = { PIN_NAV_UP, HIGH, HIGH, 0 };
static ButtonState sBtnDown = { PIN_NAV_DOWN, HIGH, HIGH, 0 };

// Center push state machine
enum PushState {
  PUSH_STATE_IDLE,
  PUSH_STATE_PRESSED,
  PUSH_STATE_HOLDING_PTT
};

static PushState sPushState = PUSH_STATE_IDLE;
static bool sPushLastReading = HIGH;
static bool sPushDebounced = HIGH;
static uint32_t sPushDebounceTime = 0;
static uint32_t sPushPressStartTime = 0;

const char* navEventToString(NavEvent evt) {
  switch (evt) {
    case NAV_EVENT_UP:        return "UP";
    case NAV_EVENT_DOWN:      return "DOWN";
    case NAV_EVENT_CLICK:     return "CLICK";
    case NAV_EVENT_PTT_START: return "PTT_START";
    case NAV_EVENT_PTT_END:   return "PTT_END";
    default:                  return "NONE";
  }
}

void navInit() {
  pinMode(PIN_NAV_UP, INPUT_PULLUP);
  pinMode(PIN_NAV_DOWN, INPUT_PULLUP);
  pinMode(PIN_NAV_PUSH, INPUT_PULLUP);

  sBtnUp.lastReading = digitalRead(PIN_NAV_UP);
  sBtnUp.debouncedState = sBtnUp.lastReading;
  sBtnUp.lastDebounceTime = millis();

  sBtnDown.lastReading = digitalRead(PIN_NAV_DOWN);
  sBtnDown.debouncedState = sBtnDown.lastReading;
  sBtnDown.lastDebounceTime = millis();

  sPushLastReading = digitalRead(PIN_NAV_PUSH);
  sPushDebounced = sPushLastReading;
  sPushDebounceTime = millis();
  sPushState = PUSH_STATE_IDLE;
}

static void updateSimpleButton(ButtonState& btn, NavEvent triggerEvent) {
  uint32_t now = millis();
  bool reading = digitalRead(btn.pin);

  if (reading != btn.lastReading) {
    btn.lastDebounceTime = now;
    btn.lastReading = reading;
  }

  if ((now - btn.lastDebounceTime) > NAV_DEBOUNCE_MS) {
    if (reading != btn.debouncedState) {
      btn.debouncedState = reading;
      // Active LOW: transition from HIGH (released) to LOW (pressed)
      if (btn.debouncedState == LOW) {
        queueEvent(triggerEvent);
      }
    }
  }
}

static void updatePushButton() {
  uint32_t now = millis();
  bool reading = digitalRead(PIN_NAV_PUSH);

  if (reading != sPushLastReading) {
    sPushDebounceTime = now;
    sPushLastReading = reading;
  }

  if ((now - sPushDebounceTime) > NAV_DEBOUNCE_MS) {
    if (reading != sPushDebounced) {
      sPushDebounced = reading;
      if (sPushDebounced == LOW) {
        // Transitioned to pressed
        sPushPressStartTime = now;
        sPushState = PUSH_STATE_PRESSED;
      } else {
        // Transitioned to released
        if (sPushState == PUSH_STATE_HOLDING_PTT) {
          queueEvent(NAV_EVENT_PTT_END);
        } else if (sPushState == PUSH_STATE_PRESSED) {
          // Released before hold threshold -> short click
          queueEvent(NAV_EVENT_CLICK);
        }
        sPushState = PUSH_STATE_IDLE;
      }
    }
  }

  // Check if held long enough while still pressed
  if (sPushState == PUSH_STATE_PRESSED && sPushDebounced == LOW) {
    if ((now - sPushPressStartTime) >= NAV_PTT_HOLD_MS) {
      sPushState = PUSH_STATE_HOLDING_PTT;
      queueEvent(NAV_EVENT_PTT_START);
    }
  }
}

void navUpdate() {
  updateSimpleButton(sBtnUp, NAV_EVENT_UP);
  updateSimpleButton(sBtnDown, NAV_EVENT_DOWN);
  updatePushButton();
}

bool navPollEvent(NavEvent& outEvent) {
  if (sQueueHead == sQueueTail) {
    outEvent = NAV_EVENT_NONE;
    return false;
  }
  outEvent = sEventQueue[sQueueTail];
  sQueueTail = (sQueueTail + 1) % EVENT_QUEUE_SIZE;
  return true;
}

bool navIsPttActive() {
  return (sPushState == PUSH_STATE_HOLDING_PTT);
}

void navInjectEvent(NavEvent evt) {
  queueEvent(evt);
}
