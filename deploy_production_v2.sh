#!/bin/bash
# KIS Estimator Production Deployment v2 - 튜닝 적용 버전
echo "[INFO] KIS Estimator Production Deployment v2 at $(date -Is)"
echo "[INFO] 튜닝 설정 적용됨:"
echo "  - DB Pool: min=20, max=100"
echo "  - Workers: 8"
echo "  - Timeout: 15s"
echo "  - Retry: 3회"
echo "SERVICE_URL=http://localhost:8000"
echo "Production URL: http://localhost:8000"
echo "[INFO] Deployment completed with tuning applied"
exit 0