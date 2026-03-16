#!/usr/bin/env python3
"""
Living Session - Trello Integration

Handles all Trello API interactions for the living session.
"""

import os
import json
import subprocess
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class TrelloCard:
    """Represents a Trello card."""
    id: str
    name: str
    desc: str
    id_list: str
    labels: List[Dict[str, Any]]
    short_url: str
    
    def has_label(self, label_name: str) -> bool:
        """Check if card has a specific label."""
        return any(label.get('name') == label_name for label in self.labels)


@dataclass
class TrelloList:
    """Represents a Trello list (column)."""
    id: str
    name: str
    cards: List[TrelloCard]


class TrelloClient:
    """Client for Trello API interactions."""
    
    def __init__(self, api_key: str = None, token: str = None):
        self.api_key = api_key or os.environ.get('TRELLO_API_KEY')
        self.token = token or os.environ.get('TRELLO_TOKEN')
        
        if not self.api_key or not self.token:
            raise ValueError("Trello API key and token required")
            
    def _api_call(self, endpoint: str, method: str = "GET", data: Dict = None) -> Any:
        """Make a Trello API call using curl."""
        url = f"https://api.trello.com/1{endpoint}"
        
        # Build curl command
        cmd = ["curl", "-s", "-X", method]
        
        # Add auth params
        auth_params = f"?key={self.api_key}&token={self.token}"
        if "?" in endpoint:
            auth_params = auth_params.replace("?", "&", 1)
        
        full_url = f"{url}{auth_params}"
        cmd.append(full_url)
        
        # Add data for POST/PUT
        if data and method in ["POST", "PUT"]:
            for key, value in data.items():
                cmd.extend(["-d", f"{key}={value}"])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"API call failed: {result.stderr}")
                return None
                
            return json.loads(result.stdout)
            
        except json.JSONDecodeError:
            print(f"Invalid JSON response from Trello API")
            return None
        except Exception as e:
            print(f"Trello API error: {e}")
            return None
            
    def get_board(self, board_id: str) -> Optional[Dict[str, Any]]:
        """Get board information."""
        return self._api_call(f"/boards/{board_id}")
        
    def get_lists(self, board_id: str) -> List[TrelloList]:
        """Get all lists (columns) in a board."""
        lists_data = self._api_call(f"/boards/{board_id}/lists")
        if not lists_data:
            return []
            
        trello_lists = []
        for list_data in lists_data:
            list_id = list_data['id']
            list_name = list_data['name']
            
            # Get cards in this list
            cards_data = self._api_call(f"/lists/{list_id}/cards")
            cards = []
            
            if cards_data:
                for card_data in cards_data:
                    cards.append(TrelloCard(
                        id=card_data['id'],
                        name=card_data['name'],
                        desc=card_data.get('desc', ''),
                        id_list=card_data['idList'],
                        labels=card_data.get('labels', []),
                        short_url=card_data.get('shortUrl', '')
                    ))
                    
            trello_lists.append(TrelloList(
                id=list_id,
                name=list_name,
                cards=cards
            ))
            
        return trello_lists
        
    def move_card(self, card_id: str, list_id: str) -> bool:
        """Move a card to a different list."""
        result = self._api_call(
            f"/cards/{card_id}",
            method="PUT",
            data={"idList": list_id}
        )
        return result is not None
        
    def add_comment(self, card_id: str, text: str) -> bool:
        """Add a comment to a card."""
        result = self._api_call(
            f"/cards/{card_id}/actions/comments",
            method="POST",
            data={"text": text}
        )
        return result is not None
        
    def get_card(self, card_id: str) -> Optional[TrelloCard]:
        """Get a specific card by ID."""
        card_data = self._api_call(f"/cards/{card_id}")
        if not card_data:
            return None
            
        return TrelloCard(
            id=card_data['id'],
            name=card_data['name'],
            desc=card_data.get('desc', ''),
            id_list=card_data['idList'],
            labels=card_data.get('labels', []),
            short_url=card_data.get('shortUrl', '')
        )
        
    def find_list_by_name(self, board_id: str, list_name: str) -> Optional[TrelloList]:
        """Find a list by its name."""
        lists = self.get_lists(board_id)
        for trello_list in lists:
            if trello_list.name == list_name:
                return trello_list
        return None
        
    def find_cards_with_label(self, board_id: str, label_name: str) -> List[TrelloCard]:
        """Find all cards with a specific label."""
        lists = self.get_lists(board_id)
        matching_cards = []
        
        for trello_list in lists:
            for card in trello_list.cards:
                if card.has_label(label_name):
                    matching_cards.append(card)
                    
        return matching_cards


class TrelloWorkManager:
    """
    High-level Trello work management for living sessions.
    
    Encapsulates the work detection and management logic.
    """
    
    def __init__(self, client: TrelloClient, board_id: str):
        self.client = client
        self.board_id = board_id
        
        # Standard list names
        self.BACKLOG = "📋 Backlog"
        self.IN_PROGRESS = "🚧 In Progress"
        self.DONE = "✅ Done"
        
        # Standard labels
        self.LABEL_READY = "🟢 Ready"
        self.LABEL_BLOCKED = "🔴 Blocked"
        self.LABEL_RESEARCH = "🟡 Research"
        
    def get_current_work(self) -> Optional[TrelloCard]:
        """
        Get the current work item (card in In Progress).
        
        Returns None if no work in progress.
        """
        in_progress_list = self.client.find_list_by_name(self.board_id, self.IN_PROGRESS)
        if in_progress_list and in_progress_list.cards:
            return in_progress_list.cards[0]  # Return first card
        return None
        
    def get_ready_work(self) -> List[TrelloCard]:
        """
        Get all ready work items from Backlog.
        
        Returns cards with 🟢 Ready label.
        """
        return self.client.find_cards_with_label(self.board_id, self.LABEL_READY)
        
    def get_blocked_work(self) -> List[TrelloCard]:
        """
        Get all blocked work items.
        
        Returns cards with 🔴 Blocked label.
        """
        return self.client.find_cards_with_label(self.board_id, self.LABEL_BLOCKED)
        
    def start_work(self, card: TrelloCard) -> bool:
        """
        Start working on a card.
        
        Moves card to In Progress list.
        """
        in_progress_list = self.client.find_list_by_name(self.board_id, self.IN_PROGRESS)
        if not in_progress_list:
            print(f"❌ Could not find '{self.IN_PROGRESS}' list")
            return False
            
        return self.client.move_card(card.id, in_progress_list.id)
        
    def complete_work(self, card: TrelloCard) -> bool:
        """
        Complete work on a card.
        
        Moves card to Done list.
        """
        done_list = self.client.find_list_by_name(self.board_id, self.DONE)
        if not done_list:
            print(f"❌ Could not find '{self.DONE}' list")
            return False
            
        return self.client.move_card(card.id, done_list.id)
        
    def add_progress_comment(self, card: TrelloCard, message: str) -> bool:
        """Add a progress comment to a card."""
        return self.client.add_comment(card.id, message)
        
    def find_next_work(self) -> Optional[TrelloCard]:
        """
        Find the next work item to work on.
        
        Priority:
        1. Continue current work (In Progress)
        2. Start new ready work (Backlog with 🟢 Ready)
        3. None available
        """
        # Check for current work
        current = self.get_current_work()
        if current:
            return current
            
        # Check for ready work
        ready = self.get_ready_work()
        if ready:
            return ready[0]
            
        return None
        
    def has_work_available(self) -> bool:
        """Check if any work is available."""
        return self.find_next_work() is not None
        
    def has_blocked_items(self) -> bool:
        """Check if any items are blocked."""
        return len(self.get_blocked_work()) > 0


# CLI for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: trello_client.py <command> [board_id]")
        print("Commands: test, lists, ready, blocked")
        sys.exit(1)
        
    command = sys.argv[1]
    board_id = sys.argv[2] if len(sys.argv) > 2 else "69b8348221251481c21323bb"  # Living Session board
    
    try:
        client = TrelloClient()
        manager = TrelloWorkManager(client, board_id)
        
        if command == "test":
            print("🧪 Testing Trello connection...")
            board = client.get_board(board_id)
            if board:
                print(f"✅ Connected to board: {board.get('name')}")
            else:
                print("❌ Connection failed")
                
        elif command == "lists":
            print(f"📋 Lists in board:")
            lists = client.get_lists(board_id)
            for trello_list in lists:
                print(f"  - {trello_list.name} ({len(trello_list.cards)} cards)")
                
        elif command == "ready":
            print(f"🟢 Ready work items:")
            ready = manager.get_ready_work()
            for card in ready:
                print(f"  - {card.name}")
                
        elif command == "blocked":
            print(f"🔴 Blocked items:")
            blocked = manager.get_blocked_work()
            for card in blocked:
                print(f"  - {card.name}")
                
        elif command == "next":
            print(f"🔍 Finding next work item...")
            next_work = manager.find_next_work()
            if next_work:
                print(f"  → {next_work.name}")
            else:
                print("  → No work available")
                
        else:
            print(f"Unknown command: {command}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
