// ─────────────────────────────────────────────────────────────
//  recommend.js — lean client, all heavy work done by Flask
//  Browser makes 2 calls total: POST /search  +  POST /dual_recommend
// ─────────────────────────────────────────────────────────────

function showLoader()  { var l = document.getElementById('loader'); if(l) l.classList.add('active'); }
function hideLoader()  { var l = document.getElementById('loader'); if(l) l.classList.remove('active'); }
function showDualLoader() { var l = document.getElementById('dualLoader'); if(l) l.classList.add('active'); }
function hideDualLoader() { var l = document.getElementById('dualLoader'); if(l) l.classList.remove('active'); }

// ── Enable/disable search button ─────────────────────────────
$(function() {
  var src = document.getElementById('autoComplete');
  if (!src) return;
  src.addEventListener('input', function(e) {
    $('.movie-button').prop('disabled', e.target.value.trim() === '');
  });

  $('.movie-button').on('click', function() {
    var title = $('.movie').val().trim();
    if (!title) { $('.results').hide(); $('.fail').show(); return; }
    load_details(title);
  });
});

// ── Recommended card click ────────────────────────────────────
function recommendcard(el) {
  load_details(el.getAttribute('title'));
}



// ── Main search — single call to Flask /search ────────────────
function load_details(title) {
  showLoader();
  $('.fail').hide();

  $.ajax({
    type: 'POST',
    url:  '/search',
    data: { title: title },
    success: function(html) {
      hideLoader();
      if (html === 'NOT_FOUND') {
        $('.fail').show();
        $('.results').hide();
        return;
      }
      // Inject HTML first
      $('.results').html(html).show();

      // Immediately move ALL modals to <body> so Bootstrap backdrop
      // never gets trapped — do this synchronously before user can click
      $('.results .modal').each(function() {
        $(this).appendTo('body');
      });

      // Re-init modals so backdrop click / Escape key works
      $('body > .modal').modal({ backdrop: true, keyboard: true, show: false });

      $('#autoComplete').val('');
      $(window).scrollTop(0);
    },
    error: function() {
      hideLoader();
      $('.fail').show();
      $('.results').hide();
    }
  });
}

// ── Dual recommend ────────────────────────────────────────────
function dual_start() {
  var movie1 = (document.getElementById('autoComplete')  || {}).value || '';
  var movie2 = (document.getElementById('autoComplete2') || {}).value || '';
  movie1 = movie1.trim(); movie2 = movie2.trim();

  if (!movie1 || !movie2) { alert('Please enter both movies'); return; }

  showDualLoader();

  $.ajax({
    type: 'POST',
    url:  '/dual_recommend',
    data: { movie1: movie1, movie2: movie2 },
    success: function(response) {
      hideDualLoader();

      if (!response || response === 'NOT_FOUND') {
        alert('No recommendations found. Please check the movie names.');
        return;
      }

      var recs = response.split('---').filter(Boolean);
      if (!recs.length) { alert('No recommendations found'); return; }

      // Build card grid with placeholders
      var html = '<h4>Suggested Movies</h4><div id="movieGrid">';
      recs.forEach(function(movie) {
        html += '<div class="movie-card" data-movie="' + movie + '">' +
                '<img src="https://via.placeholder.com/200x280?text=Loading..." />' +
                '<p>' + movie + '</p></div>';
      });
      html += '</div>';

      var box = document.querySelector('.box');
      var old = document.getElementById('dualResults');
      if (old) old.remove();
      var container = document.createElement('div');
      container.id  = 'dualResults';
      container.innerHTML = html;
      box.appendChild(container);

      // Fetch each poster via Flask /poster route — non-blocking, async
      document.querySelectorAll('#dualResults .movie-card').forEach(function(card) {
        var movie = card.getAttribute('data-movie');
        $.get('/poster', { title: movie }, function(data) {
          var img = card.querySelector('img');
          if (img && data.poster) img.src = data.poster;
        });
      });
    },
    error: function() {
      hideDualLoader();
      alert('Error getting recommendations. Please try again.');
    }
  });
}

// ── DOMContentLoaded ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  // Wire dual Find Movie button
  var btn = document.getElementById('dualBtn');
  if (btn) btn.addEventListener('click', dual_start);

  // Auto-trigger from ?movie= URL param (after dual card click)
  var movie = new URLSearchParams(window.location.search).get('movie');
  if (movie) load_details(movie);
});


