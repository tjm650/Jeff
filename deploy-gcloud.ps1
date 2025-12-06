# Google Cloud Run Deployment Script (PowerShell)
# Usage: .\deploy-gcloud.ps1 -ProjectId <project-id> -Region <region>

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-central1",
    
    [Parameter(Mandatory=$false)]
    [string]$ServiceName = "jeff-backend"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying to Google Cloud Run" -ForegroundColor Green
Write-Host "Project: $ProjectId" -ForegroundColor Cyan
Write-Host "Region: $Region" -ForegroundColor Cyan
Write-Host ""

# Set gcloud project
Write-Host "📋 Setting gcloud project..." -ForegroundColor Yellow
gcloud config set project $ProjectId

# Enable APIs
Write-Host "🔧 Enabling APIs..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Authenticate Docker
Write-Host "🔑 Configuring Docker authentication..." -ForegroundColor Yellow
gcloud auth configure-docker "$Region-docker.pkg.dev"

# Build image
Write-Host "🏗️  Building Docker image..." -ForegroundColor Yellow
$ImageName = "$Region-docker.pkg.dev/$ProjectId/docker-repo/${ServiceName}:latest"
Push-Location backend
docker build -t $ImageName .
Pop-Location

# Push image
Write-Host "📦 Pushing image to Artifact Registry..." -ForegroundColor Yellow
docker push $ImageName

# Get service account
$ServiceAccount = "cloud-run-service@$ProjectId.iam.gserviceaccount.com"

# Get Cloud SQL connection name
Write-Host ""
Write-Host "ℹ️  Cloud SQL connection name format: PROJECT_ID:REGION:INSTANCE_NAME" -ForegroundColor Blue
$CloudSqlConnectionName = Read-Host "Enter your Cloud SQL connection name"

# Deploy
Write-Host ""
Write-Host "🚀 Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
    --image=$ImageName `
    --platform=managed `
    --region=$Region `
    --allow-unauthenticated `
    --memory=1Gi `
    --cpu=1 `
    --timeout=3600 `
    --max-instances=10 `
    --min-instances=0 `
    --service-account=$ServiceAccount `
    --add-cloudsql-instances=$CloudSqlConnectionName `
    --set-env-vars="USE_CLOUD_SQL=true,DEBUG=false,CLOUD_SQL_CONNECTION_NAME=$CloudSqlConnectionName,DB_SOCKET_DIR=/cloudsql" `
    --ingress=all

# Get the service URL
$ServiceUrl = gcloud run services describe $ServiceName --region=$Region --format='value(status.url)'

Write-Host ""
Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host "Service URL: $ServiceUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Update your frontend NEXT_PUBLIC_API_URL to: $ServiceUrl"
Write-Host "2. Set up custom domain (optional): gcloud run domain-mappings create --service=$ServiceName --domain=your-domain.com --region=$Region"
Write-Host "3. Monitor logs: gcloud run services logs read $ServiceName --region=$Region --limit=50"
