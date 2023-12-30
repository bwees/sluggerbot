import tinydb
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open("charachters.txt") as f:
    ALL_CHARACHTERS = f.readlines()

ALL_CHARACHTERS = [x.strip().upper() for x in ALL_CHARACHTERS]  

class ReturnCodes(Enum):
    SUCCESS = 0
    ALREADY_HAS_TEAM = 1
    NO_TEAM = 2
    NOT_FREE_AGENT = 3
    NOT_ON_TEAM = 4
    INVALID_TRADE = 5
    SAME_TEAM = 6


class League:
    def __init__(self, teams_db: str, trades_db: str):
        self.teams_db = tinydb.TinyDB(teams_db)
        logger.info("Teams DB: %s Loaded Successfully", teams_db)

        self.trades_db = tinydb.TinyDB(trades_db)
        logger.info("Trades DB: %s Loaded Successfully", trades_db)


        self.free_agents = self.get_free_agents()
        logger.info(f"Free Agents: {len(self.free_agents)}")

        logger.info(f'Loaded {len(self.teams_db)} teams and {len(self.trades_db)} trades')

    def get_team(self, user_id: int):
        return self.teams_db.get(tinydb.Query().user_id == user_id)

    def get_teams(self, as_choices: bool = False):
        teams = self.teams_db.all()

        if as_choices:
            choices = {}
            for team in teams:
                choices[team["team_name"]] = str(team["user_id"])

            return choices

        return teams

    def create_team(self, user_id: int, team_name: str):
        # check if user already has a team
        if self.teams_db.contains(tinydb.Query().user_id == user_id):
            return ReturnCodes.ALREADY_HAS_TEAM

        else:
            self.teams_db.insert({"user_id": user_id, "team_name": team_name, "players": []})
            return self.get_team(user_id)

    def delete_team(self, user_id: int):
        team = self.get_team(user_id)

        if team:
            self.teams_db.remove(tinydb.Query().user_id == user_id)
            return ReturnCodes.SUCCESS
        else:
            return ReturnCodes.NO_TEAM

    def get_free_agents(self, as_choices: bool = False):
        all_players = ALL_CHARACHTERS.copy()
        
        for team in self.teams_db.all():
            for player in team["players"]:
                all_players.remove(player)

        if as_choices:
            choices = {}
            for player in all_players:
                choices[player] = player

            return choices

        return all_players

    def add_player(self, user_id: int, player: str):
        team = self.get_team(user_id)
        if team:
            if player not in self.free_agents:
                return ReturnCodes.NOT_FREE_AGENT

            team["players"].append(player)
            self.teams_db.update(team, tinydb.Query().user_id == user_id)
            self.free_agents.remove(player)

            return ReturnCodes.SUCCESS
        else:
            return ReturnCodes.NO_TEAM

    def remove_player(self, user_id: int, player: str):
        team = self.get_team(user_id)

        if team:
            if player not in team["players"]:
                return ReturnCodes.NOT_ON_TEAM

            team["players"].remove(player)
            self.teams_db.update(team, tinydb.Query().user_id == user_id)
            self.free_agents.append(player)

            return ReturnCodes.SUCCESS
        else:
            return ReturnCodes.NO_TEAM

    def get_players(self, user_id: int):
        team = self.get_team(user_id)

        if team:
            return team["players"]
        else:
            return ReturnCodes.NO_TEAM

    def create_trade(self, user1_id: int, user2_id: int, user1_trade: str, user2_trade: str):
        trade = Trade(user1_id, user2_id, user1_trade, user2_trade)
        
        if trade.validate_trade(self) == ReturnCodes.SUCCESS:
            # add trade to db
            self.trades_db.insert({"user1_id": user1_id, "user2_id": user2_id, "user1_trade": user1_trade, "user2_trade": user2_trade})
            return trade
        else:
            return ReturnCodes.INVALID_TRADE
        
    def cancel_trade(self, trade: "Trade"):
        trade = self.get_trade(trade.message_id)
        if trade:
            self.trades_db.remove(tinydb.Query().message_id == trade.message_id)
            return ReturnCodes.SUCCESS
        else:
            return ReturnCodes.INVALID_TRADE
        
    def process_trade(self, trade: "Trade"):
        trade = self.get_trade(trade.message_id)
        if trade and trade.validate_trade(self) == ReturnCodes.SUCCESS:
            user1_team = self.get_team(trade.user1_id)
            user2_team = self.get_team(trade.user2_id)

            user1_team["players"].remove(trade.user1_trade)
            user1_team["players"].append(trade.user2_trade)

            user2_team["players"].remove(trade.user2_trade)
            user2_team["players"].append(trade.user1_trade)

            self.teams_db.update(user1_team, tinydb.Query().user_id == trade.user1_id)
            self.teams_db.update(user2_team, tinydb.Query().user_id == trade.user2_id)

            self.trades_db.remove(tinydb.Query().message_id == trade.message_id)

            return ReturnCodes.SUCCESS
        else:
            return ReturnCodes.INVALID_TRADE
        
    def assign_trade_message(self, trade: "Trade", message_id: int):
        self.trades_db.update({"message_id": message_id}, tinydb.Query().user1_id == trade.user1_id and tinydb.Query().user2_id == trade.user2_id and tinydb.Query().user1_trade == trade.user1_trade and tinydb.Query().user2_trade == trade.user2_trade)

    def get_trade(self, msg_id: int):
        if self.trades_db.get(tinydb.Query().message_id == int(msg_id)) is None:
            return None
        
        return Trade.from_dict(self.trades_db.get(tinydb.Query().message_id == msg_id))
    
    def get_trades(self):
        return [Trade.from_dict(trade) for trade in self.trades_db.all()]
    
        

    
class Trade:
    def __init__(self, user1_id: int, user2_id: int, user1_trade: str, user2_trade: str, message_id: int = None):
        self.user1_id = user1_id
        self.user2_id = user2_id
        self.user1_trade = user1_trade
        self.user2_trade = user2_trade
        self.message_id = message_id

    def __str__(self):
        return f'{self.user1_id} trades {self.user1_trade} for {self.user2_id}"s {self.user2_trade}'
    
    @staticmethod
    def from_dict(trade_dict: dict):
        return Trade(trade_dict["user1_id"], trade_dict["user2_id"], trade_dict["user1_trade"], trade_dict["user2_trade"], trade_dict["message_id"])

    def validate_trade(self, league: League):
        user1_team = league.get_team(self.user1_id)
        user2_team = league.get_team(self.user2_id)

        if user1_team == user2_team:
            return ReturnCodes.SAME_TEAM

        if user1_team and user2_team:
            if self.user1_trade not in user1_team["players"]:
                return ReturnCodes.NOT_ON_TEAM

            if self.user2_trade not in user2_team["players"]:
                return ReturnCodes.NOT_ON_TEAM

            return ReturnCodes.SUCCESS
        else:
            return ReturnCodes.NO_TEAM
