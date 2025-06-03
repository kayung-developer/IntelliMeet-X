import asyncio
import json
import uuid
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketState
import uvicorn
from urllib.parse import unquote as url_unquote

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# In-memory storage for rooms and participants
rooms = {}

# --- HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IntelliMeet X - Ultimate AI Video Conference</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/selfie_segmentation/selfie_segmentation.js" crossorigin="anonymous"></script>
    <style>
        :root {
            --primary-bg: #1f2023; /* Darker, more modern */
            --secondary-bg: #282a2d;
            --tertiary-bg: #3a3d40;
            --accent-color: #0078d4; /* MS Teams Blue */
            --accent-hover-color: #005a9e;
            --danger-color: #d92c2c;
            --danger-hover-color: #b82424;
            --success-color: #107c10;
            --text-color: #f0f0f0;
            --text-secondary-color: #c0c0c0;
            --border-color: #4a4d50;
            --video-bg: #121212;
            --control-panel-height: 75px;
            --sidebar-width: 340px;
            --header-height: 55px;
            --font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
            --border-radius-md: 8px;
            --border-radius-sm: 4px;
            --shadow-md: 0 4px 12px rgba(0,0,0,0.3);
            --yellow-warning: #ffc107; /* Added for hand raised icon */
        }

        /* Basic Reset & Global Styles */
        *, *::before, *::after { box-sizing: border-box; }
        body, h1, h2, h3, p, ul, li { margin: 0; padding: 0; }
        body {
            font-family: var(--font-family);
            background-color: var(--primary-bg);
            color: var(--text-color);
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
            font-size: 15px; /* Base font size */
        }
        .hidden { display: none !important; }
        button { cursor: pointer; font-family: inherit; }
        input, select, textarea { font-family: inherit; }

        /* --- Modals (Entry, Settings, etc.) --- */
        .modal-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background-color: rgba(0,0,0,0.7);
            display: flex; justify-content: center; align-items: center;
            z-index: 2000; backdrop-filter: blur(8px);
            opacity: 0; visibility: hidden; transition: opacity 0.3s, visibility 0s 0.3s;
        }
        .modal-overlay.visible { opacity: 1; visibility: visible; transition-delay: 0s; }
        .modal-content {
            background-color: var(--secondary-bg);
            padding: 25px 35px;
            border-radius: var(--border-radius-md);
            text-align: center;
            box-shadow: var(--shadow-md);
            width: 100%; max-width: 420px;
            transform: scale(0.95); transition: transform 0.3s;
            max-height: 90vh; overflow-y: auto; /* For scrollable modals */
        }
        .modal-overlay.visible .modal-content { transform: scale(1); }
        .modal-content h2 {
            color: var(--text-color); margin-bottom: 20px; font-weight: 500; font-size: 1.6em;
        }
        .modal-content input[type="text"], .modal-content select {
            display: block; width: 100%; padding: 12px 15px; margin-bottom: 15px;
            border: 1px solid var(--border-color); border-radius: var(--border-radius-sm);
            background-color: var(--tertiary-bg); color: var(--text-color);
            font-size: 1em; outline: none; transition: border-color 0.2s;
        }
        .modal-content input[type="text"]:focus, .modal-content select:focus { border-color: var(--accent-color); }
        .modal-content button {
            width: 100%; padding: 12px 25px; background-color: var(--accent-color);
            color: white; border: none; border-radius: var(--border-radius-sm);
            font-size: 1.1em; font-weight: 500; transition: background-color 0.2s;
        }
        .modal-content button:hover { background-color: var(--accent-hover-color); }
        .modal-content .modal-close-button {
            background-color: var(--tertiary-bg); margin-top: 15px;
        }
        .modal-content .modal-close-button:hover { background-color: var(--border-color); }

        #settings-modal .modal-content { max-width: 600px; text-align: left; } /* Wider for VB options */
        .settings-section { margin-bottom: 20px; }
        .settings-section h3 {
            font-size: 1.2em; color: var(--text-secondary-color); margin-bottom: 12px;
            border-bottom: 1px solid var(--border-color); padding-bottom: 8px; font-weight: 500;
        }
        .settings-section label { display: block; margin-bottom: 6px; font-size: 0.95em; }
        .settings-section .toggle-switch-container {
            display: flex; align-items: center; justify-content: space-between;
            padding: 10px; background-color: var(--tertiary-bg);
            border-radius: var(--border-radius-sm); margin-bottom: 10px;
        }
        .toggle-switch { position: relative; display: inline-block; width: 44px; height: 24px; }
        .toggle-switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #555; transition: .3s; border-radius: 24px; }
        .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .3s; border-radius: 50%; }
        input:checked + .slider { background-color: var(--accent-color); }
        input:checked + .slider:before { transform: translateX(20px); }

        /* Virtual Background Options */
        #virtual-background-choices {
            padding: 10px; background-color: var(--tertiary-bg); border-radius: var(--border-radius-sm);
            margin-top: 10px;
        }
        #virtual-background-choices p { margin-bottom: 10px; font-size: 0.9em; }
        .vb-options-buttons { display: flex; gap: 8px; margin-bottom: 15px; flex-wrap: wrap; }
        .vb-options-buttons button {
            padding: 8px 12px; font-size: 0.9em; width: auto; background-color: var(--primary-bg);
        }
        .vb-options-buttons button.selected { background-color: var(--accent-color); }

        #predefined-backgrounds-container { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 15px;}
        .vb-thumbnail {
            width: 80px; height: 45px; object-fit: cover; cursor: pointer;
            border: 2px solid var(--border-color); border-radius: var(--border-radius-sm);
            transition: border-color 0.2s;
        }
        .vb-thumbnail:hover, .vb-thumbnail.selected { border-color: var(--accent-color); }
        #upload-background-input { width: calc(100% - 30px); margin-bottom: 0; }


        /* --- Main Layout --- */
        .app-container { display: flex; flex-direction: column; height: 100%; }
        .app-header {
            height: var(--header-height); background-color: var(--primary-bg);
            display: flex; align-items: center; justify-content: space-between;
            padding: 0 20px; border-bottom: 1px solid var(--border-color); flex-shrink: 0;
        }
        .app-logo { font-size: 1.5em; font-weight: 700; color: var(--accent-color); }
        .room-info span { font-size: 1.1em; font-weight: 500; }
        .header-actions button {
            background: none; border: none; color: var(--text-secondary-color);
            font-size: 1.4em; cursor: pointer; padding: 8px; margin-left: 8px;
            border-radius: var(--border-radius-sm); transition: color 0.2s, background-color 0.2s;
        }
        .header-actions button:hover { color: var(--text-color); background-color: var(--tertiary-bg); }

        .main-content-area { display: flex; flex-grow: 1; overflow: hidden; }
        .video-area {
            flex-grow: 1; display: flex; flex-direction: column;
            background-color: var(--primary-bg); padding: 15px; overflow: hidden;
        }
        .video-layout-controls { margin-bottom: 10px; display: flex; gap: 8px; }
        .video-layout-controls button {
            background-color: var(--tertiary-bg); color: var(--text-secondary-color); border: none;
            padding: 8px 12px; border-radius: var(--border-radius-sm); font-size: 0.9em;
        }
        .video-layout-controls button.active, .video-layout-controls button:hover { background-color: var(--accent-color); color: white; }

        .video-grid-container {
            flex-grow: 1; display: grid; gap: 15px; overflow-y: auto; align-content: flex-start;
            /* Layouts will be applied by JS */
        }
        .video-grid-container.grid-layout { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
        .video-grid-container.speaker-layout { /* JS will manage this */ }
        .video-grid-container::-webkit-scrollbar { width: 8px; }
        .video-grid-container::-webkit-scrollbar-track { background: var(--secondary-bg); }
        .video-grid-container::-webkit-scrollbar-thumb { background: var(--tertiary-bg); border-radius: 4px; }

        .video-participant {
            background-color: var(--video-bg); border-radius: var(--border-radius-md);
            overflow: hidden; position: relative; aspect-ratio: 16/9;
            display: flex; align-items: center; justify-content: center;
            border: 2px solid transparent; transition: border-color 0.3s, box-shadow 0.3s;
        }
        .video-participant.active-speaker { border-color: var(--accent-color); box-shadow: 0 0 10px var(--accent-color); }
        .video-participant video, .video-participant canvas { /* canvas added */
            width: 100%; height: 100%; object-fit: cover; background-color: #000;
        }
        .video-participant.local-participant video,
        .video-participant.local-participant canvas { transform: scaleX(-1); } /* canvas added */

        .video-participant.screen-sharing-active video,
        .video-participant.remote-screen-share video { transform: scaleX(1); }
        /* .video-participant.virtual-bg-active video { display: none; } */ /* Handled by JS now */
        /* .video-participant.virtual-bg-active canvas { display: block; } */ /* Handled by JS now */


        .participant-overlay {
            position: absolute; bottom: 0; left: 0; width: 100%; padding: 8px 12px;
            background: linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0) 100%);
            display: flex; justify-content: space-between; align-items: center;
        }
        .participant-name { color: white; font-size: 0.9em; font-weight: 500; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); }
        .participant-status-icons { display: flex; gap: 8px; }
        .status-icon {
            color: white; font-size: 1em; background-color: rgba(0,0,0,0.6); padding: 5px;
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
        }
        .status-icon.mic-muted { color: var(--danger-color); }
        .status-icon.hand-raised { color: var(--yellow-warning); }
        .status-icon.video-off i { color: var(--text-secondary-color); }


        .avatar-placeholder {
            width: 90px; height: 90px; border-radius: 50%; background-color: var(--tertiary-bg);
            color: var(--text-secondary-color); display: none; /* Hidden by default */
            align-items: center; justify-content: center; font-size: 2.8em; font-weight: bold;
        }
        .video-participant.no-video .avatar-placeholder { display: flex !important; }
        .video-participant.no-video video, .video-participant.no-video canvas { display: none !important; } /* canvas added */

        #live-captions-area {
            position: absolute; bottom: var(--control-panel-height); left: 0; right: 0;
            padding: 10px 20px; background-color: rgba(0,0,0,0.7); color: white;
            font-size: 1.1em; text-align: center; z-index: 50;
            max-height: 20vh; overflow-y: auto;
            opacity: 0; visibility: hidden; transition: opacity 0.3s, visibility 0s 0.3s;
        }
        #live-captions-area.visible { opacity: 1; visibility: visible; transition-delay: 0s;}


        /* Sidebar */
        .sidebar {
            width: var(--sidebar-width); background-color: var(--secondary-bg); padding: 0;
            display: flex; flex-direction: column; border-left: 1px solid var(--border-color);
            transition: width 0.3s ease, opacity 0.3s ease, right 0.3s ease-in-out;
            overflow: hidden; flex-shrink: 0;
        }
        .sidebar.collapsed { width: 0; opacity: 0; padding: 0; }
        .sidebar-tabs { display: flex; border-bottom: 1px solid var(--border-color); }
        .sidebar-tab-button {
            flex-grow: 1; padding: 14px 0; background-color: transparent; color: var(--text-secondary-color);
            border: none; border-bottom: 3px solid transparent; cursor: pointer;
            font-size: 1em; font-weight: 500; transition: color 0.2s, border-color 0.2s;
        }
        .sidebar-tab-button i { margin-right: 8px; }
        .sidebar-tab-button:hover { color: var(--text-color); }
        .sidebar-tab-button.active { color: var(--accent-color); border-bottom-color: var(--accent-color); }
        .sidebar-tab-content { padding: 15px; overflow-y: auto; flex-grow: 1; display: none; }
        .sidebar-tab-content.active { display: flex; flex-direction: column; }
        .sidebar-tab-content::-webkit-scrollbar { width: 6px; }
        .sidebar-tab-content::-webkit-scrollbar-track { background: var(--secondary-bg); }
        .sidebar-tab-content::-webkit-scrollbar-thumb { background: var(--tertiary-bg); border-radius: 3px; }

        /* Participants List */
        #participants-list-ul { list-style: none; }
        #participants-list-ul li {
            display: flex; align-items: center; padding: 10px 5px;
            border-bottom: 1px solid var(--tertiary-bg); font-size: 0.95em;
        }
        #participants-list-ul li:last-child { border-bottom: none; }
        .participant-list-avatar {
            width: 36px; height: 36px; border-radius: 50%; background-color: var(--tertiary-bg);
            color: var(--text-secondary-color); display: flex; align-items: center; justify-content: center;
            font-size: 1em; font-weight: bold; margin-right: 12px; flex-shrink: 0;
        }
        .participant-list-name { flex-grow: 1; }
        .participant-list-icons { display: flex; gap: 10px; font-size: 1.1em; color: var(--text-secondary-color); }
        .participant-list-icons i { cursor: pointer; transition: color 0.2s; }
        .participant-list-icons i:hover { color: var(--text-color); }
        .participant-list-icons .fa-microphone-slash { color: var(--danger-color); }
        .participant-list-icons .fa-video-slash { color: var(--text-secondary-color); }
        .participant-list-icons .fa-hand-paper { color: var(--yellow-warning); } /* Corrected class for FA hand */

        /* Chat */
        #chat-messages-container { flex-grow: 1; overflow-y: auto; margin-bottom: 10px; padding-right: 5px; }
        .chat-message {
            display: flex; flex-direction: column; margin-bottom: 12px;
            padding: 8px 12px; border-radius: 18px; max-width: 80%; word-wrap: break-word;
        }
        .chat-message.self { background-color: var(--accent-color); color: white; margin-left: auto; border-bottom-right-radius: var(--border-radius-sm); align-items: flex-end;}
        .chat-message.other { background-color: var(--tertiary-bg); margin-right: auto; border-bottom-left-radius: var(--border-radius-sm); align-items: flex-start;}
        .chat-message .sender { font-weight: 600; font-size: 0.85em; margin-bottom: 3px; color: var(--text-secondary-color); }
        .chat-message.self .sender { color: rgba(255,255,255,0.85); }
        .chat-message .message-text { font-size: 0.95em; }
        .chat-message .timestamp { font-size: 0.75em; color: var(--text-secondary-color); margin-top: 4px; }
        .chat-message.self .timestamp { align-self: flex-end; }
        .chat-message.other .timestamp { align-self: flex-start; }

        #chat-input-area { display: flex; margin-top: 5px; align-items: flex-end;} /* Align items for textarea */
        #chat-input { /* Changed to textarea */
            flex-grow: 1; padding: 10px 15px; border: 1px solid var(--border-color);
            border-radius: 20px; background-color: var(--tertiary-bg); color: var(--text-color);
            outline: none; font-size: 0.95em; resize: none; min-height: 44px; max-height: 120px; /* For textarea */
        }
        #send-chat-button {
            padding: 0 15px; background-color: var(--accent-color); color: white;
            border: none; cursor: pointer; border-radius: 20px; font-size: 1.2em;
            transition: background-color 0.2s; display: flex; align-items: center; justify-content: center;
            margin-left: 8px; height: 44px; /* Match min-height of textarea */ flex-shrink: 0;
        }
        #send-chat-button:hover { background-color: var(--accent-hover-color); }

        .tool-button {
            display: block; width: 100%; text-align: left;
            background-color: var(--tertiary-bg); color: var(--text-color);
            border: 1px solid var(--border-color); padding: 12px 15px;
            border-radius: var(--border-radius-sm); margin-bottom: 8px;
            font-size: 1em; transition: background-color 0.2s;
        }
        .tool-button i { margin-right: 10px; width: 20px; text-align: center;}
        .tool-button:hover { background-color: var(--border-color); }

        #ai-insights-panel { /* New style for AI insights panel */
            padding:10px; background: var(--tertiary-bg);
            border-radius: var(--border-radius-sm); margin-top:10px;
            border: 1px solid var(--border-color);
        }
        #ai-insights-panel h4 { font-size: 1.05em; margin-bottom: 8px; color: var(--text-secondary-color);}
        #ai-insights-panel p, #ai-insights-panel li { font-size: 0.9em; margin-bottom: 5px; }


        /* Polls, Whiteboard (Conceptual Placeholders in Sidebar) */
        .tool-placeholder { text-align: center; color: var(--text-secondary-color); margin-top: 20px; }

        /* Control Panel */
        .control-panel {
            height: var(--control-panel-height); background-color: var(--primary-bg);
            display: flex; justify-content: center; align-items: center;
            padding: 0 20px; gap: 12px; border-top: 1px solid var(--border-color); flex-shrink: 0;
        }
        .control-button {
            background-color: var(--secondary-bg); color: var(--text-color); border: none;
            width: 50px; height: 50px; border-radius: 50%; cursor: pointer; font-size: 1.3em;
            display: flex; align-items: center; justify-content: center;
            transition: background-color 0.2s, color 0.2s, box-shadow 0.2s; position: relative;
        }
        .control-button.active { background-color: var(--accent-color); color: white; }
        .control-button:not(.active):hover { background-color: var(--tertiary-bg); box-shadow: 0 0 8px rgba(0,0,0,0.2); }
        .control-button.hangup { background-color: var(--danger-color); color: white; }
        .control-button.hangup:hover { background-color: var(--danger-hover-color); }

        .tooltip { position: relative; display: inline-block; }
        .tooltip .tooltiptext {
            visibility: hidden; background-color: var(--tertiary-bg); color: #fff; text-align: center;
            border-radius: var(--border-radius-sm); padding: 6px 10px; position: absolute; z-index: 100;
            bottom: calc(100% + 8px); left: 50%; transform: translateX(-50%); opacity: 0;
            transition: opacity 0.2s ease-in-out, visibility 0s 0.2s; font-size: 0.85em;
            white-space: nowrap; box-shadow: var(--shadow-md);
        }
        .tooltip:hover .tooltiptext { visibility: visible; opacity: 1; transition-delay: 0.1s; }
        .reactions-popup {
            position: absolute; bottom: calc(100% + 10px); left: 50%; transform: translateX(-50%);
            background-color: var(--secondary-bg); border: 1px solid var(--border-color);
            border-radius: var(--border-radius-md); padding: 10px; display: flex; gap: 10px;
            box-shadow: var(--shadow-md); z-index: 110;
        }
        .reactions-popup span { font-size: 1.6em; cursor: pointer; padding: 5px; border-radius: var(--border-radius-sm); transition: background-color 0.2s; }
        .reactions-popup span:hover { background-color: var(--tertiary-bg); }

        /* Reactions Fly-up Animation */
        .reaction-emoji {
            position: absolute; bottom: 70px; left: 50%; transform: translateX(-50%);
            font-size: 2.2em; opacity: 1; animation: flyUp 2.5s ease-out forwards;
            pointer-events: none; z-index: 10;
        }
        @keyframes flyUp {
            0% { bottom: 70px; opacity: 1; transform: translateX(-50%) scale(1); }
            100% { bottom: 85%; opacity: 0; transform: translateX(-50%) scale(0.5); }
        }

        /* Spinner */
        .spinner {
            border: 4px solid rgba(255, 255, 255, 0.2); border-radius: 50%;
            border-top-color: var(--accent-color); width: 36px; height: 36px;
            animation: spin 0.8s linear infinite; position: absolute;
            top: 50%; left: 50%; transform: translate(-50%, -50%);
        }
        @keyframes spin { 0% { transform: translate(-50%, -50%) rotate(0deg); } 100% { transform: translate(-50%, -50%) rotate(360deg); } }

        /* Responsive Adjustments */
        @media (max-width: 992px) { /* Larger tablets and small desktops */
            :root { --sidebar-width: 300px; }
        }
        @media (max-width: 768px) { /* Tablets */
            :root { --sidebar-width: 280px; --control-panel-height: 65px; }
            .video-grid-container.grid-layout { grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
            .control-button { width: 45px; height: 45px; font-size: 1.2em; }
            .app-header { padding: 0 15px; }
            .app-logo { font-size: 1.3em; }
        }
         @media (max-width: 480px) { /* Mobile phones */
            .video-grid-container.grid-layout { grid-template-columns: 1fr; } /* Single column */
            .control-panel { gap: 8px; justify-content: space-around; }
            .control-button { width: 42px; height: 42px; font-size: 1.1em; }
            .sidebar {
                position: fixed; right: calc(-1 * var(--sidebar-width)); top: var(--header-height);
                height: calc(100vh - var(--header-height) - var(--control-panel-height));
                z-index: 100; opacity: 1; box-shadow: -5px 0 15px rgba(0,0,0,0.2);
            }
            .sidebar.open { right: 0; width: var(--sidebar-width); }
            #sidebar-toggle-button-header { display: inline-block !important; } /* Ensure visible */
            .tooltip .tooltiptext { display: none; } /* Hide tooltips on mobile to prevent clutter */
            .app-logo { display: none; } /* Hide logo for more space */
            .room-info { flex-grow: 1; text-align: center; }
         }

    </style>
</head>
<body>
    <!-- Entry Modal -->
    <div id="entry-modal" class="modal-overlay visible">
        <div class="modal-content">
            <h2>Join IntelliMeet X</h2>
            <input type="text" id="username-input" placeholder="Your Name" autocomplete="name">
            <input type="text" id="roomid-input" placeholder="Room ID (e.g., 'project-pegasus')" autocomplete="off">
            <button id="join-button"><i class="fas fa-video"></i> Join / Create Room</button>
        </div>
    </div>

    <!-- Settings Modal -->
    <div id="settings-modal" class="modal-overlay">
        <div class="modal-content">
            <h2><i class="fas fa-cog"></i> Settings</h2>
            <div class="settings-section">
                <h3><i class="fas fa-microphone-alt"></i> Audio</h3>
                <label for="audio-input-select">Microphone:</label>
                <select id="audio-input-select"></select>
                <div class="toggle-switch-container">
                    <span>AI Noise Cancellation:</span>
                    <label class="toggle-switch">
                        <input type="checkbox" id="ai-noise-cancellation-toggle" data-state-key="aiNoiseCancellation">
                        <span class="slider"></span>
                    </label>
                </div>
                 <div class="toggle-switch-container">
                    <span>Echo Cancellation:</span>
                    <label class="toggle-switch">
                        <input type="checkbox" id="echo-cancellation-toggle" data-state-key="echoCancellation" checked>
                        <span class="slider"></span>
                    </label>
                </div>
            </div>
            <div class="settings-section">
                <h3><i class="fas fa-video"></i> Video</h3>
                <label for="video-input-select">Camera:</label>
                <select id="video-input-select"></select>
                 <div class="toggle-switch-container">
                    <span>Enable Virtual Background:</span>
                    <label class="toggle-switch">
                        <input type="checkbox" id="virtual-background-toggle" data-state-key="virtualBackgroundEnabled">
                        <span class="slider"></span>
                    </label>
                </div>
                <div id="virtual-background-choices" class="hidden">
                    <p>Choose your virtual background style. This uses your camera feed.</p>
                    <div class="vb-options-buttons">
                        <button id="vb-option-none" data-vb-type="none">None</button>
                        <button id="vb-option-blur" data-vb-type="blur">Blur</button>
                    </div>
                    <p>Predefined Images:</p>
                    <div id="predefined-backgrounds-container">
                        <!-- Thumbnails will be added by JS -->
                    </div>
                    <label for="upload-background-input" style="margin-top:10px;">Upload Custom Image (JPG, PNG):</label>
                    <input type="file" id="upload-background-input" accept="image/jpeg, image/png">
                </div>

                <div class="toggle-switch-container">
                    <span>AI Video Enhancement:</span>
                    <label class="toggle-switch">
                        <input type="checkbox" id="video-enhancement-toggle" data-state-key="videoEnhancement">
                        <span class="slider"></span>
                    </label>
                </div>
                 <div class="toggle-switch-container">
                    <span>Auto Framing:</span>
                    <label class="toggle-switch">
                        <input type="checkbox" id="auto-framing-toggle" data-state-key="autoFraming">
                        <span class="slider"></span>
                    </label>
                </div>
            </div>
             <div class="settings-section">
                <h3><i class="fas fa-closed-captioning"></i> Accessibility</h3>
                 <div class="toggle-switch-container">
                    <span>Live Captions:</span>
                    <label class="toggle-switch">
                        <input type="checkbox" id="live-captions-toggle" data-state-key="liveCaptions">
                        <span class="slider"></span>
                    </label>
                </div>
                <label for="caption-language-select">Caption Language:</label>
                <select id="caption-language-select">
                    <option value="en-US">English (US)</option>
                    <option value="es-ES">Español (España)</option>
                    <option value="fr-FR">Français (France)</option>
                    <option value="de-DE">Deutsch (Deutschland)</option>
                    <option value="ja-JP">日本語 (日本)</option>
                </select>
            </div>
            <!-- New Conceptual Features Section -->
            <div class="settings-section">
                <h3><i class="fas fa-brain"></i> AI Enhancements (Conceptual)</h3>
                <div class="toggle-switch-container">
                    <span>AI Meeting Summaries (Post-meeting):</span>
                    <label class="toggle-switch">
                        <input type="checkbox" id="ai-summary-toggle" data-state-key="aiMeetingSummary">
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="toggle-switch-container">
                    <span>AI Action Item Detection:</span>
                    <label class="toggle-switch">
                        <input type="checkbox" id="ai-action-items-toggle" data-state-key="aiActionItemDetection">
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="toggle-switch-container">
                    <span>Real-time Translation (Captions Ext):</span>
                    <label class="toggle-switch">
                        <input type="checkbox" id="ai-translation-toggle" data-state-key="aiRealtimeTranslation">
                        <span class="slider"></span>
                    </label>
                </div>
            </div>
            <div class="settings-section">
                <h3><i class="fas fa-record-vinyl"></i> Recording (Conceptual)</h3>
                <label for="record-scope-select">Recording Scope:</label>
                <select id="record-scope-select" data-state-key="recordingScope">
                    <option value="full">Full Meeting (Gallery)</option>
                    <option value="self">My Audio/Video Only</option>
                    <option value="speaker">Active Speaker + Shared Screen</option>
                </select>
                 <div class="toggle-switch-container" style="margin-top:10px;">
                    <span>Cloud Recording:</span>
                    <label class="toggle-switch">
                        <input type="checkbox" id="cloud-recording-toggle" data-state-key="cloudRecordingEnabled">
                        <span class="slider"></span>
                    </label>
                </div>
            </div>
            <!-- End New Conceptual Features Section -->
            <button id="close-settings-button" class="modal-close-button"><i class="fas fa-times"></i> Close</button>
        </div>
    </div>

    <!-- Main Application Container -->
    <div class="app-container hidden">
        <header class="app-header">
            <div class="app-logo">IntelliMeet X</div>
            <div class="room-info"><span id="room-id-display"></span></div>
            <div class="header-actions">
                <button id="meeting-info-button" title="Meeting Info"><i class="fas fa-info-circle"></i></button>
                <button id="sidebar-toggle-button-header" title="Toggle Panel"><i class="fas fa-users"></i></button>
                <button id="settings-button-header" title="Settings"><i class="fas fa-cog"></i></button>
            </div>
        </header>

        <div class="main-content-area">
            <div class="video-area">
                <div class="video-layout-controls">
                    <button id="layout-grid-button" class="active" title="Grid View"><i class="fas fa-th-large"></i> Grid</button>
                    <button id="layout-speaker-button" title="Speaker View"><i class="fas fa-user"></i> Speaker</button>
                    <button id="layout-focus-button" title="Focus View"><i class="fas fa-compress-arrows-alt"></i> Focus</button>
                </div>
                <div class="video-grid-container grid-layout" id="video-grid">
                    <div class="video-participant local-participant" id="local-video-container-wrapper">
                        <div class="avatar-placeholder"></div>
                        <video id="local-video" autoplay muted playsinline style="display: block;"></video>
                        <canvas id="local-video-canvas" style="display: none;"></canvas> 
                        <div class="spinner hidden" id="local-video-spinner"></div>
                        <div class="participant-overlay">
                            <span class="participant-name" id="local-participant-name-display">You</span>
                            <div class="participant-status-icons">
                                <span class="status-icon mic-status hidden" id="local-mic-status-icon" title="Microphone Muted"><i class="fas fa-microphone-slash"></i></span>
                                <span class="status-icon video-off hidden" id="local-video-off-icon" title="Video Off"><i class="fas fa-video-slash"></i></span>
                                <span class="status-icon hand-raised hidden" id="local-hand-raised-icon" title="Hand Raised"><i class="fas fa-hand-paper"></i></span>
                            </div>
                        </div>
                    </div>
                </div>
                <div id="live-captions-area"><p id="captions-text"></p></div>
            </div>

            <aside class="sidebar" id="sidebar">
                <div class="sidebar-tabs">
                    <button class="sidebar-tab-button active" data-tab="participants"><i class="fas fa-users"></i> Participants</button>
                    <button class="sidebar-tab-button" data-tab="chat"><i class="fas fa-comments"></i> Chat</button>
                    <button class="sidebar-tab-button" data-tab="tools"><i class="fas fa-tools"></i> Tools</button>
                </div>
                <div id="participants-content" class="sidebar-tab-content active">
                    <h3 style="margin-bottom:10px; font-size: 1.1em;">Participants (<span id="participant-count">0</span>)</h3>
                    <ul id="participants-list-ul"></ul>
                </div>
                <div id="chat-content" class="sidebar-tab-content">
                     <div id="chat-messages-container"></div>
                     <div id="chat-input-area">
                        <textarea id="chat-input" placeholder="Type a message... (Shift+Enter for new line)" rows="1"></textarea>
                        <button id="send-chat-button" title="Send Message" aria-label="Send Chat Message"><i class="fas fa-paper-plane"></i></button>
                     </div>
                </div>
                <div id="tools-content" class="sidebar-tab-content">
                    <h4>Collaboration Tools</h4>
                    <button class="tool-button" id="whiteboard-button" title="Whiteboard"><i class="fas fa-chalkboard"></i> Whiteboard</button>
                    <button class="tool-button" id="polls-button" title="Polls"><i class="fas fa-poll-h"></i> Polls</button>
                    <button class="tool-button" id="file-share-button" title="File Share"><i class="fas fa-share-square"></i> File Share</button>
                    <button class="tool-button" id="breakout-rooms-button" title="Breakout Rooms"><i class="fas fa-users-cog"></i> Breakout Rooms</button>

                    <h4 style="margin-top: 20px;">AI Tools (Conceptual)</h4>
                    <button class="tool-button" id="ai-insights-button"><i class="fas fa-lightbulb"></i> AI Meeting Insights</button>
                    <div id="ai-insights-panel" class="hidden">
                        <h4>AI Generated Insights</h4>
                        <p><strong>Summary:</strong> <span>Waiting for insights...</span></p>
                        <p><strong>Action Items:</strong></p>
                        <ul>
                            <li>No action items identified yet.</li>
                        </ul>
                    </div>
                    <div class="tool-placeholder" style="margin-top:15px;">More tools coming soon!</div>
                </div>
            </aside>
        </div>

        <footer class="control-panel">
            <div class="tooltip">
                <button id="toggle-mic-button" class="control-button active" aria-label="Toggle Microphone"><i class="fas fa-microphone"></i></button>
                <span class="tooltiptext">Mute/Unmute Mic</span>
            </div>
            <div class="tooltip">
                <button id="toggle-video-button" class="control-button active" aria-label="Toggle Video"><i class="fas fa-video"></i></button>
                <span class="tooltiptext">Stop/Start Video</span>
            </div>
            <div class="tooltip">
                <button id="share-screen-button" class="control-button" aria-label="Share Screen"><i class="fas fa-desktop"></i></button>
                <span class="tooltiptext">Share Screen</span>
            </div>
             <div class="tooltip">
                <button id="record-button" class="control-button" aria-label="Record Meeting"><i class="fas fa-record-vinyl"></i></button>
                <span class="tooltiptext">Start/Stop Recording</span>
            </div>
            <div class="tooltip">
                <button id="raise-hand-button" class="control-button" aria-label="Raise Hand"><i class="fas fa-hand-paper"></i></button>
                <span class="tooltiptext">Raise/Lower Hand</span>
            </div>
            <div class="tooltip">
                <button id="reactions-button" class="control-button" aria-label="Send Reaction"><i class="far fa-grin-beam"></i></button> <!-- Changed icon -->
                <span class="tooltiptext">Send Reaction</span>
                 <div class="reactions-popup hidden">
                    <span role="button" tabindex="0" data-emoji="👍" aria-label="Thumbs Up">👍</span> 
                    <span role="button" tabindex="0" data-emoji="❤️" aria-label="Heart">❤️</span> 
                    <span role="button" tabindex="0" data-emoji="😂" aria-label="Laughing">😂</span> 
                    <span role="button" tabindex="0" data-emoji="😮" aria-label="Surprised">😮</span> 
                    <span role="button" tabindex="0" data-emoji="🎉" aria-label="Party Popper">🎉</span>
                    <span role="button" tabindex="0" data-emoji="👏" aria-label="Clapping">👏</span>
                 </div>
            </div>
            <div class="tooltip">
                <button id="hangup-button" class="control-button hangup" aria-label="Leave Call"><i class="fas fa-phone-slash"></i></button>
                <span class="tooltiptext">Leave Call</span>
            </div>
        </footer>
    </div>

    <script>
        // --- IntelliMeet X Client-side JavaScript ---
        'use strict'; // Enable strict mode

        // DOM Elements (grouped for clarity)
        const Modals = {}, Inputs = {}, Buttons = {}, Toggles = {}, Selects = {}, UI = {}, VBElements = {};

        function initializeDOMElements() {
            Modals.entry = document.getElementById('entry-modal');
            Modals.settings = document.getElementById('settings-modal');

            Inputs.username = document.getElementById('username-input');
            Inputs.roomId = document.getElementById('roomid-input');
            Inputs.audioDevice = document.getElementById('audio-input-select');
            Inputs.videoDevice = document.getElementById('video-input-select');
            Inputs.chat = document.getElementById('chat-input');
            Inputs.uploadBackground = document.getElementById('upload-background-input'); // VB

            Buttons.join = document.getElementById('join-button');
            Buttons.settingsHeader = document.getElementById('settings-button-header');
            Buttons.closeSettings = document.getElementById('close-settings-button');
            Buttons.sidebarToggle = document.getElementById('sidebar-toggle-button-header');
            Buttons.sendChat = document.getElementById('send-chat-button');
            Buttons.toggleMic = document.getElementById('toggle-mic-button');
            Buttons.toggleVideo = document.getElementById('toggle-video-button');
            Buttons.shareScreen = document.getElementById('share-screen-button');
            Buttons.record = document.getElementById('record-button');
            Buttons.raiseHand = document.getElementById('raise-hand-button');
            Buttons.reactions = document.getElementById('reactions-button');
            Buttons.hangup = document.getElementById('hangup-button');
            Buttons.layoutGrid = document.getElementById('layout-grid-button');
            Buttons.layoutSpeaker = document.getElementById('layout-speaker-button');
            Buttons.layoutFocus = document.getElementById('layout-focus-button');
            Buttons.whiteboard = document.getElementById('whiteboard-button');
            Buttons.polls = document.getElementById('polls-button');
            Buttons.fileShare = document.getElementById('file-share-button');
            Buttons.breakoutRooms = document.getElementById('breakout-rooms-button');
            Buttons.meetingInfo = document.getElementById('meeting-info-button');
            Buttons.aiInsights = document.getElementById('ai-insights-button'); 
            Buttons.vbOptionNone = document.getElementById('vb-option-none'); // VB
            Buttons.vbOptionBlur = document.getElementById('vb-option-blur'); // VB

            Toggles.aiNoiseCancellation = document.getElementById('ai-noise-cancellation-toggle');
            Toggles.echoCancellation = document.getElementById('echo-cancellation-toggle');
            Toggles.virtualBackground = document.getElementById('virtual-background-toggle');
            Toggles.videoEnhancement = document.getElementById('video-enhancement-toggle');
            Toggles.autoFraming = document.getElementById('auto-framing-toggle');
            Toggles.liveCaptions = document.getElementById('live-captions-toggle');
            Toggles.aiSummary = document.getElementById('ai-summary-toggle'); 
            Toggles.aiActionItems = document.getElementById('ai-action-items-toggle'); 
            Toggles.aiTranslation = document.getElementById('ai-translation-toggle'); 
            Toggles.cloudRecording = document.getElementById('cloud-recording-toggle'); 


            Selects.captionLanguage = document.getElementById('caption-language-select');
            Selects.recordScope = document.getElementById('record-scope-select'); 


            UI.appContainer = document.querySelector('.app-container');
            UI.roomIdDisplay = document.getElementById('room-id-display');
            UI.sidebar = document.getElementById('sidebar');
            UI.videoGrid = document.getElementById('video-grid');
            UI.localVideoWrapper = document.getElementById('local-video-container-wrapper');
            if (UI.localVideoWrapper) { 
                UI.localVideo = UI.localVideoWrapper.querySelector('#local-video');
                UI.localVideoCanvas = UI.localVideoWrapper.querySelector('#local-video-canvas');
                UI.localVideoSpinner = UI.localVideoWrapper.querySelector('#local-video-spinner');
                UI.localParticipantName = UI.localVideoWrapper.querySelector('#local-participant-name-display');
                UI.localMicStatus = UI.localVideoWrapper.querySelector('#local-mic-status-icon');
                UI.localVideoOffStatus = UI.localVideoWrapper.querySelector('#local-video-off-icon');
                UI.localHandRaised = UI.localVideoWrapper.querySelector('#local-hand-raised-icon');
                UI.localAvatar = UI.localVideoWrapper.querySelector('.avatar-placeholder');
            }
            UI.participantCount = document.getElementById('participant-count');
            UI.participantsList = document.getElementById('participants-list-ul');
            UI.chatMessages = document.getElementById('chat-messages-container');
            UI.liveCaptionsArea = document.getElementById('live-captions-area');
            UI.captionsText = document.getElementById('captions-text');
            UI.aiInsightsPanel = document.getElementById('ai-insights-panel'); 
            if (Buttons.reactions) { 
                 const reactionsTooltip = Buttons.reactions.closest('.tooltip');
                 if(reactionsTooltip) UI.reactionsPopup = reactionsTooltip.querySelector('.reactions-popup');
            }

            VBElements.choicesContainer = document.getElementById('virtual-background-choices'); // VB
            VBElements.predefinedContainer = document.getElementById('predefined-backgrounds-container'); // VB
        }


        // Global State
        let localStream, screenStream, processedLocalAudioStream;
        let localUserId, localUsername, currentRoomId;
        let ws;
        let peerConnections = {}; 
        let mediaStates = {
            isMicEnabled: true, isVideoEnabled: true, isScreenSharing: false, isHandRaised: false,
            isRecording: false, aiNoiseCancellation: false, echoCancellation: true, 
            virtualBackgroundEnabled: false, // Renamed from virtualBackground
            virtualBackgroundType: 'none', // 'none', 'blur', 'image'
            virtualBackgroundImageSrc: null, // URL or DataURL for image
            videoEnhancement: false, autoFraming: false, liveCaptions: false,
            aiMeetingSummary: false, aiActionItemDetection: false, aiRealtimeTranslation: false, 
            recordingScope: 'full', cloudRecordingEnabled: false 
        };

        let audioContext, mediaStreamSourceNode, gainNode, lowPassFilterNode, highPassFilterNode, compressorNode;

        // Virtual Background specific state
        let selfieSegmentation = null;
        let isVBProcessing = false;
        let currentVBImageElement = null; // To hold the loaded Image() object for VB
        let animationFrameIdVB = null;


        let speechRecognition = null;
        let mediaRecorder = null;
        let recordedChunks = [];

        const STUN_SERVERS = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };
        const DB_NAME = 'IntelliMeetXPrefs_v3'; // Incremented DB version due to new VB states
        const DB_VERSION = 1;
        const PREFS_STORE_NAME = 'userPreferences_v3';
        let db; 

        const PREDEFINED_BACKGROUNDS = [ // Add paths to your images
            { name: "Office", url: "https://picsum.photos/seed/office/640/360" },
            { name: "Cafe", url: "https://picsum.photos/seed/cafe/640/360" },
            { name: "Nature", url: "https://picsum.photos/seed/nature/640/360" },
            { name: "Abstract", url: "https://picsum.photos/seed/abstract/640/360" }
        ];

        // --- Initialization and Setup ---
        async function initializeApp() {
            console.log("IntelliMeet X: Initializing App...");
            initializeDOMElements(); 
            try {
                await initDB(); 
                await loadPreferences();
            } catch (error) { console.error("DB/Prefs init error:", error); }

            initializeVirtualBackgroundSystem(); // Setup MediaPipe and VB UI
            setupEventListeners(); 
            await populateDeviceSelectors(); 
            updateSidebarToggleButton();
            applyInitialMediaStatesFromPrefs(); // Apply loaded preferences for VB etc.
            console.log("IntelliMeet X Initialized Successfully.");
        }

        function applyInitialMediaStatesFromPrefs() {
            // Virtual Background
            if (VBElements.choicesContainer && Toggles.virtualBackground) {
                VBElements.choicesContainer.classList.toggle('hidden', !mediaStates.virtualBackgroundEnabled);
                Toggles.virtualBackground.checked = mediaStates.virtualBackgroundEnabled;
                updateVBOptionsUI(); // Selects the correct button/thumbnail
            }
            // Other toggles are handled by loadPreferences directly updating their 'checked' state
        }


        function setupEventListeners() {
            console.log("Setting up event listeners...");
            try {
                if(Buttons.join) Buttons.join.addEventListener('click', handleJoinRoom); else console.warn("Join button not found");
                if(Inputs.username) Inputs.username.addEventListener('keypress', (e) => { if (e.key === 'Enter') Inputs.roomId?.focus(); });
                if(Inputs.roomId) Inputs.roomId.addEventListener('keypress', (e) => { if (e.key === 'Enter') handleJoinRoom(); });

                if(Buttons.settingsHeader) Buttons.settingsHeader.addEventListener('click', () => toggleModal(Modals.settings, true)); else console.warn("SettingsHeader button not found");
                if(Buttons.closeSettings) {
                    Buttons.closeSettings.addEventListener('click', () => {
                        console.log("Close settings button clicked");
                        toggleModal(Modals.settings, false);
                    });
                } else {
                     console.warn("CloseSettings button not found");
                }


                if(Inputs.audioDevice) Inputs.audioDevice.addEventListener('change', handleDeviceChange);
                if(Inputs.videoDevice) Inputs.videoDevice.addEventListener('change', handleDeviceChange);

                Object.values(Toggles).forEach(toggle => {
                    if(toggle) toggle.addEventListener('change', handleToggleChange);
                    else console.warn("A toggle element is null during listener setup.");
                });
                if(Selects.captionLanguage) Selects.captionLanguage.addEventListener('change', handleCaptionLanguageChange);
                if(Selects.recordScope) Selects.recordScope.addEventListener('change', handleRecordingScopeChange); 

                if(Buttons.sidebarToggle) Buttons.sidebarToggle.addEventListener('click', toggleSidebar);
                document.querySelectorAll('.sidebar-tab-button').forEach(button => {
                    button.addEventListener('click', () => switchSidebarTab(button.dataset.tab));
                });

                if(Buttons.toggleMic) Buttons.toggleMic.addEventListener('click', toggleMic);
                if(Buttons.toggleVideo) Buttons.toggleVideo.addEventListener('click', toggleVideo);
                if(Buttons.shareScreen) Buttons.shareScreen.addEventListener('click', toggleScreenShare);
                if(Buttons.record) Buttons.record.addEventListener('click', toggleRecording);
                if(Buttons.raiseHand) Buttons.raiseHand.addEventListener('click', toggleHandRaise);
                if(Buttons.reactions) Buttons.reactions.addEventListener('click', showReactionsPopup);

                if (UI.reactionsPopup) {
                    UI.reactionsPopup.querySelectorAll('span[data-emoji]').forEach(emojiEl => {
                        emojiEl.addEventListener('click', () => sendReaction(emojiEl.dataset.emoji));
                        emojiEl.addEventListener('keypress', (e) => { 
                            if (e.key === 'Enter' || e.key === ' ') sendReaction(emojiEl.dataset.emoji);
                        });
                    });
                } else { console.warn("Reactions popup container not found for event listeners."); }

                if(Buttons.hangup) Buttons.hangup.addEventListener('click', handleHangup);
                if(Buttons.sendChat) Buttons.sendChat.addEventListener('click', sendChatMessage);
                if(Inputs.chat) Inputs.chat.addEventListener('keypress', (e) => { 
                    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
                });

                if(Buttons.layoutGrid) Buttons.layoutGrid.addEventListener('click', () => applyVideoLayout('grid'));
                if(Buttons.layoutSpeaker) Buttons.layoutSpeaker.addEventListener('click', () => applyVideoLayout('speaker'));
                if(Buttons.layoutFocus) Buttons.layoutFocus.addEventListener('click', () => applyVideoLayout('focus'));

                // Conceptual Tool Buttons
                [Buttons.whiteboard, Buttons.polls, Buttons.fileShare, Buttons.breakoutRooms].forEach(btn => {
                    if(btn) btn.addEventListener('click', (e) => {
                        const toolId = e.currentTarget.id.replace('-button', '');
                        const toolName = e.currentTarget.title || e.currentTarget.textContent.trim();
                        console.log("Conceptual tool button clicked:", toolId);
                        alert(`${toolName} feature is conceptual.`);
                        broadcastToRoom({ type: 'tool_interaction', toolId: toolId, toolName: toolName });
                    });
                });
                if(Buttons.meetingInfo) Buttons.meetingInfo.addEventListener('click', (e) => {
                    alert("Meeting Info: Conceptual feature to show room details, invite link, etc.");
                });
                if(Buttons.aiInsights) Buttons.aiInsights.addEventListener('click', toggleAIInsightsPanel); 


                window.addEventListener('beforeunload', handleBeforeUnload);
                document.addEventListener('fullscreenchange', handleFullscreenChange);

                // Virtual Background Listeners
                if (Buttons.vbOptionNone) Buttons.vbOptionNone.addEventListener('click', () => setVirtualBackground('none'));
                if (Buttons.vbOptionBlur) Buttons.vbOptionBlur.addEventListener('click', () => setVirtualBackground('blur'));
                if (Inputs.uploadBackground) Inputs.uploadBackground.addEventListener('change', handleVBImageUpload);


                console.log("Event listeners setup complete.");
            } catch (error) {
                console.error("Error during setupEventListeners:", error);
            }
        }

        function toggleModal(modalElement, show) {
            if (!modalElement) { console.error("toggleModal: modalElement is null"); return; }
            console.log("Toggling modal:", modalElement.id, "Show:", show);
            if (show) {
                modalElement.classList.add('visible');
                if (modalElement === Modals.settings) populateDeviceSelectors(); // Repopulate on open
            } else {
                modalElement.classList.remove('visible');
            }
        }

        async function initDB() {
             console.log("Initializing DB...");
            return new Promise((resolve, reject) => {
                if (!('indexedDB' in window)) {
                    console.warn('IndexedDB not supported.'); return reject('IndexedDB not supported');
                }
                const request = indexedDB.open(DB_NAME, DB_VERSION);
                request.onerror = (e) => { console.error("DB error:", e.target.error); reject(e.target.error); };
                request.onsuccess = (e) => { db = e.target.result; console.log("DB Initialized."); resolve(db); };
                request.onupgradeneeded = (e) => {
                    const storeDb = e.target.result;
                    if (!storeDb.objectStoreNames.contains(PREFS_STORE_NAME)) {
                        storeDb.createObjectStore(PREFS_STORE_NAME, { keyPath: 'id' });
                        console.log("DB upgraded, object store created.");
                    }
                };
            });
        }

        async function savePreferences() {
            if (!db) { console.warn("DB not available for saving preferences."); return; }
            console.log("Saving preferences...");
            try {
                const transaction = db.transaction(PREFS_STORE_NAME, 'readwrite');
                const store = transaction.objectStore(PREFS_STORE_NAME);
                const prefs = {
                    id: 'currentUser',
                    username: localUsername || Inputs.username?.value,
                    audioInputId: Inputs.audioDevice?.value,
                    videoInputId: Inputs.videoDevice?.value,
                    captionLanguage: Selects.captionLanguage?.value,
                    ...mediaStates 
                };
                Object.keys(Toggles).forEach(key => { 
                    const stateKey = Toggles[key]?.dataset.stateKey;
                    if(Toggles[key] && stateKey && prefs.hasOwnProperty(stateKey)) { // Ensure stateKey exists in prefs
                        prefs[stateKey] = Toggles[key].checked;
                    }
                });
                if (Selects.recordScope) prefs.recordingScope = Selects.recordScope.value; 

                store.put(prefs);
                console.log("Preferences saved:", prefs);
            } catch (error) { console.error("Error saving preferences:", error); }
        }

        async function loadPreferences() {
            if (!db) { console.warn("DB not available for loading preferences."); return; }
            console.log("Loading preferences...");
            return new Promise((resolve, reject) => {
                try {
                    const transaction = db.transaction(PREFS_STORE_NAME, 'readonly');
                    const store = transaction.objectStore(PREFS_STORE_NAME);
                    const request = store.get('currentUser');
                    request.onsuccess = (event) => {
                        const prefs = event.target.result;
                        console.log("Preferences loaded from DB:", prefs);
                        if (prefs) {
                            if (Inputs.username && prefs.username) Inputs.username.value = prefs.username;
                            localStorage.setItem('preferredAudioInput', prefs.audioInputId || '');
                            localStorage.setItem('preferredVideoInput', prefs.videoInputId || '');

                            Object.keys(mediaStates).forEach(key => {
                                if (prefs[key] !== undefined) mediaStates[key] = prefs[key];
                            });

                            Object.keys(Toggles).forEach(key => {
                                const toggleElement = Toggles[key];
                                const stateKey = toggleElement?.dataset.stateKey;
                                if(toggleElement && stateKey && prefs[stateKey] !== undefined) {
                                    toggleElement.checked = prefs[stateKey];
                                }
                            });
                            if(Selects.captionLanguage && prefs.captionLanguage) Selects.captionLanguage.value = prefs.captionLanguage;
                            if(Selects.recordScope && prefs.recordingScope) Selects.recordScope.value = prefs.recordingScope; 
                        }
                        resolve();
                    };
                    request.onerror = (e) => { console.error("Error loading prefs from DB:", e.target.error); reject(e.target.error); };
                } catch (error) { console.error("Error initiating pref load from DB:", error); reject(error); }
            });
        }

        async function handleJoinRoom() {
            console.log("handleJoinRoom called");
            if (!Inputs.username || !Inputs.roomId) { console.error("Username or RoomID input not found"); return; }
            localUsername = Inputs.username.value.trim();
            currentRoomId = Inputs.roomId.value.trim();

            if (!localUsername || !currentRoomId) {
                alert('Please enter your name and a room ID.'); return;
            }

            localUserId = `user-${generateUUID()}`; 
            if(UI.localParticipantName) UI.localParticipantName.textContent = `${localUsername} (You)`;
            if(UI.roomIdDisplay) UI.roomIdDisplay.textContent = currentRoomId;

            toggleModal(Modals.entry, false);
            if(UI.appContainer) UI.appContainer.classList.remove('hidden');

            if (window.innerWidth <= 480) { 
                 if(UI.sidebar) { UI.sidebar.classList.remove('open'); UI.sidebar.classList.add('collapsed'); }
            } else {
                 if(UI.sidebar) { UI.sidebar.classList.remove('collapsed'); UI.sidebar.classList.remove('open'); }
            }
            updateSidebarToggleButton();

            try {
                await startLocalMedia(); 
                await savePreferences(); 
                connectWebSocket();
                updateLocalVideoTileAppearance(); 
            } catch (error) {
                console.error("Error during join room process:", error);
                alert("Failed to join room. Please check console for errors.");
            }
        }

        async function startLocalMedia(isSwitching = false) {
            console.log("startLocalMedia called, isSwitching:", isSwitching);
            if (localStream && !isSwitching) { 
                await applyAudioProcessingSettings(); return;
            }
            if (localStream && isSwitching) { 
                localStream.getTracks().forEach(track => track.stop());
                if (audioContext && audioContext.state !== 'closed') { await audioContext.close(); audioContext = null; }
                if (isVBProcessing) stopVirtualBackgroundEffect(); // Stop VB if active during switch
            }

            if(UI.localVideoSpinner) UI.localVideoSpinner.classList.remove('hidden');
            try {
                const audioConstraints = {
                    deviceId: Inputs.audioDevice?.value ? { exact: Inputs.audioDevice.value } : undefined,
                    echoCancellation: mediaStates.echoCancellation, 
                    noiseSuppression: !mediaStates.aiNoiseCancellation, 
                    autoGainControl: true 
                };
                const videoConstraints = { 
                    deviceId: Inputs.videoDevice?.value ? { exact: Inputs.videoDevice.value } : undefined,
                    width: { ideal: 1280 }, height: { ideal: 720 } 
                };

                const rawMediaStream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints, video: videoConstraints });
                if(UI.localVideo) UI.localVideo.srcObject = null;

                if (rawMediaStream.getAudioTracks().length > 0) {
                    processedLocalAudioStream = await setupAudioProcessingGraph(rawMediaStream.getAudioTracks()[0]);
                    localStream = new MediaStream([...rawMediaStream.getVideoTracks(), ...processedLocalAudioStream.getAudioTracks()]);
                } else { localStream = rawMediaStream; }

                if(UI.localVideo) {
                    UI.localVideo.srcObject = localStream; 
                    await UI.localVideo.play().catch(e => console.warn("Local video play error:", e));
                }

                localStream?.getAudioTracks().forEach(track => track.enabled = mediaStates.isMicEnabled);
                localStream?.getVideoTracks().forEach(track => track.enabled = mediaStates.isVideoEnabled);

                if (mediaStates.virtualBackgroundEnabled) {
                    await startVirtualBackgroundEffect(); // Start VB if enabled
                } else {
                    updateLocalVideoTileAppearance(); // Ensure raw video is shown if VB is off
                }
                if (mediaStates.liveCaptions) await toggleLiveCaptions(true);

                if (isSwitching) {
                    for (const remoteId in peerConnections) {
                        const pc = peerConnections[remoteId]?.pc; if (!pc) continue;
                        localStream?.getTracks().forEach(track => {
                            const sender = pc.getSenders().find(s => s.track && s.track.kind === track.kind);
                            if (sender) sender.replaceTrack(track).catch(e => console.error("Track replace error:", e));
                        });
                    }
                }
                updateLocalUIMediaStates();

            } catch (error) {
                console.error('Media access error:', error);
                alert(`Media access failed: ${error.name} - ${error.message}. Check permissions.`);
                mediaStates.isMicEnabled = false; mediaStates.isVideoEnabled = false;
                updateLocalUIMediaStates();
            } finally {
                if(UI.localVideoSpinner) UI.localVideoSpinner.classList.add('hidden');
            }
        }


        async function handleDeviceChange() {
            console.log("handleDeviceChange called");
            try {
                await startLocalMedia(true); 
                await savePreferences(); 
            } catch(error) {
                console.error("Error in handleDeviceChange:", error);
            }
        }

        async function handleToggleChange(event) {
            if (!event || !event.target) { console.error("handleToggleChange: Invalid event or target"); return; }
            const toggleId = event.target.id;
            const isChecked = event.target.checked;
            const stateKey = event.target.dataset.stateKey; 

            console.log(`Toggle changed: ${toggleId}, Checked: ${isChecked}, StateKey: ${stateKey}`);

            if (stateKey && mediaStates.hasOwnProperty(stateKey)) {
                mediaStates[stateKey] = isChecked;
            } else {
                console.warn(`No mediaStates key found for toggle: ${toggleId} or stateKey: ${stateKey}`);
            }

            try {
                switch(toggleId) {
                    case 'ai-noise-cancellation-toggle': await applyAudioProcessingSettings(); break;
                    case 'echo-cancellation-toggle': await startLocalMedia(true); break; 
                    case 'virtual-background-toggle': // Main VB enable/disable
                        if (VBElements.choicesContainer) VBElements.choicesContainer.classList.toggle('hidden', !isChecked);
                        if (isChecked) {
                           await startVirtualBackgroundEffect(); // Uses current mediaStates.virtualBackgroundType
                        } else {
                           await stopVirtualBackgroundEffect();
                        }
                        break;
                    case 'video-enhancement-toggle': console.log("Video Enhancement (conceptual):", isChecked); if(isChecked) alert("AI Video Enhancement is conceptually active."); break;
                    case 'auto-framing-toggle': console.log("Auto Framing (conceptual):", isChecked); if(isChecked) alert("Auto Framing is conceptually active."); break;
                    case 'live-captions-toggle': await toggleLiveCaptions(isChecked); break;
                    case 'ai-summary-toggle': console.log("AI Summary Toggle (conceptual):", isChecked); if(isChecked) alert("AI Meeting Summaries will be conceptually generated post-meeting."); break;
                    case 'ai-action-items-toggle': console.log("AI Action Items Toggle (conceptual):", isChecked); if(isChecked) alert("AI Action Item Detection is now conceptually active."); break;
                    case 'ai-translation-toggle': console.log("AI Realtime Translation Toggle (conceptual):", isChecked); if(isChecked) alert("Real-time translation for captions is conceptually enabled."); break;
                    case 'cloud-recording-toggle': console.log("Cloud Recording Toggle (conceptual):", isChecked); if(isChecked) alert("Cloud recording is conceptually enabled. Recordings would be 'sent' to a server."); break;
                    default: console.warn("Unknown toggle ID:", toggleId);
                }
                await savePreferences();
            } catch(error) {
                 console.error(`Error handling toggle ${toggleId}:`, error);
            }
        }

        async function setupAudioProcessingGraph(rawAudioTrack) { 
            console.log("Setting up audio processing graph");
            if (audioContext && audioContext.state !== 'closed') await audioContext.close();
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            mediaStreamSourceNode = audioContext.createMediaStreamSource(new MediaStream([rawAudioTrack]));
            gainNode = audioContext.createGain();
            lowPassFilterNode = audioContext.createBiquadFilter(); lowPassFilterNode.type = "lowpass";
            highPassFilterNode = audioContext.createBiquadFilter(); highPassFilterNode.type = "highpass";
            compressorNode = audioContext.createDynamicsCompressor();
            compressorNode.threshold.setValueAtTime(-50, audioContext.currentTime);
            compressorNode.knee.setValueAtTime(40, audioContext.currentTime);
            compressorNode.ratio.setValueAtTime(12, audioContext.currentTime);
            compressorNode.attack.setValueAtTime(0.003, audioContext.currentTime);
            compressorNode.release.setValueAtTime(0.25, audioContext.currentTime);
            let currentNode = mediaStreamSourceNode;
            currentNode.connect(highPassFilterNode); currentNode = highPassFilterNode;
            currentNode.connect(lowPassFilterNode); currentNode = lowPassFilterNode;
            currentNode.connect(compressorNode); currentNode = compressorNode;
            currentNode.connect(gainNode);
            const dest = audioContext.createMediaStreamDestination();
            gainNode.connect(dest);
            await applyAudioProcessingSettings();
            return dest.stream;
        }
        async function applyAudioProcessingSettings() {
            if (!audioContext || audioContext.state === 'closed' || !lowPassFilterNode || !highPassFilterNode) {
                console.warn("Audio context or filters not ready for applying settings.");
                return;
            }
            console.log("Applying audio processing settings, AI Noise Cancellation:", mediaStates.aiNoiseCancellation);
            if (mediaStates.aiNoiseCancellation) {
                lowPassFilterNode.frequency.linearRampToValueAtTime(3800, audioContext.currentTime + 0.1); 
                highPassFilterNode.frequency.linearRampToValueAtTime(150, audioContext.currentTime + 0.1);
            } else {
                lowPassFilterNode.frequency.linearRampToValueAtTime(20000, audioContext.currentTime + 0.1);
                highPassFilterNode.frequency.linearRampToValueAtTime(20, audioContext.currentTime + 0.1);
            }
        }

        // --- Virtual Background System ---
        function initializeVirtualBackgroundSystem() {
            if (typeof SelfieSegmentation === "undefined") {
                console.error("MediaPipe SelfieSegmentation not loaded!");
                alert("Virtual Background feature cannot be initialized. MediaPipe library missing.");
                if(Toggles.virtualBackground) Toggles.virtualBackground.disabled = true;
                return;
            }

            selfieSegmentation = new SelfieSegmentation({locateFile: (file) => {
                return `https://cdn.jsdelivr.net/npm/@mediapipe/selfie_segmentation/${file}`;
            }});
            selfieSegmentation.setOptions({ modelSelection: 1 }); // 0 for general (faster), 1 for landscape (more accurate)
            selfieSegmentation.onResults(onSegmentationResults);

            // Populate predefined backgrounds
            if (VBElements.predefinedContainer) {
                PREDEFINED_BACKGROUNDS.forEach(bg => {
                    const img = document.createElement('img');
                    img.src = bg.url;
                    img.alt = bg.name;
                    img.title = bg.name;
                    img.classList.add('vb-thumbnail');
                    img.dataset.vbSrc = bg.url;
                    img.addEventListener('click', () => setVirtualBackground('image', bg.url));
                    VBElements.predefinedContainer.appendChild(img);
                });
            }
            updateVBOptionsUI(); // To select based on loaded prefs
        }

        async function setVirtualBackground(type, imageSrc = null) {
            console.log(`Setting VB: type=${type}, src=${imageSrc}`);
            mediaStates.virtualBackgroundType = type;
            mediaStates.virtualBackgroundImageSrc = type === 'image' ? imageSrc : null;

            currentVBImageElement = null; // Reset current image
            if (type === 'image' && imageSrc) {
                try {
                    currentVBImageElement = await loadImage(imageSrc);
                } catch (error) {
                    console.error("Failed to load background image:", error);
                    alert("Failed to load background image. Reverting to 'None'.");
                    mediaStates.virtualBackgroundType = 'none';
                    mediaStates.virtualBackgroundImageSrc = null;
                }
            }

            updateVBOptionsUI();
            await savePreferences();

            if (mediaStates.virtualBackgroundEnabled && localStream && UI.localVideo && !UI.localVideo.paused) {
                 // If VB is already on, just changing type/image, effect should restart or continue
                await stopVirtualBackgroundEffect(); // Stop current if any
                await startVirtualBackgroundEffect(); // Start new one
            } else if (!mediaStates.virtualBackgroundEnabled) {
                await stopVirtualBackgroundEffect(); // Ensure it's off
            }
        }

        function loadImage(src) {
            return new Promise((resolve, reject) => {
                const img = new Image();
                img.crossOrigin = "anonymous"; // Important for picsum or other external images if used
                img.onload = () => resolve(img);
                img.onerror = (err) => reject(err);
                img.src = src;
            });
        }

        function handleVBImageUpload(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    setVirtualBackground('image', e.target.result);
                }
                reader.readAsDataURL(file);
            }
        }

        async function startVirtualBackgroundEffect() {
            if (!mediaStates.virtualBackgroundEnabled || !localStream || !UI.localVideo || !UI.localVideoCanvas || !selfieSegmentation) {
                console.warn("Cannot start VB: Not enabled, no stream, or UI/MediaPipe not ready.");
                await stopVirtualBackgroundEffect(); // Ensure it's visually off
                return;
            }
            if (isVBProcessing) return; // Already processing

            console.log("Starting Virtual Background Effect. Type:", mediaStates.virtualBackgroundType);
            isVBProcessing = true;
            UI.localVideo.style.display = 'none';
            UI.localVideoCanvas.style.display = 'block';
            UI.localVideoWrapper.classList.add('virtual-bg-active');


            // Ensure canvas dimensions match video
            if (UI.localVideo.videoWidth > 0 && UI.localVideo.videoHeight > 0) {
                 UI.localVideoCanvas.width = UI.localVideo.videoWidth;
                 UI.localVideoCanvas.height = UI.localVideo.videoHeight;
            } else { // Fallback if video metadata not yet loaded
                const trackSettings = localStream.getVideoTracks()[0]?.getSettings();
                UI.localVideoCanvas.width = trackSettings?.width || 640;
                UI.localVideoCanvas.height = trackSettings?.height || 360;
            }


            // Pre-load image if it's an image type and not loaded yet
            if (mediaStates.virtualBackgroundType === 'image' && mediaStates.virtualBackgroundImageSrc && !currentVBImageElement) {
                try {
                    currentVBImageElement = await loadImage(mediaStates.virtualBackgroundImageSrc);
                } catch (error) {
                    console.error("Failed to load background image on start:", error);
                    // Fallback or notify user
                    await setVirtualBackground('none'); // Revert to none if image fails
                    // No need to call startVirtualBackgroundEffect again from here, setVirtualBackground will handle it if needed
                    return;
                }
            }

            processVirtualBackgroundFrame();
        }

        async function processVirtualBackgroundFrame() {
            if (!isVBProcessing || !localStream || UI.localVideo.paused || UI.localVideo.ended || UI.localVideo.readyState < 2) { //readyState < 2 means not enough data
                stopVirtualBackgroundEffect(); // Stop if conditions are not met
                return;
            }
            try {
                await selfieSegmentation.send({ image: UI.localVideo });
            } catch (error) {
                console.error("Error sending frame to MediaPipe:", error);
                // Potentially stop VB if errors persist
            }
            animationFrameIdVB = requestAnimationFrame(processVirtualBackgroundFrame);
        }


        async function stopVirtualBackgroundEffect() {
            console.log("Stopping Virtual Background Effect");
            isVBProcessing = false;
            if (animationFrameIdVB) {
                cancelAnimationFrame(animationFrameIdVB);
                animationFrameIdVB = null;
            }
            if (UI.localVideo) UI.localVideo.style.display = 'block';
            if (UI.localVideoCanvas) {
                UI.localVideoCanvas.style.display = 'none';
                const ctx = UI.localVideoCanvas.getContext('2d');
                if (ctx) ctx.clearRect(0, 0, UI.localVideoCanvas.width, UI.localVideoCanvas.height);
            }
            if(UI.localVideoWrapper) UI.localVideoWrapper.classList.remove('virtual-bg-active');
            updateLocalVideoTileAppearance(); // General update
        }

        function onSegmentationResults(results) {
            if (!isVBProcessing || !UI.localVideoCanvas || !results.segmentationMask || !results.image) {
                return;
            }
            const canvasCtx = UI.localVideoCanvas.getContext('2d');
            const canvasWidth = UI.localVideoCanvas.width;
            const canvasHeight = UI.localVideoCanvas.height;

            canvasCtx.save();
            canvasCtx.clearRect(0, 0, canvasWidth, canvasHeight);

            // Draw the base (video or background)
            switch (mediaStates.virtualBackgroundType) {
                case 'blur':
                    canvasCtx.filter = 'blur(8px)'; // Blur strength
                    canvasCtx.drawImage(results.image, 0, 0, canvasWidth, canvasHeight);
                    canvasCtx.filter = 'none'; // Reset filter for person
                    break;
                case 'image':
                    if (currentVBImageElement && currentVBImageElement.complete) {
                        canvasCtx.drawImage(currentVBImageElement, 0, 0, canvasWidth, canvasHeight);
                    } else { // Fallback if image not loaded
                        canvasCtx.fillStyle = '#000066'; // Dark blue fallback
                        canvasCtx.fillRect(0, 0, canvasWidth, canvasHeight);
                    }
                    break;
                case 'none':
                default: // No background processing, draw video directly (should be handled by stopVirtualBackgroundEffect)
                    canvasCtx.drawImage(results.image, 0, 0, canvasWidth, canvasHeight);
                    canvasCtx.restore();
                    return; // No compositing needed for 'none'
            }

            // Composite person over the background
            canvasCtx.globalCompositeOperation = 'destination-out'; // Cut out the person shape from the BG
            canvasCtx.drawImage(results.segmentationMask, 0, 0, canvasWidth, canvasHeight);

            canvasCtx.globalCompositeOperation = 'source-over'; // Draw person on top
            canvasCtx.drawImage(results.image, 0, 0, canvasWidth, canvasHeight);

            canvasCtx.restore();
        }

        function updateVBOptionsUI() {
            // Update button selections
            document.querySelectorAll('#virtual-background-choices .vb-options-buttons button').forEach(btn => {
                btn.classList.toggle('selected', btn.dataset.vbType === mediaStates.virtualBackgroundType);
            });

            // Update thumbnail selections
            if (VBElements.predefinedContainer) {
                VBElements.predefinedContainer.querySelectorAll('.vb-thumbnail').forEach(thumb => {
                    thumb.classList.toggle('selected',
                        mediaStates.virtualBackgroundType === 'image' &&
                        thumb.dataset.vbSrc === mediaStates.virtualBackgroundImageSrc
                    );
                });
            }
            // If current type is "image" but no src, or src doesn't match any predefined, deselect all.
            if (mediaStates.virtualBackgroundType === 'image' && !mediaStates.virtualBackgroundImageSrc) {
                 if (VBElements.predefinedContainer) VBElements.predefinedContainer.querySelectorAll('.vb-thumbnail.selected').forEach(t => t.classList.remove('selected'));
            }
        }

        // --- End Virtual Background System ---


        async function toggleLiveCaptions(enable) {
            console.log("toggleLiveCaptions:", enable);
            if (!UI.liveCaptionsArea || !UI.captionsText || !Selects.captionLanguage || !Toggles.liveCaptions) {
                 console.warn("Caption UI elements not found."); return;
            }
            if (enable) {
                if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                    alert("Live captions not supported by your browser."); Toggles.liveCaptions.checked = false; mediaStates.liveCaptions = false; return;
                }
                UI.liveCaptionsArea.classList.add('visible');
                const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
                speechRecognition = new SR();
                speechRecognition.continuous = true; speechRecognition.interimResults = true;
                speechRecognition.lang = Selects.captionLanguage.value || 'en-US';
                speechRecognition.onresult = (e) => {
                    let iT = '', fT = '';
                    for (let i = e.resultIndex; i < e.results.length; ++i) {
                        if (e.results[i].isFinal) fT += e.results[i][0].transcript; else iT += e.results[i][0].transcript;
                    }
                    UI.captionsText.innerHTML = fT + `<i style="color: #aaa;">${iT}</i>`;
                    if (fT.trim()) broadcastToRoom({ type: 'caption-segment', text: fT.trim(), lang: speechRecognition.lang });
                    if (mediaStates.aiRealtimeTranslation && fT.trim()) {
                        console.log(`Conceptual translation for: "${fT.trim()}" (lang: ${speechRecognition.lang})`);
                    }
                };
                speechRecognition.onerror = (e) => console.error("SR error:", e.error);
                speechRecognition.onend = () => { if (mediaStates.liveCaptions && speechRecognition) { try { speechRecognition.start(); } catch(e){ console.warn("SR restart failed:", e); }}};
                try { speechRecognition.start(); console.log("Captions started, lang:", speechRecognition.lang); }
                catch (e) { console.error("SR start fail:", e); Toggles.liveCaptions.checked = false; mediaStates.liveCaptions = false; UI.liveCaptionsArea.classList.remove('visible'); alert("Could not start live captions.");}
            } else {
                UI.liveCaptionsArea.classList.remove('visible'); UI.captionsText.textContent = '';
                if (speechRecognition) { speechRecognition.stop(); speechRecognition = null; console.log("Captions stopped.");}
            }
             mediaStates.liveCaptions = enable; 
        }
        async function handleCaptionLanguageChange() {
            console.log("handleCaptionLanguageChange to:", Selects.captionLanguage?.value);
            if (mediaStates.liveCaptions && speechRecognition) {
                await toggleLiveCaptions(false); 
                await toggleLiveCaptions(true);  
            }
            await savePreferences();
        }

        async function handleRecordingScopeChange() {
            if (!Selects.recordScope) return;
            mediaStates.recordingScope = Selects.recordScope.value;
            console.log("Conceptual recording scope set to:", mediaStates.recordingScope);
            await savePreferences();
        }

        function connectWebSocket() { 
            console.log("Connecting WebSocket...");
            const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
            const encodedUsername = encodeURIComponent(localUsername);
            ws = new WebSocket(`${wsProtocol}://${window.location.host}/ws/${currentRoomId}/${localUserId}/${encodedUsername}`);
            ws.onopen = () => console.log('WebSocket connected to room:', currentRoomId);
            ws.onmessage = handleWebSocketMessage;
            ws.onclose = (event) => { console.log('WebSocket disconnected:', event.reason, event.code); cleanupSession(false); };
            ws.onerror = (error) => console.error('WebSocket error:', error);
        }
        async function handleWebSocketMessage(event) { 
            let message; try { message = JSON.parse(event.data); } catch (error) { console.error("WS JSON parse error:", error, event.data); return; }
            switch (message.type) {
                case 'room-state': updateParticipantData(message.participants); for (const uid in message.participants) { if (uid !== localUserId) await initializePeerConnection(uid, message.participants[uid].username, true); } break;
                case 'user-joined': addParticipantToLocalState(message.userId, message.username); break;
                case 'user-left': removeParticipantFromLocalState(message.userId); break;
                case 'offer': if (message.userId !== localUserId) { await initializePeerConnection(message.userId, message.fromUsername, false); const pc = peerConnections[message.userId]?.pc; if (pc) { try { await pc.setRemoteDescription(new RTCSessionDescription(message.sdp)); const answer = await pc.createAnswer(); await pc.setLocalDescription(answer); sendSignalingMessage(message.userId, { type: 'answer', sdp: pc.localDescription }); } catch (e) { console.error("Offer handling error:", e); }}} break;
                case 'answer': if (message.userId !== localUserId && peerConnections[message.userId]?.pc) { try { await peerConnections[message.userId].pc.setRemoteDescription(new RTCSessionDescription(message.sdp)); } catch (e) { console.error("Answer handling error:", e); }} break;
                case 'candidate': if (message.userId !== localUserId && peerConnections[message.userId]?.pc) { const pc = peerConnections[message.userId].pc; if (message.candidate && pc.remoteDescription) { try { await pc.addIceCandidate(new RTCIceCandidate(message.candidate)); } catch (e) { console.warn('Add ICE candidate error:', e.message); }}} break;
                case 'media-state-update': if (message.userId !== localUserId) updateRemoteParticipantMediaState(message.userId, message.mediaState); break;
                case 'reaction': if (message.userId !== localUserId) displayReactionOnParticipant(message.userId, message.emoji); break;
                case 'caption-segment': if (message.userId !== localUserId && mediaStates.liveCaptions && UI.captionsText && UI.liveCaptionsArea) { const sender = peerConnections[message.userId]?.username || 'Remote'; const curr = UI.captionsText.textContent; UI.captionsText.textContent = curr ? `${curr}\\n${sender}: ${message.text}` : `${sender}: ${message.text}`; UI.liveCaptionsArea.scrollTop = UI.liveCaptionsArea.scrollHeight; } break;
                case 'conceptual_ai_insights_response': 
                    if (message.userId === localUserId) { 
                         displayConceptualAIInsights(message.data);
                    }
                    break;
                case 'system_notification': 
                    if (message.text) {
                        console.log("System Notification:", message.text);
                        appendChatMessage("System", message.text, false, new Date().toISOString(), true);
                    }
                    break;
            }
        }
        function sendSignalingMessage(targetUserId, data) { if (ws && ws.readyState === WebSocket.OPEN) { ws.send(JSON.stringify({ target: targetUserId, ...data })); } else { console.warn("WS not open for signaling:", data); }}
        function broadcastToRoom(data) { if (ws && ws.readyState === WebSocket.OPEN) { ws.send(JSON.stringify({ target: 'all', ...data })); } else { console.warn("WS not open for broadcast:", data); }}
        async function initializePeerConnection(remoteUserId, remoteUsername, isInitiator) { 
            const streamToSend = (mediaStates.isScreenSharing && screenStream) ? screenStream : localStream;
            if (peerConnections[remoteUserId]?.pc && (peerConnections[remoteUserId].pc.connectionState === 'connected' || peerConnections[remoteUserId].pc.connectionState === 'connecting')) return;
            const pc = new RTCPeerConnection(STUN_SERVERS);
            peerConnections[remoteUserId] = { pc, username: remoteUsername, dataChannel: null, isMicEnabled: true, isVideoEnabled: true, isHandRaised: false, isScreenSharing: false };
            pc.onicecandidate = e => { if (e.candidate) sendSignalingMessage(remoteUserId, { type: 'candidate', candidate: e.candidate }); };
            pc.ontrack = e => addRemoteStreamToUI(remoteUserId, remoteUsername, e.streams[0]);
            pc.ondatachannel = e => { peerConnections[remoteUserId].dataChannel = e.channel; setupDataChannelEvents(e.channel, remoteUserId, remoteUsername); };
            if (streamToSend) { streamToSend.getTracks().forEach(track => { try { pc.addTrack(track, streamToSend); } catch (err) { console.error("AddTrack error:", err, track.kind); }}); }
            if (isInitiator) { const dc = pc.createDataChannel('mainDataChannel', {reliable: true}); peerConnections[remoteUserId].dataChannel = dc; setupDataChannelEvents(dc, remoteUserId, remoteUsername); try { const offer = await pc.createOffer(); await pc.setLocalDescription(offer); sendSignalingMessage(remoteUserId, { type: 'offer', sdp: pc.localDescription, fromUsername: localUsername }); } catch (e) { console.error(`Create offer error for ${remoteUsername}:`, e); }}
        }
        function setupDataChannelEvents(dc, remoteUserId, remoteUsername) { dc.onopen = () => console.log(`DC open with ${remoteUsername}`); dc.onclose = () => console.log(`DC close with ${remoteUsername}`); dc.onmessage = e => handleDataChannelMessage(remoteUserId, remoteUsername, e.data); dc.onerror = (e) => console.error(`DC error with ${remoteUsername}:`, e);}
        function handleDataChannelMessage(remoteUserId, remoteUsername, data) { try { const message = JSON.parse(data); if (message.type === 'chat') { appendChatMessage(message.username || remoteUsername, message.text, false, message.timestamp); }} catch (error) { console.error("DC parse error:", error); }}
        function broadcastOnDataChannels(message) { const stringMsg = JSON.stringify(message); Object.values(peerConnections).forEach(conn => { if (conn.dataChannel && conn.dataChannel.readyState === 'open') { try { conn.dataChannel.send(stringMsg); } catch (e) { console.error(`DC send error to ${conn.username}:`, e); }}});}
        function closePeerConnection(remoteUserId) { const conn = peerConnections[remoteUserId]; if (conn) { if (conn.pc) { conn.pc.close(); } delete peerConnections[remoteUserId]; } document.getElementById(`video-wrapper-${remoteUserId}`)?.remove();}
        function toggleMic() { console.log("toggleMic called"); if (!localStream && !processedLocalAudioStream) { console.warn("Mic toggle: No audio stream."); } mediaStates.isMicEnabled = !mediaStates.isMicEnabled; (processedLocalAudioStream || localStream)?.getAudioTracks().forEach(track => track.enabled = mediaStates.isMicEnabled); updateLocalUIMediaStates(); broadcastMediaStateUpdate(); updateParticipantListItem(localUserId, getLocalMediaStates());}
        function toggleVideo() { console.log("toggleVideo called"); if(!localStream) console.warn("Video toggle: No localStream."); mediaStates.isVideoEnabled = !mediaStates.isVideoEnabled; localStream?.getVideoTracks().forEach(track => track.enabled = mediaStates.isVideoEnabled); updateLocalUIMediaStates(); broadcastMediaStateUpdate(); updateLocalVideoTileAppearance(); updateParticipantListItem(localUserId, getLocalMediaStates());}

        function updateLocalVideoTileAppearance() {
            if (!UI.localVideo || !UI.localAvatar || !UI.localVideoCanvas || !UI.localVideoWrapper || !UI.localVideoOffStatus) {
                console.warn("updateLocalVideoTileAppearance: UI elements missing."); return;
            }

            const isVideoTrackActive = localStream?.getVideoTracks().find(t => t.enabled && t.readyState === 'live');

            // Determine if canvas should be shown (VB active and video track is good)
            const showCanvas = mediaStates.virtualBackgroundEnabled && isVideoTrackActive;
            // Determine if raw video should be shown (VB NOT active and video track is good)
            const showRawVideo = !mediaStates.virtualBackgroundEnabled && isVideoTrackActive;

            UI.localVideo.style.display = showRawVideo ? 'block' : 'none';
            UI.localVideoCanvas.style.display = showCanvas ? 'block' : 'none';

            const isEffectivelyVideoOn = showRawVideo || showCanvas;

            UI.localVideoWrapper.classList.toggle('no-video', !isEffectivelyVideoOn);
            UI.localAvatar.style.display = isEffectivelyVideoOn ? 'none' : 'flex';

            if (!isEffectivelyVideoOn && UI.localAvatar) {
                UI.localAvatar.textContent = localUsername ? localUsername.charAt(0).toUpperCase() : 'U';
            }

            UI.localVideoWrapper.classList.toggle('screen-sharing-active', mediaStates.isScreenSharing);
            UI.localVideoOffStatus.classList.toggle('hidden', mediaStates.isVideoEnabled && isVideoTrackActive); // Video off icon if main toggle is off OR no active track
        }

        function updateLocalUIMediaStates() { if(!Buttons.toggleMic || !Buttons.toggleVideo || !Buttons.raiseHand || !Buttons.shareScreen || !Buttons.record || !UI.localMicStatus || !UI.localHandRaised) { console.warn("updateLocalUIMediaStates: UI elements missing."); return;} Buttons.toggleMic.innerHTML = mediaStates.isMicEnabled ? '<i class="fas fa-microphone"></i>' : '<i class="fas fa-microphone-slash" style="color:var(--danger-color);"></i>'; Buttons.toggleMic.classList.toggle('active', mediaStates.isMicEnabled); UI.localMicStatus.classList.toggle('hidden', mediaStates.isMicEnabled); Buttons.toggleVideo.innerHTML = mediaStates.isVideoEnabled ? '<i class="fas fa-video"></i>' : '<i class="fas fa-video-slash" style="color:var(--danger-color);"></i>'; Buttons.toggleVideo.classList.toggle('active', mediaStates.isVideoEnabled); Buttons.raiseHand.classList.toggle('active', mediaStates.isHandRaised); UI.localHandRaised.classList.toggle('hidden', !mediaStates.isHandRaised); Buttons.shareScreen.classList.toggle('active', mediaStates.isScreenSharing); Buttons.record.classList.toggle('active', mediaStates.isRecording); Buttons.record.innerHTML = mediaStates.isRecording ? '<i class="fas fa-stop-circle" style="color:var(--danger-color);"></i>' : '<i class="fas fa-record-vinyl"></i>'; }
        async function toggleScreenShare() { console.log("toggleScreenShare called"); if (mediaStates.isScreenSharing) await stopScreenShare(); else await startScreenShare(); }
        async function startScreenShare() { console.log("startScreenShare called"); if (!navigator.mediaDevices?.getDisplayMedia) { alert("Screen sharing not supported by your browser."); return; } try { screenStream = await navigator.mediaDevices.getDisplayMedia({ video: { frameRate: {ideal: 15, max:30} }, audio: true }); mediaStates.isScreenSharing = true; if (isVBProcessing) await stopVirtualBackgroundEffect(); const screenVideoTrack = screenStream.getVideoTracks()[0]; const screenAudioTrack = screenStream.getAudioTracks()[0]; for (const id in peerConnections) { const pc = peerConnections[id]?.pc; if (!pc) continue; const videoSender = pc.getSenders().find(s => s.track?.kind === 'video'); if (videoSender) await videoSender.replaceTrack(screenVideoTrack); else pc.addTrack(screenVideoTrack, screenStream); const audioSender = pc.getSenders().find(s => s.track?.kind === 'audio'); if (screenAudioTrack) { if (audioSender) await audioSender.replaceTrack(screenAudioTrack); else pc.addTrack(screenAudioTrack, screenStream); (processedLocalAudioStream || localStream)?.getAudioTracks().forEach(t => t.enabled = false); } else if (audioSender && (processedLocalAudioStream || localStream)?.getAudioTracks().length > 0) { await audioSender.replaceTrack((processedLocalAudioStream || localStream).getAudioTracks()[0]); (processedLocalAudioStream || localStream)?.getAudioTracks().forEach(t => t.enabled = mediaStates.isMicEnabled); }} updateLocalVideoTileAppearance(); Buttons.shareScreen.classList.add('active'); screenVideoTrack.onended = async () => { if(mediaStates.isScreenSharing) await stopScreenShare(); }; broadcastMediaStateUpdate(); } catch (err) { console.error("Screen share start error:", err); mediaStates.isScreenSharing = false; if(screenStream) screenStream.getTracks().forEach(t=>t.stop()); screenStream = null; Buttons.shareScreen.classList.remove('active'); if (localStream) { for (const id in peerConnections) { const pc = peerConnections[id]?.pc; if (!pc) continue; const videoSender = pc.getSenders().find(s => s.track?.kind === 'video'); const audioSender = pc.getSenders().find(s => s.track?.kind === 'audio'); if (videoSender && localStream.getVideoTracks()[0]) await videoSender.replaceTrack(localStream.getVideoTracks()[0]); if (audioSender && (processedLocalAudioStream || localStream).getAudioTracks()[0]) await audioSender.replaceTrack((processedLocalAudioStream || localStream).getAudioTracks()[0]); }} if (mediaStates.virtualBackgroundEnabled) await startVirtualBackgroundEffect();}}
        async function stopScreenShare() { console.log("stopScreenShare called"); if (!screenStream && !mediaStates.isScreenSharing) return; mediaStates.isScreenSharing = false; if (screenStream) { screenStream.getTracks().forEach(t => t.stop()); screenStream = null; } const camVideo = localStream?.getVideoTracks()[0]; const micAudio = (processedLocalAudioStream || localStream)?.getAudioTracks()[0]; for (const id in peerConnections) { const pc = peerConnections[id]?.pc; if (!pc) continue; const videoSender = pc.getSenders().find(s => s.track?.kind === 'video'); if (videoSender) { if (camVideo) await videoSender.replaceTrack(camVideo); else if (videoSender.track) pc.removeTrack(videoSender); } else if (camVideo && localStream) pc.addTrack(camVideo, localStream); const audioSender = pc.getSenders().find(s => s.track?.kind === 'audio'); if (audioSender) { if (micAudio) await audioSender.replaceTrack(micAudio); else if(audioSender.track) pc.removeTrack(audioSender); } else if (micAudio && (processedLocalAudioStream || localStream)) pc.addTrack(micAudio, (processedLocalAudioStream || localStream)); (processedLocalAudioStream || localStream)?.getAudioTracks().forEach(t => t.enabled = mediaStates.isMicEnabled); } if (mediaStates.virtualBackgroundEnabled) await startVirtualBackgroundEffect(); else updateLocalVideoTileAppearance(); Buttons.shareScreen.classList.remove('active'); broadcastMediaStateUpdate(); }
        function toggleHandRaise() { console.log("toggleHandRaise called"); mediaStates.isHandRaised = !mediaStates.isHandRaised; updateLocalUIMediaStates(); broadcastMediaStateUpdate(); updateParticipantListItem(localUserId, getLocalMediaStates());}
        function getLocalMediaStates() { return { ...mediaStates }; }
        function showReactionsPopup() { console.log("showReactionsPopup called"); if (UI.reactionsPopup) { UI.reactionsPopup.classList.toggle('hidden'); if (!UI.reactionsPopup.classList.contains('hidden')) { const closeHandler = (event) => { if (UI.reactionsPopup && !UI.reactionsPopup.contains(event.target) && event.target !== Buttons.reactions) { UI.reactionsPopup.classList.add('hidden'); document.removeEventListener('click', closeHandler, true); }}; setTimeout(() => document.addEventListener('click', closeHandler, true), 0);}}}
        function sendReaction(emoji) { console.log("sendReaction:", emoji); displayReactionOnParticipant(localUserId, emoji); broadcastToRoom({ type: 'reaction', emoji: emoji }); if (UI.reactionsPopup) UI.reactionsPopup.classList.add('hidden');}
        function displayReactionOnParticipant(userId, emoji) { const targetId = userId === localUserId ? 'local-video-container-wrapper' : `video-wrapper-${userId}`; const container = document.getElementById(targetId); if (container) { const el = document.createElement('span'); el.className = 'reaction-emoji'; el.textContent = emoji; container.appendChild(el); setTimeout(() => el.remove(), 2400);}}
        function toggleRecording() { console.log("toggleRecording called"); mediaStates.isRecording = !mediaStates.isRecording; if (mediaStates.isRecording) startClientSideRecording(); else stopClientSideRecording(); updateLocalUIMediaStates(); }
        function startClientSideRecording() { 
            console.log(`Starting client-side recording. Conceptual scope: ${mediaStates.recordingScope}. Conceptual cloud: ${mediaStates.cloudRecordingEnabled}`);
            const streamToRecord = screenStream || localStream; 
            if (!streamToRecord) { alert("Nothing to record."); mediaStates.isRecording = false; updateLocalUIMediaStates(); return; } 
            recordedChunks = []; 
            try { 
                const options = { mimeType: 'video/webm; codecs=vp9,opus' }; 
                if (!MediaRecorder.isTypeSupported(options.mimeType)) { console.warn("VP9/Opus MIME type not supported, using default."); delete options.mimeType; } 
                mediaRecorder = new MediaRecorder(streamToRecord, options); 
                mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) recordedChunks.push(e.data); }; 
                mediaRecorder.onstop = () => { 
                    const blob = new Blob(recordedChunks, { type: mediaRecorder.mimeType || 'video/webm' }); 
                    const url = URL.createObjectURL(blob); 
                    const a = document.createElement('a'); 
                    a.style.display = 'none';
                    a.href = url; 
                    a.download = `IntelliMeetX-recording-${new Date().toISOString().slice(0,19).replace("T", "_").replace(/:/g, "-")}.webm`; 
                    document.body.appendChild(a);
                    a.click(); 
                    window.URL.revokeObjectURL(url); 
                    a.remove();
                    console.log("Recording saved.");
                    if (mediaStates.cloudRecordingEnabled) {
                        console.log("Conceptual: Uploading recording to cloud...");
                    }
                }; 
                mediaRecorder.start(); 
                console.log("Recording started. MimeType:", mediaRecorder.mimeType); 
            } catch (e) { 
                console.error("MediaRecorder error:", e); 
                alert("Failed to start recording: " + e.message); 
                mediaStates.isRecording = false; 
                updateLocalUIMediaStates();
            }
        }
        function stopClientSideRecording() { console.log("stopClientSideRecording called"); if (mediaRecorder && mediaRecorder.state !== "inactive") { mediaRecorder.stop(); console.log("Recording stopped."); }}
        function broadcastMediaStateUpdate() { broadcastToRoom({ type: 'media-state-update', mediaState: getLocalMediaStates() }); }
        function updateRemoteParticipantMediaState(remoteUserId, rStates) { if (!peerConnections[remoteUserId] && rStates.username) peerConnections[remoteUserId] = { username: rStates.username }; else if(!peerConnections[remoteUserId]) peerConnections[remoteUserId] = {}; Object.assign(peerConnections[remoteUserId], rStates); const wrapper = document.getElementById(`video-wrapper-${remoteUserId}`); if (wrapper) { wrapper.querySelector('.mic-status')?.classList.toggle('hidden', rStates.isMicEnabled); wrapper.querySelector('.hand-raised')?.classList.toggle('hidden', !rStates.isHandRaised); const videoEl = wrapper.querySelector('video'); const avatarEl = wrapper.querySelector('.avatar-placeholder'); const showVideo = (rStates.isVideoEnabled || rStates.isScreenSharing) && videoEl?.srcObject?.active; if(videoEl) videoEl.style.display = showVideo ? 'block' : 'none'; if(avatarEl) { avatarEl.style.display = showVideo ? 'none' : 'flex'; if(!showVideo) avatarEl.textContent = peerConnections[remoteUserId]?.username?.charAt(0).toUpperCase() || '?';} wrapper.classList.toggle('no-video', !showVideo); wrapper.classList.toggle('remote-screen-share', rStates.isScreenSharing); } updateParticipantListItem(remoteUserId, rStates); }
        function addParticipantToLocalState(userId, username) { if (!peerConnections[userId]) peerConnections[userId] = { username, isMicEnabled: true, isVideoEnabled: true, isHandRaised: false, isScreenSharing: false, pc: null, dataChannel: null }; else peerConnections[userId].username = username; updateParticipantListUI();}
        function removeParticipantFromLocalState(userId) { closePeerConnection(userId); updateParticipantListUI(); }
        function updateParticipantData(participantsData) { Object.keys(peerConnections).forEach(id => { if (id !== localUserId && !participantsData[id]) removeParticipantFromLocalState(id); }); for (const [id, data] of Object.entries(participantsData)) { if (id !== localUserId) { if (!peerConnections[id]) peerConnections[id] = { username: data.username, ...data, pc:null, dataChannel:null }; else peerConnections[id].username = data.username;}} updateParticipantListUI();}
        function updateParticipantListUI() { if(!UI.participantsList || !UI.participantCount) return; UI.participantsList.innerHTML = ''; let count = 0; const localData = { username: localUsername, ...getLocalMediaStates() }; UI.participantsList.appendChild(createParticipantListItem(localUserId, localData)); count++; Object.entries(peerConnections).forEach(([id, data]) => { if (id === localUserId) return; if (data && data.username) { UI.participantsList.appendChild(createParticipantListItem(id, data)); count++; }}); UI.participantCount.textContent = count;}
        function createParticipantListItem(userId, data) { const li = document.createElement('li'); li.id = `participant-li-${userId}`; const avatar = document.createElement('div'); avatar.className = 'participant-list-avatar'; avatar.textContent = data.username ? data.username.charAt(0).toUpperCase() : '?'; li.appendChild(avatar); const nameSpan = document.createElement('span'); nameSpan.className = 'participant-list-name'; nameSpan.textContent = `${data.username || 'User'}${userId === localUserId ? ' (You)' : ''}`; li.appendChild(nameSpan); const iconsDiv = document.createElement('div'); iconsDiv.className = 'participant-list-icons'; iconsDiv.innerHTML = `<i class="fas ${data.isMicEnabled ? 'fa-microphone' : 'fa-microphone-slash'}" title="${data.isMicEnabled ? 'Mic on' : 'Mic muted'}"></i><i class="fas ${data.isScreenSharing ? 'fa-desktop' : (data.isVideoEnabled ? 'fa-video' : 'fa-video-slash')}" title="${data.isScreenSharing ? 'Screen sharing' : (data.isVideoEnabled ? 'Video on' : 'Video off')}"></i>${data.isHandRaised ? '<i class="fas fa-hand-paper" title="Hand raised"></i>' : ''}`; li.appendChild(iconsDiv); return li;}
        function updateParticipantListItem(userId, pStates) { const dataForListItem = userId === localUserId ? { username: localUsername, ...getLocalMediaStates() } : peerConnections[userId]; if (!dataForListItem) return; const li = document.getElementById(`participant-li-${userId}`); if (li) li.replaceWith(createParticipantListItem(userId, dataForListItem)); else updateParticipantListUI();}
        function addRemoteStreamToUI(userId, username, stream) { if(!UI.videoGrid) return; let wrapper = document.getElementById(`video-wrapper-${userId}`); if (!wrapper) { wrapper = document.createElement('div'); wrapper.id = `video-wrapper-${userId}`; wrapper.className = 'video-participant'; wrapper.innerHTML = `<div class="avatar-placeholder">${username.charAt(0).toUpperCase()}</div><video autoplay playsinline></video><canvas class="hidden"></canvas><div class="spinner hidden"></div><div class="participant-overlay"><span class="participant-name">${username}</span><div class="participant-status-icons"><span class="status-icon mic-status hidden" title="Mic Muted"><i class="fas fa-microphone-slash"></i></span><span class="status-icon video-off hidden" title="Video Off"><i class="fas fa-video-slash"></i></span><span class="status-icon hand-raised hidden" title="Hand Raised"><i class="fas fa-hand-paper"></i></span></div></div>`; UI.videoGrid.appendChild(wrapper); } const videoEl = wrapper.querySelector('video'); if (videoEl && videoEl.srcObject !== stream) { videoEl.srcObject = stream; videoEl.play().catch(e=>console.warn(`Remote video play fail for ${username}:`, e));} if (peerConnections[userId]) updateRemoteParticipantMediaState(userId, peerConnections[userId]); else updateRemoteParticipantMediaState(userId, { isMicEnabled: true, isVideoEnabled: true, isHandRaised: false, isScreenSharing: false }); applyVideoLayout(currentLayout); }
        let currentLayout = 'grid'; function applyVideoLayout(layoutType) { console.log("applyVideoLayout:", layoutType); if(!UI.videoGrid) return; currentLayout = layoutType; UI.videoGrid.className = 'video-grid-container'; UI.videoGrid.classList.add(`${layoutType}-layout`); document.querySelectorAll('.video-layout-controls button').forEach(btn => btn.classList.remove('active')); document.getElementById(`layout-${layoutType}-button`)?.classList.add('active'); }
        function sendChatMessage() { console.log("sendChatMessage called"); if (!Inputs.chat) return; const text = Inputs.chat.value.trim(); if (text) { const timestamp = new Date().toISOString(); appendChatMessage(localUsername, text, true, timestamp); broadcastOnDataChannels({ type: 'chat', username: localUsername, text, timestamp }); Inputs.chat.value = ''; Inputs.chat.style.height = 'auto'; }}
        function appendChatMessage(username, text, isSelf, timestamp, isSystem = false) { 
            if(!UI.chatMessages) return; 
            const msgDiv = document.createElement('div'); 
            msgDiv.classList.add('chat-message', isSelf ? 'self' : 'other'); 
            if (isSystem) msgDiv.style.fontStyle = "italic"; 
            msgDiv.innerHTML = `<span class="sender">${isSelf ? "You" : username}</span><p class="message-text">${text.replace(/\\n/g, '<br>')}</p><span class="timestamp">${new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>`; 
            UI.chatMessages.appendChild(msgDiv); 
            UI.chatMessages.scrollTop = UI.chatMessages.scrollHeight; 
        }
        async function handleHangup() { console.log("handleHangup called"); await cleanupSession(true); toggleModal(Modals.entry, true); if(UI.appContainer) UI.appContainer.classList.add('hidden'); if(UI.videoGrid) { UI.videoGrid.innerHTML = ''; const localTile = createLocalVideoTile(); UI.videoGrid.appendChild(localTile); } if(UI.participantsList) UI.participantsList.innerHTML = ''; if(UI.chatMessages) UI.chatMessages.innerHTML = ''; if(UI.roomIdDisplay) UI.roomIdDisplay.textContent = ''; if(UI.participantCount) UI.participantCount.textContent = '0'; 
            // Reset mediaStates to defaults, respecting original checkbox defaults
            const defaultMediaStates = { isMicEnabled: true, isVideoEnabled: true, isScreenSharing: false, isHandRaised: false, isRecording: false, aiNoiseCancellation: false, echoCancellation: true, virtualBackgroundEnabled: false, virtualBackgroundType: 'none', virtualBackgroundImageSrc: null, videoEnhancement: false, autoFraming: false, liveCaptions: false, aiMeetingSummary: false, aiActionItemDetection: false, aiRealtimeTranslation: false, recordingScope: 'full', cloudRecordingEnabled: false};
            Object.keys(mediaStates).forEach(key => {
                mediaStates[key] = defaultMediaStates[key];
                 // Update toggles based on default values
                const toggleKey = Object.keys(Toggles).find(tKey => Toggles[tKey]?.dataset.stateKey === key);
                if (toggleKey && Toggles[toggleKey]) {
                    Toggles[toggleKey].checked = defaultMediaStates[key];
                }
            });
            if (VBElements.choicesContainer) VBElements.choicesContainer.classList.add('hidden');
            updateVBOptionsUI(); // Ensure VB UI reflects 'none'
            updateLocalUIMediaStates(); 
            await savePreferences();
        }
        function createLocalVideoTile() { console.log("createLocalVideoTile called"); const wrapper = document.createElement('div'); wrapper.className = 'video-participant local-participant'; wrapper.id = 'local-video-container-wrapper'; wrapper.innerHTML = `<div class="avatar-placeholder"></div><video id="local-video" autoplay muted playsinline style="display: block;"></video><canvas id="local-video-canvas" style="display: none;"></canvas><div class="spinner hidden" id="local-video-spinner"></div><div class="participant-overlay"><span class="participant-name" id="local-participant-name-display">You</span><div class="participant-status-icons"><span class="status-icon mic-status hidden" id="local-mic-status-icon" title="Mic Muted"><i class="fas fa-microphone-slash"></i></span><span class="status-icon video-off hidden" id="local-video-off-icon" title="Video Off"><i class="fas fa-video-slash"></i></span><span class="status-icon hand-raised hidden" id="local-hand-raised-icon" title="Hand Raised"><i class="fas fa-hand-paper"></i></span></div></div>`; initializeDOMElements(); return wrapper;}
        async function handleBeforeUnload() { console.log("handleBeforeUnload called"); if (ws && ws.readyState === WebSocket.OPEN) { ws.send(JSON.stringify({ type: 'leaving', userId: localUserId, roomId: currentRoomId })); } await cleanupSession(false); }
        async function cleanupSession(isIntentional = false) { console.log("Cleaning up session, intentional:", isIntentional); [localStream, screenStream, processedLocalAudioStream].forEach(s => s?.getTracks().forEach(t => t.stop())); localStream = screenStream = processedLocalAudioStream = null; Object.keys(peerConnections).forEach(id => closePeerConnection(id)); peerConnections = {}; if (speechRecognition) { speechRecognition.onend = null; speechRecognition.stop(); speechRecognition = null; } if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop(); mediaRecorder = null; recordedChunks = []; if (ws) { if (ws.readyState === WebSocket.OPEN && isIntentional) { ws.send(JSON.stringify({ type: 'hangup', userId: localUserId, roomId: currentRoomId })); } ws.onopen = ws.onmessage = ws.onclose = ws.onerror = null; if(ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) ws.close(1000, "Client session cleanup"); ws = null; } if (audioContext && audioContext.state !== 'closed') { try { await audioContext.close(); } catch(e) { console.warn("AudioContext close error:", e); } audioContext = null; } if (isVBProcessing) await stopVirtualBackgroundEffect(); }
        function generateUUID() { var d = new Date().getTime(), d2 = (performance?.now?.()*1000) || 0; return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => { var r = Math.random() * 16; r = (c === 'x' ? (d > 0 ? (d + r)%16 | 0 : (d2 + r)%16 | 0) : (r & 0x3 | 0x8)); if(d > 0) d = Math.floor(d/16); else d2 = Math.floor(d2/16); return r.toString(16); });}
        function handleFullscreenChange() { console.log("Fullscreen state changed:", document.fullscreenElement); }

        async function populateDeviceSelectors() {
            if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
                console.warn("enumerateDevices() not supported."); return;
            }
            try {
                const devices = await navigator.mediaDevices.enumerateDevices();
                if (!Inputs.audioDevice || !Inputs.videoDevice) {
                     console.warn("Audio/Video select elements not found for populating."); return;
                }
                const currentAudioVal = Inputs.audioDevice.value;
                const currentVideoVal = Inputs.videoDevice.value;

                Inputs.audioDevice.innerHTML = ''; Inputs.videoDevice.innerHTML = '';

                let audioDeviceCount = 0;
                let videoDeviceCount = 0;

                devices.forEach(device => {
                    const option = document.createElement('option');
                    option.value = device.deviceId;
                    if (device.kind === 'audioinput') {
                        audioDeviceCount++;
                        option.text = device.label || `Microphone ${audioDeviceCount}`;
                        Inputs.audioDevice.appendChild(option);
                    } else if (device.kind === 'videoinput') {
                        videoDeviceCount++;
                        option.text = device.label || `Camera ${videoDeviceCount}`;
                        Inputs.videoDevice.appendChild(option);
                    }
                });

                // Try to reselect previously selected or preferred, otherwise first.
                const preferredAudio = localStorage.getItem('preferredAudioInput') || currentAudioVal;
                if (preferredAudio && Inputs.audioDevice.querySelector(`option[value="${preferredAudio}"]`)) {
                    Inputs.audioDevice.value = preferredAudio;
                } else if (Inputs.audioDevice.options.length > 0) {
                     Inputs.audioDevice.value = Inputs.audioDevice.options[0].value;
                }


                const preferredVideo = localStorage.getItem('preferredVideoInput') || currentVideoVal;
                 if (preferredVideo && Inputs.videoDevice.querySelector(`option[value="${preferredVideo}"]`)) {
                    Inputs.videoDevice.value = preferredVideo;
                } else if (Inputs.videoDevice.options.length > 0) {
                     Inputs.videoDevice.value = Inputs.videoDevice.options[0].value;
                }


            } catch (err) { console.error("Error populating device selectors:", err); }
        }

        function toggleSidebar() {
            if (!UI.sidebar) return;
            const isMobile = window.innerWidth <= 480;
            if (isMobile) {
                UI.sidebar.classList.toggle('open'); 
            } else {
                UI.sidebar.classList.toggle('collapsed'); 
            }
            updateSidebarToggleButton();
        }

        function updateSidebarToggleButton() {
            if (!Buttons.sidebarToggle || !UI.sidebar) return;
            const isMobile = window.innerWidth <= 480;
            const isOpenOrNotCollapsed = isMobile ? UI.sidebar.classList.contains('open') : !UI.sidebar.classList.contains('collapsed');

            if (isOpenOrNotCollapsed) {
                Buttons.sidebarToggle.innerHTML = '<i class="fas fa-times"></i>'; 
                Buttons.sidebarToggle.title = "Close Panel";
            } else {
                const activeTabButton = UI.sidebar.querySelector('.sidebar-tab-button.active');
                const iconClass = activeTabButton ? activeTabButton.querySelector('i').className : 'fas fa-users';
                Buttons.sidebarToggle.innerHTML = `<i class="${iconClass}"></i>`;
                Buttons.sidebarToggle.title = "Open Panel";
            }
        }

        function switchSidebarTab(tabId) {
            document.querySelectorAll('.sidebar-tab-content').forEach(content => content.classList.remove('active'));
            document.querySelectorAll('.sidebar-tab-button').forEach(button => button.classList.remove('active'));

            const newActiveTabContent = document.getElementById(`${tabId}-content`);
            const newActiveTabButton = document.querySelector(`.sidebar-tab-button[data-tab="${tabId}"]`);

            if(newActiveTabContent) newActiveTabContent.classList.add('active');
            if(newActiveTabButton) newActiveTabButton.classList.add('active');
            updateSidebarToggleButton(); 
        }
        function toggleAIInsightsPanel() {
            if (UI.aiInsightsPanel) {
                UI.aiInsightsPanel.classList.toggle('hidden');
                if (!UI.aiInsightsPanel.classList.contains('hidden')) {
                    console.log("Displaying conceptual AI Insights. Requesting from server...");
                    broadcastToRoom({ type: 'request_ai_insights', forUserId: localUserId });
                }
            }
        }

        function displayConceptualAIInsights(data) {
            if (UI.aiInsightsPanel && !UI.aiInsightsPanel.classList.contains('hidden')) {
                const summaryElSpan = UI.aiInsightsPanel.querySelector('p strong + span');
                const actionListEl = UI.aiInsightsPanel.querySelector('ul');

                if(summaryElSpan) summaryElSpan.textContent = data.summary || "Conceptual summary from server...";

                if(actionListEl) {
                    actionListEl.innerHTML = ''; 
                    (data.actionItems || ["Conceptual action item 1.", "Conceptual action item 2."]).forEach(item => {
                        const li = document.createElement('li');
                        li.textContent = item;
                        actionListEl.appendChild(li);
                    });
                }
                console.log("Conceptual AI Insights updated with data:", data);
            }
        }

        document.addEventListener('DOMContentLoaded', initializeApp);

    </script>
</body>
</html>
"""


# FastAPI Backend (largely unchanged, only minor logging/comments if needed for clarity)
class ConnectionManager:
    async def connect(self, websocket: WebSocket, room_id: str, user_id: str, username: str):
        await websocket.accept()
        if room_id not in rooms:
            rooms[room_id] = {"participants": {}, "host_id": user_id}
            logger.info(f"Room '{room_id}' created by host {username}({user_id}).")

        current_participants_info = {
            uid: {"username": data["username"]}
            for uid, data in rooms[room_id]["participants"].items()
        }
        await websocket.send_json(
            {"type": "room-state", "participants": current_participants_info, "hostId": rooms[room_id]["host_id"]})

        rooms[room_id]["participants"][user_id] = {"ws": websocket, "username": username}
        logger.info(
            f"User {username}({user_id}) connected to room '{room_id}'. Total: {len(rooms[room_id]['participants'])}")

        await self.broadcast(room_id,
                             {"type": "user-joined", "userId": user_id, "username": username},
                             exclude_user_id=user_id)

    def get_user_id_by_websocket(self, room_id: str, websocket: WebSocket):
        if room_id in rooms:
            for uid, data in rooms[room_id]["participants"].items():
                if data["ws"] == websocket: return uid
        return None

    async def disconnect(self, room_id: str, user_id: str, websocket: WebSocket):
        room_closed = False
        actual_user_id = user_id

        if not actual_user_id and room_id in rooms:  # Get user_id if not passed (e.g. unexpected disconnect)
            actual_user_id = self.get_user_id_by_websocket(room_id, websocket)

        if room_id in rooms and actual_user_id and actual_user_id in rooms[room_id]["participants"]:
            username = rooms[room_id]["participants"][actual_user_id]["username"]
            del rooms[room_id]["participants"][actual_user_id]
            logger.info(f"User {username}({actual_user_id}) disconnected from room '{room_id}'.")

            if not rooms[room_id]["participants"]:
                del rooms[room_id];
                logger.info(f"Room '{room_id}' is empty and closed.");
                room_closed = True
            elif actual_user_id == rooms[room_id].get("host_id") and rooms[room_id]["participants"]:  # Host left
                new_host_id = list(rooms[room_id]["participants"].keys())[0]
                rooms[room_id]["host_id"] = new_host_id
                new_host_username = rooms[room_id]['participants'][new_host_id]['username']
                logger.info(f"Host left room '{room_id}'. New host: {new_host_username}({new_host_id}).")
                await self.broadcast(room_id,
                                     {"type": "new-host", "hostId": new_host_id, "hostUsername": new_host_username})

            if not room_closed:  # If room still active, notify others
                await self.broadcast(room_id, {"type": "user-left", "userId": actual_user_id, "username": username})
        elif room_id in rooms and actual_user_id:
            logger.warning(f"User {actual_user_id} not found in room '{room_id}' during disconnect, but room exists.")
        elif actual_user_id:  # User ID provided, but room not found
            logger.warning(f"Room '{room_id}' not found for disconnecting user {actual_user_id}.")
        else:  # No user ID and room not found (or user ID couldn't be derived from websocket)
            logger.warning(
                f"Could not identify user or room for disconnect. Room: '{room_id}', User (if known): '{actual_user_id}'.")

        return room_closed

    async def broadcast(self, room_id: str, message: dict, exclude_user_id: str = None):
        if room_id in rooms:
            active_connections = []
            # Create a list of connections to iterate over, to avoid issues if a disconnect happens mid-broadcast
            for uid, data in list(rooms[room_id]["participants"].items()):
                if uid != exclude_user_id:
                    active_connections.append((uid, data["ws"]))

            disconnected_during_broadcast = []

            for uid, conn_ws in active_connections:
                try:
                    if conn_ws.client_state == WebSocketState.CONNECTED:
                        await conn_ws.send_json(message)
                    else:
                        logger.warning(
                            f"WS for {uid} in room '{room_id}' not connected (state: {conn_ws.client_state}). Will attempt cleanup.")
                        disconnected_during_broadcast.append(uid)
                except Exception as e:  # Includes RuntimeError if connection closes during send
                    logger.error(f"Broadcast error to {uid} in room '{room_id}': {e}")
                    disconnected_during_broadcast.append(uid)

            # Clean up users that disconnected during broadcast, if any
            # for uid_to_clean in set(disconnected_during_broadcast): # Use set to avoid duplicate cleanup calls
            #    if uid_to_clean in rooms[room_id]["participants"]: # Check if not already cleaned by another process
            #        logger.info(f"Cleaning up user {uid_to_clean} from room '{room_id}' due to broadcast failure/disconnect.")
            #        await self.disconnect(room_id, uid_to_clean, rooms[room_id]["participants"][uid_to_clean]["ws"])


manager = ConnectionManager()


@app.get("/", response_class=HTMLResponse)
async def get_index_route(request: Request):
    return HTMLResponse(content=HTML_TEMPLATE)


@app.websocket("/ws/{room_id}/{user_id}/{username_encoded}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str, username_encoded: str):
    username = ""
    try:
        username = url_unquote(username_encoded)
    except Exception as e:
        logger.error(f"Username decode fail for '{username_encoded}', error: {e}")
        await websocket.close(code=1008, reason="Invalid username encoding");
        return

    if not username.strip():
        logger.error(f"Empty username provided for user_id {user_id} in room {room_id}.")
        await websocket.close(code=1008, reason="Username cannot be empty");
        return

    await manager.connect(websocket, room_id, user_id, username)
    active_ws_user_id = user_id
    active_ws_room_id = room_id
    active_ws_username = username

    try:
        while True:
            data = await websocket.receive_text()
            message = {}
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                logger.warning(
                    f"Malformed JSON from {active_ws_username}({active_ws_user_id}) in room '{active_ws_room_id}': {data[:200]}...")
                continue

            # --- Conceptual Feature Handling ---
            if message.get("type") == "request_ai_insights":
                logger.info(
                    f"User {active_ws_username} requested conceptual AI insights for room '{active_ws_room_id}'.")
                await asyncio.sleep(0.2)  # Simulate work
                if active_ws_room_id in rooms and active_ws_user_id in rooms[active_ws_room_id]["participants"]:
                    target_ws = rooms[active_ws_room_id]["participants"][active_ws_user_id]["ws"]
                    if target_ws.client_state == WebSocketState.CONNECTED:
                        await target_ws.send_json({
                            "type": "conceptual_ai_insights_response",
                            "userId": active_ws_user_id,
                            "data": {
                                "summary": f"This is a conceptual AI summary for room {active_ws_room_id}, requested by {active_ws_username} at {uuid.uuid4().hex[:6]}.",
                                "actionItems": [
                                    f"Conceptual Action 1 for {active_ws_username}",
                                    "Conceptual Action 2 (general)"
                                ],
                                "sentiment": "Positive (Conceptual)"
                            }
                        })
                continue

            elif message.get("type") == "tool_interaction":
                tool_id = message.get("toolId", "Unknown Tool")
                tool_name = message.get("toolName", tool_id)
                logger.info(f"User {active_ws_username} interacted with conceptual tool: {tool_name} (ID: {tool_id})")
                await manager.broadcast(active_ws_room_id, {
                    "type": "system_notification",
                    "text": f"{active_ws_username} is using the '{tool_name}' tool (conceptually)."
                }, exclude_user_id=active_ws_user_id)
                if active_ws_room_id in rooms and active_ws_user_id in rooms[active_ws_room_id]["participants"]:
                    target_ws = rooms[active_ws_room_id]["participants"][active_ws_user_id]["ws"]
                    if target_ws.client_state == WebSocketState.CONNECTED:
                        await target_ws.send_json({
                            "type": "system_notification",
                            "text": f"Your interaction with '{tool_name}' has been noted (conceptual feature)."
                        })
                continue
                # --- End Conceptual Feature Handling ---

            target_user_id = message.get("target")
            msg_to_send = {**message, "userId": active_ws_user_id, "fromUsername": active_ws_username}
            if 'target' in msg_to_send:
                del msg_to_send['target']

            if target_user_id == "all":
                await manager.broadcast(active_ws_room_id, msg_to_send, exclude_user_id=active_ws_user_id)
            elif target_user_id:
                if active_ws_room_id in rooms and target_user_id in rooms[active_ws_room_id]["participants"]:
                    target_ws = rooms[active_ws_room_id]["participants"][target_user_id]["ws"]
                    if target_ws.client_state == WebSocketState.CONNECTED:
                        await target_ws.send_json(msg_to_send)
                    else:
                        logger.warning(
                            f"Target WS for {target_user_id} in room '{active_ws_room_id}' not connected. State: {target_ws.client_state}")
                else:
                    logger.warning(
                        f"Target user '{target_user_id}' or room '{active_ws_room_id}' not found for message from {active_ws_username}. Message: {message}")

    except WebSocketDisconnect as e:
        logger.info(
            f"WebSocketDisconnect for {active_ws_username}({active_ws_user_id}) in room '{active_ws_room_id}'. Code: {e.code}, Reason: {e.reason}")
    except Exception as e:
        logger.error(
            f"Unexpected WS Error for {active_ws_username}({active_ws_user_id}) in room '{active_ws_room_id}': {e}",
            exc_info=True)  # exc_info=True will log the full traceback
    finally:
        # Ensure disconnect is called with current values, not potentially stale ones if an error occurred before full init
        current_room_id_at_disconnect = active_ws_room_id
        current_user_id_at_disconnect = active_ws_user_id
        current_username_at_disconnect = active_ws_username

        await manager.disconnect(current_room_id_at_disconnect, current_user_id_at_disconnect, websocket)
        logger.info(
            f"WS connection finalized and cleaned up for {current_username_at_disconnect}({current_user_id_at_disconnect}).")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
