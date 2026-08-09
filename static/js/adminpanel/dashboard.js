/* ==========================================================================
   ADMIN DASHBOARD (dashboard.html) - PAGE SPECIFIC JAVASCRIPT
   Features:
   1. Patient Registrations Trend (line chart)
   2. Appointment Status Breakdown (donut chart)
   3. Appointments by Department (bar chart)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    function readJSON(id) {
        var el = document.getElementById(id);
        return el ? JSON.parse(el.textContent) : [];
    }

    if (typeof Chart === 'undefined') return;

    Chart.defaults.font.family = "'Poppins', sans-serif";
    Chart.defaults.color = '#78716c';


    /* ----------------------------------------------------------------------
       1. Patient Registrations Trend
    ---------------------------------------------------------------------- */
    var trendCanvas = document.getElementById('trendChart');
    if (trendCanvas) {
        new Chart(trendCanvas, {
            type: 'line',
            data: {
                labels: readJSON('trendLabelsData'),
                datasets: [{
                    label: 'New Patients',
                    data: readJSON('trendValuesData'),
                    borderColor: '#b45309',
                    backgroundColor: 'rgba(180, 83, 9, 0.12)',
                    tension: 0.35,
                    fill: true,
                    pointBackgroundColor: '#b45309',
                    pointRadius: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: '#f0efed' } },
                    x: { grid: { display: false } },
                }
            }
        });
    }


    /* ----------------------------------------------------------------------
       2. Appointment Status Breakdown
    ---------------------------------------------------------------------- */
    var statusCanvas = document.getElementById('statusChart');
    if (statusCanvas) {
        var statusLabels = readJSON('statusLabelsData');
        new Chart(statusCanvas, {
            type: 'doughnut',
            data: {
                labels: statusLabels,
                datasets: [{
                    data: readJSON('statusValuesData'),
                    backgroundColor: readJSON('statusColorsData'),
                    borderWidth: 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '68%',
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 10, padding: 14 } },
                }
            }
        });

        if (!statusLabels.length) {
            statusCanvas.closest('.chart-wrap').innerHTML = '<p class="text-muted text-center py-5 mb-0">No appointment data yet.</p>';
        }
    }


    /* ----------------------------------------------------------------------
       3. Appointments by Department
    ---------------------------------------------------------------------- */
    var deptCanvas = document.getElementById('departmentChart');
    if (deptCanvas) {
        var deptLabels = readJSON('departmentLabelsData');
        new Chart(deptCanvas, {
            type: 'bar',
            data: {
                labels: deptLabels,
                datasets: [{
                    label: 'Appointments',
                    data: readJSON('departmentValuesData'),
                    backgroundColor: '#d97706',
                    borderRadius: 6,
                    maxBarThickness: 46,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: '#f0efed' } },
                    x: { grid: { display: false } },
                }
            }
        });

        if (!deptLabels.length) {
            deptCanvas.closest('.chart-wrap').innerHTML = '<p class="text-muted text-center py-5 mb-0">No appointment data yet.</p>';
        }
    }

});
