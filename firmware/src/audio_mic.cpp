#include "audio_mic.h"
#include <driver/i2s.h>
#include "pins.h"
#include "config.h"

#define I2S_PORT I2S_NUM_0

static const size_t MAX_AUDIO_BYTES = AUDIO_SAMPLE_RATE * sizeof(int16_t) * AUDIO_MAX_SECONDS; // ~320 KB
static uint8_t* sAudioBuffer = nullptr;
static size_t sRecordedBytes = 0;
static bool sIsRecording = false;

void micInit() {
  Serial.println("mic: allocating audio recording buffer...");
  if (psramFound()) {
    sAudioBuffer = (uint8_t*)ps_malloc(MAX_AUDIO_BYTES);
    Serial.printf("mic: allocated %u bytes in PSRAM\n", MAX_AUDIO_BYTES);
  } else {
    sAudioBuffer = (uint8_t*)malloc(64 * 1024); // 64 KB fallback
    Serial.println("mic: PSRAM not found, using heap buffer");
  }

  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = AUDIO_SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 4,
    .dma_buf_len = 512,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };

  i2s_pin_config_t pin_config = {
    .bck_io_num = PIN_I2S_SCK,
    .ws_io_num = PIN_I2S_WS,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = PIN_I2S_SD
  };

  esp_err_t err = i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  if (err == ESP_OK) {
    i2s_set_pin(I2S_PORT, &pin_config);
    Serial.println("mic: I2S driver initialized successfully");
  } else {
    Serial.printf("mic: failed to install I2S driver: %d\n", err);
  }
}

void micStartRecording() {
  sRecordedBytes = 0;
  sIsRecording = true;
  Serial.println("mic: recording started (PTT active)...");
}

void micUpdateRecording() {
  if (!sIsRecording || !sAudioBuffer) return;

  size_t bytesRemaining = MAX_AUDIO_BYTES - sRecordedBytes;
  if (bytesRemaining < 1024) {
    // Buffer full
    return;
  }

  size_t bytesRead = 0;
  esp_err_t res = i2s_read(I2S_PORT, sAudioBuffer + sRecordedBytes, min((size_t)1024, bytesRemaining), &bytesRead, 10 / portTICK_PERIOD_MS);
  if (res == ESP_OK && bytesRead > 0) {
    sRecordedBytes += bytesRead;
  }
}

void micStopRecording() {
  if (!sIsRecording) return;
  sIsRecording = false;
  Serial.printf("mic: recording stopped. Captured %u bytes of PCM audio\n", sRecordedBytes);
}

bool micIsRecording() {
  return sIsRecording;
}

size_t micGetRecordedBytes() {
  return sRecordedBytes;
}

const uint8_t* micGetRecordedBuffer() {
  return sAudioBuffer;
}
