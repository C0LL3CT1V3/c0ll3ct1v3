# Main-branch pipeline (CodePipeline + CodeBuild)

Merges to **main** build and ship the existing **EC2 + Docker Compose** prod box. This is not ECS.

Region: **us-east-2**. Stack name: `c0ll3ct1v3-pipeline`.

```
GitHub main
  → CodeBuild: pytest + frontend unit tests + docker push :latest and :sha
  → Manual approval
  → CodeBuild: SSM on i-08e02bc6466d72442
       git reset --hard $sha
       rolling prod-up (db/redis stay up)
       busy gate + /health + nginx
```

Compose still pulls `:latest`. The git SHA is also pushed so you can retag without a rebuild (`scripts/ecr-rollback.sh`).

Each approved deploy recreates backend, then worker, then frontend. **Postgres and Redis do not restart.** Open portal tabs keep React state. There is a short API 502 window while backend swaps. A warm zero-downtime swap would need a second box.

## One-time console / AWS

1. **SSM on the instance.** The instance profile (`c0ll3ct1v3-ec2-role`) needs `AmazonSSMManagedInstanceCore`. SSM Agent must show as online:

   ```bash
   aws ssm describe-instance-information --region us-east-2 \
     --filters "Key=InstanceIds,Values=i-08e02bc6466d72442"
   ```

2. **Git on the box.** `/home/ubuntu/c0ll3ct1v3` must `git fetch origin main` (deploy key or HTTPS). Use a full clone, not a shallow one.

3. **GitHub connection (us-east-2).** Developer Tools → Connections → Create connection → GitHub. Complete the handshake. Copy the connection ARN (`arn:aws:codeconnections:us-east-2:...` or `arn:aws:codestar-connections:...`).

4. **Frontend build secret.** CRA values are baked into the frontend image. Create JSON (empty strings are fine for optional keys):

   ```json
   {
     "REACT_APP_AUTH0_DOMAIN": "",
     "REACT_APP_AUTH0_CLIENT_ID": "",
     "REACT_APP_AUTH0_AUDIENCE": "",
     "REACT_APP_AUTH0_SCOPE": "openid profile email",
     "REACT_APP_AUTH0_MFA_ACR": "http://schemas.openid.net/pape/policies/2007/06/multi-factor",
     "REACT_APP_DROPBOX_APP_KEY": "",
     "REACT_APP_GOOGLE_CLIENT_ID": "",
     "REACT_APP_GOOGLE_API_KEY": "",
     "REACT_APP_GOOGLE_APP_ID": "",
     "REACT_APP_DEFAULT_TENANT": "",
     "REACT_APP_BUGTRACKER_URL": ""
   }
   ```

   ```bash
   aws secretsmanager create-secret \
     --region us-east-2 \
     --name c0ll3ct1v3/pipeline/frontend-build \
     --secret-string file://frontend-build.json
   ```

   Do not commit that file. CodeBuild may only `GetSecretValue` this ARN.

5. **Deploy the stack** (after `aws login`, region us-east-2):

   ```bash
   aws cloudformation deploy \
     --region us-east-2 \
     --stack-name c0ll3ct1v3-pipeline \
     --template-file infrastructure/pipeline/template.yaml \
     --capabilities CAPABILITY_NAMED_IAM \
     --parameter-overrides \
       GitHubConnectionArn=arn:aws:codeconnections:us-east-2:... \
       FrontendBuildSecretArn=arn:aws:secretsmanager:us-east-2:756090160994:secret:c0ll3ct1v3/pipeline/frontend-build-XXXX
   ```

6. **First run.** The pipeline will start on the next push to `main` (or you can Release change). **Stop at Manual approval** until you have watched a green Build. Approving runs `prod-up.sh` on the live box.

## IAM shape

- Build role: ECR push/pull on the three `c0ll3ct1v3-{backend,frontend,worker}` repos only; Secrets Manager read on the frontend-build secret only.
- Deploy role: `ssm:SendCommand` on this instance ARN **and** `AWS-RunShellScript` only. `GetCommandInvocation` is `*` because that API does not take an instance ARN; it cannot start a command.
- Pipeline role: S3 artifacts, `UseConnection` on the GitHub connection, `StartBuild` on the two projects.

## Busy gate

Before recreating containers, `prod-up.sh` runs `python -m app.services.deploy_gate` in the **current** backend container.

Not ready when:

- a `media_uploads` row is `uploading` or `initiating` and younger than 2 hours
- Redis has an authenticated API timestamp newer than 3 minutes (`DEPLOY_IDLE_SECONDS`, default 180)
- Redis is configured but unreachable (fail closed)

If still busy after 10 minutes, the deploy **fails** (does not force). `--force` is for incidents only.

Bearer requests (except `/health`) set Redis key `c0ll3ct1v3:deploy:last_auth_at`.

## Rollback (no rebuild)

```bash
./scripts/ecr-rollback.sh <sha-already-in-ecr>
# on EC2:
cd /home/ubuntu/c0ll3ct1v3 && ./scripts/prod-up.sh --force
```

`--full` still exists on `prod-up.sh` and **does** `compose down` including Postgres. Do not use it from the pipeline.

## Health

After recreate, the SSM command fails unless:

- `http://127.0.0.1:8000/health` returns 200
- `https://127.0.0.1/` returns 200/301/302 (`curl -k`)
