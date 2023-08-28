from subprocess import Popen
import subprocess
from time import sleep
import datetime

log_f_name = "reconnecter" + str(datetime.datetime.now()) + ".log"
log_f_name = log_f_name.replace(" ", "-")
log_f_name = log_f_name.replace(":", "-")

def write_log(log_str):
  with open(log_f_name, "a") as log_f:
    now_str = str(datetime.datetime.now())
    log_s = f"{now_str}: {log_str}"
    
    log_f.write(log_s)
    log_f.write('\n\n')

    print(log_s)

def run_proc(cmd):
  #p = Popen([bat_f, "-p"], stdout=subprocess.PIPE)
  p = Popen(cmd, stdout=subprocess.PIPE)
  p_out, p_err = p.communicate()
  return str(p_out)

def reconnect():
  nets_res = run_proc("netsh wlan show networks")
  nets_res = nets_res.split("\\r\\n")
  net_ids = list()

  for line in nets_res:
    if "SSID" in line:
      net_id = line.split(":")[1].strip()
      net_ids.append(net_id)

  valid_ids = [id for id in net_ids if id in profiles]

  print(valid_ids)

  teststr = valid_ids[0]

  connect_cmd = f'netsh wlan connect ssid="{teststr}" name="{teststr}"'
  
  connect_res = run_proc(connect_cmd)

  print(connect_res)


#on startup, getting network profiles
profiles_res = run_proc("netsh wlan show profile")
profiles_res = profiles_res.split("User profiles")[1]
profiles_res = profiles_res.split("\\r\\n")

profiles = list()
for line in profiles_res:
  if ":" in line:
    profile = line.split(":")[1].strip()
    profiles.append(profile)

#main loop:
while True:
  connected_res = run_proc("amIConnected.bat")
  parsed_1 = connected_res.split("'")[1]
  parsed_2 = parsed_1.split("\\")[0]
  p_res = parsed_2.strip()

  write_log(p_res)
  print(p_res)

  if p_res == "connected":
    pass
  elif p_res == "not connected":
    print('\a')
    reconnect()
  
  sleep(3)
