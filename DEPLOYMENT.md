# Free Online Hosting & Deployment Guide

This guide explains how to host your **D&D 2024 Character Creator** online for free so you can share it with friends.

---

## Recommended: 100% Free Hosting on Render (Render.com)

Render provides a **free Web Service tier** that can host both the Python Flask API and the compiled React frontend in a single unified service. No credit card is required.

### Why Render?
- **Zero Cost**: Free plan with 750 free hours/month (plenty for personal/friend use).
- **Automated CI/CD**: Automatically builds and deploys whenever you push to GitHub.
- **Unified Domain**: Front-end and API share the exact same origin (no CORS configuration needed).
- **Free SSL**: Comes with automatic `https://<your-app-name>.onrender.com`.

*(Note: Free instances spin down after 15 minutes of inactivity and take ~30–45 seconds to wake up on the first visit.)*

---

### Step-by-Step Deployment on Render

#### Step 1: Push Your Code to GitHub
1. Create a repository on [GitHub](https://github.com/new).
2. Push your code:
   ```bash
   git add .
   git commit -m "Configure free online hosting and supplements"
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git branch -M main
   git push -u origin main
   ```

#### Step 2: Sign Up on Render
1. Go to [https://render.com](https://render.com) and click **Sign Up**.
2. Select **Continue with GitHub** to connect your account.

#### Step 3: Create a Web Service

**Method A — Using Blueprint (`render.yaml`) (Easiest)**:
1. In Render Dashboard, click **New +** -> **Blueprint**.
2. Select your repository.
3. Render will read `render.yaml` and configure everything automatically!
4. Click **Apply**.

**Method B — Manual Setup**:
1. In Render Dashboard, click **New +** -> **Web Service**.
2. Connect your GitHub repository.
3. Configure the settings:
   - **Name**: `dnd-character-creator` (or your preferred name)
   - **Environment**: `Python 3`
   - **Branch**: `main`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: `Free`
4. Under **Environment Variables**, add:
   - `FLASK_ENV`: `production`
   - `PYTHON_VERSION`: `3.11.9`
5. Click **Create Web Service**.

#### Step 4: Access Your Live Website
Render will run `./build.sh` (installing Python libraries and building the React SPA) and start the server. Once the build finishes, your site will be live at:
```
https://<your-app-name>.onrender.com
```
Share that link with your friends!

---

## Alternative 1: Koyeb (koyeb.com)

Koyeb offers a generous free tier (Nano instance) that runs continuous containers with fast edge routing.

1. Create a free account at [koyeb.com](https://www.koyeb.com).
2. Click **Create App** -> **GitHub**.
3. Select this repository.
4. Choose **Dockerfile** as the build method (the repo includes a production multi-stage `Dockerfile`).
5. Set port to `5000`.
6. Click **Deploy**.

---

## Alternative 2: Local Docker Testing

If you want to test the production container locally before deploying:

```bash
# Build the Docker image
docker build -t dnd-character-creator .

# Run the container on port 5000
docker run -p 5000:5000 dnd-character-creator
```
Then visit `http://localhost:5000`.
