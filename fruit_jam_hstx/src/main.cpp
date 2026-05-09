// Fruit Jam HSTX 720p Demo — main sketch entry point.
//
// Phase 0 (this file): the absolute minimum — proves the toolchain
// builds a working sketch for the Adafruit Fruit Jam, the UF2 flashes,
// and the device prints a heartbeat over USB CDC serial. No HSTX, no
// audio, no USB host yet — those land in P1..P9 per
// fruit_jam_dvi/arduino_720p_PLAN.md.
//
// Once flashed, you should see "[fruit_jam_hstx] P0 hello, t=N s" on the
// USB CDC serial (115200 baud) once per second.

#include <Arduino.h>

static const uint32_t HEARTBEAT_PERIOD_MS = 1000;

void setup() {
  Serial.begin(115200);
  // Wait briefly for the host to open the CDC port; never block
  // forever — if no host is attached we still want to run.
  uint32_t start = millis();
  while (!Serial && (millis() - start) < 2000) {
    delay(10);
  }
  Serial.println();
  Serial.println("[fruit_jam_hstx] P0 boot — toolchain check");
  Serial.printf("                 board: %s\n", "Adafruit Fruit Jam (RP2350B)");
  Serial.printf("                 cpu_freq=%lu Hz\n", (unsigned long)F_CPU);
  Serial.println();
}

void loop() {
  static uint32_t last = 0;
  uint32_t now = millis();
  if (now - last >= HEARTBEAT_PERIOD_MS) {
    last = now;
    Serial.printf("[fruit_jam_hstx] P0 hello, t=%lu s\n",
                  (unsigned long)(now / 1000));
  }
  delay(10);
}
