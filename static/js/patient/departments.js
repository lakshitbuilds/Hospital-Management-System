document.addEventListener('DOMContentLoaded', function () {
    var modal = document.getElementById('departmentDetailsModal');
    if (!modal) return;

    modal.addEventListener('show.bs.modal', function (event) {
        var button = event.relatedTarget;
        if (!button) return;
        document.getElementById('departmentDetailsTitle').textContent = button.getAttribute('data-department-name');
        document.getElementById('departmentDetailsDescription').textContent = button.getAttribute('data-department-description');
    });
});
