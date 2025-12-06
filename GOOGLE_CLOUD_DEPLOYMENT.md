# Google Cloud Run Deployment Guide

This guide walks you through deploying your Django backend to Google Cloud Run.

## Prerequisites

1. **Google Cloud Account** - Create one at [cloud.google.com](https://cloud.google.com)
2. **gcloud CLI** - [Install it](https://cloud.google.com/sdk/docs/install)
3. **Docker** - [Install Docker Desktop](https://www.docker.com/products/docker-desktop)

## Step 1: Create a Google Cloud Project

```bash
# Set your project ID
$projectId = "jeff-backend-project"
$region = "us-central1"  # or your preferred region

# Create project
gcloud projects create $projectId

# Set as active project
gcloud config set project $projectId
```

## Step 2: Enable Required APIs

```bash
# Enable Cloud Run, Cloud SQL Admin, Cloud Build, and Artifact Registry
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable container.googleapis.com
```

## Step 3: Create Cloud SQL Instance (PostgreSQL)

```bash
# Create a PostgreSQL instance
$instanceName = "jeff-postgres"
$dbName = "jeff_db"
$dbUser = "django_user"
$dbPassword = "YourSecurePassword123!"  # Change this!

gcloud sql instances create $instanceName `
    --database-version=POSTGRES_16 `
    --tier=db-f1-micro `
    --region=$region `
    --availability-type=regional `
    --enable-bin-log=false `
    --no-backup

# Wait for instance to be ready (2-3 minutes)
gcloud sql operations list

# Create database
gcloud sql databases create $dbName --instance=$instanceName

# Create database user
gcloud sql users create $dbUser --instance=$instanceName --password=$dbPassword
```

## Step 4: Configure Environment Variables

Create a `.env.gcloud` file in your `backend` directory with:

```env
DEBUG=false
SECRET_KEY=your-secret-key-here
USE_CLOUD_SQL=true
CLOUD_SQL_CONNECTION_NAME=PROJECT_ID:REGION:INSTANCE_NAME
DB_USER=django_user
DB_PASS=YourSecurePassword123!
DB_NAME=jeff_db
DB_SOCKET_DIR=/cloudsql
ALLOWED_HOSTS=*.run.app,your-domain.com
CORS_ALLOWED_ORIGINS=https://jeff-frontend.vercel.app
OPENAI_API_KEY=your-openai-key
GEMINI_API_KEY=your-gemini-key
ANTHROPIC_API_KEY=your-anthropic-key
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_WHATSAPP_NUMBER=your-whatsapp-number
PAYNOW_INTEGRATION_ID=your-paynow-id
PAYNOW_INTEGRATION_KEY=your-paynow-key
```

## Step 5: Create Service Account for Cloud SQL

```bash
# Create service account
$serviceAccount = "cloud-run-service"
gcloud iam service-accounts create $serviceAccount `
    --display-name="Cloud Run Service Account"

# Grant Cloud SQL Client role
gcloud projects add-iam-policy-binding $projectId `
    --member="serviceAccount:$serviceAccount@$projectId.iam.gserviceaccount.com" `
    --role="roles/cloudsql.client"
```

## Step 6: Set Up Artifact Registry

```bash
# Create a Docker repository
gcloud artifacts repositories create docker-repo `
    --repository-format=docker `
    --location=$region `
    --description="Docker repository for Jeff backend"

# Configure Docker authentication
gcloud auth configure-docker "$region-docker.pkg.dev"
```

## Step 7: Build and Push Docker Image

```bash
# Set image name
$imageName = "$region-docker.pkg.dev/$projectId/docker-repo/jeff-backend:latest"

# Build Docker image (from backend directory)
cd backend
docker build -t $imageName .
cd ..

# Push to Artifact Registry
docker push $imageName
```

## Step 8: Deploy to Cloud Run

```bash
# Deploy the service
gcloud run deploy jeff-backend `
    --image=$imageName `
    --platform=managed `
    --region=$region `
    --allow-unauthenticated `
    --memory=1Gi `
    --cpu=1 `
    --timeout=3600 `
    --max-instances=10 `
    --min-instances=0 `
    --service-account="$serviceAccount@$projectId.iam.gserviceaccount.com" `
    --add-cloudsql-instances="$projectId:$region:$instanceName" `
    --set-env-vars="USE_CLOUD_SQL=true,DEBUG=false,CLOUD_SQL_CONNECTION_NAME=$projectId:$region:$instanceName,DB_USER=$dbUser,DB_PASS=$dbPassword,DB_NAME=$dbName,DB_SOCKET_DIR=/cloudsql" `
    --ingress=all
```

## Step 9: Run Database Migrations

```bash
# Get the Cloud Run service URL
$serviceUrl = gcloud run services describe jeff-backend --region=$region --format='value(status.url)'

# SSH into the service (via Cloud Build job)
# Option 1: Run migrations via one-off job
gcloud run jobs create jeff-migrate `
    --image=$imageName `
    --service-account="$serviceAccount@$projectId.iam.gserviceaccount.com" `
    --add-cloudsql-instances="$projectId:$region:$instanceName" `
    --set-env-vars="USE_CLOUD_SQL=true,DEBUG=false,CLOUD_SQL_CONNECTION_NAME=$projectId:$region:$instanceName,DB_USER=$dbUser,DB_PASS=$dbPassword,DB_NAME=$dbName,DB_SOCKET_DIR=/cloudsql" `
    --region=$region

# Or run directly after deployment:
$migrationImage = "$region-docker.pkg.dev/$projectId/docker-repo/jeff-backend-migrate:latest"
docker run --rm $migrationImage python manage.py migrate
```

## Step 10: Set Up Custom Domain (Optional)

```bash
# Map your domain to Cloud Run
gcloud run domain-mappings create `
    --service=jeff-backend `
    --domain=api.yourdomainhere.com `
    --region=$region

# Note: You'll need to point your DNS records to Cloud Run's IP
# Check the DNS records via:
gcloud run domain-mappings describe api.yourdomainhere.com --region=$region
```

## Step 11: Configure CORS and Update Frontend

Update your frontend's `.env.local`:

```env
NEXT_PUBLIC_API_URL=https://jeff-backend-<service-hash>.<region>.run.app
# or if using custom domain:
NEXT_PUBLIC_API_URL=https://api.yourdomainhere.com
```

## Monitoring and Logs

```bash
# View logs
gcloud run services logs read jeff-backend --region=$region --limit=50

# View detailed logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=jeff-backend" --limit 50 --format json

# Monitor in Cloud Console
# https://console.cloud.google.com/run
```

## Rollback to Previous Version

```bash
# If something goes wrong, you can quickly switch to the previous image
gcloud run deploy jeff-backend `
    --image=<previous-image-hash> `
    --region=$region
```

## Cost Optimization Tips

1. **Use auto-scaling**: Cloud Run charges only when requests are being processed
2. **Set minimum instances to 0**: Pay-per-use model (small cold-start delay)
3. **Use Cloud SQL Autopause**: Enable to pause PostgreSQL during inactivity
4. **Monitor usage**: Check the Cloud Console for pricing

## Troubleshooting

### Database Connection Issues
```bash
# Check if Cloud SQL Proxy can reach the database
gcloud sql connect $instanceName --user=$dbUser

# Verify service account has Cloud SQL Client role
gcloud projects get-iam-policy $projectId --flatten="bindings[].members" --filter="bindings.members:serviceAccount:$serviceAccount*"
```

### Permission Denied Errors
```bash
# Make sure service account has necessary roles
gcloud projects add-iam-policy-binding $projectId `
    --member="serviceAccount:$serviceAccount@$projectId.iam.gserviceaccount.com" `
    --role="roles/cloudsql.client"
```

### Environment Variables Not Loading
```bash
# List current environment variables
gcloud run services describe jeff-backend --region=$region --format='value(spec.template.spec.containers[0].env)'
```

## Next Steps

1. Set up **Cloud Storage** for media uploads (optional)
2. Configure **Cloud CDN** for static files optimization
3. Set up **Cloud Monitoring** and **Cloud Alerting**
4. Enable **Firestore** or **Datastore** for caching (optional)

## Switching Back to Render (If Needed)

If you need to go back to Render:
1. The old `render.yaml` is preserved
2. Push changes to GitHub
3. Redeploy from Render dashboard

Good luck with your deployment! 🚀
