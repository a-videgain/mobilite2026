#!/bin/bash
# Déploiement sur Cloud Run (à lancer depuis Cloud Shell, dans le dossier du dépôt).
# Usage : bash deploy.sh            -> réglage normal (hors séance)
#         bash deploy.sh seance     -> réglage pour une séance avec ~150 étudiants
set -e
REGION=europe-west9
SERVICE=mobilite

if [ "$1" = "seance" ]; then
  MIN=12; MAX=30; CPU=2; CONC=8
else
  MIN=0;  MAX=20; CPU=1; CONC=10
fi

gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory 2Gi --cpu "$CPU" \
  --concurrency "$CONC" \
  --min-instances "$MIN" --max-instances "$MAX" \
  --timeout 3600 \
  --session-affinity
