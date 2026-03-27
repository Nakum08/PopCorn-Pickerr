if (document.querySelector("#autoComplete")) {
  new autoComplete({
    data: { src: films },
    selector: "#autoComplete",
    threshold: 2,
    debounce: 100,
    searchEngine: "strict",
    resultsList: {
        render: true,
        container: source => {
            source.setAttribute("id", "food_list");
        },
        destination: document.querySelector("#autoComplete"),
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
    onSelection: feedback => {
        document.getElementById('autoComplete').value = feedback.selection.value;
    }
  });
}
if (document.querySelector("#autoComplete2")) {
  new autoComplete({
    data: { src: films },
    selector: "#autoComplete2",
    threshold: 2,
    debounce: 100,
    searchEngine: "strict",
   resultsList: {
    render: true,
    container: source => {
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
    onSelection: feedback => {
        document.getElementById('autoComplete2').value = feedback.selection.value;
    }
  });
}

const searchButton = document.querySelector('.btn.btn-primary.btn-block.movie-button');
const animationContainer = document.querySelector('.slider');
const imageContainer = document.querySelectorAll('.bg-image');

if (searchButton && animationContainer && imageContainer.length) {
  searchButton.addEventListener('click', () => {
    animationContainer.style.display = 'none';
    imageContainer.forEach(el => {
      el.style.display = 'block';
    });
  });
}
    

const searchButton2 = document.querySelector('.btn.btn-primary.btn-block.movie-button');
const element = document.querySelector('.ml-container');

if (searchButton2 && element) {
  searchButton2.addEventListener('click', () => {
    element.style.top = '6%';
  });
}


