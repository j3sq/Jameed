from learner.card import Card, Hand, HandType, HandValue


class Player(object):
    """
    Describes and manages a player with a hand of cards (5 cards).
    All analysis is happening here
    """

    def __init__(self, deck, chips, name):
        # type (Deck)->None
        self.hand = Hand(deck)
        self.chips = chips
        self.name = name

    def __str__(self):
        return 'Name: {0}\nHand: {1}\nChips: {2}'.format(self.name, self.hand, self.chips)


