# Assignment 1: ESP32 Camera Finger Count Detection

## Overview
This project implements real-time finger count detection using an ESP32-CAM module streaming video frames processed via Python, OpenCV, and MediaPipe.

## Hardware Requirements
- ESP32-CAM module
- FTDI programmer (for flashing)
- USB cable & jumper wires

## Software & Dependencies
- Python 3.10
- OpenCV (`opencv-python`)
- MediaPipe (`mediapipe`)

## How to Run
1. Flash the ESP32-CAM firmware with the provided camera web server sketch.
2. Update the video stream IP address in your Python script.
3. Run the detection script: