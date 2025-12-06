#!/bin/bash
# Google Cloud Run Deployment Script
# Usage: ./deploy-gcloud.sh <project-id> <region>

set -e

PROJECT_ID=${1:-""}
REGION=${2:-"us-central1"}
SERVICE_NAME="jeff-backend"

if [ -z "$PROJECT_ID" ]; then
    echo "Usage: ./deploy-gcloud.sh <project-id> [region]"
    echo "Example: ./deploy-gcloud.sh my-project us-central1"
    exit 1
fi

echo "🚀 Deploying to Google Cloud Run"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Set gcloud project
echo "📋 Setting gcloud project..."
gcloud config set project "$PROJECT_ID"

# Enable APIs
echo "🔧 Enabling APIs..."
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Authenticate Docker
echo "🔑 Configuring Docker authentication..."
gcloud auth configure-docker "$REGION-docker.pkg.dev"

# Build image
echo "🏗️  Building Docker image..."
IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/docker-repo/$SERVICE_NAME:latest"
cd backend
docker build -t "$IMAGE_NAME" .
cd ..

# Push image
echo "📦 Pushing image to Artifact Registry..."
docker push "$IMAGE_NAME"

# Get service account
SERVICE_ACCOUNT="cloud-run-service@$PROJECT_ID.iam.gserviceaccount.com"

# Get Cloud SQL connection name
echo ""
echo "ℹ️  Cloud SQL connection name format: PROJECT_ID:REGION:INSTANCE_NAME"
read -p "Enter your Cloud SQL connection name: " CLOUD_SQL_CONNECTION_NAME

# Deploy
echo ""
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --image="$IMAGE_NAME" \
    --platform=managed \
    --region="$REGION" \
    --allow-unauthenticated \
    --memory=1Gi \
    --cpu=1 \
    --timeout=3600 \
    --max-instances=10 \
    --min-instances=0 \
    --service-account="$SERVICE_ACCOUNT" \
    --add-cloudsql-instances="$CLOUD_SQL_CONNECTION_NAME" \
    --set-env-vars="USE_CLOUD_SQL=true,DEBUG=false,CLOUD_SQL_CONNECTION_NAME=$CLOUD_SQL_CONNECTION_NAME,DB_SOCKET_DIR=/cloudsql" \
    --ingress=all

# Get the service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format='value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo "Service URL: $SERVICE_URL"
echo ""
echo "Next steps:"
echo "1. Update your frontend NEXT_PUBLIC_API_URL to: $SERVICE_URL"
echo "2. Set up custom domain (optional): gcloud run domain-mappings create --service=$SERVICE_NAME --domain=your-domain.com --region=$REGION"
echo "3. Monitor logs: gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=50"
