const showImage1 = () => {
    document.getElementById("image1").style.display ='block';
    setTimeout(() => {  document.getElementById("image1").style.display ='none';
                        document.getElementById("round1").style.display ='none';
                        document.getElementById("input1").style.display ='block';}, 5000);
}
const showImage2 = () => {
    document.getElementById("result1").style.display ='none';
    document.getElementById("image2").style.display ='block';
    setTimeout(() => {  document.getElementById("image2").style.display ='none';
                        document.getElementById("round2").style.display ='none';
                        document.getElementById("input2").style.display ='block';}, 5000);
}
const showImage3 = () => {
    document.getElementById("result2").style.display ='none';
    document.getElementById("image3").style.display ='block';
    setTimeout(() => {  document.getElementById("image3").style.display ='none';
                        document.getElementById("round3").style.display ='none';
                        document.getElementById("input3").style.display ='block';}, 5000);
}
const validRound1 = (nbBanana) => {
    document.getElementById("round2").style.display ='block';
    document.getElementById("input1").style.display ='none';
    document.getElementById("result1").style.display ='block';
    let guess = document.getElementById('guess_number1');
    resultat = "Différence de bananes : " + (parseInt(guess.value) - parseInt(nbBanana)).toString();
    good_number = "Le juste nombre : " + nbBanana
    document.getElementById('text-result1').textContent = resultat;
    document.getElementById('text-banana1').textContent = good_number;
}
const validRound2 = (nbBanana) => {
    document.getElementById("round3").style.display ='block';
    document.getElementById("input2").style.display ='none';
    document.getElementById("result2").style.display ='block';
    let guess = document.getElementById('guess_number2');
    resultat = "Différence de bananes : " + (parseInt(guess.value) - parseInt(nbBanana)).toString();
    good_number = "Le juste nombre : " + nbBanana
    document.getElementById('text-result2').textContent = resultat;
    document.getElementById('text-banana2').textContent = good_number;
}
const validRound3 = (nbBanana1, nbBanana2, nbBanana3) => {
    document.getElementById("congrats").style.display ='block';
    document.getElementById("result3").style.display ='block';
    document.getElementById("share").style.display ='block';
    let guess1 = document.getElementById('guess_number1');
    let guess2 = document.getElementById('guess_number2');
    let guess3 = document.getElementById('guess_number3');
    resultat1 = Math.abs(parseInt(guess1.value) - parseInt(nbBanana1));
    resultat2 = Math.abs(parseInt(guess2.value) - parseInt(nbBanana2));
    resultat3 = Math.abs(parseInt(guess3.value) - parseInt(nbBanana3));
    score = resultat1 + resultat2 + resultat3;
    score_final = "Ton score final : " + score.toString() + " " + String.fromCodePoint( 127820 ) + String.fromCodePoint( 127820 ) + String.fromCodePoint( 127820 );
    res3 = (parseInt(guess3.value) - parseInt(nbBanana3));
    resultat = "Différence de bananes : " + res3.toString();
    good_number = "Le juste nombre : " + nbBanana3
    document.getElementById('text-result3').textContent = resultat;
    document.getElementById('text-banana3').textContent = good_number;
    document.getElementById('score').textContent = score_final;
}
const copyText = (nbBanana1, nbBanana2, nbBanana3) => {
    document.getElementById("congrats").style.display ='block';
    document.getElementById("result3").style.display ='block';
    let guess1 = document.getElementById('guess_number1');
    let guess2 = document.getElementById('guess_number2');
    let guess3 = document.getElementById('guess_number3');
    resultat1 = Math.abs(parseInt(guess1.value) - parseInt(nbBanana1));
    resultat2 = Math.abs(parseInt(guess2.value) - parseInt(nbBanana2));
    resultat3 = Math.abs(parseInt(guess3.value) - parseInt(nbBanana3));
    score = resultat1 + resultat2 + resultat3;
    const shareSentence = "FindBananas #1"
                        + "\n\u2022 Round 1 : " + resultat1.toString() + " " + String.fromCodePoint( 127820 )
                        + "\n\u2022 Round 2 : " + resultat2.toString() + " "  + String.fromCodePoint( 127820 )
                        + "\n\u2022 Round 3 : " + resultat3.toString() + " "  + String.fromCodePoint( 127820 )
                        + "\nTotal : " + score.toString() + " "  + String.fromCodePoint( 127820 ) + String.fromCodePoint( 127820 ) + String.fromCodePoint( 127820 )
    navigator.clipboard
    .writeText(shareSentence)
    .then(() => {
                alert("Copied !");
              })
              .catch(() => {
                alert("something went wrong");
              });

}
