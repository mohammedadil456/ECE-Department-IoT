#include <WiFi.h>
#include <WebServer.h>
#include <DHT.h>

// Configure locally. Do not commit real Wi-Fi credentials.
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

#define DHT_PIN 4
#define DHT_TYPE DHT22
const float TEMP_ALERT_C = 30.0;

DHT dht(DHT_PIN, DHT_TYPE);
WebServer server(80);

const char DASHBOARD[] PROGMEM = R"HTML(
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ECE Smart Lab Monitor</title>
<style>body{font-family:system-ui,sans-serif;margin:0;background:#071b2d;color:#eef9ff;display:grid;place-items:center;min-height:100vh}.panel{width:min(90%,650px);padding:28px;border:1px solid #2d5b70;border-radius:22px;background:#102c40}h1{margin:0 0 8px}.muted{color:#a9c8d5}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:24px 0}.tile{background:#173b50;padding:20px;border-radius:16px}.value{font-size:2.3rem;font-weight:700}.status{padding:10px;border-radius:10px;background:#1c594f}</style></head><body><main class="panel"><h1>ECE Smart Lab Monitor</h1><p class="muted">ESP32 + DHT22 · Local dashboard</p><section class="grid"><div class="tile"><div class="muted">Temperature</div><div id="temp" class="value">-- °C</div></div><div class="tile"><div class="muted">Humidity</div><div id="hum" class="value">-- %</div></div></section><div id="status" class="status">Connecting to sensor…</div><p class="muted">Refreshes every 3 seconds.</p></main><script>async function update(){try{const r=await fetch('/api/readings',{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);const d=await r.json();document.querySelector('#temp').textContent=d.temperature_c+' °C';document.querySelector('#hum').textContent=d.humidity_pct+' %';document.querySelector('#status').textContent=d.status==='attention'?'Temperature threshold reached':'Readings updated';}catch(e){document.querySelector('#status').textContent='Sensor/server unavailable';}}update();setInterval(update,3000);</script></body></html>
)HTML";

void handleReadings() {
  const float temperature = dht.readTemperature();
  const float humidity = dht.readHumidity();
  if (isnan(temperature) || isnan(humidity)) {
    server.send(503, "application/json", "{\"error\":\"sensor_read_failed\"}");
    return;
  }
  const char* status = temperature >= TEMP_ALERT_C ? "attention" : "normal";
  String json = "{\"temperature_c\":" + String(temperature, 1) +
                ",\"humidity_pct\":" + String(humidity, 1) +
                ",\"status\":\"" + status + "\"}";
  server.send(200, "application/json", json);
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print('.'); }
  Serial.println();
  Serial.print("Dashboard: http://"); Serial.println(WiFi.localIP());
  server.on("/", HTTP_GET, []() { server.send(200, "text/html", DASHBOARD); });
  server.on("/api/readings", HTTP_GET, handleReadings);
  server.begin();
}

void loop() { server.handleClient(); }
