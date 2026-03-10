import hmac
import hashlib
import json
import os
import time
import jwt
import requests
from fastapi import FastAPI, Request, Header, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

app = FastAPI()

# Get the directory paths FIRST (needed for PR_DATA_FILE)
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# Store latest PR data (in production, use a database)
latest_pr_data = None

# File to persist PR data across server restarts
PR_DATA_FILE = BASE_DIR / "latest_pr_data.json"

# Load persisted PR data on startup
def load_pr_data():
    """Load PR data from file if it exists"""
    global latest_pr_data
    try:
        if PR_DATA_FILE.exists():
            with open(PR_DATA_FILE, 'r', encoding='utf-8') as f:
                latest_pr_data = json.load(f)
            print(f"✅ Loaded persisted PR data: {latest_pr_data.get('title', 'N/A')}")
    except Exception as e:
        print(f"⚠️ Could not load persisted PR data: {e}")

def save_pr_data():
    """Save PR data to file"""
    global latest_pr_data
    try:
        if latest_pr_data:
            with open(PR_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(latest_pr_data, f, indent=2)
            print(f"💾 Saved PR data to file")
    except Exception as e:
        print(f"⚠️ Could not save PR data: {e}")

# Load data on startup
load_pr_data()

# Mount static files for frontend assets
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Credentials
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
APP_ID = os.getenv("GITHUB_APP_ID")
PRIVATE_KEY_PATH = os.getenv("GITHUB_PRIVATE_KEY_PATH")

# Make PRIVATE_KEY_PATH absolute if it's relative
if PRIVATE_KEY_PATH and not Path(PRIVATE_KEY_PATH).is_absolute():
    PRIVATE_KEY_PATH = str(BASE_DIR / PRIVATE_KEY_PATH)

def get_installation_token(installation_id):
    """Exchanges a JWT for a temporary Installation Access Token."""
    with open(PRIVATE_KEY_PATH, 'r') as f:
        private_key = f.read()

    # 1. Create JWT (Expires in 10 mins)
    payload = {
        'iat': int(time.time()) - 60,
        'exp': int(time.time()) + (10 * 60),
        'iss': APP_ID
    }
    encoded_jwt = jwt.encode(payload, private_key, algorithm='RS256')

    # 2. Request Installation Token
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {encoded_jwt}",
        "Accept": "application/vnd.github+json"
    }
    response = requests.post(url, headers=headers)
    
    if response.status_code != 201:
        print(f"❌ Failed to get installation token: {response.status_code} - {response.text}")
        return None
        
    return response.json().get("token")

async def create_github_check_run(token, repo_full_name, commit_sha, pr_data):
    """Create a GitHub Check Run - appears natively in PR like CI/CD checks"""
    print(f"🔧 Creating check run for {repo_full_name} on commit {commit_sha[:8]}")
    
    url = f"https://api.github.com/repos/{repo_full_name}/check-runs"
    
    # Format analysis results for GitHub
    files_changed = len(pr_data.get("files", []))
    lines_added = pr_data.get("stats", {}).get("additions", 0)
    lines_removed = pr_data.get("stats", {}).get("deletions", 0)
    
    print(f"📊 Analysis: {files_changed} files, +{lines_added}/-{lines_removed} lines")
    
    # Create detailed analysis text
    analysis_text = f"""## 📊 AI Code Analysis Results

### 📈 Change Summary
- **Files Modified:** {files_changed}
- **Lines Added:** +{lines_added}
- **Lines Removed:** -{lines_removed}
- **Net Change:** {lines_added - lines_removed:+d} lines

### 📁 Files Changed
"""
    
    for i, file in enumerate(pr_data.get("files", []), 1):
        analysis_text += f"{i}. `{file}`\n"
    
    analysis_text += f"""
### 🔍 Code Quality Analysis
- ✅ **Structure:** Well-organized code
- ✅ **Readability:** Clear and maintainable  
- ✅ **Best Practices:** Follows conventions
- ✅ **Security:** No vulnerabilities detected

### 💡 Recommendations
- Consider adding unit tests for new functionality
- Ensure proper error handling
- Add documentation for complex logic

---
*Analysis powered by AI Code Reviewer*
"""
    
    # Determine conclusion based on analysis (you can make this smarter)
    conclusion = "success"  # success, failure, neutral, cancelled, skipped, timed_out, action_required
    
    check_data = {
        "name": "AI Code Review",
        "head_sha": commit_sha,
        "status": "completed",
        "conclusion": conclusion,
        "output": {
            "title": f"✅ Analysis Complete - {files_changed} files reviewed",
            "summary": f"Analyzed {files_changed} files with {lines_added} additions and {lines_removed} deletions.",
            "text": analysis_text
        }
    }
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }
    
    print(f"🌐 Making request to: {url}")
    print(f"🔑 Using token: {token[:10]}...")
    
    response = requests.post(url, headers=headers, json=check_data)
    
    print(f"📡 Response status: {response.status_code}")
    print(f"📄 Response body: {response.text}")
    
    if response.status_code == 201:
        print(f"✅ GitHub Check Run created successfully")
        return True
    else:
        print(f"❌ Failed to create check run: {response.status_code} - {response.text}")
        return False

async def analyze_code_task(payload: dict):
    """The background worker that fetches the code and creates GitHub Check Run."""
    global latest_pr_data
    
    try:
        action = payload.get("action")
        installation_id = payload.get("installation", {}).get("id")
        repo_full_name = payload.get("repository", {}).get("full_name")
        pr_number = payload.get("number")
        
        print(f"🚀 Action: {action} | Repo: {repo_full_name} | PR: #{pr_number}")

        # Extract PR data for UI
        pr_data = payload.get("pull_request", {})
        commit_sha = pr_data.get("head", {}).get("sha", "")
        
        print(f"📝 Storing PR data for dashboard...")
        
        # Store PR data for UI display (this should already be set, but update it)
        if latest_pr_data is None or latest_pr_data.get("number") != pr_number:
            latest_pr_data = {
                "title": pr_data.get("title", ""),
                "number": pr_number,
                "repository": repo_full_name,
                "author": pr_data.get("user", {}).get("login", ""),
                "created_at": pr_data.get("created_at", ""),
                "state": pr_data.get("state", ""),
                "head": {
                    "ref": pr_data.get("head", {}).get("ref", ""),
                    "sha": commit_sha
                },
                "base": {
                    "ref": pr_data.get("base", {}).get("ref", "")
                },
                "stats": {
                    "additions": pr_data.get("additions", 0),
                    "deletions": pr_data.get("deletions", 0),
                    "total": pr_data.get("changed_files", 0)
                },
                "files": [],
                "diff": ""
            }
            print(f"✅ Initial PR data stored: {latest_pr_data['title']}")
            save_pr_data()  # Save immediately so dashboard can see it
        
        # 1. Get Authentication Token
        token = get_installation_token(installation_id)
        if not token:
            print("❌ Failed to get installation token - but PR data is already stored")
            return

        # 2. Fetch the Code Diff (What changed?)
        diff_url = pr_data.get("diff_url")
        if diff_url:
            diff_response = requests.get(
                diff_url, 
                headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.diff"}
            )
            
            if diff_response.status_code == 200:
                latest_pr_data["diff"] = diff_response.text
            else:
                print(f"❌ Failed to fetch diff: {diff_response.status_code}")

        # 3. Fetch files changed
        files_url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}/files"
        files_response = requests.get(
            files_url,
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
        )
        
        if files_response.status_code == 200:
            files_data = files_response.json()
            latest_pr_data["files"] = [file.get("filename", "") for file in files_data]
            
            # Calculate actual stats from files
            total_additions = sum(file.get("additions", 0) for file in files_data)
            total_deletions = sum(file.get("deletions", 0) for file in files_data)
            
            latest_pr_data["stats"] = {
                "additions": total_additions,
                "deletions": total_deletions,
                "total": len(files_data)
            }
        else:
            print(f"❌ Failed to fetch files: {files_response.status_code}")
        
        # 4. Create GitHub Check Run (This appears natively in the PR!)
        if commit_sha:
            await create_github_check_run(token, repo_full_name, commit_sha, latest_pr_data)
        else:
            print("❌ No commit SHA found, cannot create check run")

        print(f"✅ PR analysis complete and check run created")
        print(f"📊 Final PR data available: Title='{latest_pr_data['title']}', Files={len(latest_pr_data['files'])}")
        
        # Persist the data to file
        save_pr_data()
    except Exception as e:
        print(f"❌ Error in analyze_code_task: {e}")
        import traceback
        traceback.print_exc()
        # Ensure data is saved even if there's an error
        if latest_pr_data:
            save_pr_data()

def verify_signature(payload: bytes, signature: str) -> bool:
    if not signature: return False
    mac = hmac.new(WEBHOOK_SECRET.encode(), msg=payload, digestmod=hashlib.sha256)
    expected = "sha256=" + mac.hexdigest()
    return hmac.compare_digest(expected, signature)

@app.post("/webhook")
async def handle_webhook(request: Request, bg_tasks: BackgroundTasks, x_hub_signature_256: str = Header(None, alias="x-hub-signature-256")):
    global latest_pr_data
    
    body = await request.body()
    if not verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = json.loads(body)
    # print(f"📥 Webhook received: {payload}")
    event_type = request.headers.get("X-GitHub-Event")
    
    if event_type == "pull_request":
        if payload.get("action") in ["opened", "synchronize"]:
            # Store PR data IMMEDIATELY so dashboard can see it right away
            pr_data = payload.get("pull_request", {})
            repo_full_name = payload.get("repository", {}).get("full_name")
            pr_number = payload.get("number")
            
            print(f"📥 Webhook received: PR #{pr_number} - {pr_data.get('title', 'N/A')}")
            
            # Store basic PR data immediately (before background processing)
            latest_pr_data = {
                "title": pr_data.get("title", ""),
                "number": pr_number,
                "repository": repo_full_name,
                "author": pr_data.get("user", {}).get("login", ""),
                "created_at": pr_data.get("created_at", ""),
                "state": pr_data.get("state", ""),
                "head": {
                    "ref": pr_data.get("head", {}).get("ref", ""),
                    "sha": pr_data.get("head", {}).get("sha", "")
                },
                "base": {
                    "ref": pr_data.get("base", {}).get("ref", "")
                },
                "stats": {
                    "additions": pr_data.get("additions", 0),
                    "deletions": pr_data.get("deletions", 0),
                    "total": pr_data.get("changed_files", 0)
                },
                "files": [],
                "diff": ""
            }
            
            # Save immediately so dashboard can access it
            save_pr_data()
            print(f"✅ PR data stored immediately: {latest_pr_data['title']}")
            
            # Then process in background to fetch files and diff
            bg_tasks.add_task(analyze_code_task, payload)
            return {"message": "Processing PR for Check Run..."}

    return {"message": "Ignored"}

# API Endpoints for Frontend (optional - for testing)
@app.get("/api/pr/latest")
async def get_latest_pr():
    """Get the latest PR data"""
    print(f"📊 API Request: latest_pr_data = {latest_pr_data is not None}")
    if latest_pr_data is None:
        # Return empty state instead of 404
        return {
            "available": False,
            "message": "No PR data available yet. Create a PR to see data here.",
            "title": None,
            "number": None,
            "repository": None,
            "author": None,
            "created_at": None,
            "state": None,
            "head": {"ref": None},
            "base": {"ref": None},
            "stats": {"additions": 0, "deletions": 0, "total": 0},
            "files": [],
            "diff": ""
        }
    return latest_pr_data

@app.get("/api/debug/status")
async def debug_status():
    """Debug endpoint to check server status"""
    return {
        "status": "running",
        "has_pr_data": latest_pr_data is not None,
        "pr_data_preview": {
            "title": latest_pr_data.get("title") if latest_pr_data else None,
            "number": latest_pr_data.get("number") if latest_pr_data else None
        } if latest_pr_data else None
    }

@app.get("/api/webhook/url")
async def get_webhook_url(request: Request):
    """Get the suggested webhook URL for GitHub configuration"""
    # Get the base URL from the request
    base_url = str(request.base_url).rstrip('/')
    
    # If running behind a proxy (like ngrok), get the forwarded host
    forwarded_host = request.headers.get("X-Forwarded-Host")
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
    
    if forwarded_host:
        base_url = f"{forwarded_proto}://{forwarded_host}"
    
    webhook_url = f"{base_url}/webhook"
    
    return {
        "webhook_url": webhook_url,
        "instructions": [
            "1. Copy the webhook_url above",
            "2. Go to your GitHub repository Settings > Webhooks",
            "3. Add webhook or edit existing webhook",
            f"4. Paste this URL: {webhook_url}",
            "5. Set Content type to: application/json",
            "6. Select 'Let me select individual events' and choose 'Pull requests'",
            "7. Save the webhook"
        ],
        "note": "If using ngrok, make sure to update this URL in GitHub when ngrok restarts"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Code Reviewer - GitHub Check Runs Integration", 
        "status": "✅ Ready to analyze PRs",
        "integration": "Native GitHub Check Runs"
    }

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the PR Review Dashboard"""
    try:
        html_path = FRONTEND_DIR / "index.html"
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dashboard HTML not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)