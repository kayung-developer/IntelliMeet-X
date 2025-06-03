# IntelliMeet X

IntelliMeet X is a feature-rich, browser-based video conferencing application built with WebRTC, FastAPI (Python), and modern web technologies. It aims to provide a seamless meeting experience with a variety of tools and AI-powered (conceptual) features.

## Features

**Core Conferencing:**
*   **Real-time Audio/Video:** High-quality, low-latency communication using WebRTC.
*   **Room-based Meetings:** Join or create rooms using unique IDs.
*   **Screen Sharing:** Share your entire screen, application window, or browser tab (includes audio sharing option).
*   **Chat:** Real-time text messaging with other participants in the room.
*   **Participant List:** View all participants currently in the meeting, along with their media status.
*   **Media Controls:**
    *   Mute/Unmute Microphone
    *   Start/Stop Video
    *   Raise/Lower Hand
    *   Send Emoji Reactions

**Advanced Video & Audio:**
*   **Virtual Backgrounds:**
    *   **None:** No background effect.
    *   **Blur:** Apply a blur effect to your background.
    *   **Predefined Images:** Choose from a selection of built-in background images.
    *   **Custom Upload:** Upload your own image (JPG, PNG) to use as a virtual background.
    *   *(Powered by MediaPipe Selfie Segmentation)*
*   **Auto Framing:** Automatically keeps your face centered and zoomed appropriately in your video feed.
    *   *(Powered by MediaPipe Face Detection)*
*   **Video Enhancement (Basic):** Applies subtle CSS filters to improve video brightness and contrast.
*   **Echo Cancellation:** Built-in browser echo cancellation (configurable).
*   **(Conceptual) AI Noise Cancellation:** Simulates noise reduction for clearer audio.

**Accessibility & Productivity:**
*   **Live Captions:** Real-time speech-to-text transcription of your audio.
    *   Language selection for captions (English, Spanish, French, German, Japanese).
    *   *(Powered by Web Speech API)*
*   **Video Layouts:**
    *   **Grid View:** Displays all participants in a grid.
    *   **Speaker View:** Focuses on the active speaker.
    *   **Focus View:** Enlarges a single selected participant (conceptual, currently mirrors speaker).
*   **Settings Panel:** Centralized control for audio, video, accessibility, AI, and recording preferences.
*   **User Preferences:** Remembers your name, device selections, and various toggle states using IndexedDB.
*   **(Conceptual) Collaboration Tools:** Buttons for Whiteboard, Polls, File Share, Breakout Rooms (currently trigger alerts).

**Recording & AI (Simulated/Conceptual):**
*   **Client-Side Recording:** Record the meeting (your view, or shared screen) and download it as a WebM file.
*   **(Conceptual) Cloud Recording:** Toggle for cloud recording, with options for recording scope (Full Meeting, Self, Active Speaker + Screen).
*   **(Simulated) Meeting Summaries:** On hangup, generates a simulated summary based on captured live captions.
*   **(Simulated) Action Item Detection:** On hangup, detects potential action items from captured live captions.
*   **(Conceptual) Real-time Translation:** Toggle for translating live captions.
*   **(Conceptual) AI Insights Panel:** A sidebar panel to display AI-generated meeting insights (summary, action items).

**UI/UX:**
*   **Responsive Design:** Adapts to various screen sizes, from desktop to mobile.
*   **Intuitive Controls:** Clear icons and tooltips for all actions.
*   **Dynamic Sidebar:** Collapsible panel for Participants, Chat, and Tools.

## Technologies Used

*   **Frontend:**
    *   HTML5
    *   CSS3 (Flexbox, Grid, Custom Properties)
    *   JavaScript (ES6+)
    *   [MediaPipe](https://mediapipe.dev/) (Selfie Segmentation for Virtual Backgrounds, Face Detection for Auto Framing)
    *   [Font Awesome](https://fontawesome.com/) (Icons)
    *   [Google Fonts](https://fonts.google.com/) (Roboto)
*   **Backend:**
    *   Python 3.7+
    *   [FastAPI](https://fastapi.tiangolo.com/) (High-performance web framework)
    *   [Uvicorn](https://www.uvicorn.org/) (ASGI server)
    *   WebSockets (for signaling and real-time communication)
*   **Web APIs:**
    *   WebRTC (Real-Time Communication)
    *   Web Audio API (for potential audio processing)
    *   Web Speech API (for Live Captions)
    *   IndexedDB (for client-side storage of preferences)

## Getting Started

### Prerequisites

*   Python 3.7 or higher
*   `pip` (Python package installer)
*   A modern web browser that supports WebRTC, MediaPipe, and other Web APIs (e.g., Chrome, Edge, Firefox).
*   Internet connection (for loading MediaPipe models from CDN).

### Installation

1.  **Save the Code:**
    *   Save the Python backend code (provided in the prompt, starting with `import asyncio` and ending with `uvicorn.run(...)`) as `main.py`.
    *   The HTML, CSS, and JavaScript code (provided in the prompt, starting with `<!DOCTYPE html>`) is embedded within the `HTML_TEMPLATE` variable in `main.py`.

2.  **Install Dependencies:**
    Open your terminal or command prompt, navigate to the directory where you saved `main.py`, and run:
    ```bash
    pip install fastapi uvicorn websockets
    ```

### Running the Application

1.  **Start the Backend Server:**
    In the same terminal, run:
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8080
    ```
    *   You can add `--reload` for automatic reloading during development: `uvicorn main:app --host 0.0.0.0 --port 8080 --reload`

2.  **Access IntelliMeet X:**
    Open your web browser and navigate to: `http://localhost:8080`

## How to Use

1.  **Join/Create a Room:**
    *   On the entry modal, enter your name.
    *   Enter a Room ID. If the room exists, you'll join it. If not, a new room with that ID will be created.
    *   Click "Join / Create Room".

2.  **Grant Permissions:**
    *   Your browser will prompt you for permission to access your camera and microphone. Please allow these for the application to function.

3.  **Explore Features:**
    *   Use the control panel at the bottom to toggle your mic/video, share your screen, raise your hand, send reactions, or hang up.
    *   Open the Settings (cog icon in the header or main controls) to configure devices, virtual backgrounds, AI features, etc.
    *   Use the sidebar (toggle via header button) to view participants, chat, or access conceptual tools.
    *   Change video layouts using the buttons above the video grid.

## Important Notes

*   **Conceptual Features:** Many AI-powered features (Noise Cancellation, Summaries, Action Items, Translation, AI Insights) and advanced tools (Whiteboard, Polls, Cloud Recording) are currently conceptual or simulated. They demonstrate the UI and potential, but full backend logic is not implemented.
*   **Client-Side Recording:** The recording feature is client-side. When you stop recording, the file will be downloaded directly to your computer.
*   **STUN Server:** The application uses a public Google STUN server (`stun:stun.l.google.com:19302`) for WebRTC NAT traversal. For production environments, consider deploying your own STUN/TURN servers for reliability.
*   **Browser Compatibility:** Best experienced on modern desktop browsers. Mobile support is present but may have limitations with some advanced features like MediaPipe effects.
*   **HTTPS:** For deploying on a public server, HTTPS is crucial for WebRTC and `getUserMedia` to work reliably. The current setup is for local HTTP development.
*   **MediaPipe Models:** Virtual Background and Auto Framing features rely on MediaPipe models loaded from a CDN, requiring an internet connection during use.

## Future Enhancements (Potential)

*   Full implementation of conceptual AI and collaboration tools.
*   Server-side recording and processing.
*   Persistent chat history and user accounts.
*   TURN server integration for robust NAT traversal in complex network environments.
*   Enhanced error handling and user feedback.
*   More sophisticated video/audio processing.
