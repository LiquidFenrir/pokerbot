import time

def reduce_cards(cards):
    colors = {
        " of Spades": "S",
        " of Diamonds": "D",
        " of Hearts": "H",
        " of Clubs": "C",
    }
    numbers = {
        "Two": "2",
        "Three": "3",
        "Four": "4",
        "Five": "5",
        "Six": "6",
        "Seven": "7",
        "Eight": "8",
        "Nine": "9",
        "Ten": "T",
        "Jack": "J",
        "Queen": "Q",
        "King": "K",
        "Ace": "A",
    }
    for i, card in enumerate(cards):
        for k, v in colors.items():
            if k in card:
                card = card.replace(k, v)
        for k, v in numbers.items():
            if k in card:
                card = card.replace(k, v)
        cards[i] = card
    return cards

def to_number(card):
    FACE_CARDS = {'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    if card[0].isnumeric():
        return int(card[0])
    else:
        return FACE_CARDS[card[0]]

def check_straight(cards):
    if len(cards) >= 5:
        low_ace = list(cards)
        for i in range(1,4):
            if low_ace[-i][0] == "A":
                low_ace.insert(0, "1" + low_ace[-i][1])
            else:
                break

        oldcard = ""
        straights = [[]]
        for card in low_ace:
            if oldcard:
                if to_number(oldcard) == to_number(card):
                    continue
                elif to_number(oldcard)+1 == to_number(card):
                    pass
                else:
                    straights.append([])
            oldcard = card
            straights[-1].append(card)

        for straight in straights:
            while len(straight) > 5:
                straight.pop(0)
            if len(straight) == 5:
                return straight

    return []

colors = [
    "S",  # Spades
    "D",  # Diamonds
    "H",  # Hearts
    "C",  # Clubs
]
single_cards = [
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "T",  # 10
    "J",  # Jack
    "Q",  # Queen
    "K",  # King
    "A",  # Ace
]
fours = threes = doubles = fulls = highs = []

def gen_lists():
    start = time.clock()

    global fours
    global threes 
    global doubles
    global fulls
    global highs

    fours = [frozenset([f"{single_card}{color}" for color in colors]) for single_card in single_cards]

    threes = []
    doubles = []
    for four in fours:
        four = list(four)
        threes.append(frozenset(four[:3]))
        threes.append(frozenset(four[1:]))

        threes.append(frozenset(four[2:] + four[:1]))
        threes.append(frozenset(four[3:] + four[:2]))

        doubles.append(frozenset([four[0], four[1]]))
        doubles.append(frozenset([four[0], four[2]]))
        doubles.append(frozenset([four[0], four[3]]))

        doubles.append(frozenset([four[1], four[2]]))
        doubles.append(frozenset([four[1], four[3]]))

        doubles.append(frozenset([four[2], four[3]]))

    fulls = [frozenset(list(double) + list(three)) for three in threes for double in doubles if not three.issuperset(double)]

    highs = frozenset([f"{single_card}{color}" for color in colors for single_card in single_cards[9:]])

    end = time.clock()
    print("time taken for list creation:", end-start)

def check_combinations(common, hand):
    common = reduce_cards(common)
    common.sort(key=to_number)
    hand = reduce_cards(hand)
    hand.sort(key=to_number)
    cards = common + hand
    cards.sort(key=to_number)

    flushes = {color: [] for color in colors}
    for color in colors:
        for card in cards:
            if color in card:
                flushes[color].append(card)

    for k, v in flushes.items():
        while len(v) > 5:
            v.pop(0)
        straight_flush = check_straight(v)
        if len(straight_flush) == 5 and straight_flush == v:
            if straight_flush[-1][0] == "A":
                return (10, "Royal flush", straight_flush)
            else:
                return (9, "Straight flush", straight_flush)

    four_of_a_kind = [list(four) for four in fours if four.issubset(cards)]
    if four_of_a_kind:
        return (8, "Four of a kind", four_of_a_kind)

    full_houses = [list(full) for full in fulls if full.issubset(cards)]
    if full_houses:
        return (7, "Full house", full_houses)

    for k, flush in flushes.items():
        if len(flush) >= 5:
            return (6, "Flush", flush)

    straight = check_straight(cards)
    if straight:
        return (5, "Straight", straight)

    three_of_a_kind = [list(three) for three in threes if three.issubset(cards)]
    if three_of_a_kind:
        return (4, "Three of a kind", three_of_a_kind)

    pairs = [list(double) for double in doubles if double.issubset(cards)]
    while len(pairs) > 2:
        pairs.pop(0)
    if len(pairs) == 2:
        return (3, "Two pairs", pairs)
    elif len(pairs) == 1:
        return (2, "Pair", pairs)

    high_cards = list(highs.intersection(hand))
    if high_cards:
        return (1, "High card", high_cards)
    else:
        return (0, "Nothing", [])
