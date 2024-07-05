from datetime import datetime
from subprocess import Popen, PIPE
import os

import ctypes, sys

def seconds_to_hours(secs):
    mm, ss = divmod(secs, 60)
    hh, mm = divmod(mm, 60)
    return "%d:%02d:%02d" % (hh, mm, ss)

def datetime_formatted(dt):
  return dt.strftime('%H:%M:%S %d/%m/%Y')
#  return dt.strftime('%d/%m/%Y, %H:%M:%S')

def timeonly_formatted(dt):
  return dt.strftime('%H:%M:%S')

def run_proc(cmd):
  p = Popen(cmd, stdout=PIPE)
  p_out, p_err = p.communicate()
  return str(p_out)

# parses command output for netsh commands - NOT for batch file's echo output
def parse_cmd_output(msg):
  return msg.split("\\r\\n")

def netsh_info_to_val(msg):
  return msg.split(":")[1].strip()

clear = lambda: os.system('cls')

class CwdStack:
  def __init__(self):
    self.list = []
    self.push(os.getcwd())

  def push(self, path):
    self.list.append(path)
    os.chdir(path)

  def pop(self):
    self.list.pop()
    os.chdir(self.list[-1])



def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


