(function () {
  'use strict';

  var PAGE_LOAD_START = (window.performance && performance.timeOrigin) || Date.now();
  function getEndpoint() {
    if (window.MONITOR_ENDPOINT) {
      return window.MONITOR_ENDPOINT;
    }
    if (window.location && window.location.pathname === '/demo') {
      return '/demo-api/client-events';
    }
    return '/api/client-events';
  }

  function getServiceId() {
    if ((!window.MONITOR_SERVICE_ID || window.MONITOR_SERVICE_ID === '') && window.location && window.location.pathname === '/demo') {
      return 999;
    }
    var raw = window.MONITOR_SERVICE_ID;
    var parsed = Number(raw);

    if (!Number.isFinite(parsed) || parsed <= 0) {
      return null;
    }

    return Math.trunc(parsed);
  }

  function getBrowserName() {
    var ua = navigator.userAgent || '';

    if (ua.indexOf('Edg/') !== -1) return 'Edge';
    if (ua.indexOf('OPR/') !== -1 || ua.indexOf('Opera') !== -1) return 'Opera';
    if (ua.indexOf('Chrome/') !== -1) return 'Chrome';
    if (ua.indexOf('Safari/') !== -1 && ua.indexOf('Chrome/') === -1) return 'Safari';
    if (ua.indexOf('Firefox/') !== -1) return 'Firefox';

    return 'Other';
  }

  function getDeviceType() {
    var ua = navigator.userAgent || '';
    var isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua);
    return isMobile ? 'mobile' : 'desktop';
  }

  function getLoadTimeMs() {
    if (window.performance && performance.timing && performance.timing.navigationStart > 0) {
      var timing = performance.timing;
      if (timing.loadEventEnd > 0) {
        return Math.max(0, timing.loadEventEnd - timing.navigationStart);
      }
      if (timing.domComplete > 0) {
        return Math.max(0, timing.domComplete - timing.navigationStart);
      }
    }

    return Math.max(0, Date.now() - PAGE_LOAD_START);
  }

  function buildPayload(eventType, errorText) {
    var eventPayload = {
      page_url: window.location.href,
      load_time_ms: getLoadTimeMs(),
      error_text: errorText || null,
      browser_name: getBrowserName(),
      device_type: getDeviceType(),
      is_offline: !navigator.onLine,
    };

    var serviceId = getServiceId();
    if (serviceId === null) {
      return null;
    }

    return {
      service_id: serviceId,
      event_type: eventType,
      payload: eventPayload,
    };
  }

  function sendEvent(eventType, errorText) {
    var payload = buildPayload(eventType, errorText);
    if (!payload) {
      return;
    }
    var body = JSON.stringify(payload);

    try {
      if (navigator.sendBeacon) {
        var blob = new Blob([body], { type: 'application/json' });
        var sent = navigator.sendBeacon(getEndpoint(), blob);
        if (sent) {
          return;
        }
      }
    } catch (e) {
      // fallback to fetch below
    }

    if (window.fetch) {
      fetch(getEndpoint(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body,
        keepalive: true,
      }).catch(function () {
        // ignore network errors intentionally
      });
    }
  }

  window.addEventListener('load', function () {
    sendEvent('page_load', null);
  });

  window.addEventListener('error', function (event) {
    var message = event && event.message ? String(event.message) : 'Unknown JavaScript error';
    sendEvent('js_error', message);
  });

  window.addEventListener('unhandledrejection', function (event) {
    var reason = event && event.reason;
    var message = 'Unhandled promise rejection';

    if (typeof reason === 'string') {
      message = reason;
    } else if (reason && reason.message) {
      message = String(reason.message);
    }

    sendEvent('promise_error', message);
  });

  window.addEventListener('offline', function () {
    sendEvent('offline', null);
  });
})();
