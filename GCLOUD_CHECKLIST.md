# Google Cloud Deployment Checklist

## Pre-Deployment (One-time setup)

### Account & Project Setup
- [ ] Create Google Cloud Account at [cloud.google.com](https://cloud.google.com)
- [ ] Create a new Google Cloud Project
- [ ] Note down your `PROJECT_ID`
- [ ] Choose your deployment `REGION` (default: `us-central1`)

### Local Tools Installation
- [ ] Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- [ ] Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [ ] Run `gcloud init` and authenticate
- [ ] Run `docker login` to authenticate Docker

### Enable Required APIs
- [ ] Cloud Run API
- [ ] Cloud SQL Admin API
- [ ] Cloud Build API
- [ ] Artifact Registry API
- [ ] Container Registry API

### Create Cloud SQL Instance
- [ ] Create PostgreSQL 16 instance (`db-f1-micro` tier for testing)
- [ ] Create database (e.g., `jeff_db`)
- [ ] Create database user (e.g., `django_user`)
- [ ] Note the connection name: `PROJECT_ID:REGION:INSTANCE_NAME`

### Set Up Service Account
- [ ] Create service account: `cloud-run-service`
- [ ] Grant `Cloud SQL Client` role to service account
- [ ] Note the service account email

### Set Up Artifact Registry
- [ ] Create Docker repository in Artifact Registry
- [ ] Configure Docker authentication: `gcloud auth configure-docker REGION-docker.pkg.dev`

## Deployment Steps

### 1. Prepare Environment Variables
- [ ] Copy `.env.gcloud` template
- [ ] Fill in all required variables:
  - `SECRET_KEY` (generate a new one)
  - `CLOUD_SQL_CONNECTION_NAME`
  - `DB_USER`, `DB_PASS`, `DB_NAME`
  - All API keys (OpenAI, Gemini, Anthropic, Twilio, Paynow)
  - `CORS_ALLOWED_ORIGINS` (your frontend URL)

### 2. Build and Push Docker Image
- [ ] Run: `docker build -t REGION-docker.pkg.dev/PROJECT_ID/docker-repo/jeff-backend:latest .`
- [ ] Run: `docker push REGION-docker.pkg.dev/PROJECT_ID/docker-repo/jeff-backend:latest`

### 3. Deploy to Cloud Run
**Option A: Use PowerShell Script (Windows)**
```powershell
.\deploy-gcloud.ps1 -ProjectId "YOUR_PROJECT_ID" -Region "us-central1"
```

**Option B: Use Bash Script (Linux/Mac)**
```bash
chmod +x deploy-gcloud.sh
./deploy-gcloud.sh YOUR_PROJECT_ID us-central1
```

**Option C: Manual Deployment**
```bash
gcloud run deploy jeff-backend \
    --image=REGION-docker.pkg.dev/PROJECT_ID/docker-repo/jeff-backend:latest \
    --platform=managed \
    --region=REGION \
    --allow-unauthenticated \
    --memory=1Gi \
    --cpu=1 \
    --service-account=cloud-run-service@PROJECT_ID.iam.gserviceaccount.com \
    --add-cloudsql-instances=PROJECT_ID:REGION:INSTANCE_NAME \
    --set-env-vars="USE_CLOUD_SQL=true,DEBUG=false,CLOUD_SQL_CONNECTION_NAME=PROJECT_ID:REGION:INSTANCE_NAME,DB_USER=django_user,DB_PASS=YOUR_DB_PASSWORD,DB_NAME=jeff_db,DB_SOCKET_DIR=/cloudsql"
```

### 4. Run Database Migrations
After deployment, create a one-time migration job:

```bash
gcloud run jobs create jeff-migrate \
    --image=REGION-docker.pkg.dev/PROJECT_ID/docker-repo/jeff-backend:latest \
    --service-account=cloud-run-service@PROJECT_ID.iam.gserviceaccount.com \
    --add-cloudsql-instances=PROJECT_ID:REGION:INSTANCE_NAME \
    --set-env-vars="USE_CLOUD_SQL=true,CLOUD_SQL_CONNECTION_NAME=PROJECT_ID:REGION:INSTANCE_NAME,DB_USER=django_user,DB_PASS=YOUR_DB_PASSWORD,DB_NAME=jeff_db,DB_SOCKET_DIR=/cloudsql" \
    --region=REGION

# Execute the migration job
gcloud run jobs execute jeff-migrate --region=REGION
```

Or use Docker locally:
```bash
docker run -e USE_CLOUD_SQL=true \
    -e CLOUD_SQL_CONNECTION_NAME=PROJECT_ID:REGION:INSTANCE_NAME \
    -e DB_USER=django_user \
    -e DB_PASS=YOUR_DB_PASSWORD \
    -e DB_NAME=jeff_db \
    REGION-docker.pkg.dev/PROJECT_ID/docker-repo/jeff-backend:latest \
    python manage.py migrate
```

## Post-Deployment

### Verify Deployment
- [ ] Get service URL: `gcloud run services describe jeff-backend --region=REGION --format='value(status.url)'`
- [ ] Test API endpoint: Visit the URL in browser or use curl
- [ ] Check logs: `gcloud run services logs read jeff-backend --region=REGION --limit=50`

### Update Frontend
- [ ] Get your backend service URL
- [ ] Update frontend `.env.local`:
  ```
  NEXT_PUBLIC_API_URL=https://jeff-backend-XXXXX.REGION.run.app
  ```
- [ ] Update `CORS_ALLOWED_ORIGINS` in Django settings if needed

### Set Up Custom Domain (Optional)
- [ ] Create DNS A record or CNAME pointing to Cloud Run
- [ ] Run: `gcloud run domain-mappings create --service=jeff-backend --domain=api.yourdomain.com --region=REGION`
- [ ] Wait for SSL certificate provisioning (5-10 minutes)

### Configure Monitoring
- [ ] Set up Cloud Logging alerts
- [ ] Configure Cloud Monitoring dashboards
- [ ] Set up error notifications

## Troubleshooting

### Common Issues

**1. Database Connection Errors**
```bash
# Verify Cloud SQL instance is running
gcloud sql instances describe INSTANCE_NAME

# Check service account has Cloud SQL Client role
gcloud projects get-iam-policy PROJECT_ID --flatten="bindings[].members" --filter="bindings.members:serviceAccount:cloud-run-service*"
```

**2. Deploy Command Not Found**
```bash
# Verify gcloud is installed and authenticated
gcloud --version
gcloud auth list
```

**3. Image Push Failed**
```bash
# Verify Docker authentication
gcloud auth configure-docker REGION-docker.pkg.dev

# Verify repository exists
gcloud artifacts repositories list --location=REGION
```

**4. Service Won't Start**
```bash
# Check recent logs
gcloud run services logs read jeff-backend --region=REGION --limit=100

# Check environment variables are set
gcloud run services describe jeff-backend --region=REGION
```

**5. Migrations Won't Run**
- Ensure service account has Cloud SQL Client role
- Check DB credentials in environment variables
- Verify Cloud SQL instance is publicly accessible or in same VPC

## Cost Estimation

**Estimated Monthly Costs (for testing):**
- Cloud Run: ~$0.40 (1GB memory, 100k requests)
- Cloud SQL: ~$15-20 (db-f1-micro, minimum)
- Cloud Storage (if used): Variable
- **Total: ~$15-30/month for testing setup**

## Rollback Instructions

If deployment fails or you need to go back to Render:

```bash
# Delete Cloud Run service
gcloud run services delete jeff-backend --region=REGION

# Or just deploy the old version again
git push origin main
# Redeploy from Render dashboard
```

## Useful Commands Reference

```bash
# View all deployments
gcloud run services list --region=REGION

# View service details
gcloud run services describe jeff-backend --region=REGION

# Stream logs in real-time
gcloud run services logs read jeff-backend --region=REGION --follow

# List Cloud SQL instances
gcloud sql instances list

# Connect to Cloud SQL
gcloud sql connect INSTANCE_NAME --user=django_user

# Delete service
gcloud run services delete jeff-backend --region=REGION

# Update service with new image
gcloud run deploy jeff-backend \
    --image=NEW_IMAGE_NAME \
    --region=REGION
```

## Support & Documentation

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Django Deployment Guide](https://docs.djangoproject.com/en/5.2/howto/deployment/)
- [gcloud CLI Reference](https://cloud.google.com/sdk/gcloud/reference)

---

**Note:** Keep your `.env.gcloud` file secure and never commit it to git!
