// =============================================================
//  recommend.js
//  Handles all user interactions on the home page:
//    - Enabling/disabling the Search button
//    - Sending the search request to Flask (/search)
//    - Injecting the returned HTML into the results div
//    - The Watch Together dual-recommend flow
//    - Loading indicator show/hide helpers
// =============================================================


// -------------------------------------------------------------
//  LOADER HELPERS
//  Simple wrappers so we're not repeating classList calls
//  all over the place. "active" class is what shows the loader.
// -------------------------------------------------------------
function showLoader()     { var l = document.getElementById('loader');     if (l) l.classList.add('active'); }
function hideLoader()     { var l = document.getElementById('loader');     if (l) l.classList.remove('active'); }
function showDualLoader() { var l = document.getElementById('dualLoader'); if (l) l.classList.add('active'); }
function hideDualLoader() { var l = document.getElementById('dualLoader'); if (l) l.classList.remove('active'); }


// -------------------------------------------------------------
//  SEARCH BUTTON ENABLE/DISABLE
//  The Search button is disabled by default so you can't click
//  it on an empty input. We watch the input and flip it as soon
//  as there's any text.
// -------------------------------------------------------------
$(function() {
  var src = document.getElementById('autoComplete');
  if (!src) return; // not on home page, bail out

  src.addEventListener('input', function(e) {
    $('.movie-button').prop('disabled', e.target.value.trim() === '');
  });

  // When Search is clicked, grab the input value and kick off the search
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


// -------------------------------------------------------------
//  RECOMMENDED CARD CLICK
//  Called by onclick="recommendcard(this)" on each movie card
//  in recommend.html. Reads the title from the element's
//  "title" attribute and runs a new search for it.
// -------------------------------------------------------------
function recommendcard(el) {
  load_details(el.getAttribute('title'));
}


// -------------------------------------------------------------
//  MAIN SEARCH — POST to Flask /search
//  This is the heart of the whole thing. We send the movie
//  title to Flask, which does ALL the heavy work (OMDb fetch,
//  ML recommendations, cast, reviews) and returns rendered HTML.
//  We just inject that HTML into the results div. That's it.
//  Two network calls total instead of the 20+ the old code made.
// -------------------------------------------------------------
function load_details(title) {
  showLoader();
  $('.fail').hide();

  $.ajax({
    type: 'POST',
    url:  '/search',
    data: { title: title },

    success: function(html) {
      hideLoader();

      // Flask returns the string "NOT_FOUND" if nothing matched
      if (html === 'NOT_FOUND') {
        $('.fail').show();
        $('.results').hide();
        return;
      }

      // Inject the rendered recommend.html into the results container
      $('.results').html(html).show();

      // Bootstrap modals in the injected HTML need to live directly
      // on <body> — if they're nested inside .results, the backdrop
      // gets trapped in the stacking context and won't close properly
      $('.results .modal').each(function() {
        $(this).appendTo('body');
      });

      // Re-initialise the moved modals so backdrop click and Escape work
      $('body > .modal').modal({ backdrop: true, keyboard: true, show: false });

      // Clear the search box and scroll back to the top so the user
      // can see the results from the beginning
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


// -------------------------------------------------------------
//  DUAL RECOMMEND — Watch Together page
//  Takes two movie titles, sends them to Flask /dual_recommend,
//  and builds a grid of movie cards with placeholder posters.
//  Each poster is then fetched asynchronously via /poster so
//  the cards appear instantly and images pop in as they load.
// -------------------------------------------------------------
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

      // Flask returns "NOT_FOUND" if either movie isn't in our dataset
      if (!response || response === 'NOT_FOUND') {
        alert('No recommendations found. Please check the movie names.');
        return;
      }

      var recs = response.split('---').filter(Boolean);
      if (!recs.length) {
        alert('No recommendations found');
        return;
      }

      // Build the card grid — placeholders show immediately while
      // the real posters load in the background
      var html = '<h4>Suggested Movies</h4><div id="movieGrid">';
      recs.forEach(function(movie) {
        html += '<div class="movie-card" data-movie="' + movie + '">' +
                '<img src="https://via.placeholder.com/200x280?text=Loading..." />' +
                '<p>' + movie + '</p></div>';
      });
      html += '</div>';

      // Replace any previous results, don't just append
      var box = document.querySelector('.box');
      var old = document.getElementById('dualResults');
      if (old) old.remove();

      var container = document.createElement('div');
      container.id  = 'dualResults';
      container.innerHTML = html;
      box.appendChild(container);

      // Fetch each poster from Flask /poster (which hits OMDb) asynchronously.
      // These run in parallel and swap the placeholder image when each arrives.
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


// -------------------------------------------------------------
//  DOM READY — wire up buttons and handle URL params
// -------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function() {

  // Wire the "Find Movie" button on the dual page
  var btn = document.getElementById('dualBtn');
  if (btn) btn.addEventListener('click', dual_start);

  // If the URL has ?movie=... (set when clicking a dual result card),
  // auto-trigger a search for that movie on page load
  var movie = new URLSearchParams(window.location.search).get('movie');
  if (movie) load_details(movie);

});