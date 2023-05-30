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


window.addEventListener('message', 
(event) => {
  console.log('i got some data!', data);
  console.log(event);
  if (
    event.origin === "http://localhost:3000" ||
    event.origin === "https://dev-app.hdata.us" ||
    event.origin === "https://staging-app.hdata.us" ||
    event.origin === "https://app.hdata.us"
  ) {
    console.log('i got some data!', data);
  };
});