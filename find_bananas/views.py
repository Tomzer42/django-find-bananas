from django.shortcuts import render
from django.http import HttpResponse
from bananas_updater.create_bananas import bananas_of_the_day
from bananas_updater.updater import start_sessions
from find_bananas.models import Bananas
from datetime import datetime

def home(request):

  print(Bananas.objects.count())
  print(Bananas.objects.latest('timestamp').timestamp)
  print(Bananas.objects.latest('timestamp').nb_bananas_1)
  if Bananas.objects.count() == 0 :
    bananas_of_the_day(True)

  latest_bananas = Bananas.objects.latest('timestamp')

  dico = {
    "round1": {},
    "round2": {},
    "round3": {}
  }

  dico["round1"]["number"] = latest_bananas.nb_bananas_1
  dico["round2"]["number"] = latest_bananas.nb_bananas_2
  dico["round3"]["number"] = latest_bananas.nb_bananas_3
  dico["round1"]["image"] = latest_bananas.image_1
  dico["round2"]["image"] = latest_bananas.image_2
  dico["round3"]["image"] = latest_bananas.image_3
  dico["date"] = latest_bananas.date
  print("Round 1 :", dico["round1"]["number"])
  print("Round 2 :", dico["round2"]["number"])
  print("Round 3 :", dico["round3"]["number"])


  context = {
    "dico": dico
  }

  if request.method == 'POST':
    if request.POST.get('finalScore'): #If we are in the 3rd round
      request.session['final_score'] = request.POST.get('finalScore')
      request.session['result_round3'] = request.POST.get('resultRound3')
      request.session['guess1'] = request.POST.get('guess1')
      request.session['guess2'] = request.POST.get('guess2')
      request.session['guess3'] = request.POST.get('guess3')
      print(request.session['final_score'])
      print(request.session['result_round3'])
      print(request.session['guess1'])

      # Set the 'played_game' flag in the session to True when the player finish the round 3
      request.session['played_game'] = True

      start_sessions(request)  # Start the scheduled task


  # Check if the user has already played the game
  if request.session.get('played_game', False): #If yes, we retrieved data about his results
    context["final_score"] = request.session['final_score']
    context["result_round3"] = request.session['result_round3']
    context["guess1"] = request.session['guess1']
    context["guess2"] = request.session['guess2']
    context["guess3"] = request.session['guess3']

    # If the user has already played, display the result template page
    return render(request, 'find_bananas/result.html', context)

  return render(request, 'find_bananas/home.html', context)

def about(request):
  return render(request, 'find_bananas/about.html')
