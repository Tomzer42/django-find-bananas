document.addEventListener("DOMContentLoaded", function () {
    const modalContainer = document.getElementById("tutorialModal");
    const modalSteps = document.querySelectorAll(".modal-step");
    const dots = document.querySelectorAll(".dot");
    const prevButton = document.querySelector(".modal-prev-button");
    const nextButton = document.querySelector(".modal-next-button");
    const closeModalButton = document.querySelector(".close-button");
    const closeButton = document.createElement("span");
    const whiteButton = document.querySelector(".white-button");
    const whiteContainer = document.querySelector(".white-container");
    const mainTitle = document.querySelector(".main-title");
    const buttonText = document.querySelector(".button-text");
    const playIcon = document.querySelector(".play-icon");

    setTimeout(function() {
        var modal = document.getElementById("tutorialModal");
        modal.classList.add("active"); // Add the "active" class to apply styles
        
        var tutorialLink = document.getElementById("tutorialLink"); // Change "tutorialLink" to your actual link ID
        tutorialLink.addEventListener("click", function (event) {
            currentStep = 0;
            event.preventDefault(); // Prevent the default link behavior
            modal.style.display = "flex"; // Open the modal
        });
    }, 1000); // 2000 milliseconds = 2 seconds

    let currentStep = 0;

    function showStep(step) {
        modalSteps.forEach((stepElement) => {
            stepElement.classList.remove("active");
        });

        dots.forEach((dot, index) => {
            if (index === step) {
                dot.classList.add("active");
            } else {
                dot.classList.remove("active");
            }
        });

        modalSteps[step].classList.add("active");
    }

    function nextStep() {
        currentStep = (currentStep + 1) % modalSteps.length;
        showStep(currentStep);
    }

    function prevStep() {
        currentStep = (currentStep - 1 + modalSteps.length) % modalSteps.length;
        showStep(currentStep);
    }

    dots.forEach((dot, index) => {
        dot.addEventListener("click", function () {
            showStep(index);
            currentStep = index;
        });
    });

    prevButton.addEventListener("click", prevStep);
    nextButton.addEventListener("click", nextStep);

    document.addEventListener("keydown", function (event) {
        if (event.key === "ArrowRight") {
            nextStep();
        } else if (event.key === "ArrowLeft") {
            prevStep();
        } else if (event.key === "Escape") {
            closeModal();
        }
    });

    function closeModal() {
        modalContainer.style.display = "closing";
        setTimeout(() => {
            modalContainer.style.display = "none";
            modalContainer.classList.remove("closing"); // Remove closing class after the transition
            currentStep = 0;
            showStep(currentStep);
        }, 300); // Match the transition duration (0.3s)
    }

    closeButton.innerHTML = '<i class="fas fa-times"></i>';
    closeButton.classList.add("close-button");
    modalContainer.appendChild(closeButton);

    closeButton.addEventListener("click", closeModal);
    closeModalButton.addEventListener("click", closeModal);

    modalContainer.addEventListener("click", function (event) {
        if (event.target === modalContainer) {
            closeModal();
        }
    });

    // Show the initial step when the modal is opened
    showStep(currentStep);


    whiteButton.addEventListener("click", function() {
        // Save the original button text and description
        const originalButtonText = buttonText.textContent;

        mainTitle.textContent = "Round 1"; // Hide the main title after button click
        // mainTitle.style.display = "none";
        buttonText.textContent = "Get ready..."; // Change button text and disable button temporarily
        playIcon.style.display = "none"; // Hide the play icon
        whiteButton.disabled = true;

        // Simulate content change delay (2 seconds)
        setTimeout(function() {
            mainTitle.textContent = "How many bananas can you see?";
            buttonText.textContent = originalButtonText; // Restore original button text
            playIcon.style.display = "inline"; // Show the play icon
            whiteButton.style.display = "none"; // Hide the button
            whiteContainer.style.display = "flex"; // Open the white-container
            // whiteContainer.scrollIntoView({ behavior: "smooth" }); // Optional: Scroll to the white-container
        }, 2000); // 2000 milliseconds (2 seconds) delay
    });

});
