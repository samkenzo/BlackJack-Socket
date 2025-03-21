import socket
import json
import threading
import tkinter as tk
from tkinter import simpledialog
from tkinter import messagebox

# -----------------------------
# 1. Set up the Tkinter UI
# -----------------------------
mainWindow = tk.Tk()
mainWindow.title("Blackjack Client")
mainWindow.geometry("640x480")
mainWindow.configure(bg="green")

info_label = tk.Label(mainWindow, text="", bg="green", fg="white", font=("Helvetica", 14))
info_label.pack(pady=10)

score_label = tk.Label(mainWindow, text="Score: 0", bg="green", fg="white", font=("Helvetica", 12))
score_label.pack(pady=5)

dealer_label = tk.Label(mainWindow, text="", bg="green", fg="white", font=("Helvetica", 12))
dealer_label.pack(pady=5)

result_label = tk.Label(mainWindow, text="", bg="green", fg="yellow", font=("Helvetica", 16))
result_label.pack(pady=10)

# Frame for bet entry
bet_frame = tk.Frame(mainWindow, bg="green")
bet_frame.pack(pady=10)
bet_label = tk.Label(bet_frame, text="Bet Amount:", bg="green", fg="white")
bet_label.pack(side=tk.LEFT)
bet_entry = tk.Entry(bet_frame)
bet_entry.pack(side=tk.LEFT)
bet_button = tk.Button(bet_frame, text="Place Bet")
bet_button.pack(side=tk.LEFT, padx=5)

# Frame for game buttons
button_frame = tk.Frame(mainWindow, bg="green")
button_frame.pack(pady=10)
hit_button = tk.Button(button_frame, text="Hit", state=tk.DISABLED)
hit_button.pack(side=tk.LEFT, padx=5)
stay_button = tk.Button(button_frame, text="Stay", state=tk.DISABLED)
stay_button.pack(side=tk.LEFT, padx=5)
new_game_button = tk.Button(button_frame, text="New Game", state=tk.DISABLED)
new_game_button.pack(side=tk.LEFT, padx=5)

# -----------------------------
# 2. Set up the socket connection
# -----------------------------
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.settimeout(10)

def connect_to_server():
    try:
        client_socket.connect(('127.0.0.1', 5999))
        print("✅ Connected to server!")
    except Exception as e:
        print("❌ Connection failed:", e)
        messagebox.showerror("Error", f"Connection failed: {e}")

threading.Thread(target=connect_to_server, daemon=True).start()

# -----------------------------
# 3. Communication functions
# -----------------------------
def send_command(command_dict):
    command = json.dumps(command_dict) + "\n"
    try:
        client_socket.sendall(command.encode('utf-8'))
        print(f"📤 Sent: {command_dict}")
    except Exception as e:
        print(f"❌ Error sending command: {e}")

def process_message(message):
    print("📥 Processing message:", message)
    msg_type = message.get("type")

    if msg_type == "info":
        info_label.config(text=message.get("message", ""))
        # After setting nick and receiving info, enable bet entry
        bet_button.config(state=tk.NORMAL)

    elif msg_type == "game_state":
        # Update game state information:
        player_hand = message.get("player_hand", "")
        dealer_hand = message.get("dealer_hand", "")
        score = message.get("player_score", 0)
        money = message.get("money", 0)
        info_label.config(text=f"Your Hand: {player_hand}\nMoney: ${money}")
        score_label.config(text=f"Score: {score}")
        dealer_label.config(text=f"Dealer shows: {dealer_hand}")
        # Enable hit and stay buttons after bet is placed
        hit_button.config(state=tk.NORMAL)
        stay_button.config(state=tk.NORMAL)
        new_game_button.config(state=tk.DISABLED)

    elif msg_type == "game_over":
        # Display final results
        player_hand = message.get("player_hand", "")
        dealer_hand = message.get("dealer_hand", "")
        player_score = message.get("player_score", 0)
        dealer_score = message.get("dealer_score", 0)
        result = message.get("result", "")
        money = message.get("money", 0)
        info_label.config(text=f"Your Hand: {player_hand}\nMoney: ${money}")
        score_label.config(text=f"Score: {player_score}")
        dealer_label.config(text=f"Dealer's Hand: {dealer_hand} (Score: {dealer_score})")
        result_label.config(text=result)
        # Disable hit and stay; enable new game button
        hit_button.config(state=tk.DISABLED)
        stay_button.config(state=tk.DISABLED)
        new_game_button.config(state=tk.NORMAL)

    elif msg_type == "error":
        messagebox.showerror("Error", message.get("message", "An error occurred."))

def receive_messages():
    buffer = ""
    while True:
        try:
            data = client_socket.recv(1024)
            if not data:
                print("❌ Server disconnected.")
                break
            buffer += data.decode('utf-8')
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                try:
                    message = json.loads(line)
                    mainWindow.after(0, process_message, message)
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error: {e}")
                    continue
        except Exception as e:
            print(f"❌ Error receiving data: {e}")
            break
    client_socket.close()

threading.Thread(target=receive_messages, daemon=True).start()

# -----------------------------
# 4. Command functions for UI buttons
# -----------------------------
def hit():
    send_command({"command": "hit"})

def stay():
    send_command({"command": "stay"})

def new_game():
    send_command({"command": "new_game"})
    # Clear previous results and disable new game button until new bet is placed
    result_label.config(text="")
    hit_button.config(state=tk.DISABLED)
    stay_button.config(state=tk.DISABLED)
    new_game_button.config(state=tk.DISABLED)
    info_label.config(text="Place your bet for a new game.")

def place_bet():
    try:
        amount = int(bet_entry.get())
    except ValueError:
        messagebox.showerror("Error", "Invalid bet amount.")
        return
    send_command({"command": "bet", "amount": amount})
    # Disable bet entry until next game
    bet_button.config(state=tk.DISABLED)

# -----------------------------
# 5. UI: Nickname prompt and button bindings
# -----------------------------
def set_nickname():
    nick = simpledialog.askstring("Nickname", "Enter your nickname:")
    if nick:
        send_command({"command": "set_nick", "nick": nick})
    else:
        messagebox.showerror("Error", "You must enter a nickname.")
        mainWindow.after(100, set_nickname)

# Bind buttons to functions
hit_button.config(command=hit)
stay_button.config(command=stay)
new_game_button.config(command=new_game)
bet_button.config(command=place_bet)

# Start by prompting for a nickname
mainWindow.after(100, set_nickname)

# -----------------------------
# 6. Start the Tkinter main loop
# -----------------------------
mainWindow.mainloop()
