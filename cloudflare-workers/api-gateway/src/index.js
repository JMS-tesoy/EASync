import { AutoRouter } from 'itty-router';

const router = AutoRouter();

// CORS Configuration
const CORS_HEADERS = {
	'Access-Control-Allow-Origin': '*', // Update this to specific domains in production
	'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
	'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
	'Access-Control-Max-Age': '86400',
};

// Security Headers
const SECURITY_HEADERS = {
	'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
	'X-XSS-Protection': '1; mode=block',
	'X-Frame-Options': 'DENY',
	'X-Content-Type-Options': 'nosniff',
	'Referrer-Policy': 'strict-origin-when-cross-origin',
};

// Preflight OPTIONS handler
router.options('*', () => {
	return new Response(null, {
		headers: CORS_HEADERS,
	});
});

// Proxy handler for all other requests
router.all('*', async (request, env) => {
	const url = new URL(request.url);
	const backendUrl = env.BACKEND_URL || 'http://127.0.0.1:8000/api/v1';

	// Construct target URL
	// If the request path is /api/v1/auth/login, we want to forward it to BACKEND_URL/auth/login
	// Adjust path logic based on how BACKEND_URL is defined.
	// Assumption: BACKEND_URL includes /api/v1 base path.

	// If request URL is https://worker.dev/api/v1/resource
	// And BACKEND_URL is http://backend/api/v1
	// We want to path match correctly.

	// Simplification: We assume the worker is mounted at /api/v1 or root.
	// Let's forward the pathname directly to the backend base.

	const targetPath = url.pathname;
	const targetUrl = new URL(targetPath, backendUrl).toString() + url.search;

	try {
		const newRequest = new Request(targetUrl, {
			method: request.method,
			headers: request.headers,
			body: request.body,
			redirect: 'follow',
		});

		// Add custom headers if needed
		newRequest.headers.set('X-Forwarded-For', request.headers.get('CF-Connecting-IP'));
		newRequest.headers.set('X-Worker-Proxy', 'true');

		const response = await fetch(newRequest);

		// Recreate response to modify headers (Response headers are immutable in some contexts)
		const newResponse = new Response(response.body, response);

		// Add CORS and Security headers to response
		Object.entries(CORS_HEADERS).forEach(([key, value]) => {
			newResponse.headers.set(key, value);
		});
		Object.entries(SECURITY_HEADERS).forEach(([key, value]) => {
			newResponse.headers.set(key, value);
		});

		return newResponse;

	} catch (e) {
		return new Response(JSON.stringify({ error: 'Gateway Error', message: e.message }), {
			status: 502,
			headers: {
				...CORS_HEADERS,
				'Content-Type': 'application/json'
			}
		});
	}
});

export default {
	fetch: router.fetch
};
