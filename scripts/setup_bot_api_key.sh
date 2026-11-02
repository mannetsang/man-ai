#!/bin/bash
# Bot API Key Setup
# 
# This script documents the one-time setup steps for the bot API key feature.
# Run these commands as a project Owner or someone with sufficient GCP permissions.

PROJECT_ID="shp-ai-bot-2026"
SECRET_NAME="chat-assistant-bot-api-key"
SERVICE_ACCOUNT="chat-assistant@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== Bot API Key Setup ==="
echo ""
echo "This will:"
echo "  1. Generate a secure 32-byte (64-char hex) API key"
echo "  2. Store it in Google Secret Manager as '${SECRET_NAME}'"
echo "  3. Grant the Cloud Run service account read access to the secret"
echo ""

# Check if running as dry-run
if [[ "$1" == "--dry-run" ]]; then
    echo "DRY RUN MODE - no changes will be made"
    echo ""
fi

# Step 1: Generate and create the secret
echo "Step 1: Generate and create the secret"
echo "---------------------------------------"
echo ""
echo "Command to create the secret:"
echo ""
echo "  openssl rand -hex 32 | gcloud secrets create ${SECRET_NAME} \\"
echo "    --project=${PROJECT_ID} \\"
echo "    --replication-policy=automatic \\"
echo "    --data-file=-"
echo ""

if [[ "$1" != "--dry-run" ]]; then
    read -p "Create the secret now? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        openssl rand -hex 32 | gcloud secrets create ${SECRET_NAME} \
            --project=${PROJECT_ID} \
            --replication-policy=automatic \
            --data-file=-
        
        if [[ $? -eq 0 ]]; then
            echo "✓ Secret created successfully"
        else
            echo "✗ Failed to create secret (may already exist)"
            echo "  To update: openssl rand -hex 32 | gcloud secrets versions add ${SECRET_NAME} --data-file=-"
        fi
    else
        echo "Skipped."
    fi
    echo ""
fi

# Step 2: Grant service account access
echo "Step 2: Grant service account access to the secret"
echo "---------------------------------------------------"
echo ""
echo "Command to grant access:"
echo ""
echo "  gcloud secrets add-iam-policy-binding ${SECRET_NAME} \\"
echo "    --project=${PROJECT_ID} \\"
echo "    --member=\"serviceAccount:${SERVICE_ACCOUNT}\" \\"
echo "    --role=\"roles/secretmanager.secretAccessor\""
echo ""

if [[ "$1" != "--dry-run" ]]; then
    read -p "Grant access now? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        gcloud secrets add-iam-policy-binding ${SECRET_NAME} \
            --project=${PROJECT_ID} \
            --member="serviceAccount:${SERVICE_ACCOUNT}" \
            --role="roles/secretmanager.secretAccessor"
        
        if [[ $? -eq 0 ]]; then
            echo "✓ Access granted successfully"
        else
            echo "✗ Failed to grant access"
        fi
    else
        echo "Skipped."
    fi
    echo ""
fi

# Step 3: Retrieve the key for bot configuration
echo "Step 3: Retrieve the key for bot configuration"
echo "----------------------------------------------"
echo ""
echo "To retrieve the key for configuring the bot (Jules):"
echo ""
echo "  gcloud secrets versions access latest \\"
echo "    --project=${PROJECT_ID} \\"
echo "    --secret=${SECRET_NAME}"
echo ""
echo "IMPORTANT: Keep this key secret. Do not log it, commit it, or share it publicly."
echo ""

if [[ "$1" != "--dry-run" ]]; then
    read -p "Display the key now? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "API Key:"
        gcloud secrets versions access latest \
            --project=${PROJECT_ID} \
            --secret=${SECRET_NAME}
        echo ""
    else
        echo "Skipped."
    fi
    echo ""
fi

# Step 4: Rotate the key (optional)
echo "Step 4: Key rotation (optional)"
echo "-------------------------------"
echo ""
echo "To rotate the key (generate a new version):"
echo ""
echo "  openssl rand -hex 32 | gcloud secrets versions add ${SECRET_NAME} \\"
echo "    --project=${PROJECT_ID} \\"
echo "    --data-file=-"
echo ""
echo "The app will pick up the new key within 5 minutes (cache refresh interval)."
echo ""

echo "=== Setup Complete ==="
echo ""
echo "The bot (Jules) can now authenticate using:"
echo "  Authorization: Bearer <API_KEY>"
echo ""
echo "See scripts/bot_api_examples.sh for usage examples."
