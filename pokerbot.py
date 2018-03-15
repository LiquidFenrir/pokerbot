import yaml

import discord
from discord.ext import commands
import logging

import random, time
from check import check_combinations, to_number, gen_lists

alone = True

try:
    with open("config.yaml") as c:
        config = yaml.safe_load(c)
except FileNotFoundError:
    exit("Config file not found.")

bot = commands.Bot(command_prefix=config['prefix'],
                   description=config['description'])

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)

async def send(ctx, msg):
    print(msg)
    await ctx.send(msg)

def format_cards(cards):
    colors = {
        "Spades": 0x1F0A0,
        "Hearts": 0x1F0B0,
        "Diamonds": 0x1F0C0,
        "Clubs": 0x1F0D0,
    }
    numbers = {
        "Ace": 1,
        "Two": 2,
        "Three": 3,
        "Four": 4,
        "Five": 5,
        "Six": 6,
        "Seven": 7,
        "Eight": 8,
        "Nine": 9,
        "Ten": 0xA,
        "Jack": 0xB,
        "Queen": 0xD,
        "King": 0xE,
    }
    formatted = ""
    for card in cards:
        uni = 0
        for k, v in colors.items():
            if k in card:
                uni = v
                break
        for k, v in numbers.items():
            if k in card:
                uni += v
                break
        formatted += f"{chr(uni)} {card}\n"
    return formatted

class Player:
    def __init__(self, player: discord.User):
        self.player = player
        self.name = player.name
        self.mention = player.mention
        self.money = 100
        self.hand = []
        self.small_blind = False
        self.big_blind = False
        self.total_bet = 0

    def __eq__(self, other):
        return self.player == other.player

    async def send(self, msg):
        try:
            print(f"sending to {self.name}:")
            await send(self.player, msg)
        except Exception as e:
            print("Some retard doesn't like DMs", e)

    async def bet(self, ctx, amount, minimum):
        minimum -= self.total_bet

        if amount > self.money:
            await self.send(f"You don't have enough money to bet that much. (maximum {self.money})")
        elif amount < minimum:
            await self.send(f"You have to bet at least {minimum} to match.")
        else:
            self.total_bet += amount
            self.money -= amount
            return True

        return False

active_player = None

WAITING_FOR_PLAYERS = 0
PRE_FLOP = 1
FLOP = 2
TURN = 3
RIVER = 4
SHOWDOWN = 5

class Game():
    def __init__(self):
        self.started = False
        self.players = []
        self.active_players = []
        self.active_player_id = 0
        self.deck = []
        self.common_cards = []
        self.round_number = 0
        self.base_blind = 5
        self.blind_amount = 0
        self.top_bet = 0
        self.state = WAITING_FOR_PLAYERS
        self.balance = 0  # amount of money on the table

    def init_deck(self):
        self.deck.clear()
        colors = ["Spades", "Diamonds", "Hearts", "Clubs"]
        numbers_name = {
            2: "Two",
            3: "Three",
            4: "Four",
            5: "Five",
            6: "Six",
            7: "Seven",
            8: "Eight",
            9: "Nine",
            10: "Ten",
        }
        numbers = [numbers_name[i] for i in range(2, 10+1)]
        numbers += ["Jack", "Queen", "King", "Ace"]
        for color in colors:
            for number in numbers:
                self.deck.append(f"{number} of {color}")
        random.shuffle(self.deck)

    async def add_player(self, ctx):
        """Adds a player to the list before starting a game."""
        player = Player(ctx.message.author)
        if alone or not player in self.players:
            self.players.append(player)
            await send(ctx, f"Player {player.name} added to game!")
        else:
            await send(ctx, f"Player {player.name} already scheduled for game!")

    async def remove_player(self, ctx):
        """Removes a player from the list before starting a game."""
        player = Player(ctx.message.author)
        if not player in self.players:
            await send(ctx, f"Player {player.name} not scheduled for game!")
        else:
            self.players.remove(player)
            await send(ctx, f"Player {player.name} removed from game!")

    async def end_game(self):
        self.started = False
        self.players.clear()
        self.state = WAITING_FOR_PLAYERS

    async def take_blinds(self, ctx):
        small_blind = big_blind = None
        for player in self.active_players:
            if player.small_blind:
                small_blind = player
                if player.money < self.blind_amount:
                    self.balance += player.money
                    player.money = 0
                    player.total_bet = player.money
                else:
                    self.balance += self.blind_amount
                    player.money -= self.blind_amount
                    player.total_bet = self.blind_amount
            elif player.big_blind:
                big_blind = player
                if player.money < self.blind_amount*2:
                    self.balance += player.money
                    player.total_bet = player.money
                    player.money = 0
                else:
                    self.balance += self.blind_amount*2
                    player.money -= self.blind_amount*2
                    player.total_bet = self.blind_amount*2

        self.top_bet = self.blind_amount*2
        await send(ctx, f"Players {small_blind.mention} and {big_blind.mention} automatically bet {self.blind_amount} and {self.blind_amount*2} for the blinds!")

    async def deal_cards(self, ctx):
        for i in range(2):
            for player in self.active_players:
                player.hand.append(self.deck.pop())
        for player in self.active_players:
            await player.send("Here are your cards:\n" + format_cards(player.hand))
        await send(ctx, "Cards dealt! Round starting.")

    async def show_common_cards(self, ctx):
        await send(ctx, "Common cards:\n" + format_cards(self.common_cards))

    def reset_bets(self):
        self.top_bet = 0
        for player in self.active_players:
            player.total_bet = 0

    async def do_flop(self, ctx):
        self.deck.pop()
        self.common_cards.append(self.deck.pop())
        self.common_cards.append(self.deck.pop())
        self.common_cards.append(self.deck.pop())
        await self.show_common_cards(ctx)
        self.reset_bets()
        self.state = FLOP 

    async def do_turn(self, ctx):
        self.deck.pop()
        self.common_cards.append(self.deck.pop())
        await self.show_common_cards(ctx)
        self.reset_bets()
        self.state = TURN

    async def do_river(self, ctx):
        self.deck.pop()
        self.common_cards.append(self.deck.pop())
        await self.show_common_cards(ctx)
        self.reset_bets()
        self.state = RIVER

    async def find_winner(self, ctx):
        winner = None
        top_value = 0
        common_total = check_combinations(self.common_cards, [])
        for player in self.active_players:
            total = check_combinations(self.common_cards, player.hand)
            if total == common_total:
                total = check_combinations([], player.hand)

            value, combination_type, combination = total
            try:
                combination[0].sort(key=to_number)
            except:
                combination.sort(key=to_number)
            print(total)

            extras = []
            if value == 1:  # High card
                extras.append(to_number(combination[0]))
            elif value == 2:  # Pair
                extras.append(to_number(combination[0][0]))
            elif value == 3:  # Two pairs
                extras.append(to_number(combination[1][0]))  # first = higher in rank, due to how pairs are generated
                extras.append(to_number(combination[0][0]))
            elif value == 4:  # Three of a kind
                extras.append(to_number(combination[0][0]))
            elif value == 5:  # Straight
                extras.append(to_number(combination[-1]))
            elif value == 6:  # Flush
                extras.append(to_number(combination[-1]))
            elif value == 7:  # Full house
                triplet = to_number(combination[0][2])
                double = to_number(combination[0][0])
                if double == triplet:
                    extras.append(to_number(combination[0][-1]))
                else:
                    extras.append(double)
                extras.append(triplet)  # always part of the triplet
            elif value == 8:  # Four of a kind
                extras.append(to_number(combination[0][0]))
            elif value == 9:  # Straight flush
                extras.append(to_number(combination[-1]))

            value <<= 8
            for i, extra in enumerate(extras):
                value |= int(extra) << (len(extras)-i-1)*4
            print(hex(value))
            if value > top_value:
                top_value = value
                winner = player
            await send(ctx, f"Player {player.name} had a **{combination_type}**.")
            print(value, combination_type, combination)
        return winner

    async def do_showdown(self, ctx):
        winner = self.active_players[0]
        if len(self.active_players) != 1:
            await self.show_common_cards(ctx)
            for player in self.active_players:
                await send(ctx, f"Player {player.name}'s hand was:")
                await send(ctx, format_cards(player.hand))
            winner = await self.find_winner(ctx)
        await send(ctx, f"Player {winner.mention} won this round and received {self.balance} !")
        winner.money += self.balance
        self.round_number += 1
        await self.start_round(ctx)

    async def next_player(self, ctx):
        global active_player
        try:
            if len(self.active_players) == 1:
                await self.do_showdown(ctx)
                return

            active_player = self.active_players[self.active_player_id]
            self.active_player_id += 1
            try:
                while active_player.money == 0 or (self.top_bet == active_player.total_bet and not self.top_bet == 0):  # don't ask those that went all in, or have already matched the top bet to bet
                    active_player = self.active_players[self.active_player_id]
                    self.active_player_id += 1
            except IndexError as e:
                raise e

            await send(ctx, f"It's {active_player.mention}'s turn to bet!")
            if self.top_bet:
                await send(ctx, f"You have to bet at least {self.top_bet-active_player.total_bet} to match, and have {active_player.money} on hand.")
        except IndexError:
            for i, player in enumerate(self.active_players):
                if player.money != 0 and player.total_bet != self.top_bet:
                # if player.total_bet != self.top_bet:
                    self.active_player_id = i
                    await self.next_player(ctx)
                    return

            if self.state == PRE_FLOP:
                await self.do_flop(ctx)
            elif self.state == FLOP:
                await self.do_turn(ctx)
            elif self.state == TURN:
                await self.do_river(ctx)
            elif self.state == RIVER:
                await self.do_showdown(ctx)
                return

            self.active_player_id = 0
            await self.next_player(ctx)

    async def start_round(self, ctx):
        for player in self.players:
            player.hand.clear()
            player.small_blind = False
            player.big_blind = False
            player.total_bet = 0
            if player.money <= 0:
                self.players.remove(player)  # remove those who lost

        if len(self.players) == 1:  # only one player remaining, the winner
            await send(ctx, f"Player {self.players[0].mention} won the game!")
            await self.end_game()
            return

        self.common_cards.clear()
        self.active_players = list(self.players)
        self.blind_amount, self.active_player_id = divmod(self.round_number, len(self.active_players))
        self.blind_amount += 1
        self.blind_amount *= self.base_blind
        self.active_players[self.active_player_id].small_blind = True
        big_blind_id = self.active_player_id+1
        big_blind_id %= len(self.active_players)
        self.active_players[big_blind_id].big_blind = True
        self.balance = 0
        self.top_bet = 0

        await self.take_blinds(ctx)
        await self.deal_cards(ctx)

        self.state = PRE_FLOP
        await self.next_player(ctx)

    async def start_game(self, ctx):
        self.started = True
        self.init_deck()
        self.round_number = 0
        await self.start_round(ctx)

game = Game()

@bot.command()
async def join(ctx):
    """Register for the game before it starts"""
    if not game.started:
        await game.add_player(ctx)
    else:
        await send(ctx, "Game already started, players list is locked.")

@bot.command()
async def leave(ctx):
    """Leave the game or queue"""
    if not game.started:
        await game.remove_player(ctx)
    else:
        if ctx.message.author == active_player.player:
            game.balance += active_player.money
            game.players.remove(active_player)
            game.active_players.remove(active_player)
            game.active_player_id -= 1
            await send(ctx, f"Player {active_player.name} left the game!\nAll their coins will go to the winner of the round!")
            await game.next_player(ctx)

@bot.command()
async def start(ctx):
    """Start a game when at least 2 people have joined"""
    if not game.started:
        if len(game.players) >= 2:
            if Player(ctx.message.author) in game.players:
                await game.start_game(ctx)
            else:
                await send(ctx, "Only players can start the game.")
        else:
            await send(ctx, "The games need 2 players or more to start.")
    else:
        await send(ctx, "Game already started.")

@bot.command()
async def abort(ctx):
    """Stop a started game before someone wins"""
    if game.started:
        if Player(ctx.message.author) in game.players:
            await game.end_game()
        else:
            await send(ctx, "Only players can cancel the game.")
    else:
        await send(ctx, "Game not started.")

@bot.command()
async def bet(ctx, amount: int):
    """Bet coins. Pretty straightforward"""
    if game.started:
        if ctx.message.author == active_player.player:
            if await active_player.bet(ctx, amount, game.top_bet):
                if amount:
                    if game.top_bet == 0:
                        game.top_bet = active_player.total_bet
                        await send(ctx, f"Player {active_player.name} opened at {amount}!")
                    elif game.top_bet < active_player.total_bet:
                        game.top_bet = active_player.total_bet
                        await send(ctx, f"Player {active_player.name} raised by {amount}!")
                    elif game.top_bet == active_player.total_bet:
                        await send(ctx, f"Player {active_player.name} called!")
                    game.balance += amount
                    await send(ctx, f"Total: {game.balance} on the table")
                await game.next_player(ctx)
    else:
        await send(ctx, "Game not started.")

@bot.command()
async def call(ctx):
    """Bet coins. Pretty straightforward"""
    if game.started:
        if ctx.message.author == active_player.player:
            amount = game.top_bet - active_player.total_bet
            await active_player.bet(ctx, amount, game.top_bet)
            await send(ctx, f"Player {active_player.name} called!")
            game.balance += amount
            await send(ctx, f"Total: {game.balance} on the table")
            await game.next_player(ctx)
    else:
        await send(ctx, "Game not started.")

@bot.command()
async def fold(ctx):
    """Discard your hand and any possible earnings this round, but don't have to bet anymore"""
    if game.started:
        if ctx.message.author == active_player.player:
            game.active_players.remove(active_player)
            game.active_player_id -= 1
            await send(ctx, f"Player {active_player.name} folded for this round!")
            await game.next_player(ctx)
    else:
        await send(ctx, "Game not started.")

@bot.command()
async def check(ctx):
    """Equivalent to betting 0 when no one has bet before"""
    if game.started:
        if ctx.message.author == active_player.player:
            if game.top_bet == 0:
                await game.next_player(ctx)
            else:
                await active_player.send("People have already bet, you can't check.")
    else:
        await send(ctx, "Game not started.")

@bot.command()
async def allin(ctx):
    """Equivalent to betting all your money, you won't have to bet anymore until the end of round"""
    if game.started:
        if ctx.message.author == active_player.player:
            total = active_player.money
            if await active_player.bet(ctx, total, 0):
                if game.top_bet < active_player.total_bet:
                    game.top_bet = active_player.total_bet
                game.balance += total
                await send(ctx, f"Player {active_player.name} went all-in and bet {total}!")
                await send(ctx, f"Total: {game.balance} on the table")
                await game.next_player(ctx)
    else:
        await send(ctx, "Game not started.")

logger = logging.getLogger('discord')
logger.setLevel(logging.WARNING)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

gen_lists()
bot.run(config['token'])