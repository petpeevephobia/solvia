# SSH Key Setup Instructions for GitHub Actions

## ⚠️ CRITICAL: The SSH key must be added EXACTLY as shown below

### Step 1: Copy the SSH Private Key

Copy the ENTIRE content of `id_rsa_solvia` file, including:
- The first line: `-----BEGIN OPENSSH PRIVATE KEY-----`
- All the encoded content in between
- The last line: `-----END OPENSSH PRIVATE KEY-----`

**Important**: Do NOT modify or format the key. Copy it exactly as is.

### Step 2: Add to GitHub Secrets

1. Go to: https://github.com/petpeevephobia/solvia/settings/secrets/actions
2. Click "New repository secret" or update existing `SERVER_SSH_KEY`
3. Name: `SERVER_SSH_KEY`
4. Value: Paste the ENTIRE content of `id_rsa_solvia`

### Step 3: Verify the Format

The secret should look EXACTLY like this (example structure):

```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAACFwAAAAdzc2gtcn
...
[many more lines of encoded text]
...
DnJGRvtJ4xHHAAAAD3Jvb3RAc3J2MTAxNTg4MQECAw==
-----END OPENSSH PRIVATE KEY-----
```

### Common Mistakes to Avoid

❌ DO NOT:
- Add quotes around the key
- Add escape characters (\n)
- Format or indent the key
- Remove the BEGIN/END lines
- Add any extra text or spaces

✅ DO:
- Copy the entire file content as-is
- Include all header and footer lines
- Preserve the exact formatting

### Test Command

To verify your local key works:
```bash
ssh -i id_rsa_solvia root@72.60.195.244 "echo 'Connection successful'"
```

If this works locally but not in GitHub Actions, the issue is with the GitHub Secret formatting.

### Alternative Method

If issues persist, you can also try base64 encoding:

1. Encode the key:
```bash
base64 -w 0 < id_rsa_solvia > id_rsa_solvia.b64
```

2. Add the base64 content to GitHub Secrets as `SERVER_SSH_KEY_BASE64`

3. Update the workflow to decode it:
```yaml
echo "${{ secrets.SERVER_SSH_KEY_BASE64 }}" | base64 -d > ~/.ssh/id_rsa
```