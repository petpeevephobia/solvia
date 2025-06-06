# Business Analysis Table Setup Guide

## 🔧 **Quick Setup Steps**

### 1. **Import CSV Template**
- Import `reports/Business_Analysis.csv` into your Airtable base
- Name the table exactly: `Business_Analysis`

### 2. **Critical Field Type Fixes**
After CSV import, **manually fix these field types**:

#### **Boolean Fields** (Change from "Select" to "Checkbox"):
- `has_ecommerce` 
- `has_local_presence`
- `has_public_pricing`
- `is_location_based` 
- `experience_indicators`
- `has_advanced_features`
- `social_media_integration`
- `has_content_marketing`
- `has_lead_generation`
- `has_social_proof`
- `phone_prominence`
- `has_contact_forms`
- `has_live_chat`

#### **Number Fields** (Should already be correct):
- `business_complexity_score`
- `service_count`
- `establishment_year`

#### **Date Fields**:
- `analysis_date` - Set to "Date and time" format

#### **Long Text Fields** (Change from "Single line text" to "Long text"):
- `services_offered`
- `target_locations`
- `value_proposition`
- `trust_indicators`
- `business_insights`
- `seo_strategy_recommendations`

#### **Link to Record Field**:
- `url` - Link to "Websites" table

### 3. **Primary Field Setup**
- Set `analysis_date` as the primary field (not the linked URL field)

## 🛠️ **Field Configuration Details**

| Field Name | Type | Description |
|------------|------|-------------|
| `url` | Link to another record | Links to Websites table |
| `business_model` | Single select | E-commerce, SaaS, Professional Services, etc. |
| `target_market` | Single select | B2B, B2C |
| `industry_sector` | Single select | Technology, Healthcare, Finance, etc. |
| `company_size` | Single select | Startup, Small, Medium, Large, Enterprise |
| `has_ecommerce` | Checkbox | Boolean |
| `has_local_presence` | Checkbox | Boolean |
| `business_complexity_score` | Number | 1-10 scale |
| `primary_age_group` | Single select | Young Adults, Middle Age, Seniors, General |
| `income_level` | Single select | Luxury, Premium, Mid-Range, Budget |
| `audience_sophistication` | Single select | Expert, High, General, Basic |
| `services_offered` | Long text | Service descriptions |
| `has_public_pricing` | Checkbox | Boolean |
| `service_count` | Number | Count of services |
| `geographic_scope` | Single select | Global, National, Regional, Local |
| `target_locations` | Long text | Location strings |
| `is_location_based` | Checkbox | Boolean |
| `business_maturity` | Single select | Startup, Growing, Established, Mature |
| `establishment_year` | Number | Year founded |
| `experience_indicators` | Checkbox | Boolean |
| `platform_detected` | Single select | WordPress, Shopify, Custom, etc. |
| `has_advanced_features` | Checkbox | Boolean |
| `social_media_integration` | Checkbox | Boolean |
| `tech_sophistication` | Single select | Advanced, High, Medium, Basic |
| `has_content_marketing` | Checkbox | Boolean |
| `has_lead_generation` | Checkbox | Boolean |
| `has_social_proof` | Checkbox | Boolean |
| `content_maturity` | Single select | Advanced, Mature, Developing, Basic |
| `phone_prominence` | Checkbox | Boolean |
| `has_contact_forms` | Checkbox | Boolean |
| `has_live_chat` | Checkbox | Boolean |
| `preferred_contact_method` | Single select | Phone, Email, Form, Chat, Social |
| `competitive_positioning` | Single select | Leader, Challenger, Niche, Follower |
| `positioning_strength` | Single select | Dominant, Strong, Medium, Weak |
| `value_proposition` | Long text | Value proposition description |
| `brand_strength` | Single select | Very Strong, Strong, Medium, Weak |
| `trust_indicators` | Long text | Trust signals found |
| `business_insights` | Long text | AI-generated insights |
| `seo_strategy_recommendations` | Long text | SEO recommendations |
| `analysis_date` | Date and time | When analysis was performed |

## ⚠️ **Common Errors & Solutions**

### Error: "Cannot parse value 'false' for field has_ecommerce"
**Solution**: Change all `has_*` fields from "Select" to "Checkbox" type

### Error: "Cannot parse date value"
**Solution**: Ensure `analysis_date` is set to "Date and time" type

### Error: "UNKNOWN_FIELD_NAME"
**Solution**: Table name must be exactly `Business_Analysis` (case-sensitive)

### Error: "INVALID_MULTIPLE_CHOICE_OPTIONS"
**Solution**: Your Single select fields don't have the required options. Follow `Business_Analysis_Select_Options.md` for all required options

## ✅ **Verification**
After setup, the Business_Analysis table should:
1. Have 40 total fields
2. All boolean fields should be checkboxes
3. Long text fields should allow multiple lines
4. Date field should accept ISO format timestamps
5. URL field should link to Websites table records 