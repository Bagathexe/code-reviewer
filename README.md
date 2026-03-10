# GitHub PR Review Dashboard

A simple web interface to display Pull Request information and code changes.

## Features

### 📋 PR Information Display
- PR Title and Number
- Repository Name
- Author/Creator
- Creation Date
- PR Status (Open/Closed/Merged)
- Branch Information (source → target)

### 📝 Code Changes Analysis
- Files Modified (list of changed files)
- Lines Added/Removed count
- Code Diff Preview
- File-by-file changes

## Setup Instructions

### 1. Backend Setup
```bash
cd backend
python gitData.py
```

### 2. Access the Dashboard
Open your browser and go to:
```
http://localhost:8000/dashboard
```

### 3. API Endpoints
- `GET /api/pr/latest` - Get latest PR data
- `GET /dashboard` - PR Dashboard UI
- `POST /webhook` - GitHub webhook endpoint

## How It Works

1. **GitHub Webhook**: When a PR is opened/updated, GitHub sends data to `/webhook`
2. **Data Processing**: Backend extracts PR info, fetches diff, and stores data
3. **UI Display**: Frontend fetches data from `/api/pr/latest` and displays it
4. **Real-time Updates**: Dashboard shows the most recent PR activity

## File Structure

```
├── backend/
│   └── gitData.py          # FastAPI server with webhook and API
├── frontend/
│   ├── index.html          # Dashboard UI
│   ├── styles.css          # Styling
│   └── script.js           # Frontend logic
├── .env                    # Environment variables
└── README.md              # This file
```

## Testing

The dashboard includes sample data for testing when no real PR data is available.

## Next Steps

1. Create a PR in your connected repository
2. Watch the webhook process the data
3. Refresh the dashboard to see real PR information
4. Add AI analysis features for code review

## Troubleshooting

- **404 Error**: Make sure your GitHub webhook URL includes `/webhook`
- **No Data**: Create a PR to generate data for the dashboard
- **ngrok URL Changes**: When ngrok restarts and gets a new URL:
  1. Get your new webhook URL by visiting: `http://localhost:8000/api/webhook/url` (or your ngrok URL)
  2. Update the webhook URL in GitHub repository Settings > Webhooks
  3. The frontend will automatically detect ngrok URLs when accessed through them

## ngrok Setup (for GitHub Webhooks)

If you're using ngrok to expose your local server:

1. **Start ngrok**:
   ```bash
   ngrok http 8000
   ```

2. **Get your webhook URL**:
   - Visit: `http://localhost:8000/api/webhook/url` (or your ngrok URL)
   - Copy the `webhook_url` from the response

3. **Configure GitHub Webhook**:
   - Go to your GitHub repository: Settings > Webhooks > Add webhook
   - Paste the webhook URL
   - Content type: `application/json`
   - Select event: `Pull requests`
   - Save

4. **When ngrok URL changes**:
   - Simply visit `/api/webhook/url` again to get the new URL
   - Update it in GitHub webhook settings

5. **Frontend Access**:
   - Access the dashboard through your ngrok URL: `https://your-ngrok-url.ngrok.io/dashboard`
   - The frontend will automatically use the correct API URL
- **CORS Issues**: Backend includes CORS middleware for local development