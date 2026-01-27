/**
 * API Configuration
 * Centralized API URL management with environment variable support
 */

// Get API URL from environment variable or fallback to localhost
export const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1'

// Get WebSocket URL from environment variable or fallback to localhost
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000'

// Get environment name
export const ENVIRONMENT = import.meta.env.VITE_ENVIRONMENT || 'development'

// Helper to check if in production
export const isProduction = () => ENVIRONMENT === 'production'

// Helper to check if in development
export const isDevelopment = () => ENVIRONMENT === 'development'

/**
 * Get static file URL (for EA downloads)
 * @param {string} filename - Name of the file
 * @returns {string} Full URL to the file
 */
export const getStaticFileUrl = (filename) => {
    const baseUrl = API_URL.replace('/api/v1', '')
    return `${baseUrl}/static/downloads/${filename}`
}

export default {
    API_URL,
    WS_URL,
    ENVIRONMENT,
    isProduction,
    isDevelopment,
    getStaticFileUrl
}
