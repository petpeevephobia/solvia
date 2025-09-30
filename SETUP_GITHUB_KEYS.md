# 🔐 GitHub SSH Keys Setup Guide

## Part 1: Update GitHub Actions SSH Secret (CI/CD Authentication)

### Step 1: Copy the SSH Private Key

The private key is in: `NEW_SSH_KEY_FOR_GITHUB.txt`

```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACC1hi82Mk5NAcqdC2R6aUbNT867GI7bTsturs6fAKh95wAAAJjU5seu1ObH
rgAAAAtzc2gtZWQyNTUxOQAAACC1hi82Mk5NAcqdC2R6aUbNT867GI7bTsturs6fAKh95w
AAAEA/H8Nl6Dpf3elchmqH81SmmdbtLfosoQs7dLeq/sEi6bWGLzYyTk0Byp0LZHppRs1P
zrsYjttOy26uzp8AqH3nAAAAE2dpdGh1Yi1hY3Rpb25zLWNpY2QBAg==
-----END OPENSSH PRIVATE KEY-----
```

### Step 2: Update SERVER_SSH_KEY in BOTH Repositories

**Important:** You need to update this secret in BOTH repositories!

#### For Dashboard (solvia):
1. Go to: https://github.com/solviasg/solvia/settings/secrets/actions
2. Click on `SERVER_SSH_KEY`
3. Click **Update**
4. Delete all existing content
5. Paste the **entire key above** (all 7 lines including BEGIN and END)
6. Click **Update secret**

#### For Landing Page (solvia-site):
1. Go to: https://github.com/solviasg/solvia-site/settings/secrets/actions
2. Click on `SERVER_SSH_KEY`
3. Click **Update**
4. Delete all existing content
5. Paste the **entire key above** (all 7 lines including BEGIN and END)
6. Click **Update secret**

---

## Part 2: Add Deploy Keys (For Server Git Pull)

These keys allow the server to pull code from GitHub.

### Deploy Key for Dashboard (solvia)

**Public Key:**
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJXfJoSmx3oSDBHjErtNeb+pFF1irXzmr8fMLD5XscCO deploy-key-solvia
```

**Steps:**
1. Go to: https://github.com/solviasg/solvia/settings/keys
2. Click **Add deploy key**
3. Title: `Server Deploy Key - Production`
4. Key: Paste the public key above
5. ✅ Check **Allow write access** (IMPORTANT!)
6. Click **Add key**

### Deploy Key for Landing Page (solvia-site)

**Public Key:**
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExBL5wGR9hP/y4j63FDShP0taubzhKwSwvvUVEviIVB deploy-key-solvia-site
```

**Steps:**
1. Go to: https://github.com/solviasg/solvia-site/settings/keys
2. Click **Add deploy key**
3. Title: `Server Deploy Key - Production`
4. Key: Paste the public key above
5. ✅ Check **Allow write access** (IMPORTANT!)
6. Click **Add key**

---

## Verification Checklist

- [ ] SERVER_SSH_KEY updated in solvia repository
- [ ] SERVER_SSH_KEY updated in solvia-site repository
- [ ] Deploy key added to solvia repository (with write access)
- [ ] Deploy key added to solvia-site repository (with write access)

---

## What Each Key Does

- **SERVER_SSH_KEY**: Allows GitHub Actions to SSH into the production server to run deployment commands
- **Deploy Keys**: Allow the production server to pull code from GitHub repositories

---

**After completing these steps, let me know and I'll continue with the CI/CD workflow updates!**