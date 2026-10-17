#include "eink.h"

#include <Adafruit_ThinkInk.h>

#include "sim_home.h"

// 4224 Friend wiring from context/hardware.md. SRCS and MISO stay open.
// D9 is both the BUSY wire and the board's MISO pad, so the SPI bus is
// pointed at SCK and MOSI only.
static const int kDc = D1;
static const int kRst = D2;
static const int kCs = D0;
static const int kBusy = D9;

static ThinkInk_420_Tricolor_MFGNR panel(kDc, kRst, kCs, -1, kBusy, &SPI);

static bool planeBit(const uint8_t* plane, int x, int y) {
  const uint8_t byte = plane[y * SIM_STRIDE + (x >> 3)];
  return byte & (0x80 >> (x & 7));
}

static void blitSimFrame() {
  for (int y = 0; y < SIM_H; y++) {
    for (int x = 0; x < SIM_W; x++) {
      if (planeBit(SIM_BLACK, x, y)) {
        panel.drawPixel(x, y, EPD_BLACK);
      } else if (planeBit(SIM_RED, x, y)) {
        panel.drawPixel(x, y, EPD_RED);
      }
    }
  }
}

bool einkShowLogo() {
  Serial.println("eink: starting");
  panel.begin(THINKINK_TRICOLOR);

  // Default SPI.begin() claims D9 as MISO. That pad is the BUSY input.
  SPI.end();
  SPI.begin(D8, -1, D10, -1);
  pinMode(kBusy, INPUT);

  // begin() leaves the glass at 400×300. The captured frame is 300×400.
  panel.setRotation(0);
  Serial.printf("eink: %dx%d frame %dx%d\n", panel.width(), panel.height(), SIM_W, SIM_H);
  panel.clearBuffer();
  blitSimFrame();

  Serial.println("eink: painting");
  uint32_t start = millis();
  panel.display();
  uint32_t elapsed = millis() - start;
  Serial.printf("eink: refresh %lu ms\n", static_cast<unsigned long>(elapsed));
  return true;
}
