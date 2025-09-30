# 🔴 FINAL SSH KEY FIX - STEP BY STEP

## Problem
The SSH key in GitHub Secrets is corrupted/wrong format causing "error in libcrypto"

## Solution
Follow these EXACT steps:

---

## STEP 1: Open the Key File

Open this file in a text editor:
```
SSH_KEY_TO_COPY.txt
```

**OR** use this command to display it:
```bash
cat SSH_KEY_TO_COPY.txt
```

---

## STEP 2: Select ALL Content

**IMPORTANT**: Select from the VERY FIRST character to the VERY LAST character

The content should start with:
```
-----BEGIN RSA PRIVATE KEY-----
```

And end with:
```
-----END RSA PRIVATE KEY-----
```

**CRITICAL**: Make sure you include:
- The BEGIN line
- All 49 lines of encoded text in between
- The END line
- Total: **51 lines**

---

## STEP 3: Copy to Clipboard

- Press Cmd+A (select all)
- Press Cmd+C (copy)

---

## STEP 4: Update GitHub Secret

1. Go to: https://github.com/petpeevephobia/solvia/settings/secrets/actions

2. Click on: `SERVER_SSH_KEY`

3. Click: "Update"

4. In the "Secret" field:
   - Press Cmd+A (select all existing content)
   - Press Delete (clear it completely)
   - Press Cmd+V (paste new key)

5. **VERIFY**: The pasted content should:
   - Start with: `-----BEGIN RSA PRIVATE KEY-----`
   - End with: `-----END RSA PRIVATE KEY-----`
   - Have about 51 lines of text

6. Click: "Update secret"

---

## STEP 5: Verify Update

After clicking "Update secret", GitHub should show:
- ✅ "Secret SERVER_SSH_KEY was updated"

---

## STEP 6: Test

After updating the secret, push any commit to trigger the workflow:

```bash
git commit --allow-empty -m "test: verify SSH fix"
git push origin main
```

Then check: https://github.com/petpeevephobia/solvia/actions

The "Setup SSH" step should now show:
- ✅ SSH connection successful

---

## Common Mistakes to Avoid

❌ DO NOT:
- Copy only part of the key
- Add extra spaces or newlines
- Copy from a different file
- Forget to include BEGIN/END lines

✅ DO:
- Copy the entire content from SSH_KEY_TO_COPY.txt
- Use Cmd+A to select all
- Verify the BEGIN and END lines are included
- Make sure it's 51 lines total

---

## If It Still Fails

If you see "error in libcrypto" again:

1. The key was NOT copied correctly
2. Try copying from the terminal instead:
   ```bash
   cat SSH_KEY_TO_COPY.txt | pbcopy
   ```
   This copies to clipboard, then paste in GitHub

3. Or take a screenshot showing what you pasted and send it (first 2 lines and last 2 lines only)