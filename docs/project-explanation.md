# Project Explanation — ECE Smart Lab IoT Monitor

## Aim
Build a simple IoT prototype that measures temperature and relative humidity and presents the latest values on a local browser dashboard.

## Main components
- **DHT22:** digital temperature and humidity sensor.
- **ESP32:** microcontroller with Wi-Fi; reads the sensor and hosts an HTTP server.
- **Browser UI:** shows measurements and refreshes every three seconds.
- **JSON endpoint:** makes readings accessible to other local applications.

## Operation
1. The ESP32 joins the configured Wi-Fi network.
2. The firmware samples the DHT22.
3. The web server serves the dashboard at the board's local IP.
4. The browser requests `/api/readings` repeatedly and updates the values.
5. A simple threshold can show an attention status; thresholds should be adapted to the actual lab and sensor.

## Learning concepts
Sensor interfacing, GPIO, embedded C++, Wi-Fi, HTTP client/server concepts, JSON serialization, and basic frontend JavaScript.

## Constraints
This is a student prototype, not a certified building-management or safety system. Readings can drift and are sensitive to sensor placement. Local HTTP is unencrypted; keep it on a trusted network and do not port-forward the device.

## Suggested future enhancements
- MQTT publish/subscribe
- Timestamped history in a database
- Calibration and reference comparison
- Authentication and TLS for remote access
- Configurable thresholds and notifications
