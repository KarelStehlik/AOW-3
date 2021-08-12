from constants import *


class upgrade:
    cost = 0
    time = 0

    def __init__(self, game, side):
        game.players[side].pending_upgrades.append(self)
        self.time_remaining = self.time * FPS
        self.game = game
        self.side = side

    def upgrading_tick(self):
        self.time -= 1
        if self.time < 0:
            self.finished()
            return True
        return False

    def finished(self):
        self.game.players[self.side].pending_upgrades.remove(self)
        self.game.players[self.side].owned_upgrades.append(self)
        self.on_finish()

    def on_finish(self):
        pass
