// ==================== DATA ====================
let currentPage = 'home';
let isLoggedIn = false;
let isAdmin = false;
let selectedDisasterType = null;

let disasters = [
    {
        id: 1,
        type: 'fire',
        location: 'Downtown District, City Center',
        lat: 28.6139,
        lng: 77.2090,
        time: '2 minutes ago',
        severity: 'critical',
        description: 'Large industrial fire near warehouse complex',
        verified: true
    },
    {
        id: 2,
        type: 'earthquake',
        location: 'Northern Region, Mountains',
        lat: 32.1765,
        lng: 77.1734,
        time: '15 minutes ago',
        severity: 'high',
        description: 'Magnitude 5.2 earthquake detected',
        verified: true
    },
    {
        id: 3,
        type: 'landslide',
        location: 'Hillside Avenue, Suburbs',
        lat: 28.5244,
        lng: 77.0855,
        time: '45 minutes ago',
        severity: 'medium',
        description: 'Soil movement detected after heavy rainfall',
        verified: false
    }
];

let reports = [
    { id: 1, type: 'fire', location: 'Downtown', time: '10:30 AM', status: 'approved', reporter: 'User123', severity: 'high' },
    { id: 2, type: 'earthquake', location: 'North City', time: '10:15 AM', status: 'pending', reporter: 'NGO_Relief', severity: 'critical' },
    { id: 3, type: 'landslide', location: 'Mountain Road', time: '09:45 AM', status: 'rejected', reporter: 'User456', severity: 'medium' }
];

// ==================== PAGE NAVIGATION ====================
function switchPage(page) {
    currentPage = page;

    // Hide all pages
    const pages = document.querySelectorAll('.page');
    pages.forEach(p => p.classList.remove('active'));

    // Show selected page
    const selectedPage = document.querySelector(`[data-page="${page}"].page`);
    if (selectedPage) {
        selectedPage.classList.add('active');
    }

    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === page) {
            item.classList.add('active');
        }
    });

    // Close mobile menu after navigation
    closeMobileMenu();

    // Render page content
    switch(page) {
        case 'home':
            renderHome();
            break;
        case 'alerts':
            renderAlerts();
            break;
        case 'report':
            renderReport();
            break;
        case 'localarea':
            renderLocalArea();
            break;
        case 'admin':
            if (isAdmin) {
                renderAdmin();
            } else {
                alert('Admin access only!');
                switchPage('home');
            }
            break;
    }

    // Scroll to top
    window.scrollTo(0, 0);
}

// ==================== MOBILE MENU ====================
function openMobileMenu() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.add('open');
    }
}

function closeMobileMenu() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.remove('open');
    }
}

// ==================== HOME PAGE ====================
function renderHome() {
    const grid = document.getElementById('disastersGrid');
    if (grid) {
        grid.innerHTML = disasters.slice(0, 3).map(disaster => createDisasterCard(disaster)).join('');
    }

    // Update stats
    const activeStat = document.getElementById('activeStat');
    const verifiedStat = document.getElementById('verifiedStat');
    const pendingStat = document.getElementById('pendingStat');
    const approvedStat = document.getElementById('approvedStat');
    const disasterCount = document.getElementById('disasterCount');

    if (activeStat) activeStat.textContent = disasters.length;
    if (verifiedStat) verifiedStat.textContent = disasters.filter(d => d.verified).length;
    if (pendingStat) pendingStat.textContent = reports.filter(r => r.status === 'pending').length;
    if (approvedStat) approvedStat.textContent = reports.filter(r => r.status === 'approved').length;
    if (disasterCount) disasterCount.textContent = disasters.length;
}

function createDisasterCard(disaster) {
    const severityClass = disaster.severity === 'critical' ? 'critical' : disaster.severity;
    const icon = disaster.type === 'fire' ? '🔥' : disaster.type === 'earthquake' ? '🌍' : '⛰️';

    return `
        <div class="disaster-card ${severityClass}">
            <div class="disaster-header">
                <span class="disaster-icon">${icon}</span>
                ${disaster.verified ? '<span class="verified-badge">✓ VERIFIED</span>' : ''}
            </div>
            <h3 class="disaster-location">${disaster.location}</h3>
            <p class="disaster-description">${disaster.description}</p>
            <div class="disaster-time">
                <span>🕐</span>
                ${disaster.time}
            </div>
        </div>
    `;
}

// ==================== REPORT PAGE ====================
function renderReport() {
    // This page contains the form - just make sure it's visible
    const reportForm = document.getElementById('reportForm');
    if (reportForm) {
        reportForm.reset();
        document.querySelectorAll('.disaster-type-btn').forEach(b => b.classList.remove('selected'));
        document.getElementById('fileSelected').innerHTML = '';
        selectedDisasterType = null;
    }
}

// ==================== REPORT FORM ====================
document.addEventListener('DOMContentLoaded', () => {
    // Disaster type buttons
    document.querySelectorAll('.disaster-type-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            document.querySelectorAll('.disaster-type-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            selectedDisasterType = btn.dataset.type;
            const selectedTypeInput = document.getElementById('selectedType');
            if (selectedTypeInput) {
                selectedTypeInput.value = selectedDisasterType;
            }
        });
    });

    // File input
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files[0]) {
                document.getElementById('fileSelected').innerHTML = `<p class="file-selected">✓ ${e.target.files[0].name} selected</p>`;
            }
        });
    }

    // Report form submit
    const reportForm = document.getElementById('reportForm');
    if (reportForm) {
        reportForm.addEventListener('submit', handleReportSubmit);
    }

    // Navigation items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const page = item.dataset.page;
            if (page) {
                switchPage(page);
            }
        });
    });

    // Action cards
    document.querySelectorAll('.action-card').forEach(card => {
        card.addEventListener('click', () => {
            const page = card.dataset.page;
            if (page) {
                switchPage(page);
            }
        });
    });

    // Toggle button
    const toggleBtn = document.getElementById('toggleBtn');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', openMobileMenu);
    }

    // Close menu button
    const closeBtn = document.getElementById('closeBtn');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeMobileMenu);
    }

    // Login button
    const loginBtn = document.getElementById('loginBtn');
    if (loginBtn) {
        loginBtn.addEventListener('click', handleLogin);
    }

    // Logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        const sidebar = document.getElementById('sidebar');
        const toggleBtn = document.getElementById('toggleBtn');
        if (sidebar && toggleBtn && !sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
            closeMobileMenu();
        }
    });

    // Initial render
    renderHome();
});

function handleReportSubmit(e) {
    e.preventDefault();

    if (!selectedDisasterType) {
        alert('Please select a disaster type');
        return;
    }

    const locationInput = document.getElementById('locationInput');
    const descriptionInput = document.getElementById('descriptionInput');
    const ngoCheckbox = document.getElementById('ngoCheckbox');

    const location = locationInput ? locationInput.value : '';
    const description = descriptionInput ? descriptionInput.value : '';
    const isNGO = ngoCheckbox ? ngoCheckbox.checked : false;

    if (!location || !description) {
        alert('Please fill all required fields');
        return;
    }

    // Create new disaster
    const newDisaster = {
        id: disasters.length + 1,
        type: selectedDisasterType,
        location: location,
        lat: 28.6139 + Math.random() * 0.1,
        lng: 77.2090 + Math.random() * 0.1,
        time: 'just now',
        severity: 'medium',
        description: description,
        verified: isNGO
    };

    disasters.unshift(newDisaster);

    // Reset form
    document.getElementById('reportForm').reset();
    document.querySelectorAll('.disaster-type-btn').forEach(b => b.classList.remove('selected'));
    document.getElementById('fileSelected').innerHTML = '';
    selectedDisasterType = null;

    // Show notification
    showNotification('Report submitted successfully!');

    // Switch to home
    setTimeout(() => {
        switchPage('home');
    }, 1500);
}

// ==================== ALERTS PAGE ====================
function renderAlerts() {
    const feedList = document.getElementById('feedList');
    if (!feedList) return;

    feedList.innerHTML = disasters.map(disaster => {
        const severityClass = disaster.severity === 'critical' ? 'critical' : disaster.severity;
        const icon = disaster.type === 'fire' ? '🔥' : disaster.type === 'earthquake' ? '🌍' : '⛰️';

        return `
            <div class="alert-item ${severityClass}">
                <span class="alert-icon">${icon}</span>
                <div class="alert-content">
                    <div class="alert-header">
                        <h3 class="alert-title">${disaster.location}</h3>
                        ${disaster.verified ? '<span class="alert-badge">✓ VERIFIED</span>' : ''}
                    </div>
                    <p class="alert-description">${disaster.description}</p>
                    <div class="alert-meta">
                        <span>🕐 ${disaster.time}</span>
                        <span>🎯 ${disaster.severity.toUpperCase()}</span>
                    </div>
                </div>
                <span class="alert-bell">🔔</span>
            </div>
        `;
    }).join('');
}

// ==================== LOCAL AREA PAGE ====================
function renderLocalArea() {
    const grid = document.getElementById('localDisastersGrid');
    if (!grid) return;

    grid.innerHTML = disasters.map(disaster => createDisasterCard(disaster)).join('');

    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            // Add filtering logic here
        });
    });
}

// ==================== ADMIN PANEL ====================
function renderAdmin() {
    if (!isAdmin) {
        alert('Admin access required!');
        return;
    }

    const reportsList = document.getElementById('reportsList');
    if (!reportsList) return;

    renderAdminTab('pending');

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderAdminTab(btn.dataset.tab);
        });
    });
}

function renderAdminTab(tab) {
    const reportsList = document.getElementById('reportsList');
    if (!reportsList) return;

    const filteredReports = reports.filter(r => r.status === tab);

    reportsList.innerHTML = filteredReports.map(report => {
        const icon = report.type === 'fire' ? '🔥' : report.type === 'earthquake' ? '🌍' : '⛰️';

        return `
            <div class="report-item">
                <div class="report-header">
                    <div class="report-info">
                        <span class="report-icon">${icon}</span>
                        <div class="report-details">
                            <h3>${report.location} - ${report.type.toUpperCase()}</h3>
                            <p>Reporter: ${report.reporter} • ${report.time}</p>
                        </div>
                    </div>
                    <span class="status-badge status-${report.status}">${report.status.toUpperCase()}</span>
                </div>
                ${report.status === 'pending' ? `
                    <div class="action-buttons">
                        <button class="approve-btn" onclick="approveReport(${report.id})">
                            ✓ APPROVE
                        </button>
                        <button class="reject-btn" onclick="rejectReport(${report.id})">
                            ✕ REJECT
                        </button>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

function approveReport(id) {
    reports = reports.map(r => r.id === id ? { ...r, status: 'approved' } : r);
    renderAdminTab('pending');
    showNotification('Report approved!');
}

function rejectReport(id) {
    reports = reports.map(r => r.id === id ? { ...r, status: 'rejected' } : r);
    renderAdminTab('pending');
    showNotification('Report rejected!');
}

// ==================== NOTIFICATIONS ====================
function showNotification(message) {
    const notification = document.getElementById('notification');
    const notificationMessage = document.getElementById('notificationMessage');

    if (notification && notificationMessage) {
        notificationMessage.textContent = message;
        notification.style.display = 'flex';
        notification.classList.remove('hide');

        setTimeout(() => {
            notification.classList.add('hide');
            setTimeout(() => {
                notification.style.display = 'none';
            }, 300);
        }, 3000);
    }
}

// ==================== LOGIN/LOGOUT ====================
function handleLogin() {
    isLoggedIn = true;
    isAdmin = confirm('Login as admin?');

    const loginBtn = document.getElementById('loginBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const adminBtn = document.querySelector('[data-page="admin"]');

    if (loginBtn) loginBtn.style.display = 'none';
    if (logoutBtn) logoutBtn.style.display = 'flex';

    if (isAdmin && adminBtn) {
        adminBtn.style.display = 'flex';
    }

    showNotification(isAdmin ? 'Logged in as Admin!' : 'Logged in successfully!');
}

function handleLogout() {
    isLoggedIn = false;
    isAdmin = false;

    const loginBtn = document.getElementById('loginBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const adminBtn = document.querySelector('[data-page="admin"]');

    if (logoutBtn) logoutBtn.style.display = 'none';
    if (loginBtn) loginBtn.style.display = 'block';
    if (adminBtn) adminBtn.style.display = 'none';

    switchPage('home');
    showNotification('Logged out successfully!');
}
