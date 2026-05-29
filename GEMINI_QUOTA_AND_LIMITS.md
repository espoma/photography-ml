# Gemini API Quota and Free Tier Limits

## Where to Check Your Quota

1. **Google AI Studio Dashboard** (Easiest)
   - Visit: https://aistudio.google.com/
   - Sign in with your Google account
   - Left sidebar → "API keys" → Click your API key
   - Shows your current usage and rate limits

2. **Google Cloud Console** (If using Google Cloud project)
   - Visit: https://console.cloud.google.com/
   - Navigate to "APIs & Services" → "Credentials"
   - Select your API key
   - Go to "Quota" tab to see limits

## Free Tier Limits (as of May 2026)

| Metric | Limit |
|--------|-------|
| **Daily requests** | 1,500 requests/day |
| **Requests per minute** | 15 RPM |
| **Tokens per minute** | 1,000,000 TPM |
| **Cost** | Free |

## Why You Saw 503 Errors

The `503 UNAVAILABLE` error typically means:
- Gemini API is experiencing high demand/load spikes
- Your account temporarily hit rate limits
- The model is being updated

## Fallback Models Added

Your app now tries multiple free-tier models in this order:

1. **`gemini-2.5-flash`** (Primary) - Latest, fastest
2. **`gemini-1.5-flash`** (Fallback 1) - Reliable alternative
3. **`gemini-1.5-flash-8b`** (Fallback 2) - Lightweight version

If all three fail, it returns default tags: `["ai_generated", "photography"]`

## How to Increase Your Quota

1. **Upgrade to paid plan** (Google One)
   - Visit: https://ai.google.dev/pricing
   - Pay-as-you-go model ($0.075 per 1M input tokens)

2. **Request quota increase** (Google Cloud)
   - Go to Google Cloud Console → Quotas
   - Find "Generative AI" quota
   - Click "Edit Quotas" and request higher limit

3. **Use alternative free models**
   - Claude API (Anthropic) - Limited free tier
   - LLaMA 2 (via Hugging Face) - Self-hosted or API

## Current Implementation

The ML service now:
- ✅ Tries primary model first
- ✅ Automatically falls back to secondary models
- ✅ Logs each attempt for debugging
- ✅ Returns sensible defaults if all fail
- ✅ Doesn't block the user upload (they still get a saved image with fallback tags)

## Monitoring

Check the backend logs for tag generation status:
```bash
tail -f /tmp/photography-backend.log | grep "ML Service"
```

Look for:
- ✅ `Successfully generated tags with gemini-X-X`
- ⚠️  `Model gemini-X-X failed`
- ❌ `ML Service Error`

## Next Steps (Future)

- Add async tag generation (don't block upload)
- Implement retry logic with exponential backoff
- Cache tags for similar images
- Add image embeddings for similarity search (uses different API quota)
