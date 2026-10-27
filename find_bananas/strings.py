"""Texts used by game.js, kept in one place and passed through gettext so
they can be translated with the rest of the site."""

from django.utils.translation import gettext as _


def game_strings() -> dict:
    return {
        "roundTitle": _("Round {n} of {total}"),
        "roundRange": _("Between {min} and {max} bananas. They stay on screen for 5 seconds."),
        "guessLabelAfterReload": _("The bananas were already shown. How many did you see?"),
        "exact": _("Exact!"),
        "tooMany": _("{n} too many"),
        "tooFew": _("{n} too few"),
        "nextRound": _("Next round"),
        "seeResult": _("See my result"),
        "scoreLabel": _("bananas off in total"),
        "scoreLabelOne": _("banana off in total"),
        "scorePerfect": _("Perfect score"),
        "topPercent": _("Top {p}% of today’s {players} players"),
        "firstPlayer": _("You are the first player today. Your ranking appears once {min} people have played."),
        "firstPlayers": _("{players} players so far today. Your ranking appears once {min} people have played."),
        "notRanked": _("This game took too long to count in today’s ranking."),
        "countdown": _("Next challenge in {h} h {m} min"),
        "countdownSoon": _("Next challenge in less than a minute"),
        "signupCta": _("Keep your results and track your progress:"),
        "signupLink": _("create a free account"),
        "historyLink": _("See all my results"),
        "shareTitle": _("Find Bananas #{number}"),
        "shareRound": _("Round {n}: {gap} off"),
        "shareTotal": _("Total: {score} off"),
        "shareTop": _("top {p}%"),
        "shareChallenge": _("Can you beat me?"),
        "copied": _("Score copied. Paste it anywhere to challenge your friends."),
        "copyFailed": _("Could not copy automatically. Copy the text below."),
        "guessRequired": _("Type a number between 0 and 9999."),
        "errors": {
            "network": _("No connection. Check your network and try again: your progress is saved."),
            "edition_over": _("This challenge has ended. Reload to play the new one."),
            "too_many_requests": _("Too many attempts from your connection. Wait a few minutes and reload."),
            "image_expired": _("The bananas can only be shown once. Type your guess."),
            "already_played": _("You already played today’s challenge with another account."),
            "default": _("The game could not continue. Reload the page: your progress is saved."),
        },
    }
