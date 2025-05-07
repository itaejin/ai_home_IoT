# AI and IoT Integrated Smart Home

## Project Overview
This project combines artificial intelligence and IoT to create a smart home system. It utilizes cameras for facial and finger-count recognition, while various sensors control objects within the home. To monitor real-time data, sensor information is managed through InfluxDB via the EMQX Broker. The data is then visualized using Grafana for easy user access.

## Features
### 1. Face Recognition for Door Lock Control
When standing in front of the front door, the system automatically recognizes the face and unlocks the door. 

The recognition accuracy is set to 75%.


### 2. Fire Detection Alarm
The system continuously operates and triggers an alarm when a fire detection sensor detects any abnormality.

### 3. Hand Gesture LED Control
The number of fingers shown can control specific LEDs inside the house.

### 4. Automatic Door System
The door automatically opens when approaching it. 

The door will open when the distance to the door is 10 cm or less.
