# Telegram Authentication Integration Guide

## Overview

This guide walks you through integrating the Telegram authentication system into your bot and frontend application.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Bot Integration](#bot-integration)
3. [Frontend Integration](#frontend-integration)
4. [Database Setup](#database-setup)
5. [Environment Configuration](#environment-configuration)
6. [Testing the Integration](#testing-the-integration)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

- FastAPI backend with Telegram auth endpoints implemented
- Telegram bot with python-telegram-bot library
- Next.js frontend (or any frontend framework)
- PostgreSQL database
- Environment variables configured

## Bot Integration

### 1. Update Bot Dependencies

Add the required dependency to your bot:

```bash
pip install requests
```

### 2. Bot Configuration

Add these environment variables to your bot:

```env
BACKEND_URL="https://your-api.com"
BACKEND_API_KEY="your-secure-api-key-here"
```

### 3. Implement Link Command

Add this to your Telegram bot code:

```python
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

BACKEND_URL = os.getenv("BACKEND_URL")
BACKEND_API_KEY = os.getenv("BACKEND_API_KEY")

async def link_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /link command to create account linking URL"""
    user = update.effective_user
    telegram_user_id = user.id
    
    # Check if user is already linked
    try:
        status_response = requests.get(
            f"{BACKEND_URL}/api/auth/telegram/status/{telegram_user_id}",
            headers={"Authorization": f"Bearer {BACKEND_API_KEY}"}
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            if status_data["is_linked"]:
                await update.message.reply_text(
                    "✅ Your account is already linked!\n"
                    f"Username: {status_data['username']}"
                )
                return
    except Exception as e:
        print(f"Error checking link status: {e}")
    
    # Create new link
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/auth/telegram/link",
            headers={
                "Authorization": f"Bearer {BACKEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"telegram_user_id": telegram_user_id}
        )
        
        if response.status_code == 200:
            data = response.json()
            link_url = data["link_url"]
            
            # Create inline keyboard with the link
            keyboard = [[
                InlineKeyboardButton("🔗 Link Account", url=link_url)
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🔐 To link your Telegram account with the web platform:\n\n"
                "1️⃣ Click the button below\n"
                "2️⃣ You'll be redirected to the website\n"
                "3️⃣ Your account will be automatically linked\n\n"
                "⚠️ This link expires in 5 minutes for security.",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "❌ Sorry, I couldn't create a link right now. "
                "Please try again in a few minutes."
            )
            
    except requests.exceptions.RequestException as e:
        print(f"Error creating link: {e}")
        await update.message.reply_text(
            "❌ Network error occurred. Please try again later."
        )
    except Exception as e:
        print(f"Unexpected error: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Please try again."
        )

# Add the command handler to your bot
def main():
    application = Application.builder().token("YOUR_BOT_TOKEN").build()
    
    # Add handlers
    application.add_handler(CommandHandler("link", link_account))
    
    # Add to help command
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        help_text = """
Available commands:
/start - Start the bot
/help - Show this help message
/link - Link your Telegram account with the web platform
        """
        await update.message.reply_text(help_text)
    
    application.add_handler(CommandHandler("help", help_command))
    
    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()
```

### 4. Enhanced Error Handling

Add comprehensive error handling:

```python
async def link_account_with_retry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enhanced link command with retry logic and better error handling"""
    user = update.effective_user
    telegram_user_id = user.id
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Create link request
            response = requests.post(
                f"{BACKEND_URL}/api/auth/telegram/link",
                headers={
                    "Authorization": f"Bearer {BACKEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={"telegram_user_id": telegram_user_id},
                timeout=10
            )
            
            if response.status_code == 200:
                # Success case
                data = response.json()
                keyboard = [[
                    InlineKeyboardButton("🔗 Link Account", url=data["link_url"])
                ]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "🔐 Click the button below to link your account:\n\n"
                    "⏱ This link expires in 5 minutes",
                    reply_markup=reply_markup
                )
                return
                
            elif response.status_code == 429:
                # Rate limited
                await update.message.reply_text(
                    "⏳ You're making requests too quickly. "
                    "Please wait a moment and try again."
                )
                return
                
            elif response.status_code == 401:
                # API key issue
                await update.message.reply_text(
                    "🔧 Service configuration error. "
                    "Please contact support."
                )
                return
                
        except requests.exceptions.Timeout:
            retry_count += 1
            if retry_count >= max_retries:
                await update.message.reply_text(
                    "⏱ Request timed out. Please try again later."
                )
                return
                
        except requests.exceptions.ConnectionError:
            retry_count += 1
            if retry_count >= max_retries:
                await update.message.reply_text(
                    "🌐 Cannot connect to the service. Please try again later."
                )
                return
                
        except Exception as e:
            print(f"Unexpected error in link_account: {e}")
            await update.message.reply_text(
                "❌ An unexpected error occurred. Please try again."
            )
            return
    
    # If we get here, all retries failed
    await update.message.reply_text(
        "❌ Service temporarily unavailable. Please try again later."
    )
```

## Frontend Integration

### 1. Create Completion Page

Create `pages/telegram/complete.tsx` (Next.js) or equivalent:

```tsx
import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';

interface CompletionResult {
  success: boolean;
  message: string;
  user?: {
    id: number;
    username: string;
    telegram_user_id: number;
  };
}

export default function TelegramComplete() {
  const router = useRouter();
  const [result, setResult] = useState<CompletionResult | null>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const completeLink = async () => {
      const { token } = router.query;
      
      if (!token || typeof token !== 'string') {
        setResult({
          success: false,
          message: 'Invalid or missing token'
        });
        setLoading(false);
        return;
      }
      
      try {
        const response = await fetch('/api/telegram/complete', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ token }),
        });
        
        const data = await response.json();
        
        if (response.ok) {
          // Store session token
          localStorage.setItem('session_token', data.token);
          
          setResult({
            success: true,
            message: 'Account successfully linked!',
            user: data.user
          });
          
          // Redirect after 3 seconds
          setTimeout(() => {
            router.push('/dashboard');
          }, 3000);
          
        } else {
          let message = 'Account linking failed';
          
          switch (data.detail) {
            case 'TOKEN_EXPIRED':
              message = 'Link has expired. Please request a new link from the bot.';
              break;
            case 'TOKEN_USED':
              message = 'This link has already been used.';
              break;
            case 'TOKEN_INVALID':
              message = 'Invalid link. Please request a new link from the bot.';
              break;
          }
          
          setResult({
            success: false,
            message
          });
        }
      } catch (error) {
        console.error('Link completion error:', error);
        setResult({
          success: false,
          message: 'Network error. Please check your connection and try again.'
        });
      }
      
      setLoading(false);
    };
    
    if (router.isReady) {
      completeLink();
    }
  }, [router.isReady, router.query]);
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-lg">Linking your account...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-8">
        {result?.success ? (
          <div className="text-center">
            <div className="text-green-500 text-6xl mb-4">✅</div>
            <h1 className="text-2xl font-bold text-gray-800 mb-4">
              Account Linked Successfully!
            </h1>
            <p className="text-gray-600 mb-4">{result.message}</p>
            {result.user && (
              <div className="bg-gray-100 rounded p-4 mb-4">
                <p><strong>User ID:</strong> {result.user.id}</p>
                <p><strong>Username:</strong> {result.user.username}</p>
                <p><strong>Telegram ID:</strong> {result.user.telegram_user_id}</p>
              </div>
            )}
            <p className="text-sm text-gray-500">
              Redirecting to dashboard in 3 seconds...
            </p>
          </div>
        ) : (
          <div className="text-center">
            <div className="text-red-500 text-6xl mb-4">❌</div>
            <h1 className="text-2xl font-bold text-gray-800 mb-4">
              Linking Failed
            </h1>
            <p className="text-gray-600 mb-6">{result?.message}</p>
            <button
              onClick={() => window.open('https://t.me/your_bot', '_blank')}
              className="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded"
            >
              Open Telegram Bot
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
```

### 2. Create API Route

Create `pages/api/telegram/complete.ts`:

```typescript
import { NextApiRequest, NextApiResponse } from 'next';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  
  try {
    const { token } = req.body;
    
    if (!token) {
      return res.status(400).json({ error: 'Token is required' });
    }
    
    // Forward request to backend
    const response = await fetch(`${BACKEND_URL}/api/auth/telegram/complete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ token }),
    });
    
    const data = await response.json();
    
    if (response.ok) {
      // Set HTTP-only cookie for session
      const sessionToken = data.token;
      
      res.setHeader('Set-Cookie', [
        `session=${sessionToken}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=86400`
      ]);
      
      // Remove token from response for security
      const { token: _, ...responseData } = data;
      
      return res.status(200).json(responseData);
    } else {
      return res.status(response.status).json(data);
    }
    
  } catch (error) {
    console.error('Telegram completion error:', error);
    return res.status(500).json({ 
      error: 'Internal server error',
      detail: 'SERVICE_UNAVAILABLE'
    });
  }
}
```

### 3. Add Environment Variables

Add to your frontend `.env.local`:

```env
BACKEND_URL=http://localhost:8000
NEXTAUTH_SECRET=your-nextauth-secret-here
```

## Database Setup

### 1. Run Migration

Apply the database migration:

```bash
# In your FastAPI project directory
alembic upgrade head
```

### 2. Verify Tables

Check that the tables were created:

```sql
-- Check users table has telegram_user_id column
\d users;

-- Check telegram_link_tokens table exists
\d telegram_link_tokens;

-- Verify indexes
\di users;
\di telegram_link_tokens;
```

## Environment Configuration

### Backend (.env.development)

```env
# Database
POSTGRES_URL="your-postgres-connection-string"
POSTGRES_USER="your-db-user"
POSTGRES_PASSWORD="your-db-password"
POSTGRES_HOST="your-db-host"
POSTGRES_DATABASE="your-db-name"

# Telegram Auth
BACKEND_API_KEY="your-secure-api-key-here"
BACKEND_JWT_SECRET="your-jwt-secret-key-here"
BACKEND_JWT_AUDIENCE="telegram-link"
FRONTEND_BASE_URL="http://localhost:3000"
SESSION_SECRET="your-session-secret-key-here"
```

### Bot Environment

```env
BOT_TOKEN="your-telegram-bot-token"
BACKEND_URL="http://localhost:8000"
BACKEND_API_KEY="your-secure-api-key-here"
```

### Frontend Environment

```env
BACKEND_URL="http://localhost:8000"
NEXTAUTH_SECRET="your-nextauth-secret-here"
```

## Testing the Integration

### 1. End-to-End Test

1. Start your FastAPI backend
2. Start your frontend application
3. Start your Telegram bot
4. Send `/link` command to your bot
5. Click the link button
6. Verify redirection to completion page
7. Check that user is created in database
8. Verify session is established

### 2. Test Commands

```bash
# Test bot link creation
curl -X POST "http://localhost:8000/api/auth/telegram/link" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"telegram_user_id": 123456789}'

# Test link completion
curl -X POST "http://localhost:8000/api/auth/telegram/complete" \
  -H "Content-Type: application/json" \
  -d '{"token": "your-token-here"}'

# Check database
psql -d your_db -c "SELECT * FROM users WHERE telegram_user_id IS NOT NULL;"
psql -d your_db -c "SELECT * FROM telegram_link_tokens ORDER BY issued_at DESC LIMIT 5;"
```

## Troubleshooting

### Common Issues

**1. "Invalid API key" Error**
- Check that `BACKEND_API_KEY` is the same in bot and backend
- Verify the Authorization header format: `Bearer your-key`

**2. "TOKEN_INVALID" Error**
- Token may have expired (5 minutes)
- Check JWT secret configuration
- Verify token wasn't truncated in URL

**3. Rate Limit Exceeded**
- Wait for the rate limit window to reset
- Implement exponential backoff in bot

**4. Database Connection Issues**
- Verify database credentials
- Check if migration was applied
- Ensure database is accessible from backend

**5. CORS Issues**
- Add frontend domain to CORS origins in FastAPI
- Check if credentials are allowed

### Debug Mode

Enable debug logging in your bot:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Add detailed logging to link function
print(f"Creating link for user: {telegram_user_id}")
print(f"Backend URL: {BACKEND_URL}")
print(f"Response status: {response.status_code}")
print(f"Response body: {response.text}")
```

### Health Checks

Add health check endpoints:

```python
# In your FastAPI app
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "telegram-auth"
    }

@app.get("/health/telegram")
async def telegram_health(api_key: str = Depends(verify_api_key)):
    return {
        "telegram_auth": "healthy",
        "api_key_valid": True,
        "jwt_secret_configured": bool(settings.BACKEND_JWT_SECRET)
    }
```

This integration guide should help you successfully implement the Telegram authentication flow in your application. Remember to test thoroughly in a development environment before deploying to production.