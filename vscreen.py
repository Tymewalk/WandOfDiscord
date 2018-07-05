# VSCREEN
# Allows you to make a virtual terminal screen of arbitrary size.
# You could use this for something else, although I just used it for WandOfDiscord.
class VScreen(object):
    def __init__(self, size_x, size_y):
        self.size_x = size_x
        self.size_y = size_y
        self.screen = self._genscreen(size_x, size_y)

    def _genscreen(self, x, y, char=' '):
        return [char*x]*y

    def get_screen(self):
        '''Get the current screen as a string.'''
        to_return = ""
        for row in self.screen:
            to_return += (row + "\n")

        return to_return

    def blit(self, msg, x, y):
        '''Output a string to the screen. Does not wrap around.'''
        row = list(self.screen[y])
        if (len(msg) + x) > len(row):
            msg = msg[0:(len(msg) - x)]
        row[x:(len(msg) + x)] = msg
        row = ''.join(row)
        self.screen[y] = row

    def clear(self):
        '''Clear the whole screen.'''
        self.screen = self._genscreen(self.size_x, self.size_y)