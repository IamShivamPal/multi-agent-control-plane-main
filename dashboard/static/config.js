// API Configuration
const API_CONFIG = {
    // Automatically detect environment
    PRODUCTION_URL: 'https://multi-agent-control-plane.onrender.com',
    LOCALHOST_URL: 'http://localhost:5000',
    
    // Get current API base URL
    getApiBase: function() {
        const hostname = window.location.hostname;
        
        // If running on Render or production domain
        if (hostname.includes('render.com') || hostname.includes('onrender.com')) {
            return this.PRODUCTION_URL + '/api';
        }
        
        // If running locally
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return this.LOCALHOST_URL + '/api';
        }
        
        // Default: use current origin
        return window.location.origin + '/api';
    }
};

// Export for use in dashboard
const API_BASE = API_CONFIG.getApiBase();
console.log('API Base URL:', API_BASE);
