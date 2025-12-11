# SOLVIA Design System - Complete Reference

> **Purpose**: Comprehensive design specification for pixel-perfect implementation of Solvia v2
> **Source**: Extracted from original Solvia codebase (37 files, 15,000+ lines)
> **Last Updated**: 2025-12-01

---

## Table of Contents

1. [Color System](#1-color-system)
2. [Typography](#2-typography)
3. [Spacing & Layout](#3-spacing--layout)
4. [Components](#4-components)
5. [Sidebar Navigation](#5-sidebar-navigation)
6. [Mobile Dock](#6-mobile-dock)
7. [Dashboard](#7-dashboard)
8. [Filter System](#8-filter-system)
9. [Cards & Containers](#9-cards--containers)
10. [Buttons](#10-buttons)
11. [Forms & Inputs](#11-forms--inputs)
12. [Modals](#12-modals)
13. [Status & Badges](#13-status--badges)
14. [Animations](#14-animations)
15. [Responsive Breakpoints](#15-responsive-breakpoints)
16. [File Structure](#16-file-structure)

---

## 1. Color System

### Primary Colors
```css
--color-primary: #F97316;          /* Main brand orange */
--color-primary-rgb: 249, 115, 22;
--color-primary-light: #FFF7ED;    /* Light orange background */
--color-primary-hover: #EA580C;    /* Darker orange for hover */
--color-primary-600: #EC6019;      /* Alternative primary */
```

### Background Colors
```css
--background-body: #F9FAFB;        /* Main app background */
--background-card: #FFFFFF;        /* Card backgrounds */
--background-sidebar: #FFFFFF;     /* Sidebar (WHITE, not dark!) */
```

### Text Colors
```css
--color-text-dark: #000000;        /* Primary text */
--color-text-primary: #1F2937;     /* Heading text */
--color-text-light: #6B7280;       /* Secondary/muted text */
--color-text-muted: #9CA3AF;       /* Very muted text */
```

### Status Colors
```css
--color-positive: #10B981;         /* Success/positive green */
--color-negative: #EF4444;         /* Error/negative red */
--color-warning: #F59E0B;          /* Warning yellow */
--color-info: #3B82F6;             /* Info blue */
```

### Border Colors
```css
--border-color: #E5E7EB;           /* Default border */
--border-color-light: #F3F4F6;     /* Light border */
```

### Severity Colors (Issues)
```css
/* Critical Issue Card */
background: #FFD8D8;
border-left: 4px solid #EF4444;

/* Warning Issue Card */
background: #FFF1D8;
border-left: 4px solid #F59E0B;

/* Info Issue Card */
background: #E0F2FE;
border-left: 4px solid #3B82F6;
```

### Score Colors
```css
/* SEO Score Thresholds */
.score-high    { color: #10B981; } /* >= 70 */
.score-medium  { color: #F59E0B; } /* 40-69 */
.score-low     { color: #EF4444; } /* < 40 */
```

---

## 2. Typography

### Font Families
```css
font-family: 'Nunito', 'Poppins', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;

/* Heading font */
font-family: 'Poppins', sans-serif;

/* Body/UI font */
font-family: 'Nunito', sans-serif;
```

### Font Sizes
```css
/* Headings */
h1: 2rem (32px)
h2: 1.5rem (24px)
h3: 1.25rem (20px)
h4: 1.125rem (18px)

/* Body */
body: 1rem (16px)
body-sm: 0.875rem (14px)
caption: 0.75rem (12px)

/* Specific Components */
.metric-value: 32px (large metrics)
.metric-label: 14px
.nav-item-text: 14px
.mobile-dock-label: 10px
```

### Font Weights
```css
normal: 400
medium: 500
semibold: 600
bold: 700
```

---

## 3. Spacing & Layout

### Base Spacing Scale
```css
/* 4px base unit */
space-1: 4px
space-2: 8px
space-3: 12px
space-4: 16px
space-5: 20px
space-6: 24px
space-8: 32px
space-10: 40px
space-12: 48px
```

### Common Paddings
```css
/* Cards */
card-padding: 24px (p-6)
card-padding-sm: 20px (p-5)

/* Containers */
container-padding: 32px (p-8)
section-margin: 32px (mb-8)

/* Navigation items */
nav-item-padding: 12px 16px (py-3 px-4)
```

### Border Radius
```css
--radius-sm: 6px
--radius-md: 8px
--radius-lg: 12px
--radius-xl: 16px
--radius-button: 8px
--radius-card: 12px
--radius-input: 8px
--radius-full: 9999px (circular)
```

---

## 4. Components

### Component Summary
| Component | Location | Key Characteristics |
|-----------|----------|---------------------|
| Sidebar | Fixed left, 80px collapsed, 233px expanded | White bg, hover expand |
| Mobile Dock | Fixed bottom, 64px height | 3 items, safe-area padding |
| Metric Card | Dashboard grid | Icon top-right, value prominent |
| Issue Card | Dashboard | Severity color left border |
| Filter Bar | Dashboard top | Date presets, last update info |
| Chat Section | Dashboard bottom | Input + suggestions |

---

## 5. Sidebar Navigation

### Dimensions
```css
/* Collapsed state */
width: 80px;

/* Expanded state (on hover) */
width: 233px;

/* Header height */
min-height: 80px;
```

### Structure
```html
<aside class="sidebar">
  <!-- Header with logo -->
  <div class="sidebar-header">
    <div class="logo-icon">
      <img src="/static/orange-svg-emblem-40px.svg" /> <!-- Collapsed: emblem -->
      <img src="/images/logo_v2.png" />                 <!-- Expanded: full logo -->
    </div>
    <div class="logo-text">Solvia</div>
  </div>

  <!-- Navigation -->
  <nav class="sidebar-nav">
    <a class="nav-item" data-route="dashboard">
      <svg class="nav-item-icon">...</svg>
      <span class="nav-item-text">Dashboard</span>
    </a>
    <a class="nav-item" data-route="audit-history">
      <svg class="nav-item-icon">...</svg>
      <span class="nav-item-text">Audit History</span>
    </a>
  </nav>

  <!-- Footer -->
  <div class="sidebar-footer">
    <div class="ai-model-info">AI Chat Model: GPT o4-mini</div>
    <a class="sidebar-footer-item" data-route="settings">Settings</a>
    <div class="sidebar-footer-item" onclick="logout()">Log out</div>
    <div class="user-info">
      <div class="user-avatar"><!-- User icon --></div>
      <div class="user-email">user@email.com</div>
    </div>
  </div>
</aside>
```

### Styling
```css
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  height: 100vh;
  background: #FFFFFF;           /* WHITE background */
  border-right: 1px solid #E5E7EB;
  transition: width 0.3s ease;
  z-index: 50;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  min-height: 80px;
  border-bottom: 1px solid #E5E7EB;
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 12px;
}

.logo-icon img {
  width: 28px;
  height: 28px;
  transition: all 0.3s;
}

/* Expanded logo */
.sidebar:hover .logo-icon img {
  height: 28px;
  width: auto;
  max-width: 140px;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  margin: 4px 16px;
  border-radius: 8px;
  color: #6B7280;
  text-decoration: none;
  transition: all 0.2s;
}

.nav-item:hover {
  background: #F3F4F6;
  color: #1F2937;
}

.nav-item.active {
  background: #FEF3E7;
  color: #EC6019;
}

.nav-item-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.nav-item-text {
  font-size: 14px;
  font-weight: 500;
  margin-left: 12px;
  white-space: nowrap;
  opacity: 0;
  width: 0;
  overflow: hidden;
  transition: opacity 0.3s, width 0.3s;
}

.sidebar:hover .nav-item-text {
  opacity: 1;
  width: auto;
}

/* User info at bottom */
.user-info {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  gap: 12px;
}

.user-avatar {
  width: 32px;
  height: 32px;
  background: #FFEADE;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-avatar svg {
  width: 18px;
  height: 18px;
  color: #EC6019;
}
```

---

## 6. Mobile Dock

### Dimensions
```css
height: 64px;
padding-bottom: env(safe-area-inset-bottom); /* iOS safe area */
```

### Structure
```html
<nav class="mobile-dock">
  <div class="mobile-dock-container">
    <a class="mobile-dock-item" data-route="dashboard">
      <div class="mobile-dock-icon">
        <svg><!-- Dashboard icon --></svg>
      </div>
      <span class="mobile-dock-label">Dashboard</span>
    </a>
    <a class="mobile-dock-item" data-route="audit-history">
      <div class="mobile-dock-icon">
        <svg><!-- Audit icon --></svg>
      </div>
      <span class="mobile-dock-label">Audit History</span>
    </a>
    <a class="mobile-dock-item" data-route="settings">
      <div class="mobile-dock-icon">
        <svg><!-- Settings icon --></svg>
      </div>
      <span class="mobile-dock-label">Settings</span>
    </a>
  </div>
</nav>
```

### Styling
```css
.mobile-dock {
  display: none;                    /* Hidden on desktop */
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 50;
  background: #FFFFFF;
  border-top: 1px solid #E5E7EB;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.08);
  padding-bottom: env(safe-area-inset-bottom);
}

@media (max-width: 768px) {
  .mobile-dock {
    display: block;
  }
}

.mobile-dock-container {
  display: flex;
  align-items: center;
  justify-content: space-around;
  height: 64px;
  padding: 0 16px;
}

.mobile-dock-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 8px 12px;
  border-radius: 8px;
  color: #6B7280;
  text-decoration: none;
  transition: color 0.2s;
}

.mobile-dock-item.active {
  color: #EC6019;
}

.mobile-dock-icon {
  width: 20px;
  height: 20px;
}

.mobile-dock-label {
  font-size: 10px;
  font-weight: 500;
}
```

---

## 7. Dashboard

### Layout Structure
```html
<div class="dashboard-container">
  <!-- Header -->
  <div class="dashboard-header">
    <h1>Hey, {userName}! We're tracking <span class="text-primary">{website}</span></h1>
    <div class="last-update">Last Update: Nov 30, 2025</div>
  </div>

  <!-- Overview Section -->
  <section class="overview">
    <div class="section-header">
      <h2>Overview</h2>
      <p class="section-subtitle">All data displayed are from the past 28 days</p>
      <!-- Filter buttons -->
    </div>
    <div class="metrics-grid">
      <!-- 4 metric cards -->
    </div>
  </section>

  <!-- Current Issues Section -->
  <section class="current-issues">
    <div class="section-header">
      <h2>Current Issues</h2>
      <button class="btn-run-audit">Run a new audit</button>
    </div>
    <div class="issues-grid">
      <!-- 3 issue cards -->
    </div>
  </section>

  <!-- Chat Section -->
  <section class="chat-section">
    <!-- Solvia AI chat -->
  </section>
</div>
```

### Metric Card
```html
<div class="metric-card">
  <div class="metric-icon">
    <svg><!-- Icon --></svg>
  </div>
  <div class="metric-content">
    <div class="metric-label">SEO Score</div>
    <div class="metric-value">78</div>
    <div class="metric-change">Based on real GSC data</div>
  </div>
</div>
```

```css
.metric-card {
  background: #FFFFFF;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  position: relative;
  display: flex;
  flex-direction: column;
}

.metric-icon {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  background: #F3F4F6;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.metric-icon svg {
  width: 20px;
  height: 20px;
  stroke: #EC6019;
}

.metric-label {
  font-size: 14px;
  color: #6B7280;
  font-weight: 500;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 32px;
  font-weight: 600;
  color: #1F2937;
  margin-bottom: 4px;
}

.metric-change {
  font-size: 13px;
  color: #6B7280;
}
```

### Issue Card
```html
<div class="issue-card issue-critical">
  <div class="issue-header">
    <span class="issue-emoji">🔴</span>
    <span class="issue-badge badge-critical">CRITICAL</span>
  </div>
  <h3 class="issue-title">Low Click-Through Rate</h3>
  <p class="issue-description">Your CTR is below industry average...</p>
  <div class="issue-fix">
    <span class="fix-label">Fix:</span>
    <span class="fix-text">Optimize meta titles and descriptions...</span>
  </div>
</div>
```

```css
.issue-card {
  border-radius: 12px;
  padding: 20px;
  border-left: 4px solid;
}

.issue-card.issue-critical {
  background: #FFD8D8;
  border-left-color: #EF4444;
}

.issue-card.issue-warning {
  background: #FFF1D8;
  border-left-color: #F59E0B;
}

.issue-card.issue-info {
  background: #E0F2FE;
  border-left-color: #3B82F6;
}

.issue-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.issue-emoji {
  font-size: 18px;
}

.issue-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 9999px;
}

.badge-critical {
  background: #FEE2E2;
  color: #991B1B;
}

.badge-warning {
  background: #FEF3C7;
  color: #92400E;
}

.badge-info {
  background: #DBEAFE;
  color: #1E40AF;
}

.issue-title {
  font-size: 16px;
  font-weight: 600;
  color: #1F2937;
  margin-bottom: 8px;
}

.issue-description {
  font-size: 14px;
  color: #4B5563;
  margin-bottom: 12px;
}

.issue-fix {
  font-size: 14px;
}

.fix-label {
  font-weight: 500;
  color: #374151;
}

.fix-text {
  color: #4B5563;
}
```

---

## 8. Filter System

### Filter Bar Structure
```html
<div class="filter-bar">
  <div class="filter-content">
    <div class="filter-controls-left">
      <div class="date-quick-buttons">
        <button class="filter-btn" data-preset="24h">24h</button>
        <button class="filter-btn" data-preset="7d">7d</button>
        <button class="filter-btn active" data-preset="28d">28d</button>
        <button class="filter-btn" data-preset="3mo">3mo</button>
        <button class="filter-btn filter-btn-custom" data-preset="custom">
          <span>Custom</span>
          <svg><!-- Chevron --></svg>
        </button>
      </div>
    </div>
    <div class="filter-meta">
      <span class="filter-meta-text">Last update: Just now</span>
    </div>
  </div>
</div>
```

### Styling
```css
.filter-bar {
  background: #FFFFFF;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.filter-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.date-quick-buttons {
  display: flex;
  gap: 8px;
}

.filter-btn {
  padding: 8px 12px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  border: 1px solid #E5E7EB;
  background: #FFFFFF;
  color: #4B5563;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-btn:hover {
  color: #EC6019;
  border-color: #FECACA;
  background: #FFF7ED;
}

.filter-btn.active {
  background: #EC6019;
  color: #FFFFFF;
  border-color: #EC6019;
}

.filter-meta-text {
  font-size: 13px;
  color: #6B7280;
}
```

---

## 9. Cards & Containers

### Base Card
```css
.card {
  background: #FFFFFF;
  border-radius: 12px;
  border: 1px solid #F3F4F6;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid #E5E7EB;
  margin-bottom: 16px;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #1F2937;
}
```

### Container Widths
```css
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

/* Dashboard with sidebar */
.main-content {
  margin-left: 80px;  /* Sidebar collapsed width */
  padding: 24px 32px;
  padding-bottom: 100px; /* Space for mobile dock */
}

@media (min-width: 768px) {
  .main-content:hover {
    margin-left: 233px; /* Sidebar expanded width */
  }
}
```

---

## 10. Buttons

### Primary Button
```css
.btn-primary {
  background: #F97316;
  color: #FFFFFF;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn-primary:hover {
  background: #EA580C;
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}
```

### Secondary Button
```css
.btn-secondary {
  background: #FFFFFF;
  color: #374151;
  border: 1px solid #E5E7EB;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: #F9FAFB;
  border-color: #D1D5DB;
}
```

### Ghost Button
```css
.btn-ghost {
  background: transparent;
  color: #6B7280;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-ghost:hover {
  background: #F3F4F6;
  color: #1F2937;
}
```

### Run Audit Button
```css
.btn-run-audit {
  background: #FFFFFF;
  color: #EC6019;
  border: 1px solid #EC6019;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-run-audit:hover {
  background: #EC6019;
  color: #FFFFFF;
}

.btn-run-audit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

---

## 11. Forms & Inputs

### Text Input
```css
.input {
  width: 100%;
  padding: 12px 16px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  font-size: 14px;
  color: #1F2937;
  transition: all 0.2s;
}

.input::placeholder {
  color: #9CA3AF;
}

.input:focus {
  outline: none;
  border-color: #EC6019;
  box-shadow: 0 0 0 3px rgba(236, 96, 25, 0.1);
}

.input-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 6px;
}
```

### Chat Input
```css
.chat-input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  font-size: 14px;
  color: #1F2937;
}

.chat-input:focus {
  outline: none;
  border-color: #EC6019;
  box-shadow: 0 0 0 2px rgba(236, 96, 25, 0.1);
}

.chat-send-btn {
  padding: 12px 16px;
  background: #EC6019;
  color: #FFFFFF;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.chat-send-btn:hover {
  background: #D54F10;
}
```

---

## 12. Modals

### Modal Structure
```html
<div class="modal" id="globalModal">
  <div class="modal-overlay" onclick="closeModal()"></div>
  <div class="modal-content">
    <div class="modal-header">
      <div class="modal-icon"><!-- Success/Error icon --></div>
      <h3 class="modal-title">Title</h3>
    </div>
    <div class="modal-body">
      <p>Message content</p>
    </div>
    <div class="modal-footer">
      <button class="btn-primary" onclick="closeModal()">OK</button>
    </div>
  </div>
</div>
```

### Styling
```css
.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  display: none;
  align-items: center;
  justify-content: center;
}

.modal.show {
  display: flex;
}

.modal-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
}

.modal-content {
  position: relative;
  background: #FFFFFF;
  border-radius: 12px;
  padding: 24px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 20px 25px rgba(0, 0, 0, 0.15);
}

.modal-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.modal-icon.success {
  background: #D1FAE5;
  color: #10B981;
}

.modal-icon.error {
  background: #FEE2E2;
  color: #EF4444;
}

.modal-icon.warning {
  background: #FEF3C7;
  color: #F59E0B;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: #1F2937;
  text-align: center;
  margin-bottom: 8px;
}

.modal-body {
  text-align: center;
  color: #6B7280;
  margin-bottom: 24px;
}

.modal-footer {
  text-align: center;
}
```

---

## 13. Status & Badges

### Status Indicators
```css
.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-good {
  background: #D1FAE5;
  color: #065F46;
}

.status-warning {
  background: #FEF3C7;
  color: #92400E;
}

.status-critical {
  background: #FEE2E2;
  color: #991B1B;
}

.status-pending {
  background: #F3F4F6;
  color: #6B7280;
}
```

### Badges
```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 500;
}

.badge-success {
  background: #D1FAE5;
  color: #065F46;
}

.badge-warning {
  background: #FEF3C7;
  color: #92400E;
}

.badge-error {
  background: #FEE2E2;
  color: #991B1B;
}

.badge-info {
  background: #DBEAFE;
  color: #1E40AF;
}

.badge-neutral {
  background: #F3F4F6;
  color: #374151;
}
```

---

## 14. Animations

### Transitions
```css
/* Default transition */
transition: all 0.2s ease;

/* Sidebar expansion */
transition: width 0.3s ease;

/* Button hover */
transition: all 0.2s ease;
transform: translateY(-1px);

/* Card hover */
transition: box-shadow 0.2s ease, transform 0.2s ease;
transform: translateY(-2px);
```

### Loading Spinner
```css
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #FFFFFF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
```

### Skeleton Loading
```css
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.skeleton {
  background: linear-gradient(90deg, #F3F4F6 0%, #E5E7EB 50%, #F3F4F6 100%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}
```

---

## 15. Responsive Breakpoints

### Breakpoints
```css
/* Mobile first approach */
sm: 640px   /* Small devices */
md: 768px   /* Tablets */
lg: 1024px  /* Desktop */
xl: 1280px  /* Large desktop */
```

### Key Responsive Behaviors

```css
/* Sidebar: Hidden on mobile, visible on desktop */
@media (max-width: 767px) {
  .sidebar {
    display: none;
  }
  .mobile-dock {
    display: block;
  }
  .main-content {
    margin-left: 0;
    padding-bottom: 80px; /* Space for dock */
  }
}

/* Grid layouts */
@media (max-width: 767px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  .issues-grid {
    grid-template-columns: 1fr;
  }
}

@media (min-width: 640px) and (max-width: 1023px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .metrics-grid {
    grid-template-columns: repeat(4, 1fr);
  }
  .issues-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

---

## 16. File Structure

### Original Project Structure
```
app/static/
├── images/
│   ├── orange-svg-emblem.svg      # Logo emblem (collapsed sidebar)
│   ├── orange-svg-emblem-40px.svg # Logo emblem 40px
│   ├── logo_v2.png                # Full logo (expanded sidebar)
│   └── login-image.jpg            # Login background
│
├── js/
│   ├── utils/
│   │   ├── ApiUtils.js            # API utilities (1725 lines)
│   │   └── ModalUtils.js          # Modal component (145 lines)
│   └── components/
│       ├── FilterBar.js           # Filter bar component (391 lines)
│       └── DateRangeModal.js      # Date picker modal (378 lines)
│
├── styles/
│   ├── main.css                   # Imports all stylesheets
│   ├── global.css                 # Base styles, fonts
│   ├── sidebar.css                # Sidebar styles
│   ├── dashboard.css              # Dashboard layouts
│   ├── components.css             # Buttons, badges, etc.
│   ├── filters.css                # Filter bar styles
│   ├── mobile-dock.css            # Mobile navigation
│   ├── chat.css                   # Chat section
│   ├── modals.css                 # Modal styles
│   └── responsive.css             # Media queries
│
├── spa.html                       # Main SPA template (351 lines)
├── spa-router.js                  # SPA router (2330 lines)
├── auth.js                        # Auth utilities (126 lines)
├── style.css                      # Legacy styles (2907 lines)
├── domain-selection.js            # Domain selection (214 lines)
├── domain-selection.css           # Domain selection styles
└── domain-selection.html          # Domain selection page
```

### Key Files for Implementation

| File | Lines | Purpose |
|------|-------|---------|
| spa-router.js | 2330 | Main SPA logic, rendering, API calls |
| style.css | 2907 | Complete legacy styles |
| sidebar.css | ~200 | Sidebar hover-expand behavior |
| mobile-dock.css | ~100 | Mobile bottom navigation |
| dashboard.css | ~300 | Dashboard grid layouts |
| FilterBar.js | 391 | Date filter component |
| ModalUtils.js | 145 | Global modal component |

---

## Quick Reference Cards

### Color Palette Card
| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Primary | #F97316 | 249,115,22 | Buttons, active states |
| Primary Light | #FFF7ED | 255,247,237 | Hover backgrounds |
| Primary 600 | #EC6019 | 236,96,25 | Alternative primary |
| Background | #F9FAFB | 249,250,251 | Page background |
| White | #FFFFFF | 255,255,255 | Cards, sidebar |
| Text Dark | #1F2937 | 31,41,55 | Headings |
| Text Muted | #6B7280 | 107,114,128 | Secondary text |
| Border | #E5E7EB | 229,231,235 | Borders |
| Success | #10B981 | 16,185,129 | Positive states |
| Error | #EF4444 | 239,68,68 | Negative states |
| Warning | #F59E0B | 245,158,11 | Warning states |

### Spacing Quick Reference
| Token | Value | Tailwind |
|-------|-------|----------|
| xs | 4px | p-1 |
| sm | 8px | p-2 |
| md | 12px | p-3 |
| lg | 16px | p-4 |
| xl | 20px | p-5 |
| 2xl | 24px | p-6 |
| 3xl | 32px | p-8 |

### Component Dimensions
| Component | Width | Height |
|-----------|-------|--------|
| Sidebar (collapsed) | 80px | 100vh |
| Sidebar (expanded) | 233px | 100vh |
| Mobile Dock | 100% | 64px |
| Metric Card Icon | 32px | 32px |
| User Avatar | 32px | 32px |
| Nav Item Icon | 20px | 20px |

---

---

## 17. Settings Page

### Layout (from settings.css)
```css
/* Side Menu for Settings - Full width fixed sidebar */
.side-menu {
  width: 240px;
  background: white;
  height: 100vh;
  border-right: 1px solid #e5e7eb;
  position: fixed;
  left: 0;
  top: 0;
  z-index: 1000;
}

.main-content {
  margin-left: 240px;
  min-height: 100vh;
  padding: 32px;
  background-color: #f8f9fa;
}
```

### Menu Item Active State
```css
.menu-item.active {
  background: #f5f5f5;
  border-right: 2px solid #EC6019;
}
```

### Settings Section Card
```css
.settings-section {
  background-color: #ffffff;
  border-radius: 12px;
  padding: 32px;
  margin-bottom: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e5e7eb;
}
```

### Property Selection Item
```css
.property-item {
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.property-item:hover,
.property-item.selected {
  border-color: #EC6019;
  background-color: #fef7f4;
}
```

### Notification Toast
```css
.notification-toast {
  position: fixed;
  bottom: 20px;
  right: 20px;
  padding: 16px 24px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 14px;
  z-index: 10000;
  animation: slideIn 0.3s ease;
}

.notification-toast.success {
  background-color: #dcfce7;
  color: #166534;
  border: 1px solid #bbf7d0;
}

.notification-toast.error {
  background-color: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}
```

---

## 18. Dashboard Specifics (from dashboard.css)

### Font Strategy
```css
/* Import fonts */
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@700&family=Nunito:wght@400&display=swap');

/* Poppins = Bold headings (700) */
.user-name, .domain-name, .overview-title, .metric-value {
  font-family: 'Poppins', sans-serif !important;
  font-weight: 700 !important;
}

/* Nunito = Regular body text (400) */
body, .metric-title, .metric-change {
  font-family: 'Nunito', sans-serif;
  font-weight: 400;
}
```

### Welcome Section
```css
.welcome-text {
  font-family: 'Poppins', sans-serif;
  font-size: 1.5rem;
  font-weight: 700;
  color: #1F2937;
}

.domain-name {
  font-family: 'Poppins', sans-serif;
  font-weight: 700;
  color: #EC6019;
}
```

### Metrics Grid
```css
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}
```

### Metric Card Structure
```css
.metric-card {
  background: white;
  border-radius: 0.75rem;  /* 12px */
  padding: 1.5rem;         /* 24px */
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
}

.metric-value {
  font-family: 'Poppins', sans-serif;
  font-size: 2rem;         /* 32px */
  font-weight: 700;
  color: #1F2937;
}

.metric-change.positive { color: #10b981; }
.metric-change.negative { color: #ef4444; }
.metric-change.neutral { color: #1F2937; }
```

### Empty State Canvas
```css
.empty-canvas {
  background: white;
  border-radius: 0.5rem;
  padding: 3rem;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 2px dashed #cbd5e1;
}
```

---

## Complete File Reading Summary

### All 38 Files Read:

| Category | Files | Lines |
|----------|-------|-------|
| JavaScript | 7 | ~5,300 |
| HTML | 6 | ~1,800 |
| CSS | 14 | ~6,500 |
| Images/Assets | 11 | N/A |
| **TOTAL** | **38** | **~13,600** |

### Files Read:
1. `spa-router.js` (2,330 lines)
2. `auth.js` (126 lines)
3. `domain-selection.js` (214 lines)
4. `js/utils/ApiUtils.js` (1,725 lines)
5. `js/utils/ModalUtils.js` (145 lines)
6. `js/components/FilterBar.js` (391 lines)
7. `js/components/DateRangeModal.js` (378 lines)
8. `spa.html` (351 lines)
9. `index.html` (52 lines)
10. `audit-history.html` (534 lines)
11. `property_selection.html` (348 lines)
12. `setup_wizard.html` (478 lines)
13. `domain-selection.html` (49 lines)
14. `style.css` (2,907 lines)
15. `settings.css` (456 lines)
16. `dashboard.css` (301 lines)
17. `domain-selection.css` (251 lines)
18. `styles/sidebar.css`
19. `styles/dashboard.css`
20. `styles/global.css`
21. `styles/main.css`
22. `styles/components.css`
23. `styles/filters.css`
24. `styles/mobile-dock.css`
25. `styles/chat.css`
26. `styles/responsive.css`
27. `styles/modals.css`

---

**Document Version**: 1.1.0
**Created**: 2025-12-01
**Updated**: 2025-12-01 (Added settings.css, dashboard.css specs)
**Based on**: Original Solvia Alpha codebase (38 files)
