# 🔑 ADD DEPLOY KEYS TO GITHUB - STEP BY STEP

## ⚠️ CRITICAL: Deploy keys are NOT added yet!

Test shows: `Permission denied (publickey)` when server tries to connect to GitHub.

---

## 📝 What Are Deploy Keys?

Deploy keys allow the **server** to pull code from GitHub repositories.

- **SERVER_SSH_KEY** (✅ you already added this) = GitHub Actions → Server
- **Deploy Keys** (❌ need to add now) = Server → GitHub

---

## 🎯 STEP 1: Add Deploy Key to Dashboard

### Go to:
```
https://github.com/solviasg/solvia/settings/keys
```

### Click: **"Add deploy key"** button (top right)

### Fill in:

**Title:**
```
Server Deploy Key - Production
```

**Key:** (copy this ENTIRE line)
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJXfJoSmx3oSDBHjErtNeb+pFF1irXzmr8fMLD5XscCO deploy-key-solvia
```

### ✅ **IMPORTANT: Check the box "Allow write access"**

### Click: **"Add key"**

---

## 🎯 STEP 2: Add Deploy Key to Landing Page

### Go to:
```
https://github.com/solviasg/solvia-site/settings/keys
```

### Click: **"Add deploy key"** button (top right)

### Fill in:

**Title:**
```
Server Deploy Key - Production
```

**Key:** (copy this ENTIRE line)
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExBL5wGR9hP/y4j63FDShP0taubzhKwSwvvUVEviIVB deploy-key-solvia-site
```

### ✅ **IMPORTANT: Check the box "Allow write access"**

### Click: **"Add key"**

---

## 🔍 How to Verify You Did It Correctly

After adding both keys, you should see:

**In Dashboard repo (solvia/settings/keys):**
- ✅ "Server Deploy Key - Production"
- Shows: "Read/write" access
- Key fingerprint: `SHA256:qABc9fvoqMINQc5XAtGyIhZAH3CsVnv5391qySXgfH4`

**In Landing repo (solvia-site/settings/keys):**
- ✅ "Server Deploy Key - Production"
- Shows: "Read/write" access
- Key fingerprint: `SHA256:ZzzLWjnFz9fHLd6TVqjX4SH4qX8zUUjXAD7qYuDW9Qs`

---

## ✅ After Adding Both Keys

Come back and tell me: **"deploy keys added"**

Then I'll run the server setup script to initialize everything!

---

## 🆘 Common Mistakes

❌ **Only added one deploy key** → Need to add to BOTH repos
❌ **Forgot "Allow write access"** → Server can't pull code
❌ **Added to wrong section** → Should be in "Deploy keys", NOT "SSH keys"
❌ **Copied wrong key** → Make sure fingerprint matches

---