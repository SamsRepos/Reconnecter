import os
from datetime import datetime

if not os.path.exists('./log'):
  os.mkdir('log')
  
log_file_path = "./log/reconnecter" + str(datetime.now()) + ".log"
log_file_path = log_file_path.replace(" ", "-")
log_file_path = log_file_path.replace(":", "-")

def log(msg):
  with open(log_file_path, "a") as log_f:
    now_str = str(datetime.now())
    log_str = f"{now_str}: {msg}"
    log_f.write(log_str)
    log_f.write('\n\n')