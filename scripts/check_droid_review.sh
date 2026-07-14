#!/bin/bash
# Check droid-review status for the current PR/commit
# Exit 0 if droid-review passed, exit 1 if failed or not found
# Skip gracefully for non-PR events (push to main)

set -e

# Input: GitHub event name, repository, commit SHA, GitHub token
EVENT_NAME="${1}"
REPOSITORY="${2}"
COMMIT_SHA="${3}"
GH_TOKEN="${4}"

# For push events (not pull_request), skip gracefully
if [ "$EVENT_NAME" != "pull_request" ]; then
  echo "Not a pull_request event, skipping droid-review check"
  exit 0
fi

# Query check runs for this commit
echo "Querying check runs for commit $COMMIT_SHA in $REPOSITORY..."
CHECKS=$(curl -s -H "Authorization: token $GH_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${REPOSITORY}/commits/${COMMIT_SHA}/check-runs?check_name=Droid+Auto+Review")

# Extract the conclusion of the first matching check
STATUS=$(echo "$CHECKS" | jq -r '.check_runs[0].conclusion // "pending"')

echo "droid-review conclusion: $STATUS"

# Decision logic
if [ "$STATUS" = "success" ]; then
  echo "✓ droid-review passed"
  exit 0
elif [ "$STATUS" = "failure" ]; then
  echo "✗ FAIL: droid-review failed"
  exit 1
elif [ "$STATUS" = "pending" ] || [ "$STATUS" = "null" ] || [ -z "$STATUS" ]; then
  echo "⚠ droid-review not yet complete or not found"
  echo "This may indicate:"
  echo "  - droid-review is still running (wait and retry)"
  echo "  - droid-review was not triggered (check workflow configuration)"
  echo "  - droid-review check run was not created"
  exit 1
else
  echo "? Unknown droid-review status: $STATUS"
  exit 1
fi
