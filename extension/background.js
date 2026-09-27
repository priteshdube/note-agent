// Background service worker for Lecture Notes Assistant

// Backend URL - in production, this would be your deployed backend
const BACKEND_URL = 'http://localhost:8000/api';

// Helper function to send status updates to popup
function sendStatusUpdate(message, type = 'info') {
    chrome.runtime.sendMessage({
        action: 'updateStatus',
        message: message,
        type: type
    });
}

// Process audio data by sending to backend
async function processAudio(audioData, topicName) {
    try {
        sendStatusUpdate('Sending audio to backend...', 'info');

        // Convert audio data to blob
        const audioBlob = new Blob([new Uint8Array(audioData)], { type: 'audio/wav' });

        // Create form data
        const formData = new FormData();
        formData.append('audio_file', audioBlob, 'recording.wav');
        if (topicName) {
            formData.append('topic_name', topicName);
        }

        // Send to backend
        const response = await fetch(`${BACKEND_URL}/process-lecture`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Backend error: ${response.status}`);
        }

        const result = await response.json();
        sendStatusUpdate('Notes generated successfully!', 'success');

        // Notify popup of completion
        chrome.runtime.sendMessage({
            action: 'recordingComplete'
        });

        // Optionally open the Notion page
        if (result.notion_page_url) {
            chrome.tabs.create({ url: result.notion_page_url });
        }

    } catch (err) {
        console.error('Error processing audio:', err);
        sendStatusUpdate('Error: ' + err.message, 'error');

        chrome.runtime.sendMessage({
            action: 'error',
            message: err.message
        });
    }
}

// Process YouTube URL by sending to backend
async function processYouTube(youtubeUrl, topicName) {
    try {
        sendStatusUpdate('Sending YouTube URL to backend...', 'info');

        // Create form data
        const formData = new FormData();
        formData.append('youtube_url', youtubeUrl);
        if (topicName) {
            formData.append('topic_name', topicName);
        }

        // Send to backend
        const response = await fetch(`${BACKEND_URL}/process-youtube`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Backend error: ${response.status}`);
        }

        const result = await response.json();
        sendStatusUpdate('Notes generated successfully!', 'success');

        // Notify popup of completion
        chrome.runtime.sendMessage({
            action: 'youtubeComplete'
        });

        // Optionally open the Notion page
        if (result.notion_page_url) {
            chrome.tabs.create({ url: result.notion_page_url });
        }

    } catch (err) {
        console.error('Error processing YouTube video:', err);
        sendStatusUpdate('Error: ' + err.message, 'error');

        chrome.runtime.sendMessage({
            action: 'error',
            message: err.message
        });
    }
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'processAudio') {
        processAudio(message.audioData, message.topicName);
        return true; // Indicates we'll respond asynchronously
    } else if (message.action === 'processYouTube') {
        processYouTube(message.youtubeUrl, message.topicName);
        return true; // Indicates we'll respond asynchronously
    }
});

// Optional: Handle extension installation/update
chrome.runtime.onInstalled.addListener((details) => {
    if (details.reason === 'install') {
        console.log('Lecture Notes Assistant installed');
    } else if (details.reason === 'update') {
        console.log('Lecture Notes Assistant updated');
    }
});