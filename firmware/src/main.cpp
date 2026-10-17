#include <Arduino.h>
#include <rom/rtc.h>

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);

  // Read pin levels at boot before setting them as outputs
  pinMode(D2, INPUT);
  pinMode(D10, INPUT);
  int d2_boot = digitalRead(D2);
  int d10_boot = digitalRead(D10);

  Serial.begin(115200);

  // Wait up to 3 seconds for USB Serial to attach
  uint32_t start = millis();
  while (!Serial && (millis() - start < 3000)) {
    delay(10);
  }

  Serial.println("\n=== Omni Strapping Pin Boot Test ===");
  Serial.printf("Reset reason: %d\n", rtc_get_reset_reason(0));
  Serial.printf("D2 (GPIO3 - RST) level at boot:  %s\n",
                d2_boot ? "HIGH (Safe)" : "LOW (Warning)");
  Serial.printf("D10 (GPIO9 - MOSI) level at boot: %s\n",
                d10_boot ? "HIGH (Safe)" : "LOW (Warning)");
  Serial.println("=====================================\n");
}

void loop() {
  // Heartbeat: blinks even if USB Serial disconnects
  digitalWrite(LED_BUILTIN, LOW); // XIAO user LED is active-low
  delay(500);
  digitalWrite(LED_BUILTIN, HIGH);
  delay(500);
  if (Serial) {
    Serial.println("omni alive");
  }
}