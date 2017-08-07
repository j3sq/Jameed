from enum import Enum
import json


class Card(object):
    """
    Describes (rank & suit) of one single deck card.
    Each card has an integer value (int_value) which is used to determine card rank and suit according to the following
    formula:
        suit = int_value / 13    (0: Clubs, 1: Diamonds, 2: Hearts, 3: Spades)
        rank = (int_value % 13) + 2 (where 0=>2, 1=>3, ...8=>10, 9=>J, 10=>Q, 11=>K, 12=>A)
    An int_value = -1 indicates an uninitialized card (card will have a suite = -1, and rank = -1)
    """
    suits = ('C', 'D', 'H', 'S')
    ranks = ('2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A')

    def __init__(self, int_value=-1):
        self.int_value = int_value
        self.rank = -1
        self.suit = -1
        if -1 < int_value < 52:
            self.rank = int_value % 13
            self.suit = int_value / 13

    def __str__(self):
        assert -1 < self.int_value < 52, 'Card not initialized'
        return '{0}{1}'.format(Card.ranks[self.rank], Card.suits[self.suit])

    def __int__(self):
        return self.int_value

    def __mul__(self, other):
        return self.int_value * other

    def __add__(self, other):
        return self.int_value + other

    def __radd__(self, other):
        return self.int_value + other

    def __eq__(self, other):
        return self.int_value == other.int_value

    @staticmethod
    def from_suit_first_id(card_id=-1):
        # type(int)->Card
        assert -1 < card_id < 52, 'Card value out of range'
        suit = card_id % 4
        rank = card_id / 4
        return Card(suit * 13 + rank)

    @staticmethod
    def from_string(string):
        # type(str)->Card
        string = string.upper()
        rank = Card.ranks.index(string[0:len(string) - 1])  # the 0:1 is needed for 10
        suit = Card.suits.index(string[-1])
        return Card(suit * 13 + rank)

    @staticmethod
    def from_rank_and_suit(rank, suit):
        # type(int, int)->Card
        return Card(suit * 13 + rank)


class Deck(object):
    """
    Describes and manages a deck of cards (52 cards, no jokers).
    """

    def __init__(self, cards_values=None, seed=-1):
        import random
        if cards_values is None:
            cards_values = range(0, 52)
            if 0 < seed < 1:
                random.shuffle(cards_values, lambda: seed)
            else:
                random.shuffle(cards_values)

        self.in_cards = []  # type: list[Card]
        self.out_cards = []  # type: list[Card]
        self.played_cards_pointer = 0  # points to the current top of the deck that's still available (not out already)

        for card_value in cards_values:
            self.in_cards.append(Card(card_value))

    def __str__(self):
        return 'In cards: {0}.\nOut cards: {1} '.format(self.str_in_cards(), self.str_out_cards())

    def str_in_cards(self):
        return ' '.join(str(card) for card in self.in_cards)

    def str_out_cards(self):
        return ' '.join(str(card) for card in self.out_cards)

    def deal_cards(self, count):
        # type: (int) -> list[Card]
        assert 0 < count <= 5, 'Only 1, 2, 3, 4 or 5 cards can be dealt at once'
        assert len(self.in_cards) > count, 'Not enough cards!'
        dealt_cards = []  # type: list[Card]
        while count > 0:
            dealt_cards.append(self.in_cards.pop())
            count -= 1
        self.out_cards.extend(dealt_cards)
        return dealt_cards

    def copy(self):
        deck_copy = Deck(cards_values=[card.int_value for card in self.in_cards])
        deck_copy.out_cards = [Card(int_value=card.int_value) for card in self.out_cards]
        deck_copy.played_cards_pointer = self.played_cards_pointer
        return deck_copy


class HandType(Enum):
    high_card = 0
    one_pair = 1
    two_pair = 2
    three_of_a_kind = 3
    straight = 4
    flush = 5
    full_house = 6
    four_of_a_kind = 7
    straight_flush = 8


PUBLIC_ENUMS = {'HandType': HandType}


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if type(obj) in PUBLIC_ENUMS.values():
            return {'__enum__': str(obj)}
        elif type(obj) is Card:
            return {'Card': str(obj)}
        elif type(obj) is HandValue:
            return obj.__dict__
        return json.JSONEncoder.default(self, obj)


def as_enum(d):
    if "__enum__" in d:
        name, member = d["__enum__"].split(".")
        return getattr(PUBLIC_ENUMS[name], member)
    if 'Card' in d:
        return Card.from_string(d['Card'])
    else:
        return d


class HandValue(object):
    def __init__(self, hand_type, cards):
        # type(HandType, Card, Card, Card, Card, Card)-> None
        self.hand_type = hand_type
        self.cards = cards

        self._s0 = -1
        self.strength = -1
        self.is_potential_flush = (-1, -1)
        self.is_potential_straight = (-1, -1, -1)

    def __str__(self):
        return '{0},{1},{2},{3},{4},{5},{6},{7},{8},{9}'.format(self.hand_type, self.cards[0], self.cards[1],
                                                                self.cards[2], self.cards[3], self.cards[4], self.s0,
                                                                self.strength, self.is_potential_straight,
                                                                self.is_potential_flush)

    # s0 is a heuristic for hand strength
    @property
    def s0(self):
        if self._s0 != -1:
            return self._s0
        self._s0 = self.hand_type.value * 13 ** 5 + self.cards[0].rank * 13 ** 4 + self.cards[1].rank * 13 ** 3 + \
                   self.cards[2].rank * 13 ** 2 + self.cards[3].rank * 13 + self.cards[4].rank
        return self._s0


class Hand(object):
    """
    Manages a hand of 5 cards
    """
    _hands_dict = {}

    def __init__(self, deck=None, cards=None, cards_id=None, cards_id_suit_first=None, hand_id=None, cards_string=None):
        self.cards = []
        if deck is not None:
            self.cards = deck.deal_cards(5)
        elif cards is not None:
            self.cards = [Card(card.int_value) for card in cards]
        elif cards_id is not None:
            for card_id in cards_id:
                self.cards.append(Card(card_id))
        elif cards_id_suit_first is not None:
            for card_id in cards_id_suit_first:
                self.cards.append(Card.from_suit_first_id(card_id))
        elif hand_id is not None:
            for j in range(4, -1, -1):
                card_id = hand_id // 52 ** j
                self.cards.append(Card(card_id))
                hand_id %= 52 ** j
        elif cards_string is not None:
            cards = cards_string.split(',')
            for card in cards:
                self.cards.append(Card.from_string(card))
        else:
            raise (NotImplementedError, 'Hands constructed in an unsupported way')

        self.sort_hand()
        self.as_rank_only = self.get_rank_only()
        self._hand_value = None

    def __str__(self):
        return ' '.join(str(card) for card in self.cards)

    def sort_hand(self):
        import operator
        self.cards.sort(key=operator.attrgetter('rank', 'suit'), reverse=True)

    def get_rank_only(self):
        return [card.rank for card in self.cards]

    @property
    def hand_id(self):
        return self.cards[0] * 52 ** 4 + self.cards[1] * 52 ** 3 + self.cards[2] * 52 ** 2 + self.cards[3] * 52 + \
               self.cards[4]

    def hand_id_to_cards_id(self, hand_id):
        cards_id = []
        for i in range(0, 5):
            cards_id.append((hand_id % 52 ** (i + 1)) / 52 ** i)

    def evaluate_hand(self):
        # type()->HandValue
        # build some data about the hand
        suits = [0] * 4
        ranks = [0] * 13
        pairs = 0
        triples = 0
        quads = 0
        pair_idx = []
        triple_idx = -1
        quad_idx = -1

        for i, card in enumerate(self.cards):
            suits[card.suit] += 1
            ranks[card.rank] += 1
            if ranks[card.rank] == 2:
                pairs += 1
                pair_idx.append(i - 1)
            if ranks[card.rank] == 3:
                pairs -= 1
                pair_idx.remove(i - 2)
                triples += 1
                triple_idx = i - 2
            if ranks[card.rank] == 4:
                triples -= 1
                triple_idx = -1
                quads += 1
                quad_idx = i - 3

        flush = max(suits) == 5
        high_card = max(ranks) == 1
        straight = high_card and (self.cards[0].rank == (self.cards[-1].rank + 4)
                                  or (self.cards[0].rank == 12 and self.cards[1].rank == 3))

        if flush and straight:
            return HandValue(HandType.straight_flush, self.cards)
        if flush:
            return HandValue(HandType.flush, self.cards)
        if straight:
            return HandValue(HandType.straight, self.cards)

        if high_card:
            return HandValue(HandType.high_card, self.cards)

        # check for full house
        if triples == 1 and pairs == 1:
            return HandValue(HandType.full_house, [self.cards[triple_idx], self.cards[triple_idx + 1],
                                                   self.cards[triple_idx + 2],
                                                   self.cards[pair_idx[0]], self.cards[pair_idx[0] + 1]])

        # check for one_pair
        if pairs == 1:
            kicker_idx = range(0, 5)
            kicker_idx.pop(pair_idx[0])
            kicker_idx.pop(pair_idx[0])
            return HandValue(HandType.one_pair, [self.cards[pair_idx[0]], self.cards[pair_idx[0] + 1],
                                                 self.cards[kicker_idx[0]],
                                                 self.cards[kicker_idx[1]], self.cards[kicker_idx[2]]])

        # check for two pairs
        if pairs == 2:
            kicker_idx = range(0, 5)
            kicker_idx.pop(pair_idx[0])
            kicker_idx.pop(pair_idx[0])
            kicker_idx.pop(pair_idx[1] - 2)
            kicker_idx.pop(pair_idx[1] - 2)
            return HandValue(HandType.two_pair, [self.cards[pair_idx[0]], self.cards[pair_idx[0] + 1],
                                                 self.cards[pair_idx[1]],
                                                 self.cards[pair_idx[1] + 1], self.cards[kicker_idx[0]]])

        # check for three of a kind
        if triples == 1:
            kicker_idx = range(0, 5)
            kicker_idx.pop(triple_idx)
            kicker_idx.pop(triple_idx)
            kicker_idx.pop(triple_idx)

            return HandValue(HandType.three_of_a_kind, [self.cards[triple_idx], self.cards[triple_idx + 1],
                                                        self.cards[triple_idx + 2],
                                                        self.cards[kicker_idx[0]], self.cards[kicker_idx[1]]])

        # check for four of a kind
        if quads == 1:
            kicker_idx = range(0, 5)
            kicker_idx.pop(quad_idx)
            kicker_idx.pop(quad_idx)
            kicker_idx.pop(quad_idx)
            kicker_idx.pop(quad_idx)

            return HandValue(HandType.four_of_a_kind, [self.cards[quad_idx], self.cards[quad_idx + 1],
                                                       self.cards[quad_idx + 2],
                                                       self.cards[quad_idx + 3], self.cards[kicker_idx[0]]])

    def evaluate_all_hand_combinations(self):
        import itertools
        hands_dict = {}
        cards = range(0, 52)
        all_hands = itertools.combinations(cards, 5)
        for combination in all_hands:
            # adjust deck numbers so that 0,1,2,3,4 is 2C,2D,2H,2S,3C instead of 2C,3C,4C,5C,6C
            self.cards = []
            hand = Hand(cards_id_suit_first=combination)
            hand_value = hand.evaluate_hand()
            if hand_value.hand_type == HandType.one_pair or hand_value.hand_type == HandType.high_card:
                hand_value.is_potential_flush = hand.is_potential_flush()
                hand_value.is_potential_straight = hand.is_potential_straight()
            hands_dict[hand.hand_id] = hand_value
            # if len(hands_dict) == 100:
            #   break

        sorted_dic_as_tuples = sorted(hands_dict.items(), key=lambda entry: entry[1].s0)
        del hands_dict
        print ('Done sorting: ', len(sorted_dic_as_tuples))
        hands_dict = {}
        duplicate_count = 0
        count = 0
        last_strength = -1
        for hand_id, hand_value in sorted_dic_as_tuples:
            if hand_value.s0 != last_strength:
                last_strength = hand_value.s0
                count += duplicate_count + 1
                duplicate_count = 0
            else:
                duplicate_count += 1

            hand_value.strength = count
            hands_dict[hand_id] = str(hand_value)
        print ('Saving!')
        import json
        with open('./hands.json', 'w') as outfile:
            json.dump(hands_dict.items(), outfile, cls=CustomEncoder)  # , pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load_hands_dict(file_name):
        import json
        with open(file_name, 'r') as infile:
            Hand._hands_dict = dict(json.load(infile, object_hook=as_enum))

    def lowest_rank_of_suit(self, suit):
        if suit == -1:
            check_suit = False
        else:
            check_suit = True
        lowest_rank = 14
        lowest_rank_idx = -1
        for i, card in enumerate(self.cards):
            if card.rank < lowest_rank and (card.suit == suit or not check_suit):
                lowest_rank = card.rank
                lowest_rank_idx = i

        return lowest_rank_idx

    def highest_rank_of_suit(self, suit=-1):
        if suit == -1:
            check_suit = False
        else:
            check_suit = True
        highest_rank = -1
        highest_rank_idx = -1
        for i, card in enumerate(self.cards):
            if card.rank > highest_rank and (card.suit == suit or not check_suit):
                highest_rank = card.rank
                highest_rank_idx = i

        return highest_rank_idx

    def get_card_of_suit(self, suit, skip=0):
        count = 0
        for i, card in enumerate(self.cards):
            if card.suit == suit:
                count += 1
                if count > skip:
                    return i

    def get_card_of_rank(self, rank, suit=-1):
        for i, card in enumerate(self.cards):
            if card.rank == rank and (suit == -1 or card.suit == suit):
                return i

    def is_potential_flush(self):
        # returns a tuple (idx, hand_id). If the hand is potential flush, idx is the index of the card to be thrown and
        # hand_id is the (the lowest possible) potential flush hand_id. If hand is not a potential flush (-1,-1) is
        #  returned
        suits = [0] * 4
        for card in self.cards:
            suits[card.suit] += 1
        if max(suits) != 4:
            return -1, -1
        # so it's a potential flush, get the lowest card that can make this a flush
        idx = self.get_card_of_suit(suits.index(1))
        ranks = range(13)
        for card in self.cards:
            ranks[card.rank] = 14
        rank = ranks.index(min(ranks))
        indices = range(5)
        indices.pop(idx)
        hand = Hand(cards=[self.cards[indices[0]], self.cards[indices[1]], self.cards[indices[2]],
                           self.cards[indices[3]], Card.from_rank_and_suit(rank, self.cards[indices[0]].suit)])
        return idx, hand.hand_id

    def is_potential_straight(self):
        # returns a tuple (idx,type, hand_id). If the hand is potential straight, idx is the index of the card to be
        # thrown and hand_id is the potential flush hand_id.
        # type can be 2 indicating that two ranks can make this hand straight (e.g. 3S,4C,5D,6S,JH can become straight
        # by either 2X card or 7X card. On the hand, type 1 means that there's only one card rank that can make the hand
        # straight (e.g. 3S,4C,6S,7D,8D can become straight by 5X alone)
        # If hand is not a potential flush (-1,-1,-1) is returned

        # check for low ace case

        i = self.highest_rank_of_suit()
        idx = -1
        if self.cards[i].rank == 12:
            remaining_ranks = [0, 1, 2, 3]
            for i, card in enumerate(self.cards):
                try:
                    remaining_ranks.pop(remaining_ranks.index(card.rank))
                except ValueError:
                    idx = i
            if len(remaining_ranks) == 1:
                indices = range(5)
                indices.pop(idx)
                hand = Hand(cards=[self.cards[indices[0]], self.cards[indices[1]], self.cards[indices[2]],
                                   self.cards[indices[3]],
                                   Card.from_rank_and_suit(remaining_ranks[0], (self.cards[indices[0]].suit + 1) % 4)])
                return idx, 1, hand.hand_id
        # Check for all other cases
        straight_hands = [[0, 1, 2, 3, 4], [1, 2, 3, 4, 5], [2, 3, 4, 5, 6], [3, 4, 5, 6, 7], [4, 5, 6, 7, 8],
                          [5, 6, 7, 8, 9], [6, 7, 8, 9, 10], [7, 8, 9, 10, 11], [8, 9, 10, 11, 12]]
        potential_hands_indices = []
        for card in self.cards:
            for i, straight_hand in enumerate(straight_hands):
                try:
                    straight_hand.pop(straight_hand.index(card.rank))
                    if len(straight_hand) == 1:
                        potential_hands_indices.append(i)
                except ValueError:
                    pass
        potential_hands_count = len(potential_hands_indices)
        if potential_hands_count == 0:
            return -1, -1, -1
        else:
            # make a histogram of all potential hands + the current hand
            hist = [0] * 13
            # potential hands
            for potential_hands_index in potential_hands_indices:
                for idx in range(potential_hands_index, potential_hands_index + 5):
                    hist[idx] += 1
            # current hand
            for card in self.cards:
                hist[card.rank] += 1

            # Now do a moving sum to find which combination with the highest potential
            largest_sum = -1
            largest_sum_i = -1
            for i in range(0, 10):
                current_sum = sum(hist[i:i + 5])
                if current_sum > largest_sum:
                    largest_sum = current_sum
                    largest_sum_i = i

            potential_hand = range(largest_sum_i, largest_sum_i + 5)
            idx = -1
            for i, card in enumerate(self.cards):
                try:
                    potential_hand.pop(potential_hand.index(card.rank))
                except ValueError:
                    idx = i

            indices = range(5)
            indices.pop(idx)
            hand = Hand(cards=[self.cards[indices[0]], self.cards[indices[1]], self.cards[indices[2]],
                               self.cards[indices[3]],
                               Card.from_rank_and_suit(potential_hand[0], (self.cards[indices[0]].suit + 1) % 4)])

            # In some cases like 5X,6X,7X,8X,10X there're more than two possible straights, namely:
            # 1- Throw 10X and draw 9X => 5X,6X,7X,8X,9X
            # 2- Throw 10X and draw 4X => 4X,5X,6X,7X,8X
            # 3- Throw 5X  and draw 9X => 6X,7X,8X,9X,10X
            # However the third option (throwing 5x) is less likely to happen compared to the combination of 1 and 2 and
            # therefore the case is disregarded

            if potential_hands_count > 2:
                potential_hands_count = 2
            return idx, potential_hands_count, hand.hand_id

    @property
    def hand_value(self):
        if self._hand_value is not None:
            return self._hand_value
        str_value = Hand._hands_dict[self.hand_id]
        str_value = str_value.replace('(', '')
        str_value = str_value.replace(')', '')
        fields = str_value.split(',')
        hand_type = HandType[fields[0].split('.')[1]]
        cards = [Card.from_string(fields[1]), Card.from_string(fields[2]), Card.from_string(
            fields[3]), Card.from_string(fields[4]), Card.from_string(fields[5])]

        s0 = int(fields[6])
        strength = int(fields[7])
        potential_straight = (int(fields[8]), int(fields[9]), int(fields[10]))
        potential_flush = (int(fields[11]), int(fields[12]))

        hand_value = HandValue(hand_type=hand_type, cards=cards)
        hand_value._s0 = s0
        hand_value.strength = strength
        hand_value.is_potential_flush = potential_flush
        hand_value.is_potential_straight = potential_straight
        self._hand_value = hand_value
        return hand_value

    def draw(self, deck, cards_to_throw):
        for card_to_throw in cards_to_throw:
            # find the card in hand (Hand and HandValue have different ordering scheme)
            for idx, card in enumerate(self.cards):
                if card == self.hand_value.cards[card_to_throw]:
                    self.cards[idx] = deck.deal_cards(1)[0]
        # reset all cached parameters and state
        self.sort_hand()
        self.as_rank_only = self.get_rank_only()
        self._hand_value = None
        # print self

