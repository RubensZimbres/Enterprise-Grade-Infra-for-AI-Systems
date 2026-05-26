#!/bin/bash
echo "Validating naming conventions for Terraform resources..."

legacy_found=0
while IFS= read -r line; do
  file=$(echo "$line" | cut -d: -f1)
  match=$(echo "$line" | cut -d: -f2-)
  
  # Extract the value inside quotes
  val=$(echo "$match" | grep -o '"[^"]*"' | tr -d '"')
  
  # Ignore empty or dynamically interpolated strings that start with ${
  # Ignore uppercase values (likely environment variables)
  if [[ "$val" != \${* ]] && [[ "$val" != *[A-Z]* ]] && [[ "$val" == *_* ]]; then
    # Ignore specific things like "cloudsql.iam_authentication" or "user/error_count"
    if [[ "$val" != *"."* ]] && [[ "$val" != *"/"* ]]; then
      echo "WARNING: Legacy naming discrepancy detected in $file -> '$val'. Names should use hyphens instead of underscores."
      legacy_found=1
    fi
  fi
done < <(grep -rnE '^\s*(name|account_id)\s*=\s*"[^"]+"' terraform/ | grep -v 'google_cloudbuild_trigger' | grep -v 'google_service_account' | grep -v 'google_project_iam_member')

if [ $legacy_found -eq 1 ]; then
  echo "Validation completed with legacy naming warnings flagged for remediation."
else
  echo "All resource names follow standard conventions."
fi

exit 0
