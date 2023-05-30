const searchInput = document.getElementById('global-search');
const searchIcon = document.getElementById('search-btn-clear');

function showHideSearchCancelIcon(e) {
  if (e.target.value && e.target.value.length) {
    searchIcon.classList.add("show-icon");
  } else{
    searchIcon.classList.remove("show-icon");
  }
}

function hideSearchCancelIcon() {
  searchIcon.classList.remove("show-icon");
}

searchInput.addEventListener('keyup', showHideSearchCancelIcon);
searchIcon.addEventListener('click', hideSearchCancelIcon);

window.addEventListener('message', function(event) {
  if (
    event.origin === "http://localhost:3000" ||
    event.origin === "https://dev-app.hdata.us" ||
    event.origin === "https://staging-app.hdata.us" ||
    event.origin === "https://app.hdata.us"
  ) {
    if (event.data) {
      window.libraryId = vent.data.libraryId;
      console.log(event.data.libraryId);
    }
  };
});