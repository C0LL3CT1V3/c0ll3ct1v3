# Client bugtracker (SAM)

Screenshot reports from the React widget land here: HTTP API `POST /reports` → Lambda → S3 + GitHub Issues.

Region: **us-east-2**.

GitHub's image proxy cannot fetch private/presigned S3 URLs (it shows **Forbidden**). The `reports/` prefix is therefore world-readable over HTTPS. Keys are UUIDs and objects expire after 90 days. The vaults media bucket stays private.

## One-time AWS / GitHub

1. In the GitHub repo, create labels: `source:client`, `type:bug`, `type:feature-request`.
2. Create a PAT (or GitHub App token) with `issues:write` on that repo only.
3. Store it in Secrets Manager:

```bash
aws secretsmanager create-secret \
  --region us-east-2 \
  --name c0ll3ct1v3/bugtracker/github \
  --secret-string '{"token":"ghp_...","owner":"YOUR_ORG","repo":"c0ll3ct1v3"}'
```

4. Deploy:

```bash
cd infrastructure/bugtracker
sam build
sam deploy --guided --region us-east-2 \
  --parameter-overrides GitHubSecretArn=arn:aws:secretsmanager:us-east-2:756090160994:secret:c0ll3ct1v3/bugtracker/github-GkS82x
```

Optional bucket name: `ReportsBucketName=c0ll3ct1v3-bug-reports` (must be globally unique).

5. Put the output `ReportApiUrl` in `frontend/.env` as `REACT_APP_BUGTRACKER_URL` and recreate the frontend container.

## Prove plumbing (no browser)

Unit tests (no AWS):

```bash
cd infrastructure/bugtracker
python -m unittest discover -s tests -v
```

Local invoke needs credentials in the environment (Secrets Manager is not called if these are set):

```bash
export GITHUB_TOKEN=ghp_...
export GITHUB_OWNER=YOUR_ORG
export GITHUB_REPO=c0ll3ct1v3
export REPORTS_BUCKET=your-deployed-or-dev-bucket
sam build
sam local invoke ReportFunction -e events/report.json --env-vars <(echo '{"ReportFunction":{"GITHUB_TOKEN":"'"$GITHUB_TOKEN"'","GITHUB_OWNER":"'"$GITHUB_OWNER"'","GITHUB_REPO":"'"$GITHUB_REPO"'","REPORTS_BUCKET":"'"$REPORTS_BUCKET"'"}}')
```

After `sam deploy`, curl the live API with the sample body:

```bash
API=https://xxxx.execute-api.us-east-2.amazonaws.com/prod/reports
BODY=$(python -c 'import json; print(json.load(open("events/report.json"))["body"])')
curl -sS -X POST "$API" \
  -H 'Content-Type: application/json' \
  -H 'Origin: http://localhost:3030' \
  -d "$BODY"
```

You should get `{"ok":true,"issue_url":"https://github.com/..."}` and a new issue with the tiny JPEG.

## Contract

```json
{
  "image_data_url": "data:image/jpeg;base64,...",
  "summary": "string",
  "type": "bug | feature",
  "page_url": "https://...",
  "viewport": { "w": 1440, "h": 900, "dpr": 2 },
  "user_agent": "...",
  "console_errors": [{ "t": 0, "msg": "..." }]
}
```

Throttle: 5 rps / burst 10. Objects under `reports/` are anonymously readable (UUID keys) and expire after 90 days. GitHub Camo needs that public GET; presigned URLs render as Forbidden in issues.
