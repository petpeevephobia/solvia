# 🔴 URGENT: Update GitHub Secret with New RSA Key

## Problem Solved
The previous OpenSSH format key was incompatible with GitHub Actions. We've generated a new RSA format key that will work.

## Instructions for Nadra

### Step 1: Copy the New Key

Open the file: `github_actions_deploy_key`

This file contains the new RSA private key in the correct format.

**IMPORTANT**: Copy the ENTIRE content, including:
- First line: `-----BEGIN RSA PRIVATE KEY-----`
- All the encoded content (multiple lines)
- Last line: `-----END RSA PRIVATE KEY-----`

### Step 2: Update GitHub Secret

1. Go to: https://github.com/petpeevephobia/solvia/settings/secrets/actions
2. Click on `SERVER_SSH_KEY`
3. Click "Update"
4. DELETE all existing content
5. Paste the ENTIRE content from `github_actions_deploy_key`
6. Click "Update secret"

### Step 3: Verify

The key should start with:
```
-----BEGIN RSA PRIVATE KEY-----
```

And end with:
```
-----END RSA PRIVATE KEY-----
```

### Files Available

- `github_actions_deploy_key` - **USE THIS ONE** (new RSA format key)
- `github_actions_deploy_key.pub` - Public key (already added to server)
- ~~id_rsa_solvia~~ - Old OpenSSH format (doesn't work with GitHub Actions)

## What Changed

✅ New RSA format key generated (compatible with GitHub Actions)
✅ Public key already added to server
✅ Workflow simplified for better reliability
✅ Tested and working locally

Once you update the SECRET with content from `github_actions_deploy_key`, the CI/CD will work immediately!