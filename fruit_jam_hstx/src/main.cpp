// Fruit Jam HSTX 720p Demo — main sketch entry point.
//
// Phase 1' (this file): bring up the HSTX DVI/HDMI output via the
// vendored picodvi framebuffer driver (see src/hstx_fb/). Allocates a
// 320x240 RGB565 framebuffer that gets pixel-doubled to a 640x480 HDMI
// signal, fills it with a solid color, and keeps the existing P0
// serial heartbeat running on top.
//
// 720p is the eventual goal — see fruit_jam_dvi/arduino_720p_PLAN.md
// §4 phase P1.5. The vendored framebuffer driver currently tops out at
// 640x480 / 720x400; adding 1280x720@60 timing constants is a
// follow-up.
//
// Acceptance: monitor shows a solid-color 640x480 picture, and serial
// prints "[fruit_jam_hstx] P1' hello, frameno=N" once per second.

#include <Arduino.h>
#include "hstx_fb/hstx_fb.h"

static const uint32_t HEARTBEAT_PERIOD_MS = 1000;

// Framebuffer state. Static so it lives forever — the HSTX DMA channel
// reads from it on every frame.
static picodvi_framebuffer_obj_t g_fb;
static bool g_fb_ready = false;

// Adafruit Fruit Jam HSTX pin assignment — P-side of each differential
// pair on GPIO 12..19. Matches the upstream fruitjam-doom call.
static const int HSTX_CKP = 13;
static const int HSTX_D0P = 15;  // blue lane
static const int HSTX_D1P = 17;  // green lane
static const int HSTX_D2P = 19;  // red lane

static const uint32_t FB_WIDTH = 320;
static const uint32_t FB_HEIGHT = 240;
static const uint32_t FB_BPP = 16;       // RGB565

// RGB565 helper for solid-color fill.
static inline uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
  return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

static void fill_solid(uint16_t color) {
  // Word-pair fill: pack two RGB565 pixels per 32-bit word for speed.
  // The vendored framebuffer is laid out as `pitch * height` words
  // where pitch = ceil(width * bpp / 8 / 4). For 320 * 16 / 32 = 160
  // words per row.
  uint32_t pair = ((uint32_t)color << 16) | color;
  uint32_t *p = g_fb.framebuffer;
  size_t words = g_fb.framebuffer_len;
  for (size_t i = 0; i < words; ++i) {
    p[i] = pair;
  }
}

void setup() {
  Serial.begin(115200);
  uint32_t start = millis();
  while (!Serial && (millis() - start) < 2000) {
    delay(10);
  }
  Serial.println();
  Serial.println("[fruit_jam_hstx] P1' boot");
  Serial.printf("                 cpu_freq=%lu Hz\n", (unsigned long)F_CPU);
  Serial.printf("                 fb=%lux%lu bpp=%lu\n",
                (unsigned long)FB_WIDTH, (unsigned long)FB_HEIGHT,
                (unsigned long)FB_BPP);

  bool ok = common_hal_picodvi_framebuffer_construct(
      &g_fb,
      FB_WIDTH, FB_HEIGHT,
      HSTX_CKP, HSTX_D2P, HSTX_D1P, HSTX_D0P,   // red=D2, green=D1, blue=D0
      FB_BPP);
  if (!ok) {
    Serial.println("[fruit_jam_hstx] HSTX framebuffer construct FAILED");
    return;
  }
  g_fb_ready = true;
  Serial.printf("                 hstx ready: output_width=%lu pitch=%lu\n",
                (unsigned long)g_fb.output_width,
                (unsigned long)g_fb.pitch);

  // Fill with a recognizable color so we can confirm the monitor sees
  // something. Yellow-orange (R=255, G=128, B=0) — distinct from any
  // black-screen "no signal" placeholder the monitor might show.
  fill_solid(rgb565(255, 128, 0));
  Serial.println("                 framebuffer filled (orange)");
  Serial.println();
}

void loop() {
  static uint32_t last = 0;
  uint32_t now = millis();
  if (now - last >= HEARTBEAT_PERIOD_MS) {
    last = now;
    if (g_fb_ready) {
      Serial.printf("[fruit_jam_hstx] P1' hello, t=%lu s, frameno=%d\n",
                    (unsigned long)(now / 1000), g_fb.frameno);
    } else {
      Serial.printf("[fruit_jam_hstx] P1' hello (no HSTX), t=%lu s\n",
                    (unsigned long)(now / 1000));
    }
  }
  delay(10);
}
