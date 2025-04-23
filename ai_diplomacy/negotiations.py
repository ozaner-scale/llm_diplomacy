from dotenv import load_dotenv
import logging
import concurrent.futures
from typing import Dict, TYPE_CHECKING

from diplomacy.engine.message import Message, GLOBAL

from .agent import DiplomacyAgent
from .clients import load_model_client
from .utils import gather_possible_orders, load_prompt

if TYPE_CHECKING:
    from .game_history import GameHistory
    from diplomacy import Game

logger = logging.getLogger("negotiations")
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

load_dotenv()


def conduct_negotiations(
    game: 'Game',
    agents: Dict[str, DiplomacyAgent],
    game_history: 'GameHistory',
    model_error_stats: Dict[str, Dict[str, int]],
    max_rounds: int = 3,
    early_exit: bool = False,
):
    """
    Conducts a round-robin conversation among all non-eliminated powers.
    Each power can send up to 'max_rounds' messages, choosing between private
    and global messages each turn.
    
    Args:
        game: The Diplomacy game instance
        agents: Dictionary of DiplomacyAgent instances by power name
        game_history: The game history object
        model_error_stats: Dictionary to track model errors
        max_rounds: Maximum number of negotiation rounds
        early_exit: If True, will raise an exception on conversation error for early program exit
    """
    logger.info("Starting negotiation phase.")

    active_powers = [
        p_name for p_name, p_obj in game.powers.items() if not p_obj.is_eliminated()
    ]
    
    # Track negotiation errors for visualization
    conversation_errors = {}
    
    # Set up colorful error formatting
    RED = "\033[1;31m"
    YELLOW = "\033[1;33m"
    CYAN = "\033[1;36m"
    GREEN = "\033[1;32m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    # We do up to 'max_rounds' single-message turns for each power
    for round_index in range(max_rounds):
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=1
        ) as executor:
            futures = {}
            for power_name in active_powers:
                if power_name not in agents:
                    logger.warning(f"Agent for {power_name} not found in negotiations. Skipping.")
                    continue
                agent = agents[power_name]
                client = agent.client

                possible_orders = gather_possible_orders(game, power_name)
                if not possible_orders:
                    logger.info(f"No orderable locations for {power_name}; skipping.")
                    continue
                board_state = game.get_state()

                future = executor.submit(
                    client.get_conversation_reply,
                    game,
                    board_state,
                    power_name,
                    possible_orders,
                    game_history,
                    game.current_short_phase,
                    active_powers,
                    agent_goals=agent.goals,
                    agent_relationships=agent.relationships,
                )

                futures[future] = power_name
                logger.debug(f"Submitted get_conversation_reply task for {power_name}.")

            for future in concurrent.futures.as_completed(futures):
                power_name = futures[future]
                try:
                    messages, error_info = future.result()
                    
                    # If there's error information, store it for visualization
                    if error_info:
                        if power_name not in conversation_errors:
                            conversation_errors[power_name] = []
                        
                        # Add round info to the error
                        error_info["round"] = round_index + 1
                        error_info["phase"] = game.current_short_phase
                        
                        conversation_errors[power_name].append(error_info)
                        model_error_stats[power_name]["conversation_errors"] += 1
                        
                        # Print colorful error message to console
                        error_type = error_info.get("error_type", "unknown")
                        error_msg = error_info.get("message", "No details")
                        print(f"\n{RED}{'='*80}{RESET}")
                        print(f"{RED}CONVERSATION ERROR{RESET} {YELLOW}[{power_name}]{RESET} {CYAN}(Round {round_index+1}){RESET}: {BOLD}{error_type}{RESET}")
                        print(f"{YELLOW}Error details:{RESET} {error_msg}")
                        
                        # Show a snippet of raw response if available
                        raw_response = error_info.get("raw_response", "")
                        if raw_response:
                            # Limit to first 200 chars
                            snippet = raw_response[:200] + ("..." if len(raw_response) > 200 else "")
                            print(f"{YELLOW}Response snippet:{RESET} {snippet}")
                        
                        print(f"{RED}{'='*80}{RESET}")
                        
                        # Add error to agent journal
                        agents[power_name].add_journal_entry(
                            f"Failed to generate message in {game.current_short_phase} (Round {round_index+1}): {error_type}"
                        )
                        
                        # Exit early if requested
                        if early_exit:
                            raise RuntimeError(f"Early exit due to conversation error for {power_name}: {error_type}")

                    if messages:
                        for message in messages:
                            # Create an official message in the Diplomacy engine
                            # Determine recipient based on message type
                            if message.get("message_type") == "private":
                                recipient = message.get("recipient", GLOBAL) # Default to GLOBAL if recipient missing somehow
                                if recipient not in game.powers and recipient != GLOBAL:
                                    logger.warning(f"Invalid recipient '{recipient}' in message from {power_name}. Sending globally.")
                                    recipient = GLOBAL # Fallback to GLOBAL if recipient power is invalid
                            else: # Assume global if not private or type is missing
                                recipient = GLOBAL
                                
                            diplo_message = Message(
                                phase=game.current_short_phase,
                                sender=power_name,
                                recipient=recipient, # Use determined recipient
                                message=message.get("content", ""), # Use .get for safety
                                time_sent=None, # Let the engine assign time
                            )
                            game.add_message(diplo_message)
                            # Also add to our custom history
                            game_history.add_message(
                                game.current_short_phase,
                                power_name,
                                recipient, # Use determined recipient here too
                                message.get("content", ""), # Use .get for safety
                            )
                            journal_recipient = f"to {recipient}" if recipient != GLOBAL else "globally"
                            agent.add_journal_entry(f"Sent message {journal_recipient} in {game.current_short_phase}: {message.get('content', '')[:100]}...")
                            
                            # Print success message in green
                            msg_type = "GLOBAL" if recipient == GLOBAL else f"PRIVATE to {recipient}"
                            print(f"{GREEN}MESSAGE SENT{RESET} {YELLOW}[{power_name}]{RESET} {CYAN}({msg_type}){RESET}")
                    else:
                        logger.debug(f"No valid messages returned for {power_name}.")
                except Exception as e:
                    logger.error(f"Exception in processing conversation reply for {power_name}: {e}")
                    model_error_stats[power_name]["conversation_errors"] += 1
                    
                    # Print colorful error message for exceptions
                    print(f"\n{RED}{'='*80}{RESET}")
                    print(f"{RED}CONVERSATION PROCESSING ERROR{RESET} {YELLOW}[{power_name}]{RESET}: {str(e)}")
                    print(f"{RED}{'='*80}{RESET}")
                    
                    # Exit early if requested
                    if early_exit:
                        raise RuntimeError(f"Early exit due to conversation processing error for {power_name}: {str(e)}")
    
    # Store conversation errors in game history for visualization
    game_history.conversation_errors = conversation_errors
    
    # Log error summary
    error_count = sum(len(errors) for errors in conversation_errors.values())
    if error_count > 0:
        error_msg = f"Negotiation phase completed with {error_count} conversation errors."
        logger.info(f"{RED}{error_msg}{RESET}" if error_count > 0 else error_msg)
    else:
        logger.info(f"{GREEN}Negotiation phase complete with no errors.{RESET}")
    
    return game_history
