// Popup controller for Lecture Notes Assistant

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

// DOM Elements
const recordBtn = document.getElementById('recordBtn');
const stopBtn = document.getElementById('stopBtn');
const youtubeUrlInput = document.getElementById('youtubeUrl');
const processYoutubeBtn = document.getElementById('processYoutubeBtn');
const topicNameInput = document.getElementById('topicName');
const statusEl = document.getElementById('status');

// Set status message
function setStatus(message, type = 'info') {
    statusEl.textContent = message;
    statusEl.className = '';
    statusEl.classList.add(type);
    statusEl.classList.remove('hidden');

    // Hide status after 5 seconds for non-error messages
    if (type !== 'error') {
        setTimeout(() => {
            statusEl.classList.add('hidden');
        }, 5000);
    }
}

// Clear status
function clearStatus() {
    statusEl.classList.add('hidden');
}

// Start recording tab audio
async function startRecording() {
    try {
        // Get the current tab
        const [tab] = await chrome.tabs.query({active: true, currentWindow: true});

        // Request access to tab capture
        const stream = await chrome.tabCapture.getMediaStreamId({
            targetTabId: tab.id,
            audio: true,
            video: false
        });

        // Actually get the media stream
        const mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                mandatory: {
                    chromeMediaSource: 'tab',
                    chromeMediaSourceId: stream
                }
            },
            video: false
        });

        // Set up media recorder
        mediaRecorder = new MediaRecorder(mediaStream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = async () => {
            // Combine audio chunks
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const audioArrayBuffer = await audioBlob.arrayBuffer();

            // Send to background for processing
            chrome.runtime.sendMessage({
                action: 'processAudio',
                audioData: Array.from(new Uint8Array(audioArrayBuffer)),
                topicName: topicNameInput.value.trim()
            });

            // Clean up
            mediaStream.getTracks().forEach(track => track.stop());
        };

        // Start recording
        mediaRecorder.start();
        isRecording = true;

        // Update UI
        recordBtn.disabled = true;
        stopBtn.disabled = false;
        setStatus('Recording...', 'info');

    } catch (err) {
        console.error('Failed to start recording:', err);
        setStatus('Failed to start recording: ' + err.message, 'error');
    }
}

// Stop recording
function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;

        // Update UI
        recordBtn.disabled = false;
        stopBtn.disabled = true;
        setStatus('Recording stopped. Processing...', 'info');
    }
}

// Process YouTube video
async function processYouTube() {
    const youtubeUrl = youtubeUrlInput.value.trim();
    const topicName = topicNameInput.value.trim();

    if (!youtubeUrl) {
        setStatus('Please enter a YouTube URL', 'error');
        return;
    }

    if (!youtubeUrl.startsWith('http')) {
        setStatus('Please enter a valid YouTube URL', 'error');
        return;
    }

    try {
        setStatus('Processing YouTube video...', 'info');

        // Send to background for processing
        chrome.runtime.sendMessage({
            action: 'processYouTube',
            youtubeUrl: youtubeUrl,
            topicName: topicName
        });

    } catch (err) {
        console.error('Failed to process YouTube video:', err);
        setStatus('Failed to process video: ' + err.message, 'error');
    }
}

// Event listeners
recordBtn.addEventListener('click', startRecording);
stopBtn.addEventListener('click', stopRecording);
processYoutubeBtn.addEventListener('click', processYouTube);

// Handle messages from background
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'updateStatus') {
        setStatus(message.message, message.type);
    } else if (message.action === 'recordingComplete') {
        // Reset recording state
        recordBtn.disabled = false;
        stopBtn.disabled = true;
        isRecording = false;
        setStatus('Recording processed successfully!', 'success');
    } else if (message.action === 'youtubeComplete') {
        setStatus('YouTube video processed successfully!', 'success');
    } else if (message.action === 'error') {
        setStatus('Error: ' + message.message, 'error');

        // Reset recording state if it was recording
        if (isRecording && mediaRecorder) {
            mediaRecorder.stop();
            isRecording = false;
            recordBtn.disabled = false;
            stopBtn.disabled = true;
        }
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    clearStatus();
});