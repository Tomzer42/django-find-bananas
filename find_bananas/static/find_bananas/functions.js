const showImage1 = () => {
    console.log('Début du showImage1')
    document.getElementById("image1").style.display ='block';
    setTimeout(() => {  document.getElementById("image1").style.display ='none';
                        document.getElementById("round1").style.display ='none';
                        document.getElementById("input1").style.display ='block';
                        document.getElementById("guess_number1").focus();}, 5000);
}
const showImage2 = () => {
    document.getElementById("result1").style.display ='none';
    document.getElementById("image2").style.display ='block';
    setTimeout(() => {  document.getElementById("image2").style.display ='none';
                        document.getElementById("round2").style.display ='none';
                        document.getElementById("input2").style.display ='block';
                        document.getElementById("guess_number2").focus();}, 5000);
}
const showImage3 = () => {
    document.getElementById("result2").style.display ='none';
    document.getElementById("image3").style.display ='block';
    setTimeout(() => {  document.getElementById("image3").style.display ='none';
                        document.getElementById("round3").style.display ='none';
                        document.getElementById("input3").style.display ='block';
                        document.getElementById("guess_number3").focus();}, 5000);
}
const validRound1 = (nbBanana) => {
    event.preventDefault(); // Empêcher le refresh automatique d'un POST
    document.getElementById("round2").style.display ='block';
    document.getElementById("input1").style.display ='none';
    document.getElementById("result1").style.display ='block';
    let guess = document.getElementById('guess_number1');
    resultat = "The banana gap : " + (parseInt(guess.value) - parseInt(nbBanana)).toString();
    good_number = "The right number : " + nbBanana
    document.getElementById('text-result1').textContent = resultat;
    document.getElementById('text-banana1').textContent = good_number;
}
const validRound2 = (nbBanana) => {
    event.preventDefault(); // Empêcher le refresh automatique d'un POST
    document.getElementById("round3").style.display ='block';
    document.getElementById("input2").style.display ='none';
    document.getElementById("result2").style.display ='block';
    let guess = document.getElementById('guess_number2');
    resultat = "The banana gap : " + (parseInt(guess.value) - parseInt(nbBanana)).toString();
    good_number = "The right number : " + nbBanana
    document.getElementById('text-result2').textContent = resultat;
    document.getElementById('text-banana2').textContent = good_number;
}
const validRound3 = (nbBanana1, nbBanana2, nbBanana3) => {
    event.preventDefault(); // Empêcher le refresh automatique d'un POST
    document.getElementById("congrats").style.display ='block';
    document.getElementById("result3").style.display ='block';
    document.getElementById("share").style.display ='block';
    document.getElementById("tomorrow").style.display ='block';
    let guess1 = document.getElementById('guess_number1').value;
    let guess2 = document.getElementById('guess_number2').value;
    let guess3 = document.getElementById('guess_number3').value;
    resultat1 = Math.abs(parseInt(guess1) - parseInt(nbBanana1));
    resultat2 = Math.abs(parseInt(guess2) - parseInt(nbBanana2));
    resultat3 = Math.abs(parseInt(guess3) - parseInt(nbBanana3));
    score = resultat1 + resultat2 + resultat3;
    score_final = "Your final score : " + score.toString() + " " + String.fromCodePoint( 127820 ) + String.fromCodePoint( 127820 ) + String.fromCodePoint( 127820 );
    res3 = (parseInt(guess3) - parseInt(nbBanana3));
    resultat = "The banana gap : " + res3.toString();
    good_number = "The right number : " + nbBanana3
    document.getElementById('text-result3').textContent = resultat;
    document.getElementById('text-banana3').textContent = good_number;
    document.getElementById('score').textContent = score_final;
    saveFinalScore(score_final, resultat, guess1, guess2, guess3);
}
const copyText = (nbBanana1, nbBanana2, nbBanana3, guess1 = null, guess2 = null, guess3 = null) => {
  document.getElementById("congrats").style.display = 'block';
  document.getElementById("result3").style.display = 'block';
  if (guess1 == null) {
    guess1 = document.getElementById('guess_number1').value;
    guess2 = document.getElementById('guess_number2').value;
    guess3 = document.getElementById('guess_number3').value;
  }
  resultat1 = Math.abs(parseInt(guess1) - parseInt(nbBanana1));
  resultat2 = Math.abs(parseInt(guess2) - parseInt(nbBanana2));
  resultat3 = Math.abs(parseInt(guess3) - parseInt(nbBanana3));
  score = resultat1 + resultat2 + resultat3;
  const shareSentence = "FindBananas #127"
    + "\n\u2022 Round 1 : " + resultat1.toString() + " " + String.fromCodePoint(127820)
    + "\n\u2022 Round 2 : " + resultat2.toString() + " " + String.fromCodePoint(127820)
    + "\n\u2022 Round 3 : " + resultat3.toString() + " " + String.fromCodePoint(127820)
    + "\nTotal : " + score.toString() + " " + String.fromCodePoint(127820) + String.fromCodePoint(127820) + String.fromCodePoint(127820);

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(shareSentence)
      .then(() => {
        alert("Copied!");
      })
      .catch(() => {
        alert("Something went wrong");
      });
  } else {
    // Fallback method
    const textarea = document.createElement('textarea');
    textarea.value = shareSentence;
    textarea.style.position = 'fixed';
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    try {
      const success = document.execCommand('copy');
      if (success) {
        alert("Copied!");
      } else {
        throw new Error();
      }
    } catch (err) {
      alert("Something went wrong");
    } finally {
      document.body.removeChild(textarea);
    }
  }
}

//This function is responsible for sending an AJAX request to the server to save the final score.
//It includes the final score, result of round 3, and the user's guesses for all three rounds.
//The function also gets the CSRF token from a cookie and includes it in the request headers to ensure that the server can validate the request.
const saveFinalScore = (finalScore, resultRound3, guess1, guess2, guess3) =>{
    const csrftoken = getCookie('csrftoken'); // Get the CSRF token from the cookies
    $.ajax({
        type: 'POST',
        url: '/',  // Replace with the URL to handle the final score on the server
        data: { // Pass the final score as data
          finalScore: finalScore,
          resultRound3: resultRound3,
          guess1: guess1,
          guess2: guess2,
          guess3: guess3
        },
        headers: {
            'X-CSRFToken': csrftoken, // Include the CSRF token in the request headers
        },
        success: function (data) {
            console.log('Final score saved successfully.');
        },
        error: function (error) {
            console.log('An error occurred while saving the final score.');
        }
    });
}

//This function is used to extract the value of a specific cookie from the browser's document.cookie.
//It's particularly important for retrieving the CSRF token, which is used to prevent Cross-Site Request Forgery attacks.
//The function ensures that you obtain the correct CSRF token for including in our AJAX request headers.
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Check if the cookie name matches the one for CSRF token
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function closeModal() {
  const modal = document.getElementById("modal");
  modal.style.display = "none";
}

// Function to load the explanation modal
document.addEventListener("DOMContentLoaded", function () {
  const modal = document.getElementById("modal");
  const closeModal = document.getElementById("close-modal");

  // Check if the user has visited before
  const hasVisitedBefore = localStorage.getItem("hasVisitedBefore");
  if (!hasVisitedBefore) {
    // Show the modal
    modal.style.display = "flex";

    // Close the modal when the close button is clicked
    closeModal.addEventListener("click", function () {
      modal.style.display = "none";
      // Set the "hasVisitedBefore" flag in localStorage
      localStorage.setItem("hasVisitedBefore", "true");
    });

    // Close the modal when the user clicks outside of it
    window.addEventListener("click", function (event) {
      if (event.target === modal) {
        modal.style.display = "none";
        // Set the "hasVisitedBefore" flag in localStorage
        localStorage.setItem("hasVisitedBefore", "true");
      }
    });
  }
});


