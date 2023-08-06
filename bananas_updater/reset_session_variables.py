from django.contrib.sessions.models import Session

def reset_session_variables(request):
    # Reset the desired session variables
    session_keys_to_reset = [
        'final_score',
        'result_round3',
        'guess1',
        'guess2',
        'guess3',
        'played_game',
    ]
    for key in session_keys_to_reset:
        if key in request.session:
            del request.session[key]

    # Save the session after removing variables
    request.session.save()
    print("Users' sessions have been cleared")
