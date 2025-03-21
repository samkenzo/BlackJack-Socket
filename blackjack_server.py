import socket
import threading
import json
import random
import time

# --- Game Logic Classes ---

class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def value(self):
        if self.rank in ['J', 'Q', 'K']:
            return 10
        elif self.rank == "A":
            return 11
        else:
            return int(self.rank)

    def __str__(self):
        return f"{self.suit}{self.rank}"

class Deck:
    def __init__(self):
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        suits = ['♥', '♦', '♣', '♠']
        self.cards = [Card(rank, suit) for rank in ranks for suit in suits]

    def shuffle(self):
        random.shuffle(self.cards)

    def deal(self):
        if len(self.cards) == 0:
            self.__init__()
            self.shuffle()
        return self.cards.pop(0)

class Dealer:
    def __init__(self):
        self.hand = []

    def add_card(self, deck):
        card = deck.deal()
        self.hand.append(card)

    def score(self):
        score = 0
        aces = 0
        for card in self.hand:
            score += card.value()
            if card.rank == "A":
                aces += 1
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    def hand_str(self):
        return " ".join(str(card) for card in self.hand)

class Player:
    def __init__(self, nick="Player"):
        self.nick = nick
        self.hand = []
        self.money = 10000
        self.bet = 0

    def add_card(self, deck):
        card = deck.deal()
        self.hand.append(card)

    def score(self):
        score = 0
        aces = 0
        for card in self.hand:
            score += card.value()
            if card.rank == "A":
                aces += 1
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    def hand_str(self):
        return " ".join(str(card) for card in self.hand)

class BlackjackGame:
    def __init__(self, player_nick):
        self.deck = Deck()
        self.deck.shuffle()
        self.dealer = Dealer()
        self.player = Player(player_nick)
        self.game_over = False
        self.result = ""

    def place_bet(self, amount):
        if amount > self.player.money or amount <= 0:
            return False
        self.player.bet = amount
        self.player.money -= amount
        return True

    def initial_deal(self):
        # Reset hands
        self.player.hand = []
        self.dealer.hand = []
        # Deal 2 cards to player and dealer
        self.player.add_card(self.deck)
        self.dealer.add_card(self.deck)
        self.player.add_card(self.deck)
        self.dealer.add_card(self.deck)

    def player_hit(self):
        self.player.add_card(self.deck)

    def dealer_turn(self):
        while self.dealer.score() < 17:
            time.sleep(1)  # pacing delay (optional)
            self.dealer.add_card(self.deck)

    def evaluate_game(self):
        player_score = self.player.score()
        dealer_score = self.dealer.score()
        if player_score > 21:
            self.result = "Bust! You lose."
        elif dealer_score > 21:
            self.result = "Dealer busts! You win."
            self.player.money += 2 * self.player.bet
        elif player_score > dealer_score:
            self.result = "You win!"
            self.player.money += 2 * self.player.bet
        elif dealer_score > player_score:
            self.result = "Dealer wins!"
        else:
            self.result = "It's a tie!"
            self.player.money += self.player.bet
        self.game_over = True

# --- Server Class ---

class BlackjackServer:
    def __init__(self, host='0.0.0.0', port=5999):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(5)
        print(f"Server started on {host}:{port}")
        self.clients = []
        self.games = {}  # mapping client socket to their game instance

    def send(self, client, message):
        data = (json.dumps(message) + "\n").encode('utf-8')
        try:
            client.sendall(data)
        except Exception as e:
            print(f"Error sending to client: {e}")

    def handle_client(self, client, addr):
        print(f"✅ Client connected: {addr}")
        self.clients.append(client)
        game = None
        buffer = ""
        try:
            while True:
                data = client.recv(1024)
                if not data:
                    print(f"❌ Client {addr} disconnected.")
                    break
                buffer += data.decode('utf-8')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    try:
                        message = json.loads(line)
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON decode error from {addr}: {e}")
                        continue

                    print(f"✅ Received from {addr}: {message}")

                    cmd = message.get("command")
                    if cmd == "set_nick":
                        nick = message.get("nick", "Player")
                        game = BlackjackGame(nick)
                        self.games[client] = game
                        self.send(client, {"type": "info", "message": f"Nickname set to {nick}. You have ${game.player.money}."})
                    elif cmd == "bet":
                        if game is None:
                            self.send(client, {"type": "error", "message": "Set your nickname first."})
                            continue
                        amount = message.get("amount", 0)
                        if game.place_bet(amount):
                            self.send(client, {"type": "info", "message": f"Bet of ${amount} placed. Dealing cards..."})
                            game.initial_deal()
                            # Send initial game state: show both player cards and dealer's first card only
                            self.send(client, {
                                "type": "game_state",
                                "player_hand": game.player.hand_str(),
                                "dealer_hand": str(game.dealer.hand[0]),
                                "player_score": game.player.score(),
                                "money": game.player.money
                            })
                        else:
                            self.send(client, {"type": "error", "message": "Invalid bet or insufficient funds."})
                    elif cmd == "hit":
                        if game is None:
                            self.send(client, {"type": "error", "message": "Game not started."})
                            continue
                        game.player_hit()
                        score = game.player.score()
                        self.send(client, {
                            "type": "game_state",
                            "player_hand": game.player.hand_str(),
                            "player_score": score
                        })
                        if score > 21:
                            game.game_over = True
                            game.result = "Bust! You lose."
                            self.send(client, {"type": "game_over", "result": game.result, "money": game.player.money})
                    elif cmd == "stay":
                        if game is None:
                            self.send(client, {"type": "error", "message": "Game not started."})
                            continue
                        game.dealer_turn()
                        game.evaluate_game()
                        self.send(client, {
                            "type": "game_over",
                            "player_hand": game.player.hand_str(),
                            "player_score": game.player.score(),
                            "dealer_hand": game.dealer.hand_str(),
                            "dealer_score": game.dealer.score(),
                            "result": game.result,
                            "money": game.player.money
                        })
                    elif cmd == "new_game":
                        if game is None:
                            self.send(client, {"type": "error", "message": "Game not started."})
                            continue
                        # Start a new game using the same nickname and money
                        game = BlackjackGame(game.player.nick)
                        # Preserve money from previous game
                        game.player.money = self.games[client].player.money
                        self.games[client] = game
                        self.send(client, {"type": "info", "message": f"New game started. You have ${game.player.money}. Place your bet."})
                    else:
                        self.send(client, {"type": "error", "message": "Unknown command."})
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            print(f"Client disconnected: {addr}")
            if client in self.clients:
                self.clients.remove(client)
            if client in self.games:
                del self.games[client]
            client.close()

    def run(self):
        while True:
            client, addr = self.server.accept()
            thread = threading.Thread(target=self.handle_client, args=(client, addr))
            thread.daemon = True
            thread.start()

if __name__ == "__main__":
    server = BlackjackServer()
    server.run()
