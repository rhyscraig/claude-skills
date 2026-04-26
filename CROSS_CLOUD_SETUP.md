# Cross-Cloud Setup: AWS + GCP

## Status: ✅ LIVE & VERIFIED

Both AWS and GCP are now authenticated, configured, and accessible via CloudctlSkill.

## What Works

### AWS (myorg)
- **Status**: ✅ Authenticated & Accessible
- **Accounts**: 7 available (including `767828739298` - TerrorGems)
- **Access Method**: AWS SSO via CloudctlSkill
- **Services**: Lambda, IAM, STS, CloudWatch

### GCP (gcp-terrorgems)
- **Status**: ✅ Authenticated & Accessible
- **Projects**: 3 available (including `asatst-gemini-api-v2` - Vertex AI enabled)
- **Access Method**: gcloud CLI with cached credentials
- **Services**: Vertex AI, IAM, Cloud Resource Manager

## Configuration

### CloudctlSkill Configuration
Located at: `~/.config/cloudctl/orgs.yaml`

```yaml
orgs:
  - name: myorg
    provider: aws
    sso_start_url: https://d-9c67661145.awsapps.com/start
    sso_region: eu-west-2
    default_region: eu-west-2

  - name: gcp-terrorgems
    provider: gcp
    default_project: asatst-gemini-api-v2
    default_region: us-central1

enabled_orgs:
  - myorg
  - gcp-terrorgems
```

### Authentication Status
- **AWS**: Cached SSO token (valid)
- **GCP**: Cached gcloud credentials (valid)
  - Authenticated as: `rhyscraig1@gmail.com`
  - Service: `asatst-gemini-api-v2`

## Live Verification Commands

```bash
# List both clouds via CloudctlSkill
cloudctl org list

# AWS accounts
cloudctl accounts myorg

# GCP projects
gcloud projects list

# Vertex AI API status
gcloud services list --enabled --project asatst-gemini-api-v2 | grep aiplatform
```

## CloudctlSkill API Usage

```python
from skills.cloudctl import CloudctlSkill
import asyncio

async def cross_cloud_ops():
    skill = CloudctlSkill()
    
    # List organizations
    orgs = await skill.list_organizations()
    
    # Get AWS accounts
    accounts = await skill.list_accounts("myorg")
    
    # Check GCP status
    gcp_status = await skill.get_token_status("gcp-terrorgems")
    
    # Health check
    health = await skill.health_check()
    print(f"System healthy: {health.is_healthy}")

asyncio.run(cross_cloud_ops())
```

## Next: Cross-Cloud Integration

With both clouds live, next steps are:

1. **Deploy AWS Lambda Role** (OIDC Federation)
   - Execute role: `terrorgems-lambda-gcp-invoker`
   - Permissions: Assume GCP service account

2. **Deploy GCP Resources**
   - Service account: `terrorgems-lambda-invoker`
   - Workload Identity Pool: AWS OIDC
   - IAM: Vertex AI Editor

3. **Test Cross-Cloud Invocation**
   - Lambda → STS GetCallerIdentity (AWS)
   - Token exchange (OIDC)
   - Vertex AI API call (GCP)

## References

- CloudctlSkill: `/Users/craighoad/Repos/claude-skills/`
- Deployment Guide: `/tmp/CROSS_CLOUD_SETUP_README.md`
- Terraform Configs: `/tmp/terraform/aws` and `/tmp/terraform/gcp`
