(function () {
  'use strict';

  var API_SERVICES_URL = '/api/services';
  var CHECK_TIMEOUT_MS = 5000;
  var PROBES_COUNT = 3;

  var grid = document.getElementById('service-cards');
  var refreshButton = document.getElementById('refresh-services');
  var bulkCheckButton = document.getElementById('bulk-check-services');
  var serviceCards = [];

  var STATUS_META = {
    pending: { label: 'Ожидает проверки', color: '#6b7280' },
    checking: { label: 'Проверка...', color: '#2563eb' },
    available: { label: 'Доступен', color: '#15803d' },
    degraded: { label: 'Проблемы', color: '#f59e0b' },
    unavailable: { label: 'Недоступен', color: '#b91c1c' },
    timeout: { label: 'Таймаут (5s)', color: '#b45309' },
    network_error: { label: 'Ошибка сети при проверке', color: '#7c2d12' },
    unknown_error: { label: 'Неизвестная ошибка', color: '#7e22ce' }
  };

  function statusInfo(status) { return STATUS_META[status] || { label: status, color: '#111827' }; }

  function notify(kind, message) {
    var wrap = document.getElementById('toast-wrap');
    if (!wrap) return;
    var toast = document.createElement('div');
    toast.className = 'toast toast-' + kind;
    toast.textContent = message;
    wrap.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 2600);
  }

  function setStatus(el, status) {
    var info = statusInfo(status);
    el.textContent = info.label;
    el.className = 'status-pill status-' + status;
    el.dataset.status = status;
  }

  async function checkServiceOnce(service) {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, CHECK_TIMEOUT_MS);

    try {
      var response = await fetch('/api/services/' + service.id + '/check', { method: 'POST', signal: controller.signal });
      clearTimeout(timer);
      if (!response.ok) {
        return { status: 'unavailable', response_time_ms: 0, is_available: false };
      }
      var result = await response.json();
      return {
        status: result.is_available ? 'available' : 'unavailable',
        response_time_ms: result.response_time_ms || 0,
        is_available: Boolean(result.is_available)
      };
    } catch (error) {
      clearTimeout(timer);
      if (error && error.name === 'AbortError') return { status: 'timeout', response_time_ms: CHECK_TIMEOUT_MS, is_available: false };
      if (error instanceof TypeError) return { status: 'network_error', response_time_ms: 0, is_available: false };
      return { status: 'unknown_error', response_time_ms: 0, is_available: false };
    }
  }

  async function runTripleCheck(cardState) {
    var service = cardState.service;
    var checkBtn = cardState.checkBtn;

    checkBtn.disabled = true;
    if (bulkCheckButton) bulkCheckButton.disabled = true;
    setStatus(cardState.statusEl, 'checking');

    var successCount = 0;
    for (var i = 0; i < PROBES_COUNT; i++) {
      cardState.probeEls[i].textContent = 'Проверка...';
      var result = await checkServiceOnce(service);
      if (result.is_available) successCount += 1;
      cardState.probeEls[i].className = 'probe-item probe-' + result.status;
      cardState.probeEls[i].textContent = statusInfo(result.status).label + ' · ' + result.response_time_ms + ' ms';
    }

    if (successCount === PROBES_COUNT) {
      setStatus(cardState.statusEl, 'available');
    } else if (successCount === 0) {
      setStatus(cardState.statusEl, 'unavailable');
    } else {
      setStatus(cardState.statusEl, 'degraded');
    }
    checkBtn.disabled = false;
    if (bulkCheckButton) bulkCheckButton.disabled = false;
  }

  function renderCard(service) {
    var item = document.createElement('li');
    item.className = 'service-card card';

    var titleRow = document.createElement('div');
    titleRow.className = 'service-title-row';

    var title = document.createElement('h3');
    var titleLink = document.createElement('a');
    titleLink.href = '/services/' + service.id;
    titleLink.textContent = service.name;
    title.appendChild(titleLink);

    var status = document.createElement('span');
    setStatus(status, service.last_check_status || 'pending');

    titleRow.append(title, status);

    var link = document.createElement('a');
    link.href = service.url;
    link.target = '_blank';
    link.rel = 'noopener';
    link.textContent = service.url;
    link.className = 'service-url';

    var probes = document.createElement('div');
    probes.className = 'probe-grid';
    var probeEls = [];
    for (var i = 0; i < PROBES_COUNT; i++) {
      var probe = document.createElement('div');
      probe.className = 'probe-item';
      probe.textContent = '—';
      probeEls.push(probe);
      probes.appendChild(probe);
    }

    var actions = document.createElement('div'); actions.className = 'row-actions';
    var checkBtn = document.createElement('button'); checkBtn.textContent = 'Проверить';

    actions.append(checkBtn);
    item.append(titleRow, link, probes, actions);

    var cardState = { service: service, statusEl: status, probeEls: probeEls, checkBtn: checkBtn };
    checkBtn.addEventListener('click', function (event) {
      event.stopPropagation();
      runTripleCheck(cardState);
    });

    item.addEventListener('click', function (event) {
      if (event.target.closest('a, button')) return;
      if (!window.IS_ADMIN) {
        alert("Доступ только для администратора");
        window.location.href = "/admin/login";
        return;
      }

      window.location.href = `/services/${service.id}`;
      });
    serviceCards.push(cardState);

    return item;
  }

  async function addService(event) {
    event.preventDefault();

    var name = serviceNameInput.value.trim();
    var url = serviceUrlInput.value.trim();

    if (!name || !url) {
      notify('error', 'Заполните название и URL');
      return;
    }

    try {
      var response = await fetch(API_SERVICES_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, url: url })
      });

      if (!response.ok) {
        notify('error', 'Не удалось добавить сервис');
        return;
      }

      addServiceForm.reset();
      notify('success', 'Сервис добавлен');
      await loadServices();
    } catch (_) {
      notify('error', 'Ошибка подключения к серверу');
    }
  }

  async function loadServices() {
    if (!grid) return;
    serviceCards = [];
    grid.innerHTML = '<li>Загрузка сервисов...</li>';
    try {
      var response = await fetch(API_SERVICES_URL);
      if (!response.ok) throw new Error('services_failed');
      var services = await response.json();
      if (!Array.isArray(services) || services.length === 0) { grid.innerHTML = '<li>Активные сервисы не найдены.</li>'; return; }
      grid.innerHTML = '';
      services.forEach(function (service) { grid.appendChild(renderCard(service)); });
    } catch (_) {
      grid.innerHTML = '<li class="card">Не удалось загрузить сервисы. Проверьте подключение к серверу.</li>';
      notify('error', 'Ошибка загрузки сервисов');
    }
  }

  async function runBulkChecksSequentially() {
    if (!serviceCards.length) return;
    bulkCheckButton.disabled = true;
    for (var i = 0; i < serviceCards.length; i++) {
      await runTripleCheck(serviceCards[i]);
    }
    bulkCheckButton.disabled = false;
  }

  if (refreshButton) refreshButton.addEventListener('click', loadServices);
  if (bulkCheckButton) bulkCheckButton.addEventListener('click', runBulkChecksSequentially);
  if (addServiceForm) addServiceForm.addEventListener('submit', addService);

  document.addEventListener('DOMContentLoaded', loadServices);

  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) {
      loadServices();
    }
  });
})();
