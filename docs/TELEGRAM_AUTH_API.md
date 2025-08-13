# Telegram Authentication API Documentation

## Overview

The Telegram Authentication API enables secure account linking between Telegram users and the web application. It provides a magic-link flow where users can tap a button in the Telegram bot and be automatically logged into the web application.

## Authentication

All endpoints require authentication via the `Authorization` header with a Bearer token:

```
Authorization: Bearer your-api-key-here
```

## Base URL

```
https://your-api.example.com
```

## Endpoints

### Create Telegram Link

Creates a secure, short-lived link for account linking.

**Endpoint:** `POST /api/auth/telegram/link`

**Headers:**
- `Authorization: Bearer {API_KEY}` (required)
- `Content-Type: application/json`

**Request Body:**
```json
{
  "telegram_user_id": 123456789
}
```

**Success Response (200):**
```json
{
  "link_url": "https://your-app.com/telegram/complete?token=eyJhbGciOiJIUzI1NiIs..."
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid API key
- `429 Too Many Requests` - Rate limit exceeded (5 requests per 10 minutes)
- `500 Internal Server Error` - Server error

**Rate Limit:** 5 requests per 10 minutes per Telegram user ID

---

### Complete Telegram Link

Completes the account linking process using the token from the link.

**Endpoint:** `POST /api/auth/telegram/complete`

**Headers:**
- `Content-Type: application/json`

**Request Body:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Success Response (200):**
```json
{
  "status": "ok",
  "user": {
    "id": 123,
    "telegram_user_id": 123456789,
    "username": "telegram_user_123456789",
    "internal_user_id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "token": "session-jwt-token-here"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid token, expired token, or token already used
  - `TOKEN_INVALID` - Token is malformed or invalid
  - `TOKEN_EXPIRED` - Token has expired (5 minutes)
  - `TOKEN_USED` - Token has already been used
- `409 Conflict` - Telegram account already linked to another user
- `429 Too Many Requests` - Rate limit exceeded (10 requests per 10 minutes)
- `500 Internal Server Error` - Server error

**Rate Limit:** 10 requests per 10 minutes per IP address

---

### Check Link Status

Checks if a Telegram user ID is already linked to an account.

**Endpoint:** `GET /api/auth/telegram/status/{telegram_user_id}`

**Headers:**
- `Authorization: Bearer {API_KEY}` (required)

**Path Parameters:**
- `telegram_user_id` (integer) - The Telegram user ID to check

**Success Response (200):**
```json
{
  "telegram_user_id": 123456789,
  "is_linked": true,
  "user_id": 123,
  "username": "telegram_user_123456789"
}
```

For unlinked users:
```json
{
  "telegram_user_id": 123456789,
  "is_linked": false,
  "user_id": null,
  "username": null
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid API key
- `500 Internal Server Error` - Server error

## Error Format

All error responses follow this format:

```json
{
  "detail": "Error message here"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Link Creation:** 5 requests per 10 minutes per Telegram user ID
- **Link Completion:** 10 requests per 10 minutes per IP address

When rate limits are exceeded, the API returns:
```json
{
  "detail": "Rate limit exceeded: max X requests per Y minutes"
}
```

## Security Features

### Token Security
- **Short-lived tokens:** 5-minute expiry time
- **Single-use enforcement:** Each token can only be used once
- **Cryptographic signatures:** JWT tokens signed with secure secret
- **Audience validation:** Prevents token misuse

### API Security
- **API key authentication:** Required for sensitive operations
- **Rate limiting:** Prevents abuse and brute force attacks
- **Input validation:** All requests validated with Pydantic models
- **HTTPS only:** All communications must be encrypted

## Integration Examples

### Python (Bot Integration)

```python
import requests

def create_telegram_link(telegram_user_id: int) -> str:
    """Create a linking URL for a Telegram user"""
    response = requests.post(
        "https://your-api.com/api/auth/telegram/link",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={"telegram_user_id": telegram_user_id}
    )
    
    if response.status_code == 200:
        return response.json()["link_url"]
    else:
        raise Exception(f"Failed to create link: {response.text}")

def check_link_status(telegram_user_id: int) -> dict:
    """Check if a Telegram user is already linked"""
    response = requests.get(
        f"https://your-api.com/api/auth/telegram/status/{telegram_user_id}",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    
    return response.json()
```

### JavaScript (Frontend Integration)

```javascript
async function completeTelegramLink(token) {
    try {
        const response = await fetch('/api/auth/telegram/complete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ token })
        });

        if (response.ok) {
            const data = await response.json();
            // Store session token
            localStorage.setItem('session_token', data.token);
            // Redirect to dashboard
            window.location.href = '/dashboard';
        } else {
            const error = await response.json();
            handleLinkError(error.detail);
        }
    } catch (error) {
        console.error('Link completion failed:', error);
    }
}

function handleLinkError(errorCode) {
    switch (errorCode) {
        case 'TOKEN_EXPIRED':
            showMessage('Link has expired. Please request a new link from the bot.');
            break;
        case 'TOKEN_USED':
            showMessage('This link has already been used.');
            break;
        case 'TOKEN_INVALID':
            showMessage('Invalid link. Please request a new link from the bot.');
            break;
        default:
            showMessage('An error occurred. Please try again.');
    }
}
```

## Webhook Integration

For real-time notifications, you can set up webhooks:

```python
# Example webhook handler for successful linking
@app.post("/webhooks/telegram-linked")
async def handle_telegram_linked(data: dict):
    user_id = data["user"]["id"]
    telegram_user_id = data["user"]["telegram_user_id"]
    
    # Send welcome message via Telegram bot
    await send_telegram_message(
        telegram_user_id,
        "🎉 Your account has been successfully linked! Welcome to the platform."
    )
```

## Testing

### Test Endpoints

Use these curl commands to test the API:

```bash
# Create a link
curl -X POST "https://your-api.com/api/auth/telegram/link" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"telegram_user_id": 123456789}'

# Complete a link
curl -X POST "https://your-api.com/api/auth/telegram/complete" \
  -H "Content-Type: application/json" \
  -d '{"token": "your-token-here"}'

# Check status
curl -X GET "https://your-api.com/api/auth/telegram/status/123456789" \
  -H "Authorization: Bearer your-api-key"
```

### Test Flow

1. Create a link for a test Telegram user ID
2. Extract the token from the returned URL
3. Complete the link using the token
4. Verify the user was created/linked in the database
5. Check that the token cannot be reused

## Monitoring

### Metrics to Track

- `telegram_link_requested` - Number of link creation requests
- `telegram_link_completed` - Number of successful link completions
- `telegram_link_failed` - Number of failed link attempts
- `telegram_rate_limited` - Number of rate-limited requests

### Log Events

- Link creation with Telegram user ID
- Successful/failed link completions
- Rate limit violations
- Authentication failures

## Environment Configuration

Required environment variables:

```env
BACKEND_API_KEY="your-secure-api-key-here"
BACKEND_JWT_SECRET="your-jwt-secret-key-here"
BACKEND_JWT_AUDIENCE="telegram-link"
FRONTEND_BASE_URL="https://your-app.com"
SESSION_SECRET="your-session-secret-key-here"
```