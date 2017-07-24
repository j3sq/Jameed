from learner.player import Player
from learner.card import Card, Deck, Hand, HandType, HandValue, CustomEncoder, as_enum
from learner.stats import StatBuilder,SBin

import time







()
Hand.load_hands_dict('./hands.json')
hand = Hand(cards_string='KH,QC,JD,9D,8D')

result = hand.is_potential_straight()
print result
exit()
# hand.evaluate_all_hand_combinations()


# StatBuilder.define_bins()
StatBuilder.load_bins('./bins.json')
StatBuilder.load_stats('./stats_dump')
# print StatBuilder.bins
# hand = Hand(cards_string='9C,8C,6C,5D,3D')
# hbin = StatBuilder.bin_hand(hand)
# print hand.hand_value
# print hbin
# print hbin.strategies
# exit()

# hand.is_potential_straight()
# print hand.hand_value
# hbin = StatBuilder.bin_hand(hand)
# print hbin
# print hbin.strategies
# exit()
t = time.time()
sb = StatBuilder(no_of_players=2)
import random
for i in range(1000000):
    #s = random.random()
    #print "s = ", s
    if i%1000 == 0:
        print '{:,} complete!'.format(i)
    sb.simulate_deal()
    #print '#'*15

sb.print_stats()
sb.dump_stats('./stats_dump')

# idx, hand_id = hand.is_potential_flush()
# idx, s_type, hand_id = hand.is_potential_straight()
# print idx, s_type, hand.hand_id
# if idx > -1:
#     hand = Hand(hand_id=hand_id)
#     print hand.evaluate_hand(), hand.evaluate_hand().s0
#     result = Hand._hands_dict[hand.hand_id]
#     print result

# hand.evaluate_all_hand_combinations()
print 'done in {0}'.format(time.time() - t)
