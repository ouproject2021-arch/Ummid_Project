document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form').forEach(function(form) {
        form.addEventListener('submit', function() {
            var btn = form.querySelector('button[type="submit"]');
            if (btn && !btn.classList.contains('inline-button')) {
                btn.dataset.originalText = btn.innerText;
                btn.innerText = 'Please wait...';
                setTimeout(function(){ btn.disabled = true; }, 20);
            }
        });
    });
});

function filterRecordsTable() {
    var input = document.getElementById('recordSearch');
    var table = document.getElementById('recordsTable');
    if (!input || !table) return;

    var filter = input.value.toLowerCase();
    var rows = table.getElementsByTagName('tr');

    for (var i = 1; i < rows.length; i++) {
        var txt = rows[i].innerText.toLowerCase();
        rows[i].style.display = txt.indexOf(filter) > -1 ? '' : 'none';
    }
}
