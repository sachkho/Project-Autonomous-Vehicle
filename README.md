# Autonomous Vehicle Project

Welcome to our **Autonomous Vehicle Project** repository!  
This project was developed by a team of four students and focuses on creating a self-driven vehicle using a Raspberry Pi 4 and a camera.

---

## Project Overview

Our solution combines hardware and software to enable the vehicle to:
- Navigate autonomously using QR codes for localization.
- Be controlled remotely via an intuitive web interface.

---

## Repository Structure

### 1. **Design Folder**
Contains the design assets, including:
- An **SVG file** used to design and build the physical structure of the vehicle.

### 2. **Flask Folder**
Houses all Python files leveraging **Flask** for:
- Controlling the vehicle using SSH communication.
- Enabling seamless communication between the web interface and the car.

### 3. **Camera Calibration**
- The camera required calibration to accurately recognize QR codes placed on the circuit.
- These QR codes are used to localize the vehicle in real-time.

### 4. **Web Folder**
This folder includes:
- The **web interface** we developed to control the vehicle remotely.  
It provides an intuitive way to send commands to the car.

---

## Features

- **Raspberry Pi 4** and a **camera** for hardware implementation.
- **Flask-based backend** for communication and control.
- **QR-code localization** for navigation.
- **Custom-built design** with precise physical components.
- **Web interface** for user-friendly control.

---

## How to Get Started

1. Clone this repository:
   ```bash
   git clone <repository_url>
