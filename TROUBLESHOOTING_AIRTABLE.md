# Airtable Creation Troubleshooting Guide

## 🔧 Common Issues & Solutions

### Error 422: "Server error" 

**What happened:** The original script tried to create too many complex fields at once, overwhelming the Airtable API.

**✅ Solution:** Use the improved script `create_airtable_base_v2.py`

```bash
python create_airtable_base_v2.py
```

**What's different in V2:**
- Creates base with 8 essential fields first
- Adds remaining fields in small batches 
- Better error handling and recovery
- Fallback to simplified field types
- Rate limiting between requests

---

### Error 401: "Unauthorized"

**Cause:** Invalid or missing API key

**✅ Solutions:**
1. **Check API Key Format**
   - Personal Access Token: starts with `pat`
   - Legacy API Key: starts with `key`

2. **Verify Scopes** (for Personal Access Tokens)
   - `data.records:read`
   - `data.records:write` 
   - `schema.bases:read`
   - `schema.bases:write`

3. **Regenerate API Key**
   - Go to https://airtable.com/create-personal-access-token
   - Create new token with correct scopes

---

### Error 403: "Forbidden"

**Cause:** API key doesn't have permission for the workspace

**✅ Solutions:**
1. **Check Workspace Access**
   - Make sure you're a member of the workspace
   - Verify workspace ID is correct

2. **Try Without Workspace ID**
   - Leave `AIRTABLE_WORKSPACE_ID` empty
   - Base will be created in your default workspace

---

### Script Keeps Failing

**Try the Minimal Approach:**

```bash
python create_airtable_base_v2.py
# Choose option 2: "Minimal base"
```

This creates a basic base with just 4 fields that's guaranteed to work, then you can add fields manually.

---

## 🚀 Recommended Workflow

### Option 1: Full Automation (V2)
```bash
python create_airtable_base_v2.py
# Choose option 1
# Follow prompts
```

### Option 2: Manual Approach
```bash
python create_airtable_base_v2.py
# Choose option 2 for minimal base
# Then manually add fields using the reference guide
```

### Option 3: Hybrid Approach
1. Use V2 script to create base + basic fields
2. Visit your Airtable base
3. Manually add any fields that failed
4. Use the `airtable_columns_reference.md` as your guide

---

## 📊 Field Adding Tips

When manually adding fields that failed:

### Field Type Mappings
- `singleLineText` → Single line text
- `multilineText` → Long text
- `number` → Number
- `percent` → Percent
- `checkbox` → Checkbox
- `dateTime` → Date & time
- `url` → URL

### Common Field Issues
- **Date fields**: Use ISO format
- **Percent fields**: Values between 0-1 (0.85 = 85%)
- **Number precision**: Set decimal places as needed

---

## 🛠️ Testing Your Setup

After creating your base:

1. **Verify Base Creation**
   ```bash
   # Check if your base URL works
   https://airtable.com/YOUR_BASE_ID
   ```

2. **Test API Connection**
   ```python
   import requests
   
   headers = {"Authorization": "Bearer YOUR_API_KEY"}
   response = requests.get(f"https://api.airtable.com/v0/YOUR_BASE_ID/SEO%20Audit%20Results", headers=headers)
   print(response.status_code)  # Should be 200
   ```

3. **Update Environment**
   ```env
   AIRTABLE_BASE_ID=YOUR_NEW_BASE_ID
   ```

4. **Test Solvia Integration**
   ```bash
   python main.py
   ```

---

## 🆘 Still Having Issues?

### Quick Diagnostics

1. **API Key Test**
   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" https://api.airtable.com/v0/meta/bases
   ```

2. **Base Access Test**
   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" https://api.airtable.com/v0/YOUR_BASE_ID/
   ```

### Alternative: Manual Base Creation

If all automation fails:

1. **Create base manually** in Airtable
2. **Add one field at a time** using the column reference
3. **Copy the Base ID** to your `.env` file
4. **Test with Solvia script**

### Getting Help

Check these in order:
1. ✅ API key has correct scopes
2. ✅ Internet connection is stable  
3. ✅ Airtable service is not down
4. ✅ Using the V2 script (not the original)
5. ✅ Try minimal base option first

---

## 📝 Success Checklist

After successful creation:

- [ ] Base created and accessible
- [ ] All essential fields present
- [ ] Sample data (if requested) added
- [ ] Base ID copied to `.env` file
- [ ] Solvia script tested and working
- [ ] Views configured (optional)

**You're ready to start your SEO audits!** 🎉 