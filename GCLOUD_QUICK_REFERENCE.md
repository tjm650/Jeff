# 🚀 Google Cloud Run - Quick Reference Card

## 📋 Pre-Deployment Checklist (Complete These First!)

```
☐ Create Google Cloud Project
☐ Install gcloud CLI and Docker Desktop
☐ Create PostgreSQL Cloud SQL instance
☐ Create database and user in Cloud SQL
☐ Create Docker repository in Artifact Registry
☐ Create service account with Cloud SQL Client role
```

## 🚀 Deploy in 3 Steps (Windows)

### Step 1: Prepare
```powershell
# Copy and fill in environment variables
Copy-Item .env.gcloud.example .env
# Edit .env with your actual values
```

### Step 2: Build & Push
```powershell
docker build -t us-central1-docker.pkg.dev/PROJECT_ID/docker-repo/jeff-backend:latest .
docker push us-central1-docker.pkg.dev/PROJECT_ID/docker-repo/jeff-backend:latest
```

### Step 3: Deploy
```powershell
.\deploy-gcloud.ps1 -ProjectId "your-project-id" -Region "us-central1"
```

## 🔑 Key Environment Variables

| Variable | Example | Purpose |
|----------|---------|---------|
| `CLOUD_SQL_CONNECTION_NAME` | `my-project:us-central1:jeff-postgres` | Database connection |
| `DB_USER` | `django_user` | Database username |
| `DB_PASS` | `SecurePassword123!` | Database password |
| `DB_NAME` | `jeff_db` | Database name |
| `USE_CLOUD_SQL` | `true` | Enables Cloud SQL mode |
| `DEBUG` | `false` | Production mode |

## 📦 Architecture

```
┌─────────────────────────────────────────────┐
│         Google Cloud Run                     │
│  (jeff-backend service)                      │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │ Container                              │  │
│  │ - Python 3.13.4                        │  │
│  │ - Django 5.2.8                         │  │
│  │ - Gunicorn                             │  │
│  │ - All dependencies                     │  │
│  └────────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
                    ↓
        ┌──────────────────────┐
        │  Cloud SQL           │
        │  PostgreSQL 16       │
        │  (jeff_db)           │
        └──────────────────────┘
```

## 🛠️ Common Commands

| Task | Command |
|------|---------|
| **View logs** | `gcloud run services logs read jeff-backend --region=us-central1 --limit=50` |
| **Get service URL** | `gcloud run services describe jeff-backend --region=us-central1 --format='value(status.url)'` |
| **Deploy new version** | `gcloud run deploy jeff-backend --image=IMAGE_URL --region=us-central1` |
| **Connect to database** | `gcloud sql connect INSTANCE_NAME --user=django_user` |
| **Delete service** | `gcloud run services delete jeff-backend --region=us-central1` |

## 📊 Cost Tracker

**First Month Estimate:**
- Cloud Run: ~$0.50 (100k requests)
- Cloud SQL: ~$20 (db-f1-micro)
- **Total: ~$20-25**

**Free Tier Benefits:**
- 2M Cloud Run requests/month (free)
- 300 hours Cloud SQL/month (first 3 months)
- 100GB Cloud Storage/month (free)

## ⚠️ Important Notes

1. **Never commit `.env`** - It contains secrets!
2. **SQLite still works locally** - No changes to local development
3. **Database runs migrations on startup** - Check logs if migrations fail
4. **Render.yaml is preserved** - Easy fallback if needed

## 🔄 Rollback to Render

```bash
# If anything goes wrong, just push to GitHub
git push origin main

# Then redeploy from Render dashboard
# All your original setup is unchanged!
```

## 📚 Documentation Files Created

| File | Purpose |
|------|---------|
| `GOOGLE_CLOUD_README.md` | Overview and summary |
| `GOOGLE_CLOUD_DEPLOYMENT.md` | Detailed step-by-step guide |
| `GCLOUD_CHECKLIST.md` | Interactive checklist |
| `Dockerfile` | Container configuration |
| `.env.gcloud.example` | Environment variables template |
| `deploy-gcloud.ps1` | Automated deployment script |

## ✅ Deployment Verification

After deployment, verify everything works:

```bash
# 1. Get service URL
gcloud run services describe jeff-backend --region=us-central1

# 2. Test the API
curl https://jeff-backend-XXXXX.us-central1.run.app/api/

# 3. Check database connection
# Visit: https://console.cloud.google.com/sql

# 4. Monitor logs
gcloud run services logs read jeff-backend --region=us-central1
```

## 🆘 Troubleshooting Quick Links

| Issue | Solution |
|-------|----------|
| Can't push image | Run: `gcloud auth configure-docker REGION-docker.pkg.dev` |
| Database won't connect | Verify Cloud SQL instance exists and service account has Client role |
| Migrations won't run | Check logs, ensure DB credentials in environment variables are correct |
| Can't see service URL | Run: `gcloud run services describe jeff-backend` after deployment |
| High costs? | Set min instances to 0, use db-f1-micro tier for Cloud SQL |

---

**Ready to deploy?** Start with `GCLOUD_CHECKLIST.md` ✨
