---
title: Smart AR Voice Agent
emoji: 📞
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8080
---

# Smart Accounts Receivable (AR) Voice Agent

This project implements a system that extracts financial details from invoice PDFs using OCR, stores them in a mock database, and launches a real-time LiveKit voice agent that calls the customer to follow up on overdue payments.

## Prerequisites

Before running the project, you need to set up a few system-level and cloud requirements.

### 1. Poppler (Required for PDF-to-Image Conversion)
The `pdf2image` library requires Poppler to render PDF pages into images before EasyOCR can scan them.

*   **Windows:**
    1.  Download the latest binary release from: `https://github.com/oschwartz10612/poppler-windows/releases/`
    2.  Extract the zip file (e.g., to `C:\poppler`).
    3.  Add the `bin` folder (e.g., `C:\poppler\Library\bin` or `C:\poppler\bin`) to your System PATH:
        *   Search for "Environment Variables" in Windows Search.
        *   Edit the `Path` variable under User or System variables and add the path to the `bin` directory.
*   **macOS:**
    ```bash
    brew install poppler
    ```
*   **Linux (Ubuntu/Debian):**
    ```bash
    sudo apt-get install poppler-utils
    ```

### 2. LiveKit Cloud Setup
1.  Go to [LiveKit Cloud Console](https://cloud.livekit.io) and create a free account.
2.  Create a new project.
3.  Go to **Settings -> Keys** and generate a new API Key/Secret.
4.  Copy the **Server URL** (e.g., `wss://...livekit.cloud`), **API Key**, and **API Secret**.

### 3. OpenAI & Deepgram API Keys
1.  Obtain an API key from [OpenAI Developer Platform](https://platform.openai.com/).
2.  Obtain an API key from [Deepgram Console](https://console.deepgram.com/).

---

## Setup & Running Instructions

1.  **Clone / Open Project Directory**
    Recommend setting this folder as your active workspace in your editor.

2.  **Install Python Dependencies**
    Ensure Python 3.9+ is installed, then run:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup Environment Variables**
    Duplicate the `.env.example` file, rename it to `.env`, and fill in your actual credentials:
    ```bash
    cp .env.example .env
    ```

4.  **Run Mock Database Initialization**
    ```bash
    python database.py
    ```

5.  **Run the Voice Agent Worker**
    Start your agent script locally:
    ```bash
    python voice_agent.py dev
    ```

6.  **Test the Agent via Sandbox**
    *   Open [LiveKit Agent Sandbox](https://meet.livekit.io/) in your browser.
    *   Use the connection credentials from your LiveKit Cloud project to join the room.
    *   Once connected, the agent will join, say the introduction prompt, and you can start talking!
