# from utils import cwd_stack, run_proc, is_admin, ctypes, sys
# from logger import logger
# import os
# import win32com.shell as shell

# cwd_stack = cwd_stack()

# EVPN_DIR = r"C:\Program Files (x86)\ExpressVPN"

# EVPN_CONNECT_CMD    = "ExpressVPN.CLI connect"
# EVPN_DISCONNECT_CMD = "ExpressVPN.CLI disconnect"
# EVPN_STATUS_CMD     = "ExpressVPN.CLI status"

# class EvpnHandler:
#   def __init__(self, logger):
#     self.logger = logger

#   def run_cmd(self, cmd):
#     self.logger.log(f"Changing cwd to {EVPN_DIR}")
#     cwd_stack.push(EVPN_DIR)
#     self.logger.log(f"Current cwd: {os.getcwd()}")

#     self.logger.log(f"Running command: '{EVPN_CONNECT_CMD}'")

#     if is_admin():
#       output = run_proc(cmd)
#       self.logger.log(output)
#     else:
#       # Re-run the program with admin rights
#       #ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, cmd, None, 1)
#       shell.ShellExecuteEx(lpVerb='runas', lpFile="ExpressVPN.CLI", lpParameters=" connect")
    
#     cwd_stack.pop()
#     self.logger.log(f"Cwd restored to: {os.getcwd()}")

#   def connect(self):
#     self.run_cmd(EVPN_CONNECT_CMD)

#   def disconnect(self):
#     self.run_cmd(EVPN_DISCONNECT_CMD)
  