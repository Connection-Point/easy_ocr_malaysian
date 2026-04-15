// Navigation
document.querySelectorAll('.nav-links li').forEach(link => {
    link.addEventListener('click', () => {
        document.querySelectorAll('.nav-links li').forEach(l => l.classList.remove('active'));
        document.querySelectorAll('.view-section').forEach(v => v.classList.remove('active'));
        
        link.classList.add('active');
        const target = link.getAttribute('data-target');
        document.getElementById(target).classList.add('active');

        // Load specific data depending on view
        if (target === 'dashboard-view') loadDashboard();
        if (target === 'scheme-view') loadSchemes();
        if (target === 'sysparam-view') loadSysparams();
        if (target === 'records-view') loadRecords();
    });
});

// Toast
function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.style.borderLeftColor = isError ? 'var(--danger)' : 'var(--success)';
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// Modals
let currentEditingId = null;

function openModal(modalId, type, data = null) {
    document.getElementById('modal-overlay').classList.add('active');
    document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
    document.getElementById(modalId).classList.add('active');
    
    // Reset form
    document.getElementById(`${type}-form`).reset();
    currentEditingId = null;

    if (data) {
        currentEditingId = data.id || data.param_code;
        Object.keys(data).forEach(key => {
            const input = document.getElementById(key);
            if (input) input.value = data[key];
        });
    }
}

function closeModal() {
    document.getElementById('modal-overlay').classList.remove('active');
    document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
}

// API Fetch Helpers
async function callApi(url, method = 'GET', body = null) {
    try {
        const options = { method, headers: { 'Content-Type': 'application/json' } };
        if (body) options.body = JSON.stringify(body);
        const res = await fetch(url, options);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'API Error');
        return data;
    } catch (e) {
        showToast(e.message, true);
        throw e;
    }
}

// --- Load Content ---

function getStatusBadge(code, name) {
    return `<span class="badge ${code == 1 ? 'success' : 'neutral'}">${name}</span>`;
}

function getPaymentBadge(code, name) {
    return `<span class="badge ${code == 4 ? 'success' : 'warning'}">${name}</span>`;
}

let entriesChartInstance = null;
let revenueChartInstance = null;

async function loadDashboard() {
    const data = await callApi('/api/dashboard');
    currentScheme = data.scheme;
    
    // Stats
    document.getElementById('dash-scheme-name').innerText = currentScheme ? currentScheme.scheme_name : 'N/A';
    document.getElementById('dash-scheme-rates').innerText = currentScheme ? `RM ${currentScheme.first_hour_rate} / RM ${currentScheme.additional_hour_rate}` : 'N/A';
    
    // Entries Chart
    if (entriesChartInstance) entriesChartInstance.destroy();
    Chart.defaults.color = '#94a3b8';
    const ctxEntries = document.getElementById('entriesChart').getContext('2d');
    entriesChartInstance = new Chart(ctxEntries, {
        type: 'bar',
        data: {
            labels: ['10 Mins', '1 Hour', '3 Hours', '24 Hours', '1 Week'],
            datasets: [{
                label: 'Total Entries',
                data: [data.counts['10m'], data.counts['1h'], data.counts['3h'], data.counts['24h'], data.counts['1w']],
                backgroundColor: 'rgba(129, 140, 248, 0.4)',
                borderColor: 'rgba(129, 140, 248, 1)',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: '#334155' } }, x: { grid: { display: false } } } }
    });

    // Revenue Chart (now loaded via dedicated function)
    loadRevenueChart();

    // Table
    const tbody = document.getElementById('dashboard-table-body');
    tbody.innerHTML = '';
    data.records.slice(0, 10).forEach(r => {
        tbody.innerHTML += `
            <tr>
                <td><strong>${r.plate_number}</strong></td>
                <td>${r.in_time || 'N/A'}</td>
                <td>${r.out_time || '---'}</td>
                <td style="color:var(--warning);font-weight:bold;">RM ${r.fee ? parseFloat(r.fee).toFixed(2) : '0.00'}</td>
                <td>${getStatusBadge(r.status_code, r.status_name)}</td>
                <td>${getPaymentBadge(r.payment_status_code, r.payment_name)}</td>
                <td>
                    <button class="btn" style="padding:4px 8px;font-size:0.8rem" onclick="openModal('record-modal', 'record', ${JSON.stringify(r).replace(/"/g, '&quot;')})"><i class="fa-solid fa-pen"></i></button>
                    <button class="btn danger" style="padding:4px 8px;font-size:0.8rem" onclick="deleteItem('dashboard_record', ${r.id})"><i class="fa-solid fa-trash"></i></button>
                </td>
            </tr>
        `;
    });
}

// Global reference for generating modal opens
let globalData = { scheme: [], sysparam: [], record: [] };

async function loadRevenueChart() {
    const filter = document.getElementById('revenue-filter').value;
    const rawData = await callApi(`/api/revenue?filter=${filter}`);
    
    if (revenueChartInstance) revenueChartInstance.destroy();
    const ctxRevenue = document.getElementById('revenueChart').getContext('2d');
    revenueChartInstance = new Chart(ctxRevenue, {
        type: 'line',
        data: {
            labels: rawData.length > 0 ? rawData.map(r => r.label) : ['No Data'],
            datasets: [{
                label: 'Revenue (RM)',
                data: rawData.length > 0 ? rawData.map(r => r.revenue) : [0],
                borderColor: 'rgba(16, 185, 129, 1)',
                backgroundColor: 'rgba(16, 185, 129, 0.2)',
                fill: true,
                tension: 0.3,
                pointBackgroundColor: 'rgba(16, 185, 129, 1)'
            }]
        },
        options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: '#334155' } }, x: { grid: { color: '#334155' } } } }
    });
}

async function loadSchemes() {
    globalData.scheme = await callApi('/api/scheme');
    const tbody = document.getElementById('scheme-table-body');
    tbody.innerHTML = '';
    globalData.scheme.forEach(s => {
        tbody.innerHTML += `
            <tr>
                <td>${s.id}</td>
                <td><strong>${s.scheme_name}</strong></td>
                <td>RM ${s.first_hour_rate.toFixed(2)}</td>
                <td>RM ${s.additional_hour_rate.toFixed(2)}</td>
                <td>${s.grace_period_mins} m</td>
                <td>
                    <button class="btn" style="padding:4px 8px;font-size:0.8rem" onclick="openModal('scheme-modal', 'scheme', ${JSON.stringify(s).replace(/"/g, '&quot;')})"><i class="fa-solid fa-pen"></i></button>
                    <button class="btn danger" style="padding:4px 8px;font-size:0.8rem" onclick="deleteItem('scheme', ${s.id})"><i class="fa-solid fa-trash"></i></button>
                </td>
            </tr>
        `;
    });
}

async function loadSysparams() {
    globalData.sysparam = await callApi('/api/sysparam');
    const tbody = document.getElementById('sysparam-table-body');
    tbody.innerHTML = '';
    globalData.sysparam.forEach(s => {
        tbody.innerHTML += `
            <tr>
                <td>${s.param_code}</td>
                <td>${s.param_name}</td>
                <td>
                    <button class="btn" style="padding:4px 8px;font-size:0.8rem" onclick="openModal('sysparam-modal', 'sysparam', ${JSON.stringify(s).replace(/"/g, '&quot;')})"><i class="fa-solid fa-pen"></i></button>
                    <button class="btn danger" style="padding:4px 8px;font-size:0.8rem" onclick="deleteItem('sysparam', ${s.param_code})"><i class="fa-solid fa-trash"></i></button>
                </td>
            </tr>
        `;
    });
}

async function loadRecords() {
    globalData.record = await callApi('/api/records');
    const tbody = document.getElementById('records-table-body');
    tbody.innerHTML = '';
    globalData.record.forEach(r => {
        tbody.innerHTML += `
            <tr>
                <td>${r.id}</td>
                <td><strong>${r.plate_number}</strong></td>
                <td>${r.in_time}</td>
                <td>${r.out_time || '---'}</td>
                <td>RM ${r.fee ? parseFloat(r.fee).toFixed(2) : '0.00'}</td>
                <td>${r.status_code}</td>
                <td>${r.payment_status_code}</td>
                <td>
                    <button class="btn" style="padding:4px 8px;font-size:0.8rem" onclick="openModal('record-modal', 'record', ${JSON.stringify(r).replace(/"/g, '&quot;')})"><i class="fa-solid fa-pen"></i></button>
                    <button class="btn danger" style="padding:4px 8px;font-size:0.8rem" onclick="deleteItem('record', ${r.id})"><i class="fa-solid fa-trash"></i></button>
                </td>
            </tr>
        `;
    });
}


// --- Form Submits & Actions ---

async function submitForm(e, type) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    
    // Type coercions
    if(type === 'sysparam') { data.param_code = parseInt(data.param_code); }
    if(type === 'scheme') { 
        data.first_hour_rate = parseFloat(data.first_hour_rate); 
        data.additional_hour_rate = parseFloat(data.additional_hour_rate); 
        data.grace_period_mins = parseInt(data.grace_period_mins); 
        if(currentEditingId) data.id = parseInt(currentEditingId);
    }
    if(type === 'record') {
        data.fee = parseFloat(data.fee);
        data.status_code = parseInt(data.status_code);
        data.payment_status_code = parseInt(data.payment_status_code);
        if(!data.out_time) data.out_time = null;
        if(currentEditingId) data.id = parseInt(currentEditingId);
    }

    try {
        if (currentEditingId) {
            await callApi(`/api/${type}/${currentEditingId}`, 'PUT', data);
        } else {
            await callApi(`/api/${type}`, 'POST', data);
        }
        showToast(`Successfully saved ${type}`);
        closeModal();
        
        // Reload current view
        if(type === 'scheme') loadSchemes();
        if(type === 'sysparam') loadSysparams();
        if(type === 'record') { loadRecords(); loadDashboard(); }

    } catch (err) {
        console.error(err);
    }
}

async function deleteItem(type, id) {
    if(!confirm('Are you sure you want to delete this item?')) return;
    try {
        const actualType = type === 'dashboard_record' ? 'record' : type;
        await callApi(`/api/${actualType}/${id}`, 'DELETE');
        showToast('Item deleted');
        if(type === 'scheme') loadSchemes();
        if(type === 'sysparam') loadSysparams();
        if(type === 'record') loadRecords();
        if(type === 'dashboard_record') loadDashboard();
    } catch (err) {
        console.error(err);
    }
}

// Initial Load
document.addEventListener('DOMContentLoaded', loadDashboard);
