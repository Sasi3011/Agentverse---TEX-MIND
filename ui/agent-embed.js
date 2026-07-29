(function () {
  if (window.self === window.top) return;

  document.documentElement.classList.add('agent-embed');

  function markBody() {
    document.body.classList.add('agent-embed');
  }

  if (document.body) markBody();
  else document.addEventListener('DOMContentLoaded', markBody);

  function syncFixedViewport() {
    if (!document.body.classList.contains('agent-fixed-viewport')) return;
    document.documentElement.classList.add('agent-fixed-viewport');
  }

  syncFixedViewport();
  document.addEventListener('DOMContentLoaded', syncFixedViewport);
})();
