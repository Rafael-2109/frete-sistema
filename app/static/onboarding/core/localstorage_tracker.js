// app/static/onboarding/core/localstorage_tracker.js
(function (window) {
  'use strict';

  function key(modulo, tourId, userId) {
    return 'onboarding.' + modulo + '.' + tourId + '.u' + userId;
  }

  function getUserId() {
    return (window.OnboardingContext && window.OnboardingContext.user_id) || 0;
  }

  function moduloFromTourId(tourId) {
    var idx = tourId.indexOf('.');
    return idx > 0 ? tourId.substring(0, idx) : tourId;
  }

  window.OnboardingTracker = {
    wasSeen: function (tourId) {
      var userId = getUserId();
      var modulo = moduloFromTourId(tourId);
      var v = window.localStorage.getItem(key(modulo, tourId, userId));
      return v === 'visto' || v === 'pulou';
    },
    markSeen: function (tourId, status) {
      var userId = getUserId();
      var modulo = moduloFromTourId(tourId);
      window.localStorage.setItem(key(modulo, tourId, userId), status || 'visto');
    },
    resetModule: function (modulo) {
      var userId = getUserId();
      var prefix = 'onboarding.' + modulo + '.';
      var suffix = '.u' + userId;
      var toRemove = [];
      for (var i = 0; i < window.localStorage.length; i++) {
        var k = window.localStorage.key(i);
        if (k.indexOf(prefix) === 0 && k.indexOf(suffix) === k.length - suffix.length) {
          toRemove.push(k);
        }
      }
      toRemove.forEach(function (k) { window.localStorage.removeItem(k); });
      return toRemove.length;
    }
  };
})(window);
