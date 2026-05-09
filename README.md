# OBDash

![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-blue)
![OBD2](https://img.shields.io/badge/OBD2-ELM327-brightgreen)
![Connectivity](https://img.shields.io/badge/connectivity-Bluetooth%20%7C%20WiFi-orange)

**OBDash** is a modern, beautifully designed OBD2 reader application that connects to ELM327-compatible devices. It transforms your car's diagnostic data into a clean, intuitive dashboard.

## Features

- **ELM327 support** — Works with virtually any ELM327-based adapter
- **Dual connectivity** — Connect via **Bluetooth** (BLE / classic SPP) or **Wi-Fi**
- **Real-time monitoring** — RPM, speed, coolant temp, fuel trims, throttle position, and dozens more PIDs
- **Beautiful UI** — Clean, glass-morphism dashboard with light/dark theme support
- **Cross-platform** (if applicable — укажите свою платформу, например: Windows/Linux/macOS или Android/iOS)
- **Data logging** — Export sessions to CSV/JSON
- **Low latency** — Optimized for responsive real-time gauges

## Supported connections

| Connection | Protocol | Device examples |
|------------|----------|------------------|
| Bluetooth | SPP / BLE | OBDLink MX+, Veepeak, LELink, generic ELM327 mini |
| Wi-Fi | TCP (port 35000) | WiFi OBD2 dongles (e.g., Carista, OBDLink CX, generic) |

## Getting started

1. Pair your ELM327 device via Bluetooth or connect to its Wi-Fi hotspot
2. Launch OBDash
3. Select connection type and device
4. Start monitoring your car in style

## Requirements

- ELM327 v1.5+ compatible adapter (clone or genuine)
- (For Bluetooth) Bluetooth adapter supporting SPP/BLE
- (For Wi-Fi) Wi-Fi connection to the dongle's network