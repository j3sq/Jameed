import sys
import ClientBase
import random
from learner.card import Card, Hand, HandType, HandValue
from learner.stats import StatBuilder, SBin
import time
from math import exp

sys.path.append('../Learner')
HANDS_COMBINATIONS = 2598960
THRESHOLD_TO_OPEN = 0.2
THRESHOLD_TO_FORCE_ALL_IN = 0.95
THRESHOLD_TO_FORCE_FOLD = 0.2

# Coefficients for bias calculation of the 'Open' action
OPEN_ACTION_A_CHECK = 5.0
OPEN_ACTION_B_CHECK = -1.0
OPEN_ACTION_C_CHECK = 0.6
OPEN_ACTION_A_OPEN = 4.0
OPEN_ACTION_B_OPEN = 1.4
OPEN_ACTION_C_OPEN = -1.1
OPEN_ACTION_A_ALL_IN = 0.3
OPEN_ACTION_B_ALL_IN = 5.0
OPEN_ACTION_C_ALL_IN = -3.0

CALL_RAISE_ACTION_A_FOLD = 1.
CALL_RAISE_ACTION_B_FOLD = 1.
CALL_RAISE_ACTION_C_FOLD = 10.
CALL_RAISE_ACTION_D_FOLD = 0.4

CALL_RAISE_ACTION_A_CALL = 1.
CALL_RAISE_ACTION_B_CALL = 1.
CALL_RAISE_ACTION_C_CALL = 2.
CALL_RAISE_ACTION_D_CALL = 0.5

CALL_RAISE_ACTION_A_RAISE = 0.
CALL_RAISE_ACTION_B_RAISE = -1.
CALL_RAISE_ACTION_C_RAISE = 8.
CALL_RAISE_ACTION_D_RAISE = -0.3

CALL_RAISE_ACTION_A_ALL_IN = 0.
CALL_RAISE_ACTION_B_ALL_IN = -1.
CALL_RAISE_ACTION_C_ALL_IN = 25.
CALL_RAISE_ACTION_D_ALL_IN = -0.45

# Coefficients for bias calculation of the 'Open' amount
OPEN_AMOUNT_KEEP_MULTIPLES_OF_ANTE = 1
OPEN_AMOUNT_A = 1.0


class PlayerInfo(object):
    def __init__self(self):
        self.name = ''
        self.index = 0
        self.current_bet = 0
        self.chips = 0
        self.did_drew = False


class Jameed(object):
    def __init__(self, debug=False):
        Hand.load_hands_dict('./hands.json')
        StatBuilder.load_bins('./bins.json')
        StatBuilder.load_stats('./stats_dump')
        self.__hand = None  # type: Hand
        self.__bin = None  # type: SBin
        self.chips = 0
        self.__ante = 0
        self.current_bet = 0
        self.__no_of_players = 0
        self.__players_info = {}
        self.__debug = debug
        self.__did_draw = False

    def set_hand(self, hand_str):
        self.__hand = Hand(cards_string=hand_str)
        self.__bin = StatBuilder.bin_hand(self.__hand)
        self.debug('My hand is -> {}'.format(self.__hand))
        self.debug('My hand bin is  -> {}'.format(self.__bin))

    @property
    def ante(self):
        return self.__ante

    @ante.setter
    def ante(self, amount):
        self.__ante = amount

    @property
    def name(self):
        return 'Jameed'

    def __add_new_player(self, name):
        player_info = PlayerInfo()
        player_info.name = name
        self.__players_info[name] = player_info
        # self.debug('Player {} has joined the game'.format(name))
        self.__no_of_players = len(self.__players_info)

    def info(self, msg):
        print('JAMEED INFO :: {} :: {}'.format(time.time(), msg))

    def debug(self, msg):
        if self.__debug:
            print('JAMEED DEBUG :: {} :: {}'.format(time.time(), msg))

    def update_others_chips(self, name, chips):
        if name not in self.__players_info:
            self.__add_new_player(name)
        self.__players_info[name].chips = chips
        self.debug('Player {} has {} chips'.format(name, chips))

    def update_others_bet(self, name, bet):
        if name not in self.__players_info:
            self.__add_new_player(name)
        self.__players_info[name].current_bet = bet
        self.debug('Player {} current bet is {} chips'.format(name, bet))

    def update_other_draw_state(self, name, count):
        if name not in self.__players_info:
            self.__add_new_player(name)
        self.__players_info[name].did_draw = True
        self.debug('Player {} has threw {} card'.format(name, count))

    def get_cards_to_throw(self):
        # decide which strategy to go for
        # The decision is a random variable disrupted to maximize expected value
        beta = 0
        strategy_markers = []
        for i in range(len(self.__bin.strategies)):
            p_yield = self.__bin.strategies_performance_unweighted[
                i]  # probability that this strategy will yield better results
            expected_value = self.__bin.strategies_performance[
                i]  # probability that this strategy will yield better results
            beta += p_yield * expected_value
            strategy_markers.append(beta)
        q = random.uniform(0, beta)
        selected_strategy_idx = -1
        for i in range(len(strategy_markers)):
            if q < strategy_markers[i]:
                selected_strategy_idx = i
                break
        cards_to_throw = ''
        for i in self.__bin.strategies[selected_strategy_idx]:
            card_to_throw = str(self.__hand.hand_value.cards[i]).replace('10', 'T')
            cards_to_throw += card_to_throw + ' '
        self.debug('My hand is -> {}'.format(self.__hand))
        if cards_to_throw == '':
            self.debug('My strategy is to throw nothing')
        else:
            self.debug('My strategy is to throw -> {}'.format(cards_to_throw))
        self.__did_draw = True
        return cards_to_throw

    def new_round(self):
        # invalidate previous round state
        self.__ante = 0
        self.__bin = None
        self.__did_draw = False
        self.__hand = None
        self.__players_info.clear()
        self.current_bet = 0

    def get_open_action(self, minimum_pot_after_open, current_bet, remaining_chips):
        # Options:
        # 1- Open : ClientBase.BettingAnswer.ACTION_OPEN
        # 2- Check : ClientBase.BettingAnswer.ACTION_CHECK
        # 3- All-in : ClientBase.BettingAnswer.ACTION_ALLIN
        # In case of open, the amount to open with should be > minimum_pot_after_open and
        # ToDo: Distinguish behaviour for pre-draw and post-draw action
        # Start
        # Fixed strategy: Jameed has no enough chips -> check
        if minimum_pot_after_open > (remaining_chips + current_bet):
            self.debug('Open choice: Forced to go for check as I have not enough chips')
            return ClientBase.BettingAnswer.ACTION_CHECK
        # * Jameed has enough chips to open : Choose Open, Check or All-in
        p_hand = float(self.__hand.hand_value.strength) / HANDS_COMBINATIONS
        p_win = p_hand ** (self.__no_of_players - 1)  # This assumes independent events which is not the case,
        #                                           but should be a good approximation due to the large sample space

        # Fixed strategy: Hand is too bad -> check
        if p_win < THRESHOLD_TO_OPEN:
            self.debug('Open choice: Forced to check due to crappy hand')
            return ClientBase.BettingAnswer.ACTION_CHECK
        # Fixed strategy: Hand is too good --> All in
        if p_win > THRESHOLD_TO_FORCE_ALL_IN:
            self.debug('Open choice: Forced to go all in due to amazing hand')
            return ClientBase.BettingAnswer.ACTION_ALLIN

        # Biased random strategies
        action = self.sample_open_action_with_bias(p_win)
        if action == ClientBase.BettingAnswer.ACTION_ALLIN or action == ClientBase.BettingAnswer.ACTION_CHECK:
            return action
        elif action == ClientBase.BettingAnswer.ACTION_OPEN:
            amount = self.sample_open_amount_with_bias(p_win, minimum_pot_after_open, current_bet, remaining_chips)
            self.debug(self.debug('Open choice: Opening with {} chips'.format(amount)))
            return action, amount
        else:
            raise ValueError

    def sample_open_action_with_bias(self, p_win):

        # * Jameed has enough money to open, the action should be a random variable of {Check, Open, All-in} the
        #       distribution is function of p_win.
        ka = OPEN_ACTION_A_ALL_IN * exp(OPEN_ACTION_B_ALL_IN * p_win + OPEN_ACTION_C_ALL_IN)
        kc = OPEN_ACTION_A_CHECK * exp(OPEN_ACTION_B_CHECK * p_win + OPEN_ACTION_C_CHECK)
        ko = OPEN_ACTION_A_OPEN * exp(OPEN_ACTION_B_OPEN * p_win + OPEN_ACTION_C_OPEN)
        k_sum = kc + ko + ka
        r = random.uniform(0, k_sum)
        if r < kc:
            self.debug('Open choice: Biased to check')
            return ClientBase.BettingAnswer.ACTION_CHECK
        elif kc <= r < kc + ko:
            self.debug('Open choice: Biased to open')
            return ClientBase.BettingAnswer.ACTION_OPEN
        else:
            self.debug('Open choice: Biased to go all in')
            return ClientBase.BettingAnswer.ACTION_ALLIN

    def sample_open_amount_with_bias(self, p_win, minimum_pot_after_open, current_bet, remaining_chips):
        remaining_chips_after_minimum_open = remaining_chips + current_bet - minimum_pot_after_open

        if remaining_chips_after_minimum_open < OPEN_AMOUNT_KEEP_MULTIPLES_OF_ANTE * self.ante:
            return minimum_pot_after_open

        free_chips = remaining_chips_after_minimum_open - OPEN_AMOUNT_KEEP_MULTIPLES_OF_ANTE * self.ante
        open_amount = minimum_pot_after_open + random.uniform(0, free_chips * p_win)
        return int(open_amount)

    def get_call_raise_action(self, maximum_bet, minimum_amount_to_raise_to, current_bet, remaining_chips):
        # Options:
        # 1- Fold : ClientBase.BettingAnswer.ACTION_FOLD
        # 2- Call : ClientBase.BettingAnswer.ACTION_CALL
        # 3- Raise : ClientBase.BettingAnswer.ACTION_RAISE
        # 4- All-in : ClientBase.BettingAnswer.ACTION_ALLIN
        # Notes:
        #  - Call is only possible when maximum_bet < (current_bet + remaining_chips)
        #  - Raise is only possible when minimum_amount_to_raise_to < (current_bet + remaining_chips)
        #  - When action is to raise, the amount returned is the total chips into the pot
        # ToDo: Distinguish behaviour for pre-draw and post-draw action
        # Start
        # Fixed Strategy: Remaining chips < ante  ===> Go All-in (the reason is if we don't win this round
        #                                                      we can't play another one anyway)
        if remaining_chips < self.ante:
            self.debug('Call/Raise choice: Forced to go all as there\' no hope left')
            return ClientBase.BettingAnswer.ACTION_ALLIN

        p_hand = float(self.__hand.hand_value.strength) / HANDS_COMBINATIONS
        p_win = p_hand ** (self.__no_of_players - 1)  # This assumes independent events which is not the case,
        #                                           but should be a good approximation due to the large sample space
        # Fixed Strategy: Hand is extremely bad
        if p_win < THRESHOLD_TO_FORCE_FOLD:
            self.debug('Call/Raise choice: Forced to fold due to crappy hand')
            return ClientBase.BettingAnswer.ACTION_FOLD

        # Fixed Strategy: Hand is extremely good
        if p_win > THRESHOLD_TO_FORCE_ALL_IN:
            self.debug('Call/Raise choice: Forced to go all in due to amazing hand')
            return ClientBase.BettingAnswer.ACTION_ALLINACTION_FOLD

        action = self.sample_call_raise_action_with_bias(p_win, maximum_bet, minimum_amount_to_raise_to, current_bet,
                                                         remaining_chips)

        return action

    def sample_call_raise_action_with_bias(self, p_win, maximum_bet, minimum_amount_to_raise_to, current_bet,
                                           remaining_chips):
        k_f = CALL_RAISE_ACTION_A_FOLD + CALL_RAISE_ACTION_B_FOLD / (
            1.0 + exp(-CALL_RAISE_ACTION_C_FOLD * (p_win - 0.5 + CALL_RAISE_ACTION_D_FOLD)))
        k_c = CALL_RAISE_ACTION_A_CALL + CALL_RAISE_ACTION_B_CALL / (
            1.0 + exp(-CALL_RAISE_ACTION_C_CALL * (p_win - 0.5 + CALL_RAISE_ACTION_D_CALL)))
        k_r = CALL_RAISE_ACTION_A_RAISE + CALL_RAISE_ACTION_B_RAISE / (
            1.0 + exp(-CALL_RAISE_ACTION_C_RAISE * (p_win - 0.5 + CALL_RAISE_ACTION_D_RAISE)))
        k_a = CALL_RAISE_ACTION_A_ALL_IN + CALL_RAISE_ACTION_B_ALL_IN / (
            1.0 + exp(-CALL_RAISE_ACTION_C_ALL_IN * (p_win - 0.5 + CALL_RAISE_ACTION_D_ALL_IN)))
        k_sum = k_f + k_c + k_r + k_a
        r = random.uniform(0, k_sum)
        if r < k_f:
            self.debug('Call/Raise choice: Biased to fold')
            return ClientBase.BettingAnswer.ACTION_FOLD
        if r <= k_f + k_c:
            if maximum_bet < current_bet + remaining_chips:
                self.debug('Call/Raise choice: Biased to call')
                return ClientBase.BettingAnswer.ACTION_CALL
            else:
                self.debug('Call/Raise choice: Biased to call but forced to fold due to insufficient chips')
                return ClientBase.BettingAnswer.ACTION_FOLD
        if r <= k_f + k_c + k_r:
            if minimum_amount_to_raise_to < current_bet + remaining_chips:
                self.debug('Call/Raise choice: Biased to raise to {}'.format(minimum_amount_to_raise_to))
                return ClientBase.BettingAnswer.ACTION_RAISE, minimum_amount_to_raise_to # ToDo: Add possibility to go over the minimum
            elif maximum_bet < current_bet + remaining_chips:
                self.debug('Call/Raise choice: Biased to raise but forced to call due to insufficient chips')
                return ClientBase.BettingAnswer.ACTION_CALL
            else:
                self.debug('Call/Raise choice: Biased to raise but forced to fold due to insufficient chips')
                return ClientBase.BettingAnswer.ACTION_FOLD # ToDo: Maybe go ALL-in?

        self.debug('Call/Raise choice: Biased to go all in')
        return ClientBase.BettingAnswer.ACTION_ALLIN

