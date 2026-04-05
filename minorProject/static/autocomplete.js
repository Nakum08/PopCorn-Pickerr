// Initialize autocomplete for the first input field if it exists
if (document.querySelector("#autoComplete")) {
  new autoComplete({
    data: { src: films }, // Source data for suggestions (movie list)
    selector: "#autoComplete", // Target input field
    threshold: 2, // Start showing suggestions after typing 2 characters
    debounce: 100, // Small delay to avoid firing too many searches
    searchEngine: "strict", // Exact match style searching

    // Configuration for how the results dropdown behaves
    resultsList: {
        render: true,
        container: source => {
            // Assign a custom ID to the dropdown list
            source.setAttribute("id", "food_list");
        },
        destination: document.querySelector("#autoComplete"), // Attach results near input
        position: "afterend", // Place dropdown right after input field
        element: "ul" // Use unordered list for results
    },

    maxResults: 5, // Limit number of suggestions shown
    highlight: true, // Highlight matched text in suggestions

    // Define how each suggestion item looks
    resultItem: {
        content: (data, source) => {
            source.innerHTML = data.match; // Display matched result
        },
        element: "li"
    },

    // When user selects a suggestion, fill input field with selected value
    onSelection: feedback => {
        document.getElementById('autoComplete').value = feedback.selection.value;
    }
  });
}

// Initialize autocomplete for the second input field (same logic, different element)
if (document.querySelector("#autoComplete2")) {
  new autoComplete({
    data: { src: films }, // Same movie list used here
    selector: "#autoComplete2", // Second input field
    threshold: 2,
    debounce: 100,
    searchEngine: "strict",

    resultsList: {
        render: true,
        container: source => {
            // Separate ID so both dropdowns don’t clash
            source.setAttribute("id", "food_list2");
        },
        destination: document.querySelector("#autoComplete2"),
        position: "afterend",
        element: "ul"
    },

    maxResults: 5,
    highlight: true,

    resultItem: {
        content: (data, source) => {
            source.innerHTML = data.match;
        },
        element: "li"
    },

    // Update second input when a suggestion is selected
    onSelection: feedback => {
        document.getElementById('autoComplete2').value = feedback.selection.value;
    }
  });
}

// Grab main search button and UI elements for animation control
const searchButton = document.querySelector('.btn.btn-primary.btn-block.movie-button');
const animationContainer = document.querySelector('.slider');
const imageContainer = document.querySelectorAll('.bg-image');

// When search is clicked, hide animation and show background images
if (searchButton && animationContainer && imageContainer.length) {
  searchButton.addEventListener('click', () => {
    animationContainer.style.display = 'none'; // Hide slider animation
    imageContainer.forEach(el => {
      el.style.display = 'block'; // Reveal images
    });
  });
}


// Same button reused for layout adjustment after search
const searchButton2 = document.querySelector('.btn.btn-primary.btn-block.movie-button');
const element = document.querySelector('.ml-container');

// Move main container slightly down when search is triggered
if (searchButton2 && element) {
  searchButton2.addEventListener('click', () => {
    element.style.top = '6%'; // Adjust positioning for better layout
  });
}