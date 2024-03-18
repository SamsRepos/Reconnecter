import os
from datetime import datetime

if not os.path.exists('./log'):
  os.mkdir('log')
  
RELATIVE_LOG_FILE_PATH = "./log/"


class logger:
  def __init__(self, verbose):
    self.verbose = verbose

    log_file_name = f"reconnecter{datetime.now()}.log".replace(" ", "-").replace(":", "-")
    self.log_file_path = os.path.abspath(RELATIVE_LOG_FILE_PATH)
    self.log_file_path = os.path.join(self.log_file_path, log_file_name)

  def log(self, msg):
    with open(self.log_file_path, "a") as log_f:
      now_str = str(datetime.now())
      log_str = f"{now_str}: {msg}"
      log_f.write(log_str)
      log_f.write('\n\n')
    
    if(self.verbose):
      print(log_str)
