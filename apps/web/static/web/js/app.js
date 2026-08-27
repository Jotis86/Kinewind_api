(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var alerts = document.querySelectorAll(".alert-autodismiss");
    alerts.forEach(function (alertEl) {
      window.setTimeout(function () {
        bootstrap.Alert.getOrCreateInstance(alertEl).close();
      }, 4000);
    });

    document.querySelectorAll("form[data-auto-filter]").forEach(function (form) {
      var autoFields = form.querySelectorAll(
        'select, input[type="date"], input[type="datetime-local"]'
      );
      autoFields.forEach(function (field) {
        field.addEventListener("change", function () {
          form.submit();
        });
      });
    });

    var tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(function (el) {
      new bootstrap.Tooltip(el);
    });
  });
})();
