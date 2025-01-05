document.addEventListener('DOMContentLoaded', function() {
    // Get all range and number inputs within the form
    var rangeInputs = document.querySelectorAll('input[type="range"]');
    var numberInputs = document.querySelectorAll('input[type="number"]');

    // Loop through each set of inputs
    rangeInputs.forEach(function(rangeInput, index) {
        var numberInput = numberInputs[index];

        // Set initial value of number input
        numberInput.value = rangeInput.value;

        // Update number input value when range input changes
        rangeInput.addEventListener('input', function() {
            numberInput.value = rangeInput.value;
        });

        // Update range input value when number input changes
        numberInput.addEventListener('input', function() {
            // Ensure the entered value is within the min-max range
            if (parseInt(numberInput.value) < parseInt(rangeInput.min)) {
                numberInput.value = rangeInput.min;
            } else if (parseInt(numberInput.value) > parseInt(rangeInput.max)) {
                numberInput.value = rangeInput.max;
            }
            rangeInput.value = numberInput.value;
        });
    });
});


// this is for content dropdown
function toggleDropdown() {
    var dropdownContent = document.getElementById("dropdownContent");
    if (dropdownContent.style.display === "none") {
        dropdownContent.style.display = "block";
    } else {
        dropdownContent.style.display = "none";
    }
}

function toggleDropdown1() {
    var dropdownContent = document.getElementById("dropdownContent1");
    if (dropdownContent.style.display === "none") {
        dropdownContent.style.display = "block";
    } else {
        dropdownContent.style.display = "none";
    }
}


// Prevent form submission when Enter key is pressed
document.addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        event.preventDefault(); // Prevent default behavior (form submission)
    }
});

// Prevent refresh when Enter key is pressed
document.addEventListener("keydown", function(event) {
    if (event.key === "F5") {
        event.preventDefault(); // Prevent default behavior (refresh)
    }
});

// Prevent refresh when Ctrl + r is pressed
document.addEventListener("keydown", function(event) {
    if (event.key === "r" && event.ctrlKey) {
        event.preventDefault(); // Prevent default behavior (refresh)
    }
});

// Get the modal element
var modal = document.getElementById("confirmationModal");

// Get the <span> element that closes the modal
var span = document.getElementsByClassName("close")[0];

// When the user clicks on <span> (x), close the modal
span.onclick = function() {
  modal.style.display = "none";
}

// When the user clicks anywhere outside of the modal, close it
window.onclick = function(event) {
  if (event.target == modal) {
    modal.style.display = "none";
  }
}

// Function to handle form submission
function submitForm(formId) {
  // Show the confirmation modal
  modal.style.display = "block";
  
  // Store the form ID to use it later
  modal.dataset.formId = formId;

  // Prevent default form submission
  return false;
}

// Function to handle confirmation
document.getElementById("confirmBtn").onclick = function() {
  // Hide the modal
  modal.style.display = "none";

  // Get the form ID from the dataset
  var formId = modal.dataset.formId;

  // Submit the form
  document.getElementById(formId).submit();
}

// Function to handle cancellation
document.getElementById("cancelBtn").onclick = function() {
  // Hide the modal
  modal.style.display = "none";
}
