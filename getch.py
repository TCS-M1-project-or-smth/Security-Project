from sys import platform


class _Getch:
	"""Gets a single character from standard input.  Does not echo to the
screen."""

	def __init__(self):
		if platform == "win32":
			self.impl = _GetchWindows()
		else:
			self.impl = _GetchUnix()

	def __call__(self):
		return self.impl()


class _GetchUnix:
	def __call__(self):
		import sys
		import tty
		import termios

		fd = sys.stdin.fileno()
		old_settings = termios.tcgetattr(fd)
		try:
			tty.setraw(sys.stdin.fileno())
			ch = sys.stdin.read(1)
		finally:
			termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
		return ch


class _GetchWindows:
	def __call__(self):
		import msvcrt
		return msvcrt.getch()


getch = _Getch()
