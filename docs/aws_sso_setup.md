# AWS SSO Setup - Single Login Workflow

This document explains how to use a single AWS SSO login for both the AWS Toolkit VSCode extension and the AWS CLI.

## Overview

Instead of logging in separately for the AWS Toolkit and AWS CLI, you can now:
1. Login once via the AWS Toolkit VSCode extension
2. Automatically use the same session in the AWS CLI

## How It Works

The AWS Toolkit and AWS CLI both use AWS SSO but store tokens in slightly different locations:
- **AWS Toolkit**: Stores tokens in `~/.aws/sso/cache/` with a long filename
- **AWS CLI**: Expects tokens in `~/.aws/sso/cache/` with a specific filename based on the SHA1 hash of the SSO start URL

The `install-user-aws.sh` script and `aws-sync-sso` helper automatically sync these tokens.

## Setup

The setup is already configured in your devcontainer. When you rebuild the container:

1. The `install-user-aws.sh` script creates:
   - AWS CLI configuration at `~/.aws/config`
   - Helper script `aws-sync-sso` at `~/.local/bin/aws-sync-sso`
   - Automatic token sync on first run

## Usage

### Normal Workflow

1. **Login via AWS Toolkit** (one-time or when token expires):
   - Click the AWS icon in the VSCode sidebar
   - Click "Sign in to AWS"
   - Follow the browser-based SSO login flow

2. **Use AWS CLI immediately**:
   ```bash
   aws sts get-caller-identity
   aws s3 ls
   # All AWS CLI commands work automatically
   ```

### Manual Token Sync

If the AWS CLI stops working after an AWS Toolkit token refresh, manually sync:

```bash
aws-sync-sso
```

This will:
- Find the current AWS Toolkit token
- Create/update a symlink so AWS CLI can use it
- Display confirmation

## Configuration Details

### AWS Config (`~/.aws/config`)

```ini
[default]
sso_start_url = https://nrcan-rncan.awsapps.com/start
sso_region = ca-central-1
sso_account_id = 834599497928
sso_role_name = PowerUser
region = ca-central-1
output = json
```

**Note**: This uses the legacy SSO configuration (without `sso-session`) because it's more compatible with token sharing between AWS Toolkit and AWS CLI.

### Token Symlink

The `aws-sync-sso` script creates a symlink:
```
~/.aws/sso/cache/dfbe205b7eff4598971935ee0157fe1c9c02232c.json
  -> ~/.aws/sso/cache/5b3f2acc201c5de6a87859c36ceb56a9d5cbbadc.json
```

Where:
- `dfbe205b7eff4598971935ee0157fe1c9c02232c` = SHA1 hash of the SSO start URL (expected by AWS CLI)
- `5b3f2acc201c5de6a87859c36ceb56a9d5cbbadc` = AWS Toolkit token file

## Troubleshooting

### Error: "Token for https://nrcan-rncan.awsapps.com/start does not exist"

**Solution**: Run `aws-sync-sso` to sync the tokens

### Error: "No AWS Toolkit SSO token found"

**Solution**: Login via AWS Toolkit in VSCode first

### Token Expired

**Solution**:
1. Logout and login again via AWS Toolkit
2. Run `aws-sync-sso` if needed

### Alternative: Traditional SSO Login

If you prefer to use AWS CLI's built-in SSO login instead of AWS Toolkit:

```bash
aws configure sso
```

This will:
- Prompt for SSO start URL (already configured)
- Open browser for authentication
- Create its own token (independent of AWS Toolkit)

## Benefits

- **Single login**: Login once, use everywhere
- **Automatic sync**: Setup script handles token linking
- **Manual control**: `aws-sync-sso` command for manual sync when needed
- **No duplicate logins**: No need to run `aws sso login` separately

## Files Modified

- `.devcontainer/scripts/install-user-aws.sh`: Updated to create sync script and use legacy SSO config
- `~/.local/bin/aws-sync-sso`: New helper script for token synchronization
- `~/.aws/config`: Simplified to use legacy SSO configuration for better compatibility

## References

- [AWS CLI SSO Configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
- [AWS Toolkit for VSCode](https://docs.aws.amazon.com/toolkit-for-vscode/latest/userguide/welcome.html)
