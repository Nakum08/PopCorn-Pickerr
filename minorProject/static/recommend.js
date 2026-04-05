// Simple helpers to show/hide loaders without repeating code
function showLoader()     { var l = document.getElementById('loader');     if (l) l.classList.add('active'); }
function hideLoader()     { var l = document.getElementById('loader');     if (l) l.classList.remove('active'); }
function showDualLoader() { var l = document.getElementById('dualLoader'); if (l) l.classList.add('active'); }
function hideDualLoader() { var l = document.getElementById('dualLoader'); if (l) l.classList.remove('active'); }


// Disable search button when input is empty, enable when user types something
$(function() {
  var src = document.getElementById('autoComplete');
  if (!src) return; // not on this page

  src.addEventListener('input', function(e) {
    $('.movie-button').prop('disabled', e.target.value.trim() === '');
  });

  // On search click, grab input and send it
  $('.movie-button').on('click', function() {
    var title = $('.movie').val().trim();
    if (!title) {
      $('.results').hide();
      $('.fail').show();
      return;
    }
    load_details(title);
  });
});


// Clicking a recommended card just runs search again with that title
function recommendcard(el) {
  load_details(el.getAttribute('title'));
}


// Sends movie title to backend and renders returned HTML
function load_details(title) {
  showLoader();
  $('.fail').hide();

  $.ajax({
    type: 'POST',
    url:  '/search',
    data: { title: title },

    success: function(html) {
      hideLoader();

      // Backend sends NOT_FOUND if nothing matched
      if (html === 'NOT_FOUND') {
        $('.fail').show();
        $('.results').hide();
        return;
      }

      // Drop returned HTML into results section
      $('.results').html(html).show();

      // Move modals to body so Bootstrap behaves properly
      $('.results .modal').each(function() {
        $(this).appendTo('body');
      });

      // Re-init modals so close/backdrop works
      $('body > .modal').modal({ backdrop: true, keyboard: true, show: false });

      // Clear input + scroll up to see results
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


// Handles "watch together" feature with two movies
function dual_start() {
  var movie1 = (document.getElementById('autoComplete')  || {}).value || '';
  var movie2 = (document.getElementById('autoComplete2') || {}).value || '';
  movie1 = movie1.trim();
  movie2 = movie2.trim();

  if (!movie1 || !movie2) {
    alert('Please enter both movies');
    return;
  }

  showDualLoader();

  $.ajax({
    type: 'POST',
    url:  '/dual_recommend',
    data: { movie1: movie1, movie2: movie2 },

    success: function(response) {
      hideDualLoader();

      // If backend couldn’t find results
      if (!response || response === 'NOT_FOUND') {
        alert('No recommendations found. Please check the movie names.');
        return;
      }

      var recs = response.split('---').filter(Boolean);
      if (!recs.length) {
        alert('No recommendations found');
        return;
      }

      // Build cards with placeholder images first
      var html = '<h4>Suggested Movies</h4><div id="movieGrid">';
      recs.forEach(function(movie) {
        html += '<div class="movie-card" data-movie="' + movie + '">' +
                '<img src="https://via.placeholder.com/200x280?text=Loading..." />' +
                '<p>' + movie + '</p></div>';
      });
      html += '</div>';

      // Replace old results
      var box = document.querySelector('.box');
      var old = document.getElementById('dualResults');
      if (old) old.remove();

      var container = document.createElement('div');
      container.id  = 'dualResults';
      container.innerHTML = html;
      box.appendChild(container);

      // Load posters in background and swap them in
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


// Runs after page loads: hooks up button and checks URL for auto search
document.addEventListener('DOMContentLoaded', function() {

  var btn = document.getElementById('dualBtn');
  if (btn) btn.addEventListener('click', dual_start);

  // If URL has ?movie=..., auto-run search
  var movie = new URLSearchParams(window.location.search).get('movie');
  if (movie) load_details(movie);

});
