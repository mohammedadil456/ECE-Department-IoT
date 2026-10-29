# ECE SmartLab Application

An installable browser/PWA dashboard for the ECE SmartLab IoT project.

## Current application features
- Responsive desktop/mobile dashboard
- Simulation mode for demonstration without hardware
- ESP32 device mode reading the existing `GET /api/readings` endpoint
- Temperature threshold indicator and health summary
- Rolling 30-sample graph and recent readings table
- CSV export
- PWA manifest and service worker for install/offline shell

## Run
Serve this folder using any static web server (service workers require localhost or HTTPS). For example:

```bash
python -m http.server 8000
```

Open `http://localhost:8000/application/` from the repository root.

## Connect the ESP32
Put the ESP32 and the device running the app on the same Wi-Fi network. In Device URL enter the ESP32 address printed in its Serial Monitor, e.g. `http://192.168.1.50`, then choose Connect. The dashboard requests `/api/readings`.

### Browser network note
When the application is hosted on HTTPS, browsers may block requests to an HTTP-only ESP32 endpoint (mixed content). For local hardware testing, open the app from a local HTTP server on the same network or configure a secure proxy. Cross-origin access may also require CORS headers in firmware; the current starter firmware may need that adjustment.

## Important scope
Simulation values are synthetic and labeled as simulation. Physical sensor readings are only shown when the ESP32 endpoint is reachable. This frontend is the first implementation milestone; a cloud backend, user accounts, durable database, Android/Windows packaging, MQTT, multi-node provisioning, and push notifications remain subsequent milestones. Do not treat this academic prototype as a certified safety system.
