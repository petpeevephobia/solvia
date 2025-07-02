// Dashboard Debug Script
// Paste this into the browser console on the dashboard page to debug data loading

console.log('=== DASHBOARD DEBUG SCRIPT ===');

// Check if the page has loaded
console.log('1. Page state:');
console.log('- Document ready:', document.readyState);
console.log('- Auth token:', localStorage.getItem('auth_token') ? 'Present' : 'Missing');

// Check global variables
console.log('2. Global variables:');
console.log('- window.metricsData:', window.metricsData);

// Check if dashboard init functions exist
console.log('3. Dashboard functions:');
console.log('- initDashboard:', typeof window.initDashboard);
console.log('- loadRealMetrics:', typeof window.loadRealMetrics);
console.log('- checkGSCConnection:', typeof window.checkGSCConnection);
console.log('- updateDashboardMetricsWithRealData:', typeof window.updateDashboardMetricsWithRealData);

// Test API endpoints manually
async function testAPIs() {
    console.log('4. Testing API endpoints:');
    
    const token = localStorage.getItem('auth_token');
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };

    try {
        // Test GSC properties
        console.log('- Testing /auth/gsc/properties...');
        const gscResponse = await fetch('/auth/gsc/properties', { headers });
        console.log('  Status:', gscResponse.status);
        if (gscResponse.ok) {
            const gscData = await gscResponse.json();
            console.log('  Data:', gscData);
            console.log('  Number of properties:', gscData.length);
        } else {
            const error = await gscResponse.text();
            console.log('  Error:', error);
        }

        // Test GSC metrics
        console.log('- Testing /auth/gsc/metrics...');
        const metricsResponse = await fetch('/auth/gsc/metrics', { headers });
        console.log('  Status:', metricsResponse.status);
        if (metricsResponse.ok) {
            const metricsData = await metricsResponse.json();
            console.log('  Data:', metricsData);
            console.log('  Summary data available:', !!metricsData.summary);
            console.log('  Time series data available:', !!metricsData.time_series);
            if (metricsData.summary) {
                console.log('  - Impressions:', metricsData.summary.total_impressions);
                console.log('  - Clicks:', metricsData.summary.total_clicks);
                console.log('  - CTR:', metricsData.summary.avg_ctr);
                console.log('  - Position:', metricsData.summary.avg_position);
            }
        } else {
            const error = await metricsResponse.text();
            console.log('  Error:', error);
        }

        

        // Test PageSpeed metrics
        console.log('- Testing /auth/pagespeed/metrics...');
        const psiResponse = await fetch('/auth/pagespeed/metrics', { headers });
        console.log('  Status:', psiResponse.status);
        if (psiResponse.ok) {
            const psiData = await psiResponse.json();
            console.log('  Data:', psiData);
            console.log('  Performance score:', psiData.performance_score);
        } else {
            const error = await psiResponse.text();
            console.log('  Error:', error);
        }

        // Test user website
        console.log('- Testing /auth/website...');
        const websiteResponse = await fetch('/auth/website', { headers });
        console.log('  Status:', websiteResponse.status);
        if (websiteResponse.ok) {
            const websiteData = await websiteResponse.json();
            console.log('  Data:', websiteData);
        } else {
            const error = await websiteResponse.text();
            console.log('  Error:', error);
        }

    } catch (error) {
        console.error('API test error:', error);
    }
}

// Check DOM elements
console.log('5. Checking key DOM elements:');
const elements = [
    'seoScore',
    'impressionsValue', 
    'clicksValue',
    'ctrValue',
    'avgPositionValue',
    'gscBanner',
    'refreshBtn',
    'websiteInfo',
    'dateRangeInfo'
];

elements.forEach(id => {
    const element = document.getElementById(id);
    console.log(`- ${id}:`, element ? 'Found' : 'Missing', element?.textContent || element?.style?.display);
});

// Check if GSC banner is showing
const gscBanner = document.getElementById('gscBanner');
if (gscBanner) {
    console.log('6. GSC Banner status:');
    console.log('- Visible:', !gscBanner.classList.contains('hidden'));
    console.log('- Classes:', gscBanner.className);
}

// Test the dashboard initialization manually
async function testDashboardInit() {
    console.log('7. Testing dashboard initialization:');
    
    try {
        if (typeof window.checkGSCConnection === 'function') {
            console.log('- Running checkGSCConnection...');
            const hasGSC = await window.checkGSCConnection();
            console.log('- GSC Connection result:', hasGSC);
            
            if (hasGSC && typeof window.loadRealMetrics === 'function') {
                console.log('- Running loadRealMetrics...');
                await window.loadRealMetrics();
                console.log('- loadRealMetrics completed');
            }
        } else {
            console.log('- checkGSCConnection function not available');
        }
    } catch (error) {
        console.error('Dashboard init test error:', error);
    }
}

// Run API tests
testAPIs();

// Test dashboard init after a short delay
setTimeout(testDashboardInit, 1000);

console.log('=== END DEBUG SCRIPT ===');
console.log('Check the output above for any issues. Look for:');
console.log('- Missing auth token');
console.log('- API endpoints returning errors');
console.log('- Missing DOM elements');
console.log('- Empty or malformed data');
console.log('- GSC banner showing when it should not');
console.log('- Dashboard functions not defined'); 