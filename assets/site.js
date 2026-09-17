/* felicianevin.com — shared behavior: headline rotator, scroll reveal, mobile menu, lead forms */
(function () {
  // Paste the Google Apps Script web app URL here after deploying backend/Code.gs
  var ENDPOINT = 'https://script.google.com/macros/s/AKfycbxcgZOVJZVFRWpZRE_aQkX6pYLrqRjYGlFDQGDGPIN9L9Ohf7BpgSSAR7jsuD43UyR-/exec';

  var loadedAt = Date.now();

  // ---- rotating city in the headline ----
  var rot = document.querySelector('[data-rot]');
  var calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (rot && !calm) {
    var cities = ['Roseville', 'Sacramento', 'Folsom', 'Rocklin', 'El Dorado Hills', 'Lincoln', 'Auburn', 'Elk Grove'], ci = 0;
    setInterval(function () {
      ci = (ci + 1) % cities.length;
      rot.style.opacity = 0;
      setTimeout(function () { rot.textContent = cities[ci]; rot.style.opacity = 1; }, 180);
    }, 2400);
  }

  // ---- reveal sections as they scroll in ----
  if ('IntersectionObserver' in window && !calm) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
    }, { threshold: 0.12 });
    document.querySelectorAll('section:not(.hero):not(.page-head) .sec-head, .steps, .grid3, .grid2, .embed, .why, .areas').forEach(function (el) {
      if (el.getBoundingClientRect().top < window.innerHeight) return; // already on screen: leave it alone
      el.classList.add('rv'); io.observe(el);
    });
    // safety net: never leave content hidden
    setTimeout(function () { document.querySelectorAll('.rv').forEach(function (el) { el.classList.add('in'); }); }, 6000);
  }

  // ---- mobile menu ----
  var menu = document.getElementById('menu'), links = document.getElementById('navlinks');
  if (menu && links) menu.addEventListener('click', function () {
    var open = links.classList.toggle('open');
    menu.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  // ---- remember how the visitor arrived (for lead source tracking) ----
  var qs = new URLSearchParams(location.search), track = {};
  ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content'].forEach(function (k) {
    var v = qs.get(k);
    try { if (v) sessionStorage.setItem('fn-' + k, v); else v = sessionStorage.getItem('fn-' + k); } catch (e) {}
    if (v) track[k] = v;
  });
  var intentParam = qs.get('intent');

  // ---- lead forms ----
  document.querySelectorAll('form.lead-form').forEach(function (form) {
    if (intentParam) {
      var r = form.querySelector('input[name="intent"][value="' + intentParam.replace(/[^A-Za-z]/g, '') + '"]');
      if (r) r.checked = true;
    }
    var msg = form.querySelector('.form-msg'), btn = form.querySelector('button[type="submit"]');
    function say(text) { msg.textContent = text; msg.classList.add('show'); }

    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var f = new FormData(form);
      var name = (f.get('name') || '').trim(), email = (f.get('email') || '').trim(), phone = (f.get('phone') || '').trim();
      if (!name) return say('Please add your name so I know who to reach out to.');
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return say('Please add a valid email address.');
      if (f.get('sms_consent') && !phone) return say('You checked the call/text box, so please add a phone number (or uncheck it).');
      if (!ENDPOINT) return say('This form is not connected yet. Please check back shortly.');

      var body = new URLSearchParams();
      f.forEach(function (v, k) { body.append(k, v); });
      if (!f.get('sms_consent')) body.append('sms_consent', 'no');
      body.append('form', form.getAttribute('data-form') || '');
      body.append('page', location.pathname);
      body.append('referrer', document.referrer || '');
      body.append('elapsed_ms', String(Date.now() - loadedAt));
      Object.keys(track).forEach(function (k) { body.append(k, track[k]); });

      btn.disabled = true; var label = btn.textContent; btn.textContent = 'Sending…';
      fetch(ENDPOINT, { method: 'POST', body: body })
        .then(function (res) { return res.json().catch(function () { return { ok: res.ok }; }); })
        .then(function (out) {
          if (out && out.ok) {
            form.querySelectorAll('.fld, .seg, .consent, .go').forEach(function (el) { el.style.display = 'none'; });
            say('Got it. Thank you, ' + name.split(' ')[0] + '. I\'ll reach out soon.');
          } else { throw new Error('not ok'); }
        })
        .catch(function () {
          btn.disabled = false; btn.textContent = label;
          say('Something went wrong sending that. Please try again in a minute.');
        });
    });
  });
})();
