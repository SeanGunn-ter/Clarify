const HEALTH_URL = 'http://127.0.0.1:5000/health';  // Consistent URL

chrome.action.onClicked.addListener(async () => {
    try {
        const healthCheck = await fetch(HEALTH_URL, {
            cache: 'no-store',
            headers: { 'Cache-Control': 'no-cache' }
        });
        if (healthCheck.ok) {
            chrome.tabs.create({ url: 'http://127.0.0.1:5000' });
            return;
        }
    } catch (error) {
        console.log('Server not responding, attempting to start...');
    }
    
    // 2. Start via native messaging
    chrome.runtime.sendNativeMessage(
        'com.simplify.launch-server',
        { command: 'start_server' },
        (response) => {
            if (chrome.runtime.lastError) {
                console.error('Native messaging error:', chrome.runtime.lastError);
                showError('Failed to communicate with server launcher');
                return;
            }

            if (!response?.success) {
                console.error('Startup failed:', response?.error);
                showError(response?.error || 'Server failed to start');
                return;
            }

            // 3. Poll for server with timeout
            pollServerStart();
        }
    );

    function pollServerStart(attempts = 0) {
        const MAX_ATTEMPTS = 30; // 30 seconds max
        const RETRY_DELAY = 1000; // 1 second between tries

        fetch('http://localhost:5000/health')
            .then(res => {
                if (res.ok) {
                    chrome.tabs.create({ url: 'http://localhost:5000' });
                } else if (attempts < MAX_ATTEMPTS) {
                    setTimeout(() => pollServerStart(attempts + 1), RETRY_DELAY);
                } else {
                    throw new Error('Timeout waiting for server');
                }
            })
            .catch(err => {
                if (attempts < MAX_ATTEMPTS) {
                    setTimeout(() => pollServerStart(attempts + 1), RETRY_DELAY);
                } else {
                    console.error('Server never came online');
                    showError(err.message);
                }
            });
    }

    function showError(message) {
        chrome.tabs.create({ 
            url: chrome.runtime.getURL('error.html'),
            active: true
        });
    }
});