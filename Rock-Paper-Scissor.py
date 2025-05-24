import cv2
import mediapipe as mp
import random
import time
from datetime import datetime, timedelta

# Initialize MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1)
mp_draw = mp.solutions.drawing_utils

# Game state variables
player_wins = 0
computer_wins = 0
game_over = False
round_count = 0
round_start_time = None
ROUND_DURATION = 5  # 5 seconds per round
waiting_for_next_round = False
last_round_end_time = None
ROUND_COOLDOWN = 3  
computer_move = ""  # Initialize computer_move
winner = ""        # Initialize winner

# Colors for GUI
COLORS = {
    'text': (255, 255, 255),  # White
    'player': (0, 255, 255),  # Yellow
    'computer': (255, 100, 100),  # Red
    'result': (0, 255, 0),    # Green
    'score': (255, 165, 0),   # Orange
    'game_over': (0, 0, 255)  # Blue
}

# Game logic
def get_hand_gesture(hand_landmarks):
    finger_tips_ids = [4, 8, 12, 16, 20]
    fingers = []

    landmarks = hand_landmarks.landmark

    # Thumb
    if landmarks[finger_tips_ids[0]].x < landmarks[finger_tips_ids[0] - 1].x:
        fingers.append(1)
    else:
        fingers.append(0)

    # Other 4 fingers
    for id in range(1, 5):
        if landmarks[finger_tips_ids[id]].y < landmarks[finger_tips_ids[id] - 2].y:
            fingers.append(1)
        else:
            fingers.append(0)

    total_fingers = fingers.count(1)

    # Classify based on finger count
    if total_fingers == 0:
        return "rock"
    elif total_fingers == 2 and fingers[1] == 1 and fingers[2] == 1:
        return "scissors"
    elif total_fingers == 5:
        return "paper"
    else:
        return "unknown"

# Result logic
def get_winner(player, computer):
    if player == computer:
        return "Draw"
    elif (player == "rock" and computer == "scissors") or \
         (player == "scissors" and computer == "paper") or \
         (player == "paper" and computer == "rock"):
        return "You Win!"
    else:
        return "You Lose!"

def get_remaining_time():
    if round_start_time is None:
        return ROUND_DURATION
    elapsed = (datetime.now() - round_start_time).total_seconds()
    remaining = max(0, ROUND_DURATION - elapsed)
    return remaining

def start_new_round():
    global round_start_time, waiting_for_next_round, last_round_end_time, prev_move, computer_move, winner
    round_start_time = datetime.now()  # Only set the time when starting a new round
    waiting_for_next_round = False
    last_round_end_time = None
    prev_move = None
    computer_move = ""
    winner = ""

def reset_game():
    global player_wins, computer_wins, game_over, round_count, round_start_time, waiting_for_next_round, last_round_end_time, prev_move, computer_move, winner
    player_wins = 0
    computer_wins = 0
    game_over = False
    round_count = 0
    round_start_time = datetime.now()
    waiting_for_next_round = False
    last_round_end_time = None
    prev_move = None
    computer_move = ""  # Reset computer move
    winner = ""        # Reset winner

# Start webcam
print("Initializing webcam...")
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam!")
    exit()

prev_move = None

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error reading frame from camera")
        cap.release()
        time.sleep(1)
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not reconnect to webcam!")
            break
        continue

    # Flip image for mirror view
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb_frame)

    player_move = "none"
    current_time = datetime.now()

    # Handle round timing and transitions
    if not game_over:
        if round_start_time is None:
            start_new_round()
        
        remaining_time = get_remaining_time()
        
        # Only process hand detection if we're not waiting for next round
        if not waiting_for_next_round:
            if result.multi_hand_landmarks:
                for handLms in result.multi_hand_landmarks:
                    mp_draw.draw_landmarks(frame, handLms, mp_hands.HAND_CONNECTIONS)
                    player_move = get_hand_gesture(handLms)

            # Only process moves if we have time remaining
            if remaining_time > 0:
                if player_move != "unknown" and player_move != "none":
                    if prev_move != player_move:
                        computer_move = random.choice(["rock", "paper", "scissors"])
                        winner = get_winner(player_move, computer_move)
                        prev_move = player_move
                        
                        if winner == "You Win!":
                            player_wins += 1
                        elif winner == "You Lose!":
                            computer_wins += 1
                        
                        round_count += 1
                        waiting_for_next_round = True
                        last_round_end_time = current_time
                        
                        if player_wins >= 3 or computer_wins >= 3:
                            game_over = True
            
            # Handle time's up condition
            elif remaining_time <= 0 and not waiting_for_next_round:
                waiting_for_next_round = True
                last_round_end_time = current_time
                if player_move == "none" or player_move == "unknown":
                    winner = "Time's Up!"
                    computer_move = random.choice(["rock", "paper", "scissors"])
                    computer_wins += 1
                    round_count += 1
                    if player_wins >= 3 or computer_wins >= 3:
                        game_over = True
        
        # Handle round transition
        if waiting_for_next_round:
            if (current_time - last_round_end_time).total_seconds() >= ROUND_COOLDOWN:
                start_new_round()
    else:
        winner = "Game Over!"
        computer_move = ""

    # Create a semi-transparent overlay for better text visibility
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 150), (0, 0, 0), -1)  # Reduced height from 200 to 120
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Display game info with improved layout
    y_offset = 30
    line_height = 30

    # Display timer and round status
    if not game_over:
        if waiting_for_next_round:
            cooldown_time = ROUND_COOLDOWN - (current_time - last_round_end_time).total_seconds()
            if cooldown_time > 0:
                cv2.putText(frame, f"Next round in: {cooldown_time:.1f}s", 
                            (w - 250, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLORS['text'], 2)
            else:
                cv2.putText(frame, "Get Ready!", 
                            (w - 200, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLORS['text'], 2)
        else:
            timer_text = f"Time: {remaining_time:.1f}s"
            cv2.putText(frame, timer_text, 
                        (w - 200, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLORS['text'], 2)

    # Display scores
    cv2.putText(frame, f"Score - You: {player_wins} | Computer: {computer_wins}", 
                (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLORS['score'], 2)
    
    # Display moves
    if not waiting_for_next_round or game_over:
        cv2.putText(frame, f"Your Move: {player_move}", 
                    (10, y_offset + line_height), cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLORS['player'], 2)
        cv2.putText(frame, f"Computer: {computer_move}", 
                    (10, y_offset + line_height * 2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLORS['computer'], 2)
    
    # Display result
    if game_over:
        result_text = f"Game Over! {'You' if player_wins >= 3 else 'Computer'} wins the match!"
        cv2.putText(frame, result_text, 
                    (10, y_offset + line_height * 3), cv2.FONT_HERSHEY_SIMPLEX, 0.9, COLORS['game_over'], 2)
        cv2.putText(frame, "Press 'r' to restart", 
                    (10, y_offset + line_height * 4), cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLORS['text'], 2)
    else:
        cv2.putText(frame, f"Result: {winner}", 
                    (10, y_offset + line_height * 3), cv2.FONT_HERSHEY_SIMPLEX, 0.9, COLORS['result'], 2)

    cv2.imshow("Rock Paper Scissors - Hand Gesture", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('r') and game_over:
        reset_game()

cap.release()
cv2.destroyAllWindows()
