/* «Ода KitAi» — движок визуальной новеллы (ванильный JS) */
(function () {
  'use strict';

  var $ = function (s) { return document.querySelector(s); };
  var SAVE = 'kitai.save.v1';
  var GAL  = 'kitai.endings.v1';

  var el = {
    title: $('#title'), game: $('#game'), bg: $('#bg'),
    sl: $('#sprite-left'), sr: $('#sprite-right'),
    speaker: $('#speaker'), text: $('#text'), next: $('#next'),
    choices: $('#choices'), flash: $('#flash'),
    overlay: $('#overlay'), ovTitle: $('#ov-title'), ovBody: $('#ov-body')
  };

  var state = { node: 'start', aff: { kit: 0, yuki: 0 }, log: [] };
  var typing = null, fullText = '', auto = false, skip = false, autoTimer = null;

  /* ---------- Хранилище ---------- */
  function save() { try { localStorage.setItem(SAVE, JSON.stringify(state)); } catch (e) {} }
  function load() { try { return JSON.parse(localStorage.getItem(SAVE)); } catch (e) { return null; } }
  function getEndings() { try { return JSON.parse(localStorage.getItem(GAL)) || {}; } catch (e) { return {}; } }
  function unlockEnding(k) { var g = getEndings(); g[k] = true; try { localStorage.setItem(GAL, JSON.stringify(g)); } catch (e) {} }

  /* ---------- Экраны ---------- */
  function show(screen) {
    el.title.classList.toggle('active', screen === 'title');
    el.game.classList.toggle('active', screen === 'game');
  }

  /* ---------- Отрисовка узла ---------- */
  var curBg = '';
  function setBg(name) {
    if (!name || name === curBg) return;
    curBg = name;
    el.bg.classList.add('fading');
    setTimeout(function () {
      el.bg.style.backgroundImage = 'url(img/' + name + '.jpg)';
      el.bg.classList.remove('fading');
    }, 180);
  }

  function setSprites(sprites, active, faces) {
    sprites = sprites || {};
    faces = faces || {};
    [['left', el.sl], ['right', el.sr]].forEach(function (p) {
      var side = p[0], img = p[1], who = sprites[side];
      if (who && CHARS[who] && CHARS[who].img) {
        var face = faces[side];
        var src = (face && CHARS[who].faces && CHARS[who].faces[face]) || CHARS[who].img;
        var key = who + ':' + (face || '');
        if (img.getAttribute('data-who') !== key) {
          img.src = src;
          img.setAttribute('data-who', key);
        }
        img.classList.add('show');
        img.classList.toggle('dim', !!active && active !== side);
      } else {
        img.classList.remove('show');
        img.removeAttribute('data-who');
      }
    });
  }

  var cgEl = null;
  function showCg(name) {
    if (!cgEl) {
      cgEl = document.createElement('div');
      cgEl.id = 'cg';
      el.game.insertBefore(cgEl, document.getElementById('stage'));
    }
    cgEl.style.backgroundImage = 'url(img/' + name + '.jpg)';
    cgEl.classList.add('show');
    curBg = '';
  }
  function hideCg() { if (cgEl) cgEl.classList.remove('show'); }

  var audio = null, voiceOn = true;
  function playVoice(name) {
    if (audio) { audio.pause(); audio = null; }
    if (!name || !voiceOn) return;
    try {
      audio = new Audio('audio/' + name + '.mp3');
      audio.volume = 0.9;
      var pr = audio.play();
      if (pr && pr.catch) pr.catch(function () {});
    } catch (e) {}
  }
  function stopVoice() { if (audio) { audio.pause(); audio = null; } }

  function typewrite(txt) {
    clearInterval(typing);
    fullText = txt;
    el.text.textContent = '';
    el.next.classList.remove('on');
    if (skip) { el.text.textContent = txt; el.next.classList.add('on'); scheduleAuto(); return; }
    var i = 0;
    typing = setInterval(function () {
      i += 1;
      el.text.textContent = txt.slice(0, i);
      if (i >= txt.length) { clearInterval(typing); typing = null; el.next.classList.add('on'); scheduleAuto(); }
    }, 18);
  }

  function finishTyping() {
    if (typing) { clearInterval(typing); typing = null; el.text.textContent = fullText; el.next.classList.add('on'); scheduleAuto(); return true; }
    return false;
  }

  function scheduleAuto() {
    clearTimeout(autoTimer);
    if (auto || skip) {
      autoTimer = setTimeout(function () { advance(); }, skip ? 260 : 1500 + fullText.length * 22);
    }
  }

  function render(id) {
    var n = STORY[id];
    if (!n) { return; }
    state.node = id;
    save();

    if (n.ending) { return showEnding(n.ending); }

    if (n.cg) {
      showCg(n.cg);
    } else {
      hideCg();
      setBg(n.bg);
    }
    setSprites(n.cg ? null : n.sprites, n.active, n.faces);
    playVoice(n.voice);

    if (n.flash) {
      el.flash.classList.add('on');
      setTimeout(function () { el.flash.classList.remove('on'); }, 260);
    }

    var c = CHARS[n.who] || CHARS.sys;
    el.speaker.textContent = (n.who === 'sys' || !n.who) ? '' : c.name;
    el.speaker.className = c.cls || '';
    el.text.className = (n.who === 'sys' || n.who === 'me') ? 'narr' : '';

    if (n.text) {
      state.log.push({ who: el.speaker.textContent || '—', text: n.text });
      if (state.log.length > 120) state.log.shift();
    }

    typewrite(n.text || '');

    el.choices.classList.remove('show');
    el.choices.innerHTML = '';
    if (n.choices) {
      // Показать выборы после того, как текст допечатан
      var delay = skip ? 100 : Math.min(900, (n.text || '').length * 18 + 120);
      setTimeout(function () {
        if (state.node !== id) return;
        n.choices.forEach(function (ch) {
          var b = document.createElement('button');
          b.className = 'btn';
          b.textContent = ch.t;
          b.onclick = function (e) {
            e.stopPropagation();
            if (ch.aff) { for (var k in ch.aff) { state.aff[k] = (state.aff[k] || 0) + ch.aff[k]; } }
            auto = false; skip = false; syncHud();
            el.choices.classList.remove('show');
            render(ch.to);
          };
          el.choices.appendChild(b);
        });
        el.choices.classList.add('show');
      }, delay);
    }
  }

  function advance() {
    var n = STORY[state.node];
    if (!n) return;
    if (finishTyping()) return;
    if (n.choices) return;         // ждём выбор
    if (n.next) render(n.next);
  }

  /* ---------- Концовки ---------- */
  function showEnding(key) {
    unlockEnding(key);
    var e = ENDINGS[key];
    var aff = 'Кит: ' + state.aff.kit + ' · Юки: ' + state.aff.yuki;
    openOverlay(e.title,
      (e.cg ? '<img class="ending-cg" src="img/' + e.cg + '.jpg" alt="">' : '') +
      '<p class="about">' + e.desc + '</p>' +
      '<p class="about" style="opacity:.6">Связь — ' + aff + '</p>' +
      '<p class="about" style="opacity:.6">Всего концовок: 4. Открой все, чтобы собрать полную «Оду».</p>',
      [{ t: 'В главное меню', fn: function () { closeOverlay(); toTitle(); } },
       { t: 'Начать заново', fn: function () { closeOverlay(); newGame(); } }]);
    try { localStorage.removeItem(SAVE); } catch (err) {}
  }

  /* ---------- Оверлей ---------- */
  function openOverlay(title, html, buttons) {
    el.ovTitle.textContent = title;
    el.ovBody.innerHTML = html;
    var old = el.overlay.querySelectorAll('.panel .btn.dyn');
    Array.prototype.forEach.call(old, function (b) { b.remove(); });
    (buttons || []).forEach(function (b) {
      var btn = document.createElement('button');
      btn.className = 'btn dyn';
      btn.textContent = b.t;
      btn.onclick = b.fn;
      el.overlay.querySelector('.panel').insertBefore(btn, $('#ov-close'));
    });
    $('#ov-close').style.display = (buttons && buttons.length) ? 'none' : '';
    el.overlay.classList.add('show');
  }
  function closeOverlay() { el.overlay.classList.remove('show'); }
  $('#ov-close').onclick = closeOverlay;

  /* ---------- Меню/HUD ---------- */
  function syncHud() {
    $('#btn-auto').classList.toggle('on', auto);
    $('#btn-skip').classList.toggle('on', skip);
  }

  function newGame() {
    stopVoice();
    state = { node: 'start', aff: { kit: 0, yuki: 0 }, log: [] };
    auto = false; skip = false; syncHud();
    curBg = '';
    show('game');
    render('start');
  }

  function toTitle() {
    stopVoice(); hideCg();
    auto = false; skip = false; clearTimeout(autoTimer); syncHud();
    show('title');
    $('#btn-continue').disabled = !load();
  }

  $('#btn-new').onclick = newGame;
  $('#btn-continue').onclick = function () {
    var s = load();
    if (!s) return;
    state = s;
    if (!state.aff) state.aff = { kit: 0, yuki: 0 };
    if (!state.log) state.log = [];
    curBg = '';
    show('game');
    render(state.node);
  };
  $('#btn-gallery').onclick = function () {
    var g = getEndings(), html = '';
    for (var k in ENDINGS) {
      var open = !!g[k];
      html += '<div class="ending-card' + (open ? '' : ' locked') + '">' +
        (open && ENDINGS[k].cg ? '<img class="ending-cg" src="img/' + ENDINGS[k].cg + '.jpg" alt="">' : '') +
        '<b>' + (open ? ENDINGS[k].title : '??? — не открыта') + '</b>' +
        (open ? ENDINGS[k].desc : 'Пройди историю иначе, чтобы открыть.') + '</div>';
    }
    openOverlay('Галерея концовок', html);
  };
  $('#btn-about').onclick = function () {
    openOverlay('Об игре',
      '<p class="about"><b>Ода KitAi</b> — короткая аниме-визуальная новелла о школьнике, ' +
      'которому поручили выключить нейросеть, умеющую писать стихи.</p>' +
      '<p class="about">4 концовки · 3 персонажа · автосохранение.<br>' +
      'Оффлайн, без рекламы и интернета.</p>' +
      '<p class="about" style="opacity:.6">Сборка: WebView + HTML/CSS/JS. Арт сгенерирован ИИ.</p>');
  };

  $('#btn-menu').onclick = function (e) {
    e.stopPropagation();
    openOverlay('Пауза', '<p class="about">Прогресс сохраняется автоматически.</p>',
      [{ t: 'Продолжить', fn: closeOverlay },
       { t: 'В главное меню', fn: function () { closeOverlay(); toTitle(); } }]);
  };
  $('#btn-auto').onclick = function (e) { e.stopPropagation(); auto = !auto; skip = false; syncHud(); scheduleAuto(); };
  $('#btn-skip').onclick = function (e) { e.stopPropagation(); skip = !skip; auto = false; syncHud(); scheduleAuto(); };
  var btnVoice = document.getElementById('btn-voice');
  if (btnVoice) {
    btnVoice.classList.add('on');
    btnVoice.onclick = function (e) {
      e.stopPropagation();
      voiceOn = !voiceOn;
      btnVoice.classList.toggle('on', voiceOn);
      btnVoice.textContent = voiceOn ? '🔊' : '🔇';
      if (!voiceOn) stopVoice();
    };
  }

  $('#btn-log').onclick = function (e) {
    e.stopPropagation();
    var html = state.log.slice(-40).map(function (l) {
      return '<div class="log-line"><b>' + l.who + '</b><br>' + l.text.replace(/\n/g, '<br>') + '</div>';
    }).join('') || '<p class="about">Пока пусто.</p>';
    openOverlay('История диалогов', html);
  };

  el.game.addEventListener('click', function (e) {
    if (el.overlay.classList.contains('show')) return;
    if (el.choices.classList.contains('show')) return;
    if (e.target.closest('#hud')) return;
    advance();
  });

  document.addEventListener('backbutton', function () {
    if (el.overlay.classList.contains('show')) { closeOverlay(); return; }
    if (el.game.classList.contains('active')) { toTitle(); return; }
  });

  // Стартовое состояние
  toTitle();
  // Прелоад фонов
  ['bg_classroom', 'bg_rooftop', 'bg_server', 'bg_clubroom', 'bg_corridor', 'bg_street', 'bg_rain', 'cg_meeting']
    .forEach(function (b) { var i = new Image(); i.src = 'img/' + b + '.jpg'; });
})();
