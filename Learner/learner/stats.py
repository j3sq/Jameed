from card import Deck, Card, Hand, HandType, HandValue, CustomEncoder, as_enum
import json


class SBin(object):
    """
    SBin is a histogram bin used to group similar hands to gather (based on draw strategy)    """

    def __init__(self):
        self.name = ''
        self.hand_type = HandType.high_card
        self.is_potential_flush = False
        self.is_potential_straight = 0
        self.rank_from = 0
        self.rank_to = 0
        self.__strategies = [[]]
        self.strategies_performance = [1]
        self.strategies_hitcount = [0]
        self.strategies_performance_unweighted = [1]
        self.index = 0

    @property
    def strategies(self):
        return self.__strategies

    @strategies.setter
    def strategies(self, st):
        self.__strategies = st
        self.strategies_performance = [1] * len(self.__strategies)
        self.strategies_performance_unweighted = [1] * len(self.__strategies)
        self.strategies_hitcount = [0] * len(self.__strategies)

    def is_member(self, hand_value):
        # hand_value in this case is HandValue
        other_is_potential_flush = hand_value.is_potential_flush[0] > -1
        other_is_potential_straight = hand_value.is_potential_straight[1]
        # if this is a potential_straight and potential_flush then consider it potential_flush only
        if other_is_potential_flush and other_is_potential_straight>-1:
            other_is_potential_straight = -1

        # ToDo: Investigate the choice made here

        return self.hand_type == hand_value.hand_type and self.rank_from <= hand_value.cards[0].rank < self.rank_to and \
               other_is_potential_flush == self.is_potential_flush and \
               self.is_potential_straight == other_is_potential_straight

    def __str__(self):
        return self.name

    def print_stats(self):
        print self.name
        for i in range(len(self.strategies)):
            print 'Strategy {0}: Hit count = {1}, Performance = {2}, Unweighted Performance = {3}'.format(i,
                                                                                                          self.strategies_hitcount[
                                                                                                              i],
                                                                                                          self.strategies_performance[
                                                                                                              i],
                                                                                                          self.strategies_performance_unweighted[
                                                                                                              i])

    def dump_stats(self, f):
        f.write(self.name + '\n')
        for i in range(len(self.strategies)):
            f.write('{0},{1},{2},{3}\n'.format(i, self.strategies_hitcount[i], self.strategies_performance[i],
                                           self.strategies_performance_unweighted[i]))


class StatBuilder(object):
    bins = []
    global_iterations_count = 0

    def __init__(self, no_of_players=2):
        self.no_of_players = no_of_players
        self.iterations_count = 0

    @staticmethod
    def bin_hand(hand):
        for hbin in StatBuilder.bins:
            if hbin.is_member(hand.hand_value):
                # fix potential flush/straight
                for idx, strategy in enumerate(hbin.strategies):
                    if len(strategy) > 0 and strategy[0] == -1:
                        if hbin.is_potential_straight in [1, 2]:
                            strategy[0] = hand.hand_value.is_potential_straight[0]
                        elif hbin.is_potential_flush:
                            strategy[0] = hand.hand_value.is_potential_flush[0]
                        hbin.strategies[idx] = strategy
                return hbin
        print 'hi'

    @staticmethod
    def define_bins():
        """
        Define your bins here. You can also edit the json file directly
        and load it using StatBuilder.load_bins()
        """
        # Two bins are listed here as an example. The rest are written directly in json
        StatBuilder.bins = []
        hbin = SBin()
        hbin.hand_type = HandType.straight_flush
        hbin.name = 'Straight Flush'
        hbin.rank_from = 0
        hbin.rank_to = 13
        hbin.is_potential_straight = False
        hbin.is_potential_flush = False
        hbin.strategies = [[]]  # Don't do anything
        StatBuilder.bins.append(hbin)
        hbin = SBin()
        hbin.hand_type = HandType.four_of_a_kind
        hbin.name = 'Four of a Kind'
        hbin.rank_from = 0
        hbin.rank_to = 13
        hbin.is_potential_straight = 0  # 0=Not potential, 1=potential via 1 option, 2=potential via 2 options
        hbin.is_potential_flush = False
        hbin.strategies = [[], [4]]  # 1: Don't do anything, 2: Throw the fifth card
        StatBuilder.bins.append(hbin)

    @staticmethod
    def dump_bins(file_name):
        # write bins (defined in define_bins) to a json file
        with open(file_name, 'w') as outfile:
            json.dump([hbin.__dict__ for hbin in StatBuilder.bins], outfile, cls=CustomEncoder)

    @staticmethod
    def load_bins(file_name):
        StatBuilder.bins = []
        with open(file_name, 'r') as infile:
            json_bins = json.load(infile, object_hook=as_enum)
            for json_bin in json_bins:
                hbin = SBin()
                for k, v in json_bin.items():
                    hbin.__setattr__(k, v)
                StatBuilder.bins.append(hbin)
                hbin.index = len(StatBuilder.bins) - 1

    @staticmethod
    def load_stats(file_name):
        with open(file_name, 'r') as f:
            StatBuilder.global_iterations_count = int(f.readline().strip())
            current_bin = None
            while True:
                l = f.readline().strip()
                if l == '':
                    break
                l_data = l.split(',')
                if len(l_data) == 1:
                    current_bin = None
                    # New bin, search for the bin using name
                    for sbin in StatBuilder.bins:
                        if sbin.name == l:
                            current_bin = sbin
                            break
                    if current_bin is None:
                        print 'Failed while loading bins stats.'
                        return
                elif len(l_data) == 4:
                    sbin.strategies_hitcount[int(l_data[0])] = int(l_data[1])
                    sbin.strategies_performance[int(l_data[0])] = float(l_data[2])
                    sbin.strategies_performance_unweighted[int(l_data[0])] = float(l_data[3])
                else:
                    print 'Invalid file format'
                    return
        print 'Bins stats loaded successfully'

    def print_stats(self):
        for sbin in StatBuilder.bins:
            sbin.print_stats()
            print '-' * 16

    def dump_stats(self, file_location):
        StatBuilder.global_iterations_count += self.iterations_count
        with open(file_location, 'w') as f:
            f.write('{0}\n'.format(StatBuilder.global_iterations_count))
            for sbin in StatBuilder.bins:
                sbin.dump_stats(f)

    def simulate_deal(self, seed=-1):
        self.iterations_count += 1
        if seed == -1:
            starting_deck = Deck()
        else:
            starting_deck = Deck(seed=seed)

        hands = []
        bins = []
        players_strategies = []
        for i in range(self.no_of_players):
            hand = Hand(deck=starting_deck)
            hands.append(hand)
            # print hand
            hand_bin = self.bin_hand(hand)
            bins.append(hand_bin)
            players_strategies.append(range(len(hand_bin.strategies)))

        # print players_strategies
        import itertools
        strategies = list(itertools.product(*players_strategies))

        # print bins[0], ' | ', bins[1]
        # print strategies
        for strategy in strategies:
            tmp_deck = starting_deck.copy()
            tmp_hands = [Hand(cards=hands[i].cards) for i in range(len(hands))]
            self.execute_strategy(tmp_deck, tmp_hands, bins, strategy)
            # print new bins
            # for hand in tmp_hands:
            #     print self.bin_hand(hand), ' | ',
            # print
            # print '_' * 15

    def execute_strategy(self, deck, hands, bins, players_strategy):
        # print players_strategy
        for i, player_strategy in enumerate(players_strategy):
            predraw_hand = Hand(hand_id=hands[i].hand_id)
            predraw_value = hands[i].hand_value.strength
            hands[i].draw(deck, bins[i].strategies[players_strategy[i]])
            postdraw_value = hands[i].hand_value.strength
            st_ratio = postdraw_value / float(predraw_value)
            perf_sum = bins[i].strategies_performance[player_strategy] * bins[i].strategies_hitcount[
                player_strategy] + st_ratio
            perf_sum_unweighted = bins[i].strategies_performance_unweighted[player_strategy] * \
                                  bins[i].strategies_hitcount[
                                      player_strategy] + (1. if st_ratio >= 1. else 0.)
            bins[i].strategies_hitcount[player_strategy] += 1
            bins[i].strategies_performance[player_strategy] = perf_sum / bins[i].strategies_hitcount[player_strategy]
            bins[i].strategies_performance_unweighted[player_strategy] = perf_sum_unweighted / \
                                                                         bins[i].strategies_hitcount[
                                                                             player_strategy]
