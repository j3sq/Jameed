__author__ = 'fyt'

import socket
import random
import ClientBase
import time

from Client import *
from jameed import Jameed

iMsg = 0
SIGNAL_ALIVE = '==================ALIVE======================'

# Agent Name
CURRENT_HAND = []

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))
infoAgent = pokerGames()

request2argc = {'Name?': 0, 'Chips': 2, 'Ante_Changed': 1, 'Forced_Bet': 2, 'Open?': 3, 'Call/Raise?': 4, 'Cards': 5,
                'Draw?': 0, 'Round': 1, 'Game_Over': 0, 'Player_Open': 2, 'Player_Check': 1, 'Player_Raise': 2,
                'Player_Call': 1, 'Player_Fold': 1, 'Player_All-in': 2, 'Player_Draw': 2, 'Round_Win_Undisputed': 2,
                'Round_result': 2, 'Player_Hand': 6, 'Result': 3}


# Done: Name, Ante changed, Cards, Chips, Forced_Bet, Draw?, Player_Draw, Round, Open?
# ToDo:  Call/Raise?, Game_Over, Player_Open, Player_Check, Player_Raise,
# ToDo:  Player_Call, Player_Fold, Player_All-in, Round_Win_Undisputed, Round_result, Player_Hand, Result

unprocessed_buffer = []
jameed = Jameed(debug=True)

while True:

    try:
        # Get data
        data = s.recv(BUFFER_SIZE)
        # split string into fraction
        unprocessed_buffer.extend(data.split())
        if len(unprocessed_buffer) == 0:
            continue
        RequestType = unprocessed_buffer[0]
        request_argc = request2argc[RequestType]
        MsgFractions = unprocessed_buffer[:request_argc + 1]
        unprocessed_buffer = unprocessed_buffer[request_argc+1:]
        # No. of Msg
        iMsg += 1
        # print('MsgFractions', data)

        # Get Request type
        # RequestType = MsgFractions[0]

        # Get expected number of arguments


        # "Name?"
        # /** Sent from server to clients before the game starts. */
        if RequestType == 'Name?':  # if Server request for name
            #s.send('Name ' + queryPlayerName(POKER_CLIENT_NAME) + "\n")
            queryPlayerName(POKER_CLIENT_NAME)
            s.send('Name ' + jameed.name + "\n")

        # "Chips"
        # /** Sent from server to clients when the server informs the players how many chips a player has.
        # * Append space, the players name, space and the amount of chips after this string. Separate the words by space. */
        elif RequestType == 'Chips':  # if Server remind player chips number
            if MsgFractions[1] == POKER_CLIENT_NAME:
                infoAgent.Chips = int(MsgFractions[2])
                jameed.update_others_chips(MsgFractions[1], int(MsgFractions[2]))
            else:
                infoPlayerChips(MsgFractions[1], MsgFractions[2])
                jameed.chips = int(MsgFractions[2])

        # "Ante_Changed"
        # /** Sent from server to clients when the server informs the players that the ante has changed.
        # * Append space and the value of the ante after this string. */
        elif RequestType == 'Ante_Changed':  # if ante is changed
            infoAgent.Ante = int(MsgFractions[1])
            infoAnteChanged(MsgFractions[1])
            jameed.ante = int(MsgFractions[1])

        # "Forced_Bet"
        # /** Sent from server to clients when the server informs the players that a player has made a forced bet (the ante).
        # * Append the players name and the bet value after this string. Separate the words by space. */
        elif RequestType == 'Forced_Bet':  # Notice force bet
            if MsgFractions[1] == POKER_CLIENT_NAME:
                infoAgent.playersCurrentBet = infoAgent.playersCurrentBet + int(MsgFractions[2])
                jameed.current_bet = int(MsgFractions[2])
            else:
                infoForcedBet(MsgFractions[1], MsgFractions[2])
                jameed.update_others_bet(MsgFractions[1], MsgFractions[2])

        # "Open?"
        # /** Sent from server to clients as information when a player opens.
        # * Append the players name and the total amount of chips the player has put into into the pot after this string.
        # * Separate the words by space. */
        elif RequestType == 'Open?':
            # sleep for 3 s... You can remove it...
            minimumPotAfterOpen = int(MsgFractions[1])
            playersCurrentBet = int(MsgFractions[2])
            playerRemainingChips = int(MsgFractions[3])
            tmp = queryOpenAction(minimumPotAfterOpen, playersCurrentBet, playerRemainingChips)
            tmp = jameed.get_open_action(minimumPotAfterOpen, playersCurrentBet, playerRemainingChips)
            print('%' * 20)
            print(tmp)
            if isinstance(tmp, str):  # For check and All-in
                s.send(tmp + "\n")
            elif len(tmp) == 2:  # For open
                s.send(tmp[0] + ' ' + str(tmp[1]) + " \n")

            print(SIGNAL_ALIVE)
            print(POKER_CLIENT_NAME + 'Action>', tmp)

        elif RequestType == 'Call/Raise?':
            maximumBet = int(MsgFractions[1])
            minimumAmountToRaiseTo = int(MsgFractions[2])
            playersCurrentBet = int(MsgFractions[3])
            playersRemainingChips = int(MsgFractions[4])
            tmp = queryCallRaiseAction(maximumBet, minimumAmountToRaiseTo, playersCurrentBet, playersRemainingChips)
            tmp = jameed.get_call_raise_action(maximumBet,minimumAmountToRaiseTo, playersCurrentBet, playersRemainingChips)
            if isinstance(tmp, str):  # For fold, all-in, call
                s.send(tmp + "\n")
            elif len(tmp) == 2:  # For raise
                s.send(tmp[0] + ' ' + str(tmp[1]) + " \n")
            print(SIGNAL_ALIVE)
            print(POKER_CLIENT_NAME + 'Action>', tmp)
        elif RequestType == 'Cards':  # Get Cards
            # infoCardsInHand(MsgFractions) # show info for hands
            infoAgent.CurrentHand = []
            for ielem in range(1, 6):  # 1 based indexing is required...
                infoAgent.CurrentHand.append(MsgFractions[ielem])
            infoPlayerHand(POKER_CLIENT_NAME, infoAgent.CurrentHand)
            jameed.set_hand((','.join(MsgFractions[1:])).replace('T', '10'))
            # print('CurrentHand>', infoAgent.CurrentHand)
        elif RequestType == 'Draw?':
            discardCards = jameed.get_cards_to_throw()
            # discardCards = queryCardsToThrow(infoAgent.CurrentHand)
            s.send('Throws ' + discardCards + "\n")
            print(POKER_CLIENT_NAME + ' Action>' + 'Throws ' + discardCards)

        # "Round"
        # /** Sent from server to clients when a new round begins.
        # * Append space and the round number after this string. */
        elif RequestType == 'Round':
            infoNewRound(MsgFractions[1])
            jameed.new_round()

        # "Game_Over"
        # /** Sent from server to clients when the game is completed. */
        elif RequestType == 'Game_Over':
            infoGameOver()
            break

        # "Player_Open"
        # /** Sent from server to clients as information when a player opens.
        # * Append the players name and the total amount of chips the player has put into into the pot after this string.
        # * Separate the words by space. */
        elif RequestType == 'Player_Open':
            infoPlayerOpen(MsgFractions[1], MsgFractions[2])

        # "Player_Check"
        # /** Sent from server to clients as information when a player checks.
        # * Append the players name after this string. Separate the words by space. */
        elif RequestType == 'Player_Check':
            infoPlayerCheck(MsgFractions[1])

        # "Player_Raise"
        # /** Sent from server to clients when a player raises the bet.
        # * Append the name and the raised amount of chips after this string. Separate the words by space. */
        elif RequestType == 'Player_Raise':
            infoPlayerRise(MsgFractions[1], MsgFractions[2])

        # "Player_Call"
        # /** Sent from server to clients as information when a player calls.
        # * Append the players name after this string. Separate the words by space. */
        elif RequestType == 'Player_Call':
            infoPlayerCall(MsgFractions[1])

        # "Player_Fold"
        # /** Sent from server to clients as information when a player folds.
        # * Append the players name after this string. Separate the words by space. */
        elif RequestType == 'Player_Fold':
            infoPlayerFold(MsgFractions[1])

        # "Player_All-in"
        # /** Sent from server to clients as information when a player goes all-in.
        # * Append the players name after this string. Separate the words by space. */
        elif RequestType == 'Player_All-in':
            infoPlayerAllIn(MsgFractions[1], MsgFractions[2])

        # "Player_Draw"
        # /** Sent from server to client as information when a player throws away old and draws new cards.
        # * Append the players name and the number of cards exchanged after this string. Separate the words by space. */
        elif RequestType == 'Player_Draw':
            infoPlayerDraw(MsgFractions[1], MsgFractions[2])
            if MsgFractions[1] != POKER_CLIENT_NAME:
                jameed.update_other_draw_state(MsgFractions[1], MsgFractions[2])

        # "Round_Win_Undisputed"
        # /** Sent from server to clients when the server informs the players that a player won a round undisputed.
        # * Append the players name and the amount of chips the player won after the string. Separate the words by space. */
        elif RequestType == 'Round_Win_Undisputed':
            infoRoundUndisputedWin(MsgFractions[1], MsgFractions[2])

        # "Round_result"
        # /** Sent from server to clients when the server informs the players the result of a round for a player.
        # * Append the players name and the amount of chips the player won after the string. Separate the words by space. */
        elif RequestType == 'Round_result':
            infoRoundResult(MsgFractions[1], MsgFractions[2])

        # "Player_Hand"
        # /** Sent from server to clients when the server informs the players what hand a player holds.
        # * Append the players name and the cards of the players hand after this string. Separate the words by space.*/
        elif RequestType == 'Player_Hand':
            infoPlayerHand(MsgFractions[1], MsgFractions[2:])

    except socket.timeout:
        break

s.close()
