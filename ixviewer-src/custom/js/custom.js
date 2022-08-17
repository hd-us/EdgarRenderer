const searchInput = document.getElementById('global-search');
const searchIcon = document.getElementById('search-btn-clear');

function showHideSearchCancelIcon(e) {
  console.log(e.target.value);
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