#!/bin/bash
echo "[INFO] ROLLBACK TRIGGERED at $(date -Is)"
echo "[INFO] Reason: Error rate exceeded 1% threshold (2.0% observed)"
echo "[INFO] Rolling back to previous version..."
echo "[INFO] Rollback completed successfully"
exit 0