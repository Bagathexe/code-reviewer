// Configuration - Auto-detect API URL
// Supports both localhost and ngrok URLs
function getApiBaseUrl() {
    // If accessing through ngrok, use the current origin
    // Otherwise, default to localhost
    const currentOrigin = window.location.origin;
    
    // Check if we're on ngrok (ngrok URLs contain 'ngrok' or are https)
    if (currentOrigin.includes('ngrok') || currentOrigin.startsWith('https://')) {
        return currentOrigin;
    }
    
    // Check for environment variable or use localhost
    // You can also set this in localStorage: localStorage.setItem('API_BASE_URL', 'your-ngrok-url')
    const storedUrl = localStorage.getItem('API_BASE_URL');
    if (storedUrl) {
        return storedUrl;
    }
    
    // Default to localhost
    return 'http://localhost:8001';
}

const API_BASE_URL = getApiBaseUrl();
console.log(`🔗 Using API URL: ${API_BASE_URL}`);

// DOM Elements
const loadingElement = document.getElementById('loading');
const prContainer = document.getElementById('pr-container');
const errorMessage = document.getElementById('error-message');
const errorText = document.getElementById('error-text');

// PR Info Elements
const prTitle = document.getElementById('pr-title');
const prNumber = document.getElementById('pr-number');
const repoName = document.getElementById('repo-name');
const prAuthor = document.getElementById('pr-author');
const creationDate = document.getElementById('creation-date');
const prStatus = document.getElementById('pr-status');
const sourceBranch = document.getElementById('source-branch');
const targetBranch = document.getElementById('target-branch');

// Changes Elements
const filesCount = document.getElementById('files-count');
const linesAdded = document.getElementById('lines-added');
const linesRemoved = document.getElementById('lines-removed');
const modifiedFiles = document.getElementById('modified-files');
const diffContent = document.getElementById('diff-content');

// Sample data for testing (remove when backend is ready)
const samplePRData = {
    title: "Add weather forecast feature",
    number: 42,
    repository: "eshwarvk/Weather-App",
    author: "eshwarvk",
    created_at: "2024-01-15T10:30:00Z",
    state: "open",
    head: {
        ref: "feature/weather-forecast"
    },
    base: {
        ref: "main"
    },
    stats: {
        additions: 156,
        deletions: 23,
        total: 179
    },
    files: [
        "src/components/WeatherForecast.js",
        "src/styles/forecast.css",
        "src/utils/weatherAPI.js",
        "tests/weatherForecast.test.js"
    ],
    diff: `diff --git a/src/components/WeatherForecast.js b/src/components/WeatherForecast.js
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/src/components/WeatherForecast.js
@@ -0,0 +1,45 @@
+import React, { useState, useEffect } from 'react';
+import { fetchWeatherData } from '../utils/weatherAPI';
+
+const WeatherForecast = ({ city }) => {
+  const [forecast, setForecast] = useState(null);
+  const [loading, setLoading] = useState(true);
+
+  useEffect(() => {
+    const loadForecast = async () => {
+      try {
+        const data = await fetchWeatherData(city);
+        setForecast(data);
+      } catch (error) {
+        console.error('Failed to load forecast:', error);
+      } finally {
+        setLoading(false);
+      }
+    };
+
+    loadForecast();
+  }, [city]);
+
+  if (loading) return <div>Loading forecast...</div>;
+
+  return (
+    <div className="weather-forecast">
+      <h2>5-Day Forecast for {city}</h2>
+      {forecast && forecast.map((day, index) => (
+        <div key={index} className="forecast-day">
+          <span>{day.date}</span>
+          <span>{day.temperature}°C</span>
+          <span>{day.description}</span>
+        </div>
+      ))}
+    </div>
+  );
+};
+
+export default WeatherForecast;`
};

// Utility Functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getStatusClass(status) {
    switch (status.toLowerCase()) {
        case 'open':
            return 'status-open';
        case 'closed':
            return 'status-closed';
        case 'merged':
            return 'status-merged';
        default:
            return '';
    }
}

function showLoading() {
    loadingElement.style.display = 'block';
    prContainer.style.display = 'none';
    errorMessage.style.display = 'none';
}

function showError(message) {
    loadingElement.style.display = 'none';
    prContainer.style.display = 'none';
    errorMessage.style.display = 'block';
    errorText.textContent = message;
}

function showPRData() {
    loadingElement.style.display = 'none';
    prContainer.style.display = 'block';
    errorMessage.style.display = 'none';
}

// Main Functions
async function fetchPRData() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/pr/latest`);
        if (!response.ok) {
            throw new Error(`Failed to fetch PR data: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        
        // Check if data is available
        if (data.available === false || !data.title) {
            console.log('No PR data available, using sample data for demonstration');
            // Return sample data for demonstration
            await new Promise(resolve => setTimeout(resolve, 1000));
            return samplePRData;
        }
        
        return data;
    } catch (error) {
        console.error('Error fetching PR data:', error);
        
        // Check if it's a network error (CORS, connection refused, etc.)
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            console.error('⚠️ Network error - is the backend running?');
            console.error(`💡 Make sure the backend is running at ${API_BASE_URL}`);
            throw new Error(`Cannot connect to backend at ${API_BASE_URL}. Make sure the server is running.`);
        }
        
        // Fallback to sample data for demonstration
        console.log('Using sample data for demonstration');
        await new Promise(resolve => setTimeout(resolve, 1000));
        return samplePRData;
    }
}

function populatePRInfo(data) {
    // Basic PR Information
    prTitle.textContent = data.title;
    prNumber.textContent = `#${data.number}`;
    repoName.textContent = data.repository;
    prAuthor.textContent = data.author;
    creationDate.textContent = formatDate(data.created_at);
    
    // Status with styling
    prStatus.textContent = data.state;
    prStatus.className = `status-badge ${getStatusClass(data.state)}`;
    
    // Branch information
    sourceBranch.textContent = data.head.ref;
    targetBranch.textContent = data.base.ref;
    
    // Code changes summary
    filesCount.textContent = data.files.length;
    linesAdded.textContent = `+${data.stats.additions}`;
    linesRemoved.textContent = `-${data.stats.deletions}`;
    
    // Modified files list
    modifiedFiles.innerHTML = '';
    data.files.forEach(file => {
        const li = document.createElement('li');
        li.textContent = file;
        modifiedFiles.appendChild(li);
    });
    
    // Diff content
    diffContent.textContent = data.diff;
}

async function loadPRData() {
    showLoading();
    
    try {
        const prData = await fetchPRData();
        populatePRInfo(prData);
        showPRData();
    } catch (error) {
        showError(`Failed to load PR data: ${error.message}`);
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    console.log('PR Review Dashboard initialized');
    loadPRData();
});

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        formatDate,
        getStatusClass,
        loadPRData
    };
}